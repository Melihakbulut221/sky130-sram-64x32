#!/bin/sh
# Logic simulation of the final (post place-and-route) gate-level netlist with the array model.
# usage: run_gl.sh <netlist.v>     (run inside the tool container)
set -e
PDKV=${PDK_ROOT:-/pdkroot}/sky130A/libs.ref/sky130_fd_sc_hd/verilog
cd "$(dirname "$0")"
mkdir -p work
iverilog -g2012 -DFUNCTIONAL -DUNIT_DELAY=#0.05 -o work/tb_gl.vvp \
    $PDKV/primitives.v $PDKV/sky130_fd_sc_hd.v \
    sram_array_64x32_model.v "$1" tb_sram.v
vvp work/tb_gl.vvp | tail -25
