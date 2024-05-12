import os, sys
from joblib import Parallel, delayed
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.edge import Edge
from constraint.FASM import *
import utility.config as cfg
import utility.utility_functions as util

def gen_bitstreams(TC_path, file, store_path, bitstream_path, pyteman_path, blank_bitstream):
    fasm_list = set()

    # load TC
    TC = util.load_data(TC_path, file)

    pips = set()
    for cut in TC.D_CUTs:
        pips.update(edge for edge in cut.G.edges if Edge(edge).get_type() == 'pip')
        OUTMUX_node = set(filter(lambda x: nd.get_clb_node_type(x), cut.G))
        if OUTMUX_node:
            OUTMUX_node = list(OUTMUX_node)[0]
            tile = nd.get_tile(OUTMUX_node)
            label = nd.get_label(OUTMUX_node)
            subLUT_idx = 6
            value = 1
            fasm_list.add((get_OUTMUX_FASM(tile, label, subLUT_idx, value)))

    for LUT in TC.LUTs:
        LUT = TC.LUTs[LUT]
        # get init value
        tile = LUT.tile
        label = LUT.label
        init = LUT.get_init()
        fasm_list.add(get_LUT_INIT_FASM(tile, label, init))

    fasm_list.update(get_pips_FASM(*pips, mode='set'))

    store_file = store_path / f'{file.split(".")[0]}.fasm'

    with open(str(store_file), 'w+') as fasm_file:
        # fasm = '\n'.join(fasm_list)
        fasm_file.write('\n'.join(fasm_list))
        fasm_file.write('\n')

    output_bitstream = bitstream_path / f'{file.split(".")[0]}.bit'

    os.system(f'{cfg.python} {pyteman_path} {store_file} {blank_bitstream} {str(bitstream_path / output_bitstream)}')

# user input
TC_path = sys.argv[1]
TC_name = sys.argv[2]
blank_bitstream = sys.argv[3]
pyteman_path = sys.argv[4]

#TC_path = r'/home/bardia/Desktop/bardia/ManAge_Data/Data_xczu9eg_RO/Configurations/iter1'
#blank_bitstream = r"/home/bardia/Downloads/blank_zu9eg_jtag.bit"
#pyteman_path = r'/home/bardia/Downloads/pyteman/pyteman_dist/fasm2bit.py'


iter = Path(TC_path).stem
store_path = Path(TC_path).parent.parent / 'FASM' / iter
if not os.path.exists(store_path):
    util.create_folder(store_path)

bitstream_path = Path(TC_path).parent.parent / 'Bitstreams' / iter
if not os.path.exists(bitstream_path):
    util.create_folder(bitstream_path)


'''
for file in Path(TC_path).glob(f'TC_{TC_name}.data'):
    fasm_list = set()

    # load TC
    TC = util.load_data(TC_path, file.name)

    pips = set()
    for cut in TC.D_CUTs:
        pips.update(edge for edge in cut.G.edges if Edge(edge).get_type() == 'pip')
        OUTMUX_node = set(filter(lambda x: nd.get_clb_node_type(x), cut.G))
        if OUTMUX_node:
            OUTMUX_node = list(OUTMUX_node)[0]
            tile = nd.get_tile(OUTMUX_node)
            label = nd.get_label(OUTMUX_node)
            subLUT_idx = 6
            value = 1
            fasm_list.add((get_OUTMUX_FASM(tile, label, subLUT_idx, value)))

    for LUT in TC.LUTs:
        LUT = TC.LUTs[LUT]
        # get init value
        tile = LUT.tile
        label = LUT.label
        init = LUT.get_init()
        fasm_list.add(get_LUT_INIT_FASM(tile, label, init))

    fasm_list.update(get_pips_FASM(*pips, mode='set'))


    store_file = store_path / f'{file.stem}.fasm'

    with open(str(store_file), 'w+') as fasm_file:
        #fasm = '\n'.join(fasm_list)
        fasm_file.write('\n'.join(fasm_list))
        fasm_file.write('\n')

    output_bitstream = bitstream_path / f'{file.stem}.bit'

    os.system(f'{cfg.python} {pyteman_path} {store_file} {blank_bitstream} {str(bitstream_path / output_bitstream)}')'''

Parallel(n_jobs=-1)(delayed(gen_bitstreams)(TC_path, file, store_path, bitstream_path, pyteman_path, blank_bitstream) for file in os.listdir(TC_path))