import seaborn as sns
import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt
from xil_res.node import Node as nd

def print_heatmap_tiles_map(input_dict, store_path=None, filename=None, palette='colorblind', xlabel='FPGA Rows', ylabel='FPGA Columns'):
    # extract types and all_coords
    all_coords = get_all_coords(input_dict)

    # crate rows and columns indices
    rows = get_full_range_rows(all_coords)
    columns = get_full_range_columns(all_coords)

    # create the reversed dict => {coord: type, }
    reversed_input_dict = {coord: type for type, coords in input_dict.items() for coord in coords}

    # print heatmap
    store_file = os.path.join(store_path, filename)
    print_heatmap(reversed_input_dict, all_coords, rows, columns, store_file, palette, xlabel, ylabel)

def print_heatmap_wires_dict(input_dict, store_path=None, filename=None, palette='pastel', xlabel='FPGA Rows', ylabel='FPGA Columns'):
    # extract types and all_coords
    all_coords = {nd.get_coordinate(tile) for type, tiles in input_dict.items() for tile in tiles}

    # crate rows and columns indices
    rows = get_full_range_rows(all_coords)
    columns = get_full_range_columns(all_coords)

    # create the reversed dict => {coord: type, }
    reversed_input_dict = {nd.get_coordinate(tile): type for type, tiles in input_dict.items() for tile in tiles}

    # print heatmap
    store_file = os.path.join(store_path, filename)
    print_heatmap(reversed_input_dict, all_coords, rows, columns, store_file, palette, xlabel, ylabel, remove_cbar=True)

def print_heatmap(input_dict, all_coords, rows, columns, store_file, palette, xlabel, ylabel, apply_type=True, remove_cbar=False):
    types = list(set(input_dict.values()))

    # Create the data matrix (assuming get_data_matrix is defined correctly)
    data = get_data_matrix(input_dict, all_coords, apply_type)

    # Create DataFrame
    df = pd.DataFrame(data, index=list(rows), columns=list(columns))

    # Reverses the y-axis, the origin is in bottom-left
    df = df.iloc[::-1, :]

    # Create the mask for NaN values
    mask = np.isnan(df)

    # Custom palette
    custom_palette = sns.color_palette(palette, len(types))

    # Plot
    plt.figure(figsize=(8, 6))
    ax = sns.heatmap(df, mask=mask, cmap=custom_palette)
    ax.set(xlabel=xlabel, ylabel=ylabel)

    # Setting xticks and yticks based on maximum number allowed
    x_indices, x_labels = get_ticks_for_axis(len(columns))
    ax.set_xticks(x_indices)
    ax.set_xticklabels([list(columns)[i] for i in x_indices], rotation=0)  # Adjust rotation if necessary

    y_indices, y_labels = get_ticks_for_axis(len(rows))
    ax.set_yticks(y_indices)
    ax.set_yticklabels([list(rows)[::-1][i] for i in y_indices], rotation=0)

    # Customize color bar
    if not remove_cbar and apply_type:
        cbar = ax.collections[0].colorbar
        cbar.set_ticks(np.linspace(0, len(types) - 1, len(types)))
        cbar.set_ticklabels(types)

    if remove_cbar:
        print(f'Number of Types: {len(types)}')

    # Display or save the plot
    if store_file is None:
        plt.show()
    else:
        plt.savefig(store_file, bbox_inches='tight')

    # Clear the plot
    plt.clf()

def get_ticks_for_axis(length, max_ticks=30):
    # Function to select ticks for an axis based on the maximum number allowed

    if length <= max_ticks:
        return np.arange(length), [str(i) for i in range(1, length + 1)]
    else:
        step = length // max_ticks
        selected_indices = np.arange(0, length, step)
        return selected_indices, [str(i + 1) for i in selected_indices]

def get_all_coords(input_dict):
    return {coord for type, coords in input_dict.items() for coord in coords}

def get_full_range_rows(coords):
    rows = {nd.get_y_coord(coord) for coord in coords}
    return list(range(min(rows), max(rows) + 1))

def get_full_range_columns(coords):
    columns = {nd.get_x_coord(coord) for coord in coords}
    return list(range(min(columns), max(columns) + 1))

def get_data_matrix(input_dict, all_coords, apply_type=True):
    rows = {nd.get_y_coord(coord) for coord in all_coords}
    columns = {nd.get_x_coord(coord) for coord in all_coords}
    n_rows, n_columns = len(rows), len(columns)

    types = list(set(input_dict.values()))
    data = [[np.nan] * n_columns for _ in range(n_rows)]
    for coord in all_coords:
        row = nd.get_y_coord(coord) - min(rows)
        column = nd.get_x_coord(coord) - min(columns)
        if apply_type:
            type = input_dict[coord]
            try:
                data[row][column] = types.index(type)
            except:
                print(row, column, type)
                breakpoint()
        else:
            data[row][column] = input_dict[coord]

    return data

def plot_ageing_hist(ageing_list, store_file):
    # Plotting the histogram
    fig, ax = plt.subplots(figsize=(12, 8))  # Set the figure size (optional)
    counts, bins, patches = plt.hist(ageing_list, bins=10, color='#e38e34', alpha=1, edgecolor='grey')  # Create histogram

    # Set font and font size for annotations
    font_annot = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 15}

    # Add annotations on top of the bars
    for count, bin, patch in zip(counts, bins, patches):
        height = patch.get_height()  # Get the height of each bar
        plt.text(patch.get_x() + patch.get_width() / 2, height + 0.1, f'{int(count)}', ha='center', va='bottom', fontdict=font_annot)

    # Set font and font size for labels and title
    font = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 20}

    ax.set_xlabel('Degradation %', fontdict=font, labelpad=15)
    ax.set_ylabel('Frequency', fontdict=font, labelpad=15)
    # ax.set_title('Histogram with Customizations', fontdict=font)

    # Set font size for tick labels
    plt.xticks(fontsize=17, fontfamily='Arial')
    plt.yticks(fontsize=17, fontfamily='Arial')

    # Adjust space between ticks and tick labels
    ax.tick_params(axis='x', pad=10)  # Adjust the pad for x-axis ticks
    ax.tick_params(axis='y', pad=10)  # Adjust the pad for y-axis ticks

    # Activate grid and set grid line properties
    # ax.grid(True, which='both', axis='y', linestyle='--', linewidth=0.5, color='gray')

    # Set grid line colors and shapes for major and minor ticks
    ax.grid(which='major', axis='y', linestyle='--', linewidth=0.5, color='grey')
    # ax.grid(which='minor', axis='y', linestyle=':', linewidth=0.5, color='green')

    # Remove specific borders
    for dir in ['right', 'left', 'top', 'bottom']:
        ax.spines[dir].set_visible(False)

    plt.savefig(store_file, bbox_inches='tight')

    return bins

def plot_edge_type_bar(aged_edge_freq_dict, store_file):
    # sort dict
    aged_edge_freq_dict = dict(sorted(aged_edge_freq_dict.items(), key=lambda item: item[1], reverse=True))

    fig, ax = plt.subplots(figsize=(12, 8))

    # Extract keys and values
    names = [str(key) for key in aged_edge_freq_dict.keys()]
    frequencies = list(aged_edge_freq_dict.values())
    bars = plt.bar(names, frequencies, color='#006064', edgecolor='grey')

    # Set font and font size for labels and title
    font = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 20}

    ax.set_xlabel('Edge', fontdict=font, labelpad=15)
    ax.set_ylabel('Frequency', fontdict=font, labelpad=15)

    # Set font size for tick labels
    plt.xticks(fontsize=17, fontfamily='Arial', rotation=90)
    plt.yticks(fontsize=17, fontfamily='Arial')

    # Adjust space between ticks and tick labels
    ax.tick_params(axis='x', pad=10)  # Adjust the pad for x-axis ticks
    ax.tick_params(axis='y', pad=10)  # Adjust the pad for y-axis ticks

    # Set grid line colors and shapes for major and minor ticks
    ax.grid(which='major', axis='y', linestyle='--', linewidth=0.5, color='grey')
    # ax.grid(which='minor', axis='y', linestyle=':', linewidth=0.5, color='green')

    # Remove specific borders
    for dir in ['right', 'left', 'top', 'bottom']:
        ax.spines[dir].set_visible(False)

    # Set font and font size for annotations
    font_annot = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 15}

    # Annotate each bar with the frequency value
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval + 0.5, f'{yval}', ha='center', va='bottom', fontdict=font_annot, rotation=90)

    plt.savefig(store_file, bbox_inches='tight')