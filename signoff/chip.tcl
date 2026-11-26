# Full-chip extraction from the final GDS: everything down to transistors (standard cells and
# the array macro are read from the GDS, nothing is black-boxed).
#   <top>.lvs.spice  flat device netlist for LVS
#   <top>.pex.spice  flat netlist with parasitic capacitance for SPICE
set top $::env(TOP)
crashbackups stop
drc off
gds read ${top}.gds
load $top
select top cell
extract do local
extract all
ext2spice lvs
ext2spice hierarchy off
ext2spice subcircuit top on
ext2spice -o ${top}.lvs.spice
ext2spice cthresh 0.02
ext2spice rthresh infinite
ext2spice subcircuit top on
ext2spice hierarchy off
ext2spice scale off
ext2spice -o ${top}.pex.spice
quit -noprompt
