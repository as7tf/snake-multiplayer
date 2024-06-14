import pygame

from entities.entity import Entity

from systems.system import System


class RenderSystem(System):
    def __init__(self, rows: int, columns: int, cell_size: int):
        self.cell_size = cell_size

        # Set the screen size
        screen_width = self.cell_size * columns
        screen_height = self.cell_size * rows
        self.window = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Snake Game")

    def setup(self):
        self.window.fill((255, 255, 255))
        pygame.display.flip()

    def run(self, entities: list[Entity]):
        self.window.fill((255, 255, 255))

        for entity in entities:
            draw_positions = entity.body_component.segments
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
        
        pygame.display.flip()
