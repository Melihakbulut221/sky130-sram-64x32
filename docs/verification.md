# Verification

What was checked, with which tool, and what was not. The numbers are in [results.md](results.md),
the raw reports in [`reports/`](../reports).

**Scope.** Every result here is a simulation or a sign-off check on the generated layout.
Nothing has been fabricated or measured.

## Summary

| # | check | tool | object | result |
|---|---|---|---|---|
| 1 | static noise margins, write margin, read current over 11 PVT points | ngspice, SKY130 BSIM4 models | bit cell (schematic) | positive margins everywhere |
| 2 | Monte Carlo local mismatch, 1,000 cells × 5 conditions | ngspice, `*_mm` model corners | bit cell (schematic) | 0 failures |
| 3 | design rules, full deck | Magic 8.3 `drc(full)` | array macro | 0 violations |
| 4 | design rules, PDK deck `sky130A_mr.drc` (FEOL, BEOL, off-grid) | KLayout 0.30 | array macro | 0 violations |
| 5 | layout vs. schematic | Netgen 1.5 | array macro | match, 12,288 devices |
| 6 | logic simulation, 4,453 self-checked reads | Icarus Verilog | periphery RTL + switch-level array model | pass |
| 7 | column slice at transistor level, 9 PVT points | ngspice | 64 cells + complete standard-cell path (schematic) | pass |
| 8 | place-and-route sign-off: DRC (Magic + KLayout), XOR, gate-level LVS, antenna, timing, power grid | LibreLane 3.0.17 | complete memory | 0 violations |
| 9 | logic simulation of the final netlist, 4,453 self-checked reads | Icarus Verilog | post-route gate-level netlist + array model | pass |
| 10 | transistor-level LVS, flat, no black boxes | Magic + Netgen | complete memory (final GDS) | match, 18,248 devices |
| 11 | post-layout SPICE at the three library corners | ngspice | extracted final layout | pass |
| 12 | clock-period sweep and inputs switching next to the clock edge, three corners | ngspice | extracted final layout | [results](results.md) |
| 13 | post-layout SPICE with every transistor, 17 operations | ngspice | extracted final layout | [results](results.md) |
| 14 | behavioural model against the same testbench | Icarus Verilog | `release/sram_64x32.v` | pass |
| 15 | integration: self-test controller + released macro through the flow | LibreLane | `example/` | 0 violations |

## Details

### 1–2. Bit cell

`python -m sram.bitcell size | corners | mc`

- Hold and read static noise margin from butterfly curves (the largest square between the two
  voltage transfer curves, found in coordinates rotated by 45°).
- Write margin as the word-line write margin: one bit line at 0 V, the word line is swept up,
  and the margin is VDD minus the word-line voltage at which the cell flips. The bit-line write
  margin is computed as well.
- Read current with the bit line held at VDD; leakage with the word line off.
- Conditions: tt / ss / ff / sf / fs, −40 to 125 °C, 1.62 to 1.98 V (11 combinations).
- Monte Carlo uses the PDK's `*_mm` corners, which add an independent random term to the
  threshold voltage, oxide thickness and other parameters of every transistor.

Caveat: the Monte Carlo spread (σ of the read margin ≈ 11 mV) is only as good as those mismatch
models. They have not been compared with silicon data for devices of this size as part of this
project. The distribution of the write margin is quantised by the step of the DC sweep (2.5 mV).

### 3–5. Array macro

`python -m signoff.run_macro`

The layout is written as Magic cells, checked with Magic's complete rule set
(`drc style drc(full)`, euclidean distances), streamed out to GDS, and checked again with the
KLayout deck that ships with the PDK. These are two independent implementations of the SKY130
rules. LVS compares the netlist Magic extracts from the layout with a netlist that
`sram/netlist.py` writes from the same design parameters.

The rules that cannot be met by a single cell (every n-well needs a tap; every diffusion needs a
tap within 15 µm) are met at array level by the strap rows, and are part of the zero count.

Not checked at this level: metal density (a chip-level rule; the macro leaves metal 5 free and
has no fill).

### 6, 9, 14. Logic simulation

`tb/run_rtl.sh`, `tb/run_gl.sh <netlist>`

The array is replaced by a switch-level model (`tb/sram_array_64x32_model.v`) that reproduces
what matters to the periphery: a precharged bit line keeps its level, a selected cell pulls one
side low with limited strength, a driver overrides it, and a cell is overwritten when a bit
line is forced low while its word line is on. The model reports an error if two word lines are
ever on together.

The testbench writes and reads every word with two patterns, exercises the byte mask, disabled
cycles and alternating write / read on one word, then runs 4,000 random operations. `dout` is
compared with a reference model before every rising clock edge, including the cycles in which
it must hold.

These simulations use the functional cell models with a unit delay. They verify the logic and
the netlist, not the timing. (The timing-annotated cell models of the PDK rely on a Verilog
feature that Icarus does not implement, so an SDF simulation was not possible with the tools at
hand.) Timing is covered by static timing analysis (8) and by SPICE (11–13).

### 7. Column slice

`python -m sram.slice corners`

One bit-line pair with 64 cells and the complete path from the clock pin to `dout`, built from
the standard-cell transistor netlists, with the wire capacitances extracted from the array.
Used before the layout existed to check the scheme electrically and to measure internal
margins, for example the time between the phase clock switching off and the hold latches
opening (0.5 to 1.6 ns over corners).

### 8. Place-and-route sign-off

`flow/run.sh config.json` (inside the tool container)

LibreLane runs 75 steps. The ones that matter as checks: detailed-route DRC, antenna check,
Magic DRC and KLayout DRC on the final GDS, XOR between the GDS written by Magic and by KLayout,
gate-level LVS, multi-corner static timing analysis with extracted RC (setup, hold, slew,
capacitance), and a static IR-drop report. All counts are zero.

Static timing analysis covers the periphery up to the array. The array has no timing model, so
paths through the bit lines are outside its reach; they are covered by SPICE.

### 10. Transistor-level LVS of the complete memory

`python -m signoff.run_chip`

The flow's own LVS treats the array and the standard cells as black boxes. As an independent
check, Magic extracts the final GDS completely, down to every transistor of the array and of
the standard cells, into a flat netlist. Netgen compares it with the source: the final
gate-level netlist, the standard-cell SPICE library and the array schematic, flattened as well.

The comparison is run flat because a hierarchical one is ambiguous for this circuit: 64 rows and
32 bit slices are interchangeable until the address decoder and the port names tell them apart.

### 11–13. Post-layout SPICE

`python -m sram.chipsim corners | period | interface | func tt 25 1.8 20 full`

The netlist is the flat extraction of the final GDS with the parasitic capacitance Magic
extracts for every net (including coupling capacitors). The test writes two or four words,
reads them back, performs a byte-masked write and a disabled cycle, and checks all 32 outputs
before every rising clock edge.

Two details of the method:

- **Model handling.** The PDK wraps each transistor in a sub-circuit that contains every binned
  model card of the device; ngspice copies it per instance, about 1 MB per transistor.
  `sram/models.py` instead writes one top-level model per transistor size (the card of the
  matching bin with the size substituted into its expressions). A comparison of drain currents
  between the two forms for all ten sizes of the design shows no difference.
- **Interface timing.** Two extra runs per corner move every input transition to 0.3 ns before
  and to 0.15 ns after the rising clock edge, to confirm the setup and hold times that static
  timing analysis reports.
- **Row pruning.** In the corner and period sweeps only the rows that the test addresses are
  kept as transistors. The cells of the other rows are replaced by the capacitance their
  switched-off pass gates put on the bit lines (0.25 fF per cell, measured on the extracted
  devices). Run 13 uses the complete netlist without pruning.

Wire resistance is not extracted. The longest wires are a word line (155 µm of metal 1,
about 100 Ω against 85 fF) and a bit line (60 µm of metal 2, about 25 Ω against 35 fF); their RC
products are below 10 ps. The timing analysis of the periphery (8) does use extracted RC.

### 15. Integration example

`example/` contains a March C- self-test controller and a top level that instantiates the
released macro. It is simulated (`example/tb_bist.v`: a good memory passes, a memory with one
stuck bit is caught and its address reported) and taken through the same flow, using only the
files in `release/`: the macro's LEF, GDS, Liberty files and black box. The run is clean (Magic
and KLayout DRC, LVS, antenna, timing, power grid), which shows that the views are consistent
and that the metal 4 power straps of the macro connect to a surrounding two-layer grid. The LVS
of this run treats the macro as a black box; its inside is covered by check 10.

## Not covered

- Silicon. No fabrication, no measurement.
- Foundry sign-off. The open rule decks are the reference for the open PDK; a foundry may run a
  different deck.
- Wire resistance in the post-layout SPICE netlist, electromigration, dynamic IR drop.
- Timing-annotated gate-level simulation.
- Dynamic stability under supply noise, data retention at reduced voltage, soft errors, ageing.
- Mismatch beyond what the PDK's Monte Carlo models describe.
