import os
import scripts.config as cfg
import scripts.utility_functions as util
from xil_res.architecture import Arch
#from relocation.relocation_storage import RLS
from relocation.configuration import Config
from xil_res.node import Node as nd
from relocation.rloc import RLOC as rl

if __name__ == "__main__":

    # User's inputs
    desired_tile = 'INT_X46Y90'
    iteration = len(cfg.minimal_config_path)

    # create the iteration folder
    cfg.minimal_config_path = os.path.join(cfg.config_path, f'iter{iteration}')
    util.create_folder(cfg.config_path)

    # init device
    device = Arch('xczu9eg')

    # config
    TC = Config()
    print('hi')
