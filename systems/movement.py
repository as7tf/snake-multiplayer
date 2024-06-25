from entities.base import Entity

from schemas.game import PlayerCommand
from systems.system import System


class MovementSystem(System):
    def setup(self):
        pass

    def run(self, entities: list[Entity], move_commands: list[PlayerCommand]):
        if not move_commands:
            for entity in entities:
                if entity.movement_component is not None:
                    entity.movement_component.move(None)
            return

        commanded_players = [command.player_name for command in move_commands]
        for entity in entities:
            if entity.movement_component is not None:
                if entity._entity_id in commanded_players:
                    player_command = next(
                        command
                        for command in move_commands
                        if command.player_name == entity._entity_id
                    )
                    entity.movement_component.move(player_command.command)
                else:
                    entity.movement_component.move(None)
