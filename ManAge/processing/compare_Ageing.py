import os, sys, time
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from processing.data_process import *
from processing.plot import plot_ageing_hist, plot_edge_type_bar
import utility.utility_functions as util

# User inputs
ref_cuts_list_file = sys.argv[1]
cuts_list_file = sys.argv[2]
store_path = sys.argv[3]
file_name = sys.argv[4]

if ref_cuts_list_file == cuts_list_file:
    exit()

# store folder
Path(store_path).mkdir(parents=True, exist_ok=True)

# load reference cuts list
ref_cuts_list_path, ref_file = str(Path(ref_cuts_list_file).parent), Path(ref_cuts_list_file).name
ref_cuts_list = util.load_data(ref_cuts_list_path, ref_file)
ref_df = conv_cuts_list2df(ref_cuts_list)

# load cuts list
cuts_list_path, file = str(Path(cuts_list_file).parent), Path(cuts_list_file).name
cuts_list = util.load_data(cuts_list_path, file)
df = conv_cuts_list2df(cuts_list)

# Filter out uncommon rows
ref_df, df = merge_df(ref_df, df)

# Add the percentage increase for 'rising_delay' and 'falling_delay'
df = add_incr_delay_columns(ref_df, df, 'rising_delay_increase_%', 'falling_delay_increase_%')

# Filter Aged CUTs
rising_aged_df = get_aged_df(df, 'rising_delay_increase_%', ['falling_delay_increase_%', 'falling_delay'])
falling_aged_df = get_aged_df(df, 'falling_delay_increase_%', ['rising_delay_increase_%', 'rising_delay'])

# store histograms
rising_ageing_list = rising_aged_df['rising_delay_increase_%']
rising_histogram_file = str(Path(store_path) / f'rising_{Path(file_name).with_suffix(".pdf")}')
plot_ageing_hist(rising_ageing_list, rising_histogram_file)

falling_ageing_list = falling_aged_df['falling_delay_increase_%']
falling_histogram_file = str(Path(store_path) / f'falling_{Path(file_name).with_suffix(".pdf")}')
plot_ageing_hist(falling_ageing_list, falling_histogram_file)

# Aged edges frequency
rising_aged_edge_freq_dict = get_edge_type_regex_freq_dict(rising_aged_df)
store_file = str(Path(store_path) / f'rising_aged_edges_{Path(file_name).with_suffix(".pdf")}')
plot_edge_type_bar(rising_aged_edge_freq_dict, store_file)

falling_aged_edge_freq_dict = get_edge_type_regex_freq_dict(falling_aged_df)
store_file = str(Path(store_path) / f'falling_aged_edges_{Path(file_name).with_suffix(".pdf")}')
plot_edge_type_bar(falling_aged_edge_freq_dict, store_file)

# Quantile
rising_max_10_percent_aged_df = filter_above_threshold(df, 0.1, column='rising_delay_increase_%')
falling_max_10_percent_aged_df = filter_above_threshold(df, 0.1, column='falling_delay_increase_%')

# 10 % Aged edges frequency
rising_max_10_percent_edge_freq_dict = get_edge_type_regex_freq_dict(rising_max_10_percent_aged_df)
store_file = str(Path(store_path) / f'rising_aged_edges_10_percent_{Path(file_name).with_suffix(".pdf")}')
plot_edge_type_bar(rising_max_10_percent_edge_freq_dict, store_file)

falling_max_10_percent_edge_freq_dict = get_edge_type_regex_freq_dict(falling_max_10_percent_aged_df)
store_file = str(Path(store_path) / f'falling_aged_edges_10_percent_{Path(file_name).with_suffix(".pdf")}')
plot_edge_type_bar(falling_max_10_percent_edge_freq_dict, store_file)

# store data frames
rising_file_name = f'rising_{file_name}'
util.store_data(store_path, rising_file_name, rising_aged_df)

falling_file_name = f'rising_{file_name}'
util.store_data(store_path, falling_file_name, falling_aged_df)
