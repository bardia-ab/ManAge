import sys, os, time
from pathlib import Path
from tqdm import tqdm
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

from Ageing_Experiment.Ageing import Ageing

full_blank_bitstream = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/Design/blank_zu9eg_jtag.bit'
os.system(f'python3 run_experiment.py program {full_blank_bitstream}')

RO_bitstream = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/Design/Bitstream/full/1_X42_47_Y20_24.bit'
#blank_bitstream = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/Design/blank_zu9eg_jtag_shutdown.bit'
blank_bitstream = full_blank_bitstream
N_Parallel = 50
cycles = 21

ageing_exp = Ageing(RO_bitstream, blank_bitstream, N_Parallel)

# set UART
baud_rate = 230400
serial_port = '/dev/ttyUSB0'
ageing_exp.set_UART(baud_rate, serial_port)

# set timing
one_day = 24 * 60 * 60
initial_heatup_time = 15    # mins
initial_recovery_time = 15  # mins
burning_time = 20           # hours
recovery_time = 30          # mins

ageing_exp.set_timing(initial_heatup_time, initial_recovery_time, burning_time, recovery_time)

# logger
general_logger = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/logs/logs.txt'
current_script = '/home/bardia/Desktop/ManAge/ManAge/Ageing_Experiment/read_current.py'
temp_script = '/home/bardia/Desktop/ManAge/ManAge/Ageing_Experiment/log_temp.tcl'
multimeter_port = '/dev/ttyUSB1'
current_csv_file = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/logs/current.csv'
temp_csv_file = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/logs/temp.csv'

ageing_exp.set_logger(general_logger, current_script, temp_script, multimeter_port, current_csv_file, temp_csv_file)

# RO bitstreams list
bitstream_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/Design/Bitstream/partial_shutdown'
ageing_exp.set_RO_bitstreams_list(bitstream_dir)

# monitoring parameters
runaway_threshold = 3.35
lower_threshold = 3.2
stab_tolerance = 0.03
tolerance_dur = 60 # mins

# set minimal characterization paths
min_vivado_srcs_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Data_xczu9eg/Vivado_Resources/X2Y0'
min_bitstreams_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Data_xczu9eg/Bitstreams/X2Y0'
min_results_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/Result/minimal_char'

ageing_exp.set_min_char(min_vivado_srcs_dir, min_bitstreams_dir, min_results_dir)

# set full characterization paths
full_vivado_srcs_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Data_xczu9eg_full/Vivado_Resources/X2Y0'
full_bitstreams_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Data_xczu9eg_full/Bitstreams/X2Y0'
full_results_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/XCZU9EG/11_X2Y0_08_05_2025/Result/full_char'

ageing_exp.set_full_char(full_vivado_srcs_dir, full_bitstreams_dir, full_results_dir)

pbar = tqdm(total=cycles)

# start logging
ageing_exp.log_temp()
ageing_exp.log_current()

# initial heat up
pbar.set_postfix_str('Burning')
ageing_exp.heatup(True)

# initial recovery
pbar.set_postfix_str('Recovery')
ageing_exp.recovery(True)

# initial minimal characterization
pbar.set_postfix_str('Minimal Characterization')
ageing_exp.characterize(type='min')

# initial full characterization
pbar.set_postfix_str('Full Characterization')
ageing_exp.characterize(type='full')

# increment iteration
ageing_exp.increment()
pbar.update(1)

# set first bitstream index
ageing_exp.bitstream_ptr = 64

for iteration in range(1, cycles):
    pbar.set_description(f'Iteration: {iteration}')

    #heat up
    pbar.set_postfix_str('Burning')
    ageing_exp.set_RO_bitstreams_list(bitstream_dir)
    ageing_exp.program(ageing_exp.RO_bitstreams_list[ageing_exp.bitstream_ptr])
    ageing_exp.heatup_monitored(lower_threshold, runaway_threshold, stab_tolerance, tolerance_dur)

    #recovery
    pbar.set_postfix_str('Recovery')
    ageing_exp.recovery(False)

    #minimal characterization
    pbar.set_postfix_str('Minimal Characterization')
    ageing_exp.characterize(type='min')

    #full characterization
    pbar.set_postfix_str('Full Characterization')
    ageing_exp.characterize(type='full')

    # increment iteration
    ageing_exp.increment()

    pbar.update(1)

# one day recovery
pbar.set_postfix_str('One Day Recovery')
time.sleep(one_day)

# minimal characterization
pbar.set_postfix_str('Final Minimal Characterization')
ageing_exp.characterize(type='min')

# full characterization
pbar.set_postfix_str('Final Full Characterization')
ageing_exp.characterize(type='full')

# terminate logging
ageing_exp.terminate_current_logger()
ageing_exp.terminate_temp_logger()

# close logger
ageing_exp.general_logger.close()