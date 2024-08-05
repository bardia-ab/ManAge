import argparse
from tqdm import tqdm
from joblib import Parallel, delayed
from pathlib import Path
from RO.RO_Functions import design, cluster, gen_bitstream
from xil_res.architecture import Arch
import utility.config as cfg

# Create parser
parser = argparse.ArgumentParser(prog='RO_cluster', description='Design RO network')
subparser = parser.add_subparsers(title='subcommands', dest='subcommand')

# Create a parent parser
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument('device_name', choices=Arch.get_models(), help='Specify the fabric of the FPGA')

# Subcommand: design
parser_design = subparser.add_parser('design', parents=[parent_parser], help='Design RO nwteork for each type of coordinates')
parser_design.add_argument('output_fasm_dir', help='Path to the output FASM files directory')

parser_design.add_argument('-c', '--clk_pips_file', help='Specify the path to clock pips file. These pips are excluded from the design.')
parser_design.add_argument('-r', '--remove_pips_file', help='Specify the path to a pips file that must be excluded from the design.')

# Subcommand: cluster
parser_cluster = subparser.add_parser('cluster', parents=[parent_parser], help='Cluster the whole fabric into specified window size.')
parser_cluster.add_argument('input_fasm_dir', help='Path to the input FASM files directory')
parser_cluster.add_argument('size', type=int, nargs=2, help='Specify the size of the window (Width, Height)')
parser_cluster.add_argument('output_fasm_dir', help='Path to the output FASM files directory')

parser_cluster.add_argument('-f', '--filter', help='Specify the CLB tile whose encompassing window is desired')

# Subcommand: bitstream
parser_bitstream = subparser.add_parser('bitstream', parents=[parent_parser], help='Generate bitstreams for FASM files')
parser_bitstream.add_argument('input_fasm_dir', help='Path to the input FASM files directory')
parser_bitstream.add_argument('blank_bitstream_file', help='Path to the blank bitstream file')
parser_bitstream.add_argument('output_bitstream_dir', help='Path to the output bitstream files directory')


if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    # Device
    device = Arch(args.device_name, non_clb_tiles=True)

    if args.subcommand == 'design':
        # create folder
        Path(args.output_fasm_dir).mkdir(parents=True, exist_ok=True)

        design(args, device)

    elif args.subcommand == 'cluster':
        # create folder
        Path(args.output_fasm_dir).mkdir(parents=True, exist_ok=True)

        cluster(args, device)

    elif args.subcommand == 'bitstream':
        # create folder
        Path(args.output_bitstream_dir).mkdir(parents=True, exist_ok=True)

        # Create pbar
        fasm_files = list(Path(args.input_fasm_dir).glob('*.fasm'))
        pbar = tqdm(total=len(fasm_files))

        Parallel(n_jobs=cfg.n_jobs, require='sharedmem')(delayed(gen_bitstream)(cfg.pyteman_path, fasm_file, args.blank_bitstream_file, args.output_bitstream_dir, pbar) for fasm_file in fasm_files)

        
    else:
        parser.print_help()


