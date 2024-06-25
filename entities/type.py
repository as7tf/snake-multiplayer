from entities.base import Entity

from components.body.component import BodyComponent
from components.body.snake import SnakeBody
from components.movement.snake import SnakeMovement


# Define the player snake
class Snake(Entity):
    def __init__(self, snake_id: str, start_position: tuple[int, int], color=(0, 255, 0)):
        super().__init__(entity_id=snake_id, color=color)

        self.body_component = SnakeBody(start_position, 5)
        self.movement_component = SnakeMovement(self.body_component, "RIGHT")


# Define the food
class Food(Entity):
    def __init__(self, start_position: tuple[int, int] = (0, 0)):
        super().__init__("snake_food", (255, 0, 0))

        self.body_component = BodyComponent(start_position)

    @property
    def position(self):
        return self.body_component.segments[0]

    @position.setter
    def position(self, new_position: tuple[int, int]):
        self.body_component.segments[0] = new_position
