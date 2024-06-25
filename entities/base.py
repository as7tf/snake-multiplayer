from entities.entity_id import EntityID
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


class EntityBetter:
    def __init__(self, entity_id, entity_hash):
        self.id = entity_id
        self.hash = entity_hash
        self._components = {}

    def add_component(self, component):
        component_type = type(component)
        if component_type in self._components:
            raise ValueError(
                f"Component already exists for this entity."
                + f"Entity hash: '{self.hash}',"
                + f"Component type: '{component_type.__name__}'"
            )
        self._components[type(component)] = component

    def get_component(self, component_type):
        return self._components.get(component_type)

    def list_components(self):
        return list(self._components.keys())

    def remove_component(self, component_type):
        if component_type in self._components:
            del self._components[component_type]

    def __eq__(self, value) -> bool:
        if not issubclass(type(value), EntityBetter):
            raise ValueError("Entities can only be compared to other entities.")

        return True if self.hash == value.hash else False
