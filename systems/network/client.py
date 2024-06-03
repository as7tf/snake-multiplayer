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


class GameClient:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self.tcp_conn = TCPClient(server_ip, server_port)
        
        self._message_queue = mp.Queue(maxsize=1)
        self._response_queue = mp.Queue(maxsize=1)
        self._internal_state = mp.Value("i", ClientState.IDLE.value)
        self._server_data = None
        self._close_timeout = 5
        self._closing_limit = 5
        self._throttle = 1 / ticks_per_second

        self._executor = None
        self._process = None
        self._read_server_task = None
        self._loop = None

        self._connection_lost_exception = (
            ConnectionResetError,
            ConnectionAbortedError,
            BrokenPipeError
        )

    def start(self):
        self._process = mp.Process(target=self._asyncio_run)
        self._process.start()

    def stop(self):
        self._client_state = ClientState.EXITING
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
        self._client_state = ClientState.CONNECTING
        while not self.is_running():
            time.sleep(0.1)

    def disconnect(self):
        self._client_state = ClientState.DISCONNECTING

    def read_response(self):
        # NOTE - Game must not wait for server data
        try:
            return self._response_queue.get_nowait()
        except q.Empty:
            return None

    def send_message(self, data, timeout: float = None):
        # NOTE - Game must wait for client availability
        self._message_queue.put(data, timeout=timeout)

    def is_running(self):
        return self._client_state == ClientState.RUNNING


    @property
    def _client_state(self):
        with self._internal_state.get_lock():
            return ClientState(self._internal_state.value)

    @_client_state.setter
    def _client_state(self, state: ClientState):
        if not isinstance(state, ClientState):
            raise ValueError(f"Client state must be of type {ClientState}")
        elif self._client_state == ClientState.EXITING:
            return
        with self._internal_state.get_lock():
            self._internal_state.value = state.value

    def _asyncio_run(self):
        self._executor = ThreadPoolExecutor(max_workers=2)

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
            if self._executor:
                self._executor.shutdown()


    # Client State methods
    async def _run(self):
        try:
            while self._client_state != ClientState.EXITING:
                if self._client_state == ClientState.IDLE:
                    await asyncio.sleep(1)
                elif self._client_state == ClientState.CONNECTING:
                    await self._connection_loop()
                elif self._client_state == ClientState.DISCONNECTING:
                    await self._disconnect_loop()
                elif self._client_state == ClientState.RUNNING:
                    await self._running_loop()
                else:
                    print(f"Current client state is not implemented: {self._client_state}")
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    async def _connection_loop(self):
        if not await self._connect():
            await asyncio.sleep(0.5)
        else:
            asyncio.create_task(self._get_response(), name=f"{self._get_response.__name__}")
            self._client_state = ClientState.RUNNING

    async def _disconnect_loop(self):
        try:
            await self._disconnect()
        except self._connection_lost_exception:
            pass
        self._client_state = ClientState.IDLE

    async def _running_loop(self):
        start_time = asyncio.get_event_loop().time()

        # Perform operations concurrently to improve efficiency
        message_get = asyncio.create_task(self._message_queue_get(), name=f"{self._message_queue_get.__name__}")
        response_put = asyncio.create_task(self._response_queue_put(), name=f"{self._response_queue_put.__name__}")

        done, pending = await asyncio.wait(
            [message_get, response_put],
            return_when=asyncio.ALL_COMPLETED,  # Wait for all tasks to complete
        )

        # Process completed tasks
        try:
            for task in done:
                if task == message_get:
                    client_data = await task
                    if client_data is not None:
                        await self._send_data(client_data)
                elif task == response_put:
                    await task
            for task in pending:
                await task
        except self._connection_lost_exception:
            self._client_state = ClientState.IDLE
            return

        elapsed_time = asyncio.get_event_loop().time() - start_time
        sleep_time = max(0, self._throttle - elapsed_time)
        await asyncio.sleep(sleep_time)


    # Data Queues
    async def _response_queue_put(self):
        if self._server_data is None:
            return
        else:
            data = self._server_data
            self._server_data = None

        try:
            await self._loop.run_in_executor(
                self._executor,
                self._response_queue.put_nowait,
                data
            )
        except q.Full:
            pass

    async def _message_queue_get(self):
        try:
            return await self._loop.run_in_executor(
                self._executor,
                self._message_queue.get_nowait
            )
        except q.Empty:
            return None


    # TCP Communication
    async def _get_response(self):
        while self._client_state != ClientState.EXITING:
            await asyncio.sleep(0.1)
            while self.is_running():
                receive_message_task = asyncio.create_task(
                    self.tcp_conn.receive_message(),
                    name=f"{self.tcp_conn.receive_message.__name__}"
                )

                done, pending = await asyncio.wait(
                    [receive_message_task],
                    return_when=asyncio.FIRST_COMPLETED,  # Wait for all tasks to complete
                )
                try:
                    for task in done.union(pending):
                        server_data = await task
                except self._connection_lost_exception:
                    pass
                if server_data is not None:
                    self._server_data = server_data

    async def _send_data(self, data):
        data = json.dumps(data)
        await self.tcp_conn.send_message(data)

    async def _connect(self):
        try:
            await self.tcp_conn.connect()
            print(
                f"Connected to server at {self.tcp_conn.host}:{self.tcp_conn.port}"
            )
            return True
        except ConnectionRefusedError:
            print("Connection refused")
            return False

    async def _disconnect(self):
        await self.tcp_conn.disconnect()

    def __del__(self):
        if self._process is not None:
            self.stop()


def main():
    try:
        game_client = GameClient("127.0.0.1", GAME_PORT, ticks_per_second=50)
        game_client.start()
        game_client.connect()

        import random
        directions = ["UP", "LEFT","RIGHT","DOWN"]

        client_throttle = 0.02
        write_timeout = 1

        while game_client.is_running():
            # Client tick rate throttle
            time.sleep(client_throttle)

            # Message sending logic
            try:
                player_data = {"snake_direction": directions[random.randint(0,3)]}

                # TODO - Minimize block duration
                # The writing speed is limited by the connection tick rate
                game_client.send_message(player_data, timeout=write_timeout)
            except q.Full:
                print("Write queue full")
                pass

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
