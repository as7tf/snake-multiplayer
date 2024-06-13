import json
import random
import time
from enum import Enum, auto

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

from entities.type import Food, Snake
from systems.game_logic import GameLogicSystem
from systems.movement import MovementSystem
from systems.network.constants import GAME_PORT
from systems.network.server import SnakeServer


class ServerGameState(Enum):
    IDLE = auto()
    LOBBY = auto()
    PLAYING = auto()
    EXITING = auto()


class ServerLoop:
    def __init__(self, rows, columns, cell_size, server_ip, tick_rate=60):
        self._rows = rows
        self._columns = columns
        self._cell_size = cell_size

        coordinate_space = (self._rows, self._columns, self._cell_size)
        self._game_logic_system = GameLogicSystem(*coordinate_space)
        self._movement_system = MovementSystem()
        # self.rendering_system = RenderSystem(*coordinate_space)
        self._server = SnakeServer(server_ip, GAME_PORT)

        self._state = ServerGameState.IDLE
        self._clock = pygame.time.Clock()
        self._tick_rate = tick_rate
        self._players = []

    def _setup(self):
        pygame.init()

        self._movement_system.setup()
        self._game_logic_system.setup()
        # self.rendering_system.setup()
        self._server.start()

        self._state = ServerGameState.LOBBY

    def close(self):
        self._state = ServerGameState.EXITING
        self._server.stop()
        pygame.quit()

    def run(self):
        self._setup()
        try:
            while self._state != ServerGameState.EXITING:
                dt = self._clock.tick(self._tick_rate) / 1000
                if self._state == ServerGameState.LOBBY:
                    self._lobby()
                elif self._state == ServerGameState.PLAYING:
                    self._playing(dt)
        except KeyboardInterrupt:
            pass
        self.close()

    def _lobby(self):
        # Listening:
        #   Listen to connections
        #   Accept connections up to max players

        #   Choose player color randomly
        #   Wait for all players to have name and color set (Need to be different)

        #   Wait until all players are ready
        #   Block connections new connections and start preparing phase

        print("Listening for players...")
        while self._state == ServerGameState.LOBBY:
            # TODO - Wait for a ready message
            # TODO - Limit players
            # TODO - Block new connections after game start
            self._server.joined_players.intersection_update(
                self._server.connected_players
            )
            print("Players in lobby:", self._server.joined_players)

            # Assuming lobby ends after a certain number of players join
            if len(self._server.connected_players) >= 2:
                print(f"Game players: {self._server.connected_players}")
                break

            time.sleep(0.5)
        print("Lobby ready. Starting the game...")
        self._state = ServerGameState.PLAYING

    def _playing(self, dt):
        # Playing
        #   Send initial game data
        #   Start countdown for game start
        #   Send game update
        #   Get players updates
        #   On game end, go back to lobby
        #   Or start a new game automatically

        while True:
            print("Playing")
            self._server.joined_players.intersection_update(
                self._server.connected_players
            )
            time.sleep(2)

        def serialize_entities(entities):
            _server_entities = []

            for entity in entities:
                if isinstance(entity, Food):
                    _server_entities.append(
                        {"type": "food", "position": entity.position}
                    )
            return _server_entities

        entities = []
        entities.append(
            Food(
                (
                    random.randint(0, self._columns - 1),
                    random.randint(0, self._rows - 1),
                )
            )
        )

        # Initialize players snakes
        for player_name in self._players:
            snake = Snake(player_name, (6, 0))
            entities.append(snake)

        quit_game = False
        while self._state == ServerGameState.PLAYING:
            if quit_game == True:
                self._state = ServerGameState.EXITING
                break

            serialized_entities = serialize_entities(entities)
            self._server.send_all(json.dumps(serialized_entities))

            # TODO - Make the systems run for all players commands
            players_response: dict = self._server.read_all()
            if players_response:
                for player, response in players_response.items():
                    print(f"Player {player} response: {response}")
                    if response and "snake_direction" in response:
                        player_command = {
                            "snake_direction": response["snake_direction"]
                        }

                        self._movement_system.run(
                            entities, player_command
                        )  # Server side

            entities = self._game_logic_system.run(entities)  # Server side

            # self.rendering_system.run(entities)

            self._clock.tick(10)

        # Game goes back to lobby
        self._state = ServerGameState.LOBBY


if __name__ == "__main__":
    ServerLoop(10, 10, 20, "127.0.0.1").run()
