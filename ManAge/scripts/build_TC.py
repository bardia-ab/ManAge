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


# USer Inputs
device_name = sys.argv[1]
json_path = sys.argv[2]
store_path = sys.argv[3]
mode = sys.argv[4]

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


    for cut_label in configuration:
        (cut_name, origin) = cut_label.split('_')
        cut_index = int(re.findall('\d+', cut_name)[0])
        edges = configuration[cut_label]['edges']
        cut = CUT.conv_graph2CUT(TC, cut_index, origin, *edges)

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