"""Post-layout checks of the complete memory, independent of the place-and-route flow.

    python -m signoff.run_chip [run-tag]

1. Magic extracts the final GDS down to transistors (standard cells and array included).
2. Netgen compares that with the source: the final gate-level netlist + the standard-cell SPICE
   library + the schematic netlist of the array. No black boxes: the layout netlist is flat, and
   Netgen flattens the source to transistors as well. (A hierarchical comparison is ambiguous
   here, because 64 identical rows and 32 identical bit slices are interchangeable until the
   address decoder and the port names tell them apart.)
3. The flat netlist with parasitic capacitance is brought back for SPICE (out/chip/).
"""
import os
import shutil
import sys
import tempfile

from signoff import vm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOP = "sram_64x32"
PDK = "/pdkroot/sky130A"
SC = f"{PDK}/libs.ref/sky130_fd_sc_hd/spice"


def run(tag="run5"):
    final = os.path.join(ROOT, "flow", "runs", tag, "final")
    out = os.path.join(ROOT, "out", "chip")
    os.makedirs(out, exist_ok=True)
    lvs = [f"set layout [readnet spice {TOP}.lvs.spice]", "set source [readnet verilog /dev/null]"]
    for f in ("sky130_ef_sc_hd__decap_12", "sky130_ef_sc_hd__fill_12", "sky130_ef_sc_hd__fill_8", "sky130_ef_sc_hd__fill_4",
              "sky130_ef_sc_hd__fill_2", "sky130_fd_sc_hd"):
        lvs.append(f"readnet spice {SC}/{f}.spice $source")
    lvs += ["readnet spice sram_array_64x32.sch.spice $source", f"readnet verilog {TOP}.pnl.v $source",
            f'lvs "$layout {TOP}" "$source {TOP}" {PDK}/libs.tech/netgen/sky130A_setup.tcl {TOP}.lvs.rpt']
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(os.path.join(final, "gds", TOP + ".gds"), d)
        shutil.copy(os.path.join(final, "pnl", TOP + ".pnl.v"), d)
        shutil.copy(os.path.join(ROOT, "macro", "sram_array_64x32.sch.spice"), d)
        shutil.copy(os.path.join(HERE, "chip.tcl"), d)
        open(os.path.join(d, "lvs.tcl"), "w").write("\n".join(lvs) + "\n")
        vm.push(d, "chip", clean=True)
    print(vm.tool(f"TOP={TOP} magic -dnull -noconsole -rcfile {PDK}/libs.tech/magic/sky130A.magicrc chip.tcl > magic.log 2>&1; "
                  f"tail -3 magic.log; grep -c '^X' {TOP}.lvs.spice; ls -la {TOP}.pex.spice", "chip", timeout=7200)[-700:])
    print(vm.tool(f"netgen -batch source lvs.tcl > netgen.log 2>&1; tail -6 {TOP}.lvs.rpt; grep -n 'Number of devices' {TOP}.lvs.rpt | tail -1",
                  "chip", timeout=7200, check=False)[-900:])
    vm.pull("chip", out, [TOP + ".lvs.spice", TOP + ".pex.spice", TOP + ".lvs.rpt", "magic.log", "netgen.log"])


if __name__ == "__main__":
    run(*sys.argv[1:2])
