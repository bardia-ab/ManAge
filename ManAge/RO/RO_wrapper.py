import os, sys, shutil

from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from xil_res.architecture import Arch
import utility.config as cfg

# user inputs
device_name = 'xczu9eg'
clk_pips = str(Path(__file__).parent / 'clk_pips.txt')
config_name = 'TC_full'

# Scripts
CWD = Path(__file__).parent
RO_minima_script = str(CWD / 'RO_minimalTC.py')
reloc_script = str(CWD / 'RO_reloc.py')
gen_fsm_script = str(CWD / 'RO_gen_bitstream.py')

# Create RO minimal TC
for iteration, desired_tile in zip(range(1, 4), ['INT_X46Y90', 'INT_X45Y90', 'INT_X44Y90']):
    os.system(f'{cfg.python} "{RO_minima_script}" {device_name} {desired_tile} {iteration} "{clk_pips}"')

# Relocation
iteration = 1
device = Arch(device_name)
desired_tiles = device.get_INTs()
os.system(f'{cfg.python} "{reloc_script}" {device_name} {iteration} {config_name} {" ".join(desired_tiles)}')


CWD = Path(__file__).parent
reloc_script = str(CWD / 'RO_reloc.py')
gen_fsm_script = str(CWD / 'RO_gen_bitstream.py')


# generate FASM & bitstreamc
TC_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu9eg_RO\Configurations\iter1'
blank_bitstream = r"C:\Users\t26607bb\Desktop\CPS_Project\RO_Python\bitstream\zero_blank_zu9eg_jtag.bit"
pyteman_path = r'C:\Users\t26607bb\Desktop\Pyteman\pyteman_dist\fasm2bit.py'
removed_pips_file = str(CWD / 'removed_pips.txt')
os.system(f'{cfg.python} "{gen_fsm_script}" {TC_path} {config_name} {blank_bitstream} {pyteman_path} {removed_pips_file}')
