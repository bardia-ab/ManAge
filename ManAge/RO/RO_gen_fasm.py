import os, sys
import networkx as nx
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.edge import Edge
from constraint.FASM import *
import utility.config as cfg
import utility.utility_functions as util

# user input
#TC_path = sys.argv[1]
#TC_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu9eg_RO\Configurations\iter1'
#blank_bitstream = r"C:\Users\t26607bb\Desktop\CPS_Project\RO_Python\bitstream\blank_zu9eg_jtag.bit"
#pyteman_path = r'C:\Users\t26607bb\Desktop\Pyteman\pyteman_dist\fasm2bit.py'

TC_path = r'/mnt/c/Users/t26607bb/Desktop/CPS_Project/Path_Search/Data_xczu9eg_RO/Configurations/iter1'
blank_bitstream = r"/mnt/c/Users/t26607bb/Desktop/CPS_Project/RO_Python/bitstream/blank_zu9eg_jtag.bit"
pyteman_path = r'/mnt/c/Users/t26607bb/Desktop/Pyteman/pyteman_dist/fasm2bit.py'


iter = Path(TC_path).stem
store_path = Path(TC_path).parent.parent / 'FASM' / iter
util.create_folder(store_path)

bitstream_path = Path(TC_path).parent.parent / 'Bitstreams' / iter
util.create_folder(bitstream_path)

for file in os.listdir(TC_path):
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

    fasm_list.update(get_pips_FASM(*pips, mode='set'))


    store_file = store_path / f'{file.split(".")[0]}.fasm'

    with open(str(store_file), 'w+') as fasm_file:
        #fasm = '\n'.join(fasm_list)
        fasm_file.write('\n'.join(fasm_list))

    output_bitstream = bitstream_path / f'{file.split(".")[0]}.bit'

    os.system(f'{cfg.python} {pyteman_path} {store_file} {blank_bitstream} {str(bitstream_path / output_bitstream)}')