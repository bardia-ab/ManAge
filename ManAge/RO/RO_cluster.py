import os, sys, re
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

import utility.config as cfg
import utility.utility_functions as util
from xil_res.architecture import Arch
from xil_res.node import Node as nd
from relocation.configuration import Config
from constraint.FASM import read_FASM
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

def relocate(fasm_list, new_clb):
    new_fasm_list = set()
    for entry in fasm_list:
        if entry.startswith('CLE'):
            new_fasm_list.add(re.sub('CLE[LM](_[LR])*_X\d+Y\d+', new_clb, entry))

        if entry.startswith('INT'):
            new_fasm_list.add(re.sub('INT(_INTF_[LR](_PCIE4|_TERM_GT)*)*_X\d+Y\d+|INT_INTF_(LEFT|RIGHT)_TERM_(IO|PSS)', f'INT_{nd.get_coordinate(new_clb)}', entry))

    return new_fasm_list

#################

# user inputs
device_name = sys.argv[1]
fasm_path = sys.argv[2]
rect_width = int(sys.argv[3])
rect_height = int(sys.argv[4])
store_path = sys.argv[5]

# create folder
Path(store_path).mkdir(exist_ok=True)

# Device
device = Arch(device_name, non_clb_tiles=True)

# fasm files
fasm_dict = {}
for file in Path(fasm_path).glob('*.fasm'):
    fasm_dict[file.stem] = read_FASM(file)

# reverse site_dict
reversed_site_dict = {value: key for key, value in device.site_dict.items()}

# Sites
sites = {device.site_dict[clb] for clb in device.get_CLBs()}
rectangles = split_grid(sites, rect_width, rect_height)

for rectangle in rectangles:
    fasm_list = set()
    clbs = {reversed_site_dict[site] for site in rectangle}
    min_x, max_x, min_y, max_y = get_boundaries(clbs)
    output_file = str(Path(store_path) / f'X{(min_x + max_x) // 2}Y{(min_y + max_y) // 2}.fasm')
    #if f'{bitstream_name}.data' in os.listdir(str(store_path)):
        #continue

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
            try:
                #INTF_tile = next(filter(lambda tile: re.match(f'INT_INTF_[LR]_(PCIE4)*_{nd.get_coordinate(clb)}', tile), device.tiles))
                INTF_tile = next(filter(lambda tile: tile.startswith('INT_INTF') and nd.get_coordinate(clb) in tile, device.tiles))
            except StopIteration:
                continue

            INTF_tile_type = INTF_tile.split("_X")[0]
            fasm_list.update(relocate(fasm_dict[INTF_tile_type], clb))

    with open(output_file, 'w+') as fasm_file:
        fasm_file.writelines(fasm_list)

    print(f'{Path(output_file).name} is done!')