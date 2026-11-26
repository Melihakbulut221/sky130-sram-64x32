"""Source-code panels: lines taken from the real files, syntax colouring, and a highlight
band that follows the narration."""
import os

from PIL import Image, ImageDraw
from pygments import lex
from pygments.lexers import PythonLexer, get_lexer_by_name
from pygments.token import Token

from . import style as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOK = [
    (Token.Comment, S.MUTED), (Token.Literal.String.Doc, (122, 162, 122)),
    (Token.Literal.String, (165, 214, 255)), (Token.Literal.Number, (121, 192, 255)),
    (Token.Keyword, (255, 123, 114)), (Token.Name.Function, (210, 168, 255)),
    (Token.Name.Class, (240, 190, 110)), (Token.Name.Decorator, (210, 168, 255)),
    (Token.Name.Builtin, (121, 192, 255)), (Token.Operator.Word, (255, 123, 114)),
    (Token.Operator, (200, 205, 215)),
]


def color_of(tok):
    for t, c in TOK:
        if tok in t:
            return c
    return S.FG


def excerpt(path, start, n=None, end=None):
    """Take n lines of a file starting at the first line that contains 'start' (or up to the
    line that contains 'end'). Returns (first_line_number, [lines])."""
    with open(os.path.join(ROOT, path)) as f:
        lines = f.read().split("\n")
    i0 = next(i for i, l in enumerate(lines) if start in l)
    if end is not None:
        i1 = next(i for i in range(i0 + 1, len(lines)) if end in lines[i])
    else:
        i1 = i0 + n
    return i0 + 1, lines[i0:i1]


def code_panel(path, start, n=None, end=None, hl=(), size=(1180, 790), fs=None, lang="python",
               title=None, skip=()):
    """Code panel. hl: lines to highlight, as local index ranges [(a, b)] or as strings to look
    for in a line. skip: local line indices to leave out."""
    first, lines = excerpt(path, start, n, end)
    while lines and not lines[-1].strip():          # drop trailing blank lines
        lines.pop()
    ind = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    lines = [l[ind:] for l in lines]                # remove the common indentation
    idx = [i for i in range(len(lines)) if i not in skip]
    w, h = size
    pad_top = 58
    if fs is None:
        longest = max(len(lines[i]) for i in idx) + 6
        fs = 25
        while fs > 15:
            f = S.font(fs, "mono")
            cw = f.getlength("M")
            if cw * longest <= w - 40 and (fs + 9) * len(idx) <= h - pad_top - 16:
                break
            fs -= 1
    if fs < 18:
        print(f"  [warning] small code font fs={fs}: {path} '{start.strip()[:40]}' ({len(idx)} lines)")
    f = S.font(fs, "mono")
    cw, lh = f.getlength("M"), fs + 9
    im = Image.new("RGB", (w, h), S.PANEL)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=14, fill=S.PANEL, outline=S.LINE, width=2)
    d.rounded_rectangle([0, 0, w - 1, 44], radius=14, fill=S.PANEL2)
    d.rectangle([0, 30, w - 1, 44], fill=S.PANEL2)
    for k, c in enumerate((S.RED, S.YELLOW, S.GREEN)):
        d.ellipse([18 + 26 * k, 14, 34 + 26 * k, 30], fill=c)
    d.text((110, 10), title or path, font=S.font(22, "mono"), fill=S.MUTED)

    marks = set()
    for h_ in hl:
        if isinstance(h_, str):
            marks.update(i for i in idx if h_ in lines[i])
        else:
            marks.update(range(h_[0], h_[1] + 1))
    lexer = PythonLexer() if lang == "python" else get_lexer_by_name(lang)
    toks = list(lex("\n".join(lines), lexer))
    # token lists per line
    per_line, cur = [[]], 0
    for tok, val in toks:
        parts = val.split("\n")
        for j, part in enumerate(parts):
            if j:
                per_line.append([])
            if part:
                per_line[-1].append((tok, part))
    y = pad_top
    for i in idx:
        if i in marks:
            d.rectangle([4, y - 3, w - 5, y + lh - 5], fill=(46, 58, 40))
            d.rectangle([4, y - 3, 10, y + lh - 5], fill=S.GREEN)
        d.text((18, y), f"{first + i:4d}", font=f, fill=(90, 100, 112))
        x = 18 + cw * 6
        dim = bool(marks) and i not in marks
        for tok, part in (per_line[i] if i < len(per_line) else []):
            c = color_of(tok)
            if dim:
                c = tuple(int(v * 0.62 + b * 0.38) for v, b in zip(c, S.PANEL))
            d.text((x, y), part, font=f, fill=c)
            x += cw * len(part)
        y += lh
    return im


def terminal(text, size=(1180, 790), title="terminal", fs=None, hl=()):
    lines = text.rstrip("\n").split("\n")
    w, h = size
    if fs is None:
        fs = 25
        longest = max(len(l) for l in lines) + 2
        while fs > 14:
            f = S.font(fs, "mono")
            if f.getlength("M") * longest <= w - 40 and (fs + 9) * len(lines) <= h - 74:
                break
            fs -= 1
    f = S.font(fs, "mono")
    lh = fs + 9
    im = Image.new("RGB", (w, h), (10, 12, 16))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=14, fill=(10, 12, 16), outline=S.LINE, width=2)
    d.rounded_rectangle([0, 0, w - 1, 44], radius=14, fill=S.PANEL2)
    d.rectangle([0, 30, w - 1, 44], fill=S.PANEL2)
    for k, c in enumerate((S.RED, S.YELLOW, S.GREEN)):
        d.ellipse([18 + 26 * k, 14, 34 + 26 * k, 30], fill=c)
    d.text((110, 10), title, font=S.font(22, "mono"), fill=S.MUTED)
    y = 60
    for ln in lines:
        col = S.FG
        if ln.startswith("$"):
            col = S.BLUE
        elif any(k in ln for k in ("FAIL", "MISMATCH", "ERROR")):
            col = S.RED
        elif any(k in ln for k in ("PASS", "match uniquely", "TOTAL 0", "violations: 0", "[ok]", "errors=0")):
            col = S.GREEN
        if any(k in ln for k in hl):
            d.rectangle([4, y - 3, w - 5, y + lh - 5], fill=(46, 58, 40))
        d.text((20, y), ln, font=f, fill=col)
        y += lh
    return im
