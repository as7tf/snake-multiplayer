import numpy as np

from entities.type import Snake

from systems.system import System


class MovementSystem(System):
    def setup(self):
        # ! Do not change dictionary order it is being used for checking if the
        # ! snake is doing a 180 degrees turn
        self.command_translator = {
            "UP": (0, -1),
            "LEFT": (-1, 0),
            "DOWN": (0, 1),
            "RIGHT": (1, 0),
        }

    def process_entities(self, entities, command):
        snakes: list[Snake] = list(filter(lambda entity: isinstance(entity, Snake), entities))

        for snake in snakes:
            if command is not None:
                direction = command["snake_direction"]

                if not self._is_opposite_direction(snake.direction, direction):
                    snake.direction = direction
            
            offset = self.command_translator[snake.direction]
            np_offset = np.array(offset).astype(int)

            np_head = np.array(snake.head).astype(int)
            new_head = np.add(np_offset, np_head)

            snake._body.insert(0, tuple(new_head))

            # Remove last body segment if body is greater than current snake size
            if len(snake._body) > snake.size:
                snake._body.pop()

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
