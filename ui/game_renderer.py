import pygame

from game_logic.entity import Entity


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
