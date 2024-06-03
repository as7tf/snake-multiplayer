import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import multiprocessing as mp
import queue as q
import time
import traceback as tb

from systems.network.constants import GAME_PORT

from utils.timer import Timer


# TODO - Follow client design
class TCPServer:
    def __init__(self, host_ip, host_port, ticks_per_second: int = 50):
        self._message_queue = mp.Queue(maxsize=100)
        self._response_queue = mp.Queue(maxsize=1)

        self.ip = host_ip
        self.port = host_port

        self._close_timeout = 5
        self._throttle = 1 / ticks_per_second

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
        # NOTE - Game must not wait for client data
        try:
            clients_data: dict = self._response_queue.get_nowait()
            return clients_data.get(client_id)
        except q.Empty:
            return None

    def read_all(self):
        # NOTE - Game must not wait for client data
        try:
            return self._response_queue.get_nowait()
        except q.Empty:
            return None

    def send_to(self, client_id, data, timeout: float = None):
        # NOTE - Game must wait for server availability
        self._message_queue.put({client_id: data}, timeout=timeout)

    def send_all(self, data, timeout: float = None):
        # NOTE - Game must wait for server availability
        self._message_queue.put({"all": data}, timeout=timeout)

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
        try:
            writer.close()
            await writer.wait_closed()
        except ConnectionResetError:
            pass

    async def _run(self):
        await self._start_server()
        try:
            while self._running:
                start_time = asyncio.get_event_loop().time()

                # Perform both operations concurrently to improve efficiency
                client_data_task = asyncio.create_task(self._put_client_data(), name="client_data")
                server_update_task = asyncio.create_task(self._read_server_data(), name="server_update")

                done, pending = await asyncio.wait(
                    [client_data_task, server_update_task],
                    return_when=asyncio.ALL_COMPLETED,  # Wait for all tasks to complete
                )

                # Process completed tasks
                for task in done:
                    if task == client_data_task:
                        await task  # Ensure any exceptions are raised
                    elif task == server_update_task:
                        server_updates = await task
                        await self._send_server_updates(server_updates)
                for task in pending:
                    await task

                end_time = asyncio.get_event_loop().time()
                elapsed_time = end_time - start_time
                sleep_time = max(0, self._throttle - elapsed_time)

                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            pass

    async def _start_server(self):
        self._server = await asyncio.start_server(
            self._handle_client, self.ip, self.port
        )
        addr = self._server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        self._running = True

    async def _send_server_updates(self, server_updates):
        # TODO - Optimize same message sending
        # TODO - Optimize sending multiple messages to the same client
        for update in server_updates:
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
            message = str(message)
            writer.write(message.encode())
            await writer.drain()
        except ConnectionResetError:
            print(f"Failed to send message to {client_id}, connection lost")

    def _generate_unique_id(self, ip, port):
        unique_str = f"{ip}:{port}"
        hashed = hashlib.sha256(unique_str.encode()).hexdigest()
        return hashed

    async def _read_server_data(self):
        def get_all_queue(queue: mp.Queue):
            data = []
            while not queue.empty():
                data.append(queue.get_nowait())
            data.reverse()
            return data

        return await self._loop.run_in_executor(
            self._executor,
            get_all_queue,
            self._message_queue,
        )

    async def _put_client_data(self):
        client_data = {}
        for client_id in self._clients:
            client_data[client_id] = self._clients[client_id]["data"]
            self._clients[client_id]["data"] = None

        try:
            await self._loop.run_in_executor(
                self._executor,
                self._response_queue.put_nowait,
                client_data,
            )
        except q.Full:
            pass


def main():
    game_server = TCPServer("127.0.0.1", GAME_PORT, ticks_per_second=50)
    game_server.start()
    timer = Timer()

    import random

    server_throttle = 0.01
    try:
        # TODO - Add a separator between messages
        while True:
            time.sleep(server_throttle)
            timer.reset()
            clients_data = game_server.read_all()
            if clients_data:
                print(f"Players data: {clients_data}")

                game_update = random.randint(0, 100)
                game_server.send_all(game_update)
            # print(f"Time elapsed: {round(timer.elapsed_ms(), 1)} ms")
    except KeyboardInterrupt:
        game_server.stop()


if __name__ == "__main__":
    main()
