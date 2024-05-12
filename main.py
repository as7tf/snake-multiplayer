import pygame

from game_logic.entity_manager import EntityManager
from game_logic.entity_type import Food, Snake
from game_logic.game_logic_manager import GameLogicManager
from ui.game_renderer import GameRenderer


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
