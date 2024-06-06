import sys, os, re
import networkx as nx
from itertools import product
from RO_Functions import *
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.architecture import Arch
from xil_res.test_storage import TestCollection
from xil_res.cut import CUT

# User input
device = sys.argv[1]
desired_tile = sys.argv[2]
iteration = int(sys.argv[3])
clk_pips = sys.argv[4]


# create device
device = Arch(device)
device.set_compressed_graph(desired_tile)

# preserve clock PIPs
removed_pips = set()
if Path(clk_pips).exists():
    with open (clk_pips) as file:
        for line in file:
            line = re.split('<*->+', line)
            tile = line[0].split('/')[0]
            pip_u = line[0].split('.')[-1]
            pip_v = line[1].rstrip("\n")
            pip = (f'{tile}/{pip_u}', f'{tile}/{pip_v}')
            removed_pips.add(pip)


# one coordinate
invalid_nodes = set(filter(lambda node: nd.get_coordinate(node) != nd.get_coordinate(desired_tile), device.G))
device.G.remove_nodes_from(invalid_nodes)
device.G.remove_edges_from(removed_pips)

# get RO paths
all_paths = get_ROs3(device.G)
antennas = get_antennas(device.G, all_paths)

edges = set()
for path in all_paths + antennas:
    edges.update(zip(path, path[1:]))

G_netlist = nx.DiGraph()
G_netlist.add_edges_from(edges)

assert nx.is_forest(G_netlist), "Collision Occured!!!"

# test storage
test_collection = TestCollection(iteration=iteration, desired_tile=desired_tile, queue=set())

# create a TC
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