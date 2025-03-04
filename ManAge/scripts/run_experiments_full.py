import os, re, sys, subprocess
from tqdm import tqdm
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import utility.config as cfg

# Experiment Parameters
baud_rate = 230400
COM_port = '/dev/ttyUSB2'
N_Parallel = 50

# Required Directories
Data_path           = '/home/bardia/Desktop/bardia/ManAge_Data/Data_xcvu9p_full'
bitstream_path      = Path(Data_path) / 'Bitstreams'        # program
results_path        = Path(Data_path) / 'Results'           # store
vivado_srcs_path    = Path(Data_path) / 'Vivado_Resources'    # validation

# Retrieve Bitstreams
TCs = list(bitstream_path.glob('TC*'))
pbar = tqdm(total=len(TCs))

# Run Experiment
experiment_script = Path(__file__).parent.parent / 'run_experiment.py'
for TC in TCs:
    pbar.set_description(f'{TC.stem}')
    TC_vivado_srcs_path = Path(vivado_srcs_path) / TC.stem

    command = f'{cfg.python} "{experiment_script}" run {TC_vivado_srcs_path} {results_path} {N_Parallel} {TC} {COM_port} {baud_rate} -RFB -t 60'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)