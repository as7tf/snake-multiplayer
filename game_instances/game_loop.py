import pygame
import random

from entities.type import Food, Snake

from systems.game_logic import GameLogicSystem
from systems.movement import MovementSystem
from systems.player_input import InputSystem
from systems.render import RenderSystem
from systems.network.server import ServerProcess
from systems.network.constants import GAME_PORT


class LocalLoop:
    def __init__(self, rows, columns, cell_size):
        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size

        coordinate_space = (self.rows, self.columns, self.cell_size)
        self.game_logic_system = GameLogicSystem(*coordinate_space)
        self.rendering_system = RenderSystem(*coordinate_space)
        self.movement_system = MovementSystem()
        self.input_system = InputSystem()

        # TODO - Add UI system and execute after render system

    def setup(self):
        pygame.init()

        self.input_system.setup()
        self.movement_system.setup()
        self.game_logic_system.setup()
        self.rendering_system.setup()

        self._running = True

    def close(self):
        pygame.quit()

    def run(self):
        self.setup()

        entities = []
        snake = Snake("ducks_gonna_fly", (6, 0))
        snake.movement_component.speed = 1
        entities.append(snake)
        entities.append(
            Food(
                (
                    random.randint(0, self.columns - 1),
                    random.randint(0, self.rows - 1),
                )
            )
        )

        while self._running:
            # TODO - Make input specific for the player's snake
            player_command, quit_game = self.input_system.run()

            if quit_game == True:
                self._running = False
                break

            self.movement_system.run(entities, player_command)

            entities = self.game_logic_system.run(entities)

            self.rendering_system.run(entities)
        self.close()


class ServerLoop:
    def __init__(self, rows, columns, cell_size, server_ip):
        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size

        coordinate_space = (self.rows, self.columns, self.cell_size)
        self.game_logic_system = GameLogicSystem(*coordinate_space)
        self.movement_system = MovementSystem()
        self.game_server = ServerProcess(server_ip, GAME_PORT)

    def setup(self):
        self.movement_system.setup()
        self.game_logic_system.setup()

        self._running = True

    def close(self):
        pass

    def run(self):
        self.setup()

        entities = []
        entities.append(
            Food(
                (
                    random.randint(0, self.columns - 1),
                    random.randint(0, self.rows - 1),
                )
            )
        )

        # Listening:
        #   Listen to connections
        #   Accept connections up to max players
        #   Choose player color randomly
        #   Wait for all players to have name and color set (Need to be different)
        #   Wait until all players are ready
        #   Block connections new connections and start preparing phase

        quit_game = False
        while self._running:
            if quit_game == True:
                self._running = False
                break

        # Preparing:
        #   Sync players
        #   Send initial game data
        #   Start countdown for game start
        #   Start Playing phase

        quit_game = False
        while self._running:
            if quit_game == True:
                self._running = False
                break

        # Playing
        #   Send game update
        #   Get players updates
        #   On game end, go back to lobby
        #   Or start a new game automatically

        quit_game = False
        while self._running:
            if quit_game == True:
                self._running = False
                break

            # TODO - Add network layer for client-server communication
            # TODO - Create different game instances for the server and the client
            player_command = "test"

            self.movement_system.run(entities, player_command)  # Server side

            entities = self.game_logic_system.run(entities)  # Server side


class ClientLoop: 
    def __init__(self, rows, columns, cell_size):
        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size

        coordinate_space = (self.rows, self.columns, self.cell_size)
        self.rendering_system = RenderSystem(*coordinate_space)
        self.input_system = InputSystem()

        # TODO - Add UI system and execute after render system

    def setup(self):
        pygame.init()

        self.input_system.setup()
        self.rendering_system.setup()

        self._running = True

    def close(self):
        pygame.quit()

    def run(self):
        self.setup()

        entities = []
        snake = Snake("ducks_gonna_fly", (6, 0))
        snake.movement_component.speed = 1
        entities.append(snake)
        entities.append(
            Food(
                (
                    random.randint(0, self.columns - 1),
                    random.randint(0, self.rows - 1),
                )
            )
        )

        while self._running:
            # TODO - Make input specific for the player's snake
            player_command, quit_game = self.input_system.run()  # Client side

            if quit_game == True:  # Client side
                self._running = False

            # TODO - Add network layer for client-server communication
            # TODO - Create different game instances for the server and the client

            self.rendering_system.run(entities)  # Client side
        self.close()
