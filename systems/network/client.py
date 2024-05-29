import asyncio
import time
import json

from constants import GAME_PORT


class Timer:
    def __init__(self):
        self._time = time.time_ns()

    def reset(self):
        self._time = time.time_ns()

    def elapsed_ms(self):
        ret = time.time_ns() - self._time
        ret = ret / 10e5
        return ret


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
    def __init__(self, server_ip, server_port):
        self.connection = TCPClient(server_ip, server_port)

    async def get_server_data(self):
        try:
            server_data = await self.connection.receive_message()
            return server_data
        except (
            ConnectionResetError,
            ConnectionAbortedError,
            asyncio.IncompleteReadError,
        ):
            print("Connection lost")
            return None

    async def send_player_data(self, player_data):
        data = json.dumps(player_data)
        await self.connection.send_message(data)

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


async def main():
    game_client = GameClient("127.0.0.1", GAME_PORT)
    connected = await game_client.connect()

    import random

    while connected:
        player_data = {"x": random.randint(0, 100), "y": random.randint(0, 100)}
        await game_client.send_player_data(player_data)

        server_data = await game_client.get_server_data()
        if server_data is None:
            await game_client.disconnect()
            break
        elif server_data == "":
            print("Server shutdown")
            await game_client.disconnect()
            break
        print(f"Got server data: {server_data}")
        await asyncio.sleep(0.2)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
