from components.body.component import BodyComponent
from components.movement.component import MovementComponent


class Entity:
    def __init__(self, entity_id: str, color: tuple[int, int, int]):
        if entity_id is None:
            raise ValueError("Entity id cannot be None. Enter a valid string")
        self._entity_id = entity_id
        self.color = color

        self.body_component = None
        self.movement_component = None

    def __eq__(self, value) -> bool:
        if not issubclass(type(value), Entity):
            raise ValueError("Entities can only be compared to other entities.")

        return True if self._entity_id == value._entity_id else False
