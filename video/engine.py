"""Video engine: list of steps -> narration (Kokoro neural TTS, local) + frames -> MP4.

Each Step is one visual plus one paragraph of narration. The paragraph is split into
sentences and every sentence is synthesised on its own, so captions and audio stay in
sync by construction. Frames are streamed raw into a single ffmpeg process.

Voice: Kokoro "am_michael" at speed 1.07.
env: TTS_PY     = a Python >= 3.10 that has kokoro-onnx and soundfile installed
     KOKORO_DIR = folder with kokoro-v1.0.onnx and voices-v1.0.bin (default: tools/kokoro)
"""
import hashlib
import json
import os
import re
import subprocess
import wave
from dataclasses import dataclass, field

import imageio_ffmpeg
import numpy as np
from PIL import Image

from . import style as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "video", "tts_cache_en")
VOICE, SPEED = "am_michael", 1.07
SR = 24000
GAP = 0.30            # pause after a sentence (s)
SCENE_GAP = 0.55      # extra pause when the visual changes
XFADE = 9             # cross-fade length when the visual changes (frames)
TTS_WORKERS = 4
TTS_PY = os.environ.get("TTS_PY", "python3")
KOKORO_DIR = os.environ.get("KOKORO_DIR", os.path.join(ROOT, "tools", "kokoro"))


@dataclass
class Step:
    visual: object                # PIL.Image (1920x1080, no caption) or Anim
    text: str
    section: str = ""


@dataclass
class Anim:
    fn: object                    # fn(u in [0,1]) -> PIL.Image (full frame, no caption)
    dur: float = 3.0              # animation length; the last frame is held afterwards
    _last: object = None
    _t0: float = None             # when the animation started (the visual may be reused by the next step)


# ---------------------------------------------------------------------------
# Spelling -> pronunciation: what only the speech engine sees
# ---------------------------------------------------------------------------
SAY = [
    (r"SKY130", "Sky one thirty"), (r"\bSRAM\b", "S ram"), (r"\b6T\b", "six T"),
    (r"\bNMOS\b", "N moss"), (r"\bPMOS\b", "P moss"), (r"\bMOS\b", "moss"),
    (r"\bSPICE\b", "spice"), (r"\bngspice\b", "N G spice"), (r"\bKLayout\b", "K layout"),
    (r"\bLibreLane\b", "Libre Lane"), (r"\bOpenROAD\b", "Open Road"), (r"\bYosys\b", "Yo sis"), (r"\bNetgen\b", "Net gen"),
    (r"\bPDK\b", "P D K"), (r"\bDRC\b", "D R C"), (r"\bLVS\b", "L V S"), (r"\bGDS\b", "G D S"), (r"\bRTL\b", "R T L"),
    (r"\bLEF\b", "leff"), (r"\bVDD\b", "V D D"), (r"\bGND\b", "ground"),
    (r"\bMHz\b", "megahertz"), (r"\bµm\b", "microns"), (r"\bµA\b", "microamps"), (r"\bmA\b", "milliamps"),
    (r"\bmV\b", "millivolts"), (r"\bfF\b", "femtofarads"), (r"\bns\b", "nanoseconds"), (r"\bps\b", "picoseconds"),
    (r"\bnm\b", "nanometer"), (r"(?<=\d) V\b", " volts"),
    (r"\bn-well\b", "N well"), (r"\bn type\b", "N type"), (r"\bp type\b", "P type"),
    (r"×", " by "), (r"≈", " about "), (r"→", " to "), (r"–", " to "), (r"·", " "), (r"%", " percent"),
]


def speech(text):
    for pat, rep in SAY:
        text = re.sub(pat, rep, text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def wav_path(sentence):
    key = hashlib.sha1(f"{VOICE}|{SPEED}|{speech(sentence)}".encode()).hexdigest()[:16]
    return os.path.join(CACHE, key + ".wav")


def synthesize(all_sentences):
    """Synthesise every sentence that is not cached yet, with a few Kokoro processes in parallel."""
    os.makedirs(CACHE, exist_ok=True)
    jobs, seen = [], set()
    for sen in all_sentences:
        out = wav_path(sen)
        if out not in seen and not os.path.exists(out):
            jobs.append({"text": speech(sen), "out": out, "speed": SPEED})
        seen.add(out)
    if not jobs:
        return 0
    script = os.path.join(ROOT, "video", "tts_kokoro.py")
    procs = []
    for w in range(TTS_WORKERS):
        chunk = jobs[w::TTS_WORKERS]
        if not chunk:
            continue
        jpath = os.path.join(CACHE, f"jobs_{w}.json")
        with open(jpath, "w") as f:
            json.dump(chunk, f)
        procs.append(subprocess.Popen([TTS_PY, script, KOKORO_DIR, jpath], env=dict(os.environ, KOKORO_VOICE=VOICE)))
    for p in procs:
        assert p.wait() == 0, "Kokoro TTS failed"
    return len(jobs)


def tts(sentence):
    """Read the cached narration of one sentence as int16 samples."""
    with wave.open(wav_path(sentence)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def timeline(steps):
    """(step index, sentence, start_s, duration_s) for every sentence, plus the joined audio."""
    synthesize([sen for st in steps for sen in sentences(st.text)])
    audio, items, t = [], [], 0.0
    prev_vis = None
    lead = np.zeros(int(SR * 0.6), dtype=np.int16)
    audio.append(lead)
    t += len(lead) / SR
    for si, st in enumerate(steps):
        if prev_vis is not None and st.visual is not prev_vis:
            pad = np.zeros(int(SR * SCENE_GAP), dtype=np.int16)
            audio.append(pad)
            t += len(pad) / SR
            items[-1][3] += len(pad) / SR
        prev_vis = st.visual
        for sen in sentences(st.text):
            a = tts(sen)
            a = np.concatenate([a, np.zeros(int(SR * GAP), dtype=np.int16)])
            items.append([si, sen, t, len(a) / SR])
            audio.append(a)
            t += len(a) / SR
    tail = np.zeros(int(SR * 1.5), dtype=np.int16)
    audio.append(tail)
    items[-1][3] += 1.5
    return items, np.concatenate(audio)


def render(steps, out_path, preview_dir=None, limit=None):
    items, audio = timeline(steps)
    total = len(audio) / SR
    wav_path = out_path.replace(".mp4", ".wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(audio.tobytes())
    srt = []
    for k, (si, sen, t0, dur) in enumerate(items):
        def ts(x):
            h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
            return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
        srt.append(f"{k + 1}\n{ts(t0)} --> {ts(t0 + dur - GAP * 0.5)}\n{sen}\n")
    with open(out_path.replace(".mp4", ".srt"), "w") as f:
        f.write("\n".join(srt))

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{S.W}x{S.H}", "-r", str(S.FPS), "-i", "-", "-i", wav_path,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n_total = int(round(total * S.FPS))
    frame_no = 0
    prev_arr, prev_vis = None, None
    step_start = {}
    for si, sen, t0, dur in items:
        step_start.setdefault(si, t0)
    try:
        for k, (si, sen, t0, dur) in enumerate(items):
            if limit and frame_no > limit:
                break
            st = steps[si]
            end_frame = n_total if k == len(items) - 1 else int(round((t0 + dur) * S.FPS))
            if k == 0:
                end_frame = max(end_frame, 1)
            base_cache = {}

            def frame_at(fi):
                if isinstance(st.visual, Anim):
                    if st.visual._t0 is None:
                        st.visual._t0 = step_start[si]
                    u = (fi / S.FPS - st.visual._t0) / st.visual.dur
                    if u >= 1.0:
                        if st.visual._last is None:
                            st.visual._last = st.visual.fn(1.0)
                        base = st.visual._last
                        key = "last"
                    else:
                        base, key = st.visual.fn(max(0.0, u)), None
                else:
                    base, key = st.visual, "still"
                if key and key in base_cache:
                    return base_cache[key]
                arr = np.asarray(S.caption(base, sen), dtype=np.uint8)
                if key:
                    base_cache[key] = arr
                return arr

            changed = prev_vis is not None and st.visual is not prev_vis
            j = 0
            while frame_no < end_frame:
                arr = frame_at(frame_no)
                if changed and j < XFADE and prev_arr is not None:
                    a = (j + 1) / (XFADE + 1)
                    out = (prev_arr.astype(np.float32) * (1 - a) + arr.astype(np.float32) * a).astype(np.uint8)
                else:
                    out = arr
                proc.stdin.write(out.tobytes())
                frame_no += 1
                j += 1
            prev_arr, prev_vis = frame_at(frame_no - 1), st.visual
            if preview_dir and (k == 0 or steps[items[k - 1][0]].visual is not st.visual):
                os.makedirs(preview_dir, exist_ok=True)
                Image.fromarray(prev_arr).resize((960, 540)).save(
                    os.path.join(preview_dir, f"s{si:03d}.jpg"), quality=80)
    finally:
        proc.stdin.close()
        proc.wait()
    return total, len(items), frame_no
