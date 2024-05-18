class MovementComponent:
    # ! Do not change dictionary order it is being used for checking if the
    # ! snake is doing a 180 degrees turn
    command_translator = {
        "UP": (0, -1),
        "LEFT": (-1, 0),
        "DOWN": (0, 1),
        "RIGHT": (1, 0),
    }

    def __init__(self):
        self.direction = None
        self.speed = 1  # Grid squares per frame

    def move(self):
        return NotImplementedError(f"Child system MUST implement {self.move.__name__}")
