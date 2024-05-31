import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import multiprocessing as mp
import queue as q
import traceback as tb

from systems.network.constants import GAME_PORT


class TCPServer:
    def __init__(self, host_ip, host_port):
        self._write_queue = mp.Queue(maxsize=1)
        self._read_queue = mp.Queue(maxsize=1)

        self.ip = host_ip
        self.port = host_port

        self._close_timeout = 5
        self._server_read_timeout = 1
        self._clients = {}

        self._executor = None
        self._process = None
        self._loop = None

        self._running = False

    def start(self):
        self._process = mp.Process(target=self._main_server_loop)
        self._process.start()

    def stop(self):
        self._running = False

        if self._executor:
            self._executor.shutdown()

        tries = 0
        while self._process.is_alive():
            if tries > 15/self._close_timeout:
                self._process.terminate()
                print("Server killed")
                break
            try:
                self._process.join(timeout=self._close_timeout)
            except TimeoutError:
                print("Waiting server shutdown...")
            tries += 1
        else:
            print("Server closed gracefully")

    def read_from(self, client_id):
        try:
            clients_data: dict = self._read_queue.get(timeout=self._server_read_timeout)
            return clients_data.get(client_id)
        except q.Empty:
            return None

    def read_all(self):
        try:
            return self._read_queue.get(timeout=self._server_read_timeout)
        except q.Empty:
            return None

    def send_to(self, client_id, data):
        self._write_queue.put({client_id: data})

    def send_all(self, data):
        self._write_queue.put({"all": data})

    def _main_server_loop(self):
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
        await self._start()
        try:
            while self._running:
                # TODO - Throttle this
                await self._put_client_data()
                await self._handle_write_queue()
        except asyncio.CancelledError:
            pass

    async def _start(self):
        self._server = await asyncio.start_server(
            self._handle_client, self.ip, self.port
        )
        addr = self._server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        self._running = True

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        addr = writer.get_extra_info("peername")
        client_id = self._generate_unique_id(addr[0], addr[1])[:6]
        self._clients[client_id] = {"data": None, "writer": writer}
        print(f"Connected to {client_id}")

        # Connection loop
        while True:
            try:
                data = await reader.read(100)
            except ConnectionResetError:
                break
            if not data:
                break
            self._clients[client_id]["data"] = data.decode()

        # Disconnected
        print(f"Client {client_id} disconnected")
        del self._clients[client_id]
        writer.close()
        await writer.wait_closed()

    async def _handle_write_queue(self):
        update: dict = await self._read_server_data()
        if not update:
            return
        elif "all" in update:
            await self._broadcast_data(update["all"])
        else:
            client_id, message = next(iter(update.items()))
            await self._send_data(client_id, message)

    async def _broadcast_data(self, message):
        await asyncio.gather(
            *[self._send_data(client_id, message)for client_id in self._clients]
        )

    async def _send_data(self, client_id: str, message: str):
        if client_id not in self._clients:
            print(f"Client id '{client_id}' not found")
            return

        writer: asyncio.StreamWriter = self._clients[client_id]["writer"]
        try:
            # TODO - Add a separator between messages
            writer.write(json.dumps(message).encode())
            await writer.drain()
        except ConnectionResetError:
            print(f"Failed to send message to {client_id}, connection lost")

    def _generate_unique_id(self, ip, port):
        unique_str = f"{ip}:{port}"
        hashed = hashlib.sha256(unique_str.encode()).hexdigest()
        return hashed

    async def _read_server_data(self):
        try:
            return await self._loop.run_in_executor(
                self._executor,
                self._write_queue.get,
                False,
                # self._server_read_timeout
            )
        except q.Empty:
            return None
    
    async def _put_client_data(self):        
        client_data = {
            client_id: self._clients[client_id]["data"]
            for client_id in self._clients
        }

        try:
            await self._loop.run_in_executor(
                self._executor,
                self._read_queue.put,
                client_data,
                False,
                # self._server_read_timeout
            )
        except q.Full:
            pass


def main():
    game_server = TCPServer("127.0.0.1", GAME_PORT)
    game_server.start()

    import random

    try:
        while True:
            clients_data = game_server.read_all()
            print(f"Players data: {clients_data}")

            game_update = random.randint(0, 100)
            game_server.send_all(game_update)
            # time.sleep(10)
    except KeyboardInterrupt:
        game_server.stop()


if __name__ == "__main__":
    main()
