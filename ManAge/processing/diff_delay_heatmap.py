import os, sys, time
from pathlib import Path
from tqdm import tqdm
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from processing.plot import print_heatmap
from xil_res.node import Node as nd
import utility.config as cfg
import utility.utility_functions as util

ref_cuts_list_file = sys.argv[1]
cuts_list_file = sys.argv[2]
store_path = sys.argv[3]
store_file_suffix = sys.argv[4]
xmin = int(sys.argv[5])
xmax = int(sys.argv[6])
ymin = int(sys.argv[7])
ymax = int(sys.argv[8])

if ref_cuts_list_file == cuts_list_file:
    exit()

# store folder
Path(store_path).mkdir(parents=True, exist_ok=True)

# load refference cuts list
ref_cuts_list_path, ref_file = str(Path(ref_cuts_list_file).parent), Path(ref_cuts_list_file).name
ref_cuts_list = util.load_data(ref_cuts_list_path, ref_file)

# load cuts list
cuts_list_path, file = str(Path(cuts_list_file).parent), Path(cuts_list_file).name
cuts_list = util.load_data(cuts_list_path, file)

# get rising & falling dicts
avg_ref_rising_dict, avg_ref_falling_dict = ref_cuts_list.get_delay_dicts()
avg_rising_dict, avg_falling_dict = cuts_list.get_delay_dicts()

# build diff dictionaries
avg_diff_rising_dict = {coord: avg_rising_dict[coord] - avg_ref_rising_dict[coord] for coord in avg_rising_dict}
avg_diff_falling_dict = {coord: avg_falling_dict[coord] - avg_ref_falling_dict[coord] for coord in avg_falling_dict}

# create heatmaps
boundary = {'xmin': xmin, 'xmax': xmax, 'ymin': ymin, 'ymax': ymax}
coords = set(avg_rising_dict.keys())
rows = {nd.get_y_coord(coord) for coord in coords}
columns = {nd.get_x_coord(coord) for coord in coords}

store_file = str(Path(store_path) / f'diff_rising_{store_file_suffix}.pdf')
print_heatmap(avg_diff_rising_dict, coords, rows, columns, store_file, palette='rocket', xlabel='FPGA Rows', ylabel='FPGA Columns', apply_type=False)

store_file = str(Path(store_path) / f'diff_falling_{store_file_suffix}.pdf')
print_heatmap(avg_diff_falling_dict, coords, rows, columns, store_file, palette='rocket', xlabel='FPGA Rows', ylabel='FPGA Columns', apply_type=False)