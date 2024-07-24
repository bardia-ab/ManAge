import subprocess
import utility.config as cfg
import utility.utility_functions as util

if __name__ == '__main__':
    device_name = 'xczu9eg'
    data_path = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\Data_xczu9eg'

    coord = 'X45Y90'
    minimal_config_dir = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\Data_xczu9eg\Minimal_Configurations\iter1'
    run = subprocess.run([cfg.python, 'path_finder.py', device_name, coord, '1', minimal_config_dir, '-l'], capture_output=False, text=True)

    config_dir = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\Data_xczu9eg\Configurations\iter1'
    run = subprocess.run([cfg.python, 'relocate_CUTs.py', device_name, coord, minimal_config_dir, config_dir, '-c', 'X2Y1'],
                         capture_output=False, text=True)

    coord = 'X44Y90'
    prev_config_dir = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\Data_xczu9eg\Configurations\iter1'
    minimal_config_dir = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\Data_xczu9eg\Minimal_Configurations\iter2'
    run = subprocess.run([cfg.python, 'path_finder.py', device_name, coord, '2', minimal_config_dir, '-p', prev_config_dir, '-l'], capture_output=False, text=True)

    config_dir = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\Data_xczu9eg\Configurations\iter2'
    run = subprocess.run([cfg.python, 'relocate_CUTs.py', device_name, coord, minimal_config_dir, config_dir, '-p', prev_config_dir, '-c', 'X2Y1'],
                         capture_output=False, text=True)