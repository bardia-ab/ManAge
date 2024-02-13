import sys, time
import networkx as nx
from dataclasses import dataclass, field
from itertools import product
from typing import List, Set
from tqdm import tqdm
#sys.path.insert(0, r'..\xil_res')
#sys.path.insert(0, r'..\scripts')
from xil_res.architecture import Arch
from xil_res.minimal_config import MinConfig
from experiment.clock_domain import ClockDomain, ClockGroup
import scripts.config as cfg

@dataclass
class TestCollection:
    iteration       :   int
    desired_tile    :   str
    queue           :   List             = field(default_factory = list)
    TC              :   MinConfig       = field(default = None)
    device          :   Arch            = field(default = None)
    clock_domains   :   List            = field(default_factory = list)
    clock_groups    :   List            = field(default_factory = list)
    pbar            :   tqdm            = field(default = None)
    n_pips          :   int             = field(default = 0)
    TC_idx          :   int             = field(default=0)
    covered_pips    :   list            = field(default_factory=list)

    def initialize(self):
        self.create_clock_domains()
        self.create_pbar()
        self.n_pips = len(self.queue)

    def create_pbar(self):
        self.pbar = tqdm(total=len(self.queue))

    def get_clock_domain(self, node):
        return next(CD for CD in self.clock_domains if CD.pattern.match(node))

    def get_clock_group(self, clock_group: str):
        return next(cg for cg in self.clock_groups if cg.name == clock_group)

    def create_clock_domains(self):
        # initialize clock domains
        for name, pattern in cfg.clock_domains.items():
            type = cfg.clock_domain_types[name]
            src_sink_node = cfg.src_sink_node[name]
            clock_domain = ClockDomain()
            clock_domain.set(name, pattern, src_sink_node, type)
            self.clock_domains.append(clock_domain)

        # initialize clock groups
        for CG, conflict_CG in cfg.clock_groups.items():
            clock_group = ClockGroup(CG)
            clock_group.conflict.add(conflict_CG)
            self.clock_groups.append(clock_group)

    def create_TC(self, device: Arch):
        TC = MinConfig(device, self.TC_idx)
        self.TC = TC
        self.device = device

        # reset Clock Groups
        for CG in self.clock_groups:
            CG.reset(self)

        # assign virtual source and sink nodes
        for CD in self.clock_domains:
            CD.assign_source_sink_nodes(TC.G)

        TC.CD = {clock_group: clock_group.CD for clock_group in self.clock_groups}

        # assign pip_v node
        self.assign_pip_v_node(TC.G)

    def assign_pip_v_node(self, G: nx.DiGraph):
        pip_v_nodes = {pip[1] for pip in self.queue}
        edges = set(product({cfg.pip_v}, pip_v_nodes))
        G.add_edges_from(edges, weight=0)

    def clean_pip_v_node(self, G: nx.DiGraph):
        pip_v_nodes = {pip[1] for pip in self.queue}
        excess_out_nodes = set(G.neighbors(cfg.pip_v)) - pip_v_nodes
        excess_out_node_edges = set(product({cfg.pip_v}, excess_out_nodes))
        G.remove_edges_from(excess_out_node_edges)

    def finish_TC(self, TC: MinConfig):
        result = True
        coverage = (self.n_pips - len(self.queue)) / len(self.queue)
        source_node = {CD.src_sink_node for CD in self.clock_domains if CD.type == 'source'}.pop()
        sink_node = {CD.src_sink_node for CD in self.clock_domains if CD.type == 'sink'}.pop()
        cond_capacity = (cfg.max_capacity - len(TC.CUTs)) <= 0
        cond_exec_time = time.time() - TC.start_TC_time > (cfg.long_TC_process_time + 15 * (coverage // 0.3))
        cond_empty_queue = not self.queue
        try:
            cond_path_existance = nx.has_path(TC.G, source_node, sink_node)
        except nx.exception.NodeNotFound:
            cond_path_existance = False

        if cond_capacity:
            self.pbar.set_postfix_str('Capacity is Full!')
        elif cond_exec_time:
            self.pbar.set_postfix_str('Long TC Process Time!')
        elif cond_empty_queue:
            self.pbar.set_postfix_str('Queue is empty!')
        elif not cond_path_existance:
            self.pbar.set_postfix_str('No path between sourse and sink!')
        else:
            result = False

        return result