#!/bin/sh
# Run inside the Lima VM:  flow/run.sh [extra librelane arguments]
# Periphery RTL + array macro -> GDS with LibreLane (Yosys, OpenROAD, Magic, KLayout, Netgen) on SKY130.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
exec nerdctl run --rm -v "$ROOT:$ROOT" -v "$HOME/pdk:/pdk" -w "$HERE" \
    ${SRAM_IMAGE:-ghcr.io/librelane/librelane:3.0.17} \
    librelane --pdk-root /pdk --pdk sky130A "$@"
