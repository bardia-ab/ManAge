import os, re, sys, csv
import pandas as pd
import networkx as nx
import numpy as np
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
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
    wires_dict = remove_clb_wires(wires_dict)
    rloc_wires_dict = get_rloc_wires_dict(wires_dict)
    del wires_dict

    for tile, rloc_wires in rloc_wires_dict.items():
        if rloc_wires not in wires_types:
            wires_types.append(rloc_wires)
            util.extend_dict(parsed_dict, frozenset(rloc_wires), tile, value_type='set')
        else:
            parsed_dict[frozenset(rloc_wires)].add(tile)


    parsed_dict = merge_values_based_on_subset_keys(parsed_dict)
    for idx, key in enumerate(parsed_dict.copy()):
        parsed_dict[f'Type{idx + 1}'] = parsed_dict[key]
        del parsed_dict[key]

    return parsed_dict

def parse_slice_types(CLBs, site_dict):
    slice_type = {}
    for clb in CLBs:
        util.extend_dict(slice_type, f'SLICE {nd.get_site_type(clb)}', site_dict[clb])

    return slice_type

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

def remove_clb_wires(wires_dict):
    wires_dict = {k: v for k, v in wires_dict.items() if nd.get_tile_type(k) == 'INT'}
    for tile, wires in wires_dict.items():
        wires_dict[tile] = set(filter(lambda wire: all(map(lambda node: nd.get_tile_type(node) == 'INT', wire)), wires))

    return wires_dict

def read_intent_code_files(files_path):
    nodes_dict = {}
    for file in Path(files_path).glob('*'):
        with open(str(file)) as lines:
            for line in lines:
                if line.startswith('\n'):
                    continue

                value = line.rstrip('\n')
                if nd.get_coordinate(value) != 'X46Y90':
                    continue

                util.extend_dict(nodes_dict, file.stem, value)

    return nodes_dict

def store_intent_code_table(nodes_dict, store_file):
    dct = {}
    for intent_code in nodes_dict:

        for node in nodes_dict[intent_code]:
            regex = nd.get_port(get_regex(node))
            if intent_code not in dct:
                dct[intent_code] = {}
            if regex not in dct[intent_code]:
                dct[intent_code].update({regex: 1})
            else:
                dct[intent_code][regex] += 1

        df = pd.DataFrame(dct)
        df.replace(np.nan, 0, inplace=True)
        df = df.astype(int)
        # Escape regex patterns for LaTeX
        #df.index = df.index.map(lambda x: re.escape(x))

        df.to_csv(store_file)
        latex_table = df.to_latex()
        latex_file = str(Path(store_file).with_suffix('.txt'))
        with open(latex_file, 'w') as file:
            file.write(latex_table)

def get_pips_dict(pips):
    G_pip = nx.DiGraph()
    G_pip.add_edges_from(pips)

    pips_dict = {}
    for pipjunc in G_pip:
        pipjunc_regex = get_regex(pipjunc)
        if pipjunc_regex not in pips_dict:
            pips_dict[pipjunc_regex] = {'DS': set(), 'US': set()}

        for neigh in G_pip.neighbors(pipjunc):
            pips_dict[pipjunc_regex]['DS'].add(get_regex(neigh))

        for pred in G_pip.predecessors(pipjunc):
            pips_dict[pipjunc_regex]['US'].add(get_regex(pred))

    return pips_dict

def sort_pips_dict(pips_dict):
    for pipjunc, types in pips_dict.items():
        for type, neighs in types.items():
            pips_dict[pipjunc][type] = sorted(neighs)

def filter_pips_dict(pips_dict, mode):
    if mode == 'downstream':
        return {k: v for k,v in pips_dict.items() if not v['US'] and v['DS']}
    elif mode == 'upstream':
        return {k: v for k,v in pips_dict.items() if  v['US'] and not v['DS']}
    elif mode == 'both':
        return {k: v for k,v in pips_dict.items() if  v['US'] and v['DS']}
    else:
        raise ValueError(f'{mode}: Unsupported mode!')

def pipjunc_csv(pips_dict, csv_file):
    # Define markers for each inner key
    markers = {
        'DS': 'D',  # Or any other marker for Key1
        'US': 'U'  # Or any other marker for Key2
    }

    # Get all unique column headers
    all_columns = sorted(set(col for row in pips_dict.values() for cols in row.values() for col in cols))

    # Write to CSV
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow([''] + all_columns)

        # Write rows
        for outer_key, inner_dict in pips_dict.items():
            row = [outer_key] + [''] * len(all_columns)
            for inner_key, cols in inner_dict.items():
                for col in cols:
                    index = all_columns.index(col) + 1
                    row[index] += markers[inner_key]
            writer.writerow(row)

def pipjunc_latex(pips_dict, latex_file):
    # Get all unique column headers
    all_columns = sorted(set(col for row in pips_dict.values() for cols in row.values() for col in cols))

    latex_table = """
    \\begin{table}[h]
    \\centering
    \\caption{Generated Table}
    \\begin{tabular}{|c|""" + "c|" * len(all_columns) + """}
    \\hline
    """

    # Write the header
    latex_table += " & " + " & ".join(all_columns) + " \\\\\n\\hline\n"

    # Define LaTeX color commands for ticks
    latex_markers = {
        'DS': '\\textcolor{red}{\\checkmark}',  # Red tick for Key1
        'US': '\\textcolor{blue}{\\checkmark}'  # Blue tick for Key2
    }

    # Write the rows
    for outer_key, inner_dict in pips_dict.items():
        row = [outer_key] + [''] * len(all_columns)
        for inner_key, cols in inner_dict.items():
            for col in cols:
                index = all_columns.index(col) + 1
                row[index] += latex_markers[inner_key]
        latex_table += " & ".join(row) + " \\\\\n\\hline\n"

    latex_table += """
    \\end{tabular}
    \\end{table}
    \\end{document}
    """

    # Save LaTeX table to a text file
    with open(latex_file, 'w') as f:
        f.write(latex_table)


def get_node_head(wires, desired_tile):
    wires_dict_regex = {}
    for wire in wires:
        if nd.get_tile(wire[0]) != desired_tile:
            continue

        key = get_regex(nd.get_port(wire[0]))
        value = get_regex(nd.get_port(wire[1]))
        util.extend_dict(wires_dict_regex, key, value, value_type='set')

    return wires_dict_regex

def get_regex(node: str) -> str:

    regexp = re.sub(r'(?<!EE|NN|SS|WW)(?<!\d)\d+', '#', node)
    regexp = re.sub(r'(?<!SITE_#)_[EW]_', '_[EW]_', regexp)
    regexp = re.sub('_[EW]#', '_[EW]#', regexp)
    regexp = re.sub('_(BLN|BLS)_', '_(BLN|BLS)_', regexp)
    regexp = regexp.replace('#', '\d+')
    regexp = re.sub(r'SITE_\\d\+_[A-H]', 'SITE_0_[A-H]', regexp)
    regexp = re.sub(r'Q\\d\+', 'Q2', regexp)

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