from game_entity.entity import Entity


# Define the player snake
class Snake(Entity):
    def __init__(self, snake_id: str, start_position: tuple[int, int]):
        super().__init__(entity_id=snake_id, color=(0, 255, 0))

        self.size = 5

        self.body = [start_position]
        for i in range(1, self.size):
            self.body.append((start_position[0] - i, start_position[1]))

        self.direction = "RIGHT"


# Define the food
class Food(Entity):
    def __init__(self, start_position: tuple[int, int] = (0, 0)):
        super().__init__("snake_food", (255, 0, 0))

        self.body = [start_position]
