from components.body.component import BodyComponent


class SnakeBody(BodyComponent):
    def __init__(self, position: tuple[int, int], size):
        super().__init__(starting_position=position)

        self.size = size

        for i in range(1, self.size):
            self.segments.append((position[0] - i, position[1]))

    @property
    def head(self):
        return self.segments[0]

    @head.setter
    def head(self, new_head):
        self.segments[0] = new_head

    @property
    def tail(self):
        return self.segments[1:]

