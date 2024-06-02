import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from processing.data_process import *
from joblib import Parallel, delayed
from itertools import chain
from tqdm import tqdm
from processing.cut_delay import CUTs_List
import utility.utility_functions as util


# User inputs
TCs_path = sys.argv[1]
TCs_result_path = sys.argv[2]
skew_path = sys.argv[3]
store_file = sys.argv[4]

if skew_path == 'None':
    skew_path = None

# create store path
cut_list_path = Path(store_file).parent
file_name = Path(store_file).name
cut_list_path.mkdir(parents=True, exist_ok=True)

invalid_TCs = get_invalid_TCs(TCs_result_path)
valid_TC_results = list(filter(lambda x: x.stem not in invalid_TCs, Path(TCs_result_path).glob('TC*')))

# populate CUTs list
cuts_list = CUTs_List([])
pbar = tqdm(total=len(valid_TC_results))
cuts_list.CUTs = list(chain(*Parallel(n_jobs=4, require='sharedmem')(delayed(fill_cuts_list)(TCs_result_path, TCs_path, TC, pbar, skew_path) for TC in map(lambda x: x.stem, valid_TC_results))))

# store
util.store_data(str(cut_list_path), file_name, cuts_list)