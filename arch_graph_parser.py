import os.path
import sys
from xil_res.architecture import Arch
import processing.plot as plot
import arch.analysis as an
import scripts.config as cfg

# initialize device
device_name = sys.argv[1]
device = Arch(device_name)

# draw tiles_map heatmap
parsed_tiles_map = an.parse_tiles_map(device.tiles_map)
store_path = os.path.join(cfg.Data_path, 'Analysis')
filename = 'tiles_map'
plot.print_heatmap_tiles_map(parsed_tiles_map, store_path=store_path, filename=filename)


# draw wires_dict heatmap
parsed_wires_dict = an.parse_wires_dict(device.wires_dict)
store_path = os.path.join(cfg.Data_path, 'Analysis')
filename = 'wires_dict'
plot.print_heatmap_wires_dict(parsed_wires_dict, store_path=store_path, filename=filename)

