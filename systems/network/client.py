import asyncio
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

    async def send_message(self, message):
        if self.writer:
            self.writer.write(message.encode())
            try:
                await self.writer.drain()
            except ConnectionResetError:
                self.writer.close()
                return

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


class GameClient:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 10):
        self.connection = TCPClient(server_ip, server_port)
        
        self._message_queue = mp.Queue(maxsize=1)
        self._response_queue = mp.Queue(maxsize=1)

        self._close_timeout = 5
        self._throttle = 1 / ticks_per_second

        self._executor = None
        self._process = None
        self._loop = None

        self._running = False

    def start(self):
        self._process = mp.Process(target=self._main_client_loop)
        self._process.start()

    def stop(self):
        self._running = False

        if self._executor:
            self._executor.shutdown()

        tries = 0
        while self._process.is_alive():
            if tries > 15/self._close_timeout:
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

    def read_from_server(self):
        # NOTE - Game must not wait for client data
        try:
            return self._response_queue.get_nowait()
        except q.Empty:
            return None

    def send_to_server(self, data, timeout: float = None):
        # NOTE - Game must wait for server availability
        self._message_queue.put(data, timeout=timeout)

    def _main_client_loop(self):
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
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
            self._loop.close()

    async def _run(self):
        while not await self.connect():
            await asyncio.sleep(1)
        self._running = True

        try:
            while self._running:
                start_time = asyncio.get_event_loop().time()

                server_data = await self._get_server_data()
                await self._put_server_data(server_data)

                client_data = await self._read_client_data()
                if client_data:
                    await self._send_player_data(client_data)

                end_time = asyncio.get_event_loop().time()
                elapsed_time = end_time - start_time
                sleep_time = max(0, self._throttle - elapsed_time)

                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            pass
        # print("Connection dropped")

    async def _put_server_data(self, server_data):
        try:
            return await self._loop.run_in_executor(
                self._executor,
                self._response_queue.put_nowait,
                server_data
            )
        except q.Full:
            return None
    
    async def _read_client_data(self):
        try:
            return await self._loop.run_in_executor(
                self._executor,
                self._message_queue.get_nowait,
            )
        except q.Empty:
            return None

    async def _get_server_data(self):
        try:
            server_data = await self.connection.receive_message()
            return server_data
        except (
            ConnectionResetError,
            ConnectionAbortedError,
            asyncio.IncompleteReadError,
            BrokenPipeError
        ):
            self._running = False
            return None

    async def _send_player_data(self, player_data):
        try:
            data = json.dumps(player_data)
            await self.connection.send_message(data)
        except (
            ConnectionResetError,
            ConnectionAbortedError,
            asyncio.IncompleteReadError,
            BrokenPipeError
        ):
            self._running = False
            pass

    async def connect(self):
        try:
            await self.connection.connect()
            print(
                f"Connected to server at {self.connection.host}:{self.connection.port}"
            )
            return True
        except ConnectionRefusedError:
            print("Connection refused")
            return False

    async def disconnect(self):
        try:
            await self.connection.disconnect()
        except (ConnectionResetError, ConnectionAbortedError):
            pass
        print("Disconnected from server")


def main():
    game_client = GameClient("127.0.0.1", GAME_PORT)
    game_client.start()

    import random
    directions = ["UP", "LEFT","RIGHT","DOWN"]

    try:
        while True:
            player_data = {"snake_direction": directions[random.randint(0,3)]}
            # game_client.send_to_server(player_data)

            server_data = game_client.read_from_server()
            if server_data == '':
                game_client.stop()
                break
            print(f"Got server data: {server_data}")
            time.sleep(1)
    except KeyboardInterrupt:
        game_client.stop()


if __name__ == "__main__":
    main()
