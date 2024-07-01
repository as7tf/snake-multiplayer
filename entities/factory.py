import hashlib
import random

from entities.base import EntityBetter
from entities.configuration import get_entities_configuration
from entities.entity_id import EntityID


class EntityFactory:
    def __init__(self):
        self._config = get_entities_configuration()
        self._used_hashes = set()

    def create_entity(self, entity_id: EntityID, **kwargs):
        entity_components = self._config.get(entity_id)
        if entity_components is None:
            raise ValueError(f"Entity {entity_id.name} does not exist")
        entity = EntityBetter(entity_id, self._get_entity_hash())
        for component_type in entity_components:
            entity.add_component(component_type)
        return entity

    def _get_entity_hash(self):
        hashed = hashlib.sha256(str(random.randint(0, 10000)).encode()).hexdigest()
        while hashed in self._used_hashes:
            hashed = hashlib.sha256(str(random.randint(0, 10000)).encode()).hexdigest()
        self._used_hashes.add(hashed)
        return hashed
