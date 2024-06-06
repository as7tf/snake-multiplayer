from pydantic import BaseModel
from typing import List

from constants.message_types import MessageTypes


class Position(BaseModel):
    x: float
    y: float


class PlayerUpdate(BaseModel):
    player_name: str
    position: Position


class PlayerCommand(BaseModel):
    type: str = MessageTypes.PLAYER_COMMAND.value
    command: str


class ServerUpdate(BaseModel):
    type: str = MessageTypes.SERVER_UPDATE.value
    players: List[PlayerUpdate]
    game_state: str
