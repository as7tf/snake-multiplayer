import pygame

from components.body.component import BodyComponent
from components.body.snake import SnakeBody
from components.color import ColorComponent
from entities.base import EntityBetter

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

    def run(self, entities: list[EntityBetter]):
        self.window.fill((255, 255, 255))

        for entity in entities:
            bc: BodyComponent = entity.get_component(BodyComponent)
            if bc is None:
                bc: SnakeBody = entity.get_component(SnakeBody)
            draw_positions = bc.segments
            for segment in draw_positions:
                pygame.draw.rect(
                    self.window,
                    entity.get_component(ColorComponent).color,
                    (
                        segment[0] * self.cell_size,
                        segment[1] * self.cell_size,
                        self.cell_size,
                        self.cell_size,
                    ),
                )
        
        pygame.display.flip()
