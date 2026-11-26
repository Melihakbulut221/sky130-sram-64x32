"""Write a cell (and its children) as .mag, run Magic DRC in the container, print the violations.

    python -m signoff.run_drc bitcell [extract] [gds]
"""
import os
import sys
import tempfile

from signoff import vm
from sram import cells

HERE = os.path.dirname(os.path.abspath(__file__))
MAGICRC = "/pdkroot/sky130A/libs.tech/magic/sky130A.magicrc"


def drc(cell, extract=False, gds=False, sub="mag", quiet=False, timeout=3600):
    with tempfile.TemporaryDirectory() as d:
        cell.write(d)
        for f in ("drc.tcl",):
            open(os.path.join(d, f), "w").write(open(os.path.join(HERE, f)).read())
        vm.push(d, sub)
    env = f"CELL={cell.name} " + ("EXTRACT=1 " if extract else "") + ("GDS=1 " if gds else "")
    log = vm.tool(f"{env} magic -dnull -noconsole -rcfile {MAGICRC} drc.tcl 2>&1 | tail -40", sub, timeout=timeout)
    out = os.path.join(os.path.dirname(HERE), "out", "signoff")
    pats = [cell.name + ".drc.rpt"] + ([cell.name + ".ext.spice"] if extract else []) + ([cell.name + ".gds"] if gds else [])
    vm.pull(sub, out, pats)
    rpt = open(os.path.join(out, cell.name + ".drc.rpt")).read()
    if not quiet:
        print(log[-1500:])
        print(rpt[:6000])
    return int(rpt.strip().splitlines()[-1].split()[1]), rpt


if __name__ == "__main__":
    c = getattr(cells, sys.argv[1])()
    n, _ = drc(c, "extract" in sys.argv, "gds" in sys.argv)
    if "extract" in sys.argv:
        print(open(os.path.join(os.path.dirname(HERE), "out", "signoff", c.name + ".ext.spice")).read()[:3000])
