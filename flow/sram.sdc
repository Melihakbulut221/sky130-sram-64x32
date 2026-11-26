# Timing constraints for the periphery of sram_64x32.
create_clock -name clk -period $::env(CLOCK_PERIOD) [get_ports clk]
set_clock_uncertainty 0.25 [get_clocks clk]
set_clock_transition 0.15 [get_clocks clk]

set data_inputs [lsearch -inline -all -not -exact [all_inputs] [get_ports clk]]
set_input_delay  [expr {0.2 * $::env(CLOCK_PERIOD)}] -clock clk $data_inputs
set_output_delay [expr {0.2 * $::env(CLOCK_PERIOD)}] -clock clk [all_outputs]
set_driving_cell -lib_cell sky130_fd_sc_hd__inv_2 -pin Y [all_inputs]
set_load 0.033 [all_outputs]
set_timing_derate -early 0.95
set_timing_derate -late 1.05

# phi (the gated, inverted clock) is a clock for the hold latches and an enable for the word-line,
# write and read gates. Beyond those gates it is a level-sensitive control signal that reaches the
# bit lines, so the clock network must end there: the tools must not build clock trees on word
# lines or bit lines. The paths through the array are verified with SPICE instead.
set_sense -type clock -stop_propagation [get_pins {*keep_and/X *keep_rd/X *keep_te0/X *keep_te1/X}]
