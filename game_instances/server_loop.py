import os
import queue
import random
import time
from enum import Enum, auto

from entities.type import Food, Snake
from systems.game_logic import GameLogicSystem
from systems.movement import MovementSystem
from systems.network.constants import GAME_PORT
from systems.network.snake_server import SnakeServer

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame  # noqa: E402


class GameState(Enum):
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

        self._state = GameState.IDLE
        self._clock = pygame.time.Clock()
        self._tick_rate = tick_rate
        self._players = []

    def _setup(self):
        pygame.init()

        self._movement_system.setup()
        self._game_logic_system.setup()
        # self.rendering_system.setup()
        self._server.start()

        self._state = GameState.LOBBY

    def close(self):
        self._state = GameState.EXITING
        self._server.stop()
        pygame.quit()

    def run(self):
        self._setup()
        try:
            while self._state != GameState.EXITING:
                if self._state == GameState.LOBBY:
                    self._lobby()
                elif self._state == GameState.PLAYING:
                    self._playing()
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
        while self._state == GameState.LOBBY:
            # TODO - Wait for a ready message
            # TODO - Limit players
            # TODO - Block new connections after game start
            print("Players in lobby:", self._server.get_joined_players())

            # Assuming lobby ends after a certain number of players join
            if len(self._server.connected_players) >= 2:
                print(f"Game players: {self._server.connected_players}")
                break

            time.sleep(2)
        print("Lobby ready. Starting the game...")
        time.sleep(2)
        self._server.start_playing()
        self._state = GameState.PLAYING

    def _playing(self):
        # Playing
        #   Send initial game data
        #   Start countdown for game start
        #   Send game update
        #   Get players updates
        #   On game end, go back to lobby
        #   Or start a new game automatically

        entities = []
        entities.append(
            Food(
                (
                    random.randint(0, self._columns - 1),
                    random.randint(0, self._rows - 1),
                )
            )
        )

        for player_index, player_name in enumerate(self._server.get_joined_players()):
            player_color = [0, 0, 0]
            player_color[player_index % 3] = 255
            snake = Snake(
                player_name,
                start_position=(6, 0 + 2 * player_index),
                color=player_color,
            )
            entities.append(snake)

        acu_dt = 0
        players_updates = queue.Queue(maxsize=2)
        while self._state == GameState.PLAYING:
            # Initialize players snakes
            dt = self._clock.tick(self._tick_rate)
            acu_dt += dt
            self._server.send_game_state(entities)

            # TODO - Make the systems run for all players commands
            updates = self._server.get_players_updates()
            if updates:
                if not players_updates.full():
                    players_updates.put(updates)

            if acu_dt > 200:
                if not players_updates.empty():
                    self._movement_system.run(entities, players_updates.get())
                else:
                    self._movement_system.run(entities, None)
                acu_dt = 0

            entities = self._game_logic_system.run(entities)


if __name__ == "__main__":
    ServerLoop(10, 10, 20, "127.0.0.1").run()
