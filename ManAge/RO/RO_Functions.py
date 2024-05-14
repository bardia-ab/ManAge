import copy
import os, sys
import networkx as nx
from itertools import product
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.node import Node as nd
from xil_res.path import Path
import utility.utility_functions as util
import utility.config as cfg


def get_ROs(G: nx.DiGraph):
    G_copy = copy.deepcopy(G)
    blocked_nodes = set()
    ROs = []
    sources = filter(lambda node: cfg.CLB_out_pattern.match(node), G_copy)

    for src in sources:
        for index in range(5, 0, -1):
            sink = nd.get_LUT_input(nd.get_tile(src), nd.get_label(src), index)
            try:
                path = Path.path_finder(G_copy, src, sink, weight='weight', blocked_nodes=blocked_nodes)
                break
            except:
                pass
        else:
            continue

        blocked_nodes.update(path)
        ROs.append(path)

    return ROs

def get_ROs2(G: nx.DiGraph):
    G_copy = copy.deepcopy(G)
    blocked_nodes = set()
    ROs = []
    sources = list(filter(lambda node: cfg.CLB_out_pattern.match(node), G_copy))

    for src in sources:
        sinks = (nd.get_LUT_input(nd.get_tile(src), nd.get_label(src), index) for index in range(1,6))
        G_copy.add_edges_from(product(sinks, {'t'}))
        try:
            path = Path.path_finder(G_copy, src, 't', weight='weight', blocked_nodes=blocked_nodes, dummy_nodes=['t'])
            blocked_nodes.update(path)
            ROs.append(path)
        except:
            pass

        G_copy.remove_node('t')

    return ROs

def get_antennas(G:nx.DiGraph, all_paths):
    antennas = []
    G_copy = copy.deepcopy(G)
    used_nodes = {node  for path in all_paths for node in path}
    G_copy.remove_edges_from(get_in_edges(G_copy, *all_paths))

    # remove route thrus
    route_thrus = [edge for edge in G_copy.edges if cfg.LUT_in_pattern.match(edge[0])]
    G_copy.remove_edges_from(route_thrus)

    muxed_outputs = list(filter(lambda node: cfg.MUXED_CLB_out_pattern.match(node), G_copy))

    G_copy.add_edges_from(product({'s'}, muxed_outputs))
    sinks = list(filter(lambda x: nd.get_INT_node_mode(G_copy, x) == 'out' and nd.get_tile_type(x) == 'INT', G_copy))
    G_copy.add_edges_from(product(sinks, {'t'}))

    paths = nx.node_disjoint_paths(G_copy, 's', 't')
    try:
        paths = [path[1:-1] for path in paths]
    except:
        return antennas

    G_copy.remove_edges_from(get_in_edges(G_copy, *paths))
    G_copy.remove_nodes_from({'s', 't'})
    antennas += paths
    used_nodes.update(node for path in paths for node in path)

    sinks = list(filter(lambda x: nd.get_INT_node_mode(G_copy, x) == 'out' and nd.get_tile_type(x) == 'INT', G_copy))
    while sinks:
        sinks = [node for node in sinks if node not in used_nodes]
        G_copy.add_edges_from(product({'s'}, used_nodes))
        G_copy.add_edges_from(product(sinks, {'t'}))
        paths = nx.node_disjoint_paths(G_copy, 's', 't')
        try:
            paths = [path[1:-1] for path in paths]
        except:
            return antennas

        if paths:
            G_copy.remove_edges_from(get_in_edges(G_copy, *paths))
            G_copy.remove_nodes_from({'s', 't'})
            antennas += paths
            used_nodes.update(node for path in paths for node in path)
        else:
            break

    return antennas

def get_in_edges(G, *paths):
    in_edges = set()
    for path in paths:
        for node in path:
            in_edges.update(G.in_edges(node))

    return in_edges