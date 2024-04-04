import os, re, sys
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
Data_path           = '/home/bardia/Desktop/bardia/Timing_Characterization/X1Y5'
bitstream_path      = Path(Data_path) / 'Bitstreams'            # program
results_path        = Path(Data_path) / 'Results'               # store
vivado_srcs_path    = Path(Data_path) / 'Vivado_Sources'        # validation

# Create Result path
util.create_folder(results_path)

# Setup pbar
CRs = sorted(os.listdir(bitstream_path), key=lambda x: int(re.findall('\d+', x)[0]))
pbar = tqdm(total=len(CRs))

for CR in CRs:

    # CR Directories
    CR_bitstream_path   = Path(bitstream_path) / CR
    CR_results_path     = Path(results_path) / CR
    CR_vivado_srcs_path = Path(vivado_srcs_path) / CR

    # Create a Folder for CR in vivado_srcs_path
    util.create_folder(CR_results_path)

    # Retrieve Bitstreams
    TCs = CR_bitstream_path.glob('TC*')

    # Run Experiment
    experiment_script = Path(__file__).parent.parent / 'run_experiment.py'
    for TC in TCs:
        os.system(
            f'{cfg.python} {experiment_script} {N_Parallel} {COM_port} {baud_rate} {TC.stem} {CR_bitstream_path} {CR_results_path} {CR_vivado_srcs_path}')

    pbar.update(1)