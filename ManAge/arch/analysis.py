import os, re
os.chdir(os.path.abspath('..'))
import utility.utility_functions as util
from xil_res.node import Node as nd

def parse_tiles_map(tiles_map):
    # (CLB_W, INT, None) : {INT_X#Y#, }
    parsed_dict = {}
    for origin, map in tiles_map.items():
        key = tuple(k if v is not None else None for k, v in map.items())
        util.extend_dict(parsed_dict, key, origin, value_type='set')

    return parsed_dict

def parse_wires_dict(wires_dict):
    ''' Type1: {INT_X#Y#, } '''
    wires_types = []
    parsed_dict = {}
    rloc_wires_dict = get_rloc_wires_dict(wires_dict)
    del wires_dict
    i = 0
    for tile, rloc_wires in rloc_wires_dict.items():
        if not tile.startswith('INT_X'):
            continue

        i += 1
        print(i)

        if not wires_types:
            key = 'Type 1'
            wires_types.append(rloc_wires)
            util.extend_dict(parsed_dict, frozenset(rloc_wires), tile, value_type='set')
            continue

        '''for idx, wire_type in enumerate(wires_types):
            if rloc_wires.issubset(wire_type):
                key = f'Type{idx + 1}'
            elif rloc_wires.issuperset(wire_type):
                wires_types[idx] = rloc_wires
                key = f'Type{idx + 1}'
            else:
                wires_types.append(rloc_wires)
                key = f'Type {len(wires_types)}'

            util.extend_dict(parsed_dict, key, tile, value_type='set')'''

        if rloc_wires in wires_types:
            key = f'Type{wires_types.index(rloc_wires) + 1}'
        else:
            wires_types.append(rloc_wires)
            key = f'Type {len(wires_types)}'

        util.extend_dict(parsed_dict, frozenset(rloc_wires), tile, value_type='set')

    parsed_dict = merge_values_based_on_subset_keys(parsed_dict)
    parsed_dict1 = {}
    for idx, key in enumerate(parsed_dict):
        parsed_dict1[f'Type{idx + 1}'] = parsed_dict[key]

    return parsed_dict1

def merge_values_based_on_subset_keys(data):
    # Prepare a list of keys for iteration, to avoid "dictionary changed size during iteration" error
    keys = list(data.keys())

    # Initialize a set to keep track of keys to be removed after merging
    keys_to_remove = set()

    for i, key_i in enumerate(keys):
        print(f'*{i}')
        for key_j in keys[i + 1:]:
            # Check if key_i is a subset of key_j
            if key_i.issubset(key_j):
                # Merge values of key_i into values of key_j
                data[key_j].update(data[key_i])
                # Mark key_i for removal
                keys_to_remove.add(key_i)
            # Check if key_j is a subset of key_i
            elif key_j.issubset(key_i):
                # Merge values of key_j into values of key_i
                data[key_i].update(data[key_j])
                # Mark key_j for removal
                keys_to_remove.add(key_j)

    # Remove keys that were subsets
    for key in keys_to_remove:
        del data[key]

    return data

def get_rloc_wires_dict(wires_dict):
    rloc_wires_dict = {}
    for tile, wires in wires_dict.items():
        rloc_wires = {tuple(map(lambda node: nd.get_RLOC_node(node, tile), wire)) for wire in wires}
        rloc_wires_dict[tile] = rloc_wires.copy()

    return rloc_wires_dict

def get_regex(node: str) -> str:

    regexp = re.sub(r'(?<!EE|NN|SS|WW)(?<!\d)\d+', '#', node)
    regexp = re.sub('_[EW]_', '_[EW]_', regexp)
    regexp = re.sub('_[EW]#', '_[EW]#', regexp)
    regexp = re.sub('_(BLN|BLS)_', '_(BLN|BLS)_', regexp)
    regexp = regexp.replace('#', '\d+')

    return regexp

def draw_node_sub_graph(G, node):
    G1 = nx.DiGraph()
    G1.add_edges_from(G.in_edges(node))
    G1.add_edges_from(G.out_edges(node))

    pos = nx.spring_layout(G1)
    #label_pos = {node: (x, y + 5) for node, (x, y) in pos.items()}
    nx.draw(G1, pos, with_labels=False, node_size=30000, node_shape="s", node_color="skyblue")
    node_labels = {node: node for node in G1.nodes()}  # Assuming node labels are the same as node identifiers
    nx.draw_networkx_labels(G1, pos, labels=node_labels, font_size=10, font_color="black")
    plt.show()

if __name__ == '__main__':
    from xil_res.architecture import Arch
    import matplotlib.pyplot as plt
    import numpy as np
    import networkx as nx

    device = Arch('xczu3eg')


    G = nx.DiGraph()
    node_dict = {}

    '''for pip in device.pips:
        for node in pip:
            if get_regex(node) not in node_dict:
                node_dict[get_regex(node)] = f'Node{len(node_dict) + 1}'

        G.add_edge(node_dict[get_regex(pip[0])], node_dict[get_regex(pip[1])])'''

    G.add_edges_from(device.pips)

    #draw_node_sub_graph(G, 'SS1_[EW]_BEG\\d+')

    # Generate the adjacency matrix
    adj_matrix = nx.adjacency_matrix(G)

    # Convert the sparse matrix to a NumPy array for easier manipulation (if needed)
    adj_matrix_array = adj_matrix.toarray()

    rank = np.linalg.matrix_rank(adj_matrix_array)

    print("Rank of the adjacency matrix:", rank)

    print('hi')