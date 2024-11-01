from dataclasses import dataclass, field
from typing import List, Set
import utility.utility_functions as util
import utility.config as cfg
from xil_res.node import Node as nd
from xil_res.cut import CUT
from relocation.cut import D_CUT
from xil_res.primitive import LUT

@dataclass
class Config:
    used_nodes  :   dict    = field(default_factory = dict)
    D_CUTs      :   List    = field(default_factory = list)
    CD          :   List    = field(default_factory = list)
    subLUTs     :   dict     = field(default_factory = dict)
    LUTs        :   dict     = field(default_factory = dict)
    FFs         :   dict     = field(default_factory = dict)


    def filter_LUTs(self, **attributes):
        """This function filters the existing LUTs in the configuration according to the specified attributes

        :return: Filtered LUT objects
        :rtype: types.GeneratorType
        """
        return (LUT_obj for LUT_obj in self.LUTs.values() if all(getattr(LUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_subLUTs(self, **attributes):
        """This function filters the existing subLUTs in the configuration according to the specified attributes

        :return: Filtered subLUT objects
        :rtype: types.GeneratorType
        """
        return (subLUT_obj for subLUT_obj in self.subLUTs.values() if all(getattr(subLUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_FFs(self, **attributes):
        """This function filters the existing FFs in the configuration according to the specified attributes

        :return: Filtered FF objects
        :rtype: types.GeneratorType
        """
        return (FF_obj for FF_obj in self.FFs.values() if all(getattr(FF_obj, attr) == value for attr, value in attributes.items()))

    @staticmethod
    def create_LUTs(device):
        """This function creates LUT objects for the configuration

        :param device: Device under test
        :type device: Arch
        :return: LUT objects
        :rtype: Set[LUT]
        """
        return {lut.name: lut for lut in device.get_LUTs()}

    @staticmethod
    def create_FFs(device):
        """This function creates FF objects for the configuration

        :param device: Device under test
        :type device: Arch
        :return: FF objects
        :rtype: Set[FF]
        """
        return {ff.name: ff for ff in device.get_FFs()}

    @staticmethod
    def create_subLUTs(device):
        """This function creates subLUT objects for the configuration

        :param device: Device under test
        :type device: Arch
        :return: subLUT objects
        :rtype: Set[SubLUT]
        """
        return {sublut.name: sublut for sublut in device.get_subLUTs()}

    def get_subLUT_bel(self, output, *inputs):
        """This function determines the BEL of a subLUT based on its inputs and output

        :param output: Output node
        :type output: str|None
        :raises ValueError: When the respective LUT of the subLUT is already fully occupied
        :return: BEL of the subLUT
        :rtype: str
        """
        occupancy = self.get_subLUT_occupancy(output, *inputs)
        LUT_primitive = self.LUTs[nd.get_bel(inputs[0])]
        free_subLUTs = list(self.filter_subLUTs(tile=LUT_primitive.tile, label=LUT_primitive.label, usage='free'))
        if len(free_subLUTs) == 0:
            raise ValueError(f'{LUT_primitive} is already filled!')
        elif len(free_subLUTs) == 1:
            return free_subLUTs[0].port[1:]

        if occupancy == 2:
            bel = '6LUT'
        else:
            if LUT_primitive.capacity == 1:
                bel = '6LUT' if LUT_primitive.subLUTs[-1].port[1:] == '5LUT' else '5LUT'
            else:
                bel = '5LUT'

        return bel

    def get_subLUT_occupancy(self, output, *inputs):
        """This function calculates the occupancy of a subLUT based on its inputs and output

        :param output: Output node
        :type output: str|None
        :return: Occupancy of the subLUT
        :rtype: int
        """
        cond_single_mode = not cfg.LUT_Dual
        cond_i6 = any(map(lambda x: nd.get_bel_index(x) == 6, inputs))
        cond_muxed_out = (output is not None) and (nd.get_clb_node_type(output) == 'CLB_muxed')
        occupancy = 2 if (cond_single_mode or cond_i6 or cond_muxed_out) else 1

        return occupancy

    def check_collision(self, cut: D_CUT):
        """This function checks if there is no collision between the specified CUT's nodes and already found paths in the configuration

        :param cut: Relocated CUT
        :type cut: D_CUT
        :return: True|False
        :rtype: bool
        """
        return all(map(lambda node: nd.get_tile(node) not in self.used_nodes or
                                    (nd.get_tile(node) in self.used_nodes and
                                    nd.get_port(node) not in self.used_nodes[nd.get_tile(node)]), cut.G))

    def check_LUT_util(self, cut: D_CUT):
        """This function verifies that LUTs used by the specified CUT will not be over-utilized

        :param cut: Relocated CUT
        :type cut: D_CUT
        :return: True|False
        :rtype: bool
        """
        LUT_cap = {subLUT.get_LUT_name(): self.LUTs[subLUT.get_LUT_name()].capacity if subLUT.get_LUT_name() in self.LUTs else cfg.LUT_Capacity for subLUT in cut.subLUTs}
        for subLUT in cut.subLUTs:
            LUT_cap[subLUT.get_LUT_name()] -= subLUT.get_occupancy()

        return all(map(lambda cap: cap >= 0, LUT_cap.values()))

    def check_FF_util(self, cut: D_CUT):
        """This function checks if only one node of FFs is utilized

        :param cut: Relocated CUT
        :type cut: D_CUT
        :return: True|False
        :rtype: bool
        """
        return all(map(lambda ff: ff.name not in self.FFs, cut.FFs))

    def fill_D_CUTs(self, rloc_collection, minimal_TC):
        """This function relocates a minimal test configuration's CUTs and add them to the configuration

        :param rloc_collection: Relocation Collection
        :type rloc_collection: RLOC_Collection
        :param minimal_TC: Minimal test configuration
        :type minimal_TC: MinConfig
        """
        tiles_map = rloc_collection.device.tiles_map
        wires_dict = rloc_collection.device.wires_dict
        device = rloc_collection.device
        iteration = len(rloc_collection.origins)
        CUTs = minimal_TC.CUTs

        # first add CUTs
        for cut in CUTs:
            try:
                d_cut = D_CUT(cut.origin, tiles_map, wires_dict, cut, iteration)
            except ValueError:
                raise Exception(f'{cut}: The reference CUT is invalid!')

            self.add_D_CUT(rloc_collection, d_cut)

        # set CD
        self.CD = minimal_TC.CD.copy()

        for cut_idx, cut in enumerate(CUTs):
            # get D_CUTs with valid tiles and wires
            #D_CUTs = self.get_valid_D_CUTs(rloc_collection, cut)
            origins = (coord for CR in device.CRs for coord in CR.coords)
            #D_CUTs = self.create_instances_parallel(origins, tiles_map, wires_dict, cut, iteration)
            D_CUTs = self.d_cut_generator(origins, tiles_map, wires_dict, cut, iteration)

            for idx, d_cut in enumerate(D_CUTs):
                if self.check_collision(d_cut) and self.check_LUT_util(d_cut) and self.check_FF_util(d_cut):
                    self.add_D_CUT(rloc_collection, d_cut)

    def d_cut_generator(self, origins, tiles_map, wires_dict, cut, iteration=None):
        """This function generates a new CUT for the specified origins

        :param origins: Target origins to where the specified CUT must be relocated
        :type origins: [Any, Any, None]
        :param tiles_map: Tiles map of the device under test
        :type tiles_map: dict
        :param wires_dict: Wires dictionary of the device under test
        :type wires_dict: dict
        :param cut: Original CUT from the minimal test configuration
        :type cut: CUT
        :param iteration: Iteration of path search process, defaults to None
        :type iteration: int, optional
        :yield: Relocated CUT
        :rtype: Iterable[_T]
        """
        for origin in origins:
            try:
                yield D_CUT(origin, tiles_map, wires_dict, cut, iteration=iteration)
            except ValueError:
                continue

    def fill_nodes(self, rloc_collection, cut:D_CUT | CUT):
        """This function updates the utilized nodes of the configuration and the coverage of the whole process

        :param rloc_collection: Relocation collection
        :type rloc_collection: RLOC_Collection
        :param cut: Relocated CUT
        :type cut: D_CUT | CUT
        """
        for node in cut.G:
            util.extend_dict(self.used_nodes, nd.get_tile(node), nd.get_port(node), value_type='set')

        # fill covered_pips
        rloc_collection.update_coverage(cut.main_path.get_edges())

    def fill_LUTs(self, cut: D_CUT | CUT):
        """This function fills the LUTs of the configuration with the specified CUT based on the utilized subLUTs

        :param cut: Relocated CUT
        :type cut: D_CUT | CUT
        """
        for subLUT in cut.subLUTs:
            LUT_name = subLUT.get_LUT_name()
            if LUT_name not in self.LUTs:
                self.LUTs[LUT_name] = LUT(LUT_name)

            subLUT.add_to_LUT(self)

    def fill_FFs(self, cut: D_CUT | CUT):
        """This function fills the FFs of the configuration based on the utilized FFs by the specified CUT

        :param cut: Relocated CUT
        :type cut: D_CUT | CUT
        """
        for FF_primitive in cut.FFs:
            self.FFs[FF_primitive.name] = FF_primitive

    def add_D_CUT(self, rloc_collection, d_cut: D_CUT):
        """This function adds the specified relocated CUT to the configuration

        :param rloc_collection: Relocation collection
        :type rloc_collection: RLOC_Collection
        :param d_cut: Relocated CUT
        :type d_cut: D_CUT
        """
        self.D_CUTs.append(d_cut)
        self.fill_nodes(rloc_collection, d_cut)
        self.fill_LUTs(d_cut)
        self.fill_FFs(d_cut)