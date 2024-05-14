import sys, os, time
from pathlib import Path
if not (Path(os.getcwd()).parts[-1] == Path(os.getcwd()).parts[-2] == 'ManAge'):
    sys.path.append(str(Path(__file__).parent.parent))
    os.chdir(str(Path(__file__).parent.parent))

import utility.config as cfg

script = Path(__file__).parent.parent / 'Ageing_Experiment' / 'Ageing.py'
RO_bitstream = '/home/bardia/Downloads/osci_lut6c_flood_stage2_wwee12_ff_unit_9eg_BLANKLUT_60clb'
blank_bitstream = '/home/bardia/Downloads/blank_zu9eg_jtag'
minimal_char_bitstream_path = '/home/bardia/Desktop/bardia/Timing_Characterization/Backup/Data_xczu9eg/Bitstreams/X2Y1'
full_char_bitstream_path = '/home/bardia/Desktop/bardia/Timing_Characterization/CR_X2Y1/Bitstreams'
store_path = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment'
cycles = 4

command = f'{cfg.python} {str(script)} {RO_bitstream} {blank_bitstream} {minimal_char_bitstream_path} {full_char_bitstream_path} {store_path} {cycles}'
os.system(command)