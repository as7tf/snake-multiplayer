from pygame.draw_py import Point


class Entity:
    def __init__(self, entity_id: str, color: tuple[int, int, int]):
        if entity_id is None:
            raise ValueError("Entity id cannot be None. Enter a valid string")
        self._entity_id = entity_id
        self.color = color
        self._body: list[Point] = [Point(0, 0)]

    def __eq__(self, value) -> bool:
        if not issubclass(type(value), Entity):
            raise ValueError("Entities can only be compared to other entities.")

        return True if self._entity_id == value._entity_id else False
