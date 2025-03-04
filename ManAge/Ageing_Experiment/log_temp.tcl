set temp_file [lindex $argv 0]

open_hw_manager
connect_hw_server -url localhost:3121 -quiet
current_hw_target [get_hw_targets *]
open_hw_target
current_hw_device [lindex [get_hw_devices] 0]
refresh_hw_device [lindex [get_hw_devices] 0]	-quiet
set temp [get_property TEMPERATURE [lindex [get_hw_sysmons] 0]]

if {[file exists $temp_file] != 1} {
    set file [open $temp_file a+]
    puts $file "Temperature,current_time,current_date"
    close $file
}

set i 0
set t1 [clock seconds]
while {1} {
	set file [open $temp_file a+]
	refresh_hw_device [lindex [get_hw_devices] 0] -quiet
	set temp [get_property TEMPERATURE [lindex [get_hw_sysmons] 0]]
	set i [expr $i + 1]
	set systemTime [clock seconds]
	puts $file "$temp,[clock format $systemTime -format %H:%M:%S],[clock format [clock seconds] -format "%Y-%m-%d"]"
	after 1000
	close $file

}
