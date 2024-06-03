import asyncio
from enum import Enum, auto
import json
import multiprocessing as mp
import queue as q
import time
import traceback as tb
from concurrent.futures import ThreadPoolExecutor

from systems.network.constants import GAME_PORT


class TCPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def send_message(self, message: str):
        if self.writer:
            self.writer.write(message.encode())
            await self.writer.drain()

    async def receive_message(self):
        if self.reader:
            data = await self.reader.read(100)

            if data is None:
                return None
            message = data.decode()
            return message

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()


class ClientState(Enum):
    IDLE = auto()
    CONNECTING = auto()
    RUNNING = auto()
    DISCONNECTING = auto()
    EXITING = auto()


class _NetworkClient:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._tcp_conn = TCPClient(server_ip, server_port)

        self._message_queue = mp.Queue(maxsize=1)
        self._response_queue = mp.Queue(maxsize=1)
        self._internal_state = mp.Value("i", ClientState.IDLE.value)
        self._server_data = None
        self._throttle = 1 / ticks_per_second

        self._process = None
        self._read_server_task = None
        self._loop = None

        self._connection_lost_exception = (
            ConnectionResetError,
            ConnectionAbortedError,
            BrokenPipeError
        )        

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
            tb.print_exc()
        finally:
            print("Asyncio client closed")
            self._loop.close()

    def read_response_queue(self):
        try:
            return self._response_queue.get_nowait()
        except q.Empty:
            return None

    def push_message_queue(self, data: str) -> bool:
        try:
            self._message_queue.put_nowait(data)
            return True
        except q.Full:
            return False

    def is_running(self):
        return self.state == ClientState.RUNNING

    @property
    def state(self):
        return ClientState(self._internal_state.value)

    @state.setter
    def state(self, state: ClientState):
        if not isinstance(state, ClientState):
            raise ValueError(f"Client state must be of type {ClientState}")
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
            print(
                f"Connected to server at {self._tcp_conn.host}:{self._tcp_conn.port}"
            )
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
        except self._connection_lost_exception:
            pass
        self.state = ClientState.IDLE


    # Client operation methods
    async def _get_response(self):
        while self.state != ClientState.EXITING:
            await asyncio.sleep(self._throttle)
            while self.is_running():
                start_time = asyncio.get_event_loop().time()

                server_data = None
                try:
                    server_data = await asyncio.wait_for(self._tcp_conn.receive_message(), None)
                    self._response_queue.put_nowait(server_data)
                except q.Full:
                    # TODO - Add a patience to server data age
                    pass
                except self._connection_lost_exception:
                    print("Connection lost")
                    self.state = ClientState.IDLE

                elapsed_time = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, self._throttle - elapsed_time)
                await asyncio.sleep(sleep_time)

    async def _send_data(self):
        while self.state != ClientState.EXITING:
            await asyncio.sleep(self._throttle)
            while self.is_running():
                start_time = asyncio.get_event_loop().time()

                try:
                    data = self._message_queue.get_nowait()
                    data = json.dumps(data)
                    await asyncio.wait_for(self._tcp_conn.send_message(data), None)
                except q.Empty:
                    pass
                except self._connection_lost_exception:
                    pass

                elapsed_time = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, self._throttle - elapsed_time)
                await asyncio.sleep(sleep_time)


class ClientControl:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._network_client = _NetworkClient(server_ip, server_port, ticks_per_second)
        self._process = None

        self._close_timeout = 5
        self._closing_limit = 5

    def start(self):
        self._process = mp.Process(target=self._network_client.asyncio_run)
        self._process.start()

    def stop(self):
        self._network_client.state = ClientState.EXITING
        print("Shutting down client...")

        tries = 0
        while self._process.is_alive():
            if tries > self._closing_limit/self._close_timeout:
                self._process.terminate()
                print("Client killed")
                break
            try:
                self._process.join(timeout=self._close_timeout)
            except TimeoutError:
                print("Waiting client shutdown...")
            tries += 1
        else:
            print("Client closed gracefully")
        self._process = None

    def connect(self):
        self._network_client.state = ClientState.CONNECTING
        while not self.is_running():
            time.sleep(0.1)

    def disconnect(self):
        self._network_client.state = ClientState.DISCONNECTING

    def is_running(self):
        return self._network_client.is_running()

    def read_response(self) -> str:
        """
        Reads the response from the server.

        Returns:
            str or None: The response from the server, or None if the queue is empty.
        """
        return self._network_client.read_response_queue()

    def send_message(self, data: str) -> bool:
        """
        Sends a message to the server.

        Args:
            data (str): The message to be sent.

        Returns:
            bool: True if the message was successfully enqueued, False otherwise.
        """
        return self._network_client.push_message_queue(data)

    def __del__(self):
        if self._process is not None:
            self.stop()


def main():
    try:
        game_client = ClientControl("127.0.0.1", GAME_PORT, ticks_per_second=50)
        game_client.start()
        game_client.connect()

        import random
        directions = ["UP", "LEFT","RIGHT","DOWN"]

        client_throttle = 0.02

        while game_client.is_running():
            # Client tick rate throttle
            time.sleep(client_throttle)

            # Message sending logic
            player_data = {"snake_direction": directions[random.randint(0,3)]}

            # The writing speed is limited by the connection tick rate
            success = game_client.send_message(player_data)

            # Response reading logic
            server_data = game_client.read_response()
            if server_data == '':
                print("Server disconnected")
                break
            elif server_data is None:
                continue
            else:
                print(f"Got server data: {server_data}")
    except KeyboardInterrupt:
        pass
    game_client.stop()


if __name__ == "__main__":
    main()
