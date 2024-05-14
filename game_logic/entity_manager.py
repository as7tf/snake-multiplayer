from game_logic.entity import Entity


class EntityManager:
    def __init__(self):
        self._entities: list[Entity] = []

    def add_entity(self, entity: Entity):
        if entity in self._entities:
            raise ValueError("Entity already added!")
        self._entities.append(entity)

    def get_entities(self):
        return self._entities

    def set_entities(self, entities: list[Entity]):
        self._entities = entities
