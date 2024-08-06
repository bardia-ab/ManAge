import argparse
from pathlib import Path
from tqdm import tqdm
from xil_res.architecture import Arch
from processing.data_process import *
from processing.plot import print_heatmap, plot_ageing_hist, plot_edge_type_bar

# create parser
parser = argparse.ArgumentParser(prog='analyze_char', description='Analyze the results from the timing characterization experiment')
subparser = parser.add_subparsers(title='subcommands', dest='subcommand')

# Create a parent parser
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument('device_name', choices=Arch.get_models(), help='Specify the fabric of the FPGA')

# Subcommand: fill
parser_design = subparser.add_parser('fill', parents=[parent_parser], help="Fill the list of CUTs' delays with measured delays from the timing characterization experiment")
parser_design.add_argument('conf_dir', help='Path to the clock region directory containing all configurations')
parser_design.add_argument('result_dir', help='Path to the clock region directory containing measured delays of all configurations')
parser_design.add_argument('output_file', help='Specify the path for storing the output CUTs list')

parser_design.add_argument('-s', '--skew_dir', help='Specify the path to clock skew directory')

# Subcommand: heatmap
parser_design = subparser.add_parser('heatmap', parents=[parent_parser], help="Draw the heatmap of measured delays")
parser_design.add_argument('input_file', help='Specify the path to the stored CUTs list file')
parser_design.add_argument('output_file', help='Specify the path for storing the output heatmap file')

parser_design.add_argument('-r', '--reference_file', help='Specify the path to the stored reference CUTs list file')
parser_design.add_argument('-s', '--figsize', type=int, nargs=2, default=(8, 6), help='Size of the Figure (Width, Height)')
parser_design.add_argument('-t', '--transition', choices=['both', 'rising', 'falling'], default='both', help='Specify the type of desired transition')

# Subcommand: compare
parser_design = subparser.add_parser('compare', parents=[parent_parser], help="compare the measured delays with the reference quantitatively")
parser_design.add_argument('reference_file', help='Specify the path to the stored reference CUTs list file')
parser_design.add_argument('input_file', help='Specify the path to the stored CUTs list file')
parser_design.add_argument('output_file', help='Specify the path for storing the output DataFrame file')

parser_design.add_argument('--histogram', action='store_true', help='Draw the histogram of measured degradation')
parser_design.add_argument('-e', '--aged_edges', choices=['pip', 'wire'], help='Type of aged edges for which the bar plot must be drawn')
parser_design.add_argument('-q', '--quantile', type=float, help='Draw bar plot for the specified quantile')

if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()
    print(args)

    # Device
    device = Arch(args.device_name, non_clb_tiles=True)

    if args.subcommand == 'fill':
        # create output dir
        output_dir = Path(args.output_file).parent
        output_file_name = Path(args.output_file).name
        output_dir.mkdir(parents=True, exist_ok=True)

        # retrieve valid TCs
        invalid_TCs = get_invalid_TCs(args.result_dir)
        valid_TC_results = list(filter(lambda x: x.stem not in invalid_TCs, Path(args.result_dir).glob('TC*')))

        # create pbar
        pbar = tqdm(total=len(valid_TC_results))

        # populate CUTs list
        cuts_list = CUTs_List([])

        cuts_list.CUTs = list(chain(*Parallel(n_jobs=cfg.n_jobs, require='sharedmem')(
            delayed(fill_cuts_list)(args.result_dir, args.conf_dir, TC, pbar, args.skew_dir) for TC in
            map(lambda x: x.stem, valid_TC_results))))

        # store CUTs list
        util.store_data(str(output_dir), output_file_name, cuts_list)

    elif args.subcommand == 'heatmap':
        if args.input_file == args.reference_file:
            print('Specified input and reference CUTs lists are the same!')
            exit()

        # create output dir
        output_dir = Path(args.output_file).parent
        output_file_name = Path(args.output_file).name
        output_dir.mkdir(parents=True, exist_ok=True)

        # load CUTs list
        cuts_list_path, cuts_list_file = str(Path(args.input_file).parent), Path(args.input_file).name
        cuts_list = util.load_data(cuts_list_path, cuts_list_file)

        # get rising & falling dicts
        avg_rising_dict, avg_falling_dict = cuts_list.get_delay_dicts()

        if args.reference_file is not None:
            # load reference cuts list
            ref_cuts_list_path = str(Path(args.reference_file).parent)
            ref_cuts_list_file = Path(args.reference_file).name
            ref_cuts_list = util.load_data(ref_cuts_list_path, ref_cuts_list_file)

            # get rising & falling dicts
            avg_ref_rising_dict, avg_ref_falling_dict = ref_cuts_list.get_delay_dicts()

            # build diff dictionaries
            avg_rising_dict = {coord: avg_rising_dict[coord] - avg_ref_rising_dict[coord] for coord in
                                    avg_rising_dict}
            avg_falling_dict = {coord: avg_falling_dict[coord] - avg_ref_falling_dict[coord] for coord in
                                     avg_falling_dict}

            # set diff prefix
            diff_prefix = 'diff_'
        else:
            diff_prefix = ''

        # get device coordinates
        coords = set(avg_rising_dict.keys())
        rows = {nd.get_y_coord(coord) for coord in coords}
        columns = {nd.get_x_coord(coord) for coord in coords}

        # draw falling heatmap
        if args.transition != 'rising':
            output_trans_file_name = f'{diff_prefix}falling_{output_file_name}'
            output_file = str(output_dir / output_trans_file_name)
            print_heatmap(avg_falling_dict, coords, rows, columns, output_file, palette='rocket', xlabel='FPGA Columns',
                          ylabel='FPGA Rows', figsize=args.figsize, apply_type=False)

        # draw rising heatmap
        if args.transition != 'falling':
            output_trans_file_name = f'{diff_prefix}rising_{output_file_name}'
            output_file = str(output_dir / output_trans_file_name)
            print_heatmap(avg_rising_dict, coords, rows, columns, output_file, palette='rocket', xlabel='FPGA Columns',
                          ylabel='FPGA Rows', figsize=args.figsize, apply_type=False)

    elif args.subcommand == 'compare':
        if args.input_file == args.reference_file:
            print('Specified input and reference CUTs lists are the same!')
            exit()

        # create output dir
        output_dir = Path(args.output_file).parent
        output_file_name = Path(args.output_file).name
        output_dir.mkdir(parents=True, exist_ok=True)

        # load CUTs list
        cuts_list_path, cuts_list_file = str(Path(args.input_file).parent), Path(args.input_file).name
        cuts_list = util.load_data(cuts_list_path, cuts_list_file)

        # load reference cuts list
        ref_cuts_list_path = str(Path(args.reference_file).parent)
        ref_cuts_list_file = Path(args.reference_file).name
        ref_cuts_list = util.load_data(ref_cuts_list_path, ref_cuts_list_file)

        # create DataFrames
        df = conv_cuts_list2df(cuts_list)
        ref_df = conv_cuts_list2df(ref_cuts_list)

        # Filter out uncommon rows
        ref_df, df = merge_df(ref_df, df)

        # Add the percentage increase for 'rising_delay' and 'falling_delay'
        df = add_incr_delay_columns(ref_df, df, 'rising_delay_increase_%', 'falling_delay_increase_%')

        # Filter Aged CUTs
        rising_aged_df = get_aged_df(df, 'rising_delay_increase_%', ['falling_delay_increase_%', 'falling_delay'])
        falling_aged_df = get_aged_df(df, 'falling_delay_increase_%', ['rising_delay_increase_%', 'rising_delay'])

        if args.histogram:
            # create sub-directory
            histogram_dir = output_dir / 'histogram'
            histogram_dir.mkdir(parents=True, exist_ok=True)

            # plot rising transition histograms
            rising_ageing_list = rising_aged_df['rising_delay_increase_%']
            rising_histogram_file = str(histogram_dir / f'rising_{Path(output_file_name).with_suffix(".pdf")}')
            plot_ageing_hist(rising_ageing_list, rising_histogram_file)

            # plot falling transition histograms
            falling_ageing_list = falling_aged_df['falling_delay_increase_%']
            falling_histogram_file = str(histogram_dir / f'falling_{Path(output_file_name).with_suffix(".pdf")}')
            plot_ageing_hist(falling_ageing_list, falling_histogram_file)

        if args.aged_edges:
            # create sub-directory
            barplot_dir = output_dir / 'barplot'
            barplot_dir.mkdir(parents=True, exist_ok=True)

            # get regex edge_type (key) and occurrence of that edge type (value) dictionary
            edge_type_freq_dict = get_edge_type_regex_freq_dict(df, args.aged_edges)

            # Aged edges frequency for rising transition
            rising_aged_edge_freq_dict = get_edge_type_regex_freq_dict(rising_aged_df, args.aged_edges)
            norm_rising_aged_edge_freq_dict = {k: v / edge_type_freq_dict[k] for k, v in rising_aged_edge_freq_dict.items()}
            store_file = str(barplot_dir / f'rising_aged_{args.aged_edges}_{Path(output_file_name).with_suffix(".pdf")}')
            plot_edge_type_bar(norm_rising_aged_edge_freq_dict, store_file)

            # Aged edges frequency for falling transition
            falling_aged_edge_freq_dict = get_edge_type_regex_freq_dict(falling_aged_df, args.aged_edges)
            norm_falling_aged_edge_freq_dict = {k: v / edge_type_freq_dict[k] for k, v in falling_aged_edge_freq_dict.items()}
            store_file = str(barplot_dir / f'falling_aged_{args.aged_edges}_{Path(output_file_name).with_suffix(".pdf")}')
            plot_edge_type_bar(norm_falling_aged_edge_freq_dict, store_file)

            if args.quantile:
                # create sub-directory
                quantile_dir = output_dir / 'quantile'
                quantile_dir.mkdir(parents=True, exist_ok=True)

                # filter DataFrame for specified quantile
                rising_max_quant_percent_aged_df = filter_above_threshold(df, args.quantile, column='rising_delay_increase_%')
                falling_max_quant_percent_aged_df = filter_above_threshold(df, args.quantile, column='falling_delay_increase_%')

                # Aged edges frequency
                rising_max_quant_percent_edge_freq_dict = get_edge_type_regex_freq_dict(rising_max_quant_percent_aged_df)
                norm_rising_max_quant_percent_edge_freq_dict = {k: v / edge_type_freq_dict[k] for k, v in
                                                        rising_max_quant_percent_edge_freq_dict.items()}
                store_file = str(quantile_dir / f'rising_aged_edges_{args.quantile * 100}_percent_{Path(output_file_name).with_suffix(".pdf")}')
                plot_edge_type_bar(norm_rising_max_quant_percent_edge_freq_dict, store_file)

                falling_max_quant_percent_edge_freq_dict = get_edge_type_regex_freq_dict(falling_max_quant_percent_aged_df)
                norm_falling_max_quant_percent_edge_freq_dict = {k: v / edge_type_freq_dict[k] for k, v in
                                                         falling_max_quant_percent_edge_freq_dict.items()}
                store_file = str(quantile_dir / f'falling_aged_edges_{args.quantile * 100}_percent_{Path(output_file_name).with_suffix(".pdf")}')
                plot_edge_type_bar(norm_falling_max_quant_percent_edge_freq_dict, store_file)

        # store data frames
        rising_file_name = f'rising_{output_file_name}'
        util.store_data(str(output_dir), rising_file_name, rising_aged_df)

        falling_file_name = f'falling_{output_file_name}'
        util.store_data(str(output_dir), falling_file_name, falling_aged_df)

        # store full data frame
        util.store_data(str(output_dir), output_file_name, df)