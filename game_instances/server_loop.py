from enum import Enum, auto
import json
import time
import pygame
import random
import traceback as tb

from entities.type import Food, Snake

from systems.game_logic import GameLogicSystem
from systems.movement import MovementSystem
from systems.network.server import TCPServer
from systems.network.constants import GAME_PORT
from systems.render import RenderSystem

from game_instances.constants import GameState


class ServerLoop:
    def __init__(self, rows, columns, cell_size, server_ip):
        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size

        coordinate_space = (self.rows, self.columns, self.cell_size)
        self.game_logic_system = GameLogicSystem(*coordinate_space)
        self.movement_system = MovementSystem()
        # self.rendering_system = RenderSystem(*coordinate_space)
        self.server = TCPServer(server_ip, GAME_PORT)

        self.game_state = None
        self.clock = pygame.time.Clock()
        self.players = []

    def setup(self):
        pygame.init()

        self.movement_system.setup()
        self.game_logic_system.setup()
        # self.rendering_system.setup()
        self.server.start()

        self.game_state = GameState.LOBBY
        self._running = True

    def close(self):
        self._running = False
        self.server.stop()
        pygame.quit()

    def run(self):
        self.setup()
        while self._running:
            self._run_current_state()

    def _run_current_state(self):
        state_method = getattr(self, f"{self.game_state.name.lower()}")
        state_method()

    def lobby(self):
        # Listening:
        #   Listen to connections
        #   Accept connections up to max players

        #   Choose player color randomly
        #   Wait for all players to have name and color set (Need to be different)

        #   Wait until all players are ready
        #   Block connections new connections and start preparing phase

        while self._running:
            try:
                # TODO - Wait for a ready message
                # TODO - Limit players
                # TODO - Block new connections after game start

                print("Waiting for players...")

                # Assuming lobby ends after a certain number of players join
                new_players = self.server.read_all()
                if new_players:
                    new_players = list(new_players.keys())
                    for player in new_players:
                        if player not in self.players:
                            self.players.append(player)
                if len(self.players) > 0:
                    print(f"Game players: {self.players}")
                    self.server.send_all({"info": "start"})
                    break
                time.sleep(1)
            except:
                tb.print_exc()
                self.close()
                return
        
        print("Lobby ready. Starting the game...")
        self.game_state = GameState.PLAYING

    def playing(self):
        # Playing
        #   Send initial game data
        #   Start countdown for game start
        #   Send game update
        #   Get players updates
        #   On game end, go back to lobby
        #   Or start a new game automatically

        def serialize_entities(entities):
            _server_entities = []
            
            for entity in entities:
                if isinstance(entity, Food):
                    _server_entities.append({
                        "type": "food",
                        "position": entity.position
                    })
            return _server_entities

        entities = []
        entities.append(
            Food(
                (
                    random.randint(0, self.columns - 1),
                    random.randint(0, self.rows - 1),
                )
            )
        )

        # Initialize players snakes
        for player_name in self.players:
            snake = Snake(player_name, (6, 0))
            entities.append(snake)

        quit_game = False
        while self._running:
            if quit_game == True:
                self._running = False
                break

            serialized_entities = serialize_entities(entities)
            self.server.send_all(json.dumps(serialized_entities))

            # TODO - Make the systems run for all players commands
            players_response: dict = self.server.read_all()
            if players_response:
                for player, response in players_response.items():
                    print(f"Player {player} response: {response}")
                    if response and "snake_direction" in response:
                        player_command = {"snake_direction": response["snake_direction"]}

                        self.movement_system.run(entities, player_command)  # Server side

            entities = self.game_logic_system.run(entities)  # Server side

            # self.rendering_system.run(entities)

            self.clock.tick(10)

        # Game goes back to lobby
        self.game_state = GameState.LOBBY


if __name__ == "__main__":
    ServerLoop(10, 10, 20, "127.0.0.1").run()