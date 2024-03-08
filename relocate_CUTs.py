import os, sys
import scripts.config as cfg
import scripts.utility_functions as util
from xil_res.architecture import Arch
from relocation.relocation_storage import RLOC_Collection

if __name__ == "__main__":

    # User's inputs
    device_name = sys.argv[1]
    desired_tile = sys.argv[2]

    iteration = len(os.listdir(cfg.minimal_config_path))

    # init device
    device = Arch(device_name)

    # create relocation_storage
    rloc_collection = RLOC_Collection(device, iteration, desired_tile)

    # create and fill configurations
    for file in rloc_collection.minimal_configs:
        rloc_collection.fill_TC(file)

    rloc_collection.pbar.set_postfix_str(rloc_collection.get_coverage())

    # store rloc_collection
    util.store_data(cfg.config_path, 'rloc_collection.data', rloc_collection)

