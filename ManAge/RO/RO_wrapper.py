import os, sys, shutil

from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.architecture import Arch
from xil_res.node import Node as nd
from joblib import Parallel, delayed
from tqdm import tqdm
import utility.config as cfg


##########
def func_1(tile, store_name, desired_tiles, device_name):
    desired_tiles[1] = tile
    RO_reloc = Path(__file__).parent / 'RO_reloc.py'
    store_name = f'{store_name}_{desired_tiles[0]}_{desired_tiles[1]}'
    command = f'python3 {str(RO_reloc)} {device_name} {desired_tile} {store_name} {" ".join(desired_tiles)}'
    os.system(command)

##########

'''device_name = 'xczu9eg'
desired_tile = 'INT_X46Y90'
store_name = '2clb'

# init device
device = Arch(device_name)

desired_tiles= 2 * [0]
tiles = {tile for cr in device.CRs if cr.name == 'X2Y1' for tile in cr.tiles}
INT_double_CLBs = [tile for tile in tiles if None not in device.tiles_map[nd.get_coordinate(tile)].values()]
INT_double_CLBs.sort(key=lambda tile: (nd.get_x_coord(tile), nd.get_y_coord(tile)))
desired_tiles[0] = INT_double_CLBs.pop(0)'''

'''for tile in INT_double_CLBs:
    desired_tiles[1] = tile
    RO_reloc = Path(__file__).parent / 'RO_reloc.py'
    store_name = f'{store_name}_{desired_tiles[0]}_{desired_tiles[1]}'
    command = f'python3 {str(RO_reloc)} {device_name} {desired_tile} {store_name} {" ".join(desired_tiles)}'
    os.system(command)'''

'''Parallel(n_jobs=-1)(delayed(func_1)(tile, store_name, desired_tiles, device_name) for _, tile in zip(tqdm(range(len(INT_double_CLBs))), INT_double_CLBs))

RO_gen_fasm = Path(__file__).parent / 'RO_gen_fasm.py'
os.system(f'python3 {RO_gen_fasm}')

src_path = '/home/bardia/Desktop/bardia/ManAge_Data/Data_xczu9eg_RO/Bitstreams/iter1'
dest_path = '/home/bardia/Desktop/bardia/ManAge_Data/RO_sweep/bitstream/iter1'

shutil.copytree(src_path, dest_path, dirs_exist_ok=True)

current_folder = Path(dest_path)
new_folder = current_folder.parent / 'sweep_2_clb'
try:
    current_folder.rename(new_folder)
except:
    shutil.rmtree(str(new_folder))
    current_folder.rename(new_folder)

os.chdir('/home/bardia/Desktop/Virtual_Oscilloscope')
sys.path.append('/home/bardia/Desktop/Virtual_Oscilloscope')
virtual_scope = '/home/bardia/Desktop/Virtual_Oscilloscope/wrapper.py'
os.system(f'python3 {virtual_scope}')
'''
# user inputs
device_name = 'xczu9eg'
desired_tile = 'INT_X46Y90'
TC_name = '1clb_X46Y90'

TC_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu9eg_RO\Configurations\iter1'
blank_bitstream = r"C:\Users\t26607bb\Desktop\CPS_Project\RO_Python\bitstream\blank_zu9eg_jtag.bit"
pyteman_path = r'C:\Users\t26607bb\Desktop\Pyteman\pyteman_dist\fasm2bit.py'

CWD = Path(__file__).parent
reloc_script = str(CWD / 'RO_reloc.py')
gen_fsm_script = str(CWD / 'RO_gen_fasm.py')

# Relocation
desired_tiles = ['INT_X46Y90', ]
os.system(f'{cfg.python} "{reloc_script}" {device_name} {desired_tile} {TC_name} {" ".join(desired_tiles)}')

# generate FASM & bitstreamc
os.system(f'{cfg.python} "{gen_fsm_script}" {TC_path} {TC_name} {blank_bitstream} {pyteman_path}')
