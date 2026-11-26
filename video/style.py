"""Shared visual language of the video frames: colours, fonts, frame skeleton."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30

BG = (13, 17, 23)
PANEL = (22, 27, 34)
PANEL2 = (30, 37, 46)
LINE = (48, 54, 61)
FG = (230, 237, 243)
MUTED = (139, 148, 158)
BLUE = (88, 166, 255)
GREEN = (63, 185, 80)
ORANGE = (210, 153, 34)
RED = (248, 81, 73)
PURPLE = (188, 140, 255)
CYAN = (57, 197, 207)
YELLOW = (227, 179, 65)

HEADER_H = 96
CAPTION_Y = 936
CONTENT = (48, HEADER_H + 20, W - 48, CAPTION_Y - 16)     # x1, y1, x2, y2

_SF = "/System/Library/Fonts/SFNS.ttf"
_MONO = "/System/Library/Fonts/Menlo.ttc"
_HN = "/System/Library/Fonts/HelveticaNeue.ttc"
_cache = {}


def font(size, kind="sans", bold=False):
    key = (size, kind, bold)
    if key not in _cache:
        if kind == "mono":
            _cache[key] = ImageFont.truetype(_MONO, size, index=1 if bold else 0)
        else:
            f = ImageFont.truetype(_SF, size)          # SF also has arrows and maths symbols
            f.set_variation_by_name(b"Bold" if bold else b"Regular")
            _cache[key] = f
    return _cache[key]


def hexc(c):
    return "#%02x%02x%02x" % c


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def frame(section, title, progress=0.0):
    """Empty frame with the header band drawn."""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, HEADER_H], fill=PANEL)
    d.rectangle([0, HEADER_H - 3, W, HEADER_H], fill=LINE)
    d.rectangle([0, HEADER_H - 3, int(W * progress), HEADER_H], fill=BLUE)
    d.text((48, 16), section.upper(), font=font(22, bold=True), fill=BLUE)
    d.text((48, 44), title, font=font(36, bold=True), fill=FG)
    tag = "SKY130 SRAM  ·  64 × 32 bit  ·  6T"
    d.text((W - 48 - d.textlength(tag, font=font(22)), 34), tag, font=font(22), fill=MUTED)
    return im


def caption(im, text):
    """Caption band (the sentence being spoken)."""
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.rectangle([0, CAPTION_Y, W, H], fill=(8, 11, 16))
    d.rectangle([0, CAPTION_Y, W, CAPTION_Y + 2], fill=LINE)
    f = font(31)
    lines = wrap(d, text, f, W - 200)
    if len(lines) > 3:
        f = font(27)
        lines = wrap(d, text, f, W - 160)
    lh = f.size + 10
    y = CAPTION_Y + (H - CAPTION_Y - lh * len(lines)) // 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=f)) // 2, y), ln, font=f, fill=FG)
        y += lh
    return im


def paste_fit(im, content, box=CONTENT, align="center"):
    """Fit an image into a box, keeping its aspect ratio, and paste it."""
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    s = min(bw / content.width, bh / content.height)
    if abs(s - 1) > 1e-3:
        content = content.resize((max(1, int(content.width * s)), max(1, int(content.height * s))),
                                 Image.LANCZOS)
    ox = x1 + (bw - content.width) // 2 if align == "center" else x1
    oy = y1 + (bh - content.height) // 2
    im.paste(content, (ox, oy), content if content.mode == "RGBA" else None)
    return im


def bullets(im, items, box, size=34, gap=18, color=FG):
    """Bullet list. items: str | (str, colour) | ('h', heading)."""
    d = ImageDraw.Draw(im)
    x1, y1, x2, _ = box
    y = y1
    for it in items:
        col, head = color, False
        if isinstance(it, tuple):
            if it[0] == "h":
                head, it = True, it[1]
            else:
                it, col = it
        if head:
            f = font(size + 4, bold=True)
            d.text((x1, y), it, font=f, fill=BLUE)
            y += f.size + gap
            continue
        f = font(size)
        lines = wrap(d, it, f, x2 - x1 - 44)
        d.ellipse([x1 + 6, y + size // 2 - 6, x1 + 18, y + size // 2 + 6], fill=col if col != FG else BLUE)
        for ln in lines:
            d.text((x1 + 44, y), ln, font=f, fill=col)
            y += f.size + 8
        y += gap
    return im


def panel(im, box, fill=PANEL, outline=LINE, radius=14):
    ImageDraw.Draw(im).rounded_rectangle(list(box), radius=radius, fill=fill, outline=outline, width=2)
    return im
