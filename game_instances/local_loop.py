import random

import pygame

from components.body.component import BodyComponent
from components.body.snake import SnakeBody
from components.color import ColorComponent
from components.movement.snake import SnakeMovement
from components.player import PlayerComponent
from entities.entity_id import EntityID
from entities.factory import EntityFactory
from schemas.game import PlayerCommand
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

        self.entity_factory = EntityFactory()

        # TODO - Add UI system and execute after render system

    def setup(self):
        pygame.init()

        self.input_system.setup()
        self.movement_system.setup()
        self.game_logic_system.setup()
        self.rendering_system.setup()

        self._clock = pygame.time.Clock()
        self._running = True

    def setup_entities(self):
        snake = self.entity_factory.create_entity(EntityID.SNAKE)
        snake.set_component(PlayerComponent(player_name="ducks_gonna_fly"))
        snake.set_component(SnakeBody((6, 0), 3))
        snake.set_component(ColorComponent((0, 255, 0)))
        snake.set_component(SnakeMovement(snake.get_component(SnakeBody)))

        food = self.entity_factory.create_entity(EntityID.FOOD)
        food.set_component(
            BodyComponent(
                (
                    random.randint(0, self.columns - 1),
                    random.randint(0, self.rows - 1),
                )
            )
        )
        food.set_component(ColorComponent((255, 0, 0)))

        return [snake, food]

    def close(self):
        pygame.quit()

    def run(self):
        self.setup()

        entities = self.setup_entities()

        while self._running:
            # TODO - Make input specific for the player's snake
            player_command, quit_game = self.input_system.run()
            if player_command:
                player_command = [PlayerCommand(player_name="ducks_gonna_fly", command=player_command)]
            else:
                player_command = None

            if quit_game:
                self._running = False
                break
            
            self.movement_system.run(entities, player_command)

            self.game_logic_system.run(entities)

            self.rendering_system.run(entities)

            self._clock.tick(self.tick_rate)

        self.close()
