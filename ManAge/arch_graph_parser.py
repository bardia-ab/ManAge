import copy
import os.path
from pathlib import Path
import sys
from xil_res.architecture import Arch
from xil_res.node import Node as nd
import processing.plot as plot
import arch.analysis as an
import utility.config as cfg
import utility.utility_functions as util

material_palette = [
    "#03A9F4",  # Light Blue
    "#E91E63",  # Pink
    "#FFC107",  # Amber
    "#8BC34A",  # Light Green
    "#9C27B0",  # Purple
    "#673AB7",  # Deep Purple
    "#3F51B5",  # Indigo
    "#F44336",  # Red
    "#2196F3",  # Blue
    "#00BCD4",  # Cyan
    "#009688",  # Teal
    "#4CAF50",  # Green
    "#CDDC39",  # Lime
    "#FFEB3B",  # Yellow
    "#FF9800",  # Orange
    "#FF5722",  # Deep Orange
    "#795548",  # Brown
    "#9E9E9E",  # Grey
    "#607D8B"   # Blue Grey
]

# initialize device
#device_name = sys.argv[1]
device_name = 'xczu9eg'
desired_tile = 'INT_X46Y90'

device = Arch(device_name)

# create folder
store_path = Path(cfg.Data_path) / 'Analysis'
store_path.mkdir(exist_ok=True)
store_path = str(store_path)

# draw tiles_map heatmap
'''parsed_tiles_map = an.parse_tiles_map(device.tiles_map)
filename = 'tiles_map.pdf'
plot.print_heatmap_tiles_map(parsed_tiles_map, store_path=store_path, filename=filename, palette=material_palette)'''


# draw wires_dict heatmap
parsed_wires_dict = an.parse_wires_dict(device.wires_dict)
filename = 'wires_dict.pdf'
plot.print_heatmap_wires_dict(parsed_wires_dict, store_path=store_path, filename=filename, palette=material_palette)


'''slice_type = an.parse_slice_types(device.get_CLBs(), device.site_dict)
filename = 'slice_type.pdf'
plot.print_heatmap_tiles_map(slice_type, store_path=store_path, filename=filename, palette=material_palette)'''

# Intent Code Names
#intent_code_path = r'C:\Users\t26607bb\Desktop\Practice\Arch_graph\Intent_Code_Names'
'''nodes_dict = an.read_intent_code_files(intent_code_path)
store_file = str(Path(store_path) / 'intent_code.csv')
an.get_regex('CLEM_X46Y90/CLE_CLE_SITE_0_E_O')
an.store_intent_code_table(nodes_dict, store_file)'''


pips_dict = an.get_pips_dict(device.pips)
an.sort_pips_dict(pips_dict)



in_pipjunc_dict = an.filter_pips_dict(pips_dict, 'downstream')
out_pipjunc_dict = an.filter_pips_dict(pips_dict, 'upstream')
both_pipjunc_dict = an.filter_pips_dict(pips_dict, 'both')


'''csv_file = str(Path(store_path) / 'out_pipjunc_dict.csv')
latex_file = str(Path(store_path) / 'out_pipjunc_dict.txt')
an.pipjunc_csv(out_pipjunc_dict, csv_file)
an.pipjunc_latex(pips_dict, latex_file)'''

#an.get_regex('CLEM_X6Y112/CLE_CLE_M_SITE_0_E3')
#an.get_regex('CLEM_X6Y112/CLE_CLE_M_SITE_0_A3')

wires_dict_regex = an.get_node_head(device.wires_dict[desired_tile], desired_tile)

bln = [wire for wire in device.wires_dict[desired_tile] if nd.get_tile(wire[0]) == desired_tile and 'BLN' in wire[1]]
bls = [wire for wire in device.wires_dict[desired_tile] if nd.get_tile(wire[0]) == desired_tile and 'BLS' in wire[1]]

bln_disloc = {(nd.get_x_coord(wire[1]) - nd.get_x_coord(wire[0]), nd.get_y_coord(wire[1]) - nd.get_y_coord(wire[0])) for wire in bln}
bls_disloc = {(nd.get_x_coord(wire[1]) - nd.get_x_coord(wire[0]), nd.get_y_coord(wire[1]) - nd.get_y_coord(wire[0])) for wire in bls}

SDQNODE = [wire for wire in device.wires_dict[desired_tile] if nd.get_tile(wire[0]) == desired_tile and 'SDQNODE' in wire[1]]
INODE = [wire for wire in device.wires_dict[desired_tile] if nd.get_tile(wire[0]) == desired_tile and 'INODE' in wire[1]]
SDQNODE_disloc = {(nd.get_x_coord(wire[1]) - nd.get_x_coord(wire[0]), nd.get_y_coord(wire[1]) - nd.get_y_coord(wire[0])) for wire in SDQNODE}
INODE_disloc = {(nd.get_x_coord(wire[1]) - nd.get_x_coord(wire[0]), nd.get_y_coord(wire[1]) - nd.get_y_coord(wire[0])) for wire in INODE}

N_nodes = len({wire for wires in device.wires_dict.values() for wire in wires})
N_edges = len(device.pips) * len(device.get_INTs()) + len(device.get_CLBs()) * 96
#device.get_graph()
print(len(device.G.edges()))
print(len(device.G.nodes()))


###############
device.set_compressed_graph(desired_tile)
invalid_nodes = [node for node in device.G if nd.get_tile(node) != desired_tile]
device.G.remove_nodes_from(invalid_nodes)
east_nodes = [node for node in device.G if '_E_' in node]
west_nodes = [node for node in device.G if '_W_' in node]

east_G = copy.deepcopy(device.G)
west_G = copy.deepcopy(device.G)

east_G.remove_nodes_from(west_nodes)
west_G.remove_nodes_from(east_nodes)

for edge in copy.deepcopy(east_G.edges):
    edge_1 = []
    for node in edge:
        if '_E_' in node:
            node = node.replace('_E_', '_#_')

        edge_1.append(node)

    east_G.remove_edge(*edge)
    east_G.add_edge(*edge_1)
    
removed_nodes = [node for node in east_G if east_G.in_degree(node) == east_G.out_degree(node) == 0]
east_G.remove_nodes_from(removed_nodes)

for edge in copy.deepcopy(west_G.edges):
    edge_1 = []
    for node in edge:
        if '_W_' in node:
            node = node.replace('_W_', '_#_')

        edge_1.append(node)

    west_G.remove_edge(*edge)
    west_G.add_edge(*edge_1)

removed_nodes = [node for node in west_G if west_G.in_degree(node) == west_G.out_degree(node) == 0]
west_G.remove_nodes_from(removed_nodes)

print('hi')