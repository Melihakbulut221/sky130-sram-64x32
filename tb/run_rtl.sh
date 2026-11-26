#!/bin/sh
# Logic simulation of the periphery RTL with the switch-level array model (run inside the tool container).
set -e
PDKV=${PDK_ROOT:-/pdkroot}/sky130A/libs.ref/sky130_fd_sc_hd/verilog
cd "$(dirname "$0")"
mkdir -p work
iverilog -g2012 -DFUNCTIONAL -DUNIT_DELAY=#0.05 -o work/tb_rtl.vvp \
    $PDKV/primitives.v $PDKV/sky130_fd_sc_hd.v \
    sram_array_64x32_model.v ../rtl/sram_64x32.v tb_sram.v
vvp work/tb_rtl.vvp | tail -25
