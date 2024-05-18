import pygame

from entities.entity import Entity

from systems.system import System


class RenderSystem(System):
    def __init__(self, rows: int, columns: int, cell_size: int):
        self.cell_size = cell_size

        # Set the screen size
        screen_width = self.cell_size * rows
        screen_height = self.cell_size * columns
        self.window = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Snake Game")

    def setup(self):
        pass

    def process_entities(self, entities: list[Entity]):
        self.window.fill((255, 255, 255))

        for entity in entities:
            draw_positions = entity._body
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
        pygame.time.Clock().tick(6)
