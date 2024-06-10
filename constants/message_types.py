from enum import Enum


class MessageTypes(Enum):
    # Client side
    JOIN_LOBBY = "join_lobby"
    LOBBY_INFO = "lobby_info"
    CHOOSE_COLOR = "choose_color"
    SERVER_UPDATE = "server_update"
    PLAYER_COMMAND = "player_command"

    # Server side
    LOBBY_INFO_RESPONSE = "lobby_info_response"
    SERVER_RESPONSE = "server_response"
