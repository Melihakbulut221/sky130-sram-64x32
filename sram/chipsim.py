"""Post-layout SPICE of the complete memory.

The netlist is the flat extraction of the final GDS (out/chip/sram_64x32.pex.spice): every
transistor of the array and of the standard cells, plus the wire capacitance Magic extracted.

    python -m sram.chipsim func [corner temp vdd period_ns] [full]   # write / read / mask / disable sequence
    python -m sram.chipsim corners        # short sequence at the three sign-off corners
    python -m sram.chipsim period         # clock-period sweep at the three corners

By default only the rows that a test addresses are simulated as transistors; the cells of the
other rows are replaced by the load their switched-off access transistors put on the bit lines
(measured on the extracted devices). "full" simulates every transistor.
"""
import json
import os
import re
import sys
import time

import numpy as np

from . import spice as S
from .models import flat_models, model_name, slim_lib
from .paths import OUT, SIM

PEX = os.path.join(OUT, "chip", "sram_64x32.pex.spice")
DIR = os.path.join(SIM, "chip")
SUPPLY = {"VPWR", "VGND"}


def _rows_of_cells(lines):
    """Map every storage node of the array to its row, using the word line on its access transistor."""
    row = {}
    for p in lines:
        if p[0][0] == "X" and p[2].startswith("u_array/WL["):
            r = int(p[2][len("u_array/WL["):-1])
            for n in (p[1], p[3]):
                if "/cells/" in n and n.endswith("#"):
                    row[n] = r
    return row


def bitline_load(col_lines, vdd=1.8):
    """Average capacitance (F) one switched-off access transistor puts on its bit line, with the storage
    side at 0 V ("q0") and at VDD ("q1"). Measured on the 64 extracted devices of one column."""
    cache = os.path.join(DIR, "bitline_load.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    out = {}
    for inner, key in ((0.0, "q0"), (vdd, "q1")):
        d = "* off-state load of one column on its bit line\n"
        d += f'.include "{slim_lib("tt")}"\n.temp 27\n'
        d += f"Vbl bl 0 pwl(0 0 1n 0 3n {vdd})\nVin inner 0 {inner}\n"
        for k, p in enumerate(col_lines):
            bl_first = p[1].startswith("u_array/BL")
            a, b = ("bl", "inner") if bl_first else ("inner", "bl")
            d += f"X{k} {a} 0 {b} 0 " + " ".join(p[5:]) + "\n"
        d += ".control\ntran 5p 3.2n\nmeas tran q integ i(Vbl) from=1n to=3n\nquit\n.endc\n.end\n"
        log = S.run("bitline_load_" + key, d, subdir="chip")
        out[key] = abs(S.meas(log, "q")) / vdd / len(col_lines)
    json.dump(out, open(cache, "w"))
    return out


def prepare(keep_rows=None, force=False):
    """Rewrite the extracted netlist with simple node names and without the decap devices.

    keep_rows = None keeps everything. Otherwise only the cells of those rows stay as transistors;
    the cells of all other rows (which the test never selects) are replaced by the capacitance their
    switched-off access transistors put on the bit lines, and their static storage nodes become
    ground for the coupling capacitors. Returns (netlist path, name map).
    """
    tagp = "full" if keep_rows is None else "rows_" + "_".join(str(r) for r in sorted(keep_rows))
    dut = os.path.join(DIR, f"dut_{tagp}.spice")
    mp_path = dut.replace(".spice", ".map.json")
    if os.path.exists(dut) and not force and os.path.getmtime(dut) > os.path.getmtime(PEX):
        return dut, json.load(open(mp_path))
    os.makedirs(DIR, exist_ok=True)
    lines = [l.split() for l in open(PEX).read().replace("\n+", " ").splitlines() if l.split()]
    row = _rows_of_cells(lines)
    pruned = set() if keep_rows is None else {n for n, r in row.items() if r not in keep_rows}
    names, used = {}, set()

    def clean(n):
        if n in names:
            return names[n]
        c = re.sub(r"[^a-z0-9_]", "_", n.lower())
        if n == "VGND" or n in pruned:
            c = "0"
        elif n == "VPWR":
            c = "vdd"
        else:
            c = "n_" + c
            base, k = c, 1
            while c in used:
                k += 1
                c = f"{base}_{k}"
            used.add(c)
        names[n] = c
        return c

    out, ndev, ncap, dropped, cut = [], 0, 0, 0, 0
    sizes = set()
    removed_pg = {}                    # bit line -> number of removed access transistors
    col0 = [p for p in lines if p[0][0] == "X" and p[2].startswith("u_array/WL[") and "u_array/BL[0]" in (p[1], p[3])]
    for p in lines:
        if p[0].lower() == ".subckt":
            for port in p[2:]:
                clean(port)
        elif p[0][0] == "X":
            if set(p[1:5]) <= SUPPLY:
                dropped += 1
                continue
            if pruned and (p[1] in pruned or p[2] in pruned or p[3] in pruned):
                cut += 1
                for n in (p[1], p[3]):
                    if n.startswith("u_array/BL"):
                        removed_pg[n] = removed_pg.get(n, 0) + 1
                continue
            # plain M element with a shared, size-specific model (see models.flat_models)
            par = dict(kv.split("=") for kv in p[6:])
            w_, l_ = float(par["w"]), float(par["l"])
            sizes.add((p[5], w_, l_))
            out.append(f"M{ndev} " + " ".join(clean(n) for n in p[1:5]) + f" {model_name(p[5], w_, l_)} " + " ".join(p[6:]))
            ndev += 1
        elif p[0][0] == "C":
            ca, cb = clean(p[1]), clean(p[2])
            if {ca, cb} <= {"0", "vdd"}:
                continue
            out.append(f"C{ncap} {ca} {cb} {p[3]}")
            ncap += 1
    if removed_pg:
        load = bitline_load(col0)
        for bl, k in sorted(removed_pg.items()):
            # every cell is initialised to 0: the BL side sees a storage node at 0 V, the BLB side one at VDD
            c = load["q0"] if bl.startswith("u_array/BL[") else load["q1"]
            out.append(f"Cprune{ncap} {clean(bl)} 0 {c * k:.6e}")
            ncap += 1
    with open(dut, "w") as f:
        f.write(f"* sram_64x32 post-layout netlist: {ndev} MOSFETs, {ncap} capacitors "
                f"({dropped} decap devices removed, {cut} devices of unselected rows replaced by their bit-line load)\n")
        f.write("\n".join(out) + "\n")
    names["__sizes__"] = sorted(sizes)
    # storage nodes of the cells that are still transistors: "row,col" -> [Q, QB] (clean names)
    cellmap = {}
    for p in lines:
        if p[0][0] == "X" and p[2].startswith("u_array/WL["):
            r_ = int(p[2][len("u_array/WL["):-1])
            for bl, inner in ((p[1], p[3]), (p[3], p[1])):
                m_ = re.match(r"u_array/(BLB?)\[(\d+)\]$", bl)
                if m_ and inner in row and inner not in pruned:
                    cellmap.setdefault(f"{r_},{m_.group(2)}", [None, None])[0 if m_.group(1) == "BL" else 1] = names[inner]
    names["__cells__"] = cellmap
    json.dump(names, open(mp_path, "w"))
    return dut, names


# ----------------------------------------------------------------------------- stimulus
# (en, we, wmask, addr, din, expected dout at the end of the cycle or None)
OPS = [
    (0, 0, 0x0, 0, 0x00000000, None),
    (1, 1, 0xF, 0, 0xFFFFFFFF, None),
    (1, 1, 0xF, 63, 0x00000000, None),
    (1, 1, 0xF, 21, 0xA5A55A5A, None),
    (1, 1, 0xF, 42, 0x5A5AA5A5, None),
    (1, 0, 0x0, 0, 0x00000000, 0xFFFFFFFF),
    (1, 0, 0x0, 63, 0x00000000, 0x00000000),
    (1, 0, 0x0, 21, 0x00000000, 0xA5A55A5A),
    (1, 0, 0x0, 42, 0x00000000, 0x5A5AA5A5),
    (1, 1, 0x5, 21, 0x12345678, 0x5A5AA5A5),       # byte write; dout must hold
    (1, 0, 0x0, 21, 0x00000000, 0xA5345A78),
    (0, 1, 0xF, 0, 0x00000000, 0xA5345A78),        # disabled: no write, dout holds
    (1, 0, 0x0, 0, 0x00000000, 0xFFFFFFFF),
    (1, 1, 0xF, 0, 0x00000000, 0xFFFFFFFF),
    (1, 0, 0x0, 0, 0x00000000, 0x00000000),
    (1, 0, 0x0, 42, 0x00000000, 0x5A5AA5A5),
    (0, 0, 0x0, 0, 0x00000000, 0x5A5AA5A5),
]
# short sequence for the corner and period sweeps: two words, a byte write, a disabled cycle
SHORT = [
    (0, 0, 0x0, 0, 0x00000000, None),
    (1, 1, 0xF, 21, 0xA5A55A5A, None),
    (1, 1, 0xF, 42, 0x5A5AA5A5, None),
    (1, 0, 0x0, 21, 0x00000000, 0xA5A55A5A),
    (1, 0, 0x0, 42, 0x00000000, 0x5A5AA5A5),
    (1, 1, 0x5, 21, 0x12345678, 0x5A5AA5A5),
    (1, 0, 0x0, 21, 0x00000000, 0xA5345A78),
    (0, 1, 0xF, 42, 0x00000000, 0xA5345A78),
    (1, 0, 0x0, 42, 0x00000000, 0x5A5AA5A5),
    (0, 0, 0x0, 0, 0x00000000, 0x5A5AA5A5),
]
SIGNOFF = [("tt", 25, 1.8), ("ss", 100, 1.6), ("ff", -40, 1.95)]          # the corners of the standard-cell libraries
PERIODS = {"tt": (10, 7, 5), "ss": (14, 10, 8), "ff": (6, 4, 3)}           # clock periods (ns) tried per corner


def pwl(name, node, bits, T, t_in, vdd, tr=0.15e-9):
    """bits[k] is sampled at rising edge k (at (k+1)*T) and applied t_in after the previous edge."""
    s = f"V{name} {node} 0 pwl(0 {vdd * bits[0]:g}"
    prev = bits[0]
    for k in range(1, len(bits)):
        if bits[k] != prev:
            t = k * T + t_in
            s += f" {t:.5e} {vdd * prev:g} {t + tr:.5e} {vdd * bits[k]:g}"
            prev = bits[k]
    return s + ")\n"


def deck(dut, names, ops=OPS, corner="tt", temp=27, vdd=1.8, T=20e-9, t_in=1.0e-9, tag="chip", duty=0.5, extra_save=()):
    n = lambda x: names[x]
    d = f"* sram_64x32 post-layout {corner} {temp}C {vdd}V T={T * 1e9:g}ns\n"
    d += f'.include "{flat_models(corner, [tuple(x) for x in names["__sizes__"]])}"\n.temp {temp}\n'
    d += ".option klu method=gear reltol=3e-3 abstol=1e-11 vntol=3e-5 chgtol=1e-15 gmin=1e-12 itl4=60\n"
    d += f"Vvdd vdd 0 {vdd}\n"
    d += f'.include "{dut}"\n'
    th = T * duty
    d += f"Vclk {n('clk')} 0 pulse(0 {vdd} {T - 0.075e-9:.5e} 0.15n 0.15n {th - 0.15e-9:.5e} {T:.5e})\n"
    cols = list(zip(*[(o[0], o[1], o[2], o[3], o[4]) for o in ops]))
    d += pwl("en", n("en"), list(cols[0]), T, t_in, vdd) + pwl("we", n("we"), list(cols[1]), T, t_in, vdd)
    for i in range(4):
        d += pwl(f"wm{i}", n(f"wmask[{i}]"), [(v >> i) & 1 for v in cols[2]], T, t_in, vdd)
    for i in range(6):
        d += pwl(f"a{i}", n(f"addr[{i}]"), [(v >> i) & 1 for v in cols[3]], T, t_in, vdd)
    for i in range(32):
        d += pwl(f"d{i}", n(f"din[{i}]"), [(v >> i) & 1 for v in cols[4]], T, t_in, vdd)
        d += f"Cl{i} {n(f'dout[{i}]')} 0 30f\n"
    # every cell starts at 0 (Q low, QB high), the bit lines start precharged; everything else starts discharged
    ic = []
    for k, c in names.items():
        if c == "0" or k.startswith("__"):
            continue
        if k.endswith("/a_55_58#") and k.startswith("u_array/"):
            ic.append(f".ic v({c})=0")
        elif k.endswith("/a_29_28#") and k.startswith("u_array/"):
            ic.append(f".ic v({c})={vdd}")
        elif k.startswith("u_array/BL"):
            ic.append(f".ic v({c})={vdd}")
    d += "\n".join(ic) + "\n"
    save = [n("clk")] + [n(f"dout[{i}]") for i in range(32)]
    probe = {"wl0": "u_array/WL[0]", "wl21": "u_array/WL[21]", "wl42": "u_array/WL[42]", "wl63": "u_array/WL[63]",
             "bl0": "u_array/BL[0]", "blb0": "u_array/BLB[0]", "bl31": "u_array/BL[31]", "blb31": "u_array/BLB[31]",
             "phi_wl": "keep_phibuf_wl/X", "phi_d": "keep_dlybuf/X", "phi_root": "keep_icg/GCLK", "clk_i": "keep_clkbuf/X"}
    probe = {k: v for k, v in probe.items() if v in names}
    extra = {}                                           # extra_save: ((row, col), ...) -> storage nodes of those cells
    for (r_, c_) in extra_save:
        q_, qb_ = names["__cells__"][f"{r_},{c_}"]
        extra[f"q_{r_}_{c_}"], extra[f"qb_{r_}_{c_}"] = q_, qb_
    save += [names[v] for v in probe.values()] + list(extra.values())
    tstop = (len(ops) + 1) * T
    d += ".save " + " ".join(f"v({s})" for s in save) + " i(Vvdd)\n"
    d += (f".control\ntran 25p {tstop:.5e} uic\nset wr_singlescale\nwrdata {tag}.dat "
          + " ".join(f"v({s})" for s in save) + " i(Vvdd)\nquit\n.endc\n.end\n")
    cols_out = ["clk"] + [f"dout{i}" for i in range(32)] + list(probe) + list(extra) + ["ivdd"]
    return d, cols_out


def run(corner="tt", temp=27, vdd=1.8, T=20e-9, ops=OPS, t_in=1.0e-9, duty=0.5, keep=None, tag=None, extra_save=(), prune=True):
    """prune=True keeps only the rows that the sequence addresses as transistors (see prepare)."""
    rows = sorted({o[3] for o in ops if o[0]}) if prune else None
    dut, names = prepare(rows)
    tag = tag or f"chip_{corner}_{temp}_{vdd:g}_{T * 1e9:g}_{len(ops)}{'' if prune else '_full'}".replace(".", "p").replace("-", "m")
    dk, cols = deck(dut, names, ops, corner, temp, vdd, T, t_in, tag, duty, extra_save)
    t0 = time.time()
    log = S.run(tag, dk, subdir="chip", timeout=12 * 3600)
    path = os.path.join(DIR, tag + ".dat")
    if not os.path.exists(path):
        return dict(ok=False, error=log[-600:], wall=time.time() - t0, corner=corner, temp=temp, vdd=vdd, T=T)
    a = np.loadtxt(path)
    t = a[:, 0]
    w = {c: a[:, 1 + i] for i, c in enumerate(cols)}
    h = vdd / 2
    ok, got, bad = True, [], []
    for k, o in enumerate(ops):
        ts = (k + 2) * T - 0.15e-9                      # just before the next rising edge
        v = sum((1 << i) for i in range(32) if np.interp(ts, t, w[f"dout{i}"]) > h)
        got.append(v)
        if o[5] is not None and v != o[5]:
            ok = False
            bad.append((k, f"{v:08x}", f"{o[5]:08x}"))
    res = dict(ok=ok, bad=bad, got=[f"{g:08x}" for g in got], wall=time.time() - t0, corner=corner, temp=temp, vdd=vdd, T=T,
               duty=duty, t_in=t_in, netlist=open(dut).readline().strip("* \n"))
    # clock falling edge -> data out, over all bits and all read operations (last crossing in the low phase)
    tcq = []
    for k, o in enumerate(ops):
        if o[0] and not o[1] and o[5] is not None and k > 0:
            tf = (k + 1) * T + T * duty
            m = (t >= tf) & (t <= tf + T * (1 - duty))
            x = t[m]
            for i in range(32):
                y = w[f"dout{i}"][m]
                idx = np.where(((y[:-1] - h) * (y[1:] - h)) < 0)[0]
                if len(idx):
                    j = idx[-1]
                    tcq.append(x[j] + (h - y[j]) * (x[j + 1] - x[j]) / (y[j + 1] - y[j]) - tf)
    res["t_cq_max"] = float(max(tcq)) if tcq else float("nan")
    res["t_cq_min"] = float(min(tcq)) if tcq else float("nan")
    m = t > 2 * T
    res["i_avg"] = float(-np.trapezoid(w["ivdd"][m], t[m]) / (t[m][-1] - t[m][0]))
    if keep:
        np.savez(os.path.join(OUT, keep), t=t, **w)
    return res


def _job(kw):
    return run(**kw)


def sweep(jobs, name, workers=4):
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_job, jobs))
    json.dump(res, open(os.path.join(OUT, name + ".json"), "w"), indent=1)
    for r in res:
        print(f"{r.get('corner')} {r.get('temp')}C {r.get('vdd')}V T={r.get('T', 0) * 1e9:g}ns  {'PASS' if r['ok'] else 'FAIL'}  "
              f"clk-fall->dout {r.get('t_cq_min', 0) * 1e9:.2f} .. {r.get('t_cq_max', 0) * 1e9:.2f} ns  I={r.get('i_avg', 0) * 1e3:.3f} mA  "
              f"wall {r['wall']:.0f}s {r.get('bad') or r.get('error', '')}")
    return res


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "prepare":
        for rows in (None, [21, 42]):
            dut, nm = prepare(rows, force=True)
            print(len(nm) - 2, "nodes;", open(dut).readline().strip())
        print(json.load(open(os.path.join(DIR, "bitline_load.json"))))
    elif a == "func":
        c = sys.argv[2] if len(sys.argv) > 2 else "tt"
        temp = int(sys.argv[3]) if len(sys.argv) > 3 else 25
        v = float(sys.argv[4]) if len(sys.argv) > 4 else 1.8
        T = float(sys.argv[5]) * 1e-9 if len(sys.argv) > 5 else 20e-9
        full = "full" in sys.argv
        r = run(c, temp, v, T, prune=not full, keep=f"chip_{c}_{temp}_{v:g}_{T * 1e9:g}{'_full' if full else ''}.npz")
        print(json.dumps(r, indent=1))
    elif a == "corners":
        sweep([dict(corner=c, temp=t, vdd=v, T=20e-9, ops=SHORT, keep=f"chipc_{c}.npz") for (c, t, v) in SIGNOFF], "chip_corners", 3)
    elif a == "period":
        sweep([dict(corner=c, temp=t, vdd=v, T=T * 1e-9, ops=SHORT) for (c, t, v) in SIGNOFF for T in PERIODS[c]], "chip_period", 4)
    elif a == "points":
        # extra period points, e.g.  python -m sram.chipsim points ss:11 ss:12 tt:6   (merged into chip_period.json)
        pvt = {c: (c, t, v) for (c, t, v) in SIGNOFF}
        jobs = [dict(corner=pvt[x.split(":")[0]][0], temp=pvt[x.split(":")[0]][1], vdd=pvt[x.split(":")[0]][2],
                     T=float(x.split(":")[1]) * 1e-9, ops=SHORT) for x in sys.argv[2:]]
        res = sweep(jobs, "chip_period_extra", 3)
        pth = os.path.join(OUT, "chip_period.json")
        allp = [r for r in json.load(open(pth)) if (r["corner"], r["T"]) not in {(x["corner"], x["T"]) for x in res}] + res
        allp.sort(key=lambda r: (["tt", "ss", "ff"].index(r["corner"]), -r["T"]))
        json.dump(allp, open(pth, "w"), indent=1)
    elif a == "interface":
        # Every input switches exactly at the setup limit before, or at the hold limit after, the rising
        # clock edge (limits = largest value over all pins in the released Liberty file of the corner).
        from .report import _lib_constraints
        from .paths import ROOT
        lib = {"tt": "tt_025C_1v80", "ss": "ss_100C_1v60", "ff": "ff_n40C_1v95"}
        jobs, half = [], 0.075e-9                       # the stimulus crosses 50 % 75 ps after it starts to move
        for (c, t, v) in SIGNOFF:
            k = _lib_constraints(os.path.join(ROOT, "release", f"sram_64x32__{lib[c]}.lib"))
            jobs.append(dict(corner=c, temp=t, vdd=v, T=20e-9, ops=SHORT, t_in=20e-9 - k["setup_rising"] * 1e-9 - half, tag=f"chip_setup_{c}"))
            jobs.append(dict(corner=c, temp=t, vdd=v, T=20e-9, ops=SHORT, t_in=k["hold_rising"] * 1e-9 - half, tag=f"chip_hold_{c}"))
        res = sweep(jobs, "chip_interface", 4)
    elif a == "figure":
        r = run("tt", 25, 1.8, 20e-9, ops=SHORT, keep="chipc_tt.npz", tag="chip_figure", extra_save=((42, 0), (21, 0)))
        print(json.dumps({k: v for k, v in r.items() if k != "got"}, indent=1))
    elif a == "quick":
        print(json.dumps(run(ops=SHORT[:5], tag="chip_quick2"), indent=1))
