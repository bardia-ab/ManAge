import os.path
from pathlib import Path
import sys
from xil_res.architecture import Arch
from xil_res.node import Node as nd
import processing.plot as plot
import arch.analysis as an
import utility.config as cfg
import utility.utility_functions as util

# initialize device
device_name = sys.argv[1]
desired_tile = 'INT_X46Y90'

device = Arch(device_name)

# create folder
store_path = Path(cfg.Data_path) / 'Analysis'
store_path.mkdir(exist_ok=True)
store_path = str(store_path)

'''# draw tiles_map heatmap
parsed_tiles_map = an.parse_tiles_map(device.tiles_map)
filename = 'tiles_map'
plot.print_heatmap_tiles_map(parsed_tiles_map, store_path=store_path, filename=filename)
'''

'''# draw wires_dict heatmap
parsed_wires_dict = an.parse_wires_dict(device.wires_dict)
filename = 'wires_dict'
plot.print_heatmap_wires_dict(parsed_wires_dict, store_path=store_path, filename=filename)
'''

'''slice_type = an.parse_slice_types(device.get_CLBs(), device.site_dict)
filename = 'slice_type'
plot.print_heatmap_tiles_map(slice_type, store_path=store_path, filename=filename)
'''
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

an.get_regex('CLEM_X6Y112/CLE_CLE_M_SITE_0_E3')
an.get_regex('CLEM_X6Y112/CLE_CLE_M_SITE_0_A3')

wires_dict_regex = an.get_node_head(device.wires_dict[desired_tile], desired_tile)

bln = [wire for wire in device.wires_dict[desired_tile] if nd.get_tile(wire[0]) == desired_tile and 'BLN' in wire[1]]
bls = [wire for wire in device.wires_dict[desired_tile] if nd.get_tile(wire[0]) == desired_tile and 'BLS' in wire[1]]

bln_disloc = {(nd.get_x_coord(wire[1]) - nd.get_x_coord(wire[0]), nd.get_y_coord(wire[1]) - nd.get_y_coord(wire[0])) for wire in bln}
bls_disloc = {(nd.get_x_coord(wire[1]) - nd.get_x_coord(wire[0]), nd.get_y_coord(wire[1]) - nd.get_y_coord(wire[0])) for wire in bls}

print('hi')