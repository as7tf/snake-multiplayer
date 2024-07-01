import random

from components.body.component import BodyComponent
from components.body.snake import SnakeBody
from entities.base import EntityBetter
from entities.entity_id import EntityID
from systems.system import System


class GameLogicSystem(System):
    def __init__(self, rows: int, columns: int, cell_size: int) -> None:
        self._grid_rows = rows
        self._grid_columns = columns
        self._cell_size = cell_size

    def setup(self):
        pass

    def run(self, entities: list[EntityBetter]):
        snakes: list[EntityBetter] = list(
            filter(lambda entity: entity.id == EntityID.SNAKE, entities)
        )
        foods: list[EntityBetter] = list(
            filter(lambda entity: entity.id == EntityID.FOOD, entities)
        )

        self._solve_clipping(snakes)

        for snake in snakes:
            for food in foods:
                if self._has_collision(snake, food):
                    bc: SnakeBody = snake.get_component(SnakeBody)
                    bc.size += 1
                    self._spawn_valid_food(entities, food)

        for snake_1 in snakes:
            for snake_2 in snakes:
                # Checking snake collision
                bc_1: SnakeBody = snake_1.get_component(SnakeBody)
                bc_2: SnakeBody = snake_2.get_component(SnakeBody)
                if snake_1 == snake_2:
                    body_2 = bc_2.tail
                else:
                    body_2 = bc_2.segments
                if bc_1.head in body_2:
                    entities.remove(snake_1)

                # TODO - Check collision between different snakes' heads

    def _spawn_valid_food(self, entities: list[EntityBetter], food: EntityBetter):
        # TODO! - Doesn't actually spawn food, it just sets its position
        invalid_position = True

        while invalid_position:
            food_position = (
                random.randint(0, self._grid_columns - 1),
                random.randint(0, self._grid_rows - 1),
            )
            invalid_position = False

            for entity in entities:
                bc: BodyComponent = entity.get_component(BodyComponent)
                if bc is None:
                    bc: SnakeBody = entity.get_component(SnakeBody)
                for segment in bc.segments:
                    if (
                        food_position[0] == segment[0]
                        and food_position[1] == segment[1]
                    ):
                        invalid_position = True
                        break
        bc: BodyComponent = food.get_component(BodyComponent)
        bc.segments = [food_position]

    def _solve_clipping(self, snakes: list[EntityBetter]):
        for snake in snakes:
            bc: SnakeBody = snake.get_component(SnakeBody)
            snake_head = list(bc.head)
            if snake_head[0] >= self._grid_columns:
                snake_head[0] = 0
            elif snake_head[0] < 0:
                snake_head[0] = self._grid_columns - 1
            elif snake_head[1] >= self._grid_rows:
                snake_head[1] = 0
            elif snake_head[1] < 0:
                snake_head[1] = self._grid_rows - 1
            bc.head = snake_head

    def _has_collision(self, entity_a: EntityBetter, entity_b: EntityBetter):
        bc_a: BodyComponent = entity_a.get_component(BodyComponent)
        if bc_a is None:
            bc_a: SnakeBody = entity_a.get_component(SnakeBody)
        bc_b: BodyComponent = entity_b.get_component(BodyComponent)
        if (
            bc_a.segments[0][0] == bc_b.segments[0][0]
            and bc_a.segments[0][1] == bc_b.segments[0][1]
        ):
            return True
        else:
            return False
