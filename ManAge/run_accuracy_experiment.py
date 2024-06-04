import sys, os, threading
import time, serial, math
from pathlib import Path
from experiment.clock_manager import CM
from experiment.read_packet import Read
import matplotlib.pyplot as plt
from processing.data_process import *
import utility.utility_functions as util

#usage: python3 run_experiment.py N_Parallel COM_port baud_rate bitstream_path bit_file_name result_path vivado_srcs_path

# User Inputs
N_Parallel          = int(sys.argv[1])
COM_port            = sys.argv[2]
baud_rate           = int(sys.argv[3])
bitstream_path      = sys.argv[4]
bit_file_name       = sys.argv[5]
store_path          = sys.argv[6]

# create folder
Path(store_path).mkdir(parents=True, exist_ok=True)

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
port = serial.Serial(COM_port, baud_rate)
R = Read()
T1 = threading.Thread(target=Read.read_data, args=(R, port))
T2 = threading.Thread(target=Read.read_data, args=(R, port))
port.reset_input_buffer()
print(port.name)

rcvd_data = []

# Rising Transitions
port.write('RBS'.encode('Ascii'))
T1.start()
T1.join()
packet = R.packet
rcvd_data += list(packet[:-3])

# Reset
port.write('R'.encode('Ascii'))


# processing parameters
T = 1 / MMCM2.fout
N_Sets = MMCM1.fvco // (MMCM2.fvco - MMCM1.fvco)
N_Samples = 56 * MMCM2.O * N_Sets / 2
w_shift = math.ceil(math.log2(N_Samples))
N_Bytes = math.ceil((w_shift + N_Parallel) / 8)
sps = MMCM2.sps / N_Sets

# Process Received Data
segments = get_segments_delays(rcvd_data, N_Bytes, w_shift, N_Parallel, sps)
delays = [delay[1] for seg in segments for delay in seg]
plt.hist(delays)

plt.hist(delays, bins=10, color='#e38e34', alpha=1)
plt.grid(True, which='major')
plt.grid(True, which='minor')
plt.xlabel('Delay (ps)', labelpad=10, fontsize=20, fontname='Arial')
plt.ylabel('Frequency', labelpad=10, fontsize=20, fontname='Arial')
plt.xticks(fontsize=20, fontname='Arial')
plt.yticks(fontsize=20, fontname='Arial')
#plt.xticks(shift_values, delays)
plt.rcParams['axes.labelsize'] = 14  # Font size for axis labels
plt.rcParams['xtick.labelsize'] = 12  # Font size for x-axis tick labels
plt.rcParams['ytick.labelsize'] = 12
plt.tight_layout()
plt.grid(visible=True, which='major', axis='y', color='grey', linestyle='--', linewidth=1)
plt.grid(visible=False, which='major', axis='x')
for pos in ['right', 'top', 'bottom', 'left']:
    plt.gca().spines[pos].set_visible(False)

store_file = Path(store_path) / f'{bit_file_name}.pdf'
plt.savefig(store_file, bbox_inches='tight')

# store segments
util.store_data(store_path, f'{bit_file_name}.data', delays)
