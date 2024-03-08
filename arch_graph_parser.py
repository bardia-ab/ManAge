import sys
import seaborn as sns
from xil_res.architecture import Arch
from processing.plot import print_heatmap
import arch.analysis as an

# initialize device
#device_name = sys.argv[1]
device_name = 'xczu3eg'
device = Arch(device_name)

# draw tiles_map heatmap
#parsed_tiles_map = an.parse_tiles_map(device)
#print_heatmap(parsed_tiles_map)


# draw wires_dict heatmap
parsed_wires_dict = an.parse_wires_dict(device)
print_heatmap(parsed_wires_dict)

print('hi')
