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

from schemas import (
    JoinLobbyRequest,
    LobbyInfoRequest,
    LobbyInfoResponse,
    ServerResponse,
)
from systems.decoder import MessageDecoder
from systems.network.constants import GAME_PORT
from systems.network.data_stream import DataStream
from utils.timer import Timer


class ServerState(Enum):
    IDLE = auto()
    LOBBY = auto()
    PLAYING = auto()
    EXITING = auto()


class AwaitableQueue:
    pass


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
            print(f"Failed to receive message from {self.id}")
            return None

    def read_server_response(self):
        return self.response_pipe.read()

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


class ClientList:
    def __init__(self):
        self._manager = mp.Manager()
        self._shared_clients = self._manager.list()
        self._clients: list[ClientConnection] = []

    def append(self, client: ClientConnection):
        self._clients.append(client)
        self._shared_clients.append(client.id)

    def remove(self, client: ClientConnection):
        self._clients.remove(client)
        self._shared_clients.remove(client.id)

    def public_get(self):
        return [client_id for client_id in self._shared_clients]

    def __contains__(self, item):
        return item in self._clients

    def __len__(self):
        return len(self._clients)

    def __iter__(self):
        return iter(self._clients)


class TCPServer:
    def __init__(self, host_ip, host_port, ticks_per_second: int = 50):
        self._request_queue = mp.Queue(maxsize=10)
        self._broadcast_queue = mp.Queue(maxsize=10)
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

    def get_clients(self):
        return self._clients.public_get()

    def asyncio_run(self):
        self._loop = asyncio.get_event_loop()
        try:
            self._loop.run_until_complete(self._run())
        except KeyboardInterrupt:
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
            self._loop.run_until_complete(
                asyncio.gather(*asyncio.all_tasks(self._loop), return_exceptions=True)
            )
        except:
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
                self._request_queue.put(
                    (client_conn.id, client_conn.response_pipe, data.decode())
                )
            elif self.state == ServerState.PLAYING:
                # TODO - Use shared DataStream for player updates
                pass
            asyncio.create_task(self._response_processor(client_conn))

        # Disconnected
        print(f"Client {client_conn.id} disconnected")
        self._clients.remove(client_conn)
        try:
            await client_conn.disconnect()
        except ConnectionResetError:
            pass

    async def _response_processor(self, client_conn: ClientConnection):
        while self.state == ServerState.LOBBY:
            response = client_conn.read_server_response()
            if response is not None:
                await client_conn.network_send(response)
                break
            await asyncio.sleep(0.01)

    async def _broadcaster(self, message):
        while self.state != ServerState.EXITING:
            if not self._broadcast_queue.empty():
                message = self._broadcast_queue.get_nowait()
                await asyncio.gather(
                    *[client.network_send(message) for client in self._clients]
                )
            await asyncio.sleep(0.01)

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

    # TODO - Create a method to handle player updates concurrently
    def start_lobby(self):
        self._network_server.state = ServerState.LOBBY

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
        return self._network_server.get_clients()

    def _request_processor(self):
        while self._network_server.state != ServerState.EXITING:
            time.sleep(1)
            while self._network_server.state == ServerState.LOBBY:
                client_request = self._network_server.read_request(timeout=0.1)
                if client_request is not None:
                    client_id, response_pipe, data = client_request
                    response: str = self._req_handler(client_id, data)
                    success = False
                    while not success:
                        success = response_pipe.write(response, timeout=0.1)
                        if not success:
                            print(
                                f"[{self._request_processor.__name__}] Failed to send response to {client_id}"
                            )


class SnakeServer:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._server = GameServer(
            server_ip, server_port, self.request_responder, ticks_per_second
        )

        self._decoder = MessageDecoder()
        self.joined_players = set()

    def start(self):
        self._server.start()
        self._server.start_lobby()

    def stop(self):
        self._server.stop()

    @property
    def connected_players(self):
        return self._server.connected_players

    def request_responder(self, client_id, request: str):
        if client_id not in self.joined_players:
            self.joined_players.add(client_id)

        player_message = self._decoder.decode_message(request)
        print(f"Got {player_message.__class__.__name__} from {client_id}")
        if isinstance(player_message, JoinLobbyRequest):
            print("Player joining lobby:", client_id)
            self.joined_players.add(client_id)
            message = ServerResponse(status=0, message="Joined lobby").model_dump_json()
            return message
        elif isinstance(player_message, LobbyInfoRequest):
            print("Sending lobby info to", client_id)
            return LobbyInfoResponse(
                status=0,
                message="Here ya go!",
                player_names=list(self.joined_players),
                highscores=[
                    "10",
                    "9",
                    "8",
                    "7",
                    "6",
                    "5",
                    "4",
                    "3",
                    "2",
                    "1",
                ],
                available_colors=[
                    "red",
                    "blue",
                    "green",
                    "yellow",
                    "purple",
                ],
            ).model_dump_json()

        else:
            print("Message type", type(player_message))
            return ServerResponse(status=1, message="Invalid message").model_dump_json()


def main():
    game_server = SnakeServer("127.0.0.1", GAME_PORT, ticks_per_second=50)
    game_server.start()
    timer = Timer()

    server_throttle = 0.01
    try:
        # TODO - Add a separator between messages
        while True:
            time.sleep(server_throttle)
            timer.reset()
            # print(f"Time elapsed: {round(timer.elapsed_ms(), 1)} ms")
    except KeyboardInterrupt:
        game_server.stop()


if __name__ == "__main__":
    main()
