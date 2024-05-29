import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import multiprocessing as mp
import queue as q
import time

from systems.network.constants import GAME_PORT


class ServerProcess:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self._server = None
        self._server_process = None
        self._loop = None
        self._executor = None
        self.running = False

        self._clients = {}

    #
    #  Non-Async methods
    #

    def start(
        self,
        command_q: mp.Queue,
        clients_data: mp.Queue,
        game_updates: mp.Queue
    ):
        self.running = True
        self._server_process = mp.Process(target=self._main_server_loop, args=(command_q, clients_data, game_updates))
        self._server_process.start()

    def stop(self):
        self.running = False

    def wait_shutdown(self, timeout: float):
        self._server_process.join(timeout)

    #
    #  Private methods
    #

    def _main_server_loop(
        self,
        command_q: mp.Queue,
        clients_data: mp.Queue,
        game_updates: mp.Queue
    ):
        self._loop = asyncio.get_event_loop()
        try:
            self._loop.run_until_complete(self._run(command_q, clients_data, game_updates))
        except KeyboardInterrupt:
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
            self._loop.run_until_complete(
                asyncio.gather(*asyncio.all_tasks(self._loop), return_exceptions=True)
            )
        finally:
            self._loop.close()

    #
    #  Internal server functions
    #

    async def _run(
        self,
        command_q: mp.Queue,
        clients_data: mp.Queue,
        game_updates: mp.Queue
    ):
        await self._start()
        
        try:
            command = None
            while self.running:
                players_data = self._get_players_data()
                clients_data.put(players_data)

                server_update = await self._async_get(game_updates)
                await self._broadcast_update(server_update)
        except asyncio.CancelledError:
            pass
        finally:
            await self._stop()

    async def _start(self):
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        addr = self._server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        self._executor = ThreadPoolExecutor(max_workers=1)

    async def _stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._executor.shutdown()
        print("Server closed")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        addr = writer.get_extra_info("peername")

        client_id = self._generate_unique_id(addr[0], addr[1])[:6]
        self._clients[client_id] = {
            "player_id": client_id,
            "writer": writer,
            "player_data": {},
        }
        print(f"Connected to {client_id}")

        while True:
            try:
                data = await reader.read(100)
            except ConnectionResetError:
                break
            if not data:
                break
            player_data = json.loads(data.decode())
            self._clients[client_id]["player_data"].update(player_data)
        print(f"Player {client_id} disconnected")
        writer.close()
        del self._clients[client_id]

    async def _broadcast_update(self, update_data):
        message = json.dumps(update_data)
        message = message.encode()

        await asyncio.gather(
            *[
                self._send_message(client["writer"], message, client_id)
                for client_id, client in self._clients.items()
            ]
        )

    def _get_players_data(self):
        return {
            client_id: client["player_data"]
            for client_id, client in self._clients.items()
        }

    async def _send_message(self, writer, message, client_id: str):
        try:
            writer.write(message)
            await writer.drain()
        except ConnectionResetError:
            print(f"Failed to send message to {client_id}, connection lost")

    def _generate_unique_id(self, ip, port):
        unique_str = f"{ip}:{port}"
        hashed = hashlib.sha256(unique_str.encode()).hexdigest()
        return hashed

    async def _async_get(self, queue: mp.Queue):
        try:
            return await self._loop.run_in_executor(self._executor, queue.get, True, 2)
        except q.Empty:
            return None

    async def _async_put(self, queue: mp.Queue, item):
        try:
            await self._loop.run_in_executor(self._executor, queue.put, item, True, 2)
        except q.Empty:
            pass


def main():
    command_q = mp.Queue()
    clients_data_q = mp.Queue()
    game_updates_q = mp.Queue()

    game_server = ServerProcess("127.0.0.1", GAME_PORT)
    game_server.start(command_q, clients_data_q, game_updates_q)

    import random

    try:
        while game_server._server_process.is_alive():
            client_data = clients_data_q.get()
            print(f"Players data: {client_data}")

            game_update = random.randint(0, 100)
            print(f"Game update: {game_update}")
            game_updates_q.put(game_update)
            time.sleep(0.5)
    except KeyboardInterrupt:
        game_server.stop()
        timeout = 5  # in seconds
        print("Server closing...")
        while game_server._server_process.is_alive():
            try:
                game_server.wait_shutdown(timeout)
            except TimeoutError:
                print("Waiting server shutdown...")
                pass


if __name__ == "__main__":
    main()
