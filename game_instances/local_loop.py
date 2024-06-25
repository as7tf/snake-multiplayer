import pygame
import random
from enum import Enum, auto

from entities.type import Food, Snake

from systems.game_logic import GameLogicSystem
from systems.movement import MovementSystem
from systems.player_input import InputSystem
from systems.render import RenderSystem


class LocalLoop:
    def __init__(self, rows, columns, cell_size, tick_rate=60):
        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size
        self.tick_rate = tick_rate

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

        self._clock = pygame.time.Clock()
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

            self._clock.tick(self.tick_rate)
            
        self.close()
