"""Figures (matplotlib, dark theme) built from the simulation results in out/.

Every function returns a PIL image sized for the content area of a video frame; the same
images are saved for the documentation with `python -m video.figs`.
"""
import io
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image

from . import style as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
C = {k: tuple(v / 255 for v in getattr(S, k)) for k in
     ("BG", "PANEL", "PANEL2", "LINE", "FG", "MUTED", "BLUE", "GREEN", "ORANGE", "RED", "PURPLE", "CYAN", "YELLOW")}

plt.rcParams.update({
    "figure.facecolor": C["BG"], "axes.facecolor": C["PANEL"], "savefig.facecolor": C["BG"],
    "axes.edgecolor": C["LINE"], "axes.labelcolor": C["FG"], "text.color": C["FG"],
    "xtick.color": C["MUTED"], "ytick.color": C["MUTED"], "grid.color": C["LINE"],
    "font.size": 19, "axes.titlesize": 22, "axes.labelsize": 19, "legend.fontsize": 17,
    "font.family": "Helvetica Neue", "axes.grid": True, "grid.alpha": 0.7, "lines.linewidth": 2.6,
    "legend.facecolor": C["PANEL2"], "legend.edgecolor": C["LINE"], "axes.titleweight": "bold",
})


def to_img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def fig_axes(n=1, w=1820, h=800, **kw):
    fig, ax = plt.subplots(1, n, figsize=(w / 100, h / 100), **kw)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.9, bottom=0.13, wspace=0.22)
    return fig, ax


def canvas(w=1820, h=800, xlim=(0, 182), ylim=(0, 80)):
    fig = plt.figure(figsize=(w / 100, h / 100))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.axis("off"); ax.set_facecolor(C["BG"])
    return fig, ax


def box(ax, x, y, w, h, text, color="BLUE", sub=None, fs=21, fill=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.2", lw=2.4,
                                ec=C[color], fc=(*C[color], 0.16) if fill else "none"))
    ax.text(x + w / 2, y + h / 2 + (1.5 if sub else 0), text, ha="center", va="center", fontsize=fs, weight="bold", color=C["FG"])
    if sub:
        ax.text(x + w / 2, y + h / 2 - 2.6, sub, ha="center", va="center", fontsize=fs - 6, color=C["MUTED"])


def arrow(ax, p, q, color="FG", lw=2.4, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=22, lw=lw, color=C[color],
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


def line(ax, pts, color="FG", lw=2.4, ls="-"):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=C[color], lw=lw, ls=ls, solid_capstyle="round")


# ----------------------------------------------------------------------------- transistor symbol
def mos(ax, x, y, typ="n", name=None, size=None, col="FG", flip=False, gate_len=3.0):
    """Vertical MOSFET symbol centred at (x, y): drain up, source down, gate to the left (right if flip)."""
    s = -1 if flip else 1
    c = C[col]
    ax.plot([x, x], [y + 2.2, y + 5], color=c, lw=2.4)
    ax.plot([x, x], [y - 2.2, y - 5], color=c, lw=2.4)
    ax.plot([x, x - s * 1.6], [y + 2.2, y + 2.2], color=c, lw=2.4)
    ax.plot([x, x - s * 1.6], [y - 2.2, y - 2.2], color=c, lw=2.4)
    ax.plot([x - s * 1.6, x - s * 1.6], [y - 2.8, y + 2.8], color=c, lw=3.2)
    ax.plot([x - s * 2.5, x - s * 2.5], [y - 2.2, y + 2.2], color=c, lw=3.2)
    gx = x - s * 2.5
    if typ == "p":
        ax.add_patch(plt.Circle((gx - s * 0.55, y), 0.55, ec=c, fc=C["BG"], lw=2.2, zorder=5))
        gx -= s * 1.1
    ax.plot([gx, gx - s * gate_len], [y, y], color=c, lw=2.4)
    if name:
        ax.text(x + s * 1.2, y + (0.9 if size else 0), name, ha="left" if s > 0 else "right", va="center", fontsize=17, weight="bold", color=c)
    if size:
        ax.text(x + s * 1.2, y - 1.6, size, ha="left" if s > 0 else "right", va="center", fontsize=14, color=C["MUTED"])
    return gx - s * gate_len


# ----------------------------------------------------------------------------- 6T cell schematic
def cell_schematic(highlight=None, sizes=True):
    """6T cell. highlight: None | 'hold' | 'read' | 'write'."""
    from sram.bitcell import CELL as z
    fig, ax = canvas()
    sz = (lambda w: f"{w:g} / 0.15") if sizes else (lambda w: None)
    xl, xr, yn, yp = 70, 112, 30, 54
    hot = {"read": "ORANGE", "write": "RED"}.get(highlight, "FG")
    # rails
    line(ax, [(52, 66), (130, 66)], "RED"); ax.text(131, 66, "VDD", va="center", color=C["RED"], fontsize=19, weight="bold")
    line(ax, [(52, 18), (130, 18)], "BLUE"); ax.text(131, 18, "GND", va="center", color=C["BLUE"], fontsize=19, weight="bold")
    # inverters
    gl_p = mos(ax, xl, yp, "p", "PU", sz(z.wpu), flip=True, gate_len=6)
    gl_n = mos(ax, xl, yn, "n", "PD", sz(z.wpd), flip=True, gate_len=7.1)
    gr_p = mos(ax, xr, yp, "p", "PU", sz(z.wpu), gate_len=6)
    gr_n = mos(ax, xr, yn, "n", "PD", sz(z.wpd), gate_len=7.1)
    for x in (xl, xr):
        line(ax, [(x, yp + 5), (x, 66)]); line(ax, [(x, yn - 5), (x, 18)]); line(ax, [(x, yn + 5), (x, yp - 5)])
    ym = 42
    # cross coupling: gate of the left inverter (at x = gl) to node QB (right), and vice versa
    gxl, gxr = xl + 9.7, xr - 9.7
    line(ax, [(gxl, yn), (gxl, yp)]); line(ax, [(gxr, yn), (gxr, yp)])
    line(ax, [(gxl, ym + 2.5), (xr, ym + 2.5)], "GREEN", 2.8)       # QB drives the left gates
    line(ax, [(gxr, ym - 2.5), (xl, ym - 2.5)], "YELLOW", 2.8)      # Q drives the right gates
    ax.plot([xl], [ym - 2.5], "o", color=C["YELLOW"], ms=9); ax.plot([xr], [ym + 2.5], "o", color=C["GREEN"], ms=9)
    ax.plot([gxl], [ym + 2.5], "o", color=C["GREEN"], ms=7); ax.plot([gxr], [ym - 2.5], "o", color=C["YELLOW"], ms=7)
    ax.text(xl - 1.5, ym + 1.2, "Q", ha="right", fontsize=24, weight="bold", color=C["YELLOW"])
    ax.text(xr + 1.5, ym + 3.4, "QB", ha="left", fontsize=24, weight="bold", color=C["GREEN"])
    # access transistors (drawn horizontally): simple symbols
    for side, x0, node_y, name in ((-1, xl, ym - 2.5, "BL"), (1, xr, ym + 2.5, "BLB")):
        xa = x0 + side * 22
        c = C[hot if highlight in ("read", "write") else "FG"]
        line(ax, [(x0, node_y), (xa - side * 3, node_y)])
        ax.plot([xa - side * 3, xa - side * 3], [node_y, ym - 9], color=C["FG"], lw=2.4) if False else None
        # channel
        ax.plot([xa - 3, xa + 3], [node_y, node_y], color=c, lw=3.2)
        ax.plot([xa - 3, xa + 3], [node_y + 1.0, node_y + 1.0], color=c, lw=3.2)
        ax.plot([xa, xa], [node_y + 1.0, 60], color=c, lw=2.4)
        line(ax, [(xa + side * 3, node_y), (xa + side * 12, node_y)])
        ax.text(xa, node_y - 3.4, "PG", ha="center", fontsize=17, weight="bold", color=c)
        if sizes:
            ax.text(xa, node_y - 5.8, f"{z.wpg:g} / 0.15", ha="center", fontsize=14, color=C["MUTED"])
        # bit line
        xb = xa + side * 12
        line(ax, [(xb, 12), (xb, 72)], "PURPLE", 3.2)
        ax.text(xb, 74, name, ha="center", fontsize=22, weight="bold", color=C["PURPLE"])
    # word line
    line(ax, [(30, 60), (152, 60)], "CYAN", 3.2)
    ax.text(153, 60, "WL", va="center", fontsize=22, weight="bold", color=C["CYAN"])
    notes = {
        None: "Two cross-coupled inverters hold one bit; two pass gates connect it to the bit lines.",
        "hold": "Hold: word line low. The inverters keep Q and QB at opposite rails.",
        "read": "Read: both bit lines start at VDD, word line high. The side that stores 0 pulls its bit line down.",
        "write": "Write: one bit line is forced to 0. The pass gate must overpower the pull-up on that side.",
    }
    ax.text(91, 5, notes[highlight], ha="center", fontsize=21, color=C["MUTED"])
    return to_img(fig)


# ----------------------------------------------------------------------------- butterfly / SNM
def _square(vin, fl, fr):
    """Largest square in each lobe: returns [(x0, y0, side), ...]."""
    r2 = np.sqrt(2.0)
    ug = np.linspace(-vin[-1] / r2, vin[-1] / r2, 3000)
    u1, v1 = (vin - fl) / r2, (vin + fl) / r2
    u2, v2 = (fr - vin) / r2, (fr + vin) / r2
    o1, o2 = np.argsort(u1), np.argsort(u2)
    a, b = np.interp(ug, u1[o1], v1[o1]), np.interp(ug, u2[o2], v2[o2])
    out = []
    for sign in (1, -1):
        d = sign * (a - b)
        k = int(np.argmax(d))
        lo, hi = min(a[k], b[k]), max(a[k], b[k])
        p_lo = ((ug[k] + lo) / r2, (lo - ug[k]) / r2)
        side = (hi - lo) / r2
        out.append((p_lo[0], p_lo[1], side))
    return out


def butterfly():
    from sram import bitcell as B
    fig, axs = fig_axes(2)
    for ax, read, title in ((axs[0], False, "Hold (word line off)"), (axs[1], True, "Read (word line on, bit lines at VDD)")):
        for (corner, temp, vdd, col, lab) in (("tt", 27, 1.8, "BLUE", "typical, 27 °C, 1.80 V"),
                                              ("sf", 125, 1.62, "ORANGE", "fast n / slow p, 125 °C, 1.62 V")):
            vin, fl, fr = B.butterfly(B.CELL, read, corner, temp, vdd, tag=f"fig_b{int(read)}_{corner}")
            fl, fr = fl[:, 0], fr[:, 0]
            ax.plot(vin, fl, color=C[col], label=lab)
            ax.plot(fr, vin, color=C[col], ls="--")
            sq = min(_square(vin, fl, fr), key=lambda s: s[2])
            ax.add_patch(Rectangle((sq[0], sq[1]), sq[2], sq[2], fc=(*C[col], 0.25), ec=C[col], lw=2))
            ax.text(sq[0] + sq[2] / 2, sq[1] + sq[2] / 2, f"{sq[2] * 1000:.0f} mV", ha="center", va="center",
                    fontsize=17, weight="bold", color=C["FG"])
        ax.set_title(title); ax.set_xlabel("V(QB)  [V]"); ax.set_ylabel("V(Q)  [V]")
        ax.set_aspect("equal"); ax.set_xlim(0, 1.85); ax.set_ylim(0, 1.85)
    h, l = axs[0].get_legend_handles_labels()
    fig.subplots_adjust(left=0.07, right=0.78, wspace=0.3)
    fig.legend(h, l, loc="upper left", bbox_to_anchor=(0.785, 0.88), fontsize=15)
    fig.text(0.79, 0.62, "solid: left inverter\ndashed: right inverter, mirrored\n\nsquare: static noise margin,\nthe largest noise voltage that\ncannot flip the cell", fontsize=15, color=C["MUTED"], va="top")
    return to_img(fig)


def sizing_bars():
    t = json.load(open(os.path.join(OUT, "bitcell_sizing.json")))
    names = list(t)
    fig, ax = fig_axes(1)
    x = np.arange(len(names))
    r = [t[n]["worst"]["read"] * 1e3 for n in names]
    w = [t[n]["worst"]["wm_wl"] * 1e3 for n in names]
    ax.bar(x - 0.2, r, 0.38, color=C["BLUE"], label="read noise margin, worst corner")
    ax.bar(x + 0.2, w, 0.38, color=C["ORANGE"], label="write margin, worst corner")
    for i, (a, b) in enumerate(zip(r, w)):
        ax.text(i - 0.2, a + 6, f"{a:.0f}", ha="center", fontsize=16); ax.text(i + 0.2, b + 6, f"{b:.0f}", ha="center", fontsize=16)
    ax.set_xticks(x); ax.set_xticklabels([" ".join(n.split()[1:]).replace("PD", "PD\n").replace(" PG", "\nPG") for n in names], fontsize=15)
    ax.set_ylabel("mV"); ax.set_title("Cell sizing trade-off: a wider pull-down helps reading and hurts writing")
    k = [i for i, n in enumerate(names) if n.startswith("D")][0]
    ax.axvspan(k - 0.5, k + 0.5, color=(*C["GREEN"], 0.14)); ax.text(k, max(r + w) * 1.06, "chosen", ha="center", color=C["GREEN"], weight="bold")
    ax.set_ylim(0, max(r + w) * 1.22); ax.legend(loc="upper right", ncol=2)
    return to_img(fig)


def mc_hist():
    j = json.load(open(os.path.join(OUT, "bitcell_mc.json")))
    fig, axs = fig_axes(2)
    for ax, key, title, pvt in ((axs[0], "read", "Read noise margin", "sf_-40_1.62"), (axs[1], "wm_wl", "Write margin", "fs_125_1.62")):
        for p, col in (("tt_27_1.8", "BLUE"), (pvt, "ORANGE")):
            a = np.load(os.path.join(OUT, f"bitcell_mc_{p}.npz"))[key] * 1e3
            m, s = a.mean(), a.std(ddof=1)
            c, t_, v = p.split("_")
            ax.hist(a, bins=np.arange(0, a.max() + 10, 5), color=(*C[col], 0.8), label=f"{c}, {t_} °C, {v} V:  {m:.0f} ± {s:.1f} mV  ({m / s:.0f} σ)")
        ax.set_title(f"{title}: {j['tt_27_1.8'][key]['n']} mismatch samples"); ax.set_xlabel("mV"); ax.set_ylabel("cells")
        ax.set_xlim(0, None); ax.legend(loc="upper left")
        ax.axvline(0, color=C["RED"], lw=3); ax.text(8, ax.get_ylim()[1] * 0.5, "failure", color=C["RED"], rotation=90, va="center", fontsize=17)
    return to_img(fig)


# ----------------------------------------------------------------------------- waveforms
LABEL = {"wl21": "WL[21]", "wl42": "WL[42]", "bl0": "BL[0]", "blb0": "BLB[0]", "q_42_0": "Q", "qb_42_0": "QB",
         "dout0": "dout[0]", "dout1": "dout[1]"}


def waves(npz, t0, t1, title="", rows=None, T=20e-9, marks=()):
    d = np.load(npz)
    t = d["t"] * 1e9
    rows = rows or [("clk", [("clk", "MUTED")]), ("word line", [("wl0", "CYAN")]), ("bit lines", [("bl", "PURPLE"), ("blb", "ORANGE")]),
                    ("cell", [("q0", "YELLOW"), ("qb0", "GREEN")]), ("dout", [("dout", "BLUE")])]
    fig, axs = plt.subplots(len(rows), 1, figsize=(18.2, 8.0), sharex=True)
    fig.subplots_adjust(left=0.09, right=0.985, top=0.93, bottom=0.1, hspace=0.18)
    m = (t >= t0) & (t <= t1)
    for ax, (name, sigs) in zip(axs, rows):
        for s, col in sigs:
            if s in d:
                ax.plot(t[m], d[s][m], color=C[col], label=LABEL.get(s, s))
        ax.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=17)
        ax.set_ylim(-0.15, 2.05); ax.set_yticks([0, 1.8])
        if len(sigs) > 1:
            ax.legend(loc="center right", ncol=len(sigs), fontsize=14, framealpha=0.9)
        for (tm, txt) in marks:
            ax.axvline(tm, color=C["LINE"], lw=1.5, ls="--")
    for (tm, txt) in marks:
        axs[0].text(tm + 0.15, 2.15, txt, fontsize=15, color=C["FG"], va="bottom")
    axs[-1].set_xlabel("time  [ns]")
    if title:
        fig.suptitle(title, fontsize=22, weight="bold", y=0.995)
    return to_img(fig)


def corner_bars(path=None, title="Clock falling edge to data out"):
    rows = json.load(open(path or os.path.join(OUT, "slice_corners.json")))
    rows = [r for r in rows if "t_cq_rise" in r]
    fig, ax = fig_axes(1)
    x = np.arange(len(rows))
    v = [max(r["t_cq_rise"], r["t_cq_fall"]) * 1e9 for r in rows]
    cols = [C["GREEN"] if r["ok"] else C["RED"] for r in rows]
    ax.bar(x, v, 0.6, color=cols)
    for i, a in enumerate(v):
        ax.text(i, a + 0.04, f"{a:.2f}", ha="center", fontsize=17)
    ax.set_xticks(x); ax.set_xticklabels([f"{r['corner']}\n{r['temp']} °C\n{r['vdd']:.2f} V" for r in rows], fontsize=15)
    ax.set_ylabel("ns"); ax.set_title(title); ax.set_ylim(0, max(v) * 1.15)
    return to_img(fig)


# ----------------------------------------------------------------------------- architecture and timing
def architecture(highlight=None):
    fig, ax = canvas()
    hl = lambda k, c: c if (highlight in (None, k)) else "LINE"
    box(ax, 62, 30, 96, 42, "6T bit-cell array", hl("array", "YELLOW"), "64 word lines × 32 bit-line pairs  ·  full custom", fs=25)
    box(ax, 30, 30, 24, 42, "row\ndecoder", hl("row", "CYAN"), None)
    ax.text(42, 34, "64 AND gates", ha="center", fontsize=14, color=C["MUTED"])
    box(ax, 62, 13, 96, 11, "column circuits", hl("col", "PURPLE"), "tri-state drivers (precharge, write, keeper)  ·  sense inverters  ·  output latches")
    box(ax, 6, 44, 18, 28, "input\nflip-flops\n+ hold\nlatches", hl("in", "BLUE"), None, fs=18)
    box(ax, 6, 13, 48, 11, "clock phases", hl("clk", "GREEN"), "clock gate  ·  delay  ·  buffers")
    for y in (40, 51, 62):
        arrow(ax, (54, y), (62, y), "CYAN")
    ax.text(58, 65.5, "WL", ha="center", fontsize=16, color=C["CYAN"], weight="bold")
    for x in (80, 110, 140):
        arrow(ax, (x, 30), (x, 24), "PURPLE", style="<|-|>")
    ax.text(84, 26.2, "BL / BLB", fontsize=16, color=C["PURPLE"], weight="bold")
    arrow(ax, (24, 58), (30, 58), "BLUE"); arrow(ax, (15, 44), (15, 24), "GREEN", style="<|-")
    arrow(ax, (42, 24), (42, 30), "GREEN"); arrow(ax, (54, 18.5), (62, 18.5), "GREEN")
    ax.text(15, 74.5, "en · we · wmask · addr · din", fontsize=15, color=C["MUTED"], ha="center")
    arrow(ax, (110, 13), (110, 6), "BLUE"); ax.text(112, 8, "dout[31:0]", fontsize=17, color=C["BLUE"], weight="bold")
    arrow(ax, (15, 6), (15, 13), "GREEN"); ax.text(17, 8, "clk", fontsize=17, color=C["GREEN"], weight="bold")
    ax.text(170, 51, "custom\nlayout", ha="center", fontsize=17, color=C["YELLOW"])
    ax.text(170, 18.5, "standard\ncells", ha="center", fontsize=17, color=C["PURPLE"])
    return to_img(fig)


def timing_diagram():
    fig, ax = canvas()
    x0, x1 = 30, 172
    T = (x1 - x0) / 2.25
    def wave(y, pts, col, name, lw=2.8):
        line(ax, [(x0 + a * T, y + b * 5) for a, b in pts], col, lw)
        ax.text(x0 - 2.5, y + 2.5, name, ha="right", va="center", fontsize=19, weight="bold", color=C[col])
    e = 0.03
    wave(66, [(0, 0), (0.1, 0), (0.1 + e, 1), (0.6, 1), (0.6 + e, 0), (1.1, 0), (1.1 + e, 1), (1.6, 1), (1.6 + e, 0), (2.1, 0), (2.1 + e, 1), (2.25, 1)], "MUTED", "clk")
    wave(56, [(0, 0.5), (0.02, 1), (0.98, 1), (1.0, 0.5), (1.02, 1), (1.98, 1), (2.0, 0.5), (2.02, 1), (2.25, 1)], "BLUE", "addr, din, we")
    wave(56, [(0, 0.5), (0.02, 0), (0.98, 0), (1.0, 0.5), (1.02, 0), (1.98, 0), (2.0, 0.5), (2.02, 0), (2.25, 0)], "BLUE", "")
    wave(46, [(0, 0), (0.64, 0), (0.67, 1), (1.14, 1), (1.17, 0), (1.64, 0), (1.67, 1), (2.14, 1), (2.17, 0), (2.25, 0)], "CYAN", "word line")
    wave(36, [(0, 1), (0.70, 1), (0.82, 0.05), (1.17, 0.05), (1.3, 1), (1.7, 1), (1.76, 0), (2.17, 0), (2.25, 0.6)], "PURPLE", "bit line")
    wave(26, [(0, 0.5), (0.02, 1), (0.86, 1), (0.9, 0.5), (0.92, 0), (2.25, 0)], "GREEN", "dout")
    wave(26, [(0, 0.5), (0.02, 0), (0.86, 0), (0.9, 0.5), (0.92, 1), (2.25, 1)], "GREEN", "")
    for a, txt in ((0.1, "sample inputs"), (0.6, "evaluate"), (1.1, "sample inputs"), (1.6, "evaluate")):
        ax.plot([x0 + a * T + 0.7] * 2, [20, 73], color=C["LINE"], lw=1.6, ls="--")
    for a, b, txt, col in ((0.1, 0.6, "clk high:\nprecharge + decode", "ORANGE"), (0.6, 1.1, "clk low:\nread", "GREEN"),
                           (1.1, 1.6, "clk high:\nprecharge + decode", "ORANGE"), (1.6, 2.1, "clk low:\nwrite", "RED")):
        ax.add_patch(Rectangle((x0 + a * T + 0.7, 8), (b - a) * T, 9, fc=(*C[col], 0.18), ec=C[col], lw=1.8))
        ax.text(x0 + (a + b) / 2 * T + 0.7, 12.5, txt, ha="center", va="center", fontsize=17, color=C["FG"])
    ax.text(x0 + 1.5 * T, 21.5, "read data valid before the next rising edge", fontsize=16, color=C["GREEN"], ha="center")
    ax.text(91, 76.5, "One clock, two phases, no self-timed pulses", ha="center", fontsize=24, weight="bold")
    return to_img(fig)


def save_all():
    d = os.path.join(ROOT, "docs", "img")
    os.makedirs(d, exist_ok=True)
    jobs = {"cell_schematic": cell_schematic, "architecture": architecture, "timing": timing_diagram,
            "butterfly": butterfly, "sizing": sizing_bars, "mc": mc_hist, "corners_slice": corner_bars}
    for name, fn in jobs.items():
        try:
            fn().save(os.path.join(d, name + ".png"))
            print("ok", name)
        except Exception as e:                                   # a result file may not exist yet
            print("skip", name, repr(e)[:120])


if __name__ == "__main__":
    save_all()
