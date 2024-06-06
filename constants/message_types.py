from enum import Enum


class MessageTypes(Enum):
    CONNECT = "connect"
    CONNECT_RESPONSE = "connect_response"
    JOIN_LOBBY = "join_lobby"
    JOIN_LOBBY_RESPONSE = "join_lobby_response"
    SERVER_UPDATE = "server_update"
    PLAYER_COMMAND = "player_command"
    ERROR = "error"
