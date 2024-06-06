import os.path
import sys
from xil_res.test_storage import TestCollection
from xil_res.architecture import Arch
from xil_res.path import PathOut, PathIn
import utility.config as cfg
import utility.utility_functions as util


if __name__ == "__main__":

    # User's inputs
    # usage: python3 path_finder.py device_name desired_tile iteration pips_mode
    device_name = sys.argv[1]
    desired_tile    = sys.argv[2]
    iteration       = int(sys.argv[3])
    pips_mode       = sys.argv[4]

    Empty_TC = False
    if pips_mode == 'local':
        cfg.long_TC_process_time = 7

    # init device
    device = Arch(device_name)

    # set compressed graph
    device.set_compressed_graph(desired_tile)
    device.reform_cost()
    device.remove_untested_edges()
    device.weight = PathIn.weight_function(device.G, 'weight')

    pips = device.get_pips(desired_tile, mode=pips_mode)

    test_collection = TestCollection(iteration=iteration, desired_tile=desired_tile, queue=pips)

    #create a TC
    while test_collection.queue:
        test_collection.create_TC(device)
        TC = test_collection.TC
        TC.fill(test_collection)

        if TC.CUTs:
            test_collection.store_TC()
        else:
            if Empty_TC:
                device.reset_costs(test_collection)
                device.reform_cost()
                Empty_TC = True
            else:
                break

        # reset weights
        if (test_collection.n_pips - len(test_collection.queue) // test_collection.n_pips) > 0.3:
            device.reset_costs(test_collection)
            device.reform_cost()

    util.store_data(cfg.minimal_config_path, 'test_collection.data', test_collection)
