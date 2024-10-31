import copy
from heapq import heappush, heappop
from itertools import count, product
import networkx as nx
from typing import List, Set, Tuple
from xil_res.node import Node as nd
from xil_res.edge import PIP
import utility.config as cfg

class Path:

    def __init__(self):
        self.src        = None
        self.sink       = None
        self.type       = None
        self.error      = False
        self._nodes     = []
        self.subLUTs    = set()
        self.FFs        = set()
        self.prev_CD = []

    def __repr__(self):
        if self.nodes:
            return ' -> '.join(self.nodes)
        else:
            return '[]'

    def __eq__(self, other):
        return self.nodes == other.nodes

    def __hash__(self):
        return hash((self.nodes, ))

    def __getitem__(self, item):
        return self.nodes[item]

    def __setitem__(self, key, value: str):
        self.nodes[key] = value

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        self.idx = 0
        return self

    def __next__(self):
        if self.idx >= len(self):
            raise StopIteration
        else:
            self.idx += 1
            return self[self.idx - 1]

    def __add__(self, obj):
        path = Path()
        path.nodes = self.nodes + obj.nodes

        return path


    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, vertices: List[str]):
        for vertex in vertices:
            if '/' not in vertex:
                continue            #skip virtual nodes

            self._nodes.append(vertex)

    def get_edges(self) -> Set[Tuple[str, str]]:
        """This function extracts the edges of the path

        :return: Edges of the path
        :rtype: Set[Tuple[str, str]]
        """
        return set(zip(self.nodes, self.nodes[1:]))

    def get_pips(self) -> Set[Tuple[str, str]]:
        """This function extracts the PIPs of the path

        :return: PIPs of the path
        :rtype: Set[Tuple[str, str]]
        """
        return set(filter(lambda x: nd.get_tile(x[0]) == nd.get_tile(x[1]), self.get_edges()))

    def get_wires(self) -> Set[Tuple[str, str]]:
        """This function extracts the wires of the path

        :return: Wires of the path
        :rtype: Set[Tuple[str, str]]
        """
        return set(filter(lambda x: nd.get_tile(x[0]) != nd.get_tile(x[1]), self.get_edges()))

    def get_ports(self) -> List[str]:
        """This function extracts the port names of the path

        :return: Ports of the path
        :rtype: Set[Tuple[str, str]]
        """
        return [nd.get_port(node) for node in self.nodes]

    def get_LUT_in_type(self, LUT_in: str):
        """This function determines the type of the LUT input node (mid_node: route-thru, end_node: input of a NOT gate)

        :param LUT_in: LUT input node
        :type LUT_in: str
        :return: Type of the LUT input
        :rtype: str
        """
        type = 'end_node'
        if LUT_in != self[-1]:
            if cfg.Unregistered_CLB_out_pattern.match(self[self.nodes.index(LUT_in) + 1]):
                type = 'mid_node'

        return type

    def get_LUT_func(self, LUT_in: str):
        """This function determines the function of the LUT according to the type of the path and the LUT input node

        :param LUT_in: LUT input node
        :type LUT_in: str
        :raises ValueError: When the path type is invalid
        :return: LUT function
        :rtype: str
        """
        LUT_in_type = self.get_LUT_in_type(LUT_in)
        if LUT_in_type == 'mid_node':
            LUT_func = 'buffer'
        else:
            if self.type in ['path_out', 'main_path']:
                LUT_func = 'buffer'
            elif self.type == 'path_not':
                LUT_func = 'not'
            elif self.type == 'capture_launch':
                LUT_func = 'partial'
            elif self.type == 'capture_sample':
                LUT_func = 'xor'
            else:
                raise ValueError('Wrong Path_type!!!')

        return LUT_func

    def get_subLUTs(self, TC):
        """This function detects the usage of LUT nodes and creates respective subLUT objects

        :param TC: Minimal Test Configuration
        :type TC: MinConfig
        :return: All subLUT objects utilized by the path
        :rtype: Set[SubLUT]
        """
        subLUTs = set()
        for LUT_in in filter(lambda x: nd.get_primitive(x) == 'LUT', self):
            LUT_in_type = self.get_LUT_in_type(LUT_in)
            LUT_output = None if LUT_in_type == 'end_node' else self[self.nodes.index(LUT_in) + 1]
            LUT_func = self.get_LUT_func(LUT_in)

            sublut_name = f'{nd.get_tile(LUT_in)}/{nd.get_label(LUT_in)}{TC.get_subLUT_bel(LUT_output, LUT_in)}'
            subLUT = TC.subLUTs[sublut_name]
            subLUT.fill(LUT_output, LUT_func, LUT_in)
            subLUTs.add(subLUT)

        return subLUTs

    def get_FF_nodes(self):
        """This function extracts all FF nodes utilized by the path

        :return: FF nodes in the path
        :rtype: Set[str]
        """
        return {node for node in self if nd.get_primitive(node) == 'FF'}

    @staticmethod
    def path_finder(G, source, target, weight="weight", conflict_free=True, delimiter='/', dummy_nodes=[],
                    blocked_nodes=set()):
        if {source, target} & blocked_nodes:
            raise nx.NetworkXNoPath(f"No path between {source} and {target}.")

        if source not in G or target not in G:
            msg = f"Either source {source} or target {target} is not in G"
            raise nx.NodeNotFound(msg)

        if source == target:
            return [source]

        weight = Path.weight_function(G, weight)
        push = heappush
        pop = heappop
        # Init:  [Forward, Backward]
        dists = [{}, {}]  # dictionary of final distances
        paths = [{source: [source]}, {target: [target]}]  # dictionary of paths
        fringe = [[], []]  # heap of (distance, node) for choosing node to expand
        seen = [{source: 0}, {target: 0}]  # dict of distances to seen nodes
        c = count()
        # initialize fringe heap
        push(fringe[0], (0, next(c), source))
        push(fringe[1], (0, next(c), target))
        # neighs for extracting correct neighbor information
        if G.is_directed():
            neighs = [G._succ, G._pred]
        else:
            neighs = [G._adj, G._adj]
        # variables to hold shortest discovered path
        # finaldist = 1e30000
        finalpath = []
        finaldist = 0
        dir = 1
        while fringe[0] and fringe[1]:
            # choose direction
            # dir == 0 is forward direction and dir == 1 is back
            dir = 1 - dir
            # extract closest to expand
            (dist, _, v) = pop(fringe[dir])
            if v in dists[dir]:
                # Shortest path to v has already been found
                continue
            # update distance
            dists[dir][v] = dist  # equal to seen[dir][v]
            if v in dists[1 - dir]:
                # if we have scanned v in both directions we are done
                # we have now discovered the shortest path
                if not finalpath:
                    raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
                else:
                    finalpath = [node for node in finalpath if node not in dummy_nodes]
                    return finalpath

            for w, d in neighs[dir][v].items():
                # weight(v, w, d) for forward and weight(w, v, d) for back direction
                if w in blocked_nodes:
                    cost = None
                else:
                    cost = weight(v, w, d) if dir == 0 else weight(w, v, d)

                if cost is None:
                    continue
                vwLength = dists[dir][v] + cost
                if w in dists[dir]:
                    if vwLength < dists[dir][w]:
                        raise ValueError("Contradictory paths found: negative weights?")
                elif w not in seen[dir] or vwLength < seen[dir][w]:
                    # relaxing
                    seen[dir][w] = vwLength
                    push(fringe[dir], (vwLength, next(c), w))
                    paths[dir][w] = paths[dir][v] + [w]
                    if w in seen[0] and w in seen[1]:
                        # see if this path is better than the already
                        # discovered shortest path
                        totaldist = seen[0][w] + seen[1][w]
                        if finalpath == [] or finaldist > totaldist:
                            finaldist_prev = finaldist
                            finaldist = totaldist
                            revpath = paths[1][w][:]
                            revpath.reverse()
                            finalpath_prev = finalpath[:]
                            finalpath = paths[0][w] + revpath[1:]
                            if conflict_free:
                                ports_only = [node.split(delimiter)[1] for node in finalpath if (delimiter in node) and (node not in dummy_nodes)]
                                if len(ports_only) != len(set(ports_only)):
                                    finalpath = finalpath_prev
                                    finaldist = finaldist_prev

        raise nx.NetworkXNoPath(f"No path between {source} and {target}.")

    @staticmethod
    def weight_function(G, weight):
        """Returns a function that returns the weight of an edge.

        The returned function is specifically suitable for input to
        functions :func:`_dijkstra` and :func:`_bellman_ford_relaxation`.

        Parameters
        ----------
        G : NetworkX graph.

        weight : string or function
            If it is callable, `weight` itself is returned. If it is a string,
            it is assumed to be the name of the edge attribute that represents
            the weight of an edge. In that case, a function is returned that
            gets the edge weight according to the specified edge attribute.

        Returns
        -------
        function
            This function returns a callable that accepts exactly three subLUT_inputs:
            a node, an node adjacent to the first one, and the edge attribute
            dictionary for the eedge joining those nodes. That function returns
            a number representing the weight of an edge.

        If `G` is a multigraph, and `weight` is not callable, the
        minimum edge weight over all parallel edges is returned. If any edge
        does not have an attribute with key `weight`, it is assumed to
        have weight one.

        """
        if callable(weight):
            return weight
        # If the weight keyword argument is not callable, we assume it is a
        # string representing the edge attribute containing the weight of
        # the edge.
        if G.is_multigraph():
            return lambda u, v, d: min(attr.get(weight, 1) for attr in d.values())
        return lambda u, v, data: data.get(weight, 1)

class PathOut(Path):

    def __init__(self, src=cfg.pip_v):
        super().__init__()
        self.estimation = True
        self.src        = src
        self.sink       = cfg.virtual_sink_node
        self.type       = 'path_out'

    def get_blocked_nodes(self, TC, pips, first_order=False, main_path=None):
        """This function decides on the nodes that must be excluded from routing of the path_out

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :param pips: Uncovered PIPs
        :type pips: Set[Tuple[str, str]]
        :param first_order: Determines if the path_out is routed before path_in or not, defaults to False
        :type first_order: bool, optional
        :param main_path: The path for covering a PIP (in the phase of choosing the PIP that routing is done for estimation purpose this path is None), defaults to None
        :type main_path: MainPath|None
        :return: Set of nodes to be excluded from routing   
        :rtype: Set[str]
        """
        blocked_nodes = TC.blocked_nodes.copy()
        if main_path is not None:
            blocked_nodes.update(TC.get_global_nodes(main_path.pip[0]))

        if not self.estimation:
            uncovered_pips_u = {pip[0] for pip in TC.G.in_edges(self.src) if pip in pips}
            blocked_nodes.update(uncovered_pips_u)
            blocked_nodes.update(main_path.pip.get_invalid_FF_route_thru_nodes(TC))

        if not first_order:
            # long_pips
            common_nodes = main_path.common_nodes - set(main_path.path_in.nodes)
            blocked_nodes -= common_nodes

        return blocked_nodes

    def route(self, TC, pips, first_order=False, main_path=None):
        """This function finds a routing for the path_out

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :param pips: Uncovered PIPs
        :type pips: Set[Tuple[str, str]]
        :param first_order: Determines if the path_out is routed before path_in or not, defaults to False
        :type first_order: bool, optional
        :param main_path: The path for covering a PIP (in the phase of choosing the PIP that routing is done for estimation purpose this path is None), defaults to None
        :type main_path: MainPath|None, optional
        """
        path = []
        dummy_nodes = [self.src, self.sink] if self.estimation else [self.sink]
        blocked_nodes = self.get_blocked_nodes(TC, pips, first_order, main_path)
        attr = {'conflict_free': True, 'dummy_nodes': dummy_nodes, 'blocked_nodes': blocked_nodes}
        try:
            path = self.path_finder(TC.G, self.src, self.sink, **attr)
            # uncovered predecessors of the pip_v (pip_u) mustn't show up in path_out
            uncovered_pips_u = {pip[0] for pip in TC.G.in_edges(path[0]) if pip in pips}
            if uncovered_pips_u & set(path):
                blocked_nodes.update(uncovered_pips_u)

                try:
                    path = self.path_finder(TC.G, path[0], self.sink, **attr)
                    #self.nodes = path
                except nx.NetworkXNoPath:
                    path = []

        except nx.NetworkXNoPath:
            try:
                attr['conflict_free'] = False
                path = self.path_finder(TC.G, self.src, self.sink, **attr)
            except nx.NetworkXNoPath:
                pass

        if path:
            self.nodes = path
        else:
            self.error = True
            if cfg.print_message:
                print(f'No path found for {self.type}!')

class PathIn(Path):

    def __init__(self, sink: str):
        super().__init__()
        self.estimation = True
        self.src        = cfg.virtual_source_node
        self.sink       = sink
        self.type       = 'path_in'

    def get_blocked_nodes(self, TC, pips, path_out: PathOut, first_order=False, main_path=None):
        """This function decides on the nodes that must be excluded from routing of the path_in

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :param pips: Uncovered PIPs
        :type pips: Set[Tuple[str, str]]
        :param path_out: The path from the PIP's head to the sink
        :type path_out: PathOut
        :param first_order: Determines if the path_out is routed before path_in or not, defaults to False
        :type first_order: bool, optional
        :param main_path: The path for covering a PIP (in the phase of choosing the PIP that routing is done for estimation purpose this path is None), defaults to None
        :type main_path: MainPath|None, optional
        :return: Set of nodes to be excluded from routing   
        :rtype: Set[str]
        """
        blocked_nodes = TC.blocked_nodes.copy()
        if self.estimation:
            other_node_bidir_pip = set()
            covered_pips_u = {pip[0] for pip in TC.G.in_edges(self.sink) if pip not in pips} - {cfg.pip_v}
            path_out_nodes = set(path_out[1: ])
            blocked_nodes = blocked_nodes.union(covered_pips_u).union(path_out_nodes).union(other_node_bidir_pip)
        else:
            blocked_nodes.update(main_path.pip.get_invalid_FF_route_thru_nodes(TC))
            blocked_nodes.update(TC.get_global_nodes(main_path.pip[1]))
            common_nodes = main_path.common_nodes - set(main_path.path_out.nodes)
            blocked_nodes -= common_nodes

        return blocked_nodes

    def route(self, TC, pips, path_out: PathOut, first_order=False, main_path=None):
        """This function finds a routing for the path_in

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :param pips: Uncovered PIPs
        :type pips: Set[Tuple[str, str]]
        :param path_out: The path from the PIP's head to the sink
        :type path_out: PathOut
        :param first_order: Determines if the path_out is routed before path_in or not, defaults to False
        :type first_order: bool, optional
        :param main_path: The path for covering a PIP (in the phase of choosing the PIP that routing is done for estimation purpose this path is None), defaults to None
        :type main_path: MainPath|None, optional
        :return: Set of nodes to be excluded from routing   
        :rtype: Set[str]
        """
        dummy_nodes = [self.src]
        blocked_nodes = self.get_blocked_nodes(TC, pips, path_out, first_order, main_path)
        attr = {'conflict_free': True, 'dummy_nodes': dummy_nodes, 'blocked_nodes': blocked_nodes}

        try:
            path = self.path_finder(TC.G, self.src, self.sink, **attr)
            self.nodes = path
        except nx.NetworkXNoPath:
            try:
                attr['conflict_free'] = False
                path = self.path_finder(TC.G, self.src, self.sink, **attr)
                self.nodes = path
            except nx.NetworkXNoPath:
                self.error = True
                if cfg.print_message:
                    print(f'No path found for {self.type}!')

class MainPath(Path):

    def __init__(self, TC, path_in: PathIn, path_out: PathOut, pip: PIP):
        super().__init__()
        self.path_in        = path_in
        self.path_out       = path_out
        self.pip            = pip
        self.type           = 'main_path'
        self.common_nodes   = self.set_estimated_nodes_common_ports(TC)

    def set_estimated_nodes_common_ports(self, TC):
        """Since the paths must be relocated to achieve the coverage goal, nodes with the same ports are blocked.
        However, in certain cases, it might be required to utilize multiple nodes with the same port names (e.g. covering Long PIPs).
        In this case, these nodes with the same post names must be excluded from blocking during the routing of path_in and path_out.

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :return: A set of nodes with the same port name in estimated paths for path_in and path_out
        :rtype: Set[str]
        """
        common_ports = set(self.path_in.get_ports()) & set(self.path_out.get_ports())
        common_nodes = {node for node in self.path_in + self.path_out if nd.get_port(node) in common_ports}
        if cfg.block_mode == 'global':
            for node in common_nodes.copy():
                common_nodes.update(TC.get_global_nodes(node))

        return common_nodes

    def sort_paths(self):
        """This function decides on the order of the routing of path_in and path_out

        :return: Sorted path orders
        :rtype: List[PathIn|PathOut]
        """
        paths = []
        path_in = PathIn(self.pip[0])
        path_in.estimation = False
        path_out = PathOut(self.pip[1])
        path_out.estimation = False
        if self.pip.get_route_thru_flag():
            if nd.get_tile_type(self.pip.neigh_v) == 'CLB':
                paths.append(path_out)
                paths.append(path_in)
            else:
                paths.append(path_in)
                paths.append(path_out)

        elif len(self.path_out) < len(self.path_in):
            paths.append(path_out)
            paths.append(path_in)
        else:
            paths.append(path_in)
            paths.append(path_out)

        return paths


    def route(self, test_collection):
        """This function routes the path for covering a selected PIP

        :param test_collection: Test collection
        :type test_collection: TestCollection
        """
        if (self.path_in.sink != self.pip[0] and self.path_out.src != self.pip[1]):
            self.path_in.sink = self.pip[0]
            self.path_out.src = self.pip[1]

        TC = test_collection.TC
        pips = test_collection.queue
        self.prev_CD = copy.deepcopy(TC.CD)
        paths = self.sort_paths()
        for idx, path in enumerate(paths):
            if path.type == 'path_in':
                path.route(TC, pips, self.path_out, first_order=bool(1 - idx), main_path=self)
            else:
                path.route(TC, pips, first_order=bool(1 - idx), main_path=self)

            if path.error:
                self.error = True
                return

            path.prev_CD = copy.deepcopy(TC.CD)
            TC.fill_CUT(test_collection, path)

        self.path_in = next(path for path in paths if path.type == 'path_in')
        self.path_out = next(path for path in paths if path.type == 'path_out')
        self.nodes = self.path_in.nodes + self.path_out.nodes
        self.error = not(self.validate_buffers(TC))

    def validate_buffers(self, TC):
        """This function verifies that the conditions for route-thrus in the main path

        :param TC: Minimal test configuration
        :type TC: MinConfig
        :return: True|False
        :rtype: bool
        """
        result = False
        if len(list(filter(lambda node: cfg.CLB_out_pattern.match(node), self.nodes))) <= 1:
            result = True
        else:
            edges = [edge for edge in self.get_edges() if any(map(lambda node: cfg.CLB_out_pattern.match(node), edge))]
            for edge in edges:
                TC.G.get_edge_data(*edge)['weight'] += 25

        return result

class NotPath(Path):
    def __init__(self):
        super().__init__()
        self.src    = cfg.not_virtual_source_node
        self.sink   = cfg.not_virtual_sink_node
        self.type   = 'path_not'

    def assign_virtual_source_sink(self, G: nx.DiGraph, main_path:MainPath):
        """This function assigns virtual nodes to the sources and sinks of the Not path

        :param G: Architecture graph
        :type G: nx.DiGraph
        :param main_path: The path for covering a PIP
        :type main_path: MainPath
        """
        tile = nd.get_tile(main_path[0])
        label = nd.get_label(main_path[0])
        sources = (node for node in main_path if nd.get_clb_node_type(node) != 'LUT_in')
        sinks = (nd.get_LUT_input(tile, label, index) for index in range(6))
        edges = set(product({self.src}, sources))
        edges.update(set(product(sinks, {self.sink})))
        G.add_edges_from(edges)

    def remove_virtual_source_sink(self, G: nx.DiGraph):
        """This function removes the assigned virtual nodes from the architecture graph

        :param G: Architecture graph
        :type G: nx.DiGraph
        """
        G.remove_nodes_from({self.src, self.sink})

    def get_blocked_nodes(self, test_collection):
        """This function decides on the nodes to be excluded from the routing of the Not path

        :param test_collection: Test collection
        :type test_collection: TestCollection
        :return: A set of nodes to be excluded from routing
        :rtype: Set[str]
        """
        device = test_collection.device
        TC = test_collection.TC
        cut = TC.CUTs[-1]

        # Not path mustn't have route-thrus
        route_thrus = filter(lambda x: cfg.Unregistered_CLB_out_pattern.match(x), TC.G)

        # sharing the LUT_in is not allowed
        main_path_nodes = {node for node in cut.main_path if nd.get_clb_node_type(node) != 'LUT_in'}

        blocked_nodes = device.blocking_nodes(TC).union(TC.blocked_nodes) - main_path_nodes
        blocked_nodes.update(route_thrus)
        return blocked_nodes

    def route(self, test_collection):
        """This function finds a routing for the Not path

        :param test_collection: Test collection
        :type test_collection: TestCollection
        :raises nx.NetworkXNoPath: When no routing is found
        """
        device = test_collection.device
        TC = test_collection.TC
        cut = TC.CUTs[-1]
        self.prev_CD = copy.deepcopy(TC.CD)
        self.assign_virtual_source_sink(TC.G, cut.main_path)
        dummy_nodes = [self.src, self.sink]
        blocked_nodes = self.get_blocked_nodes(test_collection)
        attr = {'weight': device.weight,'conflict_free': True, 'dummy_nodes': dummy_nodes, 'blocked_nodes': blocked_nodes}
        try:
            path = self.path_finder(TC.G, self.src, self.sink, **attr)
            self.nodes = path
        except nx.NetworkXNoPath:
            try:
                if len(TC.CUTs) < (cfg.max_capacity / 8):
                    blocked_nodes -= device.blocking_nodes(TC)
                    path = self.path_finder(TC.G, self.src, self.sink, **attr)
                    self.nodes = path
                else:
                    raise nx.NetworkXNoPath

            except nx.NetworkXNoPath:
                try:
                    attr['conflict_free'] = False
                    path = self.path_finder(TC.G, self.src, self.sink, **attr)
                    self.nodes = path
                except nx.NetworkXNoPath:
                    self.error = True
                    if cfg.print_message:
                        print(f'No path found for {self.type}!')

        self.remove_virtual_source_sink(TC.G)

        # validate branch
        self.error = not(self.validate_inv_branch())

        if not self.error:
            TC.fill_CUT(test_collection, self)

    def validate_inv_branch(self):
        """This function validates that a LUT input is not shared between two paths of a CUT as this case cannot be constrained by Vivado

        :return: True|False
        :rtype: bool
        """
        result = False
        if self.nodes and not cfg.LUT_in_pattern.match(self.nodes[0]):
            result = True

        return result