proc gen_bit {Proj_Dir Vivado_Sources_Dir Data_Dir CR TC_Name N_Parallel} {
	set CUTs "$Vivado_Sources_Dir/$TC_Name/CUTs.vhd"
	set constraint "$Vivado_Sources_Dir/$TC_Name/physical_constraints.xdc"
	set stats "$Vivado_Sources_Dir/$TC_Name/stats.txt"
	set Proj_Name [get_proj_name $Proj_Dir]
	set bd_file "$Proj_Dir/$Proj_Name\.srcs/sources_1/bd/design_1/design_1.bd"
	set bitstream_file "$Data_Dir/Bitstreams/$CR/$TC_Name\.bit"
	set DCP_file "$Data_Dir/DCPs/$CR/$TC_Name\.dcp"

	# delete previous implementation
	catch {reset_run synth_1}
	catch {reset_run impl_1}
	delete_runs synth_1

	# replace CUTs
	replace_VHDL_src $CUTs
	set_property file_type {VHDL 2008} [get_files $CUTs]
	
	# replace physical_constraints
	replace_constraints $constraint
	set_property used_in_synthesis false [get_files "$constraint"]

	# update compile order
	update_compile_order -fileset sources_1
	update_module_reference design_1_top_0_0

	# replace new N_Segments & N_Partial
	open_bd_design "$bd_file"
	lassign [get_segmentation "$stats"] N_Segments N_Partial
	set_property -dict [list CONFIG.g_N_Parallel $N_Parallel CONFIG.g_N_Segments $N_Segments CONFIG.g_N_Partial $N_Partial] [get_bd_cells top_0]

	# validate board design
	save_bd_design
	validate_bd_design

	# implement design
	catch {launch_runs impl_1 -jobs 12}
	catch {wait_on_run impl_1}

	# disable version check
	set_param xicom.use_bitstream_version_check false
	
	# store bitstream & DCP
	open_run impl_1
	set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
	write_bitstream -force $bitstream_file
	write_checkpoint -force $DCP_file

}

proc get_proj_name {Proj_Dir} {
	set Proj_File [glob -dir $Proj_Dir *.xpr]
	set Proj_Name [lindex [split [lindex [split $Proj_File /] end] .] 0]

	return $Proj_Name
}

proc replace_VHDL_src {current_src} {
	set src_name [lindex [split $current_src /] end]
	set prev_src [get_files $src_name]
	if {[llength $prev_src] > 0} {
		remove_files  -fileset sources_1 "$prev_src"
	}
	add_files -fileset sources_1 -norecurse $current_src
}

proc replace_constraints {current_constraint} {
	set const_name [lindex [split $current_constraint /] end]
	set prev_constraint [get_files $const_name]
	if {[llength $prev_constraint] > 0} {
		remove_files  -fileset constrs_1 "$prev_constraint"
	}
	add_files -fileset constrs_1 -norecurse "$current_constraint"
}

proc get_segmentation {stats} {
	set file [open "$stats" r]
	set lines [read "$file"]
	regexp {(\d+).* (\d+)} $lines match N_Segments N_Partial
	
	return [list $N_Segments $N_Partial]
}

# user inputs
set Vivado_Sources_Dir [lindex $argv 0]
set Proj_Dir [lindex $argv 1]
set Data_Dir [lindex $argv 2]
set CR [lindex $argv 3]
set TC_Start_Idx [lindex $argv 4]
set N_TCs [lindex $argv 5]
set N_Parallel [lindex $argv 6]
set Even_Odd_Opt [lindex $argv 7]

set Proj_Name [get_proj_name $Proj_Dir]
set logfile "$Proj_Dir/$Proj_Name\.runs/impl_1/runme.log"

# open project
open_project "$Proj_Dir/$Proj_Name\.xpr"

# change severity of critical warnings to error
set_msg_config -severity {CRITICAL WARNING} -new_severity ERROR


if {$Even_Odd_Opt == {even}} {
	set Even_Odd_TC_Files [glob -dir $Src_Dir *even]
	lappend Even_Odd_TC_Files {*}[glob -dir $Src_Dir *odd]
	set Even_Odd_TC_Files [lsort $Even_Odd_TC_Files]

	foreach TC_even_odd $Even_Odd_TC_Files {
		set TC_Name [lindex [split $TC_even_odd "/"] end]
		set logfile_dest "$Store_path/Logs/$CR/$TC_Name\.log"

		catch {gen_bit $Proj_Dir $Src_Dir $Store_path $CR $TC_Name $N_Parallel}
		catch {file copy $logfile $logfile_dest}
	}
} elseif {$Even_Odd_Opt == {custom}} {
	set TCs [glob -dir $Src_Dir *]
	set TCs [lsort $TCs]
	
	foreach TC $TCs {
		set TC_Name [lindex [split $TC "/"] end]
		set logfile_dest "$Store_path/Logs/$CR/$TC_Name\.log"

		catch {gen_bit $Proj_Dir $Src_Dir $Store_path $CR $TC_Name $N_Parallel}
		catch {file copy $logfile $logfile_dest}
	}
} else {
	for {set i $TC_Start_Idx} {$i < $N_TCs} {incr i} {
		set TC_Name "TC$i"
		set logfile_dest "$Data_Dir/Logs/$CR/$TC_Name\.log"

		catch {gen_bit $Proj_Dir $Vivado_Sources_Dir $Data_Dir $CR $TC_Name $N_Parallel}
		catch {file copy $logfile $logfile_dest}
	}
}