import sys, os, threading, time, serial, math, argparse
from tqdm import tqdm
from pathlib import Path
from experiment.clock_manager import CM
from experiment.read_packet import Read
from processing.data_process import get_segments_delays, validate_result, log_results, log_error
import utility.utility_functions as util
import utility.config as cfg

# Create main parser
parser = argparse.ArgumentParser(prog='run_experiment', description=' Load bitstreams onto the FPGA and receive the results')
subparser = parser.add_subparsers(title='subcommands', dest='subcommand')

# create a parent parser for shared arguments
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument('vivado_srcs_dir', help="Specify the directory in which TCs' source files are stored")
parent_parser.add_argument('results_dir', help="Specify the directory into which the results will be stored")
parent_parser.add_argument('N_Parallel', type=int, default=cfg.N_Parallel, help="Specify the number of parallell CUTs in a segment")

# Subcommand: run
parser_run = subparser.add_parser('run', parents=[parent_parser], help='Run the experiment by loading the bitstreams onto the FPGA')
parser_run.add_argument('bitstream_file', help="Specify the path to the bitstream file")
parser_run.add_argument('serial_port', help="Specify the serial port for UART transmission")
parser_run.add_argument('args.baud_rate', help="Specify the baud rate of the UART transmission")

parser_run.add_argument('-t', '--timeout', type=float, default=220, help="Set a read timeout value in seconds")

# Subcommand: validate
parser_validate = subparser.add_parser('validate', parents=[parent_parser], help="Validate the stored results")

if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    
    if args.subcommand == 'run':
        # program device
        tcl_script = Path('tcl') / 'program.tcl'
        bit_file_name = Path(args.bitstream_file).stem
        os.system(f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{args.bitstream_file}"')
        time.sleep(2)

        # MMCM Initialization
        MMCM1 = CM(fin=cfg.fin, D=cfg.D1, M=cfg.M1, O=cfg.O1, mode=cfg.mode_CM1, fpsclk=cfg.fpsclk1)
        MMCM2 = CM(fin=MMCM1.fout, D=cfg.D2, M=cfg.M2, O=cfg.O2, mode=cfg.mode_CM2, fpsclk=cfg.fpsclk2)
        MMCM3 = CM(fin=MMCM1.fout, D=cfg.D2, M=cfg.M2, O=cfg.O2)

        # Run Experiments
        port = serial.Serial(args.serial_port, args.baud_rate, timeout=args.timeout)
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

        # create a folder for the bitstream in the results directory
        bitstream_result_path = Path(args.results_dir) / bit_file_name
        util.create_folder(bitstream_result_path)

        # processing parameters
        T = 1 / MMCM2.fout
        N_Sets = MMCM1.fvco // (MMCM2.fvco - MMCM1.fvco)
        N_Samples = 56 * MMCM2.O * N_Sets / 2
        w_shift = math.ceil(math.log2(N_Samples))
        N_Bytes = math.ceil((w_shift + args.N_Parallel) / 8)
        sps = MMCM2.sps / N_Sets

        # Process Received Data
        error = False
        try:
            segments_rising = get_segments_delays(data_rising, N_Bytes, w_shift, args.N_Parallel, sps)
        except:
            log_error(bit_file_name, args.results_dir, 'Rising')
            error = True

        try:
            segments_falling = get_segments_delays(data_falling, N_Bytes, w_shift, args.N_Parallel, sps)
        except:
            log_error(bit_file_name, args.results_dir, 'Falling')
            error = True

        if error:
            exit()

        # store segments
        util.store_data(bitstream_result_path, 'segments_rising.data', segments_rising)
        util.store_data(bitstream_result_path, 'segments_falling.data', segments_falling)

        # Validate Results
        validation_result_rising =  validate_result(segments_rising, args.vivado_srcs_dir, bit_file_name, args.N_Parallel)
        validation_result_falling =  validate_result(segments_falling, args.vivado_srcs_dir, bit_file_name, args.N_Parallel)

        # Log Results
        log_results(validation_result_rising, bit_file_name, args.results_dir, 'Rising')
        log_results(validation_result_falling, bit_file_name, args.results_dir, 'Falling')

    elif args.subcommand == 'validate':
        # Create log files
        error_file = open(str(Path(args.results_dir) / 'Errors.txt'), 'w+')
        validation_file = open(str(Path(args.results_dir) / 'validation.txt'), 'w+')

        TCs = list(Path(args.results_dir).glob('TC*'))

        # pbar
        pbar = tqdm(total=len(TCs))

        for TC in TCs:
            bit_file_name = TC.stem
            bitstream_result_path = Path(args.results_dir) / bit_file_name

            pbar.set_description(bit_file_name)

            # Load segments
            segments_rising = util.load_data((str(TC)), 'segments_rising.data')
            segments_falling = util.load_data((str(TC)), 'segments_falling.data')

            # Validate Results
            validation_result_rising =  validate_result(segments_rising, args.vivado_srcs_dir, bit_file_name, args.N_Parallel)
            validation_result_falling =  validate_result(segments_falling, args.vivado_srcs_dir, bit_file_name, args.N_Parallel)

            # Log Results
            log_results(validation_result_rising, bit_file_name, args.results_dir, 'Rising')
            log_results(validation_result_falling, bit_file_name, args.results_dir, 'Falling')

            pbar.update(1)
    else:
        parser.print_help()