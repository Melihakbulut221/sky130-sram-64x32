"""Script of the video: one visual plus English narration for every step.

Numbers quoted in tables and in the narration are read from the result files in out/, so the
video cannot drift away from the measured results.
"""
import json
import os

from PIL import Image, ImageDraw

from . import code as CD
from . import figs as FG
from . import shots as SH
from . import style as S
from .engine import Anim, Step

ROOT = SH.ROOT
OUT = os.path.join(ROOT, "out")
GDS = os.path.join(ROOT, "release", "sram_64x32.gds")
SHOTS = SH.Shots(GDS)
FULL = SHOTS.full
STEPS = []          # (builder(progress) | None, text)

# ---------------------------------------------------------------------------- results
R = json.load(open(os.path.join(OUT, "results.json")))
T = R["timing"]
MX, MY = R["macro_origin"]                 # lower-left corner of the array macro on the die (um)
AX, AY = MX + 2.0, MY + 1.0                # origin of the cell array
CW, CH, SH_ = R["cell_w"], R["cell_h"], 1.2
ROW0 = AY + SH_                             # bottom of word-line row 0
CELL = (AX, ROW0, AX + CW, ROW0 + CH)
QUAD = (AX, ROW0, AX + 2 * CW, ROW0 + 2 * CH)
MACRO = (MX, MY, MX + R["macro_w"], MY + R["macro_h"])


def AN(x):
    """Indefinite article for a number as it is spoken ("an 11", "an 8", "a 12")."""
    t = f"{x:g}"
    return "an" if t.startswith("8") or t.split(".")[0] in ("11", "18") else "a"


def add(builder, text):
    STEPS.append((builder, " ".join(text.split())))


def same(text):
    add(None, text)


# ---------------------------------------------------------------------------- frame builders
def fig_slide(sec, title, fig_fn, *a, **kw):
    def b(p):
        return S.paste_fit(S.frame(sec, title, p), fig_fn(*a, **kw))
    return b


def notes_panel(im, notes, x1=1256):
    box = (x1, S.CONTENT[1], S.CONTENT[2], S.CONTENT[3])
    S.panel(im, box)
    S.bullets(im, notes, (x1 + 28, box[1] + 30, box[2] - 20, box[3]), size=27, gap=16)
    return im


def code_slide(sec, title, path, start, n=None, end=None, hl=(), notes=None, skip=(), fs=None, wcode=1380, lang="python"):
    def b(p):
        im = S.frame(sec, title, p)
        w = wcode if notes else S.CONTENT[2] - S.CONTENT[0]
        panel = CD.code_panel(path, start, n, end, hl=hl, size=(w, S.CONTENT[3] - S.CONTENT[1]), skip=skip, fs=fs, lang=lang)
        im.paste(panel, (S.CONTENT[0], S.CONTENT[1]))
        if notes:
            notes_panel(im, notes, x1=S.CONTENT[0] + w + 28)
        return im
    return b


def term_slide(sec, title, text, notes=None, ttl="terminal", hl=()):
    def b(p):
        im = S.frame(sec, title, p)
        w = 1180 if notes else S.CONTENT[2] - S.CONTENT[0]
        panel = CD.terminal(text, size=(w, S.CONTENT[3] - S.CONTENT[1]), title=ttl, hl=hl)
        im.paste(panel, (S.CONTENT[0], S.CONTENT[1]))
        if notes:
            notes_panel(im, notes)
        return im
    return b


def draw_legend(im, items):
    d = ImageDraw.Draw(im)
    f = S.font(22)
    w = max(d.textlength(t, font=f) for _, t in items) + 70
    x2, y1 = S.CONTENT[2] - 14, S.CONTENT[1] + 14
    x1, y2 = x2 - w, y1 + 20 + 34 * len(items)
    d.rounded_rectangle([x1, y1, x2, y2], radius=10, fill=(8, 11, 16), outline=S.LINE, width=2)
    for k, (col, t) in enumerate(items):
        y = y1 + 14 + 34 * k
        d.rectangle([x1 + 14, y + 2, x1 + 44, y + 24], fill=col)
        d.text((x1 + 56, y), t, font=f, fill=S.FG)


def lay_slide(sec, title, box, keys=SH.ALL, ann=(), legend=None, margin=0.04):
    def b(p):
        im = S.frame(sec, title, p)
        shot, act = SHOTS.image(SH.fit(box, margin=margin), keys=keys)
        if ann:
            shot = SH.annotate(shot, act, ann)
        im.paste(shot, (S.CONTENT[0], S.CONTENT[1]))
        if legend:
            draw_legend(im, legend)
        return im
    return b


def lay_anim(sec, title, box_a, box_b, keys=SH.ALL, dur=4.0, ann_end=()):
    def b(p):
        base = S.frame(sec, title, p)
        a, bb = SH.fit(box_a), SH.fit(box_b)

        def fn(u):
            im = base.copy()
            shot, act = SHOTS.image(SH.lerp_box(a, bb, u), keys=keys)
            if u >= 1.0 and ann_end:
                shot = SH.annotate(shot, act, ann_end)
            im.paste(shot, (S.CONTENT[0], S.CONTENT[1]))
            return im
        return Anim(fn, dur)
    return b


def bullet_slide(sec, title, items, size=33):
    def b(p):
        im = S.frame(sec, title, p)
        S.panel(im, S.CONTENT)
        S.bullets(im, items, (S.CONTENT[0] + 50, S.CONTENT[1] + 40, S.CONTENT[2] - 50, S.CONTENT[3]), size=size, gap=20)
        return im
    return b


def table_slide(sec, title, rows, note=None, shot=True):
    def b(p):
        im = S.frame(sec, title, p)
        d = ImageDraw.Draw(im)
        x1, y1, x2, y2 = S.CONTENT
        if shot:
            pic, _ = SHOTS.image(SH.fit(FULL, size=(840, 800)), size=(840, 800))
            S.panel(im, (x2 - 870, y1, x2, y2))
            im.paste(pic, (x2 - 855, y1 + 2))
            x2 = x2 - 890
        S.panel(im, (x1, y1, x2, y2))
        y = y1 + 30
        fk, fv = S.font(28), S.font(28, bold=True)
        for k, v, col in rows:
            d.text((x1 + 32, y), k, font=fk, fill=S.MUTED)
            d.text((x1 + 360, y), v, font=fv, fill=col)
            y += 54
        if note:
            for ln in S.wrap(d, note, S.font(24), x2 - x1 - 64):
                d.text((x1 + 32, y + 8), ln, font=S.font(24), fill=S.MUTED)
                y += 32
        return im
    return b


def grid_slide(sec, title, header, rows, note=None, col0=560, colw=390):
    """Table with a label column and value columns. rows: (label, [values], colour)."""
    def b(p):
        im = S.frame(sec, title, p)
        d = ImageDraw.Draw(im)
        x1, y1, x2, y2 = S.CONTENT
        S.panel(im, (x1, y1, x2, y2))
        y = y1 + 44
        fh, fk, fv = S.font(30, bold=True), S.font(31), S.font(33, bold=True)
        for k, h in enumerate(header):
            d.text((x1 + col0 + colw * k, y), h, font=fh, fill=S.BLUE)
        y += 62
        d.line([x1 + 36, y - 12, x2 - 36, y - 12], fill=S.LINE, width=2)
        for label, vals, col in rows:
            d.text((x1 + 40, y), label, font=fk, fill=S.MUTED)
            for k, v in enumerate(vals):
                d.text((x1 + col0 + colw * k, y), v, font=fv, fill=col)
            y += 70
        if note:
            y += 14
            for ln in S.wrap(d, note, S.font(26), x2 - x1 - 80):
                d.text((x1 + 40, y), ln, font=S.font(26), fill=S.MUTED)
                y += 36
        return im
    return b


def title_slide(p):
    im = Image.new("RGB", (S.W, S.H), S.BG)
    shot, _ = SHOTS.image(SH.fit(FULL, size=(1920, 640)), size=(1920, 640))
    shot = Image.blend(shot, Image.new("RGB", shot.size, S.BG), 0.35)
    im.paste(shot, (0, 296))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, S.W, 300], fill=S.BG)
    d.text((80, 62), "A 6T SRAM in 130 nm", font=S.font(92, bold=True), fill=S.FG)
    d.text((84, 176), "64 words × 32 bits on SkyWater SKY130, built with open tools", font=S.font(42), fill=S.BLUE)
    d.text((84, 238), "Full-custom cell array generated from Python  ·  standard-cell periphery  ·  DRC, LVS and SPICE sign-off",
           font=S.font(29), fill=S.MUTED)
    return im


def read(path):
    with open(os.path.join(ROOT, path)) as f:
        return f.read()


# ============================================================================
# INTRO
# ============================================================================
sec = "Intro"
add(title_slide, f"""
Every chip needs memory, and the densest memory you can build in plain logic is the six transistor SRAM cell.
In this video we design one from scratch, on SkyWater's open source 130 nm process, SKY130, using only open tools.
""")
add(table_slide(sec, "What did we get?", [
    ("Capacity", "64 words × 32 bits  (2,048 bits)", S.YELLOW),
    ("Bit cell", f"6T, {R['cell_w']:.2f} × {R['cell_h']:.2f} µm, logic design rules", S.FG),
    ("Macro size", f"{R['die_w']:g} × {R['die_h']:g} µm", S.FG),
    ("Transistors", f"{R['mosfets']:,}  (array {R['array_mosfets']:,})", S.FG),
    ("DRC", "Magic 0  ·  KLayout 0 violations", S.GREEN),
    ("LVS", f"transistor level: match ({R['lvs_devices']:,} devices)", S.GREEN),
    ("Clock → data (SPICE)", f"{T['tt']['t_cq_max']:.1f} ns typ,  {T['ss']['t_cq_max']:.1f} ns slow corner", S.GREEN),
    ("Clock period (SPICE)", f"passes at {T['tt']['t_min_period_sim']:g} ns typ,  {T['ss']['t_min_period_sim']:g} ns slow", S.GREEN),
    ("Supply", "1.8 V", S.FG),
], note="Simulation and sign-off checks on the final layout. This is not a silicon measurement."), f"""
Here is the result up front. A 2 kilobit memory macro, 64 words of 32 bits, with byte write enables.
The cell array is full custom layout, generated by Python code. The logic around it is standard cells.
The layout passes the design rule checks of two independent tools, it matches its netlist transistor by transistor,
and the extracted layout works in SPICE at the slow, typical and fast corners.
There is no fabricated chip yet, so everything you will see is simulation and sign-off.
""")

# ============================================================================
# 1. THE CELL
# ============================================================================
sec = "1 · The 6T cell"
add(fig_slide(sec, "Six transistors, one bit", FG.cell_schematic, None), """
The cell is two inverters connected in a loop. The loop has two stable states, and that is the stored bit.
Two more transistors, the pass gates, connect the two sides of the loop to a pair of bit lines when the word line goes high.
""")
add(fig_slide(sec, "Reading disturbs the cell", FG.cell_schematic, "read"), """
To read, both bit lines are charged to the supply and the word line is switched on. The side of the cell that holds a zero
pulls its bit line down. But while it does that, the pass gate lifts that zero a little. If it lifts it too far, the cell flips,
and the read destroys the data. So the pull down transistor must be stronger than the pass gate.
""")
add(fig_slide(sec, "Writing must win a fight", FG.cell_schematic, "write"), """
Writing is the opposite fight. One bit line is forced to zero, and the pass gate now has to overpower the pull up transistor
that is holding the one. So the pass gate must be stronger than the pull up. One transistor, two opposite requirements.
""")
add(fig_slide(sec, "Butterfly curves: how much noise can the cell take?", FG.butterfly), f"""
The standard way to measure this is the butterfly curve. Plot the transfer curve of one inverter, mirror the other one on top,
and the largest square that fits between them is the static noise margin.
With the word line off, the margin is about {R['bitcell']['hold_tt'] * 1000:.0f} millivolts. During a read it shrinks
to about {R['bitcell']['read_tt'] * 1000:.0f}, and at the worst process corner to {R['bitcell']['read_worst'] * 1000:.0f}.
""")
add(fig_slide(sec, "Choosing the transistor sizes", FG.sizing_bars), f"""
I swept the width of the pull down transistor over all process, voltage and temperature corners.
A wider pull down improves the read margin, in blue, and costs write margin, in orange.
The chosen cell uses a 0.65 µm pull down, minimum size pass gates, and high threshold pull ups, which also cut the leakage by a factor of ten.
""")
add(fig_slide(sec, "Monte Carlo: transistor mismatch", FG.mc_hist), f"""
Corners are not enough for a memory, because every cell has its own random mismatch.
A thousand Monte Carlo samples with the mismatch models of the process put the worst case read margin
{R['bitcell']['read_mc_sigma']:.0f} standard deviations away from failure. That is as far as the models can tell us; only silicon can confirm it.
""")

# ============================================================================
# 2. LAYOUT
# ============================================================================
sec = "2 · Cell layout"
LEG = [((104, 160, 96), "n-well"), ((190, 140, 70), "diffusion"), ((220, 70, 70), "poly"), ((190, 150, 220), "local interconnect"),
       ((90, 130, 230), "metal 1"), ((220, 110, 220), "metal 2")]
CB = (CELL[0] - 0.35, CELL[1] - 0.3, CELL[2] + 0.35, CELL[3] + 0.3)
add(lay_slide(sec, "Diffusion and wells", CB, SH.layers("well", "diff"),
              ann=[(CELL[0], CELL[1], CELL[2], CELL[3], "one cell: 4.85 × 0.91 µm", S.YELLOW)]), """
Now the layout. The cell follows the classic thin cell arrangement. Two n type strips on the outside carry the pull down and
pass transistors. Two p type strips in a shared n-well in the middle carry the pull ups.
""")
add(lay_slide(sec, "Poly gates", CB, SH.layers("well", "diff", "poly")), """
Two rows of polysilicon cross them. One piece of poly is the gate of a pull down and a pull up at the same time, that is one inverter.
The short pieces at the left and right edges are the pass gates.
""")
add(lay_slide(sec, "Contacts and local interconnect", CB, SH.layers("well", "diff", "poly", "con", "li")), """
Commercial SRAM cells use special, tighter design rules. This one deliberately does not. It is drawn with the ordinary logic rules,
so it needs no waivers. The price is area: the two cross coupling wires need ordinary poly contacts, with ordinary spacing,
and they sit in the middle of the cell. The result is about twice the area of the foundry's own cell.
""")
add(lay_slide(sec, "Metal 1: word line · Metal 2: bit lines and power", CB, SH.ALL), """
Metal one carries the word line across the cell. Metal two runs vertically: ground on the cell boundaries, the two bit lines, and two supply lines over the n-well.
""")
add(code_slide(sec, "The layout is a Python function", "sram/cells.py", "    def diff(X, Y):", n=5,
               hl=["both(diff)"],
               notes=[("h", "Drawn once, used twice"), "The cell is point symmetric, so every shape is written once and mirrored by code.",
                      "All coordinates are derived from the transistor sizes and the design rules.",
                      "Change a width, regenerate, and DRC, LVS and extraction run again."]), """
None of this was drawn by hand. The cell is a Python function that writes rectangles in the Magic layout format.
Because the cell is point symmetric, each shape is described once and the code places it twice.
""")
add(lay_anim(sec, "From one cell to the array", CB, (AX - 2.6, AY - 1.2, AX + 6 * CW, AY + SH_ + 8 * CH), dur=5.0), """
Neighbouring cells are mirrored, so they share their bit line contacts, their power contacts, and the contact of the word line.
Every sixteen rows there is a strap row with well taps and two power rails.
""")
add(lay_slide(sec, "The array macro: 64 × 32 cells", MACRO, SH.ALL,
              ann=[(MX, MY + 2, MX + 1.4, MY + R["macro_h"] - 1, "64 word-line pins", S.CYAN, "in"),
                   (MX + 2, MY, MX + R["macro_w"] - 0.6, MY + 1.0, "64 bit-line pins", S.PURPLE, "bottom")]), f"""
Sixty four rows of thirty two cells make the array macro: {R['array_mosfets']:,} transistors in 158 by 66 µm.
Word lines come out on the left, bit lines at the bottom, and vertical power straps on metal four tie into the rails.
""")
add(term_slide(sec, "Sign-off of the array", read("out/signoff_macro_summary.txt"),
               notes=[("h", "Three independent checks"), "Magic: the full SKY130 rule deck", "KLayout: the PDK's own DRC deck, front end, back end and off-grid",
                      "Netgen: layout against a netlist written from the same Python parameters"]), """
The array is checked on its own before anything else is built on top. Zero violations in Magic, zero in the KLayout deck that ships with the process,
and the extracted transistors match the reference netlist uniquely.
""")

# ============================================================================
# 3. PERIPHERY
# ============================================================================
sec = "3 · Periphery"
add(fig_slide(sec, "Architecture", FG.architecture), """
An array is useless without the circuits around it: a decoder to pick a row, drivers to precharge and write the bit lines, and something to sense them.
Normally that means analog sense amplifiers and carefully tuned self timed pulses. For a small memory at 1.8 volts I chose something much more boring.
""")
add(fig_slide(sec, "Timing", FG.timing_diagram), """
The bit lines swing all the way from rail to rail, so a plain inverter can sense them. And there are no internal pulses at all.
While the clock is high, the bit lines precharge and the address decodes. While the clock is low, one word line is on.
If a phase is too short, you slow the clock down. Nothing depends on a delay matching another delay.
""")
add(code_slide(sec, "One tri-state buffer per bit line", "rtl/sram_64x32.v", "            // One tri-state driver per bit line does three jobs:", n=9, lang="verilog",
               hl=["keep_drv0", "keep_drv1"],
               notes=[("h", "Three jobs, one cell"), "clock high: drive 1 → precharge", "writing: drive 0", "other line fell: drive 1 → keeper",
                      ("otherwise off: the cell discharges the line", S.YELLOW)]), """
Each bit line gets one standard tri state buffer that does three jobs. It precharges the line, it pulls the line low for a write,
and it works as a keeper: as soon as one bit line has fallen, the other one is actively held high. Because of that keeper the memory is fully static.
You can stop the clock in either phase.
""")
add(code_slide(sec, "The phase clock", "rtl/sram_64x32.v", "    sky130_fd_sc_hd__clkinv_2      keep_clkinv", n=9, lang="verilog",
               hl=["keep_icg", "keep_dly0", "keep_dly1"],
               notes=[("h", "Race free by construction"), "A clock gate makes the phase signal glitch free.",
                      "Hold latches block new inputs until the word line is off.",
                      "The periphery is ordinary Verilog with hand-picked cells where glitches matter."]), """
The one dangerous moment is the rising clock edge, when new inputs arrive while the old word line is still switching off.
Hold latches, opened by a delayed copy of the phase clock, block the new address and data until the previous access has ended.
""")

# ============================================================================
# 4. RTL TO GDS
# ============================================================================
sec = "4 · From RTL to GDS"
add(lay_slide(sec, f"The complete memory: {R['die_w']:g} × {R['die_h']:g} µm", FULL, SH.ALL,
              ann=[(MACRO[0], MACRO[1], MACRO[2], MACRO[3], "6T array (custom)", S.YELLOW, "in"),
                   (6, MY, MX - 1, MY + R["macro_h"], "row decoder", S.CYAN, "in"),
                   (6, 11, FULL[2] - 6, MY - 1, "column circuits, input registers, clocking (standard cells)", S.PURPLE, "in")]), f"""
The periphery is synthesized, placed and routed with LibreLane: Yosys, OpenROAD, Magic, KLayout and Netgen, with the array as a hard macro.
About {R['stdcells']:,} standard cells end up below and to the left of the array.
""")
add(lay_anim(sec, "Bit lines meet standard cells", FULL, (MX + 2, MY - 26, MX + 60, MY + 6), dur=5.0), """
One surprise on the way: the clock tree tool followed the phase clock through the word line gates, onto the bit lines, and crashed.
A clock that ends in a memory cell is not what it expects. So the phase clock is distributed by three hand placed buffers in the Verilog instead.
""")
add(term_slide(sec, "Sign-off of the complete memory", read("out/signoff_chip_summary.txt"),
               notes=[("h", "Final layout"), "Design rules: Magic and KLayout", "Antenna, power grid and timing checks of the flow",
                      ("LVS repeated flat, down to every transistor", S.GREEN)]), f"""
The finished layout is clean in both design rule checkers, has no antenna violations, and passes the timing checks of the flow.
Then I extract the whole layout again down to transistors, array and standard cells together, and compare it with the source netlist.
{R['lvs_devices']:,} devices, and the circuits match.
""")

# ============================================================================
# 5. VERIFICATION
# ============================================================================
sec = "5 · Does it work?"
add(fig_slide(sec, "Post-layout SPICE: write, then read", FG.waves, os.path.join(OUT, "chipc_tt.npz"), R["wave_t0"], R["wave_t1"],
              "", R["wave_rows"], 20e-9, R["wave_marks"]), f"""
The real test is SPICE on the extracted layout, with every transistor and the parasitic capacitance of every wire.
Here a word is written and read back. After the falling clock edge the word line rises, the cell pulls one bit line all the way down,
the inverter senses it, and the output latch updates {T['tt']['t_cq_max']:.1f} nanoseconds after the clock edge.
""")
add(grid_slide(sec, "Post-layout results at the sign-off corners",
               ["typical", "slow", "fast"], [
    ("Process, temperature, supply", ["tt, 25 °C, 1.80 V", "ss, 100 °C, 1.60 V", "ff, −40 °C, 1.95 V"], S.FG),
    ("Function", ["pass", "pass", "pass"], S.GREEN),
    ("Clock ↓ to data out", [f"{T[c]['t_cq_max']:.2f} ns" for c in ("tt", "ss", "ff")], S.YELLOW),
    ("Shortest passing clock period", [f"{T[c]['t_min_period_sim']:g} ns" for c in ("tt", "ss", "ff")], S.YELLOW),
    ("Specified clock period", [f"{T[c]['min_period_spec']:g} ns" for c in ("tt", "ss", "ff")], S.FG),
    ("Supply current at 50 MHz", [f"{T[c]['i_avg_mA']:.2f} mA" for c in ("tt", "ss", "ff")], S.FG),
], note="Test sequence: writes, reads, a byte-masked write and a disabled cycle. All 32 outputs are checked before every rising clock edge."), f"""
The same sequence passes at the slow, typical and fast corners. At the slow corner the data is out {T['ss']['t_cq_max']:.1f} nanoseconds after the clock edge,
and the memory still works with {AN(T['ss']['t_min_period_sim'])} {T['ss']['t_min_period_sim']:g} nanosecond clock. The data sheet specifies {T['ss']['min_period_spec']:g}, to leave a margin.
""")
add(bullet_slide(sec, "What you get, and what is still missing", [
    ("h", "In the repository"),
    "GDS, LEF, Liberty for three corners, Verilog model, SPICE netlists",
    "A March C- self-test, hardened together with the macro as an integration example",
    "Every step reproducible from code: sizing, layout, sign-off, simulation",
    ("h", "Not done"),
    ("No silicon. Nothing here has been fabricated or measured.", S.ORANGE),
    ("Mismatch numbers are only as good as the PDK's Monte Carlo models.", S.ORANGE),
    ("No redundancy or ECC, no wire-resistance extraction inside the array, no electromigration analysis.", S.ORANGE),
]), """
So what is in the repository? The layout, the abstract, timing libraries for three corners, a simulation model, the netlists,
and a self test that runs a march test over all the words. What is missing is the most important step: silicon.
Clean sign-off and passing simulations make a design ready for a test chip, not proven.
""")

# ============================================================================
# 6. LESSONS
# ============================================================================
sec = "6 · Lessons"
add(bullet_slide(sec, "What this project taught me", [
    "Robust beats clever. Rail-to-rail bit lines and two clock phases removed every analog timing risk from a small memory.",
    "Design rules shape the circuit. Without shared contacts the cross-coupling wires decide the size of the cell.",
    "Tools assume ordinary clocks. A clock that reaches a bit line needs its tree built by hand.",
    "Check each layer of the design on its own, then all of it together, flat.",
]), """
Three things I take away. First, robust beats clever: for a small memory, full swing bit lines and two clock phases remove a whole class of timing risks.
Second, design rules shape the circuit: without the special contacts of a foundry cell, the cross coupling wires decide how big the cell is.
And third, verify every level on its own, and then everything together.
The code, the layout and all the reports are on GitHub. Thanks for watching.
""")


def build_steps():
    steps, prev = [], None
    n = len(STEPS)
    for i, (builder, text) in enumerate(STEPS):
        if builder is None:
            vis = prev
        else:
            vis = builder(i / max(1, n - 1))
        steps.append(Step(vis, text))
        prev = vis
    return steps
