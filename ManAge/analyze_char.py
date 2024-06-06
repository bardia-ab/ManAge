import os, sys, subprocess
from pathlib import Path
from tqdm import tqdm
from xil_res.architecture import Arch
import utility.config as cfg

device_name = sys.argv[1]
TCs_path = sys.argv[2]
TCs_result_path = sys.argv[3]
iteration = int(sys.argv[4])
store_path = sys.argv[5]

device = Arch(device_name)


# create cuts_list
store_file = Path(store_path) / f'iter{iteration}' / 'cuts_list.data'
script = str(Path(__file__).parent / 'processing' / 'populate_cut_delays.py')
#subprocess.run([cfg.python, script, TCs_path, TCs_result_path, 'None', store_file], capture_output=False, text=True, encoding='utf-8')

# create heatmap
cuts_list_file = store_file
heatmap_store_path = Path(cuts_list_file).parent.parent.parent / 'heatmap' / f'iter{iteration}'
store_file_suffix = 'X2Y1'
xmin, xmax, ymin, ymax = device.get_device_dimension()
xmin = str(xmin)
xmax = str(xmax)
ymin = str(ymin)
ymax = str(ymax)
script = str(Path(__file__).parent / 'processing' / 'delay_heatmap.py')
#subprocess.run([cfg.python, script, cuts_list_file, heatmap_store_path, store_file_suffix, xmin, xmax, ymin, ymax], capture_output=False,
               #text=True, encoding='utf-8')

# create diff heatmap
ref_cuts_list_file = Path(store_path) / 'iter0' / 'cuts_list.data'
heatmap_store_path = Path(cuts_list_file).parent.parent.parent / 'heatmap_diff' / f'iter{iteration}'
script = str(Path(__file__).parent / 'processing' / 'diff_delay_heatmap.py')
#subprocess.run([cfg.python, script, ref_cuts_list_file, cuts_list_file, heatmap_store_path, store_file_suffix, xmin, xmax, ymin, ymax],
               #capture_output=False, text=True, encoding='utf-8')

# compare ageing
ref_cuts_list_file = Path(store_path) / 'iter0' / 'cuts_list.data'
cuts_list_file = Path(store_path) / f'iter{iteration}' / 'cuts_list.data'
df_store_path = Path(store_path).parent / 'diff_CUTs_list' / f'iter{iteration}'
df_file_name = f'cuts_list.data'
script = str(Path(__file__).parent / 'processing' / 'compare_Ageing.py')
subprocess.run([cfg.python, script, ref_cuts_list_file, cuts_list_file, df_store_path, df_file_name],
               capture_output=False, text=True, encoding='utf-8')