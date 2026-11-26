"""Locations of external tools. Every path can be overridden from the environment."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PLL = os.path.join(os.path.dirname(ROOT), "pll_sky130")

NGSPICE = os.environ.get("NGSPICE", os.path.join(_PLL, "tools", "ngspice", "bin", "ngspice"))
PDK_ROOT = os.environ.get("PDK_ROOT", os.path.join(_PLL, "pdk"))
SPICE_LIB = os.path.join(PDK_ROOT, "sky130A", "libs.tech", "ngspice", "sky130.lib.spice")

SIM = os.path.join(ROOT, "sim")
OUT = os.path.join(ROOT, "out")
for _d in (SIM, OUT):
    os.makedirs(_d, exist_ok=True)
