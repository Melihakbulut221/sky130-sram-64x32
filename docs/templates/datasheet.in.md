# sram_64x32 data sheet

64-word × 32-bit single-port synchronous static RAM, SkyWater SKY130 (130 nm), 1.8 V.

> Status: design verified by simulation and sign-off checks on the final layout
> ([verification.md](verification.md)). Not fabricated; no silicon data.

## Features

- 2,048 bits: 64 words × 32 bits, four byte-write enables
- 6T bit cells drawn with the standard logic design rules (no SRAM rule waivers)
- Fully static: no sense amplifier, no self-timed pulse, no minimum clock frequency
- All inputs registered on the rising clock edge; registered-style output that holds between reads
- One supply, 1.8 V; standard-cell compatible pins on metal 2 / metal 3, power on metal 4
- Views: GDS, LEF, Liberty (three corners), Verilog model, gate-level netlist, SDF, SPICE netlists

## Pins

| pin | direction | description |
|---|---|---|
| `clk` | input | clock |
| `en` | input | chip enable; when 0 at a rising edge, the cycle does nothing |
| `we` | input | 1 = write, 0 = read |
| `wmask[3:0]` | input | byte-write enables; `wmask[b]` covers `din[8b+7 : 8b]` |
| `addr[5:0]` | input | word address |
| `din[31:0]` | input | write data |
| `dout[31:0]` | output | read data |
| `VPWR`, `VGND` | supply | 1.8 V and ground (vertical metal 4 straps) |

## Function

| `en` | `we` | at the rising edge of `clk` | `dout` |
|---|---|---|---|
| 0 | x | nothing | holds |
| 1 | 0 | read the word at `addr` | new data after the following falling edge |
| 1 | 1 | write `din` into the bytes selected by `wmask` | holds |

`dout` is undefined until the first read. Memory content is undefined until it is written.
After power-up, apply at least one rising clock edge with `en` = 0 before the first access: the
internal registers come up in an unknown state, and until that edge an arbitrary word line may
be active.

## Timing

![timing](img/timing.png)

- `en`, `we`, `wmask`, `addr` and `din` are sampled on the **rising** edge of `clk`
  (setup and hold relative to that edge).
- While `clk` is high the bit lines are precharged and the address is decoded. The access takes
  place while `clk` is **low**.
- Read data appears on `dout` *t*<sub>CQ</sub> after the **falling** edge and stays until the next
  read has completed. Capture it on the next rising edge.
- Both clock phases must be long enough, so the limits are a minimum high time and a minimum low
  time. The numbers below assume a 50 % duty cycle.
- The clock may be stopped in either phase for any length of time.

%TIMING_TABLE%

Setup and hold times are from static timing analysis of the routed periphery plus a 0.1 ns guard
band; post-layout SPICE passes with every input switching exactly at these limits. *t*<sub>CQ</sub>
and the period are from post-layout SPICE with 30 fF on every output; the specified minimum
period is 1.25 × the shortest period at which the test sequence still passed in SPICE.
See [results.md](results.md) for the measurements and [verification.md](verification.md) for the method.

## Electrical

%ELECTRICAL_TABLE%

## Physical

| | |
|---|---|
| Size | 225 × 156 µm (0.0351 mm²) |
| Bit cell | 4.85 × 0.91 µm (4.41 µm²) |
| Routing layers used | li1, metal 1 to metal 4; metal 5 is free |
| Signal pins | west edge (metal 3): `clk`, `en`, `we`, `addr`; south edge (metal 2): `wmask`, `din`, `dout` |
| Power pins | `VPWR` / `VGND`: vertical metal 4 straps, 1.6 µm wide, 40 µm pitch, full height |

![chip](img/layout_chip.png)

## Using the macro

Files in [`release/`](../release):

| file | use |
|---|---|
| `sram_64x32.gds`, `sram_64x32.lef` | layout and abstract |
| `sram_64x32__tt_025C_1v80.lib`, `…__ss_100C_1v60.lib`, `…__ff_n40C_1v95.lib` | timing, matching the corners of `sky130_fd_sc_hd` |
| `sram_64x32.v` | behavioural model for simulation |
| `sram_64x32.bb.v` | black box for synthesis |
| `sram_64x32.nl.v`, `sram_64x32.pnl.v`, `sram_64x32__*.sdf` | gate-level netlists and delays of the periphery |
| `sram_64x32.lvs.spice`, `sram_64x32.pex.spice` | transistor netlists extracted from the layout, without / with parasitic capacitance |

With LibreLane or OpenLane 2 (see [`example/config.json`](../example/config.json) for a complete,
working configuration):

```json
"MACROS": {
    "sram_64x32": {
        "gds": ["dir::../release/sram_64x32.gds"],
        "lef": ["dir::../release/sram_64x32.lef"],
        "vh":  ["dir::../release/sram_64x32.bb.v"],
        "lib": { "*_tt_025C_1v80": ["dir::../release/sram_64x32__tt_025C_1v80.lib"],
                 "*_ss_100C_1v60": ["dir::../release/sram_64x32__ss_100C_1v60.lib"],
                 "*_ff_n40C_1v95": ["dir::../release/sram_64x32__ff_n40C_1v95.lib"] },
        "instances": { "u_mem": { "location": [20, 78], "orientation": "N" } }
    }
},
"PDN_MACRO_CONNECTIONS": ["u_mem VPWR VGND VPWR VGND"]
```

Notes for integration:

- **Power.** The macro's grid is metal 4 only. The surrounding design must cross it with
  horizontal metal 5 straps (the default two-layer grid of the flow does this). At least two
  straps of each net should cross the macro.
- **Clock.** `dout` is launched by the falling clock edge. A design that captures it on the next
  rising edge has half a period minus *t*<sub>CQ</sub> for the path; the Liberty files describe
  this as a `falling_edge` arc. Register `dout` before using it in logic.
- **Floorplan.** Do not leave a narrow sliver of standard-cell rows beside the macro: it must be
  wide enough for tap cells and a pair of power straps, or absent.
- **Read after write** of the same word in consecutive cycles returns the new data.
- **Self-test.** [`example/sram_bist.v`](../example/sram_bist.v) is a March C- controller
  (1,284 clock cycles) that can be placed next to the macro.

## Limits

Read [verification.md](verification.md#not-covered) before relying on this macro. In short: it
has not been fabricated, the mismatch analysis rests on the PDK's Monte Carlo models, and
there is no redundancy or error correction.
