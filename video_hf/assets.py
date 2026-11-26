"""Pictures and data for the HyperFrames compositions.

Layout pictures are rendered with KLayout (no window); chart data comes from the simulation
results in out/. Everything a composition needs ends up in <project>/assets/.
"""
import json
import os

import numpy as np

from video import shots as SH
from video import script as L

W, H = 1920, 1080
PANEL = (1680, 630)            # layout panel for the cell close-ups


def _save(im, path, quality=None):
    if path.endswith(".jpg"):
        im.convert("RGB").save(path, quality=quality or 90)
    else:
        im.save(path)


def px(act, size, x, y):
    """Layout micrometres -> pixel position inside a picture rendered for the box `act`."""
    l, b, r, t = act
    return (x - l) / (r - l) * size[0], (t - y) / (t - b) * size[1]


def layout_pictures(d):
    """Render all layout pictures; return {name: (file, actual box, size)}."""
    out = {}

    def shot(name, box, size=(W, H), keys=SH.ALL, margin=0.04, ext="jpg"):
        im, act = L.SHOTS.image(SH.fit(box, size, margin), size, keys)
        f = f"{name}.{ext}"
        _save(im, os.path.join(d, f), 92)
        out[name] = dict(file="assets/" + f, box=act, size=size)

    # the cell, layer by layer (cumulative), in a wide panel
    cb = (L.CELL[0] - 0.4, L.CELL[1] - 0.62, L.CELL[2] + 0.4, L.CELL[3] + 0.62)
    stacks = [("cell_l1", ("well", "diff")), ("cell_l2", ("well", "diff", "poly")),
              ("cell_l3", ("well", "diff", "poly", "con", "li")), ("cell_l4", ("well", "diff", "poly", "con", "li", "m1")),
              ("cell_l5", None)]
    for name, layers in stacks:
        shot(name, cb, PANEL, SH.ALL if layers is None else SH.layers(*layers), margin=0.0, ext="png")
    shot("z4_chip", L.FULL, margin=0.03)
    # deep-zoom chains: nested pictures, each rendered with twice the field it is shown with, so a level
    # always fills the frame until the next one takes over
    out["chain_cell"] = zoom_chain(d, "zc", SH.fit((L.CELL[0] - 0.3, L.CELL[1] - 0.2, L.CELL[2] + 0.3, L.CELL[3] + 0.2), (W, H), 0.02),
                                   SH.fit(L.MACRO, (W, H), 0.03))
    out["chain_cols"] = zoom_chain(d, "zk", SH.fit((L.MX + 6, L.MY - 22, L.MX + 50, L.MY + 4), (W, H), 0.02), SH.fit(L.FULL, (W, H), 0.03))
    return out


def zoom_chain(d, name, small, large, over=2.0):
    """Levels between two 16:9 boxes (about a factor of two apart), zooming about one fixed point."""
    import math
    w0, w1 = small[2] - small[0], large[2] - large[0]
    n = max(1, math.ceil(math.log2(w1 / w0)))
    c0 = ((small[0] + small[2]) / 2, (small[1] + small[3]) / 2)
    c1 = ((large[0] + large[2]) / 2, (large[1] + large[3]) / 2)
    fix = tuple((c1[k] * w0 - c0[k] * w1) / (w0 - w1) for k in (0, 1))
    levels = []
    for i in range(n + 1):
        w = w0 * (w1 / w0) ** (i / n)
        h = w * H / W
        cx, cy = (fix[k] + (c0[k] - fix[k]) * w / w0 for k in (0, 1))
        box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        ov = 1.0 if i == n else over
        ibox = (cx - w * ov / 2, cy - h * ov / 2, cx + w * ov / 2, cy + h * ov / 2)
        size = (W, H) if i == n else (3200, 1800)
        im, act = L.SHOTS.image(ibox, size, SH.ALL)
        f = f"{name}{i}.jpg"
        _save(im, os.path.join(d, f), 88)
        levels.append(dict(file="assets/" + f, box=box, ibox=act))
    return levels


def chart_data():
    """Curves and tables for the animated charts, reduced to what the pictures need."""
    from sram import bitcell as B
    out = {}
    bf = {}
    for read in (False, True):
        for (corner, temp, vdd) in (("tt", 27, 1.8), ("sf", 125, 1.62)):
            vin, fl, fr = B.butterfly(B.CELL, read, corner, temp, vdd, tag=f"hf_b{int(read)}_{corner}")
            idx = np.linspace(0, len(vin) - 1, 121).astype(int)
            snm = float(B.snm_from_curves(vin, fl, fr).min())
            from video.figs import _square
            sq = min(_square(vin, fl[:, 0], fr[:, 0]), key=lambda s: s[2])
            bf[f"{'read' if read else 'hold'}_{corner}"] = dict(
                vdd=vdd, vin=[round(float(v), 4) for v in vin[idx]], fl=[round(float(v), 4) for v in fl[idx, 0]],
                fr=[round(float(v), 4) for v in fr[idx, 0]], snm=snm, sq=[float(v) for v in sq])
    out["butterfly"] = bf
    t = json.load(open(os.path.join(L.OUT, "bitcell_sizing.json")))
    out["sizing"] = [dict(name=k, read=v["worst"]["read"] * 1e3, write=v["worst"]["wm_wl"] * 1e3) for k, v in t.items()]
    mc = {}
    for key in ("tt_27_1.8", "sf_-40_1.62"):
        a = np.load(os.path.join(L.OUT, f"bitcell_mc_{key}.npz"))["read"] * 1e3
        hist, edges = np.histogram(a, bins=np.arange(0, 420, 5))
        mc[key] = dict(hist=hist.tolist(), lo=0, step=5, mean=float(a.mean()), sigma=float(a.std(ddof=1)), n=int(len(a)))
    out["mc"] = mc
    d = np.load(os.path.join(L.OUT, "chipc_tt.npz"))
    tt = d["t"] * 1e9
    m = (tt >= 58) & (tt <= 124)
    ts = np.linspace(58, 124, 700)
    out["waves"] = dict(t=[round(float(v), 3) for v in ts],
                        sig={k: [round(float(v), 3) for v in np.interp(ts, tt[m], d[k][m])]
                             for k in ("clk", "wl21", "wl42", "bl0", "blb0", "q_42_0", "qb_42_0", "dout0", "dout1")})
    out["results"] = dict(L.R)
    return out
