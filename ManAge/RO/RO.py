import sys, os
import networkx as nx
from itertools import product
from RO_Functions import *
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.architecture import Arch
from xil_res.test_storage import TestCollection
from xil_res.minimal_config import MinConfig
from xil_res.cut import CUT
from constraint.configuration import ConstConfig
import utility.utility_functions as util
import utility.config as cfg

# desired_tile
desired_tile = 'INT_X46Y90'

# create device
device = Arch('xczu9eg')
device.set_compressed_graph(desired_tile)

# one coordinate
invalid_nodes = set(filter(lambda node: nd.get_coordinate(node) != 'X46Y90', device.G))
device.G.remove_nodes_from(invalid_nodes)

# get RO paths
all_paths = get_ROs2(device.G)
antennas = get_antennas(device.G, all_paths)

edges = set()
for path in all_paths + antennas:
    edges.update(zip(path, path[1:]))

G_netlist = nx.DiGraph()
G_netlist.add_edges_from(edges)

assert nx.is_forest(G_netlist), "Collision Occured!!!"

# test storage
test_collection = TestCollection(iteration=1, desired_tile=desired_tile, queue=set())

# create a TC
#TC = MinConfig(device, 0)
test_collection.create_TC(device)
TC = test_collection.TC

for path in all_paths:
    edges = zip(path, path[1:])
    cut = CUT(origin=nd.get_coordinate(desired_tile), cut_index=len(TC.CUTs))

    # create graph
    cut.create_CUT_G_from_edges(*edges)

    # create subLUTs
    cut.create_CUT_subLUTs(TC)

    TC.CUTs.append(cut)

# add antennas
edges = set()
for path in antennas:
    edges.update(zip(path, path[1:]))

cut = CUT(origin=nd.get_coordinate(desired_tile), cut_index=len(TC.CUTs))

# create graph
cut.create_CUT_G_from_edges(*edges)

# create subLUTs
cut.create_CUT_subLUTs(TC)

TC.CUTs.append(cut)

test_collection.store_TC()
'''
# create constraint configuration
const_conf = ConstConfig(len(TC.CUTs))

for idx, cut in enumerate(TC.CUTs):

    # fill nets
    const_conf.fill_nets(cut, idx)

    # change net name
    const_conf.nets[-1].name = f'O6[{idx}]'

    # fill cells
    const_conf.fill_cells(device.site_dict, cut, idx)

    # change cell name
    const_conf.cells[-1].cell_name = f'RO[{idx}].LUT6_inst'
    const_conf.cells[-1].type = 'None'

const_conf.print_constraints('.')
'''
print('end')