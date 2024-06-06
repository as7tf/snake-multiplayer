from pydantic import BaseModel

from constants.message_types import MessageTypes
from schemas.base import ServerResponse


class JoinLobbyMessage(BaseModel):
    type: str = MessageTypes.JOIN_LOBBY.value
    player_name: str


class JoinLobbyResponse(ServerResponse):
    type: str = MessageTypes.JOIN_LOBBY_RESPONSE.value
