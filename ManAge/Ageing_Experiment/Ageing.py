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
initial_heatup_time = 5 * min
initial_recovery_time = 5 * min
recovery_time = 20 * min
burning_time = 15 * hour

# initial heat up
program_script = str(Path('tcl') / 'program.tcl')
os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{RO_bitstream}"')
time.sleep(initial_heatup_time)

# initial recovery
os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{blank_bitstream}"')
time.sleep(initial_recovery_time)

# minimal characterization paths
char_experiment_script = str(Path(__file__).parent.parent / 'run_experiment.py')
minimal_TCs = list(Path(minimal_char_bitstream_path).glob('*.bit'))
minimal_vivado_srcs_path = str(Path(minimal_char_bitstream_path).parent.parent / 'Vivado_Sources')

# full characterization paths
full_TCs = list(Path(full_char_bitstream_path).glob('*.bit'))
full_vivado_srcs_path = str(Path(full_char_bitstream_path).parent / 'Vivado_Sources')

for iteration in range(cycles):
    minimal_char_result = Path(store_path) / 'Results' / 'minimal' / f'iter{iteration}'
    full_char_result = Path(store_path) / 'Results' / 'full' / f'iter{iteration}'

    # create folder
    minimal_char_result.mkdir(parents=True, exist_ok=True)
    full_char_result.mkdir(parents=True, exist_ok=True)

    # initial minimal characterization
    for TC in minimal_TCs:

        os.system(
            f'{cfg.python} {char_experiment_script} {N_Parallel} {COM_port} {baud_rate} {minimal_char_bitstream_path} {TC.stem} {str(minimal_char_result)} {minimal_vivado_srcs_path}')

    # initial full characterization
    for TC in full_TCs:

        os.system(
            f'{cfg.python} {char_experiment_script} {N_Parallel} {COM_port} {baud_rate} {full_char_bitstream_path} {TC.stem} {str(full_char_result)} {full_vivado_srcs_path}')


    # burning
    os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{RO_bitstream}"')
    print(f'{iteration}- Burning')
    time.sleep(burning_time)

    # recovery
    os.system(f'vivado -mode batch -nolog -nojournal -source {program_script} -tclargs "{blank_bitstream}"')
    print(f'{iteration}- Recovery')
    time.sleep(recovery_time)


minimal_char_result = Path(store_path) / 'Results' / 'minimal' / f'iter{cycles}'
full_char_result = Path(store_path) / 'Results' / 'full' / f'iter{cycles}'

# create folder
minimal_char_result.mkdir(parents=True, exist_ok=True)
full_char_result.mkdir(parents=True, exist_ok=True)

# initial minimal characterization
for TC in minimal_TCs:

    os.system(
        f'{cfg.python} {char_experiment_script} {N_Parallel} {COM_port} {baud_rate} {minimal_char_bitstream_path} {TC.stem} {str(minimal_char_result)} {minimal_vivado_srcs_path}')

# initial full characterization
for TC in full_TCs:

    os.system(
        f'{cfg.python} {char_experiment_script} {N_Parallel} {COM_port} {baud_rate} {full_char_bitstream_path} {TC.stem} {str(full_char_result)} {full_vivado_srcs_path}')