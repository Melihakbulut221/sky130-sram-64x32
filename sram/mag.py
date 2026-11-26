"""Minimal writer for Magic (.mag) layout files.

All coordinates are integers in nanometres on a 5 nm grid. Magic composes paint in file
order exactly like interactive painting does: poly over ndiff becomes an nMOS channel,
a contact painted over diffusion replaces it, and contacts on adjacent planes stack.
So a cell is described with a handful of rectangles per layer.
"""
import os

GRID = 5          # nm per Magic internal unit (magscale 1 2 with lambda = 10 nm)


def _u(v):
    assert v % GRID == 0, f"off-grid coordinate {v}"
    return v // GRID


class Cell:
    def __init__(self, name):
        self.name = name
        self.shapes = []          # (layer, x1, y1, x2, y2) in paint order
        self.labels = []          # (layer, x1, y1, x2, y2, text, is_port, cls, use)
        self.uses = []            # (child Cell, inst name, x, y, mx, my, array or None)
        self.bbox = None          # abutment box (x1, y1, x2, y2), optional
        self.props = {}

    # ---------------------------------------------------------------- paint
    def rect(self, layer, x1, y1, x2, y2):
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        assert x2 > x1 and y2 > y1, (layer, x1, y1, x2, y2)
        self.shapes.append((layer, x1, y1, x2, y2))
        return (x1, y1, x2, y2)

    def box(self, layer, cx, cy, w, h):
        """Rectangle given by centre and size."""
        return self.rect(layer, cx - w // 2, cy - h // 2, cx - w // 2 + w, cy - h // 2 + h)

    def label(self, layer, x1, y1, x2, y2, text, port=True, cls="bidirectional", use="signal"):
        self.labels.append((layer, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), text, port, cls, use))

    def place(self, child, name, x=0, y=0, mx=False, my=False, array=None):
        """Instantiate `child` with its origin at (x, y).

        mx mirrors left-right (about the child's y axis), my mirrors top-bottom, both applied
        before the translation. array = (nx, pitch_x, ny, pitch_y).
        """
        self.uses.append((child, name, x, y, mx, my, array))

    # ---------------------------------------------------------------- output
    def extent(self):
        """Bounding box of the paint of this cell and everything below it."""
        xs1, ys1, xs2, ys2 = [], [], [], []
        for (_, x1, y1, x2, y2) in self.shapes:
            xs1.append(x1); ys1.append(y1); xs2.append(x2); ys2.append(y2)
        for (child, _, x, y, mx, my, arr) in self.uses:
            cx1, cy1, cx2, cy2 = child.extent()
            if mx:
                cx1, cx2 = -cx2, -cx1
            if my:
                cy1, cy2 = -cy2, -cy1
            nx, px, ny, py = arr if arr else (1, 0, 1, 0)
            xs1.append(x + cx1); ys1.append(y + cy1)
            xs2.append(x + cx2 + (nx - 1) * px); ys2.append(y + cy2 + (ny - 1) * py)
        return min(xs1), min(ys1), max(xs2), max(ys2)

    def children(self, acc=None):
        acc = {} if acc is None else acc
        for (child, *_rest) in self.uses:
            if child.name not in acc:
                child.children(acc)
                acc[child.name] = child
        return acc

    def text(self):
        out = ["magic", "tech sky130A", "magscale 1 2", "timestamp 1"]
        cur = None
        for (layer, x1, y1, x2, y2) in self.shapes:
            if layer != cur:
                out.append(f"<< {layer} >>")
                cur = layer
            out.append(f"rect {_u(x1)} {_u(y1)} {_u(x2)} {_u(y2)}")
        for (child, name, x, y, mx, my, arr) in self.uses:
            out.append(f"use {child.name} {name}")
            if arr:
                nx, px, ny, py = arr
                out.append(f"array 0 {nx - 1} {_u(px)} 0 {ny - 1} {_u(py)}")
            out.append("timestamp 1")
            out.append(f"transform {-1 if mx else 1} 0 {_u(x)} 0 {-1 if my else 1} {_u(y)}")
            cx1, cy1, cx2, cy2 = child.extent()
            out.append(f"box {_u(cx1)} {_u(cy1)} {_u(cx2)} {_u(cy2)}")
        if self.labels:
            out.append("<< labels >>")
            index = {}                      # labels with the same text are one port (one LEF pin)
            for (layer, x1, y1, x2, y2, text, port, cls, use) in self.labels:
                out.append(f"flabel {layer} {_u(x1)} {_u(y1)} {_u(x2)} {_u(y2)} 0 FreeSans 80 0 0 0 {text}")
                if port:
                    n = index.setdefault(text, len(index) + 1)
                    out.append(f"port {n} nsew {use} {cls}")
        props = dict(self.props)
        if self.bbox:
            props["FIXED_BBOX"] = " ".join(str(_u(v)) for v in self.bbox)
        if props:
            out.append("<< properties >>")
            for k, v in props.items():
                out.append(f"string {k} {v}")
        out.append("<< end >>")
        return "\n".join(out) + "\n"

    def write(self, directory):
        """Write this cell and every cell below it."""
        os.makedirs(directory, exist_ok=True)
        cells = self.children()
        cells[self.name] = self
        for c in cells.values():
            with open(os.path.join(directory, c.name + ".mag"), "w") as f:
                f.write(c.text())
        return sorted(cells)
