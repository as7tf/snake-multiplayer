from game_entity.entity import Entity
from game_entity.entity_type import Snake
from game_system.system import System

import numpy as np


class MoveSystem(System):
    def setup(self):
        # ! Do not change dictionary order it is being used for checking if the
        # ! snake is doing a 180 degrees turn
        self.command_translator = {
            "UP": (0, -1),
            "LEFT": (-1, 0),
            "DOWN": (0, 1),
            "RIGHT": (1, 0),
        }

    def run(self, snake: Snake, command):
        if not isinstance(snake, Snake):
            return

        if command is not None:
            direction = command["snake_direction"]

            if not self._is_opposite_direction(snake.direction, direction):
                snake.direction = direction
        
        offset = self.command_translator[snake.direction]
        offset = np.array(offset).astype(int)

        head = np.array(snake.body[0]).astype(int)
        new_head = np.add(offset, head)

        snake.body.insert(0, tuple(new_head))

        # Remove last body segment if body is greater than current snake size
        if len(snake.body) > snake.size:
            snake.body.pop()

    def _is_opposite_direction(self, current_direction, new_direction: str):
        # Get a list from the keys of command translator dictionary
        indexed_directions = list(self.command_translator)

        # Find the indexes of the directions on the list
        new_direction_index = indexed_directions.index(new_direction)
        current_direction_index = indexed_directions.index(current_direction)

        # Opposite direction is by 2 units of difference in the indexes.
        # Go back to 0 if it goes outside of the index list length.
        opposite_direction_index = current_direction_index + 2
        opposite_direction_index %= len(indexed_directions)

        if new_direction_index == opposite_direction_index:
            return True
        else:
            return False
