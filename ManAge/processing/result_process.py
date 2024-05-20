import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from processing.data_process import get_invalid_TCs, fill_cuts_list
from processing.cut_delay import CUTs_List
import utility.config as cfg
import utility.utility_functions as util

# User inputs
TCs_path = sys.argv[1]
TCs_result_path = sys.argv[2]
skew_path = sys.argv[3]
store_path = sys.argv[4]

# create store path
cut_list_path = str(Path(store_path) / 'CUTs_list')
util.create_folder(cut_list_path)

invalid_TCs = get_invalid_TCs(TCs_result_path)
TCs = list(filter(lambda x: x.startswith('TC') and x not in invalid_TCs, os.listdir(TCs_result_path)))

# populate CUTs list
cuts_list = CUTs_List([])
for TC in TCs:
    cuts_list.CUTs.extend(fill_cuts_list(TCs_result_path, TCs_path, cfg.N_Parallel, TC))