from game_logic.entity import Entity


# Define the player snake
class Snake(Entity):
    def __init__(self, snake_id: str, start_position: tuple[int, int]):
        super().__init__(entity_id=snake_id, color=(0, 255, 0))

        self.size = 5

        self.body = [start_position]
        for i in range(1, self.size):
            self.body.insert(0, (start_position[0] - i, start_position[1]))

        self.direction = "RIGHT"

    def move(self):
        head = self.body[0]
        x, y = head
        if self.direction == "UP":
            y -= 1
        elif self.direction == "DOWN":
            y += 1
        elif self.direction == "LEFT":
            x -= 1
        elif self.direction == "RIGHT":
            x += 1
        self.body.insert(0, (x, y))

        if len(self.body) > self.size:
            self.body.pop()


# Define the food
class Food(Entity):
    def __init__(self, start_position: tuple[int, int] = (0, 0)):
        super().__init__("snake_food", (255, 0, 0))

        self.body = [start_position]

