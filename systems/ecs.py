from entities.base import EntityBetter
from systems.system import System


class ECS:
    def __init__(self):
        self._entities = []
        self._systems: list[System] = []

    def add_entity(self, entity: EntityBetter):
        self._entities.append(entity)

    def add_system(self, system):
        self._systems.append(system)

    def update(self):
        for system in self._systems:
            system.run(self._entities)
