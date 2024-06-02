import json
import pygame
import random
import time
import traceback as tb

from entities.type import Food, Snake

from systems.network.client import GameClient
from systems.network.constants import GAME_PORT
from systems.player_input import InputSystem
from systems.render import RenderSystem

from game_instances.constants import GameState


class ClientLoop: 
    def __init__(self, rows, columns, cell_size):
        self.rows = rows
        self.columns = columns
        self.cell_size = cell_size

        coordinate_space = (self.rows, self.columns, self.cell_size)
        self.rendering_system = RenderSystem(*coordinate_space)
        self.input_system = InputSystem()

        self.client = GameClient("127.0.0.1", GAME_PORT)

        self._running = False
        self._game_state = None

        # TODO - Add UI system and execute after render system

    def setup(self):
        pygame.init()

        self.input_system.setup()
        self.rendering_system.setup()
        self.client.start()

        self.game_state = GameState.LOBBY
        self._running = True

    def close(self):
        self.client.stop()
        self._running = False
        pygame.quit()

    def run(self):
        self.setup()
        while self._running:
            self._run_current_state()

    def _run_current_state(self):
        state_method = getattr(self, f"{self.game_state.name.lower()}")
        state_method()

    def lobby(self):
        # Listening:
        #   Listen to connections
        #   Accept connections up to max players

        #   Choose player color randomly
        #   Wait for all players to have name and color set (Need to be different)

        #   Wait until all players are ready
        #   Block connections new connections and start preparing phase

        while self._running:
            try:
                # TODO - Wait for a ready message
                # TODO - Limit players
                # TODO - Block new connections after game start

                self.client.send_to_server(
                    {"name": "ducks"}
                )

                response = self.client.read_from_server()
                print(response)
                if response is not None:
                    response = json.loads(response)
                else:
                    time.sleep(1)
                    continue
                
                if "info" in response and response["info"] == "start":
                    break
                else:
                    print(f"Server response: {response}")

                time.sleep(1)
            except:
                tb.print_exc()
                self.close()
                return
        
        print("Lobby ready. Starting the game...")
        self.game_state = GameState.PLAYING

    def playing(self):
        # Playing
        #   Send initial game data
        #   Start countdown for game start
        #   Send game update
        #   Get players updates
        #   On game end, go back to lobby
        #   Or start a new game automatically

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

        while self._running:
            # TODO - Make input specific for the player's snake
            player_command, quit_game = self.input_system.run()  # Client side

            if quit_game == True:  # Client side
                self._running = False

            self.rendering_system.run(entities)  # Client side
        self.close()


if __name__ == "__main__":
    ClientLoop(10, 10, 20).run()