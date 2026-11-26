"""Assemble the deliverable views of the hard macro in release/.

    python -m sram.release [run-tag]

    sram_64x32.gds / .lef            layout and abstract, from the place-and-route run
    sram_64x32.nl.v / .pnl.v         final gate-level netlists (without / with power pins)
    sram_64x32.lvs.spice             flat transistor netlist extracted from the layout
    sram_64x32.pex.spice             the same with parasitic capacitance (for SPICE)
    sram_64x32__<corner>.lib         Liberty timing models
    sram_64x32__<corner>.sdf         delays of the periphery (from static timing analysis)
    sram_64x32.v / .bb.v             behavioural model and black box (written by hand, not copied here)

Liberty: input capacitance, setup and hold come from static timing analysis of the periphery
(OpenSTA on the routed design with extracted RC); 0.1 ns is added to every setup and hold time,
and post-layout SPICE confirms the result with all inputs switching at exactly those limits. The clock-to-output arc cannot come from there,
because it runs through the bit lines of the array; it is replaced by the value measured in
post-layout SPICE at the same corner. The table keeps the load dependence of the output buffer
that the timing analysis reports and is shifted to match SPICE at the simulated load.
"""
import json
import os
import re
import shutil
import sys

from .paths import OUT, ROOT

TOP = "sram_64x32"
REL = os.path.join(ROOT, "release")
CORNERS = {"tt": ("nom_tt_025C_1v80", "tt_025C_1v80"), "ss": ("nom_ss_100C_1v60", "ss_100C_1v60"), "ff": ("nom_ff_n40C_1v95", "ff_n40C_1v95")}
C_SIM = 0.030          # load on dout in the SPICE runs (pF)
MARGIN = 1.25          # guard band on the minimum clock period measured in SPICE
GUARD = 0.10           # ns added to every setup and hold time from static timing analysis


def _interp(xs, ys, x):
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])
    raise ValueError(x)


def patch_lib(text, t_cq, t_min_period, die_area, vdd, note):
    """Replace the clk -> dout arcs of a flow-generated Liberty file by the SPICE value t_cq (ns)."""
    def fix_pin(m):
        blk = m.group(0)
        # drop the arc from the rising edge: dout only changes after the falling edge
        blk = re.sub(r"      timing\(\) \{\s*related_pin : \"clk\";\s*timing_type : rising_edge;.*?\n      \}\n", "", blk, flags=re.S)

        def fix_table(tm):
            idx = [float(v) for v in re.search(r'index_1\("([^"]+)"\)', tm.group(0)).group(1).split(",")]
            vals = [float(v) for v in re.search(r'values\("([^"]+)"\)', tm.group(0)).group(1).split(",")]
            shift = t_cq - _interp(idx, vals, C_SIM)
            new = ",".join(f"{v + shift:.5f}" for v in vals)
            return re.sub(r'values\("[^"]+"\)', f'values("{new}")', tm.group(0))
        return re.sub(r"cell_(rise|fall)\(template_1\) \{.*?\}", fix_table, blk, flags=re.S)

    text, n = re.subn(r'    pin\("dout\[\d+\]"\) \{.*?\n    \}\n', fix_pin, text, flags=re.S)
    assert n == 32, n

    def guard(m):                      # setup / hold of the inputs: add the guard band
        return re.sub(r'values\("([-0-9.eE]+)"\)', lambda v: f'values("{float(v.group(1)) + GUARD:.5f}")', m.group(0))
    text, n = re.subn(r"timing_type : (?:setup|hold)_rising;.*?\n      \}", guard, text, flags=re.S)
    assert n == 2 * 44, n
    half = t_min_period / 2
    text = text.replace('''    pin("clk") {
      direction : input;
      clock : true;''', f'''    pin("clk") {{
      direction : input;
      clock : true;
      min_period : {t_min_period:.3f};
      min_pulse_width_high : {half:.3f};
      min_pulse_width_low : {half:.3f};''')
    text = re.sub(r"area : [0-9.]+ *\n", f"area : {die_area:.1f};\n    dont_touch : true;\n    dont_use : true;\n"
                  f"    pg_pin(\"VPWR\") {{ voltage_name : VPWR; pg_type : primary_power; }}\n"
                  f"    pg_pin(\"VGND\") {{ voltage_name : VGND; pg_type : primary_ground; }}\n", text, count=1)
    text = text.replace('  comment                        : "";', f'  comment                        : "{note}";')
    text = text.replace("  nom_process ", f"  voltage_map (VPWR, {vdd});\n  voltage_map (VGND, 0.0);\n  nom_process ", 1)
    return text


def run(tag="run5"):
    final = os.path.join(ROOT, "flow", "runs", tag, "final")
    os.makedirs(REL, exist_ok=True)
    shutil.copy(os.path.join(final, "gds", TOP + ".gds"), REL)
    shutil.copy(os.path.join(final, "lef", TOP + ".lef"), REL)
    shutil.copy(os.path.join(final, "nl", TOP + ".nl.v"), REL)
    shutil.copy(os.path.join(final, "pnl", TOP + ".pnl.v"), REL)
    for ext in (".lvs.spice", ".pex.spice"):
        shutil.copy(os.path.join(OUT, "chip", TOP + ext), REL)
    metrics = json.load(open(os.path.join(final, "metrics.json")))
    corners = {r["corner"]: r for r in json.load(open(os.path.join(OUT, "chip_corners.json")))}
    pp = os.path.join(OUT, "chip_period.json")
    period = (json.load(open(pp)) if os.path.exists(pp) else []) + list(corners.values())     # every run with a known period
    summary = {}
    for c, (flow_name, short) in CORNERS.items():
        r = corners[c]
        assert r["ok"], f"post-layout simulation failed at {c}"
        passing = [p["T"] for p in period if p["corner"] == c and p["ok"]]
        t_min = min(passing) * 1e9
        t_cq = (r["t_cq_min"] if c == "ff" else r["t_cq_max"]) * 1e9
        spec = round(t_min * MARGIN + 0.049, 1)
        text = open(os.path.join(final, "lib", flow_name, f"{TOP}__{flow_name}.lib")).read()
        note = (f"sram_64x32, corner {short}. Inputs: OpenSTA on the routed periphery plus {GUARD} ns guard band. clk falling to dout: post-layout SPICE "
                f"({'minimum' if c == 'ff' else 'maximum'} over all bits, {C_SIM * 1e3:.0f} fF load). "
                f"min_period = {MARGIN} x the shortest period that passed in SPICE ({t_min:g} ns).")
        open(os.path.join(REL, f"{TOP}__{short}.lib"), "w").write(
            patch_lib(text, t_cq, spec, metrics["design__die__area"], r["vdd"], note))
        shutil.copy(os.path.join(final, "sdf", flow_name, f"{TOP}__{flow_name}.sdf"), os.path.join(REL, f"{TOP}__{short}.sdf"))
        summary[c] = dict(temp=r["temp"], vdd=r["vdd"], t_cq_max=r["t_cq_max"] * 1e9, t_cq_min=r["t_cq_min"] * 1e9,
                          t_min_period_sim=t_min, min_period_spec=spec, i_avg_mA=r["i_avg"] * 1e3)
        print(c, summary[c])
    json.dump(summary, open(os.path.join(OUT, "timing_summary.json"), "w"), indent=1)
    print(sorted(os.listdir(REL)))


if __name__ == "__main__":
    run(*sys.argv[1:2])
