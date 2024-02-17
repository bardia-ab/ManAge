import re
import networkx as nx
from typing import Tuple
from xil_res.node import Node as nd
import scripts.config as cfg


class Edge:
    __slots__ = ('name', 'idx')
    def __init__(self, edge: Tuple[str, str]):
        self.name = edge

    def __repr__(self):
        return f'{self.name[0]} -> {self.name[1]}'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash((self.name, ))

    def __getitem__(self, item):
        return self.name[item]

    def __len__(self):
        return len(self.name)

    def __iter__(self):
        self.idx = 0
        return self

    def __next__(self):
        if self.idx >= len(self):
            raise StopIteration
        else:
            self.idx += 1
            return self[self.idx - 1]

    def get_type(self):
        if nd.get_tile(self.name[0]) == nd.get_tile(self.name[1]):
            return 'pip'
        else:
            return 'wire'

class PIP(Edge):

    def __init__(self,  edge: Tuple[str, str], G: nx.DiGraph):
        super().__init__(edge)
        self.neigh_v        = self.get_neigh_v(G)
        self.pred_u         = self.get_pred_u(G)
        self.reversed_pip   = self.get_reversed_pip(G)

    def get_neigh_v(self, G) -> str:
        return next(G.neighbors(self.name[1]))

    def get_pred_u(self, G) -> str:
        return next(G.predecessors(self.name[0]))

    def get_reversed_pip(self, G: nx.DiGraph):
        reversed_pip = (self.name[1], self.name[0])
        if reversed_pip in G.edges:
            return reversed_pip
        else: return None

    def get_invalid_FF_route_thru_nodes(self, TC):
        block_nodes = set()
        LUT_primitive, LUT_capacity, occupancy = None, None, None
        if nd.get_clb_node_type(self.neigh_v) == 'LUT_in':
            #LUT_primitive = next(TC.filter_LUTs(name=nd.get_bel(self.neigh_v)))
            LUT_primitive = TC.LUTs[nd.get_bel(self.neigh_v)]
            LUT_capacity = LUT_primitive.capacity
            occupancy = 2 if (cfg.LUT_in6_pattern.match(self.neigh_v)) else 1

            if occupancy == 1:
                attributes = {'get_clb_node_type': 'CLB_muxed',
                              'get_clock_group': nd.get_clock_group(self.neigh_v),
                              'get_label': nd.get_label(self.neigh_v)
                              }
                block_nodes.update(TC.filter_nodes(**attributes))

        if nd.get_clb_node_type(self.pred_u) in {'CLB_out', 'CLB_muxed'}:
            #LUT_primitive = next(TC.filter_LUTs(name=nd.get_bel(self.pred_u)))
            LUT_primitive = TC.LUTs[nd.get_bel(self.pred_u)]
            LUT_capacity = LUT_primitive.capacity
            occupancy = 2 if (cfg.MUXED_CLB_out_pattern.match(self.pred_u)) else 1

            if occupancy == 1:
                attributes = {'get_clb_node_type': 'LUT_in',
                              'get_bel_index' : 6,
                              'get_clock_group': nd.get_clock_group(self.pred_u),
                              'get_label': nd.get_label(self.pred_u)
                              }
                block_nodes.update(TC.filter_nodes(**attributes))

        if LUT_primitive is None:
            block_nodes.update(filter(cfg.LUT_in_pattern.match, TC.G))
        else:
            if LUT_capacity == occupancy:
                attributes = {'get_clb_node_type': 'FF_out',
                              'get_clock_group': LUT_primitive.clock_group,
                              'get_label': LUT_primitive.label
                              }

                block_nodes.update(TC.filter_nodes(**attributes))

            elif occupancy > LUT_capacity:
                attributes = {'get_clb_node_type': 'LUT_in',
                              'get_clock_group': LUT_primitive.clock_group,
                              'get_label': LUT_primitive.label
                              }

                block_nodes.update(TC.filter_nodes(**attributes))

        return block_nodes

    def get_route_thru_flag(self):
        route_thru_flag = any(map(lambda x: nd.get_tile_type(x) == 'CLB', {self.neigh_v, self.pred_u}))

        return route_thru_flag