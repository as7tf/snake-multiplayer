import asyncio
import multiprocessing as mp
import struct
import time
import traceback as tb
from enum import Enum, auto

from systems.network.constants import CONNECTION_EXCEPTION
from systems.network.data_stream import DataStream
from utils.timer import Timer  # , print_async_func_time, print_func_time


class ClientState(Enum):
    IDLE = auto()
    CONNECTING = auto()
    RUNNING = auto()
    DISCONNECTING = auto()
    EXITING = auto()


class _TCPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def send_message(self, message: bytes):
        self.writer.write(message)
        await self.writer.drain()

    async def receive_message(self, num_bytes: int = 1024):
        return await self.reader.read(num_bytes)

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()


class _NetworkClient:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._tcp_conn = _TCPClient(server_ip, server_port)

        self._message_stream = DataStream()
        self._response_stream = DataStream()

        self._internal_state = mp.Value("i", ClientState.IDLE.value)
        self._server_data = None
        self._throttle = 1 / ticks_per_second

        self._process = None
        self._read_server_task = None
        self._loop = None

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
        except Exception:
            tb.print_exc()
        finally:
            print("Asyncio client closed")
            self._loop.close()

    def read_response_stream(self, timeout: float = 0):
        return self._response_stream.read(timeout)

    def write_message_stream(self, data: str, timeout: float = 0) -> bool:
        return self._message_stream.write(data, timeout)

    def is_running(self):
        return self.state == ClientState.RUNNING

    @property
    def state(self):
        return ClientState(self._internal_state.value)

    @state.setter
    def state(self, state: ClientState):
        if not isinstance(state, ClientState):
            raise ValueError(f"Client state must be of type {ClientState.__name__}")
        elif self.state == ClientState.EXITING:
            return
        with self._internal_state.get_lock():
            self._internal_state.value = state.value

    # Client State methods
    async def _run(self):
        asyncio.create_task(self._get_response(), name=f"{self._get_response.__name__}")
        asyncio.create_task(self._send_data(), name=f"{self._send_data.__name__}")

        try:
            while self.state != ClientState.EXITING:
                if self.state in (ClientState.IDLE, ClientState.RUNNING):
                    await asyncio.sleep(self._throttle)
                elif self.state == ClientState.CONNECTING:
                    await self._connection_loop()
                elif self.state == ClientState.DISCONNECTING:
                    await self._disconnect_loop()
                else:
                    print(f"Current client state is not implemented: {self.state}")
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    async def _connection_loop(self):
        try:
            await self._tcp_conn.connect()
            print(f"Connected to server at {self._tcp_conn.host}:{self._tcp_conn.port}")
            connected = True
        except ConnectionRefusedError:
            print("Connection refused")
            connected = False
            await asyncio.sleep(0.1)

        if connected:
            self.state = ClientState.RUNNING

    async def _disconnect_loop(self):
        try:
            await self._tcp_conn.disconnect()
        except CONNECTION_EXCEPTION:
            pass
        self.state = ClientState.IDLE

    # Data operation methods
    async def _get_response(self):
        while self.state != ClientState.EXITING:
            await asyncio.sleep(self._throttle)
            while self.is_running():
                server_data = None
                try:
                    # TODO - Add a patience to server data age
                    prefix_length = await asyncio.wait_for(
                        self._tcp_conn.receive_message(4), None
                    )
                    if prefix_length is not None and len(prefix_length) == 4:
                        message_length = struct.unpack("!I", prefix_length)[0]
                        server_data = await asyncio.wait_for(
                            self._tcp_conn.receive_message(message_length), None
                        )

                        server_data = server_data.decode()
                        self._response_stream.write(server_data)
                except CONNECTION_EXCEPTION:
                    print("Connection lost")
                    self.state = ClientState.IDLE

    async def _send_data(self):
        while self.state != ClientState.EXITING:
            await asyncio.sleep(self._throttle)
            while self.is_running():
                try:
                    data = await self._loop.run_in_executor(
                        None, self._message_stream.read, 1
                    )
                    if data is not None:
                        data = data.encode("utf-8")

                        # Create the length prefix
                        message_length = len(data)
                        length_prefix = struct.pack("!I", message_length)
                        data = length_prefix + data

                        await asyncio.wait_for(self._tcp_conn.send_message(data), None)
                except CONNECTION_EXCEPTION:
                    pass


class GameClient:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._network_client = _NetworkClient(server_ip, server_port, ticks_per_second)
        self._process = None

        self._close_timeout = 5

    def start(self):
        self._process = mp.Process(target=self._network_client.asyncio_run)
        self._process.start()

    def stop(self):
        self._network_client.state = ClientState.EXITING
        print(f"[{self.__class__.__name__}] Shutting down client...")

        timer = Timer()
        while self._process.is_alive():
            if timer.elapsed_sec() > self._close_timeout:
                self._process.terminate()
                print(f"[{self.__class__.__name__}] Client killed")
                break
            self._process.join(timeout=1)
            if self._process.exitcode is None:
                print(f"[{self.__class__.__name__}] Waiting client shutdown...")
        else:
            print(f"[{self.__class__.__name__}] Client closed gracefully")
        self._process = None

    def connect(self, timeout_sec: float = 1):
        self._network_client.state = ClientState.CONNECTING
        timer = Timer()
        while not self.is_running():
            if timer.elapsed_sec() > timeout_sec:
                self.disconnect()
                return False
            time.sleep(0.1)
        else:
            return True

    def disconnect(self):
        self._network_client.state = ClientState.DISCONNECTING

    def is_running(self):
        return self._network_client.is_running()

    def read_response(self, timeout: float = 0) -> str:
        """
        Reads the response from the server.

        Returns:
            str or None: The response from the server, or None if the stream is empty.
        """
        data = self._network_client.read_response_stream(timeout)
        return data

    def send_message(self, data: str, timeout: float = 0) -> bool:
        """
        Sends a message to the server.

        Args:
            data (str): The message to be sent.

        Returns:
            bool: True if the message was successfully sent, False otherwise.
        """
        if not isinstance(data, str):
            return False
        success = self._network_client.write_message_stream(data, timeout)
        return success

    def __del__(self):
        if self._process is not None:
            self.stop()
