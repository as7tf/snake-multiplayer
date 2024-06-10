from enum import Enum, auto
import json
import random
import time
import traceback as tb

import os
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
                dt = self._clock.tick(self._tick_rate) / 1000
                if self.state == ClientGameState.IDLE:
                    self._idle()
                elif self.state == ClientGameState.CONNECTING:
                    self._connecting()
                elif self.state == ClientGameState.LOBBY:
                    self._lobby()
                elif self.state == ClientGameState.PLAYING:
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
        # time.sleep(1)
        command, quit_game = self.input_system.run()
        if quit_game:
            self.state = ClientGameState.EXITING
        self.rendering_system.run([Food((6, 0))])
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
        while True:
            print("--At lobby")
            while lobby_info is None:
                lobby_info = self.client.get_lobby_info()
                if lobby_info is not None:
                    break
                print("Waiting for lobby info...")
            else:
                print("Got lobby info!")
                print(lobby_info)
                break

        while True:
            print("Ready to play")
            time.sleep(2)

        
        # print("Lobby ready. Starting the game...")
        # self.game_state = GameState.PLAYING

    def _playing(self, dt):
        # Playing:
        #   Get server update
        #   Render entities
        #   Get player input, if any
        #   Send player command

        entities = []
        snake = Snake("ducks_gonna_fly", (6, 0))
        snake.movement_component.speed = 1
        entities.append(snake)
        entities.append(
            Food(
                (
                    random.randint(0, self.columns - 1),
                    random.randint(0, self.rows - 1),
                )
            )
        )

        while self.state != ClientGameState.EXITING:
            # TODO - Make input specific for the player's snake
            player_command, quit_game = self.input_system.run()  # Client side

            if quit_game == True:  # Client side
                # TODO - Disconnect from server
                self.client.disconnect()
                self.state = ClientGameState.EXITING
                break

            self.client.send_message(json.dumps(player_command))


            self.rendering_system.run(entities)  # Client side
        self._close()

    def _disconnecting(self):
        pass


if __name__ == "__main__":
    ClientLoop(10, 10, 20).run()