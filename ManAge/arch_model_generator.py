import time, sys
from arch.arch_model import DeviceModel
from utility.utility_functions import store_data
import utility.config as cfg

start_time = time.time()
viv_rpt_path = sys.argv[1]
device = DeviceModel()
device.parse(viv_rpt_path)

store_data(cfg.load_path, f'device_{device.name}.data', device)
print(time.time() - start_time)