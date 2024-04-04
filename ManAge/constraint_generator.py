import os, re, sys
from xil_res.architecture import Arch
from constraint.configuration import ConstConfig
import constraint.CUTs_VHDL_template  as tmpl
from constraint.net import Net
import utility.config as cfg
import utility.utility_functions as util

if __name__ == '__main__':
    # user input
    device_name = sys.argv[1]

    # create the vivado sources folder
    util.create_folder(cfg.vivado_res_path)

    # load the device
    device = Arch(device_name)

    iteration = sorted(os.listdir(cfg.config_path), key=lambda x: int(re.findall('\d+', x)[0]))[-1]
    config_path = os.path.join(cfg.config_path, iteration)
    configuration_files = list(filter(lambda x: x.startswith('TC'), os.listdir(config_path)))

    for clock_region in device.CRs:

        # create the subfolder
        clock_region_path = os.path.join(cfg.vivado_res_path, clock_region.name)
        util.create_folder(clock_region_path)

        for file in configuration_files:

            # load cong=figuration
            TC_idx = file.split('.')[0]
            TC = util.load_data(config_path, file)
            CUTs = filter(lambda x: x.origin in clock_region.tiles, TC.D_CUTs)
            CUTs = sorted(CUTs, key=lambda x: (x.index, x.get_x_coord(), x.get_y_coord()))

            # create a configuration for constraints
            N_CUTs = len(CUTs)
            configuration = ConstConfig(N_CUTs)

            # populate the configuration
            for idx, cut in enumerate(CUTs):

                # CUT stats
                CUT_idx = idx % cfg.N_Parallel
                Seg_idx = idx // cfg.N_Parallel
                w_Error_Mux_In = f'w_Error({Seg_idx})({CUT_idx})'

                # fill nets
                configuration.fill_nets(cut, idx)

                # fill cells
                configuration.fill_cells(device.site_dict, cut, idx)


                # VHDL instantiation
                g_buffer = Net.get_g_buffer(cut.G)
                VHDL_codes = tmpl.get_instantiation(idx, 'i_Clk_Launch', 'i_Clk_Sample', 'i_CE', 'i_CLR', w_Error_Mux_In, g_buffer)
                configuration.VHDL_file.add_components(''.join(VHDL_codes))

            # print constraints
            vivado_src_path = os.path.join(clock_region_path, TC_idx)
            util.create_folder(vivado_src_path)
            configuration.print_src_files(vivado_src_path)