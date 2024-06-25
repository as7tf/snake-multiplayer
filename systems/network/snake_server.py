import time

from entities.type import Food, Snake
from schemas.entities import EntitiesMessage, EntityMessage
from schemas.game import GameReady, PlayerCommand
from schemas.lobby import JoinLobbyRequest, LobbyInfoRequest, LobbyInfoResponse
from schemas.response import ServerResponse
from systems.decoder import MessageDecoder
from systems.network.constants import GAME_PORT
from systems.network.server import GameServer
from utils.timer import Timer  # , print_async_func_time, print_func_time


class SnakeServer:
    def __init__(self, server_ip, server_port, ticks_per_second: float = 50):
        self._server = GameServer(
            server_ip, server_port, self.request_responder, ticks_per_second
        )

        self._decoder = MessageDecoder()

        self._joined_players = set()
        self._player_names = {}

    def start(self):
        self._server.start()
        self._server.start_lobby()

    def start_playing(self):
        self._server.start_playing()
        self._server.broadcast_message(GameReady().model_dump_json())

    def stop(self):
        self._server.stop()

    @property
    def connected_players(self):
        return self._server.connected_players

    def get_joined_players(self):
        self._joined_players.intersection_update(self.connected_players)
        player_ids = list(
            filter(lambda x: x in self._joined_players, list(self._player_names.keys()))
        )
        player_names = list(map(lambda x: self._player_names[x], player_ids))
        for player_id, player_name in zip(player_ids, player_names):
            print(f"Player {player_id} is {player_name}")

        return player_names

    def request_responder(self, client_id, request: str):
        player_message = self._decoder.decode_message(request)
        print(f"Got {player_message.__class__.__name__} from {client_id}")
        if isinstance(player_message, JoinLobbyRequest):
            print("Player joining lobby:", client_id)
            message = ServerResponse(status=0, message="Joined lobby").model_dump_json()
            self._joined_players.add(client_id)
            self._player_names[client_id] = player_message.player_name
            return message
        elif isinstance(player_message, LobbyInfoRequest):
            print("Sending lobby info to", client_id)
            return LobbyInfoResponse(
                status=0,
                message="Here ya go!",
                player_names=list(self.get_joined_players()),
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
            ).model_dump_json()

        else:
            print("Message type", type(player_message))
            return ServerResponse(status=1, message="Invalid message").model_dump_json()

    def get_players_updates(self):
        player_updates: list[PlayerCommand] = []
        for data in self._server.gather_player_data():
            player_message = self._decoder.decode_message(data)
            if isinstance(player_message, PlayerCommand):
                player_updates.append(player_message)
        return player_updates

    def send_game_state(self, entities):
        game_state_message = self._serialize_entities(entities)
        self._server.broadcast_message(game_state_message)

    def _serialize_entities(self, entities):
        _server_entities = []

        for entity in entities:
            if isinstance(entity, Food):
                _server_entities.append(
                    EntityMessage(
                        entity_id="food",
                        body=entity.body_component.segments,
                        color=entity.color,
                    )
                )
            elif isinstance(entity, Snake):
                _server_entities.append(
                    EntityMessage(
                        entity_id="snake",
                        body=entity.body_component.segments,
                        color=entity.color,
                    )
                )
        return EntitiesMessage(entities=_server_entities).model_dump_json()


def main():
    game_server = SnakeServer("127.0.0.1", GAME_PORT, ticks_per_second=50)
    game_server.start()
    timer = Timer()

    server_throttle = 0.01
    try:
        while True:
            time.sleep(server_throttle)
            timer.reset()
            # print(f"Time elapsed: {round(timer.elapsed_ms(), 1)} ms")
    except KeyboardInterrupt:
        game_server.stop()


if __name__ == "__main__":
    main()
