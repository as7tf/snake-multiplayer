from game_logic.entity import Entity


class EntityManager:
    def __init__(self):
        self.__entities: list[Entity] = []

    def add_entity(self, entity: Entity):
        if entity in self.__entities:
            raise ValueError("Entity already added!")
        self.__entities.append(entity)

    def get_entities(self):
        return self.__entities

    def set_entities(self, entities: list[Entity]):
        self.__entities = entities
