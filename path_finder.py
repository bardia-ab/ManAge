import os.path
import sys, time, cProfile
#sys.path.insert(0, r'..\scripts')
#sys.path.insert(0, r'..\experiment')
from experiment.test_storage import TestCollection
from xil_res.architecture import Arch
from xil_res.path import PathOut, PathIn
import scripts.config as cfg
import scripts.utility_functions as util


if __name__ == "__main__":

    # User's inputs
    desired_tile = 'INT_X46Y90'
    iteration = 1

    # init device
    device = Arch('xczu9eg')

    # set compressed graph
    #dev.set_compressed_graph('INT_X46Y90')
    device.G = util.load_data(cfg.graph_path, 'G_ZCU9_INT_X46Y90.data')
    device.remove_untested_edges()
    device.weight = PathIn.weight_function(device.G, 'weight')

    # calculate minimum path length for each pip
    device.set_pips_length_dict('INT_X46Y90')

    # create a Test Collection
    #pips = device.gen_pips('INT_X46Y90')
    pips = set(device.pips_length_dict.keys())

    test_collection = TestCollection(iteration=iteration, desired_tile=desired_tile, queue=pips)
    #test_collection.initialize()

    #create a TC
    while test_collection.queue:
        test_collection.create_TC(device)
        TC = test_collection.TC
        TC.fill(test_collection)
        test_collection.store_TC()
