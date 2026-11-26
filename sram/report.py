"""Collect every result into out/results.json and write docs/results.md.

    python -m sram.report

Nothing is computed here; the numbers are read from the reports and simulation outputs that the
other steps leave behind, so the documentation and the video quote the same values.
"""
import json
import os
import re

from .bitcell import CELL
from .paths import OUT, ROOT

FLOW_TAG = "run5"
REPO_URL = "https://github.com/Melihakbulut221/sky130-sram-64x32"


def _j(name):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else None


def collect():
    from . import cells
    g = cells.BitcellGeom()
    m = json.load(open(os.path.join(ROOT, "flow", "runs", FLOW_TAG, "final", "metrics.json")))
    cfg = json.load(open(os.path.join(ROOT, "flow", "config.json")))
    mac = cells.macro()
    r = dict(flow_tag=FLOW_TAG)
    r["cell"] = dict(wpd=CELL.wpd, wpg=CELL.wpg, wpu=CELL.wpu, l=CELL.lpd, pu="pfet_01v8_hvt" if CELL.pu == "ph" else "pfet_01v8")
    r["cell_w"], r["cell_h"] = g.W / 1000, g.H / 1000
    r["cell_area"] = r["cell_w"] * r["cell_h"]
    r["macro_w"], r["macro_h"] = mac.bbox[2] / 1000, mac.bbox[3] / 1000
    r["macro_origin"] = cfg["MACROS"]["sram_array_64x32"]["instances"]["u_array"]["location"]
    r["die_w"], r["die_h"] = cfg["DIE_AREA"][2], cfg["DIE_AREA"][3]
    r["array_mosfets"] = 64 * 32 * 6
    # sign-off of the array
    rpt = open(os.path.join(OUT, "signoff", "sram_array_64x32.lvs.rpt")).read()
    r["array_lvs"] = "match uniquely" in rpt
    r["array_lvs_devices"] = int(re.findall(r"Number of devices: (\d+)", rpt)[-1])
    r["array_lvs_nets"] = int(re.findall(r"Number of nets: (\d+)", rpt)[-1])
    r["array_magic_drc"] = int(open(os.path.join(OUT, "signoff", "sram_array_64x32.drc.rpt")).read().split()[-1])
    r["array_klayout_drc"] = open(os.path.join(OUT, "signoff", "sram_array_64x32.klayout.lyrdb")).read().count("<item>")
    # the complete memory
    rpt = open(os.path.join(OUT, "chip", "sram_64x32.lvs.rpt")).read()
    r["lvs"] = "Circuits match uniquely" in rpt
    r["lvs_devices"] = int(re.findall(r"Number of devices: (\d+)", rpt)[-1])
    r["lvs_nets"] = int(re.findall(r"Number of nets: (\d+)", rpt)[-1])
    pex = open(os.path.join(OUT, "chip", "sram_64x32.pex.spice")).read()
    r["extracted_mosfets"] = len(re.findall(r"^X", pex, re.M))
    r["decap_mosfets"] = len(re.findall(r"^X\S+ (?:VPWR|VGND) (?:VPWR|VGND) (?:VPWR|VGND) (?:VPWR|VGND) ", pex, re.M))
    r["mosfets"] = r["extracted_mosfets"] - r["decap_mosfets"]
    r["stdcells"] = int(m["design__instance__count__stdcell"]) - int(m["design__instance__count__class:tap_cell"])
    r["flow"] = {k: m[k] for k in (
        "magic__drc_error__count", "klayout__drc_error__count", "design__lvs_error__count", "antenna__violating__nets",
        "design__xor_difference__count", "route__drc_errors", "design__max_slew_violation__count", "design__max_cap_violation__count",
        "design__power_grid_violation__count", "timing__setup__wns", "timing__hold__wns", "ir__drop__worst", "route__wirelength",
        "design__instance__count__stdcell", "design__instance__utilization__stdcell", "power__total")}
    # bit cell
    bc = _j("bitcell_corners.json")
    mc = _j("bitcell_mc.json")
    if bc:
        tt = [x for x in bc if x["corner"] == "tt"][0]
        r["bitcell"] = dict(hold_tt=tt["hold"], read_tt=tt["read"], wm_tt=tt["wm_wl"], iread_tt=tt["iread"], leak_tt=tt["leak"],
                            read_worst=min(x["read"] for x in bc), hold_worst=min(x["hold"] for x in bc),
                            wm_worst=min(x["wm_wl"] for x in bc), iread_worst=min(x["iread"] for x in bc),
                            leak_worst=max(x["leak"] for x in bc))
        if mc:
            r["bitcell"]["read_mc_sigma"] = min(v["read"]["mean"] / v["read"]["sigma"] for v in mc.values())
            r["bitcell"]["wm_mc_sigma"] = min(v["wm_wl"]["mean"] / v["wm_wl"]["sigma"] for v in mc.values())
            r["bitcell"]["read_mc_min"] = min(v["read"]["min"] for v in mc.values())
            r["bitcell"]["wm_mc_min"] = min(v["wm_wl"]["min"] for v in mc.values())
            r["bitcell"]["mc_n"] = list(mc.values())[0]["read"]["n"]
    r["timing"] = _j("timing_summary.json")
    r["chip_corners"] = _j("chip_corners.json")
    r["chip_period"] = _j("chip_period.json")
    r["chip_full"] = _j("chip_full_tt.json")
    r["chip_interface"] = _j("chip_interface.json")
    # waveform window of the post-layout figure: write word 42, read word 21, read word 42 (20 ns clock)
    r["wave_t0"], r["wave_t1"] = 58, 124
    r["wave_rows"] = [["clk", [["clk", "MUTED"]]], ["word lines", [["wl21", "CYAN"], ["wl42", "YELLOW"]]],
                      ["bit lines", [["bl0", "PURPLE"], ["blb0", "ORANGE"]]],
                      ["cell", [["q_42_0", "YELLOW"], ["qb_42_0", "GREEN"]]],
                      ["dout", [["dout0", "BLUE"], ["dout1", "GREEN"]]]]
    r["wave_marks"] = [[60, "write word 42"], [80, "read word 21"], [100, "read word 42"]]
    json.dump(r, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    return r


def summaries(r):
    """Short terminal-style summaries of the sign-off logs (shown in the video and in the docs)."""
    a = [
        "$ python -m signoff.run_macro",
        "",
        "Magic 8.3   drc(full), euclidean          sram_array_64x32",
        f"    DRC_TOTAL {r['array_magic_drc']}",
        "",
        "KLayout     sky130A_mr.drc   feol beol offgrid",
        f"    violations: {r['array_klayout_drc']}",
        "",
        "Netgen 1.5  layout vs. schematic",
        f"    Number of devices: {r['array_lvs_devices']}   |   Number of devices: {r['array_lvs_devices']}",
        f"    Number of nets: {r['array_lvs_nets']}      |   Number of nets: {r['array_lvs_nets']}",
        "    Final result: Circuits match uniquely." if r["array_lvs"] else "    MISMATCH",
    ]
    open(os.path.join(OUT, "signoff_macro_summary.txt"), "w").write("\n".join(a) + "\n")
    f = r["flow"]
    c = [
        "$ flow/run.sh config.json        # LibreLane: Yosys, OpenROAD, Magic, KLayout, Netgen",
        "",
        f"    Magic DRC errors ............... {f['magic__drc_error__count']}",
        f"    KLayout DRC errors ............. {f['klayout__drc_error__count']}",
        f"    LVS errors (gate level) ........ {f['design__lvs_error__count']}",
        f"    Antenna violations ............. {f['antenna__violating__nets']}",
        f"    Magic / KLayout GDS XOR ........ {f['design__xor_difference__count']}",
        f"    Setup / hold violations ........ {0 if f['timing__setup__wns'] == 0 else 'yes'} / {0 if f['timing__hold__wns'] == 0 else 'yes'}",
        f"    Power-grid violations .......... {f['design__power_grid_violation__count']}",
        "",
        "$ python -m signoff.run_chip     # Magic extraction of the final GDS, flat; Netgen",
        "",
        f"    Number of devices: {r['lvs_devices']}   |   Number of devices: {r['lvs_devices']}",
        f"    Number of nets: {r['lvs_nets']}       |   Number of nets: {r['lvs_nets']}",
        "    Final result: Circuits match uniquely." if r["lvs"] else "    MISMATCH",
    ]
    open(os.path.join(OUT, "signoff_chip_summary.txt"), "w").write("\n".join(c) + "\n")


def markdown(r):
    b = r.get("bitcell", {})
    L = ["# Results", "",
         "Generated by `python -m sram.report` from the reports and simulation outputs. Simulation and sign-off only; no silicon.", ""]
    L += ["## Bit cell", "",
          f"Pull-down {r['cell']['wpd']:g}/{r['cell']['l']:g} µm, pass gate {r['cell']['wpg']:g}/{r['cell']['l']:g} µm (nfet_01v8), "
          f"pull-up {r['cell']['wpu']:g}/{r['cell']['l']:g} µm ({r['cell']['pu']}). Cell {r['cell_w']:.2f} × {r['cell_h']:.2f} µm = {r['cell_area']:.2f} µm².", ""]
    bc = _j("bitcell_corners.json")
    if bc:
        L += ["| corner | T (°C) | VDD (V) | hold SNM (mV) | read SNM (mV) | write margin (mV) | read current (µA) | leakage per cell (pA) |",
              "|---|---|---|---|---|---|---|---|"]
        for x in bc:
            L.append(f"| {x['corner']} | {x['temp']} | {x['vdd']:.2f} | {x['hold'] * 1e3:.0f} | {x['read'] * 1e3:.0f} | {x['wm_wl'] * 1e3:.0f} | "
                     f"{x['iread'] * 1e6:.0f} | {x['leak'] * 1e12:.1f} |")
        L += ["", "Corner names follow the SKY130 model files: in `sf` the n-channel devices are fast and the p-channel devices slow, in `fs` the reverse.",
              "Write margin: word-line write margin, VDD minus the lowest word-line voltage that flips the cell with one bit line at 0 V.", ""]
    mc = _j("bitcell_mc.json")
    if mc:
        n = list(mc.values())[0]["read"]["n"]
        L += [f"### Monte Carlo, local mismatch ({n} cells per condition)", "",
              "| corner | T (°C) | VDD (V) | read SNM mean ± σ (mV) | min (mV) | mean / σ | write margin mean ± σ (mV) | min (mV) | failures |",
              "|---|---|---|---|---|---|---|---|---|"]
        for k, v in mc.items():
            c, t, vd = k.split("_")
            L.append(f"| {c} | {t} | {vd} | {v['read']['mean'] * 1e3:.0f} ± {v['read']['sigma'] * 1e3:.1f} | {v['read']['min'] * 1e3:.0f} | "
                     f"{v['read']['mean'] / v['read']['sigma']:.0f} | {v['wm_wl']['mean'] * 1e3:.0f} ± {v['wm_wl']['sigma'] * 1e3:.1f} | "
                     f"{v['wm_wl']['min'] * 1e3:.0f} | {v['read']['fails'] + v['wm_wl']['fails'] + v['hold']['fails']} |")
        L += ["", "The spread comes from the mismatch models of the PDK (`*_mm` corners). Their accuracy for devices this small has not been "
              "checked against silicon here; read the σ counts as model predictions.", ""]
    L += ["## Array macro (sram_array_64x32)", "",
          f"- Size {r['macro_w']:.2f} × {r['macro_h']:.2f} µm, {r['array_mosfets']:,} transistors",
          f"- Magic DRC (full deck): {r['array_magic_drc']} violations",
          f"- KLayout DRC (sky130A_mr.drc, FEOL + BEOL + off-grid): {r['array_klayout_drc']} violations",
          f"- Netgen LVS against the generated schematic: {'match' if r['array_lvs'] else 'MISMATCH'} "
          f"({r['array_lvs_devices']:,} devices, {r['array_lvs_nets']:,} nets)", ""]
    f = r["flow"]
    L += ["## Complete memory (sram_64x32)", "",
          f"- Die {r['die_w']:g} × {r['die_h']:g} µm ({r['die_w'] * r['die_h'] / 1e6:.4f} mm²)",
          f"- {r['mosfets']:,} transistors ({r['array_mosfets']:,} in the array) plus {r['decap_mosfets']:,} decoupling-capacitor devices in filler cells",
          f"- {r['stdcells']:,} standard cells (without tap and filler cells), routed wire length {f['route__wirelength'] / 1000:.1f} mm",
          f"- Place-and-route sign-off: Magic DRC {f['magic__drc_error__count']}, KLayout DRC {f['klayout__drc_error__count']}, "
          f"gate-level LVS errors {f['design__lvs_error__count']}, antenna violations {f['antenna__violating__nets']}, "
          f"Magic/KLayout XOR differences {f['design__xor_difference__count']}, slew / capacitance violations "
          f"{f['design__max_slew_violation__count']} / {f['design__max_cap_violation__count']}, power-grid violations {f['design__power_grid_violation__count']}, "
          f"worst static IR drop {f['ir__drop__worst'] * 1e3:.2f} mV",
          f"- Transistor-level LVS of the final GDS, flat: {'match' if r['lvs'] else 'MISMATCH'} ({r['lvs_devices']:,} devices after merging parallel "
          f"devices, {r['lvs_nets']:,} nets)", ""]
    cc, cp, t = r.get("chip_corners"), r.get("chip_period"), r.get("timing")
    if cc:
        L += ["### Post-layout SPICE, sign-off corners (20 ns clock, 30 fF on every output)", "",
              "| corner | T (°C) | VDD (V) | function | clk↓ → dout min … max (ns) | supply current (mA) |", "|---|---|---|---|---|---|"]
        for x in cc:
            L.append(f"| {x['corner']} | {x['temp']} | {x['vdd']:.2f} | {'pass' if x['ok'] else 'FAIL'} | "
                     f"{x.get('t_cq_min', 0) * 1e9:.2f} … {x.get('t_cq_max', 0) * 1e9:.2f} | {x.get('i_avg', 0) * 1e3:.2f} |")
        L += ["", f"Netlist: {cc[0].get('netlist', '')}.", ""]
    if cp:
        L += ["### Clock-period sweep (50 % duty cycle)", "", "| corner | period (ns) | frequency (MHz) | function |", "|---|---|---|---|"]
        for x in cp:
            L.append(f"| {x['corner']} | {x['T'] * 1e9:g} | {1e-6 / x['T']:.0f} | {'pass' if x['ok'] else 'FAIL'} |")
        L.append("")
    if t:
        L += ["### Timing summary used in the Liberty files", "",
              "| corner | clk↓ → dout max (ns) | clk↓ → dout min (ns) | shortest passing period (ns) | specified minimum period (ns) |", "|---|---|---|---|---|"]
        for c, x in t.items():
            L.append(f"| {c} {x['temp']} °C {x['vdd']} V | {x['t_cq_max']:.2f} | {x['t_cq_min']:.2f} | {x['t_min_period_sim']:g} | {x['min_period_spec']:g} |")
        L.append("")
    ci = r.get("chip_interface")
    if ci:
        L += ["### All inputs switching at the published setup / hold limit (post-layout SPICE, 20 ns clock)", "",
              "Times are between the 50 % points of the input and of the clock.", "",
              "| corner | inputs change | function |", "|---|---|---|"]
        for x in ci:
            when = (f"{(x['T'] - x['t_in'] - 0.075e-9) * 1e9:.3f} ns before the edge (setup limit)" if x["t_in"] > x["T"] / 2
                    else f"{(x['t_in'] + 0.075e-9) * 1e9:.3f} ns after the edge (hold limit)")
            L.append(f"| {x['corner']} {x['temp']} °C {x['vdd']} V | {when} | {'pass' if x['ok'] else 'FAIL'} |")
        L.append("")
    cf = r.get("chip_full")
    if cf:
        L += ["### Full netlist run", "",
              f"All {r['mosfets']:,} transistors, 17 operations (writes to words 0, 21, 42 and 63, reads, a byte-masked write, a disabled cycle) at "
              f"tt, {cf['temp']} °C, {cf['vdd']} V: {'pass' if cf['ok'] else 'FAIL'}; clk↓ → dout {cf['t_cq_min'] * 1e9:.2f} … {cf['t_cq_max'] * 1e9:.2f} ns.", ""]
    sl = _j("slice_corners.json")
    if sl:
        L += ["### Column slice before layout (schematic, extracted wire capacitances)", "",
              "| corner | T (°C) | VDD (V) | function | clk↓ → dout (ns) | word line (ns) | bit line (ns) | precharge (ns) | write (ns) | read bump (mV) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for x in sl:
            if "t_wl" in x:
                L.append(f"| {x['corner']} | {x['temp']} | {x['vdd']:.2f} | {'pass' if x['ok'] else 'FAIL'} | {max(x['t_cq_rise'], x['t_cq_fall']) * 1e9:.2f} | "
                         f"{x['t_wl'] * 1e9:.2f} | {x['t_bl'] * 1e9:.2f} | {x['t_pre'] * 1e9:.2f} | {x['t_write'] * 1e9:.2f} | {x['v_bump'] * 1e3:.0f} |")
        L.append("")
    st = _j("slice_static.json")
    if st:
        L += ["### Static operation: column slice with a 1 MHz clock (500 ns per phase)", "",
              "| corner | T (°C) | VDD (V) | function | high bit line at the end of a read (V) | low bit line (mV) |", "|---|---|---|---|---|---|"]
        for x in st:
            L.append(f"| {x['corner']} | {x['temp']} | {x['vdd']:.2f} | {'pass' if x['ok'] else 'FAIL'} | {x['high_line_min_V']:.3f} | {x['low_line_max_V'] * 1e3:.1f} |")
        L += ["", "The bit line that must stay high is held by the keeper for the whole phase, also at the corners with the highest leakage.", ""]
    ex = _j("example_summary.json")
    if ex:
        L += ["## Integration example (self-test controller + sram_64x32 hard macro)", "",
              f"- Die area {ex['design__die__area'] / 1e6:.4f} mm², {ex['design__instance__count__stdcell']} standard-cell instances (including fill), "
              f"{ex['clock_period_ns']} ns clock",
              f"- Magic DRC {ex['magic__drc_error__count']}, KLayout DRC {ex['klayout__drc_error__count']}, LVS errors {ex['design__lvs_error__count']}, "
              f"antenna violations {ex['antenna__violating__nets']}, power-grid violations {ex['design__power_grid_violation__count']}",
              f"- Worst setup slack {ex['timing__setup__ws']:.2f} ns, worst hold slack {ex['timing__hold__ws']:.2f} ns (all corners)", ""]
    lg = os.path.join(OUT, "logic_sim.txt")
    if os.path.exists(lg):
        L += ["## Logic simulation", "", "```", open(lg).read().strip(), "```", ""]
    open(os.path.join(ROOT, "docs", "results.md"), "w").write("\n".join(L) + "\n")


def _lib_constraints(corner_file):
    """Largest setup and hold time over all input pins of a Liberty file (ns)."""
    txt = open(corner_file).read()
    out = {}
    for kind in ("setup_rising", "hold_rising"):
        vals = []
        for blk in re.findall(rf"timing_type : {kind};(.*?)\n      \}}", txt, re.S):
            vals += [float(v) for v in re.findall(r'values\("([-0-9.eE]+)"\)', blk)]
        out[kind] = max(vals)
    out["cin"] = max(float(v) for v in re.findall(r"direction : input;\s*capacitance : ([0-9.]+);", txt))
    return out


def fill_templates(r):
    """Render README.md and docs/datasheet.md from their templates with the measured numbers."""
    import numpy as np
    t, b = r["timing"], r["bitcell"]
    rel = os.path.join(ROOT, "release")
    names = {"tt": "tt_025C_1v80", "ss": "ss_100C_1v60", "ff": "ff_n40C_1v95"}
    lib = {c: _lib_constraints(os.path.join(rel, f"sram_64x32__{n}.lib")) for c, n in names.items()}
    # supply current while enabled / disabled, from the post-layout runs (20 ns clock)
    cur = {}
    for c in names:
        d = np.load(os.path.join(OUT, f"chipc_{c}.npz"))
        tt_, i = d["t"], -d["ivdd"]
        T = 20e-9
        win = lambda k0, k1: float(np.trapezoid(i[(tt_ >= (k0 + 1) * T) & (tt_ < (k1 + 1) * T)], tt_[(tt_ >= (k0 + 1) * T) & (tt_ < (k1 + 1) * T)]) / ((k1 - k0) * T))
        cur[c] = dict(read=win(3, 5), write=win(1, 3), idle=win(9, 10))
    head = "| | tt, 25 °C, 1.80 V | ss, 100 °C, 1.60 V | ff, −40 °C, 1.95 V |\n|---|---|---|---|\n"
    row = lambda name, f: f"| {name} | " + " | ".join(f(c) for c in ("tt", "ss", "ff")) + " |\n"
    timing = head
    timing += row("Input setup time before rising `clk` (ns)", lambda c: f"{lib[c]['setup_rising']:.2f}")
    timing += row("Input hold time after rising `clk` (ns)", lambda c: f"{lib[c]['hold_rising']:.2f}")
    timing += row("*t*<sub>CQ</sub>: falling `clk` to `dout`, 30 fF load (ns)", lambda c: f"{t[c]['t_cq_min']:.2f} … {t[c]['t_cq_max']:.2f}")
    timing += row("Shortest clock period that passed in SPICE (ns)", lambda c: f"{t[c]['t_min_period_sim']:g}")
    timing += row("**Minimum clock period, specified (ns)**", lambda c: f"**{t[c]['min_period_spec']:g}**")
    timing += row("Minimum `clk` high time = minimum low time (ns)", lambda c: f"{t[c]['min_period_spec'] / 2:g}")
    timing += row("Maximum clock frequency (MHz)", lambda c: f"{1e3 / t[c]['min_period_spec']:.0f}")
    elec = head
    elec += row("Supply current, reading at 50 MHz (mA)", lambda c: f"{cur[c]['read'] * 1e3:.2f}")
    elec += row("Supply current, writing at 50 MHz (mA)", lambda c: f"{cur[c]['write'] * 1e3:.2f}")
    elec += row("Input pin capacitance, largest (fF)", lambda c: f"{lib[c]['cin'] * 1e3:.1f}")
    elec += (f"\nArray leakage from the cell simulation: {b['leak_tt'] * 2048 * 1e9:.1f} nA at tt, 27 °C, 1.8 V; "
             f"{b['leak_worst'] * 2048 * 1e6:.1f} µA at the worst simulated point (fast p-channel, 125 °C, 1.98 V).\n"
             "Supply range of the cell analysis: 1.62 V to 1.98 V, −40 °C to 125 °C.\n"
             "Standby current of the complete macro (clock stopped or `en` = 0) has not been characterised separately.\n")
    tok = {
        "%TIMING_TABLE%": timing, "%ELECTRICAL_TABLE%": elec,
        "%MOSFETS%": f"{r['mosfets']:,}", "%LVSDEV%": f"{r['lvs_devices']:,}", "%LVSNETS%": f"{r['lvs_nets']:,}",
        "%READ_WORST%": f"{b['read_worst'] * 1e3:.0f}", "%WM_WORST%": f"{b['wm_worst'] * 1e3:.0f}", "%MC_N%": f"{b['mc_n']:,}",
        "%TCQ_TT%": f"{t['tt']['t_cq_max']:.1f}", "%TCQ_SS%": f"{t['ss']['t_cq_max']:.1f}",
        "%TMIN_TT%": f"{t['tt']['t_min_period_sim']:g}", "%TMIN_SS%": f"{t['ss']['t_min_period_sim']:g}",
        "%TSPEC_SS%": f"{t['ss']['min_period_spec']:g}", "%FSPEC_SS%": f"{1e3 / t['ss']['min_period_spec']:.0f}",
        "%I_TT%": f"{cur['tt']['read'] * 1e3:.2f}",
    }
    tok["%REPO_URL%"] = REPO_URL
    for src, dst in (("README.in.md", os.path.join(ROOT, "README.md")), ("datasheet.in.md", os.path.join(ROOT, "docs", "datasheet.md")),
                     ("linkedin_post.in.md", os.path.join(ROOT, "linkedin_post.md"))):
        txt = open(os.path.join(ROOT, "docs", "templates", src)).read()
        for k, v in tok.items():
            txt = txt.replace(k, v)
        assert "%" not in re.sub(r"\d+ ?%", "", txt), [m for m in re.findall(r"%\w+%", txt)]
        open(dst, "w").write(txt)
    r["current"] = cur
    json.dump(r, open(os.path.join(OUT, "results.json"), "w"), indent=1)


if __name__ == "__main__":
    res = collect()
    summaries(res)
    markdown(res)
    if res.get("timing") and os.path.exists(os.path.join(ROOT, "release", "sram_64x32__tt_025C_1v80.lib")):
        fill_templates(res)
    print(json.dumps({k: res[k] for k in ("cell_area", "macro_w", "macro_h", "mosfets", "lvs_devices", "stdcells", "timing")}, indent=1))
