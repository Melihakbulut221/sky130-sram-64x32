# Magic sign-off of the array macro: DRC, GDS, LEF abstract, LVS netlist, parasitic netlist.
set cell $::env(CELL)
crashbackups stop
drc off
load $cell
select top cell
expand
drc style drc(full)
drc euclidean on
drc check
drc catchup
set total 0
set f [open "${cell}.drc.rpt" w]
foreach {why boxes} [drc listall why] {
    puts $f "$why"
    foreach b $boxes {
        set c {}
        foreach v $b { lappend c [format %.3f [magic::i2u $v]] }
        puts $f "   $c"
        incr total
    }
}
puts $f "TOTAL $total"
close $f
puts "DRC_TOTAL $total"
gds write ${cell}.gds
lef write ${cell}.lef -hide
# netlist for LVS (devices only)
extract do local
extract all
ext2spice lvs
ext2spice -o ${cell}.lvs.spice
# netlist with parasitic capacitance for simulation
ext2spice cthresh 0.01
ext2spice rthresh infinite
ext2spice subcircuit top on
ext2spice hierarchy off
ext2spice scale off
ext2spice -o ${cell}.pex.spice
quit -noprompt
