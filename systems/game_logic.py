import random

from entities.entity import Entity
from entities.type import Food, Snake

from systems.system import System


class GameLogicSystem(System):
    def __init__(self, rows: int, columns: int, cell_size: int) -> None:
        self._grid_rows = rows
        self._grid_columns = columns
        self._cell_size = cell_size

    def setup(self):
        pass

    def run(self, entities: list[Entity]):
        snakes: list[Snake] = list(filter(lambda entity: isinstance(entity, Snake), entities))
        foods: list[Food] = list(filter(lambda entity: isinstance(entity, Food), entities))

        self._solve_clipping(snakes)

        for snake in snakes:
            for food in foods:
                if self._check_collision(snake, food):
                    snake.body_component.size += 1
                    self._spawn_valid_food(entities, food)

        for snake_1 in snakes:
            for snake_2 in snakes:
                # Checking snake collision with own tail
                if snake_1 == snake_2:
                    tail_1 = snake_1.body_component.tail
                    if snake_1.body_component.head in tail_1:
                        entities.remove(snake_1)

                # TODO - Check collision between different snakes

        return entities

    def _spawn_valid_food(self, entities: list[Entity], food: Food):
        invalid_position = True

        while invalid_position:
            food_position = (
                random.randint(0, self._grid_columns - 1),
                random.randint(0, self._grid_rows - 1),
            )
            invalid_position = False

            for entity in entities:
                entity: Food
                for segment in entity.body_component.segments:
                    if (
                        food_position[0] == segment[0]
                        and food_position[1] == segment[1]
                    ):
                        invalid_position = True
                        break
        food.position = food_position

    def _solve_clipping(self, snakes: list[Snake]):
        for snake in snakes:
            snake_head = list(snake.body_component.head)

            if snake_head[0] >= self._grid_columns:
                snake_head[0] = 0
            elif snake_head[0] < 0:
                snake_head[0] = self._grid_columns - 1
            elif snake_head[1] >= self._grid_rows:
                snake_head[1] = 0
            elif snake_head[1] < 0:
                snake_head[1] = self._grid_rows - 1

            snake.body_component.head = snake_head

    def _check_collision(self, entity_a: Entity, entity_b: Entity):
        if (
            entity_a.body_component.segments[0][0] == entity_b.body_component.segments[0][0]
            and entity_a.body_component.segments[0][1] == entity_b.body_component.segments[0][1]
        ):
            return True
        else:
            False
