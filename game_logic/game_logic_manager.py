import random

from game_logic.entity import Entity
from game_logic.entity_type import Food, Snake


class GameLogicManager:
    def __init__(self, rows: int, columns: int, cell_size: int) -> None:
        self.__grid_rows = rows
        self.__grid_columns = columns
        self.__cell_size = cell_size

    def resolve_entities(self, entities: list[Entity]):
        snakes: list[Snake] = []
        foods: list[Food] = []

        for entity in entities:
            if isinstance(entity, Snake):
                snakes.append(entity)
            elif isinstance(entity, Food):
                foods.append(entity)

        self.__solve_clipping(snakes)

        for snake in snakes:
            for food in foods:
                if self.__check_collision(snake, food):
                    snake.size += 1
                    entities.remove(food)
                    self.__spawn_food(entities)

        for snake_a in snakes:
            for snake_b in snakes:
                if snake_a == snake_b:
                    headless = snake_a.body[1:]
                    if snake_a.body[0] in headless:
                        entities.remove(snake_a)

        return entities

    def __spawn_food(self, entities: list[Entity]):
        invalid_position = True

        while invalid_position:
            food_position = (
                random.randint(0, self.__grid_columns - 1),
                random.randint(0, self.__grid_rows - 1),
            )
            invalid_position = False

            for entity in entities:
                for segment in entity.body:
                    if (
                        food_position[0] == segment[0]
                        and food_position[1] == segment[1]
                    ):
                        invalid_position = True
                        break
        entities.append(Food(food_position))

    def __solve_clipping(self, snakes: list[Snake]):
        for snake in snakes:
            snake_head = list(snake.body[0])

            if snake_head[0] >= self.__grid_columns:
                snake_head[0] = 0
            elif snake_head[0] < 0:
                snake_head[0] = self.__grid_columns - 1
            elif snake_head[1] >= self.__grid_rows:
                snake_head[1] = 0
            elif snake_head[1] < 0:
                snake_head[1] = self.__grid_rows - 1

            snake.body[0] = snake_head

    def __check_collision(self, entity_a: Entity, entity_b: Entity):
        if (
            entity_a.body[0][0] == entity_b.body[0][0]
            and entity_a.body[0][1] == entity_b.body[0][1]
        ):
            return True
        else:
            False
