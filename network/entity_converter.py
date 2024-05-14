from game_logic.entity_manager import EntityManager


class EntityConverter:
    def __init__(self, entity_translate: dict) -> None:
        self._entity_translate = entity_translate

    def translate_packets_to_entities(self, game_packets: list[dict]) -> EntityManager:
        entity_manager = EntityManager()

        for entity_packet in game_packets:
            entity_class = self._entity_translate[entity_packet["entity_type"]]
            entity_manager.add_entity(entity_class(entity_packet["entity_id"]))
        return entity_manager

    def translate_entities_to_packets(self, entity_manager: EntityManager):
        game_packets = [{}]

        # TODO - Translate game entities to game packets

        return game_packets
