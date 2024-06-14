from typing import List

from pydantic import BaseModel

from constants.message_types import MessageTypes


class EntityMessage(BaseModel):
    body: list[tuple[int, int]]
    entity_id: str


class EntitiesMessage(BaseModel):
    type: str = MessageTypes.ENTITIES.value
    entities: List[EntityMessage]
