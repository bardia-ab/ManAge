import yaml, platform, os, re
from pathlib import Path
if Path(os.getcwd()).parts[-1] == 'scripts':
    os.chdir(os.path.abspath('..'))

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

arch_graph_path     = config[platform.system()]['arch_graph_path']
Data_path           = config[platform.system()]['Data_path']

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


######## LUT Dual Mode
print_message = False
LUT_Dual = True
LUT_Capacity = 2
block_mode = 'global'   #global|local
route_thru = True
pips_length_dict = {}


########### regex patterns
LUT_in_pattern = re.compile('^CLE.*_[A-H][1-6]$')
LUT_in6_pattern = re.compile('^CLE.*_[A-H]6$')
FF_in_pattern = re.compile('^CLE.*_[A-H][_XI]+$')
FF_out_pattern = re.compile('^CLE.*_[A-H]Q2*$')
Source_pattern = re.compile('^CLE.*_[A-H]Q2*$')
Sink_pattern = re.compile('^CLE.*_[A-H][_XI]+$')
CLB_out_pattern = re.compile('^CLE.*_[A-H]_O$')
MUXED_CLB_out_pattern = re.compile('^CLE.*_[A-H]MUX$')
Unregistered_CLB_out_pattern = re.compile('^CLE.*_[A-H]_O$|^CLE.*_[A-H]MUX$')
East_CLB = re.compile('^CLEL_R.*')
West_CLB = re.compile('(^CLEL_L|^CLEM).*')
FF_key_pattern = re.compile('^CLE.*/[A-H]FF2*$')
LUT_key_pattern = re.compile('^CLE.*/[A-H]LUT$')
top_group = re.compile('^CLE.*_[E-H].*')
bottom_group = re.compile('^CLE.*_[A-D].*')


######## Clock Domain
virtual_source_node = 's'
virtual_sink_node = 't'
not_virtual_source_node = 's_not'
not_virtual_sink_node = 't_not'
clock_domains = {'launch': Source_pattern, 'sample': Sink_pattern}
clock_domain_types = {'launch': 'source', 'sample': 'sink'}
src_sink_node = {'launch': virtual_source_node, 'sample': virtual_sink_node}
clock_groups = {'W_T': 'W_B', 'W_B': 'W_T', 'E_T': 'E_B', 'E_B': 'E_T'}

####### PIPs
pip_v = 'v'

####### Path
max_path_length = 10

###### TC
max_capacity = 16
long_TC_process_time = 60
