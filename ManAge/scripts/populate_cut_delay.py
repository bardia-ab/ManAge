import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
import utility.config as cfg

TCs_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment\min_bitstreams\X2Y1'
TCs_result_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment\Results\minimal\iter0'
skew_path = None
store_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment'

script = str(Path(__file__).parent.parent / 'processing' / 'result_process.py')
os.system(f'{cfg.python} "{script}" {TCs_path} {TCs_result_path} {skew_path} {store_path}')