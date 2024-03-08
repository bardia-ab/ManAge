
class CR:
    __slots__ = ('name', 'tiles', 'HCS_Y_coord')

    def __init__(self, name: str, HCS_Y_coord: int):
        self.name           = name
        self.HCS_Y_coord    = HCS_Y_coord
        self.tiles          = []

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


