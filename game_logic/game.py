import random
import pygame
from game_entity.entity_type import Food, Snake
from game_system.game_logic_manager import GameLogicManager
from game_system.move_system import MoveSystem
from game_system.system import System
from game_system.game_renderer import GameRenderer


class GameLoop:
    def __init__(self, rows, columns, cell_size):
        self._running = True


        self.systems = [
            MoveSystem(),
        ]
        # FIXME - Integrate into the systems pipeline
        self.game_logic_manager = GameLogicManager(rows, columns, cell_size)

        self.rendering_system = GameRenderer(rows, columns, cell_size)

        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size


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
            self.update(entities, player_command)
            entities = self.game_logic_manager.run(entities)
            self.render(entities)
        self.exit()

    def setup(self):
        pygame.init()
        self._setup_systems()
        self._running = True

    def _setup_systems(self):
        for system in self.systems:
            system.setup()

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

    def update(self, entities, player_command):
        if not self._running:
            return

        for system in self.systems:
            for entity in entities:
                system.run(entity, player_command)

    def render(self, entities):
        if not self._running:
            return

        self.rendering_system.run(entities)

    def exit(self):
        pygame.quit()


if "__main__" == __name__:
    rows = 10
    columns = 10
    cell_size = 20

    game_loop = GameLoop(rows, columns, cell_size)
    game_loop.run()
