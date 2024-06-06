import sys, os, threading
import time, serial, math
from pathlib import Path
from experiment.clock_manager import CM
from experiment.read_packet import Read
from processing.data_process import get_segments_delays, validate_result, log_results, log_error
import utility.utility_functions as util

#usage: python3 run_experiment.py N_Parallel COM_port baud_rate bitstream_path bit_file_name result_path vivado_srcs_path

# User Inputs
N_Parallel          = int(sys.argv[1])
COM_port            = sys.argv[2]
baud_rate           = int(sys.argv[3])
bitstream_path      = sys.argv[4]
bit_file_name       = sys.argv[5]
result_path         = sys.argv[6]
vivado_srcs_path    = sys.argv[7]

# program device
tcl_script = Path('tcl') / 'program.tcl'
bitstream_file = Path(bitstream_path) / bit_file_name
os.system(f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{bitstream_file}"')
time.sleep(10)

# MMCM Initialization
MMCM1 = CM(fin=100e6, D=1, M=15, O=15, mode='incremental', fpsclk=100e6)
MMCM2 = CM(fin=MMCM1.fout, D=1, M=16, O=16, mode='decremental', fpsclk=100e6)
MMCM3 = CM(fin=MMCM1.fout, D=1, M=16, O=16)

# Run Experiments
port = serial.Serial(COM_port, baud_rate, timeout=220)
R = Read()
T1 = threading.Thread(target=Read.read_data, args=(R, port))
T2 = threading.Thread(target=Read.read_data, args=(R, port))
port.reset_input_buffer()
print(port.name)

data_rising, data_falling = [], []

# Rising Transitions
port.write('RUS'.encode('Ascii'))
T1.start()
T1.join()
packet = R.packet
data_rising += list(packet[:-3])

# Falling Transitions
port.write('RDS'.encode('Ascii'))
T2.start()
T2.join()
packet = R.packet
data_falling += list(packet[:-3])

# Reset
port.write('R'.encode('Ascii'))

# create folder
bitstream_result_path = Path(result_path) / bit_file_name
util.create_folder(bitstream_result_path)

# processing parameters
T = 1 / MMCM2.fout
N_Sets = MMCM1.fvco // (MMCM2.fvco - MMCM1.fvco)
N_Samples = 56 * MMCM2.O * N_Sets / 2
w_shift = math.ceil(math.log2(N_Samples))
N_Bytes = math.ceil((w_shift + N_Parallel) / 8)
sps = MMCM2.sps / N_Sets

# Process Received Data
error = False
try:
    segments_rising = get_segments_delays(data_rising, N_Bytes, w_shift, N_Parallel, sps)
except:
    log_error(bit_file_name, result_path, 'Rising')
    error = True

try:
    segments_falling = get_segments_delays(data_falling, N_Bytes, w_shift, N_Parallel, sps)
except:
    log_error(bit_file_name, result_path, 'Falling')
    error = True

if error:
    exit()

# store segments
util.store_data(bitstream_result_path, 'segments_rising.data', segments_rising)
util.store_data(bitstream_result_path, 'segments_falling.data', segments_falling)

# Validate Results
validation_result_rising =  validate_result(segments_rising, vivado_srcs_path, bit_file_name, N_Parallel)
validation_result_falling =  validate_result(segments_falling, vivado_srcs_path, bit_file_name, N_Parallel)

# Log Results
log_results(validation_result_rising, bit_file_name, result_path, 'Rising')
log_results(validation_result_falling, bit_file_name, result_path, 'Falling')