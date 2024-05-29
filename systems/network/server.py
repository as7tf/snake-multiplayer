import asyncio
import hashlib
import json

from constants import GAME_PORT


class GameServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = None

        self.clients = {}

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        addr = self.server.sockets[0].getsockname()
        print(f"Serving on {addr}")

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        addr = writer.get_extra_info("peername")

        client_id = self._generate_unique_id(addr[0], addr[1])[:6]
        self.clients[client_id] = {
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
            self.clients[client_id]["player_data"].update(player_data)
        print(f"Player {client_id} disconnected")
        writer.close()
        del self.clients[client_id]

    async def broadcast_update(self, update_data):
        message = json.dumps(update_data)
        print(f"Broadcasting: {message}")
        message = message.encode()

        await asyncio.gather(
            *[
                self._send_message(client["writer"], message, client_id)
                for client_id, client in self.clients.items()
            ]
        )

    def get_players_data(self):
        return {
            client_id: client["player_data"]
            for client_id, client in self.clients.items()
        }

    async def _send_message(self, writer, message, client_id: str):
        try:
            writer.write(message)
            await writer.drain()
        except ConnectionResetError:
            print(f"Failed to send message to {client_id}, connection lost")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("Server stopped")

    def _generate_unique_id(self, ip, port):
        unique_str = f"{ip}:{port}"
        hashed = hashlib.sha256(unique_str.encode()).hexdigest()
        return hashed


async def main():
    game_server = GameServer("127.0.0.1", GAME_PORT)
    await game_server.start()

    import random

    try:
        while True:
            players_data = game_server.get_players_data()
            print(f"Players data: {players_data}")
            server_update = random.randint(0, 100)
            await asyncio.sleep(0.2)
            await game_server.broadcast_update(server_update)
    except asyncio.CancelledError:
        print("CancelledError")
        pass
    finally:
        await game_server.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.run_until_complete(
            asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True)
        )
    finally:
        loop.close()
        print("Loop closed")
