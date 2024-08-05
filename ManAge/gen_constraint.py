import sys, argparse
from pathlib import Path
from tqdm import tqdm

from xil_res.architecture import Arch
from xil_res.minimal_config import MinConfig
from relocation.configuration import Config
from constraint.configuration import ConstConfig
import constraint.CUTs_VHDL_template  as tmpl
from constraint.net import Net
import utility.config as cfg
import utility.utility_functions as util

# Create parser
parser = argparse.ArgumentParser(prog='generate_constraint', description="Generate constraints for specified configurations")

# Arguments
parser.add_argument('device_name', choices=Arch.get_models(), help='Specify the fabric of the FPGA')
parser.add_argument('config_file', help="Specify the path to the configuration file")
parser.add_argument('store_dir', help="Specify the directory to store output files")

parser.add_argument('-c', '--CUTs_count', type=int, help="Limit the number of CUTs whose constraints are desired to be generated")

if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    # load the device
    device = Arch(args.device_name)

    # load configuration
    config_path, file = str(Path(args.config_file).parent), Path(args.config_file).name
    TC_idx = Path(args.config_file).stem
    TC = util.load_data(config_path, file)
    if type(TC) == MinConfig:
        CUTs = TC.CUTs
    elif type(TC) == Config:
        CUTs = TC.D_CUTs
    else:
        raise ValueError(f'Invalid TC specified.')

    CUTs.sort(key=lambda x: (x.index, x.get_x_coord(), x.get_y_coord()))

    # Limit CUTs
    if args.CUTs_count is not None:
        CUTs = CUTs[:args.CUTs_count]

    # Create a configuration for constraints
    N_CUTs = len(CUTs)
    configuration = ConstConfig(N_CUTs)

    # pbar
    pbar = tqdm(total=N_CUTs)

    # Populate the configuration
    for idx, cut in enumerate(CUTs):

        # CUT stats
        CUT_idx = idx % cfg.N_Parallel
        Seg_idx = idx // cfg.N_Parallel
        w_Error_Mux_In = f'w_Error({Seg_idx})({CUT_idx})'

        try:
            # Fill nets
            configuration.fill_nets(cut, idx)
        except ValueError as e:
            print(f'TC{TC_idx}>>CUT{cut.index}')
            continue

        # Fill cells
        configuration.fill_cells(device.site_dict, cut, idx)

        # VHDL instantiation
        g_buffer = Net.get_g_buffer(cut.G)
        VHDL_codes = tmpl.get_instantiation(idx, 'i_Clk_Launch', 'i_Clk_Sample', 'i_CE', 'i_CLR', w_Error_Mux_In, g_buffer)
        configuration.VHDL_file.add_components(''.join(VHDL_codes))

        pbar.update(1)

    # Print constraints
    Path(args.store_dir).mkdir(parents=True, exist_ok=True)
    configuration.print_src_files(args.store_dir)
