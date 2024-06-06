import os
import utility.config as cfg
import utility.utility_functions as util

pips_mode = 'local'
device_name = 'xczu7eg'

for iteration, desired_tile in enumerate({'INT_X45Y90'}):
    # usage: python3 path_finder.py device_name desired_tile iteration pips_mode
    command = f'{cfg.python} path_finder.py {device_name} {desired_tile} {iteration + 1} {pips_mode}'
    os.system(command)