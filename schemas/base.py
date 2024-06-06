from pydantic import BaseModel


class ServerResponse(BaseModel):
    status: int
    message: str
