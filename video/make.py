"""Build the video and the layout pictures of the documentation.

    python -m video.make docs         -> docs/img/layout_*.png
    python -m video.make storyboard   -> video/preview/steps/*.jpg (no audio, no encoding)
    python -m video.make length       -> synthesise the narration and print the running time
    python -m video.make render       -> out/sram_sky130_video.mp4 (English, Kokoro voice)
Add "short" to storyboard / length / render for the two-minute cut (video/script_short.py,
out/sram_sky130_short.mp4).
"""
import os
import subprocess
import sys
import time

from PIL import Image

from . import engine as E
from . import style as S

ROOT = E.ROOT
VARIANTS = {"full": ("video.script", "sram_sky130_video", ""), "short": ("video.script_short", "sram_sky130_short", "_short")}


def _steps(variant):
    import importlib
    return importlib.import_module(VARIANTS[variant][0]).build_steps()


def docs():
    from . import script as L
    from . import shots as SH
    d = os.path.join(ROOT, "docs", "img")
    os.makedirs(d, exist_ok=True)
    size = (1824, 804)

    def shot(name, box, keys=SH.ALL, ann=(), margin=0.04):
        im, act = L.SHOTS.image(SH.fit(box, size, margin), size, keys)
        if ann:
            im = SH.annotate(im, act, ann, size)
        im.save(os.path.join(d, name + ".png"))
        print("ok", name)

    shot("layout_cell", L.CB, ann=[(L.CELL[0], L.CELL[1], L.CELL[2], L.CELL[3], f"one cell: {L.CW:.2f} × {L.CH:.2f} µm", S.YELLOW)])
    shot("layout_cell_fe", L.CB, SH.layers("well", "diff", "poly", "con", "li"))
    shot("layout_array", (L.AX - 2.6, L.AY - 1.2, L.AX + 6 * L.CW, L.AY + L.SH_ + 8 * L.CH))
    shot("layout_macro", L.MACRO)
    shot("layout_chip", L.FULL, ann=[(L.MACRO[0], L.MACRO[1], L.MACRO[2], L.MACRO[3], "6T array (custom)", S.YELLOW, "in"),
                                     (6, L.MY, L.MX - 1, L.MY + L.R["macro_h"], "row decoder", S.CYAN, "in"),
                                     (6, 11, L.FULL[2] - 6, L.MY - 1, "column circuits, input registers, clocking (standard cells)", S.PURPLE, "in")])
    shot("layout_columns", (L.MX + 2, L.MY - 26, L.MX + 60, L.MY + 6))


def storyboard(variant="full"):
    steps = _steps(variant)
    sfx = VARIANTS[variant][2]
    d = os.path.join(ROOT, "video", "preview", "steps" + sfx)
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    words, prev, k, thumbs = 0, None, 0, []
    for i, st in enumerate(steps):
        sens = E.sentences(st.text)
        words += len(st.text.split())
        if st.visual is prev:
            continue
        prev = st.visual
        vis = st.visual.fn(1.0) if isinstance(st.visual, E.Anim) else st.visual
        im = S.caption(vis, sens[0])
        im.save(os.path.join(d, f"{i:03d}.jpg"), quality=88)
        thumbs.append(im.resize((480, 270)))
        k += 1
    for s in range(0, len(thumbs), 16):
        sheet = Image.new("RGB", (480 * 4, 270 * 4), S.BG)
        for j, t in enumerate(thumbs[s:s + 16]):
            sheet.paste(t, (480 * (j % 4), 270 * (j // 4)))
        sheet.save(os.path.join(ROOT, "video", "preview", f"sheet{sfx}{s // 16}.jpg"), quality=85)
    nsen = sum(len(E.sentences(s.text)) for s in steps)
    print(f"steps: {len(steps)}  distinct visuals: {k}  sentences: {nsen}  words: {words}  estimated length: {words * 0.38 / 60:.1f} min")


def normalize(path):
    """Loudness-normalise the narration (EBU R128, -16 LUFS) without re-encoding the picture."""
    import imageio_ffmpeg
    tmp = path.replace(".mp4", "_norm.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", path, "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, path)
    wav = path.replace(".mp4", ".wav")
    if os.path.exists(wav):
        os.remove(wav)


def render(variant="full"):
    t0 = time.time()
    steps = _steps(variant)
    print(f"visuals ready: {time.time() - t0:.0f} s")
    out = os.path.join(ROOT, "out", VARIANTS[variant][1] + ".mp4")
    total, nsen, nfr = E.render(steps, out, preview_dir=os.path.join(ROOT, "video", "preview", "final" + VARIANTS[variant][2]))
    normalize(out)
    print(f"length: {total / 60:.2f} min ({total:.1f} s)  sentences: {nsen}  frames: {nfr}  wall time: {time.time() - t0:.0f} s")
    print(out)


def length(variant="full"):
    steps = _steps(variant)
    items, audio = E.timeline(steps)
    print(f"steps: {len(steps)}  sentences: {len(items)}  words: {sum(len(s.text.split()) for s in steps)}  "
          f"length: {len(audio) / E.SR / 60:.2f} min ({len(audio) / E.SR:.1f} s)")


if __name__ == "__main__":
    {"docs": docs, "storyboard": storyboard, "render": render, "length": length}[sys.argv[1]](*sys.argv[2:3])
