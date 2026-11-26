# Integration example: self-test + macro

`sram_bist_top` places one `sram_64x32` hard macro next to a March C- self-test controller and
takes both through the RTL-to-GDS flow. It uses only the files in [`../release`](../release):
GDS, LEF, the three Liberty files and the black-box Verilog.

| file | content |
|---|---|
| `sram_bist.v` | March C- over all 64 words, two data backgrounds, 1,284 clock cycles |
| `sram_bist_top.v` | controller + macro |
| `tb_bist.v` | test bench: a good memory passes; a memory with one stuck bit fails and its address is reported |
| `config.json`, `run.sh` | LibreLane configuration and launcher |

Two things in it are worth copying into a real design:

- **Register `dout` before using it.** Read data leaves the macro after the falling clock edge,
  so only half a period minus the clock-to-output delay is left before the next rising edge.
  The controller captures `dout` in a register and compares one cycle later.
- **Power.** The macro has vertical metal 4 straps. The two-layer grid of the flow crosses it
  with horizontal metal 5 straps and connects to them (`PDN_MACRO_CONNECTIONS`). Leave either no
  standard-cell rows beside the macro or a strip wide enough to receive tap cells and a pair of
  power straps; a narrow sliver of rows fails the latch-up rules.

Result of the run (25 ns clock): DRC clean in Magic and KLayout, LVS clean, no antenna, timing
or power-grid violations. The numbers are in [`../reports/example`](../reports/example).
