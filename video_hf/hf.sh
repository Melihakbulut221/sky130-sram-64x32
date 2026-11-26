#!/bin/sh
# Run the HyperFrames CLI with the project-local toolchain (Node.js, ffmpeg/ffprobe, headless Chrome).
#   video_hf/hf.sh <command> [args]        e.g.  video_hf/hf.sh render video_hf/short -o out/short.mp4
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$ROOT/tools/hf/bin:$ROOT/tools/node/bin:$ROOT/tools/hf/node_modules/.bin:$PATH"
export DO_NOT_TRACK=1 HYPERFRAMES_NO_TELEMETRY=1
# HyperFrames only searches "trusted" PATH directories; point it at the local binaries directly.
[ -x "$ROOT/tools/hf/bin/ffmpeg" ] && export HYPERFRAMES_FFMPEG_PATH="$ROOT/tools/hf/bin/ffmpeg"
[ -x "$ROOT/tools/hf/bin/ffprobe" ] && export HYPERFRAMES_FFPROBE_PATH="$ROOT/tools/hf/bin/ffprobe"
exec hyperframes "$@"
