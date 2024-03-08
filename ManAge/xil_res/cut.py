import networkx as nx
from xil_res.node import Node as nd
from xil_res.path import Path

class CUT:
    __slots__ = ('origin', 'index', 'main_path', 'paths', 'FFs', 'subLUTs', 'G')
    def __init__(self, origin, cut_index):
        self.origin     = origin
        self.index      = cut_index
        self.main_path  = Path()
        self.paths      = []
        self.FFs        = set()
        self.subLUTs    = set()
        self.G          = nx.DiGraph()

    def __repr__(self):
        return f'CUT{self.index}'

    def __eq__(self, other):
        return type(self) == type(other) and self.origin == other.origin and self.index == other.index

    def __hash__(self):
        return hash((self.origin, self.index))

    def add_path(self, path):
        self.paths.append(path)
        self.G.add_edges_from(path.get_edges())

    def get_covered_pips(self):
        tile = f'INT_{self.origin}'
        return set(filter(lambda edge: nd.get_tile(edge[0]) == tile, self.main_path.get_pips()))