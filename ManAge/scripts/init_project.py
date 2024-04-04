import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import utility.utility_functions as util
import utility.config as cfg

util.create_folder(cfg.Data_path)
util.create_folder(cfg.minimal_config_path)
util.create_folder(cfg.load_path)
util.create_folder(cfg.graph_path)
util.create_folder(cfg.config_path)
util.create_folder(cfg.vivado_res_path)
util.create_folder(cfg.test_result_path)
util.create_folder(cfg.bitstream_path)
util.create_folder(cfg.dcp_path)
util.create_folder(cfg.log_path)