import os, sys
from joblib import Parallel, delayed
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.edge import Edge
from xil_res.minimal_config import MinConfig
from relocation.configuration import Config
from constraint.FASM import *
import utility.config as cfg
import utility.utility_functions as util

def gen_bitstreams(TC_path, file, store_path, bitstream_path, pyteman_path, blank_bitstream, removed_pips_file):
    fasm_list = set()

    # load TC
    TC = util.load_data(TC_path, file)

    pips = set()
    if type(TC) == MinConfig:
        CUTs = TC.CUTs
    elif type(TC) == Config:
        CUTs = TC.D_CUTs
    else:
        raise ValueError('Invalid TC!')

    for cut in CUTs:
        pips.update(edge for edge in cut.G.edges if Edge(edge).get_type() == 'pip')
        '''OUTMUX_node = set(filter(lambda x: nd.get_clb_node_type(x), cut.G))
        if OUTMUX_node:
            OUTMUX_node = list(OUTMUX_node)[0]
            tile = nd.get_tile(OUTMUX_node)
            label = nd.get_label(OUTMUX_node)
            subLUT_idx = 6
            value = 1
            fasm_list.add((get_OUTMUX_FASM(tile, label, subLUT_idx, value)))'''

    for LUT in TC.LUTs:
        LUT = TC.LUTs[LUT]
        # get init value
        tile = LUT.tile
        label = LUT.label
        init = LUT.get_init()
        if LUT.capacity == 1:
            init = 2 * init[8:]
            fasm_list.add(get_dual_LUT_FASM(tile, label, 1))
            OUTMUX_idx = 5
        else:
            OUTMUX_idx = 6

        fasm_list.add(get_LUT_INIT_FASM(tile, label, init))
        fasm_list.add(get_FFMUX_FASM(tile, label, 6, 1, 1))
        fasm_list.add(get_FFMUX_FASM(tile, label, 6, 2, 1))
        fasm_list.add((get_OUTMUX_FASM(tile, label, OUTMUX_idx, 1)))

        fasm_list.update(get_FF_CTRL_pips(tile, nd.get_top_bottom(LUT.name), nd.get_direction(LUT.name), 1, 1))
        fasm_list.update(get_FF_CTRL_pips(tile, nd.get_top_bottom(LUT.name), nd.get_direction(LUT.name), 2, 1))

    fasm_list.update(get_pips_FASM(*pips, mode='set'))

    # remove pips
    if Path(removed_pips_file).exists():
        fasm_list.update(remove_pips(removed_pips_file))

    store_file = store_path / f'{file.split(".")[0]}.fasm'

    with open(str(store_file), 'w+') as fasm_file:
        fasm_file.write('\n'.join(sorted(fasm_list)))
        fasm_file.write('\n')

    output_bitstream = bitstream_path / f'{file.split(".")[0]}.bit'

    os.system(f'{cfg.python} {pyteman_path} {store_file} {blank_bitstream} {str(bitstream_path / output_bitstream)}')

def remove_pips(removed_pips_file):
    removed_pips = set()
    with open(removed_pips_file) as file:
        for line in file:
            line = re.split('<*->+', line)
            tile = line[0].split('/')[0]
            pip_u = line[0].split('.')[-1]
            pip_v = line[1].rstrip("\n")
            pip = (f'{tile}/{pip_u}', f'{tile}/{pip_v}')
            removed_pips.add(pip)

    return get_pips_FASM(*removed_pips, mode='clear')

# user input
TC_path = sys.argv[1]
config_name = sys.argv[2]
blank_bitstream = sys.argv[3]
pyteman_path = sys.argv[4]
removed_pips_file = sys.argv[5]


iter = Path(TC_path).stem
store_path = Path(TC_path).parent.parent / 'FASM' / iter
if not os.path.exists(store_path):
    util.create_folder(store_path)

bitstream_path = Path(TC_path).parent.parent / 'Bitstreams' / iter
if not os.path.exists(bitstream_path):
    util.create_folder(bitstream_path)

gen_bitstreams(TC_path, config_name, store_path, bitstream_path, pyteman_path, blank_bitstream, removed_pips_file)