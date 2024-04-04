from itertools import product
from xil_res.node import Node as nd

def get_pips_FASM(*pips, mode=None):
    value = {'set': 1, 'clear': 0, None:'{}'}
    FASM_list = set()
    for pip in pips:
        suffix = get_pip_suffix(pip)
        FASM_list.add(get_pip_setting(pip, suffix, value[mode]))

    return FASM_list

def get_LUTs_FASM(LUTs, mode=None):
    FASM_list = set()
    value = {'set': 1, 'clear': 0, None: '{}'}

    for LUT in LUTs:
        # get init value
        tile = LUT.tile
        label = LUT.label
        init = LUT.get_init()
        FASM_list.add(get_LUT_INIT_FASM(tile, label, init))

        # OUTMUX
        for sublut in LUT.subLUTs:
            if nd.get_clb_node_type(sublut.output) == 'CLB_muxed':
                FASM_list.add(get_OUTMUX_FASM(tile, label, sublut.port[1], value[mode]))

    return FASM_list

def get_pip_setting(pip, suffix='', value='{}'):
    if nd.get_tile(pip[0]) != nd.get_tile(pip[1]):
        raise ValueError(f'invalid pip: tile_u = {nd.get_tile(pip[0])} & tile_v = {nd.get_tile(pip[1])}')

    INT_tile = nd.get_tile(pip[0])
    pip_u = nd.get_port(pip[0])
    pip_v = nd.get_port(pip[1])

    return f'{INT_tile}.PIP.{pip_v}.{pip_u}{suffix} = {value}'

def get_pip_suffix(pip):
    bidir_pips = [
        ('INT_NODE_IMUX_18_INT_OUT0', 'BYPASS_E14'),
        ('INT_NODE_IMUX_37_INT_OUT0', 'BYPASS_W8'),
        ('INT_NODE_IMUX_50_INT_OUT0', 'BYPASS_W14'),
        ('INT_NODE_IMUX_5_INT_OUT0', 'BYPASS_E8')
    ]

    if (nd.get_port(pip[0]), nd.get_port(pip[1])) in bidir_pips:
        suffix = '.REV'
    elif (nd.get_port(pip[1]), nd.get_port(pip[0])) in bidir_pips:
        suffix = '.FWD'
    else:
        suffix = ''

    return suffix

def get_OUTMUX_FASM(tile, label, subLUT_idx, value):
    return f'{tile}.OUTMUX{label}.D{subLUT_idx} = {value}'

def get_LUT_INIT_FASM(LUT_tile, label, init):
    return f"{LUT_tile}.{label}LUT.INIT[63:0] = 64h'{init}"

def get_dual_LUT_FASM(LUT_tile, label, value):
    i6_dct = {
        'A': 'IMUX_{}18',
        'B': 'IMUX_{}19',
        'C': 'IMUX_{}20',
        'D': 'IMUX_{}21',
        'E': 'IMUX_{}34',
        'F': 'IMUX_{}35',
        'G': 'IMUX_{}46',
        'H': 'IMUX_{}47'
    }
    i6_port = i6_dct[label].format(nd.get_direction(LUT_tile))
    INT_tile = f'INT_{nd.get_coordinate(LUT_tile)}'
    pip = (f'{INT_tile}/VCC_WIRE', f'{INT_tile}/{i6_port}')

    return get_pip_setting(pip, value=value)

def cal_init(input_idx, function, N_inputs):
    entries = get_truth_table(N_inputs)
    if function == 'not':
        init_list = [str(int(not(entry[input_idx]))) for entry in entries]
    elif function == 'buffer':
        init_list = [str(entry[input_idx]) for entry in entries]
    else:
        init_list = [str(0) for _ in entries]

    init_list.reverse()
    init_binary = ''.join(init_list)
    init = format(int(init_binary, base=2), f'0{2**N_inputs//4}X')

    return init

def get_truth_table(n_entry):
    truth_table = list(product((0, 1), repeat=n_entry))
    return [entry[::-1] for entry in truth_table]


if __name__ == '__main__':

    entry = get_truth_table(6)
    init = cal_init(5, 'not', 6)
    print('hi')
