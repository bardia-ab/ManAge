import os, re, sys
from pathlib import Path
from joblib import Parallel, delayed
from xil_res.architecture import Arch
from constraint.configuration import ConstConfig
import constraint.CUTs_VHDL_template  as tmpl
from constraint.net import Net
import utility.config as cfg
import utility.utility_functions as util
from tqdm import tqdm

device_name = sys.argv[1]
TC_file = sys.argv[2]
clock_region = sys.argv[3]
max_CUTs = int(sys.argv[4])
store_path = sys.argv[5]

# load the device
device = Arch(device_name)

#
config_path, file = str(Path(TC_file).parent), Path(TC_file).name

# load configuration
TC_idx = Path(TC_file).stem
TC = util.load_data(config_path, file)
CUTs = filter(lambda x: x.origin in device.get_CR(clock_region).coords, TC.D_CUTs)
CUTs = sorted(CUTs, key=lambda x: (x.index, x.get_x_coord(), x.get_y_coord()))

if max_CUTs != -1:
    CUTs = CUTs[:max_CUTs]

# create a configuration for constraints
N_CUTs = len(CUTs)
configuration = ConstConfig(N_CUTs)

# pbar
pbar = tqdm(total=N_CUTs)

# populate the configuration
for idx, cut in enumerate(CUTs):

    # CUT stats
    CUT_idx = idx % cfg.N_Parallel
    Seg_idx = idx // cfg.N_Parallel
    w_Error_Mux_In = f'w_Error({Seg_idx})({CUT_idx})'

    try:
        # fill nets
        configuration.fill_nets(cut, idx)
    except ValueError as e:
        print(f'TC{TC_idx}>>CUT{cut.index}')
        continue

    # fill cells
    configuration.fill_cells(device.site_dict, cut, idx)

    # VHDL instantiation
    g_buffer = Net.get_g_buffer(cut.G)
    VHDL_codes = tmpl.get_instantiation(idx, 'i_Clk_Launch', 'i_Clk_Sample', 'i_CE', 'i_CLR', w_Error_Mux_In, g_buffer)
    configuration.VHDL_file.add_components(''.join(VHDL_codes))

    pbar.update(1)

# print constraints
Path(store_path).mkdir(parents=True, exist_ok=True)
configuration.print_src_files(store_path)

print('hi')