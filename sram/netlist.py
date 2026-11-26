"""Schematic (source) netlists, written straight from the design parameters.

These are the reference that the layout is compared against in LVS, and the netlists
used for simulation.
"""
from . import spice as S
from .bitcell import CELL


def bitcell_subckt(z=CELL, name="sram_bitcell"):
    s = f".subckt {name} WL BL BLB VDD GND\n"
    s += S.mos("pdl", "Q", "QB", "GND", "GND", "n", z.wpd, z.lpd)
    s += S.mos("pul", "Q", "QB", "VDD", "VDD", z.pu, z.wpu, z.lpu)
    s += S.mos("pgl", "BL", "WL", "Q", "GND", "n", z.wpg, z.lpg)
    s += S.mos("pdr", "QB", "Q", "GND", "GND", "n", z.wpd, z.lpd)
    s += S.mos("pur", "QB", "Q", "VDD", "VDD", z.pu, z.wpu, z.lpu)
    s += S.mos("pgr", "BLB", "WL", "QB", "GND", "n", z.wpg, z.lpg)
    return s + ".ends\n"


def array_ports(rows, cols):
    p = [f"WL[{r}]" for r in range(rows)]
    for c in range(cols):
        p += [f"BL[{c}]", f"BLB[{c}]"]
    return p + ["VDD", "GND"]


def array_subckt(rows=64, cols=32, z=CELL, name=None):
    name = name or f"sram_array_{rows}x{cols}"
    ports = array_ports(rows, cols)
    s = bitcell_subckt(z) + "\n"
    s += f".subckt {name}\n" + "".join("+ " + " ".join(ports[i:i + 12]) + "\n" for i in range(0, len(ports), 12))
    for r in range(rows):
        for c in range(cols):
            s += f"Xbit_r{r}_c{c} WL[{r}] BL[{c}] BLB[{c}] VDD GND sram_bitcell\n"
    return s + ".ends\n"
