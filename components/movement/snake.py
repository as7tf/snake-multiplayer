import numpy as np

from components.body.snake import SnakeBody
from components.movement.component import MovementComponent


class SnakeMovement(MovementComponent):
    def __init__(self, snake_body: SnakeBody=SnakeBody(), direction="LEFT"):
        super().__init__()
        self.snake_body = snake_body
        self.direction = direction
        self.speed = 1

    def move(self, command):
        direction = None
        if command is not None:
            direction = command["snake_direction"]

            if not self._is_opposite_direction(self.direction, direction):
                self.direction = direction

        offset = self.command_translator[self.direction]
        np_offset = np.array(offset).astype(int)
        np_offset = np.multiply(np_offset, np.array([self.speed, self.speed]).astype(int))

        np_head = np.array(self.snake_body.head).astype(int)
        new_head = np.add(np_offset, np_head)

        self._move_head(new_head)
        self._move_tail()

    def _move_head(self, new_head: np.ndarray):
        old_head = np.array(self.snake_body.head).astype(int)
        new_segment = old_head

        direction = np.array(self.command_translator[self.direction]).astype(int)
        while not np.array_equal(new_segment, new_head):
            new_segment = np.add(new_segment, direction)
            self.snake_body.segments.insert(0, tuple(new_segment))

    def _move_tail(self):
        # Remove last body segment if body is greater than current snake size
        while len(self.snake_body.segments) > self.snake_body.size:
            self.snake_body.segments.pop()

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

