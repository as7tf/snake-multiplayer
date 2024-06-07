from enum import Enum


class MessageTypes(Enum):
    CONNECT = "connect"
    CONNECT_RESPONSE = "connect_response"
    JOIN_LOBBY = "join_lobby"
    JOIN_LOBBY_RESPONSE = "join_lobby_response"
    LOBBY_INFO = "lobby_info"
    LOBBY_INFO_RESPONSE = "lobby_info_response"
    CHOOSE_COLOR = "choose_color"
    SERVER_UPDATE = "server_update"
    PLAYER_COMMAND = "player_command"
    ERROR = "error"
