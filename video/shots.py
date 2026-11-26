"""Layout pictures: frames rendered with KLayout's drawing engine (no window), with annotation
boxes on top and smooth zoom animations."""
import io
import math
import os

import klayout.db as kdb
import klayout.lay as lay
from PIL import Image, ImageDraw

from . import style as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LYP = os.environ.get("SKY130_LYP", os.path.join(os.path.dirname(ROOT), "pll_sky130", "pdk", "sky130A", "libs.tech",
                                               "klayout", "tech", "sky130A.lyp"))

# GDS (layer, datatype) groups of SKY130
G = {
    "well": {(64, 20)}, "imp": {(93, 44), (94, 20), (78, 44)}, "diff": {(65, 20), (65, 44)},
    "poly": {(66, 20)}, "con": {(66, 44), (95, 20)}, "li": {(67, 20)},
    "m1": {(67, 44), (68, 20)}, "m2": {(68, 44), (69, 20)}, "m3": {(69, 44), (70, 20)},
    "m4": {(70, 44), (71, 20)}, "m5": {(71, 44), (72, 20)},
}
ALL = set().union(*G.values())
SIZE = (S.CONTENT[2] - S.CONTENT[0], S.CONTENT[3] - S.CONTENT[1])     # 1824 x 804


def layers(*names):
    return set().union(*(G[n] for n in names))


class Shots:
    def __init__(self, gds):
        self.view = lay.LayoutView()
        self.view.load_layout(gds, True)
        self.view.load_layer_props(LYP)
        self.view.max_hier()
        self.view.set_config("background-color", S.hexc(S.BG))
        self.view.set_config("grid-visible", "false")
        self.view.set_config("text-visible", "false")
        self._vis = None
        self.set_layers(ALL)
        b = self.view.active_cellview().cell.dbbox()
        self.full = (b.left, b.bottom, b.right, b.top)

    def set_layers(self, keys):
        keys = frozenset(keys)
        if keys == self._vis:
            return
        it = self.view.begin_layers()
        while not it.at_end():
            lp = it.current()
            lp.visible = (lp.source_layer, lp.source_datatype) in keys
            it.next()
        self._vis = keys

    def image(self, box, size=SIZE, keys=ALL):
        """box: (x1, y1, x2, y2) in micrometres. Returns (PIL image, the box actually shown)."""
        self.set_layers(keys)
        w, h = size
        self.view.resize(w, h)
        self.view.zoom_box(kdb.DBox(*box))
        buf = self.view.get_pixels(w, h)
        im = Image.open(io.BytesIO(buf.to_png_data())).convert("RGB")
        b = self.view.box()
        return im, (b.left, b.bottom, b.right, b.top)


def fit(box, size=SIZE, margin=0.04):
    """Grow a box to the aspect ratio of the frame (centre fixed)."""
    x1, y1, x2, y2 = box
    w, h = (x2 - x1) * (1 + margin), (y2 - y1) * (1 + margin)
    ar = size[0] / size[1]
    if w / h < ar:
        w = h * ar
    else:
        h = w / ar
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def lerp_box(a, b, t):
    """Smooth transition between two boxes: exponential in scale, centre follows the scale."""
    t = 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, t)))       # ease in-out
    wa, wb = a[2] - a[0], b[2] - b[0]
    ha, hb = a[3] - a[1], b[3] - b[1]
    w = wa * (wb / wa) ** t
    h = ha * (hb / ha) ** t
    # move the centre in proportion to the scale change, so the target does not drift while zooming
    s = (w - wa) / (wb - wa) if abs(wb - wa) > 1e-9 else t
    cx = (a[0] + a[2]) / 2 + ((b[0] + b[2]) / 2 - (a[0] + a[2]) / 2) * s
    cy = (a[1] + a[3]) / 2 + ((b[1] + b[3]) / 2 - (a[1] + a[3]) / 2) * s
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def annotate(im, actual, items, size=SIZE):
    """items: (x1, y1, x2, y2, label, colour[, where]) in micrometres."""
    im = im.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    L, B, R, T_ = actual
    sx, sy = size[0] / (R - L), size[1] / (T_ - B)
    f = S.font(24, bold=True)

    def px(it):
        x1, y1, x2, y2 = it[:4]
        return (x1 - L) * sx, (T_ - y2) * sy, (x2 - L) * sx, (T_ - y1) * sy

    for it in items:                       # fills first, so a later fill does not erase an earlier outline
        d.rectangle(list(px(it)), fill=it[5] + (30,))
    for it in items:
        px1, py1, px2, py2 = px(it)
        label, col = it[4], it[5]
        where = it[6] if len(it) > 6 else "top"
        d.rectangle([px1, py1, px2, py2], outline=col + (255,), width=4)
        if label:
            tw = d.textlength(label, font=f)
            tx = min(max(px1, 4), size[0] - tw - 20)
            ty = py1 - 40 if where == "top" else py2 + 6
            if where == "in":
                tx, ty = px1 + 8, py1 + 8
            ty = min(max(ty, 2), size[1] - 38)
            d.rectangle([tx, ty, tx + tw + 16, ty + 36], fill=(8, 11, 16, 240), outline=col + (255,), width=2)
            d.text((tx + 8, ty + 3), label, font=f, fill=col + (255,))
    return Image.alpha_composite(im, ov).convert("RGB")
