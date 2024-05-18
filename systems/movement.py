from entities.entity import Entity

from systems.system import System


class MovementSystem(System):
    def setup(self):
        pass

    def run(self, entities: list[Entity], move_command):
        for entity in entities:
            if entity.movement_component is not None:
                entity.movement_component.move(move_command)
