import sys, os, time
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

import utility.config as cfg

# User Inputs
RO_bitstream = sys.argv[1]
blank_bitstream = sys.argv[2]
minimal_char_bitstream_path = sys.argv[3]
full_char_bitstream_path = sys.argv[4]
store_path = sys.argv[5]
cycles = int(sys.argv[6])

# Experiment Parameters
baud_rate = 230400
COM_port = '/dev/ttyUSB0'
N_Parallel = 50

# Timing
min = 60
hour = 60 * min
initial_heatup_time = 20 * min
recovery_time = 15 * min
burning_time = 24 * hour

# initial heat up
program_script = Path('tcl') / 'program.tcl'
os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{RO_bitstream}"')
time.sleep(initial_heatup_time)

# initial recovery
os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{blank_bitstream}"')
time.sleep(recovery_time)

# initial minimal characterization
char_experiment_script = Path(__file__).parent.parent / 'run_experiment.py'
minimal_TCs = Path(minimal_char_bitstream_path).glob('*.bit')
minimal_char_result=''

for TC in minimal_TCs:
    os.system(f'{cfg.python} {char_experiment_script} {N_Parallel} {COM_port} {baud_rate} {minimal_char_bitstream_path} {TC.stem} result_path vivado_srcs_path')

# initial full characterization

for _ in range(cycles):
    # burning
    os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{RO_bitstream}"')
    time.sleep(burning_time)

    # recovery
    os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{blank_bitstream}"')
    time.sleep(recovery_time)

    # initial minimal characterization

    # initial full characterization