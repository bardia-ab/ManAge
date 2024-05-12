import os, sys
from pathlib import Path

import networkx as nx

if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

import utility.config as cfg
import utility.utility_functions as util
from xil_res.architecture import Arch
from relocation.relocation_storage import RLOC_Collection
from relocation.cut import D_CUT
from xil_res.node import Node as nd

def check_node_collision(graphs):
    seen_nodes = set()
    for G in graphs:
        if set(G.nodes) & seen_nodes:
            return False

        seen_nodes.update(G.nodes)

    return True

if __name__ == "__main__":

    # User's inputs
    device_name = sys.argv[1]
    desired_tile = sys.argv[2]
    store_name = sys.argv[3]
    desired_tiles = sys.argv[4:]

    iteration = len(os.listdir(cfg.minimal_config_path))

    # init device
    device = Arch(device_name)

    # create relocation_storage
    rloc_collection = RLOC_Collection(device, iteration, desired_tile, overwrite=False)

    # create and fill configurations
    for file in rloc_collection.minimal_configs:
        minimal_TC = util.load_data(cfg.minimal_config_path, file)
        TC = rloc_collection.create_TC()

        G_tiles = len(desired_tiles) * [nx.DiGraph()]
        for idx, desired_tile in enumerate(desired_tiles):
            for cut in minimal_TC.CUTs:
                d_cut = D_CUT(nd.get_coordinate(desired_tile), device.tiles_map, cut, iteration=rloc_collection.iteration)

                if TC.check_LUT_util(d_cut) and TC.check_FF_util(d_cut):
                    TC.add_D_CUT(rloc_collection, d_cut)
                    G_tiles[idx] = nx.compose(G_tiles[idx], d_cut.G)

        if check_node_collision(G_tiles):
            util.store_data(cfg.config_path, f'TC_{store_name}.data', TC)