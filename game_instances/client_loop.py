from enum import Enum, auto
import json
import random
import time
import traceback as tb

import os

from schemas.entities import EntityMessage
from utils.timer import Timer, print_func_time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

from entities.type import Food, Snake

from systems.network.client import SnakeClient
from systems.network.constants import GAME_PORT
from systems.player_input import InputSystem
from systems.render import RenderSystem


class ClientGameState(Enum):
    IDLE = auto()
    CONNECTING = auto()
    LOBBY = auto()
    PLAYING = auto()
    DISCONNECTING = auto()
    EXITING = auto()


class ClientLoop:
    def __init__(self, rows, columns, cell_size, tick_rate=60):
        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size

        coordinate_space = (self.rows, self.columns, self.cell_size)
        self.rendering_system = RenderSystem(*coordinate_space)
        self.input_system = InputSystem()

        self._running = False
        self._clock = None
        self._tick_rate = tick_rate
        self.state = None

        self.client = SnakeClient(self)

        # TODO - Add UI system and execute after render system

    def run(self):
        self._setup()
        try:
            while self.state != ClientGameState.EXITING:
                if self.state == ClientGameState.IDLE:
                    self._idle()
                elif self.state == ClientGameState.CONNECTING:
                    self._connecting()
                elif self.state == ClientGameState.LOBBY:
                    self._lobby()
                elif self.state == ClientGameState.PLAYING:
                    dt = self._clock.tick(self._tick_rate) / 1000
                    self._playing(dt)
                elif self.state == ClientGameState.DISCONNECTING:
                    self._disconnecting()
        except KeyboardInterrupt:
            pass
        self._close()

    def _setup(self):
        pygame.init()
        self._clock = pygame.time.Clock()

        self.input_system.setup()
        self.rendering_system.setup()

        self.state = ClientGameState.IDLE
        self._running = True

    def _close(self):
        pygame.quit()

    def _idle(self):
        # TODO - Main menu UI
        self.state = ClientGameState.CONNECTING

    def _connecting(self):
        # Connecting:
        #   Connect to server
        #   Send player name
        #   Continue to lobby if server approved
        
        print("--Connecting to server...")
        connected = self.client.connect_to_server("localhost", GAME_PORT)
        if not connected:
            print("Could not connect to server")
            self.state = ClientGameState.IDLE
            return

        while True:
            lobby_joined = self.client.try_lobby_join("ducksgonnafly")
            if lobby_joined:
                break
            else:
                print("Could not join lobby")
                time.sleep(1)
        print("Lobby joined")
        self.state = ClientGameState.LOBBY

    def _lobby(self):
        # Lobby:
        #   Choose available colors
        #   Press ready and wait for game start
        #   Get game initial state
        #   Get game countdown

        lobby_info = None
        sleep_time = 0.5
        print("--At lobby")
        while lobby_info is None:
            timer = Timer()
            lobby_info = self.client.get_lobby_info()
            print("Lobby info:", lobby_info)
            time.sleep(max(0, sleep_time - timer.elapsed_sec()))
            if lobby_info is not None:
                break
            print("Waiting for lobby info...")
        while True:
            if self.client.wait_game_start():
                break
            print("Waiting for game start...")

        print("Lobby ready. Starting the game...")
        self.state = ClientGameState.PLAYING

    def _playing(self, dt):
        # Playing:
        #   Get server update
        #   Render entities
        #   Get player input, if any
        #   Send player command

        def deserialize_entities(entities: list[EntityMessage]):
            deserialized_entities = []
            for entity in entities:
                if entity.entity_id == "snake":
                    snake = Snake("ducks_gonna_fly", (0, 0))
                    snake.body_component.segments = entity.body
                    deserialized_entities.append(snake)
                elif entity.entity_id == "food":
                    food = Food((0, 0))
                    food.body_component.segments = entity.body
                    deserialized_entities.append(food)
            return deserialized_entities

        # TODO - Make input specific for the player's snake
        player_command, quit_game = self.input_system.run()  # Client side

        if quit_game == True:  # Client side
            self.client.disconnect_from_server()
            self.state = ClientGameState.EXITING
            return

        if player_command is not None:
            self.client.send_player_command(player_command)

        entities = self.client.get_server_update()
        if entities is not None:
            entities = deserialize_entities(entities)

            self.rendering_system.run(entities)  # Client side

    def _disconnecting(self):
        pass


if __name__ == "__main__":
    ClientLoop(10, 10, 20).run()
