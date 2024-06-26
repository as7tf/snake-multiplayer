from typing import List

from pydantic import BaseModel

from constants.message_types import MessageTypes
from schemas.response import ServerResponse


# Client requests
class JoinLobbyRequest(BaseModel):
    type: str = MessageTypes.JOIN_LOBBY.value
    player_name: str


class LobbyInfoRequest(BaseModel):
    type: str = MessageTypes.LOBBY_INFO.value


class PlayerConfigRequest(BaseModel):
    type: str = MessageTypes.CHOOSE_COLOR.value
    color: str


# Server responses
class LobbyInfoResponse(ServerResponse):
    type: str = MessageTypes.LOBBY_INFO_RESPONSE.value
    player_names: List[str]
    highscores: List[str]
    available_colors: List[str]
