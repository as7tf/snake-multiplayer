from queue import Queue

import pygame

from schemas.game import PlayerCommand
from systems.system import System


class InputSystem(System):
    def __init__(self):
        self.input_queue = Queue(maxsize=2)
        self.command_queue = Queue()
    
    def setup(self):
        pass

    def run(self, entities):
        # TODO - Use entities instead of self.snake_direction and input queue
        snake_direction = None

        # ! FIXME - This is missing some inputs
        # ! It should probably run in a thread
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.command_queue.put_nowait("exit")
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
                    self.command_queue.put_nowait("exit")
                break
        if snake_direction is not None and not self.input_queue.full():
            print(snake_direction)
            # TODO - Make input specific for the player's snake
            self.input_queue.put_nowait([PlayerCommand(player_name="ducks_gonna_fly", command=snake_direction)])
