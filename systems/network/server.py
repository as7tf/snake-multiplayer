import asyncio
import hashlib
import multiprocessing as mp
import queue as q
import struct
import threading as th
import time
import traceback as tb
from enum import Enum, auto
from typing import Callable

from systems.network.constants import CONNECTION_EXCEPTION
from systems.network.data_stream import DataStream
from utils.timer import Timer  # , print_async_func_time, print_func_time


class ServerState(Enum):
    IDLE = auto()
    LOBBY = auto()
    PLAYING = auto()
    EXITING = auto()


class AwaitableQueue:
    def __init__(
        self,
        maxsize: int,
    ):
        self._queue = mp.Queue(maxsize)
        self._loop = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    # @print_async_func_time
    async def async_put(self, item, timeout=None):
        await self._loop.run_in_executor(None, self._queue.put, item, True, timeout)

    # @print_async_func_time
    async def async_get(self, timeout=None):
        try:
            return await self._loop.run_in_executor(
                None, self._queue.get, True, timeout
            )
        except q.Empty:
            return None

    # @print_func_time
    def get(self, timeout=None):
        return self._queue.get(timeout=timeout)

    # @print_func_time
    def put(self, item, timeout=None):
        self._queue.put(item, timeout=timeout)


class ClientConnection:
    def __init__(
        self,
        client_id: str,
        network_writer: asyncio.StreamWriter,
        network_reader: asyncio.StreamReader,
    ):
        self._network_writer = network_writer
        self._network_reader = network_reader
        self._network_lock = asyncio.Lock()
        self._network_loop = asyncio.get_running_loop()

        self.id = client_id

        self.response_pipe = DataStream()
        self.client_data_pipe = DataStream()

    async def disconnect(self):
        async with self._network_lock:
            self._network_writer.close()
            await self._network_writer.wait_closed()

    async def network_send(self, message: str):
        data = message.encode()
        length_prefix = struct.pack("!I", len(data))
        async with self._network_lock:
            self._network_writer.write(length_prefix + data)
            await self._network_writer.drain()

    async def network_receive(self):
        prefix_length = await self._network_reader.read(4)
        if prefix_length is not None and len(prefix_length) == 4:
            message_length = struct.unpack("!I", prefix_length)[0]
            data = await self._network_reader.read(message_length)
            return data
        else:
            return None

    async def read_server_response(self, timeout=0):
        return await self._network_loop.run_in_executor(
            None, self.response_pipe.read, timeout
        )

    def write_client_data(self, data):
        self.client_data_pipe.write(data)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ClientConnection):
            return self.id == other.id
        return False

    def __repr__(self) -> str:
        return self.id


class MPClientConnection:
    def __init__(self, client_connection: ClientConnection):
        self.id = client_connection.id
        self.client_data_pipe = client_connection.client_data_pipe

    def __eq__(self, other):
        if isinstance(other, MPClientConnection):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)


class ClientList:
    def __init__(self):
        self._manager = mp.Manager()
        self._shared = self._manager.list()
        self._private: list[ClientConnection] = []

    def append(self, client: ClientConnection):
        self._private.append(client)
        self._shared.append(MPClientConnection(client))

    def remove(self, client: ClientConnection):
        self._private.remove(client)
        self._shared.remove(MPClientConnection(client))

    def public_get(self):
        return list(self._shared)

    def __contains__(self, item):
        return item in self._private

    def __len__(self):
        return len(self._private)

    def __iter__(self):
        return iter(self._private)


class TCPServer:
    def __init__(self, host_ip, host_port, ticks_per_second: int = 50):
        self._request_queue = AwaitableQueue(maxsize=10)
        self._broadcast_queue = AwaitableQueue(maxsize=1)
        self._internal_state = mp.Value("i", ServerState.IDLE.value)

        self._clients = ClientList()

        self.ip = host_ip
        self.port = host_port

        self._throttle = 1 / ticks_per_second

        self._loop = None

    def broadcast_data(self, data: str, timeout: float = None):
        self._broadcast_queue.put(data, timeout=timeout)

    def read_request(self, timeout=None) -> tuple[str, DataStream, str]:
        try:
            return self._request_queue.get(timeout=timeout)
        except q.Empty:
            return None

    def get_clients(self) -> list[MPClientConnection]:
        return self._clients.public_get()

    def asyncio_run(self):
        """Process main loop"""
        self._loop = asyncio.get_event_loop()
        self._request_queue.set_loop(self._loop)
        self._broadcast_queue.set_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run())
        except KeyboardInterrupt:
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
            self._loop.run_until_complete(
                asyncio.gather(*asyncio.all_tasks(self._loop), return_exceptions=True)
            )
        except Exception:
            print("\nAsyncio server exception not handled:")
            tb.print_exc()
        finally:
            self._loop.close()

    @property
    def state(self):
        return ServerState(self._internal_state.value)

    @state.setter
    def state(self, state: ServerState):
        if not isinstance(state, ServerState):
            raise ValueError(f"Server state must be of type {ServerState.__name__}")
        elif self.state == ServerState.EXITING:
            return
        with self._internal_state.get_lock():
            self._internal_state.value = state.value

    async def _run(self):
        self._server = await asyncio.start_server(
            self._handle_client, self.ip, self.port
        )
        addr = self._server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        asyncio.create_task(self._broadcaster())
        while self.state != ServerState.EXITING:
            await asyncio.sleep(2)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        addr = writer.get_extra_info("peername")

        client_conn = ClientConnection(
            self._generate_unique_id(addr[0], addr[1])[:6], writer, reader
        )
        self._clients.append(client_conn)
        asyncio.create_task(self._response_processor(client_conn))

        print(f"Connected to {client_conn.id}")

        # Connection loop
        while self.state != ServerState.EXITING:
            try:
                data = await client_conn.network_receive()
            except ConnectionResetError:
                break
            if data is None:
                break

            if self.state == ServerState.LOBBY:
                # Handle message
                await self._request_queue.async_put(
                    (client_conn.id, client_conn.response_pipe, data.decode()),
                    timeout=2,
                )
            elif self.state == ServerState.PLAYING:
                client_conn.client_data_pipe.write(data.decode())

        # Disconnected
        print(f"Client {client_conn.id} disconnected")
        self._clients.remove(client_conn)
        try:
            await client_conn.disconnect()
        except ConnectionResetError:
            pass

    async def _response_processor(self, client_conn: ClientConnection):
        """This asyncio task runs along the server"""
        while self.state != ServerState.EXITING:
            response = await client_conn.read_server_response(1)
            if response is not None:
                try:
                    await client_conn.network_send(response)
                except CONNECTION_EXCEPTION:
                    break

    async def _broadcaster(self):
        """This asyncio task runs along the server"""
        while self.state != ServerState.EXITING:
            message = await self._broadcast_queue.async_get(timeout=1)
            if message is not None:
                try:
                    await asyncio.gather(
                        *[client.network_send(message) for client in self._clients]
                    )
                except CONNECTION_EXCEPTION:
                    break

    def _generate_unique_id(self, ip, port):
        unique_str = f"{ip}:{port}"
        hashed = hashlib.sha256(unique_str.encode()).hexdigest()
        if hashed not in self._clients:
            return hashed
        else:
            print(f"Failed to generate unique id for {unique_str}")
            return self._generate_unique_id(ip, port)


class GameServer:
    def __init__(
        self,
        server_ip,
        server_port,
        request_handler: Callable,
        ticks_per_second: float = 50,
    ):
        self._network_server = TCPServer(server_ip, server_port, ticks_per_second)

        self._process = None
        self._responder_thread = None
        self._req_handler = request_handler

        self._close_timeout = 5

    def start(self):
        self._process = mp.Process(target=self._network_server.asyncio_run)
        self._process.start()

        self._responder_thread = th.Thread(target=self._request_processor)
        self._responder_thread.start()

    def start_lobby(self):
        self._network_server.state = ServerState.LOBBY

    def start_playing(self):
        self.player_pipes = [
            client.client_data_pipe for client in self._network_server.get_clients()
        ]
        self._network_server.state = ServerState.PLAYING

    def gather_player_data(self):
        data = []
        for pipe in self.player_pipes:
            player_data = pipe.read()
            if player_data is not None:
                data.append(player_data)
        return data

    def broadcast_message(self, message):
        try:
            self._network_server.broadcast_data(message, timeout=10)
        except q.Full:
            print(f"[{self.__class__.__name__}] Broadcast queue full!")

    def stop(self):
        self._network_server.state = ServerState.EXITING
        print(f"[{self.__class__.__name__}] Shutting down server...")

        self._stop_process()
        self._responder_thread.join()

    def _stop_process(self):
        timer = Timer()
        while self._process.is_alive():
            if timer.elapsed_sec() > self._close_timeout:
                self._process.terminate()
                print(f"[{self.__class__.__name__}] killed")
                break
            self._process.join(timeout=1)
            if self._process.exitcode is None:
                print(f"[{self.__class__.__name__}] Waiting server shutdown...")
        else:
            print(f"[{self.__class__.__name__}] closed gracefully")
        self._process = None

    @property
    def connected_players(self):
        return set(client.id for client in self._network_server.get_clients())

    def _request_processor(self):
        while self._network_server.state != ServerState.EXITING:
            time.sleep(2)
            while self._network_server.state == ServerState.LOBBY:
                client_request = self._network_server.read_request(timeout=2)
                if client_request is not None:
                    client_id, response_pipe, data = client_request
                    response: str = self._req_handler(client_id, data)
                    success = False
                    while not success:
                        success = response_pipe.write(response, timeout=0.2)
                        if not success:
                            print(
                                f"[{self._request_processor.__name__}] Failed to send response to {client_id}"
                            )
