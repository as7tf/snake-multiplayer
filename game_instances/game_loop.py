import random
import pygame

from entities.type import Food, Snake

from systems.game_logic import GameLogicSystem
from systems.movement import MovementSystem
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

        # TODO - Add UI system and execute after render system

    def setup(self):
        pygame.init()

        self.movement_system.setup()
        self.game_logic_system.setup()
        self.rendering_system.setup()

        self._running = True

    def run(self):
        self.setup()

        entities = []
        entities.append(Snake("ducks_gonna_fly", (6, 0)))
        entities.append(
            Food(
                (
                    random.randint(0, self.columns - 1),
                    random.randint(0, self.rows - 1),
                )
            )
        )

        while self._running:
            player_command = self.process_input()

            if self._running == False:
                break

            self.movement_system.process_entities(entities, player_command)

            entities = self.game_logic_system.process_entities(entities)

            self.render(entities)
        self.exit()

    def process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN:
                snake_direction = {"snake_direction": None}
                if event.key == pygame.K_UP:
                    snake_direction = {"snake_direction": "UP"}
                elif event.key == pygame.K_DOWN:
                    snake_direction = {"snake_direction": "DOWN"}
                elif event.key == pygame.K_LEFT:
                    snake_direction = {"snake_direction": "LEFT"}
                elif event.key == pygame.K_RIGHT:
                    snake_direction = {"snake_direction": "RIGHT"}
                elif event.key == pygame.K_ESCAPE:
                    self._running = False
                return snake_direction
        return None

    def render(self, entities):
        self.rendering_system.process_entities(entities)

    def exit(self):
        pygame.quit()


if "__main__" == __name__:
    rows = 10
    columns = 10
    cell_size = 20

    game_loop = GameLoop(rows, columns, cell_size)
    game_loop.run()
