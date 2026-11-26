# Magic batch DRC (full rule set, euclidean distances) + GDS + extraction of one cell.
# usage: CELL=<name> magic -dnull -noconsole -rcfile $PDK/libs.tech/magic/sky130A.magicrc drc.tcl
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
if {[info exists ::env(EXTRACT)]} {
    extract do local
    extract all
    ext2spice lvs
    ext2spice -o ${cell}.ext.spice
}
if {[info exists ::env(GDS)]} {
    gds write ${cell}.gds
}
quit -noprompt
