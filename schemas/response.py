from pydantic import BaseModel

from constants.message_types import MessageTypes


class ServerResponse(BaseModel):
    type: str = MessageTypes.SERVER_RESPONSE.value
    status: int
    message: str
