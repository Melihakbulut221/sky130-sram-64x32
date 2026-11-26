"""Thin ngspice wrapper: write a deck, run it in batch mode, read the results back."""
import os
import re
import subprocess

import numpy as np

from .paths import NGSPICE, SIM, SPICE_LIB

NFET = "sky130_fd_pr__nfet_01v8"
PFET = "sky130_fd_pr__pfet_01v8"
PFET_HVT = "sky130_fd_pr__pfet_01v8_hvt"
MODEL = {"n": NFET, "p": PFET, "ph": PFET_HVT}


def header(title, corner="tt", temp=27, vdd=1.8, seed=None):
    s = f"* {title}\n"
    if seed is not None:
        s += f".option seed={seed}\n"
    s += f'.lib "{SPICE_LIB}" {corner}\n.temp {temp}\n.param vdd={vdd}\n'
    return s


def mos(name, d, g, s, b, kind, w, l, m=1):
    """One MOSFET line. w and l in micrometres (the SKY130 library sets scale=1e-6)."""
    model = MODEL[kind]
    extra = f" m={m}" if m != 1 else ""
    return f"X{name} {d} {g} {s} {b} {model} w={w:g} l={l:g}{extra}\n"


def run(name, deck, timeout=14400, subdir=""):
    d = os.path.join(SIM, subdir) if subdir else SIM
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + ".spice"), "w") as f:
        f.write(deck)
    r = subprocess.run([NGSPICE, "-b", name + ".spice"], cwd=d,
                       capture_output=True, text=True, timeout=timeout)
    log = r.stdout + r.stderr
    with open(os.path.join(d, name + ".log"), "w") as f:
        f.write(log)
    return log


def load(name, subdir=""):
    """Read a `wrdata` file: columns are [x, v1, x, v2, ...] -> x, array(n_points, n_vectors)."""
    a = np.loadtxt(os.path.join(SIM, subdir, name))
    return a[:, 0], a[:, 1::2]


def meas(log, key):
    m = re.search(rf"^{key}\s*=\s*([-+0-9.eE]+)", log, re.M | re.I)
    return float(m.group(1)) if m else float("nan")
