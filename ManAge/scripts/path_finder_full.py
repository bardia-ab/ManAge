import subprocess, os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

import utility.config as cfg

if __name__ == '__main__':
    device_name = 'xcvu9p'
    data_path = r'/home/bardia/Desktop/bardia/ManAge_Data/Data_xcvu9p_full'
    coords = {
        'xczu7eg': ['X45Y90', 'X42Y90'],
        'xczu9eg': ['X45Y90', 'X44Y90'],
        'xcvu9p': ['X42Y749', 'X43Y749', 'X44Y749']
    }
    desired_CR = 'X2Y12'

    coord = coords[device_name][0]
    minimal_config_dir = Path(data_path) / 'Minimal_Configurations' / 'iter1'
    subprocess.run([cfg.python, 'path_finder.py', device_name, coord, '1', minimal_config_dir], capture_output=False, text=True)

    config_dir = Path(data_path) / 'Configurations' / 'iter1'
    subprocess.run([cfg.python, 'relocate_CUTs.py', device_name, coord, minimal_config_dir, config_dir, '-c',desired_CR],
                         capture_output=False, text=True)

    for idx in range(1, 3):
        coord = coords[device_name][idx]
        prev_config_dir = Path(data_path) / 'Configurations' / f'iter{idx}'
        minimal_config_dir = Path(data_path) / 'Minimal_Configurations' / f'iter{idx + 1}'
        subprocess.run([cfg.python, 'path_finder.py', device_name, coord, f'{idx + 1}', minimal_config_dir, '-p', prev_config_dir], capture_output=False, text=True)

        config_dir = Path(data_path) / 'Configurations' / f'iter{idx + 1}'
        subprocess.run([cfg.python, 'relocate_CUTs.py', device_name, coord, minimal_config_dir, config_dir, '-p', prev_config_dir, '-c', desired_CR],
                             capture_output=False, text=True)

    '''coord = 'X49Y764'
    idx = 5
    prev_config_dir = Path(data_path) / 'Configurations' / f'iter{idx}'
    minimal_config_dir = Path(data_path) / 'Minimal_Configurations' / f'iter{idx + 1}'
    subprocess.run(
        [cfg.python, 'path_finder.py', device_name, coord, f'{idx + 1}', minimal_config_dir, '-p', prev_config_dir],
        capture_output=False, text=True)

    config_dir = Path(data_path) / 'Configurations' / f'iter{idx + 1}'
    subprocess.run(
        [cfg.python, 'relocate_CUTs.py', device_name, coord, minimal_config_dir, config_dir, '-p', prev_config_dir,
         '-c', desired_CR],
        capture_output=False, text=True)'''

    #rloc = load_data('/home/bardia/Desktop/bardia/ManAge_Data/Data_xcvu9p_full/Configurations/iter4', 'rloc_collection.data')
    #covered_double = {k: len(v) for k, v in rloc.covered_pips.items() if nd.get_x_coord(k) in range(44, 51) and nd.get_y_coord(k) in range(720, 780) and k.startswith('INT')}
    #next(tile for tile, covered in covered_double.items() if covered == min(covered_double.values()))
    #min(covered_double.values())