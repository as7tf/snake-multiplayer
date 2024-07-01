from queue import Queue

from components.movement.snake import SnakeMovement
from components.player import PlayerComponent
from entities.base import EntityBetter
from schemas.game import PlayerCommand
from systems.system import System


class MovementSystem(System):
    def __init__(self, input_queue: Queue):
        self.input_queue = input_queue

    def setup(self):
        pass

    def run(self, entities: list[EntityBetter]):
        move_commands: list[PlayerCommand] = []
        if not self.input_queue.empty():
            move_commands = self.input_queue.get_nowait()

        if not move_commands:
            for entity in entities:
                # mc = entity.get_component(MovementComponent)
                mc = entity.get_component(SnakeMovement)
                if mc is not None:
                    mc.move(None)
            return

        commanded_players = [command.player_name for command in move_commands]
        for entity in entities:
            # mc = entity.get_component(MovementComponent)
            mc = entity.get_component(SnakeMovement)
            if mc is not None:
                pc = entity.get_component(PlayerComponent)
                if pc is not None and pc.name in commanded_players:
                    player_command = next(
                        command
                        for command in move_commands
                        if command.player_name == pc.name
                    )
                    mc.move(player_command.command)
                else:
                    mc.move(None)
