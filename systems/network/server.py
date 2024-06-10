import asyncio
import hashlib
import multiprocessing as mp
import queue as q
import struct
import time
import traceback as tb
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto

from schemas import (
    JoinLobbyRequest,
    LobbyInfoRequest,
    LobbyInfoResponse,
    ServerResponse,
)
from systems.decoder import MessageDecoder
from systems.network.constants import GAME_PORT
from utils.timer import Timer


class ServerState(Enum):
    IDLE = auto()
    RUNNING = auto()
    EXITING = auto()


# TODO - Follow client design
class TCPServer:
    def __init__(self, host_ip, host_port, ticks_per_second: int = 50):
        self._message_queue = mp.Queue(maxsize=100)
        self._response_queue = mp.Queue(maxsize=1)

        self.ip = host_ip
        self.port = host_port

        self._internal_state = mp.Value("i", ServerState.IDLE.value)
        self._close_timeout = 5
        self._throttle = 1 / ticks_per_second

        self._clients = {}

        self._executor = None
        self._process = None
        self._loop = None

    def send_data(self, data: str, timeout: float = None):
        self._message_queue.put(data, timeout=timeout)

    def read_data(self, timeout: float = None):
        try:
            return self._response_queue.get(timeout=timeout)
        except q.Empty:
            return None

    def asyncio_run(self):
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

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        addr = writer.get_extra_info("peername")
        client_id = self._generate_unique_id(addr[0], addr[1])[:6]
        self._clients[client_id] = {"data": None, "writer": writer}
        print(f"Connected to {client_id}")

        # Connection loop
        while self.state == ServerState.RUNNING:
            try:
                prefix_length = await reader.read(4)
                if prefix_length is not None and len(prefix_length) == 4:
                    message_length = struct.unpack("!I", prefix_length)[0]
                    data = await reader.read(message_length)
            except ConnectionResetError:
                break
            if not prefix_length or not data:
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
        self.state = ServerState.RUNNING
        try:
            while self.state != ServerState.EXITING:
                start_time = asyncio.get_event_loop().time()

                # Perform both operations concurrently to improve efficiency
                client_data_task = asyncio.create_task(
                    self._put_client_data(), name="client_data"
                )
                server_update_task = asyncio.create_task(
                    self._read_server_data(), name="server_update"
                )

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

        self.state = ServerState.RUNNING

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
            *[self._send_data(client_id, message) for client_id in self._clients]
        )

    async def _send_data(self, client_id: str, message: str):
        if client_id not in self._clients:
            print(f"Client id '{client_id}' not found")
            return

        writer: asyncio.StreamWriter = self._clients[client_id]["writer"]
        try:
            data = message.encode()
            length_prefix = struct.pack("!I", len(data))
            writer.write(length_prefix + data)
            await writer.drain()
        except ConnectionResetError:
            print(f"Failed to send message to {client_id}, connection lost")

    def _generate_unique_id(self, ip, port):
        unique_str = f"{ip}:{port}"
        hashed = hashlib.sha256(unique_str.encode()).hexdigest()
        if hashed not in self._clients.keys():
            return hashed
        else:
            print(f"Failed to generate unique id for {unique_str}")
            return self._generate_unique_id(ip, port)

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


class GameServer:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._network_server = TCPServer(server_ip, server_port, ticks_per_second)
        self._process = None

        self._close_timeout = 5

    def start(self):
        self._process = mp.Process(target=self._network_server.asyncio_run)
        self._process.start()

    def stop(self):
        self._network_server.state = ServerState.EXITING
        print(f"[{self.__class__.__name__}] Shutting down server...")

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

    def read_from(self, client_id):
        # NOTE - Game must not wait for client data
        clients_data: dict = self._network_server.read_data()
        return clients_data.get(client_id)

    def read_all(self):
        # NOTE - Game must not wait for client data
        return self._network_server.read_data()

    def send_to(self, client_id, data, timeout: float = None):
        # NOTE - Game must wait for server availability
        self._network_server.send_data({client_id: data}, timeout=timeout)

    def send_all(self, data, timeout: float = None):
        # NOTE - Game must wait for server availability
        self._network_server.send_data({"all": data}, timeout=timeout)


class SnakeServer:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._server = GameServer(server_ip, server_port, ticks_per_second)

        self._decoder = MessageDecoder()

    def start(self):
        self._server.start()

    def stop(self):
        self._server.stop()

    def get_player_requests(self):
        clients_data = self._server.read_all()
        if clients_data:
            print(f"Players data: {clients_data}")
            player_data = {}

            for player_name, player_data in clients_data.items():
                if player_data is None:
                    continue
                player_message = self._decoder.decode_message(player_data)
                if isinstance(player_message, JoinLobbyRequest):
                    print("Joining lobby", player_name)
                    message = ServerResponse(
                        status=0, message="Joined lobby"
                    ).model_dump_json()
                    self._server.send_to(player_name, message)
                elif isinstance(player_message, LobbyInfoRequest):
                    print("Sending lobby info to", player_name)
                    self._server.send_to(
                        player_name,
                        LobbyInfoResponse(
                            status=0,
                            message="Here ya go!",
                            player_names=list(clients_data.keys()),
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
                        ).model_dump_json(),
                    )
                else:
                    print("Message type", type(player_message))

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
            game_server.get_player_requests()
            # print(f"Time elapsed: {round(timer.elapsed_ms(), 1)} ms")
    except KeyboardInterrupt:
        game_server.stop()


if __name__ == "__main__":
    main()
