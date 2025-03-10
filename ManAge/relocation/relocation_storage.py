import os, re, shutil
from pathlib import Path
from dataclasses import dataclass, field
from tqdm import tqdm
from xil_res.architecture import Arch
from relocation.configuration import Config
from xil_res.node import Node as nd
import utility.utility_functions as util
import utility.config as cfg


@dataclass
class RLOC_Collection:
    """This class provides required attributes and methods for performing the relocation process.
    """
    device              :   Arch
    origin              :   str
    minimal_config_dir  :   str
    prev_config_dir     :   str
    config_dir          :   str
    overwrite           :   bool    = field(default = True)
    covered_pips        :   dict    = field(default_factory = dict)
    TC_idx              :   int     = field(default = 0)
    pbar                :   tqdm    = field(default = None)
    minimal_configs     :   list    = field(default_factory = list)
    origins             :   list    = field(default_factory=list)


    def __post_init__(self):
        # create the store path directory
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        #load covered_pips
        if self.prev_config_dir is not None:
            prev_rloc_collection = util.load_data(self.prev_config_dir, 'rloc_collection.data')
            self.covered_pips = prev_rloc_collection.covered_pips.copy()
            self.origins = prev_rloc_collection.origins.copy()

        # add origin
        self.origins.append(self.origin)

        # set minimal_configs files
        self.minimal_configs = list(Path(self.minimal_config_dir).glob('TC*'))
        self.minimal_configs.sort(key=lambda x: int(re.findall('\d+', x.stem).pop()))

        # create pbar
        length = len(self.minimal_configs)
        self.create_pbar(length)

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

    def create_pbar(self, length):
        """This function creates a progrss bar for the relocation process

        :param length: Number of configurations
        :type length: int
        """
        self.pbar = tqdm(total=length)

    def update_pbar(self):
        """This function updates the progress bar and test configurations' indices
        """
        self.pbar.update(1)
        self.TC_idx += 1

    def create_TC(self, file_name):
        """This function creates a test configuration

        :param file_name: Name of the test configuration
        :type file_name: str
        :return: Created test configuration
        :rtype: Config
        """
        if self.prev_config_dir is None:
            TC = Config()

        else:
            self.TC_idx = int(re.findall('\d+', file_name)[0])
            if file_name not in os.listdir(self.prev_config_dir):
                TC = Config()
            else:
                TC = util.load_data(self.prev_config_dir, file_name)


        return TC

    def fill_TC(self, file):
        """This function populates test configurations with relocated CUTs

        :param file: The path to the minimal test configuration file
        :type file: pathlib.Path
        """
        minimal_TC = util.load_data(str(file.parent), file.name)
        TC = self.create_TC(file.name)
        TC.fill_D_CUTs(self, minimal_TC)
        util.store_data(self.config_dir, f'TC{self.TC_idx}.data', TC)
        self.update_pbar()

    def update_coverage(self, edges):
        """This function updates the edges covered by CUTs and store the results in the covered_pips dictionary

        :param edges: Covered edges of the architecture graph
        :type edges: Set[Tuple[str, str]]
        """
        pips = filter(lambda e: nd.get_tile(e[0]) == nd.get_tile(e[1]), edges)
        for pip in pips:
            key = nd.get_tile(pip[0])
            value = tuple(map(nd.get_port, pip))
            util.extend_dict(self.covered_pips, key, value, value_type='set')

    def get_pips_length_dict(self):
        """This function creates a dictionary showing how many PIPs must be covered at each INT tile

        :return: A dictionary with INT tiles as keys and the number of PIPs to be covered as values 
        :rtype: dict
        """
        uncovered_pips_length = {}
        coordinates = self.device.get_coords()
        for coordinate in coordinates:
            INT_tile = f'{cfg.INT_label}_{coordinate}'
            N_pips = cfg.n_pips_two_CLB if all(map(lambda tile: tile is not None, self.device.tiles_map[coordinate].values())) else cfg.n_pips_one_CLB
            uncovered_pips_length[INT_tile] = N_pips

        return uncovered_pips_length

    def get_coverage(self):
        """This function claculates the covereage and report it in percent

        :return: Coverage   
        :rtype: str
        """
        total_pips = sum(self.get_pips_length_dict().values())
        covered_pips = sum(len(v) for k, v in self.covered_pips.items() if k.startswith(cfg.INT_label) and nd.get_coordinate(k)
                           in self.device.get_coords())

        return f'Coverage: {covered_pips / total_pips:.2%}'

    def copy_missing_conf_files(self):
        """This function copies the missing configuration files from the previous iteration directory to the current iteration directory
        """
        if self.prev_config_dir is not None:
            missing_files = set(os.listdir(self.prev_config_dir)) - set(os.listdir(self.config_dir))
            for file in missing_files:
                src = os.path.join(self.prev_config_dir, file)
                dst = os.path.join(self.config_dir, file)
                shutil.copy(src, dst)