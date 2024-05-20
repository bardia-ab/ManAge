from experiment.clock_manager import CM
from pathlib import Path
import os, re, math, sys
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from processing.cut_delay import CUTs_List, CUT_Delay
from xil_res.node import Node as nd
from constraint.configuration import ConstConfig
from utility.utility_functions import load_data


def pack_bytes(data, N_bytes):
    packets = []
    for i in range(0, len(data), N_bytes):
        packet = ''
        for j in range(N_bytes):
            packet += format(data[i + j], '02x')

        packets.append(packet)

    return packets

def pack_data(path, num_bytes):
    # It takes a text file path and groups the received data according to num_bytes determined in the HDL
    file = open(path, encoding='utf-8')
    try:
        lines = file.readlines()
    except UnicodeDecodeError:
        lines = file.readlines()

    file.close()

    chars = []
    n = num_bytes * 2
    for line in lines:
        line = line.replace(' ', '')
        if line.endswith('454E44'):
            line = line[:-6]
        else:
            pass
            #breakpoint()

        if len(lines) != 1:
            chars.extend(line.split())
        else:
            for i in range(0, len(line), n):
                chars.extend([line[i:i + n]])

    return chars

def convert_data(chars):
    # It converts hex values into decimal values
    Tx = []
    for char in chars:
        Tx.append(int(char, 16))

    return Tx

def extract_ila_data(load_path, FileName1, index, frmt):
    # index is the number of the desired column starting from 0
    # frmt: 1- int    2- hex
    values = []
    with open(os.path.join(load_path, FileName1)) as file:
        lines = file.readlines()

    for line in lines:
        if not re.match('^\d', line):
            continue

        line = line.rstrip('\n').split(',')
        if frmt == 'hex':
            values.append(int(line[index], base=16))
        else:
            values.append(int(line[index]))

    return values

def get_data_tuple(values, T, N, *CMs: CM, mode='set'):
    # mode: 1-set 2-incremental
    # in mode = set the order of CMs is important CM1, CM2
    # T is the clock period in seconds
    # N is the number of samples
    samples = []
    if mode == 'incremental':
        sps = 0
        for cm in CMs:
            if cm.mode == 'incremental':
                sps += cm.sps
            else:
                sps -= cm.sps

        for i in range(N):
            sample = (T - i * sps) % (T + 0.1)  # % T + 0.1: to limit sample values between 0 and T
            samples.append(sample)
    else:
        num_set_samples = int(56 * CMs[1].O)
        num_sets = int(CMs[0].fvco / abs(CMs[0].fvco - CMs[1].fvco))

        for N1 in range(num_sets):
            for N2 in range(num_set_samples):
                sample = (T - N1 * CMs[0].sps - N2 * CMs[1].sps) % (T + 0.1)
                samples.append(sample)

    data_tuple = list(zip(samples, values))
    data_tuple = sorted(data_tuple, key= lambda x: x[0])

    return data_tuple

def decompose_shift_capture(packets, w_shift, w_capture):
    shift_values = []
    CUT_indexes = []
    N_Bytes = math.ceil((w_shift + w_capture) / 8)
    bin_format = f'0{N_Bytes * 8}b'
    for packet in packets:
        bin_value = format(int(packet, base=16), bin_format)
        shift_values.append(int(bin_value[:-w_capture], base=2))
        CUT_indexes.append(bin_value[-w_capture:][::-1])

    return shift_values, CUT_indexes

def extract_delays(shift_values, CUT_indexes, N_Parallel, sps):
    segments = [[]]
    while shift_values:
        #segments.append([])
        while 1:
            shift_value = shift_values.pop(0)
            N_triggered = sum([1 for c in CUT_indexes[0] if c == '1'])
            if (len(segments[-1]) + N_triggered) > N_Parallel:
                segments[-1].sort()
                segments.append([])

            for CUT_idx, val in enumerate(CUT_indexes.pop(0)):
                if val == '1':
                    delay = shift_value * sps
                    segments[-1].append((CUT_idx, delay))


            '''if len(segments[-1]) >= N_Parallel:
                segments[-1].sort()
                break'''

            if not shift_values:
                segments[-1].sort()
                break

            '''prev_shift_value = shift_value
            if shift_values:
                if shift_values[0] > prev_shift_value:
                    segments[-1].sort()
                    break
            else:
                segments[-1].sort()
                break'''

    return segments

def get_segments_delays(rcvd_data, N_Bytes, w_shift, N_Parallel, sps):
    chars = pack_bytes(rcvd_data, N_Bytes)
    shift_values, CUT_indexes = decompose_shift_capture(chars, w_shift, N_Parallel)
    segments_delays = extract_delays(shift_values, CUT_indexes, N_Parallel, sps)

    return segments_delays

def validate_result(segments, vivado_srcs_path, TC_name, N_Parallel):
    try:
        vivado_srcs_path = next(Path(vivado_srcs_path).rglob(TC_name))
    except:
        print(vivado_srcs_path, TC_name)
        exit()

    stats_file = vivado_srcs_path / 'stats.txt'
    with open(stats_file) as lines:
        N_segments = int(re.search('\d+', next(lines))[0])
        N_partial = int(re.search('\d+', next(lines))[0])

    if N_partial > 0:
        l_segments = N_segments + 1
        if all(map(lambda x: len(x) == N_Parallel, segments[:-1])) and len(segments[-1]) == N_partial and len(segments) == l_segments:
            result = True
        elif all(map(lambda x: len(x) == N_Parallel, segments[:-1])) and len(segments[-1]) == N_Parallel and len(segments) == l_segments:
            del segments[-1][N_partial:]
            result = True
        else:
            result = False
    else:
        l_segments = N_segments
        if all(map(lambda x: len(x) == N_Parallel, segments)) and len(segments) == l_segments:
            result = True
        else:
            result = False

    return result

def log_results(result, bit_file_name, store_path, type):
    if result:
        print(f'{bit_file_name} => Rising Passed!\n')
    else:
        validation_file = Path(store_path) / 'validation.txt'
        with open(validation_file, 'a+') as file:
            file.write(f'{bit_file_name} => {type} Failed!\n')

def log_error(bit_file_name, store_path, type):
    error_file = Path(store_path) / 'Errors.txt'
    with open(error_file, 'a+') as file:
        file.write(f'{bit_file_name} => {type} Failed!\n')

def get_invalid_TCs(result_path):
    TCs = set()
    files = ['Errors.txt', 'validation.txt']
    for file in files:
        if file not in os.listdir(result_path):
            continue

        with open(os.path.join(result_path, file)) as txt:
            for line in txt.readlines():
                if line == '\n':
                    continue

                TC = line.split(' => ')[0]
                TCs.add(TC)

    return TCs

def fill_cuts_list(TC_result_path, TC_CUT_path, N_Parallel, TC, skew_path=None):
    TC_idx = int(re.findall('\d+', TC)[0])
    results_path = os.path.join(TC_result_path, TC)
    cuts_list = fill_D_CUTs(TC_CUT_path, TC)

    skew_dict = {}
    if skew_path:
        with open(f'{skew_path}/{TC}.txt') as file:
            for line in file.readlines():
                try:
                    CUT_idx, max_skew, min_skew = line.rstrip('\n').split('\t')
                except:
                    print(f'********************* {line} ***************')
                    print(TC_idx)
                    print(skew_path)
                    CUT_idx = line.rstrip('\n').split('\t')[0]
                    max_skew = 0
                    min_skew = 0

                if not max_skew:
                    max_skew = 0

                if not min_skew:
                    min_skew = 0

                path_idx = int(CUT_idx.split('_')[-1]) % N_Parallel
                seg_idx = int(CUT_idx.split('_')[-1]) // N_Parallel
                skew_dict[(seg_idx, path_idx)] = (float(max_skew) + float(min_skew)) / 2 * 1e-9


    for result in os.listdir(results_path):
        segments = load_data(results_path, result)
        for seg_idx, segment in enumerate(segments):
            for (path_idx, path_delay) in segment:
                D_CUT_idx = seg_idx * N_Parallel + path_idx
                try:
                    cut_delay = cuts_list.CUTs[D_CUT_idx]
                except:
                    continue

                cut_delay.seg_idx = seg_idx
                cut_delay.path_idx = path_idx

                # skew
                skew = skew_dict[(seg_idx, path_idx)] if skew_path else 0

                if 'rising' in result:
                    cut_delay.rising_delay = path_delay + skew
                else:
                    cut_delay.falling_delay = path_delay + skew

    cuts_list.CUTs = [cut_delay for cut_delay in cuts_list.CUTs if cut_delay.rising_delay != 0 and cut_delay.falling_delay != 0]
    return cuts_list.CUTs

def fill_D_CUTs(TC_CUT_path, TC):
    cuts_list = CUTs_List([])
    TC_idx = int(re.findall('\d+', TC)[0])
    TC_label = TC.split('_')[0]
    TC_CUT = load_data(TC_CUT_path, f'{TC_label}.data')
    if 'even' in TC:
        D_CUTs, _ = ConstConfig.split_D_CUTs(TC_CUT, 'FF_in_index')
    elif 'odd' in TC:
        _, D_CUTs = ConstConfig.split_D_CUTs(TC_CUT, 'FF_in_index')
    else:
        D_CUTs = [D_CUT for R_CUT in TC_CUT.CUTs for D_CUT in R_CUT.D_CUTs]

    D_CUTs.sort(key=lambda x: (x.index, nd.get_x_coord(x.origin), nd.get_y_coord(x.origin)))
    for D_CUT in D_CUTs:
        edges = [edge for edge in D_CUT.G.edges if D_CUT.G.get_edge_data(*edge)['path_type'] == 'main_path']
        cut_delay = CUT_Delay(origin=D_CUT.origin, CUT_idx=D_CUT.index, TC_idx=TC_idx, edges=edges)
        cuts_list.CUTs.append(cut_delay)

    return cuts_list
