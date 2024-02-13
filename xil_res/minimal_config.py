import copy, time, sys
import re
from itertools import product
import networkx as nx
#sys.path.insert(0, r'..\scripts')
import scripts.config as cfg
import scripts.utility_functions as util
from experiment.clock_domain import ClockGroup, ClockDomain
from xil_res.node import Node as nd
from xil_res.architecture import Arch
from xil_res.path import PathIn, PathOut, MainPath, NotPath
from xil_res.cut import CUT
from xil_res.edge import PIP
from joblib import Parallel, delayed

class MinConfig:

    __slots__ = ('G', 'TC_idx', 'G_TC', 'blocked_nodes', 'FFs', 'LUTs', 'subLUTs', 'CD', 'CUTs', 'tried_pips', 'start_TC_time')
    def __init__(self, device, TC_idx):
        self.G                      = copy.deepcopy(device.G)
        self.TC_idx                 = TC_idx
        self.G_TC                   = nx.DiGraph()
        self.blocked_nodes          = set()
        self.FFs                    = device.get_FFs()
        self.LUTs                   = device.get_LUTs()
        self.subLUTs                = device.get_subLUTs()
        self.CD                     = {}     # set in test_collection
        self.CUTs                   = []
        self.tried_pips             = set()
        self.start_TC_time          = time.time()


    def __repr__(self):
        return f'TC{self.TC_idx}'

    def filter_nodes(self, **attributes):
        return (node for node in self.G if all(nd.__dict__[attr](node) == value for attr, value in attributes.items()))

    def filter_LUTs(self, **attributes):
        return (LUT_obj for LUT_obj in self.LUTs if all(getattr(LUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_subLUTs(self, **attributes):
        return (subLUT_obj for subLUT_obj in self.subLUTs if all(getattr(subLUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_FFs(self, **attributes):
        return (FF_obj for FF_obj in self.FFs if all(getattr(FF_obj, attr) == value for attr, value in attributes.items()))

    def get_global_nodes(self, node: str):
        pattern = nd.get_global_pattern(node)
        return set(filter(lambda node: re.match(pattern, node), self.G))

    def get_global_edges(self, edge):
        pattern_u = nd.get_global_pattern(edge[0])
        pattern_v = nd.get_global_pattern(edge[1])
        return set(filter(lambda e: re.match(pattern_u, e[0]) and re.match(pattern_v, e[1]), self.G.edges))

    ########## CUT ###############
    def create_CUT(self, coord):
        cut_index = len(self.CUTs)
        cut = CUT(coord, cut_index)
        self.CUTs.append(cut)

    def fill_CUT(self, test_collection, path):
        cut = self.CUTs[-1]
        # 1- set CD
        self.set_CDs(test_collection, path)
        # 3- specify subluts & update path subluts. it also adds the sublut into LUT
        self.fill_LUTs(path)
        self.fill_FFs(path)
        # 4- Fill the CUT with path
        cut.add_path(path)
        # 7- set FFs & SubLUTs usage
        if cfg.block_mode == 'global':
            self.set_global_subLUTs(test_collection, path.subLUTs)
            self.set_global_FFs(test_collection, path.FFs)
        # 2- block path
        self.block_path(path)
        # 8- block source & sink
        #self.block_LUTs()
        self.block_source_sink(path)

    def remove_CUT(self, test_collection):
        cut = self.CUTs[-1]
        for path in reversed(cut.paths):
            # 1- reset CD
            self.reset_CDs(test_collection, path)
            # 3- remove  sublut from LUT
            self.empty_LUTs(path.subLUTs)
            self.empty_FFs(path.FFs)
            # 7- reset FFs & SubLUTs usage
            if cfg.block_mode == 'global':
                self.reset_global_subLUTs(path.subLUTs)
                self.reset_global_FFs(path.FFs)
            # 2- unblock path
            self.unblock_path(path)
            # 8- restore source & sink
            self.restore_source_sink(path)

        self.CUTs.remove(cut)

    def finalize_CUT(self, test_collection):
        cut = self.CUTs[-1]

        # check for internal collision
        self.G_TC = nx.compose(self.G_TC, cut.G)
        if not nx.is_forest(self.G_TC):
            breakpoint()

        # block subLUTs and FFs
        self.block_subLUTs(cut)
        self.block_FFs(cut)

        #block global subLUTs and FFs
        if cfg.block_mode == 'global':
            self.block_global_subLUTs(cut.subLUTs)
            self.block_global_FFs(cut.FFs)

        # increase cost
        main_path = cut.main_path
        desired_pip_weight = 1 / len(main_path)
        self.inc_cost(test_collection, main_path, desired_pip_weight, default_weight=0.5)

        # remove out node from pip_v
        pip_v = main_path.pip[1]
        edges = set(product({cfg.pip_v}, pip_v))
        self.G.remove_edges_from(edges)


    ########## Primitives ############################
    def get_subLUT_occupancy(self, output, *inputs):
        cond_single_mode = not cfg.LUT_Dual
        cond_i6 = any(map(lambda x: nd.get_bel_index(x) == 6, inputs))
        cond_muxed_out = (output is not None) and (nd.get_clb_node_type(output) == 'CLB_muxed')
        occupancy = 2 if (cond_single_mode or cond_i6 or cond_muxed_out) else 1

        return occupancy

    def get_subLUT_bel(self, output, *inputs):
        occupancy = self.get_subLUT_occupancy(output, *inputs)
        LUT_primitive = next(self.filter_LUTs(name=nd.get_bel(inputs[0])))
        if occupancy == 2:
            bel = '6LUT'
        else:
            if LUT_primitive.capacity == 1:
                bel = '6LUT' if LUT_primitive.subLUTs[-1].name[1:] == '5LUT' else '5LUT'
            else:
                bel = '5LUT'

        return bel

    def fill_LUTs(self, path):
        cut = self.CUTs[-1]
        for subLUT in path.get_subLUTs(self):
            subLUT.add_to_LUT(self)
            path.subLUTs.add(subLUT)
            cut.subLUTs.add(subLUT)

    def empty_LUTs(self, subLUTs):
        for subLUT in subLUTs:
            subLUT.remove_from_LUT(self)

    def block_subLUTs(self, path):
        for subLUT in path.subLUTs:
            subLUT.block_usage()

    def fill_FFs(self, path):
        cut = self.CUTs[-1]
        for ff_node in path.get_FF_nodes():
            FF_primitive = next(self.filter_FFs(name=nd.get_bel(ff_node)))
            FF_primitive.set_usage(ff_node)
            path.FFs.add(FF_primitive)
            cut.FFs.add(FF_primitive)

    def empty_FFs(self, FFs):
        for FF_primitive in FFs:
            FF_primitive.free_usage()

    def block_FFs(self, path):
        for FF_primitive in path.FFs:
            FF_primitive.block_usage()

    def get_global_subLUTs(self, *subLUTs):
        global_subLUTs = set()
        for subLUT in subLUTs:
            port = subLUT.port
            direction = subLUT.direction
            global_subLUTs.update(self.filter_LUTs(port=port, direction=direction))

        return global_subLUTs

    def get_global_FFs(self, *FFs):
        global_FFs = set()
        for ff in FFs:
            direction = ff.direction
            global_FFs.update(self.filter_FFs(name=ff.name, direction=direction))

        return global_FFs

    def set_global_subLUTs(self, test_collection, subLUTs):
        tiles_map = test_collection.device.tiles_map
        for subLUT in subLUTs:
            global_subLUTs = self.get_global_subLUTs(subLUT)
            global_subLUTs = {sublut for sublut in global_subLUTs if sublut.name != subLUT.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.global_set)(self, tiles_map, subLUT) for global_subLUT in global_subLUTs)

    def reset_global_subLUTs(self, subLUTs):
        for subLUT in subLUTs:
            global_subLUTs = self.get_global_subLUTs(subLUT)
            global_subLUTs = {sublut for sublut in global_subLUTs if sublut.name != subLUT.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.global_reset)(self) for global_subLUT in global_subLUTs)

    def block_global_subLUTs(self, subLUTs):
        global_subLUTs = self.get_global_subLUTs(subLUTs)
        Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.block_usage)() for global_subLUT in global_subLUTs)

    def set_global_FFs(self, test_collection, FFs):
        tiles_map = test_collection.device.tiles_map
        for ff in FFs:
            global_FFs = self.get_global_FFs(ff)
            global_FFs = {global_FF for global_FF in global_FFs if global_FF.name != ff.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.global_set)(tiles_map, ff) for global_FF in global_FFs)

    def reset_global_FFs(self, FFs):
        for ff in FFs:
            global_FFs = self.get_global_FFs(ff)
            global_FFs = {global_FF for global_FF in global_FFs if global_FF.name != ff.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.free_usage)() for global_FF in global_FFs)

    def block_global_FFs(self, FFs):
        global_FFs = self.get_global_FFs(FFs)
        Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.block_usage)() for global_FF in global_FFs)

    def block_LUTs(self):
        occupied_LUTs = self.filter_LUTs(has_filled=True)
        for occupied_LUT in occupied_LUTs:
            tile, label = occupied_LUT.tile, occupied_LUT.label
            LUT_inputs = {nd.get_LUT_input(tile, label, idx) for idx in range(1, 6)}
            self.blocked_nodes.update(LUT_inputs)

    def unblock_LUTs(self):
        freed_LUTs = self.filter_LUTs(has_freed=True)
        for freed_LUT in freed_LUTs:
            tile, label = freed_LUT.tile, freed_LUT.label
            top_idx = 7 if freed_LUT.usage == 'free' else 6
            occupied_LUT_in = {input for subLUT in freed_LUT.subLUTs for input in subLUT.inputs}
            LUT_inputs = {nd.get_LUT_input(tile, label, idx) for idx in range(1, top_idx)} - occupied_LUT_in
            self.blocked_nodes.remove(LUT_inputs)

    ########## Block nodes & edges ####################
    def block_path(self, path):
        nodes = set(path)
        if cfg.block_mode == 'global':
            for node in path:
                nodes.update(self.get_global_nodes(node))

        self.blocked_nodes.update(nodes)

        if any(map(lambda node: nd.get_clb_node_type(node) == 'LUT_in', path)):
            LUT_in = next(node for node in path if nd.get_clb_node_type(node) == 'LUT_in')
            tile, label = nd.get_tile(LUT_in), nd.get_label(LUT_in)
            self.blocked_nodes.add(nd.get_LUT_input(tile, label, 6))
            self.block_LUTs()

    def unblock_path(self, path):
        nodes = set(path)
        if cfg.block_mode == 'global':
            for node in path:
                nodes.update(self.get_global_nodes(node))

        self.blocked_nodes -= nodes

        if any(map(lambda node: nd.get_clb_node_type(node) == 'LUT_in', path)):
            self.unblock_LUTs()

    def block_source_sink(self, path):
        edges = set()
        clock_domains = [CD for _, CD in self.CD.items() if CD.name != 'None']
        for CD in clock_domains:
            matched_preds_neighs = {node for node in path if CD.pattern.match(node)}
            if cfg.block_mode == 'global':
                for pred_neigh in matched_preds_neighs.copy():
                    matched_preds_neighs.update(self.get_global_nodes(pred_neigh))

            if CD.type == 'source':
                edges.update(set(product({CD.src_sink_node}, matched_preds_neighs)))
            if CD.type == 'sink':
                edges.update(set(product(matched_preds_neighs, {CD.src_sink_node})))

        # remove sources with occupied LUTs
        occupied_LUTs = self.filter_LUTs(has_filled=True)
        for occupied_LUT in occupied_LUTs:
            sources = {node for node in self.G.neighbors('s') if nd.get_tile(node) == occupied_LUT.tile and nd.get_label(node) == occupied_LUT.label}
            edges.update(set(product({cfg.virtual_source_node}, sources)))

        self.G.remove_edges_from(edges)

    def restore_source_sink(self, path):
        edges = set()
        clock_domains = [CD for _, CD in self.CD.items() if CD.name != 'None']
        for CD in clock_domains:
            matched_preds_neighs = {node for node in path if CD.pattern.match(node)}
            if cfg.block_mode == 'global':
                for pred_neigh in matched_preds_neighs.copy():
                    matched_preds_neighs.update(self.get_global_nodes(pred_neigh))

            if CD.type == 'source':
                edges.update(set(product({CD.src_sink_node}, matched_preds_neighs)))
            if CD.type == 'sink':
                edges.update(set(product(matched_preds_neighs, {CD.src_sink_node})))

        # restore free FFs in front of freed LUTs
        freed_LUTs = self.filter_LUTs(has_freed=True)
        for freed_LUT in freed_LUTs:
            sources = {node for node in self.G.neighbors(cfg.virtual_source_node)
                       if nd.get_tile(node) == freed_LUT.tile
                       and nd.get_label(node) == freed_LUT.label
                       and next(self.filter_FFs(name=nd.get_bel(node))).usage == 'free'}
            edges.update(set(product({cfg.virtual_source_node}, sources)))

        self.G.add_edges_from(edges)

    def add_edges(self, *edges, device=None, weight=None):
        for edge in edges:
            if edge[1] in self.G_TC:
                continue

            '''if {edge[0], edge[1]} & self.reconst_blocked_nodes:
                continue'''

            if edge[1] in self.blocked_nodes:
                continue

            if weight is None:
                try:
                    weight = device.G.get_edge_data(*edge)['weight']
                except TypeError:
                    breakpoint()

            self.G.add_edge(*edge, weight=weight)

    ########## CD ####################
    def set_CDs(self, test_collection, path):
        ff_nodes = {node for node in path if nd.get_primitive(node) == 'FF'}
        for ff_node in ff_nodes:
            clock_group = nd.get_clock_group(ff_node)
            CG = test_collection.get_clock_group(clock_group)
            CG.set(ff_node, test_collection)

    def reset_CDs(self, test_collection, path):
        TC = test_collection.TC
        restored_CGs = [CG for CG in path.prev_CD if path.prev_CD[CG].name == 'None' and path.prev_CD[CG] != TC.CD[CG]]
        for CG in restored_CGs:
            CG.reset(test_collection)

    def get_clock_domain(self, node: str) -> ClockDomain:
        clock_group = nd.get_clock_group(node)
        if clock_group is None:
            raise ValueError(f'Node: {node} is not a CLB node!')

        CD = next(value for key, value in self.CD.items() if key.name == clock_group)

        return CD
    ########## Routing ###############
    def pick_pip(self, test_collection):
        device = test_collection.device
        pips = test_collection.queue

        path_out = PathOut()
        path_out.route(self, pips, first_order=True)
        if path_out.error:
            return None

        sink = path_out[0]
        path_in = PathIn(sink)
        path_in.route(self, pips, path_out)
        path_in.nodes.pop()
        if path_in.error:
            print(path_out)
            return None

        # create the main_path
        self.G.remove_edge(cfg.pip_v, path_out[0])
        pip = PIP((path_in[-1], path_out[0]), device.G)
        self.CUTs[-1].main_path = MainPath(self, path_in, path_out, pip)

        return pip

    def fill(self, test_collection):
        #device = test_collection.device
        while not test_collection.finish_TC(self):
            # clean out excess pip_v nodes
            test_collection.clean_pip_v_node(self.G)

            # create a CUT
            coord = nd.get_coordinate(test_collection.desired_tile)
            self.create_CUT(coord)

            # pick a pip
            pip = self.pick_pip(test_collection)
            if pip is None:
                break

            # find the main path
            main_path = self.CUTs[-1].main_path
            main_path.route(test_collection)
            if main_path.error:
                # unblock
                print(pip)
                breakpoint()
                test_collection.queue.remove(pip.name)
                test_collection.pbar.update(1)
                break
                #continue

            # validate main_path length
            '''if not self.validate_main_path_length(device, pip):
                continue'''

            path_not = NotPath()
            path_not.route(test_collection)
            if path_not.error:
                # unblock
                print(pip)
                breakpoint()
                test_collection.queue.remove(pip.name)
                test_collection.pbar.update(1)
                #continue
                break

            ###
            test_collection.covered_pips.append(pip.name)
            test_collection.queue.remove(pip.name)
            test_collection.pbar.update(1)
            #print(pip)
            break

    def inc_cost(self, test_collection, main_path: MainPath, desired_pip_weight, default_weight=0.5):
        edges = set()
        device = test_collection.device
        desired_tile = test_collection.desired_tile

        for edge in main_path.get_edges():
            if cfg.block_mode == 'global':
                edges.update(self.get_global_edges(edge))
            else:
                edges.add(edge)

        for edge in edges:
            if edge.get_type() == 'pip' and nd.get_tile(edge[0]) == desired_tile:
                device.G.get_edge_data(*edge)['weight'] += desired_pip_weight
            else:
                device.G.get_edge_data(*edge)['weight'] += default_weight

if __name__ == '__main__':
    t1 = time.time()
    device = Arch('ZCU9')
    device.G = util.load_data(cfg.graph_path, 'G_ZCU9_INT_X46Y90.data')
    pips = device.gen_pips('INT_X46Y90')
    TC = MinConfig(device, 0)
    pip = pips.pop()



    print(time.time() - t1)

