#!/bin/sh
# Integration example: the self-test controller and the sram_64x32 hard macro, RTL to GDS.
# Run inside the Lima VM:  example/run.sh [extra librelane arguments]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
exec nerdctl run --rm -v "$ROOT:$ROOT" -v "$HOME/pdk:/pdk" -w "$HERE" \
    ${SRAM_IMAGE:-ghcr.io/librelane/librelane:3.0.17} \
    librelane --pdk-root /pdk --pdk sky130A "$@"
