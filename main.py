import pygame
import random
from pygame.draw_py import Point


class Entity:
    def __init__(self, entity_id: str, color: tuple[int, int, int]):
        if entity_id is None:
            raise ValueError("Entity id cannot be None. Enter a valid string")
        self.__entity_id = entity_id
        self.color = color
        self.body: list[Point] = [Point(0, 0)]

    def __eq__(self, value) -> bool:
        if not issubclass(type(value), Entity):
            raise ValueError("Entities can only be compared to other entities.")

        return True if self.__entity_id == value.__entity_id else False


# Define the player snake
class Snake(Entity):
    def __init__(self, snake_id: str, start_position: tuple[int, int]):
        super().__init__(entity_id=snake_id, color=(0, 255, 0))

        self.size = 5

        self.body = [start_position]
        for i in range(1, self.size):
            self.body.insert(0, (start_position[0] - i, start_position[1]))

        self.direction = "RIGHT"

    def move(self):
        head = self.body[0]
        x, y = head
        if self.direction == "UP":
            y -= 1
        elif self.direction == "DOWN":
            y += 1
        elif self.direction == "LEFT":
            x -= 1
        elif self.direction == "RIGHT":
            x += 1
        self.body.insert(0, (x, y))

        if len(self.body) > self.size:
            self.body.pop()


# Define the food
class Food(Entity):
    def __init__(self, start_position: tuple[int, int] = (0, 0)):
        super().__init__("snake_food", (255, 0, 0))

        self.body = [start_position]


class EntityManager:
    def __init__(self):
        self.__entities: list[Entity] = []

    def add_entity(self, entity: Entity):
        if entity in self.__entities:
            raise ValueError("Entity already added!")
        self.__entities.append(entity)

    def get_entities(self):
        return self.__entities

    def set_entities(self, entities: list[Entity]):
        self.__entities = entities


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


class EntityConverter:
    def __init__(self, entity_translate: dict) -> None:
        self.__entity_translate = entity_translate

    def translate_packets_to_entities(self, game_packets: list[dict]) -> EntityManager:
        entity_manager = EntityManager()

        for entity_packet in game_packets:
            entity_class = self.__entity_translate[entity_packet["entity_type"]]
            entity_manager.add_entity(entity_class(entity_packet["entity_id"]))
        return entity_manager

    def translate_entities_to_packets(self, entity_manager: EntityManager):
        game_packets = [{}]

        # TODO - Translate game entities to game packets

        return game_packets


class PlayerCommands:
    def move_snake(self, snake_id, direction):
        pass


class GameRenderer:
    def __init__(self, rows: int, columns: int, cell_size: int):
        self.cell_size = cell_size

        # Set the screen size
        screen_width = self.cell_size * rows
        screen_height = self.cell_size * columns
        self.window = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Snake Game")

    def draw(self, game_entities: list[Entity]):
        self.window.fill((255, 255, 255))

        for entity in game_entities:
            draw_positions = entity.body
            for segment in draw_positions:
                pygame.draw.rect(
                    self.window,
                    entity.color,
                    (
                        segment[0] * self.cell_size,
                        segment[1] * self.cell_size,
                        self.cell_size,
                        self.cell_size,
                    ),
                )


if "__main__" == __name__:

    # Initialize Pygame
    pygame.init()

    # Initialize the player snake and food
    snake = Snake("ducks_gonna_fly", (0, 0))
    food = Food()

    entity_manager = EntityManager()
    entity_manager.add_entity(food)
    entity_manager.add_entity(snake)

    rows = 10
    columns = 10
    cell_size = 20
    ui_grid = GameRenderer(rows, columns, cell_size)
    gl_manager = GameLogicManager(rows, columns, cell_size)

    # Main loop
    running = True
    while running:

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP and snake.direction != "DOWN":
                    snake.direction = "UP"
                elif event.key == pygame.K_DOWN and snake.direction != "UP":
                    snake.direction = "DOWN"
                elif event.key == pygame.K_LEFT and snake.direction != "RIGHT":
                    snake.direction = "LEFT"
                elif event.key == pygame.K_RIGHT and snake.direction != "LEFT":
                    snake.direction = "RIGHT"
                elif event.key == pygame.K_ESCAPE:
                    running = False

        # Move the snake
        snake.move()

        # Resolve game logic
        solved_entities = gl_manager.resolve_entities(entity_manager.get_entities())
        entity_manager.set_entities(solved_entities)

        # Draw the entities
        ui_grid.draw(entity_manager.get_entities())

        pygame.display.flip()
        pygame.time.Clock().tick(6)

    pygame.quit()
