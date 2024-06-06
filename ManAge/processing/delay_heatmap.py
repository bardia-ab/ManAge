import os, sys, time
from pathlib import Path
from tqdm import tqdm
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from processing.plot import print_heatmap
from xil_res.node import Node as nd
import utility.config as cfg
import utility.utility_functions as util

cuts_list_file = sys.argv[1]
store_path = sys.argv[2]
store_file_suffix = sys.argv[3]
xmin = int(sys.argv[4])
xmax = int(sys.argv[5])
ymin = int(sys.argv[6])
ymax = int(sys.argv[7])

# store folder
Path(store_path).mkdir(parents=True, exist_ok=True)

# load cuts list
cuts_list_path, file = str(Path(cuts_list_file).parent), Path(cuts_list_file).name
cuts_list = util.load_data(cuts_list_path, file)

# get rising & falling dicts
avg_rising_dict, avg_falling_dict = cuts_list.get_delay_dicts()

# create heatmaps
boundary = {'xmin': xmin, 'xmax': xmax, 'ymin': ymin, 'ymax': ymax}
coords = set(avg_rising_dict.keys())
rows = {nd.get_y_coord(coord) for coord in coords}
columns = {nd.get_x_coord(coord) for coord in coords}

store_file = str(Path(store_path) / f'rising_{store_file_suffix}.pdf')
print_heatmap(avg_rising_dict, coords, rows, columns, store_file, palette='rocket', xlabel='FPGA Rows', ylabel='FPGA Columns', apply_type=False)

store_file = str(Path(store_path) / f'falling_{store_file_suffix}.pdf')
print_heatmap(avg_falling_dict, coords, rows, columns, store_file, palette='rocket', xlabel='FPGA Rows', ylabel='FPGA Columns', apply_type=False)