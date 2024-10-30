import re
import networkx as nx
from typing import Tuple, Set
from xil_res.node import Node as nd
import utility.config as cfg


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
        """This function returns the type of the Edge (pip|wire)

        :return: Edge type
        :rtype: str
        """
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
        """This function returns the neighbor of the head node in (u, v)

        :param G: Architecture Graph
        :type G: nx.DiGraph
        :return: the neighbor node
        :rtype: str
        """
        return next(G.neighbors(self.name[1]))

    def get_pred_u(self, G) -> str:
        """This function returns the predecessor of the tail node in (u, v)

        :param G: Architecture Graph
        :type G: nx.DiGraph
        :return: the predecessor node
        :rtype: str
        """
        return next(G.predecessors(self.name[0]))

    def get_reversed_pip(self, G: nx.DiGraph) -> Tuple[str] | None:
        """This function returns the reversed PIP if it exists in the specified graph

        :param G: Architecture Graph
        :type G: nx.DiGraph
        :return: Reversed PIP
        :rtype: Tuple[str] | None
        """
        reversed_pip = (self.name[1], self.name[0])
        if reversed_pip in G.edges:
            return reversed_pip
        else: return None

    def get_invalid_FF_route_thru_nodes(self, TC) -> Set[str]:
        """This function returns a set of CLB nodes which must be excluded from routing

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :return: A set of CLB nodes which must be blocked
        :rtype: Set[str]
        """
        block_nodes = set()
        try:
            CLB_node = next(filter(lambda node: nd.get_tile_type(node) == 'CLB', {self.pred_u, self.neigh_v}))
            LUT_name = f'{nd.get_tile(CLB_node)}/{nd.get_label(CLB_node)}LUT'
            LUT_primitive = TC.LUTs[LUT_name]
            occupancy = 2 if (cfg.LUT_in6_pattern.match(CLB_node) or cfg.MUXED_CLB_out_pattern.match((CLB_node))) else 1

            # Since CLB_out node is instantiated as a cell and only once is allowed, all others must be blocked
            if nd.get_clb_node_type(CLB_node) == 'CLB_out':
                block_nodes.update(TC.filter_nodes(get_clb_node_type='CLB_out'))
                block_nodes = block_nodes - {CLB_node}

            # Block all route-thrus
            if occupancy > LUT_primitive.capacity:
                block_nodes.update(filter(cfg.LUT_in_pattern.match, TC.G))

            # block LUT_in6 & CLB_muxed in the same clock group with the same label
            elif LUT_primitive.capacity == 1:
                attributes = {'get_clb_node_type': 'CLB_muxed',
                              'get_clock_group': nd.get_clock_group(self.neigh_v),
                              'get_label': nd.get_label(self.neigh_v)
                              }
                block_nodes.update(TC.filter_nodes(**attributes))

                attributes = {'get_clb_node_type': 'LUT_in',
                              'get_bel_index': 6,
                              'get_clock_group': nd.get_clock_group(self.pred_u),
                              'get_label': nd.get_label(self.pred_u)
                              }
                block_nodes.update(TC.filter_nodes(**attributes))

            # Block sources in the same clock group of the LUT primitive with the same label
            if LUT_primitive.capacity == occupancy:
                attributes = {'get_clb_node_type': 'FF_out',
                              'get_clock_group': LUT_primitive.clock_group,
                              'get_label': LUT_primitive.label
                              }

                block_nodes.update(TC.filter_nodes(**attributes))

        except StopIteration:
            block_nodes.update(filter(cfg.LUT_in_pattern.match, TC.G))

        return block_nodes

    def get_route_thru_flag(self) -> bool:
        """This function specifies if the PIP is immediately connected to a CLB or not

        :return: True|False
        :rtype: bool
        """
        route_thru_flag = any(map(lambda x: nd.get_tile_type(x) == 'CLB', {self.neigh_v, self.pred_u}))

        return route_thru_flag