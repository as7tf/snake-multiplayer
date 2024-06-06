from constants.message_types import MessageTypes
from schemas.base import ServerResponse


class ErrorMessage(ServerResponse):
    type: str = MessageTypes.ERROR.value
