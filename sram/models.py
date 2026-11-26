"""Slim SKY130 model libraries.

The stock sky130.lib.spice pulls in every device of the process (high voltage, RF, bipolar,
flash ...), which costs ngspice many seconds per run. This SRAM only uses three devices
(nfet_01v8, pfet_01v8 and the pfet_01v8_hvt of the standard cells), so we build a small
library per corner that includes exactly the same model files for just those devices.
"""
import os
import re

from .paths import PDK_ROOT, SIM

NG = os.path.join(PDK_ROOT, "sky130A", "libs.tech", "ngspice")
WANTED = ("sky130_fd_pr__nfet_01v8__", "sky130_fd_pr__pfet_01v8__", "sky130_fd_pr__pfet_01v8_hvt__")
CORNERS = ("tt", "ss", "ff", "sf", "fs")


def slim_lib(corner="tt", mismatch=False):
    """Return the path of the slim library for a process corner (built on first use)."""
    d = os.path.join(SIM, "models")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{corner}{'_mm' if mismatch else ''}.spice")
    if os.path.exists(path):
        return path
    cdir = os.path.join(NG, "corners")
    out = [f"* slim SKY130 library: corner {corner}, mismatch {'on' if mismatch else 'off'}",
           f".param mc_mm_switch={1 if mismatch else 0}", ".param mc_pr_switch=0"]
    for line in open(os.path.join(cdir, corner + ".spice")):
        m = re.match(r'\.include\s+"([^"]+)"', line)
        if m and os.path.basename(m.group(1)).startswith(WANTED):
            out.append(f'.include "{os.path.normpath(os.path.join(cdir, m.group(1)))}"')
    for line in open(os.path.join(NG, "all.spice")):       # scale option + the shared .param block
        if "parasitics/" in line:
            break
        m = re.match(r'\.include\s+"([^"]+)"', line)
        out.append(f'.include "{os.path.normpath(os.path.join(NG, m.group(1)))}"' if m else line.rstrip("\n"))
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return path


# ----------------------------------------------------------------------------- flat models for large netlists
# The PDK wraps every MOSFET in a sub-circuit that carries all the binned model cards of the
# device (50 to 70 cards). ngspice copies the whole sub-circuit for every instance, which costs
# about 1 MB per transistor: fine for a few hundred devices, impossible for twenty thousand.
# For large netlists we therefore pick, per transistor size, the one model card whose bin
# contains that size, substitute the size into its parameter expressions, and write it as an
# ordinary top-level .model. Devices are then plain M elements that share those few models.
# This is exact as long as mismatch is off (the only per-instance terms are the mismatch ones).
BASE = {"sky130_fd_pr__special_nfet_01v8": "sky130_fd_pr__nfet_01v8",
        "sky130_fd_pr__special_pfet_01v8_hvt": "sky130_fd_pr__pfet_01v8_hvt"}
SPICE_DIR = os.path.join(PDK_ROOT, "sky130A", "libs.ref", "sky130_fd_pr", "spice")


def _read_with_includes(path):
    out = []
    for line in open(path):
        m = re.match(r'\s*\.include\s+"([^"]+)"', line)
        if m:
            out += _read_with_includes(os.path.join(os.path.dirname(path), m.group(1)))
        else:
            out.append(line.rstrip("\n"))
    return out


def _split_device_file(lines, dev):
    """Return (preamble lines, [(lmin, lmax, wmin, wmax, kind, body lines), ...]) for the sub-circuit `dev`."""
    pre, bins, cur, inside, other = [], [], None, False, False
    for ln in lines:
        s = ln.strip()
        low = s.lower()
        if low.startswith(".subckt"):
            inside = s.split()[1] == dev
            other = not inside
            continue
        if low.startswith(".ends"):
            inside = other = False
            cur = None
            continue
        if other:
            continue
        if not inside:
            pre.append(ln)
            continue
        if low.startswith(".model"):
            cur = [s.split()[2], []]
            bins.append(cur)
        elif cur is not None and (s.startswith("+") or s.startswith("*")):
            if s.startswith("+"):
                cur[1].append(s)
    parsed = []
    for kind, body in bins:
        txt = " ".join(body)
        g = lambda k: float(re.search(rf"\b{k}\s*=\s*([-+0-9.eE]+)", txt).group(1))
        parsed.append((g("lmin"), g("lmax"), g("wmin"), g("wmax"), kind, body))
    return pre, parsed


def model_name(dev, w, l):
    dev = BASE.get(dev, dev)
    return (dev.replace("sky130_fd_pr__", "") + f"_w{w:g}_l{l:g}").replace(".", "p")


def flat_models(corner, sizes):
    """Write top-level .model cards for the given {(device, w_um, l_um)} at a corner; return the file path."""
    sizes = sorted({(BASE.get(d, d), w, l) for d, w, l in sizes})
    key = "_".join(f"{model_name(d, w, l)}" for d, w, l in sizes)
    import hashlib
    path = os.path.join(SIM, "models", f"flat_{corner}_{hashlib.sha1(key.encode()).hexdigest()[:8]}.spice")
    if os.path.exists(path):
        return path
    files = {}
    for line in open(os.path.join(NG, "corners", corner + ".spice")):
        m = re.match(r'\.include\s+"([^"]+)"', line)
        if m and os.path.basename(m.group(1)).startswith(WANTED) and "mismatch" not in m.group(1):
            f = os.path.normpath(os.path.join(NG, "corners", m.group(1)))
            dev = re.match(r"(sky130_fd_pr__[a-z0-9_]+?)__", os.path.basename(f)).group(1)
            files[dev] = f
    out = [f"* flat SKY130 models, corner {corner}: one .model per transistor size, mismatch off",
           ".param mc_mm_switch=0", ".param mc_pr_switch=0"]
    for line in open(slim_lib(corner)):                 # shared parameters: everything except the device files
        if "libs.ref" in line and "mismatch" not in line:
            continue
        if line.startswith(".param mc_") or line.startswith("*"):
            continue
        out.append(line.rstrip("\n"))
    done_pre = set()
    for dev, w, l in sizes:
        pre, bins = _split_device_file(_read_with_includes(files[dev]), dev)
        if dev not in done_pre:
            out += [p for p in pre if p.strip() and not p.strip().startswith("*")]
            done_pre.add(dev)
        lm, wm = l * 1e-6, w * 1e-6
        eps = 1e-12
        hit = [b for b in bins if b[0] - eps <= lm < b[1] - eps and b[2] - eps <= wm < b[3] - eps]
        if not hit:
            hit = [b for b in bins if b[0] - eps <= lm <= b[1] + eps and b[2] - eps <= wm <= b[3] + eps]
        assert hit, f"no model bin for {dev} w={w} l={l}"
        kind, body = hit[0][4], hit[0][5]

        def subst(m):
            e = m.group(0)
            e = re.sub(r"\bl\b", f"{l:g}", e)
            e = re.sub(r"\bw\b", f"{w:g}", e)
            return re.sub(r"\bmult\b", "1", e)
        out.append(f".model {model_name(dev, w, l)} {kind}")
        for b in body:
            if re.match(r"\+\s*lmin\s*=", b):
                continue                                 # no binning: the model is used for exactly one size
            out.append(re.sub(r"\{[^}]*\}", subst, b))
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return path
