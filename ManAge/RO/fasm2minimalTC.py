import sys, os
import networkx as nx
from itertools import product
from bidict import bidict
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.node import Node as nd
from xil_res.router import extract_node_disjoint_paths
from xil_res.test_storage import TestCollection
from xil_res.architecture import Arch
from xil_res.minimal_config import MinConfig
from xil_res.cut import CUT
from constraint.configuration import ConstConfig
from constraint.FASM import *
import utility.utility_functions as util
import utility.config as cfg

# user inputs
device_name = sys.argv[1]
desired_tile    = sys.argv[2]
iteration       = int(sys.argv[3])
fasm_file = sys.argv[4]

test_collection = TestCollection(iteration=iteration, desired_tile=desired_tile, queue=set())

# create device
device = Arch(device_name)
device.set_compressed_graph(desired_tile)

# create a TC
TC = MinConfig(device, 0)
test_collection.TC = TC

G = get_FASM_graph(device, fasm_file)

pips = {edge for edge in G.edges if nd.get_tile(edge[0]) == nd.get_tile(edge[1])}

# used tiles
used_tiles = {nd.get_tile(node) for pip in pips for node in pip}
wires_dict_light = {k: v for k, v in device.wires_dict.items() if k in used_tiles}
wires_dict = bidict({k: v for key, value in wires_dict_light.items() for (k, v) in value})

# add source and sink nodes
clb_out_neighs = list(filter(lambda x: re.match('.*LOGIC_OUTS.*', x), G))
LUT_ins = list(filter(lambda x: re.match('.*/IMUX.*', x) and nd.is_i6(wires_dict[x]), G))
sources = product({'s'}, clb_out_neighs)
sinks = product(LUT_ins, {'t'})
G.add_edges_from(sources)
G.add_edges_from(sinks)

# find ROs
RO_paths = list(nx.all_simple_paths(G, 's', 't'))
RO_paths = [path[1:-1] for path in RO_paths]

# remove s and t grom G
G.remove_nodes_from({'s', 't'})

for i in range(len(RO_paths)):
    RO_paths[i].insert(0, next(device.G.predecessors(RO_paths[i][0])))
    RO_paths[i].append(next(device.G.neighbors(RO_paths[i][-1])))

# load antennas
#antennas = util.load_data(CWD, 'antennas.data')
RO_edges = {edge for path in RO_paths for edge in zip(path, path[1:])}
antennas = {edge for edge in G.edges if edge not in RO_edges}

for index, path in enumerate(RO_paths):
    edges = zip(path, path[1:])
    cut = CUT(cut_index=index, origin=nd.get_coordinate(desired_tile))

    # create graph
    cut.create_CUT_G_from_edges(*edges)

    # create subLUTs
    cut.create_CUT_subLUTs(TC)

    TC.CUTs.append(cut)

# add a CUT for antennas
cut = CUT(cut_index=len(TC.CUTs), origin=nd.get_coordinate(desired_tile))
cut.create_CUT_G_from_edges(*antennas)
TC.CUTs.append(cut)

test_collection.store_TC()