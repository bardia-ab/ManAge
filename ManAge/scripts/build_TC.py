import os, sys, json
import re
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

from tqdm import tqdm
from xil_res.architecture import Arch
from xil_res.minimal_config import MinConfig
from relocation.configuration import Config
from xil_res.cut import CUT
import utility.utility_functions as util

'''a = {
    'CUT1':
         {'path1': [1,2,3,4],
          'path2': [5,6,7,8]
          },
    'CUT2':
         {'path1': [4,3,2,1],
          'path2': [8,7,6,5]
          }
     }

with open('path.json', 'w+') as file:
    json.dump(a, file, indent=2)

with open('path.json') as file:
    b = json.load(file)'''

# USer Inputs
device_name = sys.argv[1]
json_path = sys.argv[2]
store_path = sys.argv[3]
mode = sys.argv[4]
#device_name = 'xczu9eg'
#json_file = '/home/bardia/Desktop/bardia/Timing_Characterization/Backup/json_paths/TC73.json'
#store_path = '.'

# create device
device = Arch(device_name)

#retrieve JSON files
json_files = list(Path(json_path).glob('*.json'))

# create a progress bar
pbar = tqdm(total=len(json_files))

for json_file in json_files:
    with open(str(json_file)) as file:
        configuration = json.load(file)

    # create a TC
    if mode == 'minimal':
        TC_idx = int(re.findall('\d+', str(json_file.stem))[0])
        TC = MinConfig(device, TC_idx)
    else:
        TC = Config()
        TC.FFs = TC.create_FFs(device)
        TC.LUTs = TC.create_LUTs(device)
        TC.subLUTs = TC.create_subLUTs(device)


    for cut_name, edges in configuration.items():
        cut_index = int(re.findall('\d+', cut_name)[0])
        cut = CUT.conv_graph2CUT(TC, cut_index, *edges)

        if mode == 'minimal':
            TC.CUTs.append(cut)
        else:
            TC.D_CUTs.append(cut)

    # remove unused primitives
    TC.FFs = list(TC.filter_FFs(usage='used'))
    TC.LUTs = list(TC.filter_LUTs(usage='used'))
    TC.subLUTs = list(TC.filter_subLUTs(usage='used'))


    output_file = f'{Path(json_file).stem}.data'
    util.store_data(store_path, output_file, TC)

    pbar.update(1)