"""Generate the HyperFrames projects for the video (HTML + GSAP, rendered to MP4 by HyperFrames).

    python -m video_hf.build full       -> video_hf/full/    (index.html + assets/), video_hf/sram_sky130_video.srt
    python -m video_hf.build short      -> video_hf/short/   the two-minute cut
    python -m video_hf.build srt full   -> only the subtitles
    video_hf/hf.sh lint   video_hf/full
    video_hf/hf.sh render video_hf/full -o out/sram_sky130_video.mp4 --crf 21

The narration is the clock: every sentence is synthesised on its own (video/engine.py, Kokoro),
so its start time is known exactly, and every scene receives the start times of its sentences
as cues for its animation.
"""
import html
import json
import os
import subprocess
import sys
import wave

import numpy as np

from video import engine as E

from . import assets as A
from . import script as SC
from .scenes import CSS, HELPERS
from .scenes2 import CSS2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEAD = 0.35            # a scene starts this long before its first spoken word
TAIL = 1.2             # hold after the last word


def narration(scenes):
    """Timeline of all sentences: returns (per-scene list of (sentence, start, duration), audio samples)."""
    steps = [E.Step(object(), " ".join(" ".join(sc["text"]).split())) for sc in scenes]
    items, audio = E.timeline(steps)
    per = [[] for _ in scenes]
    for si, sen, t0, dur in items:
        per[si].append((sen, t0, dur))
    return per, audio


def write_audio(audio, path):
    wav = path + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(E.SR)
        w.writeframes(audio.tobytes())
    ff = os.path.join(ROOT, "tools", "hf", "bin", "ffmpeg")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:a", "aac", "-b:a", "160k", path], check=True)
    os.remove(wav)


NAMES = {"full": "sram_sky130_video", "short": "sram_sky130_short"}


def write_srt(per, path):
    """Subtitles: one entry per spoken sentence."""
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    out, k = [], 0
    for p in per:
        for sen, t0, dur in p:
            k += 1
            out.append(f"{k}\n{ts(t0)} --> {ts(t0 + dur - E.GAP * 0.5)}\n{sen}\n")
    with open(path, "w") as f:
        f.write("\n".join(out))


def srt(variant):
    """Only the subtitles (video_hf/<name>.srt); the narration comes from the cache."""
    per, _ = narration(SC.SCRIPTS[variant](A.chart_data()))
    path = os.path.join(ROOT, "video_hf", NAMES[variant] + ".srt")
    write_srt(per, path)
    print(path)


def build(variant):
    proj = os.path.join(ROOT, "video_hf", variant)
    adir = os.path.join(proj, "assets")
    os.makedirs(adir, exist_ok=True)
    pics = A.layout_pictures(adir)
    data = A.chart_data()
    scenes = SC.SCRIPTS[variant](data)
    per, audio = narration(scenes)
    total = len(audio) / E.SR
    write_audio(audio, os.path.join(adir, "narration.m4a"))
    write_srt(per, os.path.join(ROOT, "video_hf", NAMES[variant] + ".srt"))

    starts = [max(0.0, p[0][1] - LEAD) for p in per]
    starts[0] = 0.0
    ends = starts[1:] + [total]
    body, js, caps = [], [], []
    for k, (sc, p) in enumerate(zip(scenes, per)):
        t0, dur = starts[k], ends[k] - starts[k]
        cues = [round(t - t0, 3) for (_, t, _) in p]
        sid = f"s{k}"
        markup, script = sc["fn"](sid, dur, cues, pics, data, **sc.get("args", {}))
        body.append(f'<section id="{sid}" class="clip scene" data-start="{t0:.3f}" data-duration="{dur:.3f}" data-track-index="1">'
                    f'<div class="stage" id="{sid}-st">{markup}</div></section>')
        js.append(f"(function(T, D, c, P) {{\n  STAGE(P, T, D, {str(k == len(scenes) - 1).lower()});\n{script}\n}})({t0:.3f}, {dur:.3f}, {json.dumps(cues)}, '#{sid}');")
        for j, (sen, t, d) in enumerate(p):
            cid = f"cap{k}_{j}"
            end = min(t + d, total)
            words = "".join(f'<span class="cw">{html.escape(w)} </span>' for w in sen.split())
            caps.append(f'<div id="{cid}" class="clip cap" data-start="{t:.3f}" data-duration="{end - t:.3f}" data-track-index="3">'
                        f'<p id="{cid}-p">{words}</p></div>')
            js.append(f'CAP("#{cid}-p", {t:.3f}, {end - t:.3f});')

    page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>{CSS}{CSS2}</style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="1920" data-height="1080">
      <div id="bg" data-layout-ignore></div>
      {''.join(body)}
      <div id="capband" data-layout-ignore></div>
      {''.join(caps)}
      <div id="progress" class="clip" data-start="0" data-duration="{total:.3f}" data-track-index="4" data-layout-ignore><i id="progress-bar"></i></div>
      <audio id="narration" class="clip" data-start="0" data-duration="{total:.3f}" data-track-index="5" data-volume="1" src="assets/narration.m4a"></audio>
    </div>
    <script>
const DATA = {json.dumps(data, separators=(",", ":"))};
{HELPERS}
tl.fromTo("#progress-bar", {{scaleX: 0}}, {{scaleX: 1, duration: {total:.3f}, ease: "none"}}, 0);
{chr(10).join(js)}
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
tl.seek(0);
    </script>
  </body>
</html>
"""
    with open(os.path.join(proj, "index.html"), "w") as f:
        f.write(page)
    json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
               "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}},
              open(os.path.join(proj, "hyperframes.json"), "w"), indent=2)
    json.dump({"scenes": [dict(id=f"s{k}", kind=sc["fn"].__name__, start=round(starts[k], 3), end=round(ends[k], 3),
                               cues=[round(t, 3) for (_, t, _) in per[k]]) for k, sc in enumerate(scenes)], "duration": total},
              open(os.path.join(proj, "timeline.json"), "w"), indent=1)
    print(f"{variant}: {len(scenes)} scenes, {sum(len(p) for p in per)} sentences, {total / 60:.2f} min ({total:.1f} s) -> {proj}")
    return proj


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "srt":
        srt(sys.argv[2])
    else:
        build(sys.argv[1] if len(sys.argv) > 1 else "short")
