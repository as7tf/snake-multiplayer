from components.body.component import BodyComponent
from components.body.snake import SnakeBody
from components.color import ColorComponent
from components.movement.snake import SnakeMovement
from components.player import PlayerComponent
from entities.entity_id import EntityID


def get_entities_configuration():
    entities_config = _CustomEntityDict()
    entities_config.add_configuration(
        EntityID.SNAKE, components=[SnakeBody, SnakeMovement, PlayerComponent, ColorComponent]
    )
    entities_config.add_configuration(EntityID.FOOD, components=[BodyComponent, ColorComponent])
    return entities_config


class _CustomEntityDict(dict):
    def __init__(self):
        super().__init__()

    def __setitem__(self, key, value):
        if not isinstance(value, list):
            raise ValueError("Components must be a list")
        elif not isinstance(key, EntityID):
            raise ValueError("Key must be an EntityID")
        elif key in self:
            raise ValueError("Entity configuration already exists")
        super().__setitem__(key, value)

    def __getitem__(self, key):
        if not isinstance(key, EntityID):
            raise ValueError("Key must be an EntityID")
        elif key not in self:
            raise ValueError(f"{key.name} entity configuration does not exist")
        return super().__getitem__(key)

    def add_configuration(self, entity_id, components):
        self[entity_id] = components

    def get_components(self, entity_id):
        return self.get(entity_id)
