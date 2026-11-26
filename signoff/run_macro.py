"""Sign-off of the array macro: Magic DRC + GDS + LEF + extraction, Netgen LVS, KLayout DRC.

    python -m signoff.run_macro [test]
"""
import os
import re
import sys
import tempfile

from signoff import vm
from sram import cells, netlist

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out", "signoff")
PDK = "/pdkroot/sky130A"
MAGICRC = f"{PDK}/libs.tech/magic/sky130A.magicrc"


def run(c, klayout=True):
    name, sub = c.name, "macro_" + c.name
    with tempfile.TemporaryDirectory() as d:
        c.write(d)
        open(os.path.join(d, "macro.tcl"), "w").write(open(os.path.join(HERE, "macro.tcl")).read())
        open(os.path.join(d, name + ".sch.spice"), "w").write(netlist.array_subckt(c.rows, c.cols, name=name))
        vm.push(d, sub, clean=True)
    log = vm.tool(f"CELL={name} magic -dnull -noconsole -rcfile {MAGICRC} macro.tcl > magic.log 2>&1; tail -5 magic.log", sub, timeout=7200)
    print(log[-600:])
    lvs = vm.tool(f"netgen -batch lvs '{name}.lvs.spice {name}' '{name}.sch.spice {name}' "
                  f"{PDK}/libs.tech/netgen/sky130A_setup.tcl {name}.lvs.rpt > netgen.log 2>&1; tail -25 {name}.lvs.rpt", sub, timeout=7200)
    print(lvs[-1800:])
    pats = [name + e for e in (".drc.rpt", ".gds", ".lef", ".lvs.spice", ".pex.spice", ".lvs.rpt")] + ["magic.log", "netgen.log"]
    if klayout:
        k = vm.tool(f"klayout -b -r {PDK}/libs.tech/klayout/drc/sky130A_mr.drc -rd input={name}.gds -rd topcell={name} "
                    f"-rd report={name}.klayout.lyrdb -rd feol=true -rd beol=true -rd offgrid=true -rd seal=false "
                    f"-rd floating_met=false -rd thr=4 > klayout.log 2>&1; tail -4 klayout.log; "
                    f"grep -c '<item>' {name}.klayout.lyrdb", sub, timeout=7200, check=False)
        print(k[-800:])
        pats += [name + ".klayout.lyrdb", "klayout.log"]
    vm.pull(sub, OUT, pats)
    rpt = open(os.path.join(OUT, name + ".drc.rpt")).read()
    print("Magic DRC:", rpt.strip().splitlines()[-1])
    if klayout:
        db = open(os.path.join(OUT, name + ".klayout.lyrdb")).read()
        cats = re.findall(r"<category>'?([^<']+)'?</category>\s*<cell>", db)
        from collections import Counter
        print("KLayout DRC violations:", len(cats), dict(Counter(cats)))


if __name__ == "__main__":
    run(cells.macro_test() if "test" in sys.argv else cells.macro())
