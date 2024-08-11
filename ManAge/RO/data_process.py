import os, sys
import re

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sn
from pathlib import Path

from processing.plot import axis_setting, plot_settings
from constraint.FASM import read_FASM
from xil_res.node import Node as nd
import utility.config as cfg
import utility.utility_functions as util

def plot_temp_current(temp_file, curr_file, temp_label, curr_label, time_label, output_file, threshold=0.001):
    # Load data from CSV files
    df_temperature = pd.read_csv(temp_file)
    df_current = pd.read_csv(curr_file)

    # Convert absolute time to relative
    df_temperature, df_current = convert_time(df_temperature, df_current, time_label)

    # Filter negative points
    df_temperature, df_current = remove_negative_points(df_temperature, df_current, temp_label, curr_label, 'relative_time', threshold)

    # Plotting the data
    fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    # Plot current
    plot_settings['lines.marker'] = ''
    axis_setting(ax[0], '', 'Current (A)')
    ax[0].plot(df_current['relative_time'], df_current[curr_label], color='#0097A7')

    # Plot temperature
    axis_setting(ax[1], 'Time (s)', 'Temperature (°C)')
    ax[1].plot(df_temperature['relative_time'], df_temperature[temp_label], color='#F50057')

    plt.savefig(output_file, bbox_inches='tight')

def convert_time(df_temperature, df_current, time_label):
    # Convert current_time to datetime
    df_temperature[time_label] = pd.to_datetime(df_temperature[time_label], format='%H:%M:%S')
    df_current[time_label] = pd.to_datetime(df_current[time_label], format='%H:%M:%S')

    # Find the earliest time across both files
    start_time = min(df_temperature[time_label].min(), df_current[time_label].min())

    # Convert times to relative time (in seconds)
    df_temperature['relative_time'] = (df_temperature[time_label] - start_time).dt.total_seconds()
    df_current['relative_time'] = (df_current[time_label] - start_time).dt.total_seconds()

    return df_temperature, df_current

def remove_negative_points(df_temperature, df_current, temp_label, curr_label, relative_time_label, threshold):
    # Find the first occurrence of a negative temperature
    first_negative_temp_index = df_temperature[df_temperature[temp_label] < 0].index.min()

    if first_negative_temp_index is not np.nan:
        # Get the corresponding time when temperature first falls below 0
        stop_time = df_temperature.loc[first_negative_temp_index,relative_time_label]

        # Filter temperature data to include only data before the stop_time
        df_temperature = df_temperature[df_temperature[relative_time_label] < stop_time]

        # Filter current data to include only data before the stop_time
        df_current = df_current[df_current[relative_time_label] < stop_time]

        # Identify the maximum current value after the stop_time
        max_current_value = df_current[curr_label].max()
        max_current_index = df_current[df_current[curr_label] == max_current_value].index.max()

        # Continue to include current data up to the point where the difference exceeds the threshold
        for i in range(max_current_index, len(df_current)):
            if max_current_value - df_current.iloc[i][curr_label] > threshold:
                df_current = df_current.iloc[:i]
                break

    return df_temperature, df_current

def extract_CLBs(fasm_file):
    CLBs = set()
    fasm_list = read_FASM(fasm_file)
    for entry in fasm_list:
        CLBs.update(re.findall('(CLE.*X\d+Y\d+)', entry))

    return CLBs

def get_curr_max_min(df_current, curr_label):
    curr_max = df_current[curr_label].max()
    curr_min = df_current.iloc[5][curr_label]

    return curr_max, curr_min

def get_temp_max_min(df_temperature, temp_label):
    temp_min = df_temperature.iloc[0][temp_label]
    temp_max = df_temperature.iloc[-1][temp_label]

    return temp_max, temp_min

def get_delta_power(curr_max, curr_min, voltage=12):
    return (curr_max - curr_min) * voltage

def get_RO_dict(temp_file, curr_file, temp_label, curr_label, time_label, fasm_file):
    RO_dict = {}
    # Load data from CSV files
    df_temperature = pd.read_csv(temp_file)
    df_current = pd.read_csv(curr_file)

    # Convert absolute time to relative
    df_temperature, df_current = convert_time(df_temperature, df_current, time_label)

    # Filter negative points
    df_temperature, df_current = remove_negative_points(df_temperature, df_current, temp_label, curr_label, 'relative_time', threshold=0.001)

    temp_max, temp_min = get_temp_max_min(df_temperature, temp_label)
    curr_max, curr_min = get_curr_max_min(df_current, curr_label)
    delta_power = get_delta_power(curr_max, curr_min)
    clbs = extract_CLBs(fasm_file)
    RO_dict['temp_max'] = temp_max
    RO_dict['temp_min'] = temp_min
    RO_dict['curr_max'] = curr_max
    RO_dict['curr_min'] = curr_min
    RO_dict['delta_power'] = delta_power
    RO_dict['power_per_coord'] = delta_power / len({nd.get_coordinate(clb) for clb in clbs})
    RO_dict['clbs'] = clbs
    RO_dict['n_clbs'] = len(clbs)

    return RO_dict

def analysis(temp_file, curr_file, fasm_file, df_file):
    df_dir, df_file_name = str(Path(df_file).parent), Path(df_file).name

    if Path(df_file).exists():

        df = util.load_data(df_dir, df_file_name)
    else:
        columns = ['design', 'temp_max', 'temp_min', 'curr_max', 'curr_min', 'delta_power', 'power_per_coord', 'clbs',
                   'n_clbs']
        df = pd.DataFrame(columns=columns)

    RO_dict = {'design': Path(fasm_file).stem}
    RO_dict |= get_RO_dict(temp_file, curr_file, cfg.temp_label, cfg.curr_label, cfg.time_label, fasm_file)

    # Check if the design already exists in the DataFrame
    if RO_dict['design'] in df['design'].values:
        # Create a DataFrame from RO_dict
        new_row_df = pd.DataFrame([RO_dict])

        # Ensure column order matches
        new_row_df = new_row_df.reindex(columns=df.columns)

        df.loc[df['design'] == RO_dict['design'], :] = new_row_df.values[0]
    else:
        # Append the new row
        df.loc[len(df)] = RO_dict

    df = df.sort_values(by='power_per_coord', ascending=False)
    util.store_data(df_dir, df_file_name, df)
