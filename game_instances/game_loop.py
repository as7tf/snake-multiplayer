import random
import pygame

from entities.type import Food, Snake

from systems.game_logic import GameLogicSystem
from systems.movement import MovementSystem
from systems.player_input import InputSystem
from systems.render import RenderSystem


class GameLoop:
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
                break

            # TODO - Add network layer for client-server communication
            # TODO - Create different game instances for the server and the client

            self.movement_system.run(entities, player_command)  # Server side

            entities = self.game_logic_system.run(entities)  # Server side

            self.render(entities)  # Client side
        self.close()

    def render(self, entities):
        self.rendering_system.run(entities)

    def close(self):
        pygame.quit()


if "__main__" == __name__:
    rows = 10
    columns = 10
    cell_size = 20

    game_loop = GameLoop(rows, columns, cell_size)
    game_loop.run()
