import os, sys, re, argparse, subprocess
from collections import Counter
from tqdm import tqdm
from joblib import Parallel, delayed
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

from RO_Functions import *
import utility.config as cfg
import utility.utility_functions as util
from xil_res.architecture import Arch
from xil_res.minimal_config import MinConfig
from xil_res.cut import CUT
from xil_res.node import Node as nd
from xil_res.edge import Edge
from relocation.configuration import Config
from constraint.FASM import *
#################
def get_boundaries(entries):
    points = {(nd.get_x_coord(entry), nd.get_y_coord(entry)) for entry in entries}
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)

    return min_x, max_x, min_y, max_y

def split_grid(sites, rect_width, rect_height):
    points = {(nd.get_x_coord(entry), nd.get_y_coord(entry)) for entry in sites}
    min_x, max_x, min_y, max_y = get_boundaries(sites)
    rectangles = []
    for x_start in range(min_x, max_x + 1, rect_width):
        for y_start in range(min_y, max_y + 1, rect_height):
            rectangle = []
            for x in range(x_start, min(x_start + rect_width, max_x + 1)):
                for y in range(y_start, min(y_start + rect_height, max_y + 1)):
                    if (x, y) in points:
                        rectangle.append(f"SLICE_X{x}Y{y}")
            if rectangle:
                rectangles.append(rectangle)
    return rectangles

def fill_rect_TC(device, TC, rectangle, D_CUTs, split_TC_path):
    clbs = {k for site in rectangle for k, v in device.site_dict.items() if site == v}
    min_x, max_x, min_y, max_y = get_boundaries(clbs)
    bitstream_name = f'X{(min_x + max_x) // 2}Y{(min_y + max_y) // 2}'
    if f'{bitstream_name}.data' in os.listdir(str(split_TC_path)):
        return

    rect_TC = Config()
    for clb in clbs:
        filtered_D_CUTs = filter(lambda x: clb in (nd.get_tile(node) for node in x.G), D_CUTs)
        rect_TC.D_CUTs.extend(filtered_D_CUTs)
        rect_TC.LUTs.update({k:v for k, v in TC.LUTs.items() if nd.get_tile(k) == clb})

    util.store_data(str(split_TC_path), f'{bitstream_name}.data', rect_TC)
    print(f'{bitstream_name} is done!')

def relocate(fasm_list, new_tile):
    new_fasm_list = set()
    for entry in fasm_list:
        if entry.startswith(cfg.CLB_label):
            new_fasm_list.add(re.sub(f'{cfg.CLB_pattern.pattern[:-1]}', new_tile, entry))

        if entry.startswith(cfg.BRAM_label):
            new_fasm_list.add(re.sub(f'{cfg.BRAM_pattern}', new_tile, entry))

        if entry.startswith(cfg.INT_label):
            INT_tile = f'{cfg.INT_label}_{nd.get_coordinate(new_tile)}' if nd.get_tile_type(new_tile) == 'CLB' else new_tile
            new_fasm_list.add(re.sub(f'{cfg.INT_label}(_INTF_[LR](_PCIE4|_TERM_GT)*)*_X\d+Y\d+|INT_INTF_(LEFT|RIGHT)_TERM_(IO|PSS)', INT_tile, entry))

    return new_fasm_list

def preserve_clk_pips(G, clk_pips):
    removed_pips = set()
    if Path(clk_pips).exists():
        with open(clk_pips) as file:
            for line in file:
                line = re.split('<*->+', line)
                tile = line[0].split('/')[0]
                pip_u = line[0].split('.')[-1]
                pip_v = line[1].rstrip("\n")
                pip = (f'{tile}/{pip_u}', f'{tile}/{pip_v}')
                removed_pips.add(pip)

    G.remove_edges_from(removed_pips)

def remove_pips(removed_pips_file):
    removed_pips = set()
    with open(removed_pips_file) as file:
        for line in file:
            line = re.split('<*->+', line)
            tile = line[0].split('/')[0]
            pip_u = line[0].split('.')[-1]
            pip_v = line[1].rstrip("\n")
            pip = (f'{tile}/{pip_u}', f'{tile}/{pip_v}')
            removed_pips.add(pip)

    return get_pips_FASM(*removed_pips, mode='clear')

def get_netlist(G):
    all_paths = get_ROs(G)
    antennas = get_antennas(G, all_paths)

    edges = set()
    for path in all_paths + antennas:
        edges.update(zip(path, path[1:]))

    G_netlist = nx.DiGraph()
    G_netlist.add_edges_from(edges)

    return G_netlist, all_paths, antennas

def add_cut(TC, edges):
    cut = CUT(cut_index=len(TC.CUTs))

    # create graph
    cut.create_CUT_G_from_edges(*edges)

    # create subLUTs
    cut.create_CUT_subLUTs(TC)

    TC.CUTs.append(cut)

def store_fasm(TC, removed_pips_file, store_path, fasm_name):
    fasm_list = set()
    pips = set()

    for cut in TC.CUTs:
        pips.update(edge for edge in cut.G.edges if Edge(edge).get_type() == 'pip')

    LUTs = set(filter(lambda x: x.capacity < 2, TC.LUTs.values()))
    for LUT in LUTs:
        tile = LUT.tile
        label = LUT.label
        init = LUT.get_init()
        if LUT.capacity == 1:
            init = 2 * init[8:]
            OUTMUX_idx = 5
        else:
            OUTMUX_idx = 6

        fasm_list.add(get_LUT_INIT_FASM(tile, label, init))
        fasm_list.add(get_FFMUX_FASM(tile, label, 6, 1, 1))
        fasm_list.add(get_FFMUX_FASM(tile, label, 6, 2, 1))
        fasm_list.add((get_OUTMUX_FASM(tile, label, OUTMUX_idx, 1)))

        fasm_list.update(get_FF_CTRL_pips(tile, nd.get_top_bottom(LUT.name), nd.get_direction(LUT.name), 1, 1))
        fasm_list.update(get_FF_CTRL_pips(tile, nd.get_top_bottom(LUT.name), nd.get_direction(LUT.name), 2, 1))

    LUT_tiles = {LUT.tile for LUT in LUTs}
    for tile in LUT_tiles:
        clock_groups = list(product({'T', 'B'}, {'W', 'E'}))
        for clock_group in clock_groups:
            fasm_list.update(get_FF_CTRL_pips(tile, clock_group[0], clock_group[1], 1, 1))
            fasm_list.update(get_FF_CTRL_pips(tile, clock_group[0], clock_group[1], 2, 1))

        for idx in range(65, 73):
            label = chr(idx)
            # FF settings
            fasm_list.add(f'{tile}.{label}FF.INIT.V0')
            fasm_list.add(f'{tile}.{label}FF.SRVAL.V0')

    fasm_list.update(get_pips_FASM(*pips, mode='set'))

    # remove pips
    if removed_pips_file is not None:
        fasm_list.update(remove_pips(removed_pips_file))

    store_file = Path(store_path) / f'{fasm_name}.fasm'

    with open(str(store_file), 'w+') as fasm_file:
        fasm_file.write('\n'.join(sorted(fasm_list)))
        fasm_file.write('\n')

def design(args, device):
    tiles = []
    x_min, x_max, y_min, y_max = device.get_device_dimension()
    center_coord = lambda x: x_min + 12 <= nd.get_x_coord(x) <= x_max - 12 and y_min + 12 <= nd.get_y_coord(x) <= y_max - 12
    tiles.append(next(filter(lambda x: device.get_tile_map_type(x) == 'Both' and center_coord(x), device.tiles_map)))
    tiles.append(next(filter(lambda x: device.get_tile_map_type(x) == 'West' and center_coord(x), device.tiles_map)))
    tiles.append(next(filter(lambda x: device.get_tile_map_type(x) == 'East' and center_coord(x), device.tiles_map)))

    for tile in tiles:

        # Set graph
        #device.set_compressed_graph(tile)
        x, y= nd.get_x_coord(tile), nd.get_y_coord(tile)
        device.G = device.get_graph(default_weight=1, xlim_down=x, xlim_up=x, ylim_down=y, ylim_up=y)

        # preserve clock PIPs
        if args.clk_pips_file is not None:
            preserve_clk_pips(device.G, args.clk_pips_file)

        # Keep one coordinate
        invalid_nodes = set(filter(lambda node: nd.get_coordinate(node) != nd.get_coordinate(tile), device.G))
        device.G.remove_nodes_from(invalid_nodes)

        # get RO paths
        G_netlist, all_paths, antennas = get_netlist(device.G)
        assert nx.is_forest(G_netlist), "Collision Occured!!!"

        # create a TC
        TC_idx = device.get_tile_map_type(nd.get_coordinate(tile))
        TC = MinConfig(device, TC_idx)

        for path in all_paths:
            edges = zip(path, path[1:])
            add_cut(TC, edges)

        # add antennas
        edges = {edge for path in antennas for edge in zip(path, path[1:])}
        add_cut(TC, edges)

        # store FASM
        store_fasm(TC, args.remove_pips_file, args.output_fasm_dir, TC_idx)

def cluster(args, device):

    # fasm files
    fasm_dict = {}
    for file in Path(args.input_fasm_dir).glob('*.fasm'):
        fasm_dict[file.stem] = read_FASM(file)

    # reverse site_dict
    reversed_site_dict = {value: key for key, value in device.site_dict.items()}

    # Sites
    sites = {device.site_dict[clb] for clb in device.get_CLBs()}
    rectangles = split_grid(sites, args.size[0], args.size[1])
    l_sites = [len(rectangle) for rectangle in rectangles]
    print(Counter(l_sites))

    # filter
    if args.filter is not None:
        rectangles = [next(filter(lambda x: device.site_dict[args.filter] in x, rectangles))]

    # pbar
    pbar = tqdm(total=len(rectangles))

    for rectangle in rectangles:
        fasm_list = set()
        clbs = {reversed_site_dict[site] for site in rectangle}
        min_x, max_x, min_y, max_y = get_boundaries(clbs)
        output_file = str(Path(args.output_fasm_dir) / f'X{(min_x + max_x) // 2}Y{(min_y + max_y) // 2}.fasm')

        pbar.set_description(Path(output_file).name)

        for clb in clbs:
            tile_map_type = device.get_tile_map_type(nd.get_coordinate(clb))
            if tile_map_type == 'Both':
                if len(set(device.tiles_map[nd.get_coordinate(clb)].values()) & clbs) == 2:
                    fasm_list.update(relocate(fasm_dict[tile_map_type], clb))
                elif device.tiles_map[nd.get_coordinate(clb)]['CLB_W'] in clbs:
                    fasm_list.update(relocate(fasm_dict['West'], clb))
                elif device.tiles_map[nd.get_coordinate(clb)]['CLB_E'] in clbs:
                    fasm_list.update(relocate(fasm_dict['East'], clb))
                else:
                    raise ValueError('{clb}')

            else:
                fasm_list.update(relocate(fasm_dict[tile_map_type], clb))

        '''bottom_left, top_right = nd.get_borders_coords(*clbs)
        BRAM_tiles = set(filter(lambda x: x.startswith('BRAM_X') and nd.is_tile_in_rectangle(bottom_left, top_right, x),
                                device.tiles))

        for tile in BRAM_tiles:
            fasm_list.update(relocate(fasm_dict['BRAM_pattern'], tile))'''


        with open(output_file, 'w+') as fasm_file:
            fasm_file.write('\n'.join(sorted(fasm_list)))
            fasm_file.write('\n')

        pbar.update(1)

def gen_bitstream(pyteman_path, fasm_file, blank_bitstream, bitstream_path, pbar):
    output_bitstream = Path(fasm_file).with_suffix('.bit').name
    bitstream_file = Path(bitstream_path) / output_bitstream
    pbar.set_description(output_bitstream)
    script = Path(pyteman_path) / 'fasm2bit.py'
    result = subprocess.run([cfg.python, script, fasm_file, blank_bitstream, bitstream_file], capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)
        exit()

    pbar.update(1)

#################

# Create parser
parser = argparse.ArgumentParser(prog='RO_cluster', description='Design RO network')
subparser = parser.add_subparsers(title='subcommands', dest='subcommand')

# Create a parent parser
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument('device_name', choices=Arch.get_models(), help='Specify the fabric of the FPGA')

# Subcommand: design
parser_design = subparser.add_parser('design', parents=[parent_parser], help='Design RO nwteork for each type of coordinates')
parser_design.add_argument('output_fasm_dir', help='Path to the output FASM files directory')

parser_design.add_argument('-c', '--clk_pips_file', help='Specify the path to clock pips file. These pips are excluded from the design.')
parser_design.add_argument('-r', '--remove_pips_file', help='Specify the path to a pips file that must be excluded from the design.')

# Subcommand: cluster
parser_cluster = subparser.add_parser('cluster', parents=[parent_parser], help='Cluster the whole fabric into specified window size.')
parser_cluster.add_argument('input_fasm_dir', help='Path to the input FASM files directory')
parser_cluster.add_argument('size', type=int, nargs=2, help='Specify the size of the window (Width, Height)')
parser_cluster.add_argument('output_fasm_dir', help='Path to the output FASM files directory')

parser_cluster.add_argument('-f', '--filter', help='Specify the CLB tile whose encompassing window is desired')

# Subcommand: bitstream
parser_bitstream = subparser.add_parser('bitstream', parents=[parent_parser], help='Generate bitstreams for FASM files')
parser_bitstream.add_argument('input_fasm_dir', help='Path to the input FASM files directory')
parser_bitstream.add_argument('blank_bitstream_file', help='Path to the blank bitstream file')
parser_bitstream.add_argument('output_bitstream_dir', help='Path to the output bitstream files directory')


if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    # Device
    device = Arch(args.device_name, non_clb_tiles=True)

    if args.subcommand == 'design':
        # create folder
        Path(args.output_fasm_dir).mkdir(parents=True, exist_ok=True)

        design(args, device)

    elif args.subcommand == 'cluster':
        # create folder
        Path(args.output_fasm_dir).mkdir(parents=True, exist_ok=True)

        cluster(args, device)

    elif args.subcommand == 'bitstream':
        # create folder
        Path(args.output_bitstream_dir).mkdir(parents=True, exist_ok=True)

        # Create pbar
        fasm_files = list(Path(args.input_fasm_dir).glob('*.fasm'))
        pbar = tqdm(total=len(fasm_files))

        Parallel(n_jobs=cfg.n_jobs, require='sharedmem')(delayed(gen_bitstream)(cfg.pyteman_path, fasm_file, args.blank_bitstream_file, args.output_bitstream_dir, pbar) for fasm_file in fasm_files)

        
    else:
        parser.print_help()


