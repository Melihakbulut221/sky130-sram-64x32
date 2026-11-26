#!/usr/bin/env python3
"""Neural narration with Kokoro (runs locally; needs Python >= 3.10 with kokoro-onnx + soundfile).

usage: tts_kokoro.py <model_dir> <jobs.json>      jobs.json = [{"text":..., "out":..., "speed":...}, ...]
Each sentence is synthesized on its own and trimmed, so the caller controls every pause.
Same voice and method as the earlier pll_explained.mp4 video (voice am_michael).
"""
import json, sys, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

VOICE = os.environ.get("KOKORO_VOICE", "am_michael")


def trim(a, sr, thr=0.012, pad=0.03):
    idx = np.nonzero(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a
    return a[max(0, idx[0] - int(pad * sr)): idx[-1] + int(pad * sr)]


k = Kokoro(os.path.join(sys.argv[1], "kokoro-v1.0.onnx"), os.path.join(sys.argv[1], "voices-v1.0.bin"))
for j in json.load(open(sys.argv[2])):
    a, sr = k.create(j["text"], voice=VOICE, speed=j.get("speed", 1.0), lang="en-us")
    sf.write(j["out"], trim(a, sr), sr, subtype="PCM_16")
