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
from relocation.rloc import RLOC
from xil_res.node import Node as nd

###########
def check_node_collision(graphs):
    seen_nodes = set()
    for G in graphs:
        if set(G.nodes) & seen_nodes:
            return False

        seen_nodes.update(G.nodes)

    return True
###########

# User's inputs
device_name = sys.argv[1]
iteration = int(sys.argv[2])
config_name = sys.argv[3]
desired_tiles = sys.argv[4:]

# init device
device = Arch(device_name)

# create relocation_storage
rloc_collection = RLOC_Collection(device, iteration, overwrite=False)

# create and fill configurations
for file in rloc_collection.minimal_configs:
    minimal_TC = util.load_data(cfg.minimal_config_path, file)
    TC = rloc_collection.create_TC()

    G_tiles = len(desired_tiles) * [nx.DiGraph()]
    for idx, desired_tile in enumerate(desired_tiles):
        print(f'{idx} / {len(desired_tiles)}')
        for cut in minimal_TC.CUTs:
            if cut.index == len(minimal_TC.CUTs) - 1:
                if list(device.tiles_map[nd.get_coordinate(desired_tile)].values())[0] is None:
                    alter_path = str(Path(cfg.minimal_config_path).parent / 'iter3')
                    alt_minimal_TC = util.load_data(alter_path, file)
                    cut = alt_minimal_TC.CUTs[-1]
                elif list(device.tiles_map[nd.get_coordinate(desired_tile)].values())[-1] is None:
                    alter_path = str(Path(cfg.minimal_config_path).parent / 'iter2')
                    alt_minimal_TC = util.load_data(alter_path, file)
                    cut = alt_minimal_TC.CUTs[-1]
                else:
                    pass

            elif not RLOC.check_tile_compliance(device.tiles_map, cut.G, cut.origin, nd.get_coordinate(desired_tile)):
                continue

            d_cut = D_CUT(nd.get_coordinate(desired_tile), device.tiles_map, cut, iteration=rloc_collection.iteration)

            if TC.check_LUT_util(d_cut) and TC.check_FF_util(d_cut):
                TC.add_D_CUT(rloc_collection, d_cut)
                G_tiles[idx] = nx.compose(G_tiles[idx], d_cut.G)

    if check_node_collision(G_tiles):
        util.store_data(cfg.config_path, f'{config_name}.data', TC)