import os, sys, subprocess
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

from xil_res.architecture import Arch
import utility.config as cfg

# device
device_name = 'xczu9eg'
script = Path(__file__).absolute().parent / 'RO_cluster.py'
filter_tile = 'CLEL_R_X44Y90'
width = 5
height = 35
project_name = f'{width}x{height}_BRAM'

# design
subcommand = 'design'
output_fasm_dir = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\RO_design\FASM'
command = f'{cfg.python} "{script}" {subcommand} {device_name} {output_fasm_dir}'
result = subprocess.run(command, shell=True, capture_output=True, text=True)
if result.returncode != 0:
    print('Error: ', result.stderr)

# cluster
subcommand = 'cluster'
input_fasm_dir = output_fasm_dir
output_clustered_fasm_dir = rf'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\RO_design\Cluster\{project_name}'
command = f'{cfg.python} "{script}" {subcommand} {device_name} {input_fasm_dir} {width} {height} {output_clustered_fasm_dir} -f {filter_tile}'
result = subprocess.run(command, shell=True, capture_output=False, text=True)
if result.returncode != 0:
    print('Error: ', result.stderr)

# bitstream
subcommand = 'bitstream'
input_clustered_fasm_dir = output_clustered_fasm_dir
blank_bitstream_file = r"C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\RO_design\blank_zu9eg_jtag.bit"
output_bitstream_dir = rf'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\RO_design\Bitstream\{project_name}'
command = f'{cfg.python} "{script}" {subcommand} {device_name} {input_clustered_fasm_dir} {blank_bitstream_file} {output_bitstream_dir}'
result = subprocess.run(command, shell=True, capture_output=False, text=True)
if result.returncode != 0:
    print('Error: ', result.stderr)