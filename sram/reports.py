"""Copy the reports behind the published numbers into reports/ (the working directories are not in git).

    python -m sram.reports
"""
import os
import shutil

from .paths import OUT, ROOT
from .report import FLOW_TAG

REP = os.path.join(ROOT, "reports")


def cp(src, dst):
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
        return True
    print("missing:", os.path.relpath(src, ROOT))
    return False


def run():
    run_dir = os.path.join(ROOT, "flow", "runs", FLOW_TAG)
    # array macro
    for f in ("sram_array_64x32.drc.rpt", "sram_array_64x32.lvs.rpt", "sram_array_64x32.klayout.lyrdb"):
        cp(os.path.join(OUT, "signoff", f), os.path.join(REP, "array", f))
    # complete memory: place-and-route flow
    cp(os.path.join(run_dir, "final", "metrics.json"), os.path.join(REP, "flow", "metrics.json"))
    for step, f in (("54-openroad-stapostpnr", "summary.rpt"), ("75-misc-reportmanufacturability", "manufacturability.rpt"),
                    ("69-netgen-lvs", os.path.join("reports", "lvs.netgen.rpt"))):
        cp(os.path.join(run_dir, step, f), os.path.join(REP, "flow", step.split("-", 1)[1] + "__" + os.path.basename(f)))
    for d in os.listdir(run_dir):
        if d.endswith("magic-drc") or d.endswith("klayout-drc") or d.endswith("openroad-checkantennas-1"):
            for root, _, files in os.walk(os.path.join(run_dir, d, "reports")):
                for f in files:
                    cp(os.path.join(root, f), os.path.join(REP, "flow", d.split("-", 1)[1] + "__" + f))
    if cp(os.path.join(run_dir, "resolved.json"), os.path.join(REP, "flow", "resolved_config.json")):
        f = os.path.join(REP, "flow", "resolved_config.json")       # keep the report free of machine-specific paths
        txt = open(f).read().replace(ROOT, "<repo>")
        open(f, "w").write(txt)
    # complete memory: independent transistor-level LVS
    cp(os.path.join(OUT, "chip", "sram_64x32.lvs.rpt"), os.path.join(REP, "chip", "sram_64x32.flat_lvs.rpt"))
    # simulation results
    for f in ("bitcell_sizing.json", "bitcell_corners.json", "bitcell_mc.json", "slice_corners.json", "chip_corners.json",
              "chip_period.json", "chip_interface.json", "chip_full_tt.json", "timing_summary.json", "results.json", "slice_static.json",
              "signoff_macro_summary.txt", "signoff_chip_summary.txt", "logic_sim.txt"):
        cp(os.path.join(OUT, f), os.path.join(REP, "sim", f))
    # integration example
    ex = os.path.join(ROOT, "example", "runs", "run1")
    if os.path.exists(ex):
        cp(os.path.join(ex, "final", "metrics.json"), os.path.join(REP, "example", "metrics.json"))
        for step in os.listdir(ex):
            if step.endswith("misc-reportmanufacturability"):
                cp(os.path.join(ex, step, "manufacturability.rpt"), os.path.join(REP, "example", "manufacturability.rpt"))
        cp(os.path.join(OUT, "example_summary.json"), os.path.join(REP, "example", "summary.json"))
    print(sum(len(f) for _, _, f in os.walk(REP)), "files in reports/")


if __name__ == "__main__":
    run()
