import os, re, sys
import scripts.utility_functions as util
import scripts.config as cfg

if __name__ == '__main__':
    # create required directories
    bitstream_path = os.path.join(cfg.Data_path, 'Bitstreams')
    DCP_path = os.path.join(cfg.Data_path, 'DCPs')
    log_path = os.path.join(cfg.Data_path, 'Logs')

    util.create_folder(bitstream_path)
    util.create_folder(DCP_path)
    util.create_folder(log_path)

    # retrieve CRs
    CRs = os.listdir(cfg.vivado_res_path)
    CRs.sort()

    for cr in CRs:
        # create CR sub-directories
        CR_dir = os.path.join(cfg.vivado_res_path, cr)
        util.create_folder(os.path.join(bitstream_path, cr))
        util.create_folder(os.path.join(DCP_path, cr))
        util.create_folder(os.path.join(log_path, cr))

        # arguments
        start_index, N_TCs = 0, len(os.listdir(CR_dir))
        tcl_path = os.path.join('tcl', 'generate_bitstream.tcl')

        command = 'vivado -mode batch -nolog -nojournal -source {} -tclargs "{}" "{}" "{}" "{}" "{}" "{}" "{}" "{}"'
        command.format(tcl_path, CR_dir, cfg.vivado_project_path, cfg.Data_path, cr, start_index, N_TCs, cfg.N_Parallel, 'None')
        os.system(command)
