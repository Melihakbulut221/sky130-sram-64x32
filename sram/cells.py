"""Leaf-cell layouts, drawn with SKY130 *logic* design rules (no SRAM-specific rule waivers).

Everything is in nanometres on a 5 nm grid. The bit cell is the classic "thin cell"
arrangement adapted to rules without shared (butted) contacts:

      n strip | p strip   p strip | n strip          two horizontal poly levels
      PD + PG |   PU        PU    | PG + PD          (lower: PD_L/PU_L and PG_R,
                                                      upper: PG_L and PU_R/PD_R)

Neighbouring cells are mirrored in x and y, so the contacts on the cell boundary
(bit lines, VDD, GND, word-line poly contact) are shared. Each cell draws those shared
shapes in full; the mirrored copies overlap exactly.
"""
from .bitcell import CELL
from .mag import Cell

NM = 1000  # nm per micrometre


def nm(v_um):
    r = round(v_um * NM / 5) * 5
    return int(r)


# ----------------------------------------------------------------------------- rule constants (nm)
LICON = 170          # contact cut size (licon and mcon)
VIA1 = 260           # Magic via1 tile: 150 nm cut plus 55 nm of metal enclosure on every side
POLY_W = 150
ENDCAP = 130         # poly past the channel
GATE_CT = 55         # diffusion contact to gate
PC_NDIFF = 190       # poly contact to n diffusion
PC_PDIFF = 235       # poly contact to p diffusion
NWELL_PDIFF = 180    # n-well enclosure of p diffusion
NWELL_NDIFF = 340    # n diffusion to n-well


class BitcellGeom:
    """All coordinates of the bit cell, derived from the transistor sizes."""

    def __init__(self, z=CELL):
        self.z = z
        # Vertical: gate centre 215 nm from the cell edge (shared 280 nm contact region between
        # mirrored gates); 480 nm between the two poly levels (250 nm of drain past the
        # pull-down gate, then 80 nm to the pass gate, poly.7 and poly.4).
        self.H = 910
        self.y_lo, self.y_hi, self.y_mid = 215, 695, 455
        self.y_jog = self.y_lo + 75 + 250               # top of the wide part of the n strip
        wpd, wpg, wpu = nm(z.wpd), nm(z.wpg), nm(z.wpu)
        assert z.lpd == z.lpg == z.lpu == 0.15, "the layout assumes minimum-length gates"
        self.wpd, self.wpg, self.wpu = wpd, wpg, wpu
        self.xn = LICON // 2 + PC_NDIFF                 # 275: left edge of the left n strip
        self.xn_w = self.xn + wpd                       # right edge of its wide (pull-down) part
        self.xn_n = self.xn + wpg                       # right edge of its narrow (pass-gate) part
        self.xw1 = self.xn_w + NWELL_NDIFF              # n-well left edge
        self.xp1 = self.xw1 + NWELL_PDIFF               # left p strip
        self.xp1r = self.xp1 + wpu
        self.xq = self.xp1r + PC_PDIFF                  # left edge of the Q poly contact
        d2 = 480                                        # centre-to-centre distance of the two poly contacts
        self.xc = self.xq + LICON // 2 + d2 // 2        # cell centre
        self.W = 2 * self.xc
        self.x_bl = self.xn + wpg // 2                  # bit-line contact / metal2 line
        self.x_q = self.xn + 225                        # storage-node contact on the n strip
        self.x_gnd = self.xn + wpd // 2 if wpd >= 420 else self.x_bl
        self.x_vdd = self.xp1 + wpu // 2


def bitcell(z=CELL):
    g = BitcellGeom(z)
    c = Cell("sram_bitcell")
    W, H = g.W, g.H
    c.bbox = (0, 0, W, H)

    def both(fn):
        """Draw a shape and its point-symmetric partner (the cell is symmetric about its centre)."""
        fn(lambda x: x, lambda y: y)
        fn(lambda x: W - x, lambda y: H - y)

    # n-well (one vertical stripe per column)
    c.rect("nwell", g.xw1, -320, W - g.xw1, H + 320)

    # diffusion strips
    def diff(X, Y):
        c.rect("ndiff", X(g.xn), Y(-140), X(g.xn_w), Y(g.y_jog))                 # wide: pull-down + GND contact
        c.rect("ndiff", X(g.xn), Y(g.y_jog), X(g.xn_n), Y(H + 140))              # narrow: pass gate + bit-line contact
        c.rect("pdiff", X(g.xp1), Y(-140), X(g.xp1r), Y(g.y_mid + 125))          # pull-up
    both(diff)

    # poly
    def poly(X, Y):
        # lower-left level: pull-down / pull-up gate of the left inverter, ends in a contact pad
        xqb = W - g.xq - LICON                           # left edge of the QB poly contact
        c.rect("poly", X(g.xn - ENDCAP), Y(g.y_lo - 75), X(xqb + LICON + 80), Y(g.y_lo + 75))
        c.rect("poly", X(xqb - 80), Y(g.y_lo - 110), X(xqb + LICON + 80), Y(g.y_lo + 160))
        # upper-left level: word-line (pass) gate, contact pad centred on the cell boundary
        c.rect("poly", X(-165), Y(g.y_hi - 75), X(g.xn_n + ENDCAP), Y(g.y_hi + 75))
        c.rect("poly", X(-165), Y(g.y_hi - 160), X(165), Y(g.y_hi + 110))
        c.rect("pmoshvt" if g.z.pu == "ph" else "pmos", X(g.xp1), Y(g.y_lo - 75), X(g.xp1r), Y(g.y_lo + 75))
    both(poly)

    # contacts and local interconnect
    def li(X, Y):
        yq1, yq2 = g.y_mid - 85, g.y_mid + 85
        # storage node: n contact, p contact, poly contact of the opposite inverter
        c.box("ndiffc", X(g.x_q), Y(g.y_mid), LICON, LICON)
        c.box("pdiffc", X(g.x_vdd), Y(g.y_mid), LICON, LICON)
        c.rect("locali", X(g.x_q - 165), Y(yq1), X(g.xq + LICON), Y(yq2))
        c.rect("polycont", X(g.xq), Y(g.y_hi - 110), X(g.xq + LICON), Y(g.y_hi + 60))
        c.rect("locali", X(g.xq - 80), Y(yq1), X(g.xq + LICON), Y(g.y_hi + 60))
        c.rect("locali", X(g.xq - 80), Y(g.y_hi - 110), X(g.xq + LICON + 80), Y(g.y_hi + 60))
        # word-line poly contact on the boundary
        c.rect("polycont", X(-85), Y(g.y_hi - 110), X(85), Y(g.y_hi + 60))
        c.rect("locali", X(-165), Y(g.y_hi - 110), X(165), Y(g.y_hi + 60))
        c.rect("viali", X(-85), Y(g.y_hi - 110), X(85), Y(g.y_hi + 60))
        c.rect("metal1", X(-115), Y(g.y_mid), X(115), Y(g.y_hi + 120))
        # bit line (top of the left strip)
        c.box("ndiffc", X(g.x_bl), Y(H), LICON, LICON)
        c.box("locali", X(g.x_bl), Y(H), LICON, LICON + 160)
        c.box("viali", X(g.x_bl), Y(H), LICON, LICON)
        c.box("metal1", X(g.x_bl), Y(H), VIA1, VIA1 + 60)
        c.box("via1", X(g.x_bl), Y(H), VIA1, VIA1)
        # ground (bottom of the left strip), strapped to the metal2 line on the cell boundary
        c.box("ndiffc", X(g.x_gnd), Y(0), LICON, LICON)
        c.rect("locali", X(-85), Y(-85), X(g.x_gnd + 165), Y(85))
        c.box("viali", X(0), Y(0), LICON, LICON)
        c.box("metal1", X(0), Y(0), VIA1, VIA1 + 60)
        c.box("via1", X(0), Y(0), VIA1, VIA1)
        # VDD (bottom of the left p strip)
        c.box("pdiffc", X(g.x_vdd), Y(0), LICON, LICON)
        c.box("locali", X(g.x_vdd), Y(0), LICON, LICON + 160)
        c.box("viali", X(g.x_vdd), Y(0), LICON, LICON)
        c.box("metal1", X(g.x_vdd), Y(0), VIA1, VIA1 + 60)
        c.box("via1", X(g.x_vdd), Y(0), VIA1, VIA1)
    both(li)

    # word line (metal1, horizontal) and the vertical metal2 lines
    c.rect("metal1", 0, g.y_mid - 100, W, g.y_mid + 100)
    for x in (0, g.x_bl, g.x_vdd, W - g.x_vdd, W - g.x_bl, W):
        c.rect("metal2", x - 150, -160, x + 150, H + 160)

    c.label("metal1", W // 2 - 50, g.y_mid - 50, W // 2 + 50, g.y_mid + 50, "WL", cls="input")
    c.label("metal2", g.x_bl - 50, 400, g.x_bl + 50, 500, "BL")
    c.label("metal2", W - g.x_bl - 50, 400, W - g.x_bl + 50, 500, "BLB")
    for x in (g.x_vdd, W - g.x_vdd):
        c.label("metal2", x - 50, 400, x + 50, 500, "VDD", use="power")
    for x in (0, W):
        c.label("metal2", x - 50, 400, x + 50, 500, "GND", use="ground")
    c.geom = g
    return c


# ----------------------------------------------------------------------------- well-tap / power strap row
STRAP_H = 1200
VIA2 = 280           # Magic via2 tile: 200 nm cut + 40 nm enclosure


def strap(z=CELL):
    """Tap row inserted every 16 word lines (and at both ends of the array).

    Holds the n-well tap (to VDD) and the substrate tap (to GND) of every column, and ties the
    vertical metal2 power lines to two horizontal metal3 rails. Symmetric in x and y.
    """
    g = BitcellGeom(z)
    c = Cell("sram_strap")
    W, Hs = g.W, STRAP_H
    ym = Hs // 2
    c.bbox = (0, 0, W, Hs)
    c.rect("nwell", g.xw1, 0, W - g.xw1, Hs)
    # n-well tap in the middle of the column, strapped to both VDD lines on metal1
    c.box("nsubdiff", g.xc, ym, 430, 170)
    c.box("nsubdiffcont", g.xc, ym, LICON, LICON)
    c.box("locali", g.xc, ym, 330, 170)
    c.box("viali", g.xc, ym, LICON, LICON)
    c.rect("metal1", g.x_vdd - 160, ym - 130, W - g.x_vdd + 160, ym + 130)
    for x in (g.x_vdd, W - g.x_vdd):
        c.box("via1", x, ym, VIA1, VIA1)
        c.box("via2", x, 930, VIA2, VIA2)
    # substrate tap on the column boundary, under the shared GND line
    for x in (0, W):
        c.box("psubdiff", x, ym, 430, 170)
        c.box("psubdiffcont", x, ym, LICON, LICON)
        c.box("locali", x, ym, 330, 170)
        c.box("viali", x, ym, LICON, LICON)
        c.box("metal1", x, ym, VIA1, VIA1 + 60)
        c.box("via1", x, ym, VIA1, VIA1)
        c.box("via2", x, 270, VIA2, VIA2)
    for x in (0, g.x_bl, g.x_vdd, W - g.x_vdd, W - g.x_bl, W):
        c.rect("metal2", x - 150, 0, x + 150, Hs)
    c.rect("metal3", -165, 100, W + 165, 440)       # GND rail (overlaps the neighbours, covers the edge vias)
    c.rect("metal3", -165, 760, W + 165, 1100)      # VDD rail
    c.geom = g
    return c


def quad(z=CELL):
    """2 x 2 bit cells with the mirroring that lets neighbours share their boundary contacts."""
    b = bitcell(z)
    g = b.geom
    c = Cell("sram_quad")
    c.bbox = (0, 0, 2 * g.W, 2 * g.H)
    c.place(b, "c00", 0, 0)
    c.place(b, "c10", 2 * g.W, 0, mx=True)
    c.place(b, "c01", 0, 2 * g.H, my=True)
    c.place(b, "c11", 2 * g.W, 2 * g.H, mx=True, my=True)
    c.geom = g
    return c


def array(rows=64, cols=32, group=16, z=CELL, name="sram_array"):
    """Bit-cell array: `rows` word lines, `cols` bit-line pairs, a strap row every `group` rows."""
    assert rows % group == 0 and group % 2 == 0 and cols % 2 == 0
    q, s = quad(z), strap(z)
    g = q.geom
    c = Cell(name)
    y = 0
    c.row_y = []                      # y of the bottom edge of every word-line row
    for k in range(rows // group + 1):
        c.place(s, f"strap{k}", 0, y, array=(cols, g.W, 1, STRAP_H))
        y += STRAP_H
        if k < rows // group:
            c.place(q, f"blk{k}", 0, y, array=(cols // 2, 2 * g.W, group // 2, 2 * g.H))
            c.row_y += [y + r * g.H for r in range(group)]
            y += group * g.H
    c.bbox = (0, 0, cols * g.W, y)
    c.geom, c.rows, c.cols = g, rows, cols
    return c


# ----------------------------------------------------------------------------- array macro
ROWS, COLS = 64, 32
XL, XR, YB, YT = 2000, 600, 1000, 400        # macro margins around the cell array (nm)
WL_STACK_X = -700                             # where each word line climbs from metal1 to its metal3 pin
RAIL_GND, RAIL_VDD = (100, 440), (760, 1100)  # metal3 rails inside a strap row (y range)


def bl_x(col, g):
    """x of the true and complement bit line of a column (odd columns are mirrored)."""
    a, b = col * g.W + g.x_bl, col * g.W + g.W - g.x_bl
    return (a, b) if col % 2 == 0 else (b, a)


def macro(rows=ROWS, cols=COLS, group=16, z=CELL, name=None):
    """The hard macro: cell array + word-line pins (metal3, left), bit-line pins (metal2, bottom)
    and power pins (the metal3 rails of the strap rows). Origin of the returned cell = lower-left corner."""
    name = name or f"sram_array_{rows}x{cols}"
    a = array(rows, cols, group, z, name=name + "_cells")
    g = a.geom
    aw, ah = a.bbox[2], a.bbox[3]
    c = Cell(name)
    ox, oy = XL, YB                                  # array origin inside the macro
    c.place(a, "cells", ox, oy)
    c.bbox = (0, 0, XL + aw + XR, YB + ah + YT)
    # word lines: metal1 track -> via1 -> metal2 pad -> via2 -> metal3 pin on the left edge
    xs = ox + WL_STACK_X
    for r, y0 in enumerate(a.row_y):
        yc = oy + y0 + g.y_mid
        c.rect("metal1", xs - 160, yc - 100, ox, yc + 100)
        c.box("metal1", xs, yc, VIA1 + 60, VIA1)
        c.box("via1", xs, yc, VIA1, VIA1)
        c.box("metal2", xs, yc, 280, 370)
        c.box("via2", xs, yc, VIA2, VIA2)
        c.rect("metal3", 0, yc - 165, xs + 165, yc + 165)
        c.label("metal3", 0, yc - 165, 600, yc + 165, f"WL[{r}]", cls="input")
    # bit lines: the metal2 lines continue below the array as pins
    for col in range(cols):
        for nm_, x in zip(("BL", "BLB"), bl_x(col, g)):
            c.rect("metal2", ox + x - 150, 0, ox + x + 150, oy)
            c.label("metal2", ox + x - 150, 0, ox + x + 150, 600, f"{nm_}[{col}]", cls="bidirectional")
    # power: the metal3 rails of every strap row are the power pins. The power grid of the design
    # that places the macro runs its vertical metal4 straps across the array and drops vias onto them.
    for k in range(rows // group + 1):
        ys = oy + k * (STRAP_H + group * g.H)
        for net, (y1, y2) in (("GND", RAIL_GND), ("VDD", RAIL_VDD)):
            c.rect("metal3", ox - 165, ys + y1, ox + aw + 165, ys + y2)
            c.label("metal3", ox - 165, ys + y1, ox + aw + 165, ys + y2, net,
                    use="power" if net == "VDD" else "ground", cls="bidirectional")
    c.geom, c.rows, c.cols, c.array = g, rows, cols, a
    return c


def macro_test():
    return macro(32, 8, name="sram_array_test")
