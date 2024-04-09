import os, sys
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

import utility.config as cfg
import utility.utility_functions as util
from xil_res.architecture import Arch
from relocation.relocation_storage import RLOC_Collection
from relocation.cut import D_CUT
from xil_res.node import Node as nd

if __name__ == "__main__":

    # User's inputs
    #device_name = sys.argv[1]
    #desired_tile = sys.argv[2]

    device_name = 'xczu9eg'
    desired_tile = 'INT_X46Y90'
    store_name = '1clb_x46y90'

    iteration = len(os.listdir(cfg.minimal_config_path))

    # init device
    device = Arch(device_name)

    # create relocation_storage
    rloc_collection = RLOC_Collection(device, iteration, desired_tile, overwrite=False)

    # create and fill configurations
    for file in rloc_collection.minimal_configs:
        minimal_TC = util.load_data(cfg.minimal_config_path, file)
        TC = rloc_collection.create_TC()

        for cut in minimal_TC.CUTs:
            d_cut = D_CUT(nd.get_coordinate(desired_tile), device.tiles_map, cut, iteration=rloc_collection.iteration)
            TC.D_CUTs.append(d_cut)
            TC.fill_nodes(rloc_collection, d_cut)
            TC.fill_LUTs(d_cut)

        util.store_data(cfg.config_path, f'TC_{store_name}.data', TC)

    rloc_collection.pbar.set_postfix_str(rloc_collection.get_coverage())


