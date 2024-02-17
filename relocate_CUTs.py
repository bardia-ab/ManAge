import os
from joblib import Parallel, delayed
import scripts.config as cfg
import scripts.utility_functions as util
from xil_res.architecture import Arch
from relocation.relocation_storage import RLOC_Collection
from relocation.configuration import Config
from xil_res.node import Node as nd
from relocation.rloc import RLOC as rl
import concurrent.futures

if __name__ == "__main__":

    # User's inputs
    desired_tile = 'INT_X46Y90'
    iteration = len(os.listdir(cfg.minimal_config_path))

    # init device
    device = Arch('xczu9eg')

    # create relocation_storage
    rloc_collection = RLOC_Collection(device, iteration, desired_tile)
    #rloc_collection.initialize()

    # create and fill configurations
    Parallel(n_jobs=-1, require='sharedmem')(delayed(rloc_collection.fill_TC)(file) for file in rloc_collection.minimal_configs)
    #for file in rloc_collection.minimal_configs:
        #rloc_collection.fill_TC(file)
    #with concurrent.futures.ProcessPoolExecutor() as executor:
        #results = [executor.submit(rloc_collection.fill_TC, file) for file in rloc_collection.minimal_configs]

    # store rloc_collection
    try:
        util.store_data(cfg.Data_path, 'rloc_collection.data', rloc_collection)
    except:
        util.store_data(cfg.Data_path, 'covered_pips.data', rloc_collection.covered_pips)