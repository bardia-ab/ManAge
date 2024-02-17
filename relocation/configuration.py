import copy
import os, re
from dataclasses import dataclass, field
from typing import List, Set, Any
from joblib import Parallel, delayed
import scripts.utility_functions as util
import scripts.config as cfg
from xil_res.node import Node as nd
from xil_res.cut import CUT
from relocation.rloc import RLOC as rl
from relocation.cut import D_CUT
from functools import partial
import concurrent.futures

@dataclass
class Config:
    device      : Any = field(default=None, repr=False, init=True)
    used_nodes  :   dict    = field(default_factory = dict)
    D_CUTs      :   List    = field(default_factory = list)
    CD          :   dict    = field(default_factory = dict)
    subLUTs     :   Any     = field(init=False)
    LUTs        :   Any     = field(init=False)
    FFs         :   Any     = field(init=False)


    def __post_init__(self):
        if self.device:
            self.FFs = self.create_FFs(self.device)
            self.LUTs = self.create_LUTs(self.device)
            self.subLUTs = self.create_subLUTs(self.device)

    def filter_LUTs(self, **attributes):
        return (LUT_obj for LUT_obj in self.LUTs.values() if all(getattr(LUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_subLUTs(self, **attributes):
        return (subLUT_obj for subLUT_obj in self.subLUTs.values() if all(getattr(subLUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_FFs(self, **attributes):
        return (FF_obj for FF_obj in self.FFs.values() if all(getattr(FF_obj, attr) == value for attr, value in attributes.items()))

    def create_LUTs(self, device):
        return {lut.name: lut for lut in device.get_LUTs()}

    def create_FFs(self, device):
        return {ff.name: ff for ff in device.get_FFs()}

    def create_subLUTs(self, device):
        return {sublut.name: sublut for sublut in device.get_subLUTs()}

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
            global_FFs.update(self.filter_FFs(port=ff.port, direction=direction))

        return global_FFs

    def set_global_FFs(self, test_collection, FFs):
        tiles_map = test_collection.device.tiles_map
        for ff in FFs:
            global_FFs = self.get_global_FFs(ff)
            global_FFs = {global_FF for global_FF in global_FFs if global_FF.name != ff.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.global_set)(tiles_map, ff) for global_FF in global_FFs)

    def set_global_subLUTs(self, test_collection, subLUTs):
        tiles_map = test_collection.device.tiles_map
        for subLUT in subLUTs:
            global_subLUTs = self.get_global_subLUTs(subLUT)
            global_subLUTs = {sublut for sublut in global_subLUTs if sublut.name != subLUT.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.global_set)(tiles_map, subLUT) for global_subLUT in global_subLUTs)
            Parallel(n_jobs=-1, require='sharedmem')(
                delayed(global_subLUT.add_to_LUT)(self) for global_subLUT in global_subLUTs)

    def get_valid_origins(self, rloc_collection, cut: CUT):
        tiles_map = rloc_collection.device.tiles_map
        wires_dict = rloc_collection.device.wires_dict
        nodes = cut.G
        edges = cut.G.edges
        origin = cut.origin

        INT_tiles = filter(lambda tile: nd.get_tile_type(tile) == 'INT', wires_dict)
        valid_INT_tiles = filter(lambda tile: rl.check_tile_compliance(tiles_map, nodes, origin, tile) and
                                 rl.check_wire_compliance(tiles_map, wires_dict, edges, origin, tile), INT_tiles)

        return valid_INT_tiles

    def check_collision(self, cut: D_CUT):
        return all(map(lambda node: nd.get_tile(node) in self.used_nodes and
                                    nd.get_port(node) not in self.used_nodes[nd.get_tile(node)], cut.G))

    def check_LUT_util(self, cut: D_CUT):
        LUT_cap = {subLUT.get_LUT_name(): self.LUTs[subLUT.get_LUT_name()].capacity for subLUT in cut.subLUTs}
        for subLUT in cut.subLUTs:
            LUT_cap[subLUT.get_LUT_name()] -= subLUT.get_occupancy()

        return all(map(lambda cap: cap > 0, LUT_cap.values()))

    def fill_D_CUTs(self, rloc_collection, minimal_TC):
        CUTs = minimal_TC.CUTs

        # first add CUTs
        for cut in CUTs:
            d_cut = D_CUT(rloc_collection, cut, cut.origin)
            self.add_D_CUT(rloc_collection, d_cut)

        # set CD
        self.CD = minimal_TC.CD.copy()

        for cut_idx, cut in enumerate(CUTs):
            # get D_CUTs with valid tiles and wires
            D_CUTs = self.get_valid_D_CUTs(rloc_collection, cut)

            # remove the D_CUT of the cut => as D_CUTs are sorted the first element is the cut
            D_CUTs.pop(0)

            for d_cut in D_CUTs:
                if self.check_collision(d_cut) and self.check_LUT_util(d_cut):
                    self.add_D_CUT(rloc_collection, d_cut)

    def get_valid_D_CUTs(self, rloc_collection, cut: CUT):
        cut_x, cut_y = nd.get_x_coord(cut.origin), nd.get_y_coord(cut.origin)
        valid_INT_tiles = self.get_valid_origins(rloc_collection, cut)
        D_CUTs = (D_CUT(rloc_collection, cut, nd.get_coordinate(tile)) for tile in valid_INT_tiles)

        return sorted(D_CUTs, key=lambda x: (abs(x.get_x_coord() - cut_x), abs(x.get_y_coord() - cut_y)))

    def fill_nodes(self, rloc_collection, cut:D_CUT | CUT):
        for node in cut.G:
            util.extend_dict(self.used_nodes, nd.get_tile(node), nd.get_port(node), value_type='set')

        # fill covered_pips
        rloc_collection.update_coverage(cut.G.edges)

    def fill_LUTs(self, cut: D_CUT | CUT):
        for subLUT in cut.subLUTs:
            subLUT.add_to_LUT(self)

    def fill_FFs(self, cut: D_CUT | CUT):
        for FF_primitive in cut.FFs:
            self.FFs[FF_primitive.name] = copy.deepcopy(FF_primitive)

    def add_D_CUT(self, rloc_collection, d_cut: D_CUT):
        self.D_CUTs.append(d_cut)
        self.fill_nodes(rloc_collection, d_cut)
        self.fill_LUTs(d_cut)
        self.fill_FFs(d_cut)