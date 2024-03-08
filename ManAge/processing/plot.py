import seaborn as sns
import numpy as np
import pandas, os
import matplotlib.pyplot as plt
from xil_res.node import Node as nd

def print_heatmap_tiles_map(input_dict, store_path=None, filename=None, palette='pastel', xlabel='FPGA Rows', ylabel='FPGA Columns'):
    # extract types and all_coords
    all_coords = get_all_coords(input_dict)

    # crate rows and columns indices
    rows = get_full_range_rows(all_coords)
    columns = get_full_range_columns(all_coords)

    # create the reversed dict => {coord: type, }
    reversed_input_dict = {coord: type for type, coords in input_dict.items() for coord in coords}

    # print heatmap
    print_heatmap(reversed_input_dict, all_coords, rows, columns, store_path, filename, palette, xlabel, ylabel)

def print_heatmap_wires_dict(input_dict, store_path=None, filename=None, palette='pastel', xlabel='FPGA Rows', ylabel='FPGA Columns'):
    # extract types and all_coords
    all_coords = {nd.get_coordinate(tile) for type, tiles in input_dict.items() for tile in tiles}

    # crate rows and columns indices
    rows = get_full_range_rows(all_coords)
    columns = get_full_range_columns(all_coords)

    # create the reversed dict => {coord: type, }
    reversed_input_dict = {nd.get_coordinate(tile): type for type, tiles in input_dict.items() for tile in tiles}

    # print heatmap
    print_heatmap(reversed_input_dict, all_coords, rows, columns, store_path, filename, palette, xlabel, ylabel)

def print_heatmap(input_dict, all_coords, rows, columns, store_path, filename, palette, xlabel, ylabel):
    n_rows, n_columns = len(rows), len(columns)
    types = list(set(input_dict.values()))

    # create the data matrix
    data = get_data_matrix(input_dict, all_coords, n_rows, n_columns)

    # create Data Frame
    df = pandas.DataFrame(data, index=rows, columns=columns)     # origin is in top-left

    # reverses the y-axis, the origin is in bottem-left
    df = df.iloc[::-1, :]

    # create the mask
    mask = np.isnan(df)

    # custom palette
    custom_palette = sns.color_palette(palette, len(types))

    # plot
    ax = sns.heatmap(df, mask=mask, cmap=custom_palette, cbar_kws={'ticks': list(range(len(types)))})
    ax.set(xlabel=xlabel, ylabel=ylabel)
    plt.xticks(rotation=0)
    plt.yticks(rotation=0)

    # Customize color bar
    cbar = ax.collections[0].colorbar
    cbar.set_ticks(list(range(len(types))))
    cbar.set_ticklabels(types)

    if any(map(lambda x: x is None, {store_path, filename})):
        plt.show()

    else:
        plt.savefig(os.path.join(store_path, filename))

    # clear the plot
    plt.clf()

def get_all_coords(input_dict):
    return {coord for type, coords in input_dict.items() for coord in coords}

def get_full_range_rows(coords):
    rows = {nd.get_y_coord(coord) for coord in coords}
    return list(range(min(rows), max(rows) + 1))

def get_full_range_columns(coords):
    columns = {nd.get_x_coord(coord) for coord in coords}
    return list(range(min(columns), max(columns) + 1))

def get_data_matrix(input_dict, all_coords, n_rows, n_columns):
    types = list(set(input_dict.values()))
    data = [[np.nan] * n_columns for _ in range(n_rows)]
    for coord in all_coords:
        row = nd.get_y_coord(coord) - 1
        column = nd.get_x_coord(coord) - 1
        type = input_dict[coord]
        data[row][column] = types.index(type)

    return data
