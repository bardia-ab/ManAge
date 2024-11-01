import time
import re
from pathlib import Path
import networkx as nx
from dataclasses import dataclass, field
from itertools import product
from typing import List, Set
from tqdm import tqdm
from joblib import Parallel, delayed

from xil_res.architecture import Arch
from xil_res.node import Node as nd
from xil_res.minimal_config import MinConfig
from xil_res.clock_domain import ClockDomain, ClockGroup
import utility.config as cfg
import utility.utility_functions as util

@dataclass
class TestCollection:
    """
    This class provides a collection of objects required for creating Minimal Test Configurations.
    """
    iteration           :   int
    origin              :   str
    minimal_config_dir  :   str
    prev_config_dir     :   str             = field(default=None)
    prev_config_files   :   List            = field(default_factory = list)
    queue               :   set             = field(default_factory = Set)
    TC                  :   MinConfig       = field(default = None)
    device              :   Arch            = field(default = None)
    clock_domains       :   List            = field(default_factory = list)
    clock_groups        :   List            = field(default_factory = list)
    pbar                :   tqdm            = field(default = None)
    n_pips              :   int             = field(default = 0)
    TC_idx              :   int             = field(default=0)

    def __post_init__(self):
        if self.prev_config_dir is not None:
            config_files = list(Path(self.prev_config_dir).glob('TC*'))
            TC_num_CUTs = Parallel(n_jobs=cfg.n_jobs)(delayed(self.get_num_occupied_CUTs)(config_file)
                                                                  for config_file in config_files)
            self.sort_prev_TCs(TC_num_CUTs)
            rloc_collection = util.load_data(str(self.prev_config_dir), 'rloc_collection.data')
            if f'INT_{self.origin}' in rloc_collection.covered_pips:
                covered_pips = {tuple(map(lambda node: f'INT_{self.origin}/{node}', pip)) for pip in rloc_collection.covered_pips[f'INT_{self.origin}']}
            else:
                covered_pips = set()

            self.queue = self.queue - covered_pips

            self.max_capacity = cfg.max_capacity
            self.long_TC_process_time = cfg.long_TC_process_time

            self.TC_idx = len(config_files) - 1 # it is incremented in store_TC at the storing of the last config_file

        util.create_folder(self.minimal_config_dir)
        self.create_clock_domains()
        self.create_pbar()
        self.n_pips = len(self.queue)

    def __getstate__(self):
        state = self.__dict__.copy()  # Copy the dict to avoid modifying the original
        # Remove the attribute that should not be pickled
        del state['pbar']
        del state['device']
        #del state['TC']
        return state

    def __setstate__(self, state):
        # Restore instance attributes (temp_value will be missing)
        self.__dict__.update(state)


    def create_pbar(self):
        """This function creates a progress bar
        """
        custom_format = "{desc}{bar} {percentage:.0f}% | {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] >> {postfix}"
        self.pbar = tqdm(total=len(self.queue), bar_format=custom_format, desc="\033[91m")

    def get_clock_domain(self, node):
        """This function returns the ClockDomain object for the specified node (This node must match the regex pattern specified in the config.yaml file)

        :param node: A node whose clock domain is of interest
        :type node: str
        :return: Respective clcok domain object
        :rtype: ClockDomain
        """
        return next(CD for CD in self.clock_domains if CD.pattern.match(node))

    def get_clock_group(self, clock_group: str):
        """This function returns the ClockGroup object of the specified clock group name

        :param clock_group: Desire clock group name
        :type clock_group: str
        :return: Respective group name object 
        :rtype: ClockGroup
        """
        return next(cg for cg in self.clock_groups if cg.name == clock_group)

    def create_clock_domains(self):
        """This function creates clock domain and clock group objects specified in the config.yaml file
        """
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

    def get_num_occupied_CUTs(self, config_file):
        """This function returns the number of created CUTs at the current origin (used for iterations > 1)

        :param config_file: The path to the Config file
        :type config_file: pathlib.Path
        :return: A tuple including the specified config_file and the number of occupied CUTs at the current origin
        :rtype: Tuple
        """
        TC = util.load_data(str(config_file.parent), config_file.name)
        num_CUTs = len([cut for cut in TC.D_CUTs if cut.origin == self.origin])

        return (config_file, num_CUTs)

    def sort_prev_TCs(self, TC_num_CUTs):
        """This function sorts the configurations created in previous iterations based on the number of existing CUTs at the current origin

        :param TC_num_CUTs: A collection of configurations and the number of their occupied CUTs at the current origin
        :type TC_num_CUTs: List
        """
        TC_num_CUTs.sort(key=lambda x: x[1])
        self.prev_config_files = [tup[0] for tup in TC_num_CUTs]

    def create_TC(self, device: Arch):
        """This function creates a new MinConfig object or load the existing one in iterations > 1

        :param device: Device under test
        :type device: Arch
        """
        if self.prev_config_files:
            prev_config_file = self.prev_config_files.pop(0)
            prev_TC = util.load_data(str(prev_config_file.parent), prev_config_file.name)

            # Modify long_TC_process_time & max_capacity
            num_existing_CUTs = len([cut for cut in prev_TC.D_CUTs if cut.origin == self.origin])
            cfg.long_TC_process_time = self.long_TC_process_time - num_existing_CUTs * (cfg.long_TC_process_time / self.max_capacity)
            cfg.max_capacity = self.max_capacity - num_existing_CUTs

            #Modify TC_idx
            TC_idx = int(re.findall('\d+', prev_config_file.stem)[0])

        else:
            if self.prev_config_dir:
                cfg.max_capacity = self.max_capacity
                cfg.long_TC_process_time = self.long_TC_process_time

            prev_TC = None
            TC_idx = self.TC_idx

        self.TC = MinConfig(device, TC_idx, prev_TC)
        self.device = device

        # reset Clock Groups
        for CG in self.clock_groups:
            CG.clear()

        # assign virtual source and sink nodes
        for CD in self.clock_domains:
            CD.assign_source_sink_nodes(self.TC.G)

        if self.prev_config_files:
            self.remove_virtual_nodes()
        else:
            self.TC.CD = self.clock_groups

        # assign pip_v node
        self.assign_pip_v_node(self.TC.G)

    def remove_virtual_nodes(self):
        for CG in self.TC.CD:
            if CG.is_free:
                continue

            # update FFs
            ff = list(CG.FFs)[0]
            CG.FFs = set(nd.get_global_group_mates(self.TC.G, ff, CG.name))

        for CG in self.TC.CD:
            if CG.is_free:
                continue

            # remove the virtual_src_sink of the clock groups' clock domain from conflicting clock groups' FF nodes
            CG.remove_virtual_node_from_conflict_FFs(self)

            # remove the virtual_src_sink of other_CDs from the FF nodes of the clock_group
            CG.remove_other_CDs_virtual_node_from_FFs(self)

    def assign_pip_v_node(self, G: nx.DiGraph):
        """This function assigns a virtual node to the head of PIPs

        :param G: Architecture graph
        :type G: nx.DiGraph
        """
        pip_v_nodes = {pip[1] for pip in self.queue}
        edges = set(product({cfg.pip_v}, pip_v_nodes))
        G.add_edges_from(edges, weight=0)

    def clean_pip_v_node(self, G: nx.DiGraph):
        """This function removes the edge between the virtual node and the head of covered PIPs

        :param G: Architecture graph
        :type G: nx.DiGraph
        """
        pip_v_nodes = {pip[1] for pip in self.queue}
        excess_out_nodes = set(G.neighbors(cfg.pip_v)) - pip_v_nodes
        excess_out_node_edges = set(product({cfg.pip_v}, excess_out_nodes))
        G.remove_edges_from(excess_out_node_edges)

    def finish_TC(self, TC: MinConfig):
        """This function determines if the the minimal configuration must be terminated or not

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :return: True|False
        :rtype: bool
        """
        result = True
        coverage = (self.n_pips - len(self.queue)) / self.n_pips
        source_node = {CD.src_sink_node for CD in self.clock_domains if CD.type == 'source'}.pop()
        sink_node = {CD.src_sink_node for CD in self.clock_domains if CD.type == 'sink'}.pop()
        cond_capacity = (cfg.max_capacity - len(TC.CUTs)) <= 0
        cond_exec_time = time.time() - TC.start_TC_time > (cfg.long_TC_process_time + (cfg.long_TC_process_time // 10) * (coverage // 0.3))
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

    def update_coverage(self):
        """This function updates the number of covered PIPs
        """
        cut = self.TC.CUTs[-1]
        prior_length = len(self.queue)
        self.queue -= cut.get_covered_pips()
        current_length = len(self.queue)
        self.pbar.set_description(f'TC{self.TC.TC_idx} >> CUT{len(self.TC.CUTs)} >> Remaining PIPs')
        self.pbar.set_postfix_str(f'{cut.main_path.pip}')
        self.pbar.update(prior_length - current_length)

    def store_TC(self):
        """This function stores the created minimal test configuration
        """
        util.store_data(self.minimal_config_dir, f'TC{self.TC.TC_idx}.data', self.TC)
        if not self.prev_config_files:
            self.TC_idx += 1