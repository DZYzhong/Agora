class FakeGraphStore:
    def __init__(self):
        self.relations: list[tuple[str, str, str]] = []

    def add_relation(self, from_id: str, relation: str, to_id: str) -> None:
        self.relations.append((from_id, relation, to_id))

    def neighbors(self, asset_id: str) -> list[str]:
        return [to_id for from_id, _, to_id in self.relations if from_id == asset_id]
