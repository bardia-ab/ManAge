import os, re, copy
from dataclasses import dataclass, field
from tqdm import tqdm
from xil_res.architecture import Arch
from relocation.configuration import Config
from xil_res.node import Node as nd
import utility.utility_functions as util
import utility.config as cfg


@dataclass
class RLOC_Collection:
    device          :   Arch
    iteration       :   int
    desired_tile    :   str
    covered_pips    :   dict    = field(default_factory = dict)
    #TC              :   Config  = field(default=None)
    TC_idx          :   int     = field(default = 0)
    pbar            :   tqdm    = field(default = None)
    minimal_configs :   list    = field(default_factory = list)


    def __post_init__(self):
        # create the iteration folder
        cfg.config_path = os.path.join(cfg.config_path, f'iter{self.iteration}')
        util.create_folder(cfg.config_path)

        # set minimal_configs files
        cfg.minimal_config_path = os.path.join(cfg.minimal_config_path, f'iter{self.iteration}')
        self.minimal_configs = sorted(os.listdir(cfg.minimal_config_path), key=lambda x: int(re.findall('\d+', x).pop()))

        # create pbar
        length = len(self.minimal_configs)
        self.create_pbar(length)

        #self.LUTs = self.create_LUTs()

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

    def create_LUTs(self):
        return {lut.name: lut for lut in self.device.get_LUTs()}

    def create_FFs(self):
        return {ff.name: ff for ff in self.device.get_FFs()}

    def create_subLUTs(self):
        return {sublut.name: sublut for sublut in self.device.get_subLUTs()}



    def create_pbar(self, length):
        self.pbar = tqdm(total=length)

    def update_pbar(self):
        self.pbar.update(1)
        self.TC_idx += 1

    def create_TC(self):
        if self.iteration == 1:
            TC = Config()
        else:
            prev_rloc_collection = util.load_data(cfg.Data_path, 'rloc_collection.data')
            self.covered_pips = prev_rloc_collection.covered_pips.copy()

            if len(prev_rloc_collection.minimal_configs) < self.pbar.total:
                TC = Config()
            else:
                TC = util.load_data(cfg.config_path, f'TC{self.TC_idx}.data')

        return TC

    def fill_TC(self, file):
        minimal_TC = util.load_data(cfg.minimal_config_path, file)
        TC = self.create_TC()
        TC.fill_D_CUTs(self, minimal_TC)
        util.store_data(cfg.config_path, f'TC{self.TC_idx}.data', TC)
        self.update_pbar()

    def update_coverage(self, edges):
        pips = filter(lambda e: nd.get_tile(e[0]) == nd.get_tile(e[1]), edges)
        for pip in pips:
            key = nd.get_tile(pip[0])
            value = tuple(map(nd.get_port, pip))
            util.extend_dict(self.covered_pips, key, value, value_type='set')

    def get_pips_length_dict(self):
        uncovered_pips_length = {}
        for INT_tile in self.device.get_INTs():
            coordinate = nd.get_coordinate(INT_tile)
            N_pips = cfg.n_pips_two_CLB if all(map(lambda tile: tile is not None, self.device.tiles_map[coordinate].values())) else cfg.n_pips_one_CLB
            #uncovered_pips_length[INT_tile] = N_pips - len(self.covered_pips[INT_tile])
            uncovered_pips_length[INT_tile] = N_pips

        return uncovered_pips_length

    def get_coverage(self):
        total_pips = sum(self.get_pips_length_dict().values())
        covered_pips = sum(len(v) for k, v in self.covered_pips.items() if k.startswith('INT'))

        return f'Coverage: {covered_pips / total_pips * 100:.2}%'
