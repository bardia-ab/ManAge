import os, re, sys, subprocess
from tqdm import tqdm
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import utility.utility_functions as util
import utility.config as cfg


# Experiment Parameters
baud_rate = 230400
COM_port = '/dev/ttyUSB0'
N_Parallel = 50

# Required Directories
Data_path           = '/home/bardia/Desktop/bardia/ManAge_Data/Data_xczu9eg'
bitstream_path      = Path(Data_path) / 'Bitstreams'        # program
results_path        = Path(Data_path) / 'Results'           # store
vivado_srcs_path    = Path(Data_path) / 'Vivado_Resources'    # validation

# Create Result path
#results_path.mkdir(parents=True)

# Setup pbar
#CRs = sorted(os.listdir(bitstream_path), key=lambda x: int(re.findall('\d+', x)[0]))
CRs = ['X2Y5']
pbar = tqdm(total=len([file for file in bitstream_path.rglob('*.bit')]))

for CR in CRs:

    # CR Directories
    CR_bitstream_path   = Path(bitstream_path) / CR
    CR_results_path     = Path(results_path) / CR
    CR_vivado_srcs_path = Path(vivado_srcs_path) / CR

    # Create a Folder for CR in vivado_srcs_path
    CR_results_path.mkdir(parents=True, exist_ok=True)

    # Retrieve Bitstreams
    TCs = CR_bitstream_path.glob('TC*')

    # Run Experiment
    experiment_script = Path(__file__).parent.parent / 'run_experiment.py'
    for TC in TCs:
        pbar.set_description(f'{CR} >> {TC.stem}')

        command = f'{cfg.python} "{experiment_script}" run {CR_vivado_srcs_path} {CR_results_path} {N_Parallel} {TC} {COM_port} {baud_rate} -RFB'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            print("Error:", result.stderr)
            exit()

        pbar.update(1)
