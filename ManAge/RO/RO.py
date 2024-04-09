import sys, os
import networkx as nx
from itertools import product
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.node import Node as nd
from xil_res.router import extract_node_disjoint_paths
from xil_res.architecture import Arch
from xil_res.minimal_config import MinConfig
from xil_res.cut import CUT
from constraint.configuration import ConstConfig
import utility.utility_functions as util
import utility.config as cfg

# Graph
G = util.load_data(cfg.graph_path, 'G_xczu9eg_INT_X46Y90.data')

# one coordinate
invalid_nodes = set(filter(lambda node: nd.get_coordinate(node) != 'X46Y90', G))
G.remove_nodes_from(invalid_nodes)

# 16 ROs to i6
pairs = []
sources = list(filter(lambda x: cfg.CLB_out_pattern.match(x), G))
for src in sources:
    tile = nd.get_tile(src)
    label = nd.get_label(src)
    pair = (src, nd.get_LUT_input(tile, label, 6))
    pairs.append(pair)


all_paths_16 = extract_node_disjoint_paths(G, pairs)

# verify collision
G_net = nx.DiGraph()
for path in all_paths_16:
    edges = zip(path, path[1:])
    G_net.add_edges_from(edges)

conflicts = {node for node in G_net if G_net.in_degree(node) > 1}

assert not conflicts, 'Collission occured!'

'''
# 32 ROs
pairs = []
sink_nodes = []
sources = list(filter(lambda x: cfg.CLB_out_pattern.match(x), G))
for src in sources:
    tile = nd.get_tile(src)
    label = nd.get_label(src)
    pair = (src, nd.get_LUT_input(tile, label, 5))
    pairs.append(pair)

sources = list(filter(lambda x: cfg.MUXED_CLB_out_pattern.match(x), G))
for src in sources:
    tile = nd.get_tile(src)
    label = nd.get_label(src)
    sinks = {nd.get_LUT_input(tile, label, i) for i in range(1, 5)}
    sink_node = f't_{nd.get_tile(src)}_{nd.get_port_suffix(src)}'
    sink_nodes.append(sink_node)
    pair = (src, nd.get_LUT_input(tile, label, 4))
    pairs.append(pair)
    G.add_edges_from(product(sinks, {sink_node}))

all_paths_32 = find_disjoint_paths(G, pairs)
G.remove_nodes_from(sink_nodes)

# verify collision
G_net = nx.DiGraph()
for path in all_paths_32:
    edges = zip(path, path[1:])
    G_net.add_edges_from(edges)

assert nx.is_forest(G_net), 'Collission occured!'
'''

# create device
device = Arch('xczu9eg')

# create a TC
TC = MinConfig(device, 0)


for path in all_paths_16:
    edges = zip(path, path[1:])
    cut = CUT()

    # create graph
    cut.create_CUT_G_from_edges(*edges)

    # create subLUTs
    cut.create_CUT_subLUTs(TC)

    TC.CUTs.append(cut)

# create constraint configuration
const_conf = ConstConfig(len(TC.CUTs))

# change cell and net names


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

print('end')