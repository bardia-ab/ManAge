import threading
import time, serial, math
import subprocess, os, sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from tqdm import tqdm
from experiment.read_packet import Read
from processing.data_process import *
import utility.utility_functions as util
import utility.config as cfg

# bitstreams
bitstream_path = r'/home/bardia/Desktop/bardia/ManAge_Data/RO_design/Bitstream/temp_delay'
bitstreams = list(Path(bitstream_path).glob('*.bit'))
bitstreams.sort()

# result
result_path = Path(bitstream_path).parents[1] / 'results' / 'heat_delay_exp' / 'delay'
result_path.mkdir(parents=True, exist_ok=True)

# temp
temp_path = Path(result_path).parent / 'temperature'
Path(temp_path).mkdir(parents=True, exist_ok=True)

# blank bitstream
blank_bitstream = '/home/bardia/Desktop/bardia/ManAge_Data/RO_design/blank_zu9eg_jtag.bit'

cycles = 1.5 * 60
recovery_time = 1 * 60

# remove tested bitstreams
bitstreams = set(filter(lambda b: b.stem not in os.listdir(result_path), bitstreams))

# pbar
pbar = tqdm(total=len(bitstreams))

# Experiment Parameters
baud_rate = 230400
COM_port = '/dev/ttyUSB0'
N_Parallel = 1

for bitstream in bitstreams:
    pbar.set_description(bitstream.stem)

    # program device with blank bitstream
    pbar.set_postfix_str('programming blank bitstream')
    exp_script = Path(__file__).parents[1].absolute() / 'run_experiment.py'
    command = f'{cfg.python} "{exp_script}" program {blank_bitstream}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    pbar.set_postfix_str('recovery')
    time.sleep(recovery_time)

    # program device
    pbar.set_postfix_str('programming target bitstream')
    command = f'{cfg.python} "{exp_script}" program {bitstream}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    # log temp
    pbar.set_postfix_str('logging temperature')
    temp_script = Path('tcl') / 'log_temp.tcl'
    temp_csv = str(Path(temp_path) / (bitstream.with_suffix('.csv')).name)
    command = f'vivado -mode batch -nolog -nojournal -source {temp_script} -tclargs "{temp_csv}" "{cycles}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    # Run Experiments
    pbar.set_postfix_str('run experiment')
    command = f'{cfg.python} "{exp_script}" run None {result_path} {N_Parallel} {bitstream} {COM_port} {baud_rate} -RFB --skip_program --skip_validate'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    pbar.update(1)

# program device with blank bitstream
pbar.set_postfix_str('programming blank bitstream')
exp_script = Path(__file__).parents[1].absolute() / 'run_experiment.py'
command = f'{cfg.python} "{exp_script}" program {blank_bitstream}'
result = subprocess.run(command, shell=True, capture_output=True, text=True)

# Check for errors
if result.returncode != 0:
    print("Error:", result.stderr)

