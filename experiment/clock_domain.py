import re, sys
import networkx as nx
from itertools import product
sys.path.insert(0, r'..\xil_res')
from xil_res.node import Node as nd
sys.path.insert(0, r'../scripts')
import scripts.config as cfg


class ClockDomain:

    def __init__(self):
        self.name = 'None'

    def __repr__(self):
        return f'CD(name={self.name})'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def clear(cls):
        cls.pattern_dict = {}

    def set(self, name: str, pattern: re.Pattern, src_sink_node: str, type: str):
        self.name           = name
        self.pattern        = pattern           # FF_in | FF_out
        self.src_sink_node  = src_sink_node     # s | t
        self.type           = type              # source | sink

    def is_unset(self):
        result = True if self.name == 'None' else False
        return result

    def assign_source_sink_nodes(self, G: nx.DiGraph()):
        pred_neigh_nodes = set(filter(self.pattern.match, G))
        edges = set()
        if self.type == 'source':
            edges = set(product({self.src_sink_node}, pred_neigh_nodes))
        if self.type == 'sink':
            edges = set(product(pred_neigh_nodes, {self.src_sink_node}))

        G.add_edges_from(edges, weight=0)



class ClockGroup:

    def __init__(self, name):
        self.name       = name
        self.FFs        = set()
        self.conflict   = set() # groups with which cannot be group mate, so they must have other CDs
        self._CD        = ClockDomain()

    def __repr__(self):
        return f'ClockGroup(name={self.name})'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    @property
    def is_free(self):
        return self.CD == ClockDomain()

    def reset(self, test_collection, path=None):
        self.remove_FF(test_collection, path)
        #self.conflict   = set()
        self._CD         = ClockDomain()

    def set(self, ff_node: str, test_collection):
        TC = test_collection.TC
        clock_domain = test_collection.get_clock_domain(ff_node)

        # globalize group_mates
        group_mates = nd.get_global_group_mates(TC.G, ff_node, self.name)

        # add FFs
        self.FFs.update({nd.get_bel(node) for node in group_mates})

        # set clock domain
        self.CD = clock_domain

        # remove the virtual_src_sink of the ff_node clock_group from conflicted_clock_groups_nodes
        self.remove_invalid_virtual_src_sink(TC.G)

        # remove the virtual_src_sink of other_CDs from the nodes of the clock_group
        self.remove_other_CDs_virtual_src_sink(test_collection)

    def remove_FF(self, test_collection, path):
        TC = test_collection.TC

        if path is None:
            # restore the virtual_src_sink of the clock_group from conflicted_clock_groups_nodes
            self.restore_invalid_virtual_src_sink(TC.G)

        # restore the virtual_src_sink of other_CDs from the nodes of the clock_group
        self.restore_other_CDs_virtual_src_sink(test_collection)

        # empty FFs
        self.FFs = set()


    def remove_invalid_virtual_src_sink(self, G: nx.DiGraph):
        edges = set()
        if self.CD.type == 'source':
            invalid_virtual_src_neighs = {neigh for neigh in G.neighbors(self.CD.src_sink_node) if
                                          nd.get_clock_group(neigh) in self.conflict}
            edges.update(set(product({self.CD.src_sink_node}, invalid_virtual_src_neighs)))
        if self.CD.type == 'sink':
            invalid_virtual_sink_preds = {pred for pred in G.predecessors(self.CD.src_sink_node) if
                                          nd.get_clock_group(pred) in self.conflict}
            edges.update(set(product(invalid_virtual_sink_preds, {self.CD.src_sink_node})))

        G.remove_edges_from(edges)

    def restore_invalid_virtual_src_sink(self, G: nx.DiGraph):
        edges = set()
        if self.CD.name == 'None':
            return

        desired_pattern_nodes = filter(self.CD.pattern.match, G)
        desired_conflict_CG_nodes = {node for node in desired_pattern_nodes if (nd.get_clock_group(node) in self.conflict)}
        if self.CD.type == 'source':
            edges.update(set(product({self.CD.src_sink_node}, desired_conflict_CG_nodes)))
        if self.CD.type == 'sink':
            edges.update(set(product(desired_conflict_CG_nodes, {self.CD.src_sink_node})))

        G.add_edges_from(edges)

    def remove_other_CDs_virtual_src_sink(self, test_collection):
        TC = test_collection.TC
        other_CDs = {CD for CD in test_collection.clock_domains if CD != self.CD}
        edges = set()
        for other_CD in other_CDs:
            edges.update({edge for edge in TC.G.in_edges(other_CD.src_sink_node) if nd.get_clock_group(edge[0]) == self.name})
            edges.update({edge for edge in TC.G.out_edges(other_CD.src_sink_node) if nd.get_clock_group(edge[1]) == self.name})

        TC.G.remove_edges_from(edges)

    def restore_other_CDs_virtual_src_sink(self, test_collection):
        TC = test_collection.TC
        other_CDs = {CD for CD in test_collection.clock_domains if CD != self.CD}
        edges = set()
        for other_CD in other_CDs:
            edges.update({edge for edge in TC.G.in_edges(other_CD.src_sink_node) if nd.get_clock_group(edge[0]) == self.name})
            edges.update({edge for edge in TC.G.out_edges(other_CD.src_sink_node) if nd.get_clock_group(edge[1]) == self.name})

        TC.G.add_edges_from(edges)

    @property
    def CD(self):
        return self._CD

    @CD.setter
    def CD(self, clock_domain: ClockDomain):
        if self.CD.is_unset():
            self._CD.set(clock_domain.name, clock_domain.pattern, clock_domain.src_sink_node, clock_domain.type)
        else:
            if clock_domain != self.CD:
                raise ValueError(f'CD: {clock_domain} cannot set to {self}')

    @staticmethod
    def CD_changed(current_CD, prev_CD):
        result = False
        for curr_CG, prev_CG in zip(current_CD, prev_CD):
            if curr_CG.CD != prev_CG.CD:
                result = True
                break

        return result