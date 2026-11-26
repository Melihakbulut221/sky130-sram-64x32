"""6T bit cell: electrical characterisation (static noise margins, write margin, read current).

    python -m sram.bitcell size      # compare candidate sizings (nominal + corners)
    python -m sram.bitcell corners   # the chosen cell over process / voltage / temperature
    python -m sram.bitcell mc        # Monte Carlo mismatch on the chosen cell

All numbers come from DC sweeps in ngspice with the SKY130 BSIM4 models.
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np

from . import spice as S
from .models import slim_lib
from .paths import OUT


@dataclass(frozen=True)
class Sizing:
    """Widths / lengths in micrometres: pull-down, pass-gate (access), pull-up."""
    wpd: float = 0.65
    lpd: float = 0.15
    wpg: float = 0.42
    lpg: float = 0.15
    wpu: float = 0.42
    lpu: float = 0.15
    pu: str = "ph"         # "p" = pfet_01v8, "ph" = pfet_01v8_hvt (high threshold: less leakage, easier write)

    def tag(self):
        return f"pd{self.wpd:g}_{self.lpd:g}_pg{self.wpg:g}_{self.lpg:g}_{self.pu}{self.wpu:g}_{self.lpu:g}"


CELL = Sizing()            # the sizing used by the layout (see docs/bitcell.md for the comparison)


def _head(title, corner, temp, vdd, mm, seed):
    s = f"* {title}\n"
    if mm:
        s += f".option seed={seed}\n"
    s += f'.include "{slim_lib(corner, mm)}"\n.temp {temp}\n.param vdd={vdd}\n'
    s += ".option gmin=1e-13 reltol=1e-4 abstol=1e-13\n"
    return s


def _half(k, side, out, inp, wl, z: Sizing):
    """One inverter of the cell plus its access transistor (tied to a bit line at VDD)."""
    return (S.mos(f"pd{side}{k}", out, inp, "0", "0", "n", z.wpd, z.lpd)
            + S.mos(f"pu{side}{k}", out, inp, "vdd", "vdd", z.pu, z.wpu, z.lpu)
            + S.mos(f"pg{side}{k}", "vdd", wl, out, "0", "n", z.wpg, z.lpg))


def butterfly(z: Sizing, read=True, corner="tt", temp=27, vdd=1.8, n=1, seed=1, tag="x"):
    """Voltage transfer curves of both half cells. Returns vin, fl[n_pts, n], fr[n_pts, n]."""
    mm = n > 1
    d = _head("butterfly", corner, temp, vdd, mm, seed)
    d += "Vvdd vdd 0 {vdd}\nVin in 0 0\n" + f"Vwl wl 0 {vdd if read else 0}\n"
    for k in range(n):
        d += _half(k, "l", f"q{k}", "in", "wl", z) + _half(k, "r", f"qb{k}", "in", "wl", z)
    vec = " ".join(f"v(q{k})" for k in range(n)) + " " + " ".join(f"v(qb{k})" for k in range(n))
    d += f".save {vec}\n.control\ndc Vin 0 {vdd} {vdd / 360:.6f}\nset wr_singlescale\nwrdata {tag}.dat {vec}\nquit\n.endc\n.end\n"
    S.run(tag, d, subdir="bitcell")
    a = np.loadtxt(os.path.join(S.SIM, "bitcell", tag + ".dat"))
    return a[:, 0], a[:, 1:1 + n], a[:, 1 + n:1 + 2 * n]


def snm_from_curves(vin, fl, fr):
    """Static noise margin of each cell: side of the largest square inside each butterfly lobe.

    Curve 1 is (x, fl(x)), curve 2 is (fr(y), y). In coordinates rotated by 45 degrees the
    vertical distance between the two curves is the diagonal of the inscribed square.
    """
    out = []
    r2 = np.sqrt(2.0)
    ug = np.linspace(-vin[-1] / r2, vin[-1] / r2, 1500)
    for k in range(fl.shape[1]):
        u1, v1 = (vin - fl[:, k]) / r2, (vin + fl[:, k]) / r2
        u2, v2 = (fr[:, k] - vin) / r2, (fr[:, k] + vin) / r2
        o1, o2 = np.argsort(u1), np.argsort(u2)
        d = np.interp(ug, u1[o1], v1[o1]) - np.interp(ug, u2[o2], v2[o2])
        out.append((max(d.max(), 0) / r2, max((-d).max(), 0) / r2))
    return np.array(out)                      # [n, 2] : the two lobes


def write_margin(z: Sizing, corner="tt", temp=27, vdd=1.8, n=1, seed=1, tag="w"):
    """Bit-line write margin: with WL = VDD and BLB = VDD, the highest BL voltage that still flips a stored 1.

    Also returns the word-line write margin: VDD minus the lowest WL voltage that flips the cell with BL = 0.
    """
    mm = n > 1
    res = []
    for mode in ("bl", "wl"):
        d = _head("write margin " + mode, corner, temp, vdd, mm, seed)
        d += "Vvdd vdd 0 {vdd}\nVblb blb 0 {vdd}\n"
        d += ("Vbl bl 0 {vdd}\nVwl wl 0 {vdd}\n" if mode == "bl" else "Vbl bl 0 0\nVwl wl 0 0\n")
        for k in range(n):
            d += (S.mos(f"pdl{k}", f"q{k}", f"qb{k}", "0", "0", "n", z.wpd, z.lpd)
                  + S.mos(f"pul{k}", f"q{k}", f"qb{k}", "vdd", "vdd", z.pu, z.wpu, z.lpu)
                  + S.mos(f"pgl{k}", "bl", "wl", f"q{k}", "0", "n", z.wpg, z.lpg)
                  + S.mos(f"pdr{k}", f"qb{k}", f"q{k}", "0", "0", "n", z.wpd, z.lpd)
                  + S.mos(f"pur{k}", f"qb{k}", f"q{k}", "vdd", "vdd", z.pu, z.wpu, z.lpu)
                  + S.mos(f"pgr{k}", "blb", "wl", f"qb{k}", "0", "n", z.wpg, z.lpg))
            d += f".nodeset v(q{k})={vdd} v(qb{k})=0\n"
        vec = " ".join(f"v(q{k})" for k in range(n)) + " " + " ".join(f"v(qb{k})" for k in range(n))
        sweep = f"dc Vbl {vdd} 0 {-vdd / 720:.6f}" if mode == "bl" else f"dc Vwl 0 {vdd} {vdd / 720:.6f}"
        t = f"{tag}_{mode}"
        d += f".save {vec}\n.control\n{sweep}\nset wr_singlescale\nwrdata {t}.dat {vec}\nquit\n.endc\n.end\n"
        S.run(t, d, subdir="bitcell")
        a = np.loadtxt(os.path.join(S.SIM, "bitcell", t + ".dat"))
        x, q, qb = a[:, 0], a[:, 1:1 + n], a[:, 1 + n:1 + 2 * n]
        vals = []
        for k in range(n):
            idx = np.where(q[:, k] < qb[:, k])[0]
            if len(idx) == 0:
                vals.append(-1.0)                        # never flipped: write failure
            else:
                vals.append(x[idx[0]] if mode == "bl" else vdd - x[idx[0]])
        res.append(np.array(vals))
    return res[0], res[1]


def read_current(z: Sizing, corner="tt", temp=27, vdd=1.8, n=1, seed=1, tag="i"):
    """Cell read current (A) into the low storage node, bit line held at VDD; plus standby leakage of a cell."""
    mm = n > 1
    d = _head("read current", corner, temp, vdd, mm, seed)
    d += "Vvdd vdd 0 {vdd}\nVwl wl 0 {vdd}\nVvc vc 0 {vdd}\n"
    for k in range(n):
        d += f"Vbl{k} bl{k} 0 {{vdd}}\n"
        d += (S.mos(f"pdl{k}", f"q{k}", f"qb{k}", "0", "0", "n", z.wpd, z.lpd)
              + S.mos(f"pul{k}", f"q{k}", f"qb{k}", "vc", "vc", z.pu, z.wpu, z.lpu)
              + S.mos(f"pgl{k}", f"bl{k}", "wl", f"q{k}", "0", "n", z.wpg, z.lpg)
              + S.mos(f"pdr{k}", f"qb{k}", f"q{k}", "0", "0", "n", z.wpd, z.lpd)
              + S.mos(f"pur{k}", f"qb{k}", f"q{k}", "vc", "vc", z.pu, z.wpu, z.lpu)
              + S.mos(f"pgr{k}", "vdd", "wl", f"qb{k}", "0", "n", z.wpg, z.lpg))
        d += f".nodeset v(q{k})=0 v(qb{k})={vdd}\n"
    d += ".control\nop\n"
    for k in range(n):
        d += f"echo IREAD {k} $&i(Vbl{k}) $&v(q{k})\n"
    d += "alter Vwl dc = 0\nop\necho ILEAK $&i(Vvc)\nquit\n.endc\n.end\n"
    log = S.run(tag, d, subdir="bitcell")
    ir, vq, leak = [], [], float("nan")
    for line in log.splitlines():
        p = line.split()
        if p[:1] == ["IREAD"]:
            ir.append(-float(p[2]))
            vq.append(float(p[3]))
        elif p[:1] == ["ILEAK"]:
            leak = -float(p[1]) / n
    return np.array(ir), np.array(vq), leak


def summary(z: Sizing, corner="tt", temp=27, vdd=1.8, n=1, seed=1):
    tag = f"{z.tag()}_{corner}_{temp}_{vdd:g}_{n}_{seed}".replace(".", "p").replace("-", "m")
    vin, fl, fr = butterfly(z, False, corner, temp, vdd, n, seed, "bh_" + tag)
    hold = snm_from_curves(vin, fl, fr).min(axis=1)
    vin, fl, fr = butterfly(z, True, corner, temp, vdd, n, seed, "br_" + tag)
    read = snm_from_curves(vin, fl, fr).min(axis=1)
    wm_bl, wm_wl = write_margin(z, corner, temp, vdd, n, seed, "wm_" + tag)
    ir, vq, leak = read_current(z, corner, temp, vdd, n, seed, "ir_" + tag)
    return dict(corner=corner, temp=temp, vdd=vdd, hold=hold, read=read, wm_bl=wm_bl, wm_wl=wm_wl,
                iread=ir, vbump=vq, leak=leak)


def _job(args):
    return args, summary(*args)


CANDIDATES = {
    "A  PD 0.42  PG 0.42        ": Sizing(wpd=0.42),
    "B  PD 0.55  PG 0.42        ": Sizing(wpd=0.55),
    "C  PD 0.60  PG 0.42        ": Sizing(wpd=0.60),
    "D  PD 0.65  PG 0.42        ": Sizing(wpd=0.65),
    "E  PD 0.84  PG 0.42        ": Sizing(wpd=0.84),
    "F  PD 0.60  PG 0.42 L0.18  ": Sizing(wpd=0.60, lpg=0.18),
    "G  PD 0.42  PG 0.42 L0.25  ": Sizing(wpd=0.42, lpg=0.25),
}
PVT = [("tt", 27, 1.8), ("ss", 125, 1.62), ("ss", -40, 1.62), ("ff", -40, 1.98), ("ff", 125, 1.98),
       ("sf", 125, 1.62), ("sf", -40, 1.62), ("fs", 125, 1.62), ("fs", -40, 1.62), ("fs", 125, 1.98), ("sf", -40, 1.98)]


def cmd_size():
    jobs = [(z, c, t, v, 1, 1) for z in CANDIDATES.values() for (c, t, v) in PVT]
    with ProcessPoolExecutor(4) as ex:
        res = dict(ex.map(_job, jobs))
    print(f"{'sizing':28s} {'hold':>6s} {'read':>6s} {'wmBL':>6s} {'wmWL':>6s} {'Iread':>7s} | worst over PVT: read / wmBL / wmWL / Iread")
    table = {}
    for name, z in CANDIDATES.items():
        r0 = res[(z, "tt", 27, 1.8, 1, 1)]
        allr = [res[(z, c, t, v, 1, 1)] for (c, t, v) in PVT]
        w = dict(read=min(r["read"][0] for r in allr), hold=min(r["hold"][0] for r in allr),
                 wm_bl=min(r["wm_bl"][0] for r in allr), wm_wl=min(r["wm_wl"][0] for r in allr),
                 iread=min(r["iread"][0] for r in allr))
        print(f"{name:28s} {r0['hold'][0]*1e3:6.0f} {r0['read'][0]*1e3:6.0f} {r0['wm_bl'][0]*1e3:6.0f} "
              f"{r0['wm_wl'][0]*1e3:6.0f} {r0['iread'][0]*1e6:7.1f} | {w['read']*1e3:5.0f} {w['wm_bl']*1e3:5.0f} "
              f"{w['wm_wl']*1e3:5.0f} {w['iread']*1e6:6.1f}")
        table[name.strip()] = dict(nominal={k: float(np.ravel(r0[k])[0]) for k in ("hold", "read", "wm_bl", "wm_wl", "iread")},
                                   worst=w)
    json.dump(table, open(os.path.join(OUT, "bitcell_sizing.json"), "w"), indent=1)




def cmd_corners(z=CELL, quiet=False):
    with ProcessPoolExecutor(4) as ex:
        res = dict(ex.map(_job, [(z, c, t, v, 1, 1) for (c, t, v) in PVT]))
    rows = []
    for (c, t, v) in PVT:
        r = res[(z, c, t, v, 1, 1)]
        rows.append(dict(corner=c, temp=t, vdd=v, hold=float(r["hold"][0]), read=float(r["read"][0]),
                         wm_bl=float(r["wm_bl"][0]), wm_wl=float(r["wm_wl"][0]), iread=float(r["iread"][0]),
                         vbump=float(r["vbump"][0]), leak=float(r["leak"])))
        if not quiet:
            print(f"{c} {t:4d}C {v:.2f}V  hold {rows[-1]['hold']*1e3:4.0f}  read {rows[-1]['read']*1e3:4.0f}  "
                  f"wmBL {rows[-1]['wm_bl']*1e3:4.0f}  wmWL {rows[-1]['wm_wl']*1e3:4.0f}  Iread {rows[-1]['iread']*1e6:6.1f} uA  "
                  f"bump {rows[-1]['vbump']*1e3:4.0f} mV  leak {rows[-1]['leak']*1e12:8.1f} pA")
    json.dump(rows, open(os.path.join(OUT, "bitcell_corners.json"), "w"), indent=1)
    return rows


MC_PVT = [("tt", 27, 1.8), ("fs", 125, 1.62), ("fs", -40, 1.98), ("sf", -40, 1.62), ("ss", -40, 1.62)]


def cmd_mc(z=CELL, n=250, seeds=(1, 2, 3, 4), name="bitcell_mc"):
    jobs = [(z, c, t, v, n, s) for (c, t, v) in MC_PVT for s in seeds]
    with ProcessPoolExecutor(3) as ex:
        res = dict(ex.map(_job, jobs))
    out = {}
    for (c, t, v) in MC_PVT:
        cat = {k: np.concatenate([res[(z, c, t, v, n, s)][k] for s in seeds]) for k in ("hold", "read", "wm_bl", "wm_wl", "iread")}
        key = f"{c}_{t}_{v:g}"
        out[key] = {k: dict(mean=float(a.mean()), sigma=float(a.std(ddof=1)), min=float(a.min()),
                            n=int(len(a)), fails=int((a <= 0).sum())) for k, a in cat.items()}
        np.savez(os.path.join(OUT, f"{name}_{key}.npz"), **cat)
        line = f"{key:14s}"
        for k in ("hold", "read", "wm_bl", "wm_wl"):
            m, sg = out[key][k]["mean"], out[key][k]["sigma"]
            line += f" | {k} {m*1e3:4.0f} +- {sg*1e3:4.1f} mV  ({m/sg:4.1f} sigma, min {out[key][k]['min']*1e3:4.0f})"
        line += f" | Iread {out[key]['iread']['mean']*1e6:.0f} +- {out[key]['iread']['sigma']*1e6:.1f} uA"
        print(line)
    json.dump(out, open(os.path.join(OUT, name + ".json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "size":
        cmd_size()
    elif a == "corners":
        cmd_corners()
    elif a == "mc":
        cmd_mc()
    elif a == "mccmp":
        for nm in ("D", "E"):
            z = [v for k, v in CANDIDATES.items() if k.startswith(nm)][0]
            z = Sizing(wpd=z.wpd, pu="ph")
            print("==", nm, z)
            cmd_mc(z, n=100, seeds=(1, 2, 3), name="mccmp_" + nm)
