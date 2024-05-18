import pygame

from systems.system import System


class InputSystem(System):
    def setup(self):
        pass

    def run(self):
        quit_game = False
        snake_direction = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    snake_direction = {"snake_direction": "UP"}
                elif event.key == pygame.K_DOWN:
                    snake_direction = {"snake_direction": "DOWN"}
                elif event.key == pygame.K_LEFT:
                    snake_direction = {"snake_direction": "LEFT"}
                elif event.key == pygame.K_RIGHT:
                    snake_direction = {"snake_direction": "RIGHT"}
                elif event.key == pygame.K_ESCAPE:
                    quit_game = True
                break
        return snake_direction, quit_game

