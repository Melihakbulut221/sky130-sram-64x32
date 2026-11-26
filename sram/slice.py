"""Transistor-level simulation of one column slice (schematic level, before layout).

One bit-line pair with all 64 cells, the two word lines at the ends of the column, and the
complete standard-cell path around them: input flip-flops, hold latches, clock gate, word-line
gates, tri-state bit-line drivers, sense inverters and the output latch. Wire capacitances are
the values extracted from the array layout.

    python -m sram.slice corners      # function + timing over process / voltage / temperature
    python -m sram.slice waves        # nominal waveforms for the figures (out/slice_tt.npz)
    python -m sram.slice mc           # Monte Carlo mismatch, dynamic read / write
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import spice as S
from .bitcell import CELL
from .models import slim_lib
from .paths import OUT, SIM

SC_LIB = os.path.join(SIM, "models", "sky130_fd_sc_hd.spice")
C_BL = 19e-15        # bit-line wire capacitance, extracted from the macro (junctions come with the cells)
C_WL = 80e-15        # word line: 31 other cells (gates) + wire, extracted
C_PHI_WL = 160e-15   # phase-clock branch of the word-line gates: the 62 other gates + wire
C_PHI_C = 65e-15     # phase-clock branch of half of the columns: the other gates + wire
C_CLK = 90e-15       # internal clock net: the other flip-flops + wire
ROWS = 64


def sc(name, cell, **pins):
    """Standard-cell instance with supplies and wells tied."""
    order = {
        "inv_2": ("A", "Y"), "clkinv_2": ("A", "Y"), "buf_2": ("A", "X"), "clkbuf_8": ("A", "X"), "clkbuf_16": ("A", "X"),
        "nand2_1": ("A", "B", "Y"), "and2_4": ("A", "B", "X"), "and3_4": ("A", "B", "C", "X"),
        "and2b_4": ("A_N", "B", "X"), "and3b_1": ("A_N", "B", "C", "X"),
        "ebufn_2": ("A", "TE_B", "Z"), "dfxtp_1": ("CLK", "D", "Q"), "dlxtn_1": ("D", "GATE_N", "Q"),
        "dlclkp_4": ("CLK", "GATE", "GCLK"), "dlygate4sd3_1": ("A", "X"),
    }[cell]
    # the library's port order is alphabetical inputs, VGND VNB VPB VPWR, then the output
    return f"X{name} " + " ".join(pins[p] for p in order[:-1]) + f" 0 0 vdd vdd {pins[order[-1]]} sky130_fd_sc_hd__{cell}\n"


def pwl(name, node, bits, T, t_in, vdd, tr=0.1e-9):
    """PWL source: bits[k] is the value sampled at rising edge k (edges at k*T); it is applied t_in after edge k-1."""
    s = f"V{name} {node} 0 pwl(0 {vdd * bits[0]:g}"
    prev = bits[0]
    for k in range(1, len(bits)):
        if bits[k] != prev:
            t = (k - 1) * T + t_in
            s += f" {t:.5e} {vdd * prev:g} {t + tr:.5e} {vdd * bits[k]:g}"
            prev = bits[k]
    return s + ")\n"


# sequence of operations: (en, we, row_select, din); row_select 0 -> row 0, 1 -> row 63
OPS = [(0, 0, 0, 0), (1, 1, 0, 1), (1, 1, 1, 0), (1, 0, 0, 0), (1, 0, 1, 0), (1, 1, 0, 0), (1, 0, 0, 0),
       (1, 1, 1, 1), (1, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)]
# dout expected at the END of the cycle of each operation (None = don't care before the first read)
EXPECT = [None, None, None, 1, 0, 0, 0, 0, 1, 0, 0, 0]


def deck(corner="tt", temp=27, vdd=1.8, T=20e-9, t_in=1e-9, mm=False, seed=1, z=CELL, tag="slice"):
    d = f"* SRAM column slice {corner} {temp}C {vdd}V\n"
    if mm:
        d += f".option seed={seed}\n"
    d += f'.include "{slim_lib(corner, mm)}"\n.include "{SC_LIB}"\n.temp {temp}\n'
    d += ".option method=gear reltol=2e-3 abstol=1e-12 vntol=1e-5 gmin=1e-12\n"
    d += f"Vvdd vdd 0 {vdd}\n"
    n = len(OPS)
    d += f"Vclk clk 0 pulse(0 {vdd} {T - 0.1e-9:.4e} 0.2n 0.2n {T / 2 - 0.2e-9:.4e} {T:.4e})\n"
    # rising edge k is at k*T (the first one at T): shift the op list by one period
    for nm, idx in (("en", 0), ("we", 1), ("a", 2), ("din", 3)):
        d += pwl(nm, nm, [0] + [o[idx] for o in OPS], T, t_in, vdd)
    # clock buffer and input flip-flops
    d += sc("clkbuf", "clkbuf_8", A="clk", X="clk_i") + f"Cclk clk_i 0 {C_CLK:g}\n"
    for nm in ("en", "we", "a", "din"):
        d += sc("ff_" + nm, "dfxtp_1", CLK="clk_i", D=nm, Q=nm + "_q")
    # phase clock, its two branches and its delayed copy
    d += sc("clkinv", "clkinv_2", A="clk_i", Y="clkb")
    d += sc("icg", "dlclkp_4", CLK="clkb", GATE="en_q", GCLK="phi_root")
    d += sc("phibuf_wl", "clkbuf_16", A="phi_root", X="phi_wl") + f"Cphiwl phi_wl 0 {C_PHI_WL:g}\n"
    d += sc("phibuf_c", "clkbuf_16", A="phi_root", X="phi") + f"Cphic phi 0 {C_PHI_C:g}\n"
    d += sc("phibuf_c1", "clkbuf_16", A="phi_root", X="phi_x") + f"Cphix phi_x 0 {C_PHI_C + 30e-15:g}\n"
    d += sc("dly0", "dlygate4sd3_1", A="phi_root", X="phi_d1") + sc("dly1", "dlygate4sd3_1", A="phi_d1", X="phi_d2")
    d += sc("dlybuf", "clkbuf_8", A="phi_d2", X="phi_d") + "Cphid phi_d 0 90f\n"
    # hold latches
    for nm in ("we", "a", "din"):
        d += sc("lat_" + nm, "dlxtn_1", D=nm + "_q", GATE_N="phi_d", Q=nm + "_l")
    # decoder (two rows) and word-line gates
    d += sc("dec0", "inv_2", A="a_l", Y="dec0") + sc("dec1", "inv_2", A="dec0", Y="dec63")
    d += sc("wl0", "and2_4", A="dec0", B="phi_wl", X="wl0") + sc("wl63", "and2_4", A="dec63", B="phi_wl", X="wl63")
    d += f"Cwl0 wl0 0 {C_WL:g}\nCwl63 wl63 0 {C_WL:g}\n"
    # write / read enables
    d += sc("wen", "and3_4", A="phi", B="we_l", C="vdd", X="wen") + sc("rd", "and2b_4", A_N="we_l", B="phi", X="rd")
    d += sc("dinn", "inv_2", A="din_l", Y="din_n")
    # column
    d += sc("w0", "nand2_1", A="wen", B="din_n", Y="w0n") + sc("w1", "nand2_1", A="wen", B="din_l", Y="w1n")
    d += sc("te0", "and3b_1", A_N="sb", B="phi", C="w0n", X="te_bl") + sc("te1", "and3b_1", A_N="sa", B="phi", C="w1n", X="te_blb")
    d += sc("drv0", "ebufn_2", A="w0n", TE_B="te_bl", Z="bl") + sc("drv1", "ebufn_2", A="w1n", TE_B="te_blb", Z="blb")
    d += sc("sa", "inv_2", A="bl", Y="sa") + sc("sb", "inv_2", A="blb", Y="sb")
    d += sc("s", "nand2_1", A="rd", B="sb", Y="s_n") + sc("r", "nand2_1", A="rd", B="sa", Y="r_n")
    d += sc("q", "nand2_1", A="s_n", B="q_n", Y="q") + sc("qn", "nand2_1", A="r_n", B="q", Y="q_n")
    d += sc("out", "buf_2", A="q", X="dout") + "Cout dout 0 20f\n"
    d += f"Cbl bl 0 {C_BL:g}\nCblb blb 0 {C_BL:g}\n"
    # the 64 cells of the column; rows 1..62 are never selected
    ic = ""
    for r in range(ROWS):
        wl = "wl0" if r == 0 else "wl63" if r == ROWS - 1 else "0"
        q, qb = f"q{r}", f"qb{r}"
        d += (S.mos(f"pdl{r}", q, qb, "0", "0", "n", z.wpd, z.lpd) + S.mos(f"pul{r}", q, qb, "vdd", "vdd", z.pu, z.wpu, z.lpu)
              + S.mos(f"pgl{r}", "bl", wl, q, "0", "n", z.wpg, z.lpg)
              + S.mos(f"pdr{r}", qb, q, "0", "0", "n", z.wpd, z.lpd) + S.mos(f"pur{r}", qb, q, "vdd", "vdd", z.pu, z.wpu, z.lpu)
              + S.mos(f"pgr{r}", "blb", wl, qb, "0", "n", z.wpg, z.lpg))
        one = (r == ROWS - 1) or (0 < r < ROWS - 1 and r % 2 == 1)      # row 0 starts at 0, row 63 at 1
        ic += f".ic v({q})={vdd if one else 0} v({qb})={0 if one else vdd}\n"
    d += ic + f".ic v(bl)={vdd} v(blb)={vdd} v(q)=0 v(q_n)={vdd}\n"
    tstop = (n + 1) * T
    save = "clk clk_i phi phi_wl phi_d wl0 wl63 bl blb sa sb q0 qb0 q63 qb63 dout rd wen te_bl te_blb w0n w1n a_l we_l din_l"
    d += f".save {' '.join('v(' + s + ')' for s in save.split())} i(Vvdd)\n"
    tstep = max(20e-12, T / 4000)                       # keep the output small for slow clocks
    d += f".control\ntran {tstep:.4e} {tstop:.4e} uic\nset wr_singlescale\nwrdata {tag}.dat " + " ".join("v(" + s + ")" for s in save.split()) + " i(Vvdd)\nquit\n.endc\n.end\n"
    return d, save.split() + ["ivdd"]


def cross(t, v, th, rising, t0=0.0, t1=1e9):
    a, b = v[:-1], v[1:]
    idx = np.where(((a < th) & (b >= th)) if rising else ((a > th) & (b <= th)))[0]
    tc = t[idx] + (th - a[idx]) * (t[idx + 1] - t[idx]) / (b[idx] - a[idx])
    tc = tc[(tc >= t0) & (tc <= t1)]
    return tc[0] if len(tc) else float("nan")


def run(corner="tt", temp=27, vdd=1.8, T=20e-9, t_in=1e-9, mm=False, seed=1, keep=False):
    tag = f"slice_{corner}_{temp}_{vdd:g}_{T * 1e9:g}_{seed if mm else 0}".replace(".", "p").replace("-", "m")
    dk, names = deck(corner, temp, vdd, T, t_in, mm, seed, tag=tag)
    log = S.run(tag, dk, subdir="slice")
    path = os.path.join(SIM, "slice", tag + ".dat")
    if not os.path.exists(path):
        return dict(ok=False, error=log[-400:])
    a = np.loadtxt(path)
    t = a[:, 0]
    w = {n: a[:, 1 + i] for i, n in enumerate(names)}
    h = vdd / 2
    # function: dout just before each rising edge
    ok, got = True, []
    for k, e in enumerate(EXPECT):
        ts = (k + 2) * T - 0.2e-9
        v = np.interp(ts, t, w["dout"])
        got.append(int(v > h))
        if e is not None and int(v > h) != e:
            ok = False
    res = dict(ok=ok, got=got)
    fall = lambda k: (k + 1) * T + T / 2            # falling clock edge of operation k
    rise = lambda k: (k + 1) * T
    # read 1 (op 3, row 0) and read 0 (op 4, row 63): clk falling -> dout
    res["t_cq_rise"] = cross(t, w["dout"], h, True, fall(3), fall(3) + T / 2) - fall(3)
    res["t_cq_fall"] = cross(t, w["dout"], h, False, fall(4), fall(4) + T / 2) - fall(4)
    res["t_wl"] = cross(t, w["wl0"], h, True, fall(3), fall(3) + T / 2) - fall(3)
    res["t_bl"] = cross(t, w["blb"], h, False, fall(3), fall(3) + T / 2) - fall(3)
    # precharge: after the rising edge that ends read op 3, BLB back above 90 %
    res["t_pre"] = cross(t, w["blb"], 0.9 * vdd, True, rise(4), rise(4) + T / 2) - rise(4)
    # write (op 5 writes 0 into row 0): storage node falls through half supply
    res["t_write"] = cross(t, w["q0"], h, False, fall(5), fall(5) + T / 2) - fall(5)
    # hold-latch opening: phi_d falling after the rising clock edge
    res["t_latch_open"] = cross(t, w["phi_d"], h, False, rise(4), rise(4) + T / 2) - rise(4)
    res["t_phi_fall"] = cross(t, w["phi"], h, False, rise(4), rise(4) + T / 2) - rise(4)
    # read disturb: highest voltage on the low storage node during the read of row 63 (stores 0 on Q after op 2)
    m = (t > fall(4)) & (t < rise(5))
    res["v_bump"] = float(w["q63"][m].max())
    res["i_avg"] = float(-np.trapezoid(w["ivdd"][(t > rise(1))], t[(t > rise(1))]) / (t[-1] - rise(1)))
    if keep:
        np.savez(os.path.join(OUT, f"{tag}.npz"), t=t, **w)
    return res


def _job(a):
    return a, run(*a)


PVT = [("tt", 27, 1.8), ("ss", 125, 1.62), ("ss", -40, 1.62), ("ff", -40, 1.98), ("ff", 125, 1.98),
       ("sf", 125, 1.62), ("sf", -40, 1.98), ("fs", 125, 1.62), ("fs", -40, 1.98)]


def cmd_corners(T=20e-9):
    with ProcessPoolExecutor(3) as ex:
        res = dict(ex.map(_job, [(c, t, v, T) for (c, t, v) in PVT]))
    rows = []
    for (c, t, v) in PVT:
        r = res[(c, t, v, T)]
        rows.append(dict(corner=c, temp=t, vdd=v, **r))
        if "t_wl" not in r:
            print(c, t, v, r)
            continue
        print(f"{c} {t:4d}C {v:.2f}V  {'PASS' if r['ok'] else 'FAIL'}  clk->dout {r['t_cq_rise']*1e9:5.2f}/{r['t_cq_fall']*1e9:5.2f} ns  "
              f"WL {r['t_wl']*1e9:4.2f}  BL {r['t_bl']*1e9:4.2f}  precharge {r['t_pre']*1e9:4.2f}  write {r['t_write']*1e9:4.2f}  "
              f"phi off {r['t_phi_fall']*1e9:4.2f} latch open {r['t_latch_open']*1e9:4.2f} ns  bump {r['v_bump']*1e3:4.0f} mV")
    json.dump(rows, open(os.path.join(OUT, "slice_corners.json"), "w"), indent=1)
    return rows


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "corners":
        cmd_corners()
    elif a == "waves":
        print(run(keep=True))
    elif a == "one":
        print(run(*sys.argv[2:3], keep=True))
