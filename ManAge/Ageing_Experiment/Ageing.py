import os, psutil, csv
import re
import time, subprocess
from pathlib import Path
from datetime import datetime, timedelta
import utility.config as cfg

class Ageing:

    def __init__(self, RO_bitstream, blank_bitstream, N_Parallel):
        self.RO_bitstream = Path(RO_bitstream)
        self.blank_bitstream = Path(blank_bitstream)
        self.N_Parallel = N_Parallel
        self.iteration = 0

        # Timing
        self.initial_heatup_time = 0
        self.initial_recovery_time = 0
        self.burning_time = 0
        self.recovery_time = 0

        # Experiment Parameters
        self.baud_rate = 230400
        self.serial_port = '/dev/ttyUSB0'

        # Logging
        self.general_logger = None
        self.current_script = None
        self.temp_script = None
        self.multimeter_port = '/dev/ttyUSB1'
        self.current_csv_file = None
        self.temp_csv_file = None
        self.process_current = None
        self.process_temp = None
        self.RO_bitstreams_list = []
        self.bitstream_ptr = 0

    def set_logger(self, general_loger_path, current_script, temp_script, multimeter_port, current_csv_file, temp_csv_file):
        Path(general_loger_path).parent.mkdir(parents=True, exist_ok=True)
        self.general_logger = open(general_loger_path, 'a+')
        self.current_script = current_script
        self.temp_script = temp_script
        self.multimeter_port = multimeter_port
        self.current_csv_file = current_csv_file
        self.temp_csv_file = temp_csv_file

    def set_RO_bitstreams_list(self, bitstream_dir):
        self.RO_bitstreams_list = sorted(Path(bitstream_dir).glob('*.bit'), key=lambda x: int(list(re.findall('\d+', x.stem))[0]))

    def set_timing(self, initial_heatup_time, initial_recovery_time, burning_time, recovery_time):
        min = 60
        hour = 60 * min

        self.initial_heatup_time = initial_heatup_time * min
        self.initial_recovery_time = initial_recovery_time * min
        self.burning_time = burning_time * hour
        self.recovery_time = recovery_time * min

    def set_UART(self, baud_rate, serial_port):
        self.baud_rate = baud_rate
        self.serial_port = serial_port

    def set_min_char(self, vivado_srcs_dir, bitstreams_dir, results_dir):
        self.min_vivado_srcs_dir = Path(vivado_srcs_dir)
        self.min_bitstreams_dir = Path(bitstreams_dir)
        self.min_results_dir = Path(results_dir)

    def set_full_char(self, vivado_srcs_dir, bitstreams_dir, results_dir):
        self.full_vivado_srcs_dir = Path(vivado_srcs_dir)
        self.full_bitstreams_dir = Path(bitstreams_dir)
        self.full_results_dir = Path(results_dir)

    def program(self, bitstream_file):
        # log
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        current_date = datetime.now().date()
        self.general_logger.write(f'program {bitstream_file.name} at {current_date} {current_time}.\n')
        self.general_logger.flush()

        program_script =  Path(__file__).absolute().parents[1] / 'run_experiment.py'
        subcommand = 'program'
        command = f'{cfg.python} "{program_script}" {subcommand} {bitstream_file}'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            print("Error:", result.stderr)
            exit()

    def wait(self, delay):
        time.sleep(delay)

    def heatup(self, init=False):
        self.program(self.RO_bitstream)
        delay = self.initial_heatup_time if init else self.burning_time
        self.wait(delay)

    def recovery(self, init=False):
        self.program(self.blank_bitstream)
        delay = self.initial_recovery_time if init else self.recovery_time
        self.wait(delay)

    def characterize(self, type):
        if type == 'min':
            vivado_srcs_dir = self.min_vivado_srcs_dir
            bitstreams_dir = self.min_bitstreams_dir
            results_dir = self.min_results_dir  / f'iter{self.iteration}'
        elif type == 'full':
            vivado_srcs_dir = self.full_vivado_srcs_dir
            bitstreams_dir = self.full_bitstreams_dir
            results_dir = self.full_results_dir  / f'iter{self.iteration}'
        else:
            raise ValueError(f'Type: {type} is invalid')

        # create folder
        results_dir.mkdir(parents=True, exist_ok=True)

        script = Path(__file__).absolute().parents[1] / 'run_experiment.py'
        subcommand = 'run'

        TCs = list(bitstreams_dir.glob('*.bit'))

        for TC in TCs:
            if TC.stem in os.listdir(results_dir):
                continue

            TC_srcs_dir = vivado_srcs_dir / TC.stem
            command = f'{cfg.python} "{script}" {subcommand} {TC_srcs_dir} {results_dir} {self.N_Parallel} {TC} {self.serial_port} {self.baud_rate} -RFB -t 60'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # Check for errors
            if result.returncode != 0:
                print("Error:", result.stderr)
                exit()

    def increment(self):
        self.iteration += 1

    def log_current(self):
        read_current_script = Path(__file__).parent / 'read_current.py'
        current_command = ['python3', read_current_script, self.multimeter_port, self.current_csv_file]
        self.process_current = subprocess.Popen(current_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def log_temp(self):
        log_temp_script = Path(__file__).parent / 'log_temp.tcl'
        temp_command = ['vivado', '-mode', 'batch', '-nolog', '-nojournal', '-source', log_temp_script, '-tclargs',
                        self.temp_csv_file]
        self.process_temp = subprocess.Popen(temp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def terminate_current_logger(self):
        self.terminate_process_and_children(self.process_current)
        self.process_current.wait()

    def terminate_temp_logger(self):
        self.terminate_process_and_children(self.process_temp)
        self.process_temp.wait()

    def heatup_monitored(self, lower_threshold, runaway_threshold, stab_tolerance, tolerance_dur):
        start_time = time.time()
        while (time.time() - start_time < self.burning_time):
            remaining_burning_dur = self.burning_time - (time.time() - start_time)
            status = self.monitor_csv(self.current_csv_file, lower_threshold, runaway_threshold, stab_tolerance, remaining_burning_dur, duration=tolerance_dur)
            if (status == -2):  # increase power
                if self.bitstream_ptr < len(self.RO_bitstreams_list) - 1:
                    self.bitstream_ptr += 1
                    self.program(self.RO_bitstreams_list[self.bitstream_ptr])
            if (status == -1):  # decrease power
                if self.bitstream_ptr > 0:
                    self.bitstream_ptr -= 1
                    self.program(self.RO_bitstreams_list[self.bitstream_ptr])

    @staticmethod
    def terminate_process_and_children(process):
        try:
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):  # Terminate child processes
                child.terminate()
            parent.terminate()
        except psutil.NoSuchProcess:
            pass

    def monitor_csv(self, file_path, lower_threshold, threshold, tolerance, runtime, duration=5, interval=1):
        """
        Monitor a CSV file and perform actions based on its content.

        Args:
            file_path (str): Path to the CSV file.
            threshold (float): Threshold for triggering the first action.
            tolerance (float): Allowed difference for the second action.
            duration (int): Time duration in minutes for the tolerance check.
            interval (int): How often to check the file (in seconds).
        """
        t1 = time.time()
        recent_values = []  # Store recent rows for comparison

        while (time.time() - t1 < runtime):
            try:
                with open(file_path, 'r') as file:
                    # Read all rows of the CSV
                    rows = list(csv.reader(file))
                    if len(rows) < 2:
                        # Skip header or empty file
                        time.sleep(interval)
                        continue

                    # Get the last row
                    last_row = rows[-1]
                    current_value = float(last_row[0])
                    current_time = datetime.strptime(last_row[1], "%H:%M:%S")
                    current_date = datetime.now().date()
                    current_time = current_time.replace(year=current_date.year, month=current_date.month,
                                                        day=current_date.day)

                    # Check if the value exceeds the threshold
                    if current_value > threshold:
                        self.general_logger.write(f"Value {current_value} exceeded threshold {threshold} at {current_time}.\n")
                        self.general_logger.flush()
                        return -1

                    # Add the current value and time to the list
                    recent_values.append((current_time, current_value))

                    # Remove values outside the specified duration
                    cutoff_time = current_time - timedelta(minutes=duration)
                    recent_values = [(t, v) for t, v in recent_values if t >= cutoff_time]

                    # Check tolerance condition
                    if len(recent_values) > 1 and (time.time() - t1) >= (60 * duration):
                        earliest_time, earliest_value = recent_values[0]
                        #if abs(current_value - earliest_value) < tolerance:
                        if (current_value < lower_threshold):
                            #self.general_logger.write(f"Value difference {abs(current_value - earliest_value)} "
                                  #f"within tolerance {tolerance} between {earliest_time} and {current_time}. Triggering action.\n")
                            self.general_logger.write(f"Value: {current_value}, at {current_time}.\n")
                            self.general_logger.flush()
                            return -2

            except Exception as e:
                print(f"Error: {e}")

            time.sleep(interval)

        return 0
