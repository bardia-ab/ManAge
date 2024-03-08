import yaml, platform, os, re
from pathlib import Path
if Path(os.getcwd()).parts[-1] == 'scripts':
    os.chdir(os.path.abspath('..'))

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

arch_graph_path     = config[platform.system()]['arch_graph_path']
Data_path           = config[platform.system()]['Data_path']
vivado_project_path  = config[platform.system()]['vivado_project_path']

############## Directories
minimal_config_path = os.path.join(Data_path, 'Minimal_Configurations')
load_path           = os.path.join(Data_path, 'Load')
graph_path          = os.path.join(Data_path, 'Compressed_Graphs')
config_path         = os.path.join(Data_path, 'Configurations')
vivado_res_path     = os.path.join(Data_path, 'Vivado_Resources')
test_result_path    = os.path.join(Data_path, 'Results')
bitstream_path      = os.path.join(Data_path, 'Bitstreams')
dcp_path            = os.path.join(Data_path, 'DCPs')
log_path            = os.path.join(Data_path, 'Logs')


######## general
print_message = config['General']['print_message']
LUT_Dual = config['General']['LUT_Dual']
LUT_Capacity = config['General']['LUT_Capacity']
block_mode = config['General']['block_mode']   #global|local
route_thru = config['General']['route_thru']
pips_length_dict = {}


########### regex patterns
LUT_in_pattern = re.compile(config['Regex']['LUT_in_pattern'])
LUT_in6_pattern = re.compile(config['Regex']['LUT_in6_pattern'])
FF_in_pattern = re.compile(config['Regex']['FF_in_pattern'])
FF_out_pattern = re.compile(config['Regex']['FF_out_pattern'])
Source_pattern = re.compile(config['Regex']['Source_pattern'])
Sink_pattern = re.compile(config['Regex']['Sink_pattern'])
CLB_out_pattern = re.compile(config['Regex']['CLB_out_pattern'])
MUXED_CLB_out_pattern = re.compile(config['Regex']['MUXED_CLB_out_pattern'])
Unregistered_CLB_out_pattern = re.compile(config['Regex']['Unregistered_CLB_out_pattern'])
East_CLB = re.compile(config['Regex']['East_CLB'])
West_CLB = re.compile(config['Regex']['West_CLB'])
FF_key_pattern = re.compile(config['Regex']['FF_key_pattern'])
LUT_key_pattern = re.compile(config['Regex']['LUT_key_pattern'])
top_group = re.compile(config['Regex']['top_group'])
bottom_group = re.compile(config['Regex']['bottom_group'])


######## Clock Domain
virtual_source_node = config['Clock_Domain']['virtual_source_node']
virtual_sink_node = config['Clock_Domain']['virtual_sink_node']
not_virtual_source_node = config['Clock_Domain']['not_virtual_source_node']
not_virtual_sink_node = config['Clock_Domain']['not_virtual_sink_node']
clock_domain_types = config['Clock_Domain']['clock_domain_types']
clock_groups = config['Clock_Domain']['clock_groups']
clock_domains = {'launch': Source_pattern, 'sample': Sink_pattern}
src_sink_node = {'launch': virtual_source_node, 'sample': virtual_sink_node}

####### PIPs
pip_v = config['PIPs']['pip_v']
n_pips_two_CLB = config['PIPs']['n_pips_two_CLB']
n_pips_one_CLB = config['PIPs']['n_pips_one_CLB']

####### Path
max_path_length = config['Path']['max_path_length']

###### TC
max_capacity = config['TC']['max_capacity']
long_TC_process_time = config['TC']['long_TC_process_time']

##### constraints
name_prefix = config['Constraints']['name_prefix']
launch_net = config['Constraints']['launch_net']
route_thru_net = config['Constraints']['route_thru_net']
launch_FF_cell = config['Constraints']['launch_FF_cell']
sample_FF_cell = config['Constraints']['sample_FF_cell']
not_LUT_cell_name = config['Constraints']['not_LUT_cell_name']
buff_LUT_cell = config['Constraints']['buff_LUT_cell']
N_Parallel = config['Constraints']['N_Parallel']

##### python
python = 'python' if platform.system() == 'Windows' else 'python3'
