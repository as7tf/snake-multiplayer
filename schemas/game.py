from typing import List

from pydantic import BaseModel

from constants.message_types import MessageTypes
from schemas.response import ServerResponse


class GameReady(BaseModel):
    type: str = MessageTypes.GAME_READY.value


class Position(BaseModel):
    x: float
    y: float


class PlayerUpdate(BaseModel):
    player_name: str
    position: Position


class PlayerCommand(BaseModel):
    type: str = MessageTypes.PLAYER_COMMAND.value
    player_name: str
    command: dict


class ServerUpdate(ServerResponse):
    type: str = MessageTypes.SERVER_UPDATE.value
    players: List[PlayerUpdate]
    game_state: str
