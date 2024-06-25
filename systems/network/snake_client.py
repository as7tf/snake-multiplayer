import time

from pydantic import BaseModel

from schemas.entities import EntitiesMessage, EntityMessage
from schemas.game import GameReady, PlayerCommand
from schemas.lobby import JoinLobbyRequest, LobbyInfoRequest, LobbyInfoResponse
from schemas.response import ServerResponse
from systems.decoder import MessageDecoder
from systems.network.client import GameClient
from systems.network.constants import GAME_PORT
from utils.timer import Timer  # , print_async_func_time, print_func_time


class SnakeClient:
    def __init__(self, game, connection_timeout_sec: float = 5):
        self._client = None
        self._conn_timeout = connection_timeout_sec
        self._get_game_state = lambda: game.state
        self._decoder = MessageDecoder()

    # @print_func_time
    def _get_server_message(self, timeout: float = 0) -> ServerResponse:
        # NOTE - This is the only method to get data from the server
        # Possible outcomes:
        #    1. Data received
        #    2. No data received
        #    3. Error raised

        server_message = self._client.read_response(timeout)
        if server_message == "":
            print("Server disconnected")
            self.disconnect_from_server()
            return None
        elif server_message is None:
            return None
        else:
            return self._decoder.decode_message(server_message)

    def _send_client_message(self, message: BaseModel, timeout: float = 0) -> None:
        # NOTE - This is the only method to send data to the server
        # Possible outcomes:
        #    1. Data sent
        #    2. Error raised

        self._client.send_message(message.model_dump_json(), timeout)

    def _request(
        self, request: BaseModel, response_schema: ServerResponse, timeout: float = 0
    ) -> ServerResponse:
        self._send_client_message(request)
        response = self._get_server_message(timeout)

        if response is not None:
            if not isinstance(response, response_schema):
                print(f"Unexpected server message: {response}")
                return None
        else:
            print("Request timed out")
        return response

    # Game connection
    def disconnect_from_server(self) -> None:
        if self._client:
            self._client.disconnect()
            timer = Timer()
            while timer.elapsed_sec() < self._conn_timeout:
                if not self._client.is_running():
                    break
                time.sleep(0.1)

            self._client.stop()

    def connect_to_server(self, server_ip, server_port) -> bool:
        self._client = GameClient(server_ip, server_port)
        self._client.start()
        if self._client.connect(self._conn_timeout):
            return True
        else:
            return False

    def try_lobby_join(self, player_name: str) -> bool:
        join_request = JoinLobbyRequest(player_name=player_name)
        response = self._request(join_request, ServerResponse, timeout=1)

        if response is None:
            return False
        elif response.status == 0:
            return True
        else:
            print("Error joining lobby: ", response.message)
            return False

    # Game lobby
    def get_lobby_info(self):
        # NOTE - This should be ran periodically to update lobby info
        # Get available colors
        # Get other players' info
        # Get highscores
        # etc.

        lobby_info_req = LobbyInfoRequest()
        lobby_message: LobbyInfoResponse = self._request(
            lobby_info_req, LobbyInfoResponse, timeout=2
        )
        return lobby_message

    def choose_color(self, color: str) -> bool:
        # NOTE - Test in server if the color is available
        pass

    def set_ready(self, ready: bool) -> bool:
        pass

    def wait_game_start(self) -> bool:
        server_message = self._get_server_message(timeout=2)
        if isinstance(server_message, GameReady):
            return True
        return False

    # Play loop
    def get_server_update(self) -> list[EntityMessage]:
        server_message = self._get_server_message(timeout=0.1)
        if isinstance(server_message, EntitiesMessage):
            return server_message.entities
        return None

    def send_player_command(self, player_name, command: dict) -> None:
        self._send_client_message(
            PlayerCommand(player_name=player_name, command=command)
        )

    def _deserialize_entities(self, entities_message: EntitiesMessage) -> list:
        # TODO - Deserialize entities
        deserialized_entities = []
        for entity in entities_message.entities:
            deserialized_entities.append(entity)
        return deserialized_entities


def main():
    try:
        game_client = GameClient("127.0.0.1", GAME_PORT, ticks_per_second=50)
        game_client.start()
        connected = game_client.connect(5)
        if not connected:
            print("Could not connect to server")
            return

        import random

        directions = ["UP", "LEFT", "RIGHT", "DOWN"]

        client_throttle = 0.02

        while game_client.is_running():
            # Client tick rate throttle
            time.sleep(client_throttle)

            # Message sending logic
            player_data = {"snake_direction": directions[random.randint(0, 3)]}

            # The writing speed is limited by the connection tick rate
            _ = game_client.send_message(player_data)

            # Response reading logic
            server_data = game_client.read_response()
            if server_data == "":
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
