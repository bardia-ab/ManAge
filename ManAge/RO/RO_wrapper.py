import os, sys
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

import utility.config as cfg

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