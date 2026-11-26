"""More scene templates (used by the full-length video). Same conventions as scenes.py."""
import html
import os

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, get_lexer_by_name

from . import assets as A
from .scenes import J, R_, head

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS2 = """
.st-hero{position:absolute;left:96px;top:190px;font-size:190px;font-weight:900;letter-spacing:-.04em;white-space:nowrap}
.st-sub{position:absolute;left:104px;top:410px;font-size:40px;font-weight:700;color:var(--mut);white-space:nowrap}
.st-row{position:absolute;left:104px;font-size:36px;font-weight:700;white-space:nowrap}
.st-row b{display:inline-block;width:150px;color:var(--green)}
.codep{position:absolute;background:var(--panel);border:2px solid var(--line);border-radius:16px;overflow:hidden;font-family:'JetBrains Mono',monospace;padding:66px 0 24px}
.codep:before{content:"";position:absolute;left:0;top:0;right:0;height:46px;background:var(--panel2)}
.codep .fn{position:absolute;left:28px;top:9px;font-size:22px;color:var(--mut)}
.codep .ln{position:relative;white-space:pre;padding:0 30px;height:1.6em;line-height:1.6em}
.codep .hlb{position:absolute;left:0;right:0;background:rgba(63,185,80,.16);border-left:6px solid var(--green)}
.card{position:absolute;background:var(--panel);border:2px solid var(--line);border-radius:18px;padding:26px 30px}
.card h3{font-size:34px;font-weight:900;margin-bottom:6px}
.card p{font-size:26px;color:var(--mut);line-height:1.35}
.tb-h{position:absolute;top:200px;font-size:38px;font-weight:900}
.tb-s{position:absolute;top:252px;font-size:24px;color:var(--mut);white-space:nowrap}
.tb-l{position:absolute;left:96px;font-size:32px;color:var(--mut);white-space:nowrap}
.tb-v{position:absolute;font-size:44px;font-weight:900;white-space:nowrap}
.ls-n{position:absolute;left:96px;font-size:150px;font-weight:900;color:var(--blue);letter-spacing:-.04em}
.ls-h{position:absolute;left:330px;font-size:76px;font-weight:900;letter-spacing:-.03em;white-space:nowrap}
.ls-p{position:absolute;left:334px;font-size:34px;color:var(--mut);width:1400px;line-height:1.35}
"""


# ----------------------------------------------------------------------------- results up front
def stats(sid, D, c, pics, data, q=None, kicker="Intro", ttl="What did we get?"):
    q = R_(q, c, D)
    from video import script as L
    R = L.R
    p = pics["z4_chip"]
    fx0, fy0, fw = 1010, 190, 820
    fh = fw * 1080 / 1920
    g = lambda x, y: tuple(v * fw / 1920 for v in A.px(p["box"], (1920, 1080), x, y))
    rect = lambda cls, x1, y1, x2, y2, col: (lambda a, b: f'<rect class="dr {cls}" pathLength="1" x="{a[0]:.1f}" y="{a[1]:.1f}" width="{b[0] - a[0]:.1f}" '
                                             f'height="{b[1] - a[1]:.1f}" stroke="{col}" stroke-width="5" rx="5"/>')(g(x1, y2), g(x2, y1))
    svg = rect("sb-a", L.MACRO[0], L.MACRO[1], L.MACRO[2], L.MACRO[3], "#e3b341") + rect("sb-p", 6, L.MY, L.MX - 1, L.MY + R["macro_h"], "#bc8cff") \
        + rect("sb-p", 6, 11, L.FULL[2] - 6, L.MY - 1, "#bc8cff")
    ax, ay = g(L.MACRO[0], L.MACRO[3])
    m = head(kicker, ttl) + f"""
<div class="st-hero"><span class="sh1">64</span><span style="color:var(--mut)"> × </span><span class="sh2">32</span></div>
<div class="st-sub">bits · 2,048 cells · four byte-write enables</div>
<div class="st-row sr0" style="top:520px"><b>DRC</b>Magic 0 · KLayout 0</div>
<div class="st-row sr1" style="top:590px"><b>LVS</b>{R['lvs_devices']:,} devices match</div>
<div class="st-row sr2" style="top:660px"><b>SPICE</b>slow · typical · fast: pass</div>
<div class="chip st-warn" style="left:104px;top:760px;color:var(--orange);border-color:rgba(224,160,58,.5);font-size:30px">simulation and sign-off · not silicon</div>
<div style="position:absolute;left:{fx0}px;top:{fy0}px;width:{fw}px;height:{fh:.0f}px;overflow:hidden;border-radius:14px" data-layout-ignore>
<img id="{sid}-img" src="{p['file']}" style="position:absolute;left:0;top:0;width:{fw}px;height:{fh:.0f}px"></div>
<svg viewBox="0 0 {fw} {fh:.0f}" style="left:{fx0}px;top:{fy0}px;width:{fw}px;height:{fh:.0f}px" data-layout-ignore>{svg}</svg>
<div class="call sc-a" style="left:{fx0 + ax + 10:.0f}px;top:{fy0 + ay + 10:.0f}px;color:var(--yellow)">custom array, from Python</div>
<div class="call sc-p" style="left:{fx0 + 130}px;top:{fy0 + fh - 150:.0f}px;color:var(--purple)">standard cells</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".st-row, " + s + ".st-warn, " + s + ".call", {{ opacity: 0 }}, 0);
  tl.fromTo(P + "-img", {{ scale: 1.06 }}, {{ scale: 1, duration: D, ease: "none" }}, T);
  IN(s + ".st-hero", T + q.hero, {{ d: 0.6 }}); COUNT(s + ".sh1", T + q.hero, 0, 64, 0.8); COUNT(s + ".sh2", T + q.hero + 0.2, 0, 32, 0.8);
  IN(s + ".st-sub", T + q.hero + 0.7);
  DRAW(s + ".sb-a", T + q.array, 0.9); IN(s + ".sc-a", T + q.array + 0.5, {{ y: 8 }});
  DRAW(s + ".sb-p", T + q.peri, 0.9, null, 0.2); IN(s + ".sc-p", T + q.peri + 0.6, {{ y: 8 }});
  [0, 1, 2].forEach((i) => IN(s + ".sr" + i, T + q.rows[i], {{ y: 14 }}));
  IN(s + ".st-warn", T + q.warn);"""
    return m, js


# ----------------------------------------------------------------------------- sizing bars
def bars(sid, D, c, pics, data, q=None, kicker="The cell", ttl="Choosing the transistor sizes"):
    q = R_(q, c, D)
    S_ = data["sizing"]
    x0, y0, bw, gap, hmax, vmax = 150, 560, 62, 222, 400, 320.0
    svg, lab = "", ""
    for i, e in enumerate(S_):
        gx = x0 + i * gap
        nm = e["name"].split()
        for j, (k, col) in enumerate((("read", "#58a6ff"), ("write", "#e0a03a"))):
            h_ = e[k] / vmax * hmax
            svg += (f'<rect class="bar b{j}" x="{gx + j * (bw + 8)}" y="{y0 - h_:.1f}" width="{bw}" height="{h_:.1f}" rx="6" fill="{col}"/>'
                    f'<text class="bv" x="{gx + j * (bw + 8) + bw / 2}" y="{y0 - h_ - 12:.1f}" font-size="24" font-weight="700" text-anchor="middle" style="fill:{col}">{e[k]:.0f}</text>')
        svg += f'<text x="{gx + bw + 4}" y="{y0 + 38}" font-size="24" text-anchor="middle" style="fill:#8b96a5">pull-down {nm[2]}</text>'
        if len(nm) > 5:
            svg += f'<text x="{gx + bw + 4}" y="{y0 + 68}" font-size="22" text-anchor="middle" style="fill:#8b96a5">longer pass gate</text>'
        if e["name"].startswith("D"):
            svg = f'<rect class="chosen" x="{gx - 30}" y="{y0 - hmax - 30}" width="{2 * bw + 68}" height="{hmax + 84}" rx="14" fill="#3fb950" fill-opacity="0.12" stroke="#3fb950" stroke-width="3"/>' + svg
            lab = f'<text class="chosen-t" x="{gx + bw + 4}" y="{y0 - hmax - 44}" font-size="28" font-weight="900" text-anchor="middle" style="fill:#3fb950">chosen</text>'
    m = head(kicker, ttl) + f"""
<svg viewBox="0 0 1760 660" style="left:80px;top:170px;width:1760px;height:660px" data-layout-ignore>
<path d="M110,{y0}L1700,{y0}" stroke="#2a3442" stroke-width="3"/>{svg}{lab}
<text class="lg1" x="150" y="40" font-size="28" font-weight="700" style="fill:#58a6ff">■ read noise margin, worst corner (mV)</text>
<text class="lg2" x="760" y="40" font-size="28" font-weight="700" style="fill:#e0a03a">■ write margin, worst corner (mV)</text></svg>
<div class="chip bz1" style="left:96px;top:846px;color:var(--fg)">pull-down 0.65 µm · pass gate 0.42 µm</div>
<div class="chip bz2" style="left:690px;top:846px;color:var(--fg)">high-threshold pull-ups</div>
<div class="chip bz3" style="left:1060px;top:846px;color:var(--green)">leakage ÷ 10</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".chosen, " + s + ".chosen-t, " + s + ".bz1, " + s + ".bz2, " + s + ".bz3, " + s + ".bv, " + s + ".lg1, " + s + ".lg2", {{ opacity: 0 }}, 0);
  gsap.set(s + ".bar", {{ transformOrigin: "50% 100%" }});
  tl.set(s + ".b1", {{ scaleY: 0 }}, 0);
  SHOW(s + ".lg1", T + q.read, 0.3); SHOW(s + ".lg2", T + q.write, 0.3);
  tl.fromTo(s + ".b0", {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.7, ease: "power3.out", stagger: 0.12 }}, T + q.read);
  tl.fromTo(s + ".b1", {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.7, ease: "power3.out", stagger: 0.12, immediateRender: false }}, T + q.write);
  SHOW(s + ".bv", T + q.write + 1.2, 0.3, 0.03);
  SHOW(s + ".chosen", T + q.chosen, 0.4); IN(s + ".chosen-t", T + q.chosen + 0.2, {{ y: 8 }});
  IN(s + ".bz1", T + q.chosen + 0.6); IN(s + ".bz2", T + q.hvt); IN(s + ".bz3", T + q.hvt + 1.4);"""
    return m, js


# ----------------------------------------------------------------------------- Monte Carlo histogram
def hist(sid, D, c, pics, data, q=None, kicker="The cell", ttl="Monte Carlo: every cell has its own mismatch"):
    q = R_(q, c, D)
    mc = data["mc"]
    x0, y0, wpx, hmax = 140, 600, 1500, 430
    fx = lambda v: x0 + v / 420 * wpx
    svg = f'<path d="M{x0},{y0}L{x0 + wpx},{y0}" stroke="#2a3442" stroke-width="3"/>'
    for v in range(0, 421, 100):
        svg += f'<text x="{fx(v)}" y="{y0 + 40}" font-size="24" text-anchor="middle" style="fill:#8b96a5">{v}</text>'
    svg += f'<text x="{x0 + wpx / 2}" y="{y0 + 84}" font-size="26" text-anchor="middle" style="fill:#8b96a5">read noise margin  [mV]</text>'
    top = max(max(v["hist"]) for v in mc.values())
    for key, col, cls in (("tt_27_1.8", "#58a6ff", "h0"), ("sf_-40_1.62", "#e0a03a", "h1")):
        for i, n in enumerate(mc[key]["hist"]):
            if n:
                h_ = n / top * hmax
                svg += f'<rect class="hb {cls}" x="{fx(i * 5) + 1:.1f}" y="{y0 - h_:.1f}" width="{wpx / 84 - 2:.1f}" height="{h_:.1f}" fill="{col}" fill-opacity="0.9"/>'
    w = mc["sf_-40_1.62"]
    svg += (f'<path class="dr fail" pathLength="1" d="M{x0},{y0 - hmax - 30}L{x0},{y0}" stroke="#f85149" stroke-width="7"/>'
            f'<text class="failt" x="{x0 + 16}" y="{y0 - hmax - 6}" font-size="28" font-weight="900" style="fill:#f85149">failure</text>'
            f'<path class="dr span" pathLength="1" d="M{x0 + 8},{y0 - 150}L{fx(w["mean"]) - 30:.1f},{y0 - 150}" stroke="#e6edf3" stroke-width="4"/>'
            f'<text class="spant" x="{(x0 + fx(w["mean"])) / 2:.1f}" y="{y0 - 172}" font-size="56" font-weight="900" text-anchor="middle">{data["results"]["bitcell"]["read_mc_sigma"]:.0f} σ</text>')
    lab = lambda key: (lambda v, k: f"{k[0]}, {k[1]} °C, {k[2]} V:  {v['mean']:.0f} ± {v['sigma']:.1f} mV")(mc[key], key.split("_"))
    m = head(kicker, ttl) + f"""
<svg viewBox="0 0 1760 720" style="left:80px;top:170px;width:1760px;height:720px" data-layout-ignore>{svg}</svg>
<div class="chip hl0" style="left:1100px;top:186px;color:var(--blue)">{lab("tt_27_1.8")}</div>
<div class="chip hl1" style="left:1100px;top:250px;color:var(--orange)">worst corner · {lab("sf_-40_1.62")}</div>
<div class="note hn" style="left:420px;top:230px;width:540px">{w['n']:,} cells per condition, mismatch models of the PDK. Only silicon can confirm it.</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".failt, " + s + ".spant, " + s + ".hl0, " + s + ".hl1, " + s + ".hn", {{ opacity: 0 }}, 0);
  gsap.set(s + ".hb", {{ transformOrigin: "50% 100%" }});
  tl.fromTo(s + ".h0", {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.8, ease: "power3.out", stagger: 0.02 }}, T + q.tt); IN(s + ".hl0", T + q.tt + 0.4);
  tl.fromTo(s + ".h1", {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.8, ease: "power3.out", stagger: 0.02 }}, T + q.worst); IN(s + ".hl1", T + q.worst + 0.4);
  DRAW(s + ".fail", T + q.fail, 0.5); SHOW(s + ".failt", T + q.fail + 0.3, 0.3);
  DRAW(s + ".span", T + q.sigma, 0.9); IN(s + ".spant", T + q.sigma + 0.5, {{ d: 0.6 }});
  IN(s + ".hn", T + q.note);"""
    return m, js


# ----------------------------------------------------------------------------- source code
def code(sid, D, c, pics, data, path=None, start=None, n=10, lang="python", hl=(), notes=(), q=None, kicker="", ttl="", fs=26, wcode=1180):
    q = R_(q, c, D)
    lines = open(os.path.join(ROOT, path)).read().split("\n")
    i0 = next(i for i, l in enumerate(lines) if start in l)
    sel = lines[i0:i0 + n]
    ind = min(len(l) - len(l.lstrip()) for l in sel if l.strip())
    sel = [l[ind:] for l in sel]
    lexer = PythonLexer() if lang == "python" else get_lexer_by_name(lang)
    hh = highlight("\n".join(sel), lexer, HtmlFormatter(nowrap=True, noclasses=True, style="github-dark")).split("\n")
    body = "".join(f'<div class="ln ln{i}"><span style="color:#56606e">{i0 + 1 + i:4d}  </span>{hh[i] if i < len(hh) else ""}</div>' for i in range(len(sel)))
    lh = fs * 1.6
    bands = "".join(f'<div class="hlb hlb{k}" style="top:{66 + a * lh:.0f}px;height:{(b - a + 1) * lh:.0f}px"></div>' for k, (a, b) in enumerate(hl))
    nt = "".join(f'<div class="card cn cn{k}" style="left:{96 + wcode + 30}px;top:{190 + k * 176}px;width:{1920 - 96 - 96 - wcode - 30}px"><h3>{html.escape(h)}</h3><p>{html.escape(p)}</p></div>'
                 for k, (h, p) in enumerate(notes))
    m = head(kicker, ttl) + f"""
<div class="codep" style="left:96px;top:190px;width:{wcode}px;font-size:{fs}px" data-layout-ignore><div class="fn">{html.escape(path)}</div>{bands}{body}</div>{nt}"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".hlb, " + s + ".cn", {{ opacity: 0 }}, 0);
  tl.fromTo(s + ".ln", {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: 0.5, ease: "power1.out", stagger: q.step || 0.16 }}, T + (q.type == null ? 0.6 : q.type));
  (q.hl || []).forEach((t, k) => {{ SHOW(s + ".hlb" + k, T + t, 0.35); }});
  (q.notes || []).forEach((t, k) => IN(s + ".cn" + k, T + t, {{ y: 16 }}));"""
    return m, js


# ----------------------------------------------------------------------------- architecture
def arch(sid, D, c, pics, data, q=None, kicker="The periphery", ttl="What an array needs around it"):
    q = R_(q, c, D)
    B = lambda cls, x, y, w, h, t1, t2, col: (
        f'<g class="blk {cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{col}" fill-opacity="0.14" stroke="{col}" stroke-width="4"/>'
        f'<text x="{x + w / 2}" y="{y + h / 2 + (0 if not t2 else -8)}" font-size="34" font-weight="900" text-anchor="middle">{t1}</text>'
        + (f'<text x="{x + w / 2}" y="{y + h / 2 + 30}" font-size="22" text-anchor="middle" style="fill:#8b96a5">{t2}</text>' if t2 else "") + "</g>")
    Aw = lambda cls, d, col: f'<path class="dr {cls}" pathLength="1" d="{d}" stroke="{col}" stroke-width="5"/>'
    svg = (B("b-arr", 560, 60, 900, 380, "6T bit-cell array", "64 word lines × 32 bit-line pairs", "#e3b341")
           + B("b-dec", 300, 60, 200, 380, "decoder", "1 of 64 rows", "#39c5cf") + B("b-col", 560, 500, 900, 120, "column circuits", "drivers and sensing", "#bc8cff")
           + B("b-in", 60, 60, 190, 250, "inputs", "registers", "#58a6ff") + B("b-clk", 60, 500, 440, 120, "clock phases", "", "#3fb950")
           + Aw("a-dec", "M500,150L560,150M500,250L560,250M500,350L560,350", "#39c5cf") + Aw("a-col", "M760,440L760,500M1010,440L1010,500M1260,440L1260,500", "#bc8cff")
           + Aw("a-in", "M250,180L300,180", "#58a6ff") + Aw("a-clk", "M400,500L400,440M500,560L560,560M155,500L155,310", "#3fb950"))
    m = head(kicker, ttl) + f"""
<svg viewBox="0 0 1520 660" style="left:200px;top:180px;width:1520px;height:660px" data-layout-ignore>{svg}</svg>
<div class="chip ax1" style="left:1040px;top:864px;color:var(--mut)">analog sense amplifiers</div>
<div class="chip ax2" style="left:1420px;top:864px;color:var(--mut)">self-timed pulses</div>
<svg viewBox="0 0 800 60" style="left:1030px;top:864px;width:800px;height:60px" data-layout-ignore><path class="dr astr" pathLength="1" d="M0,30L690,30" stroke="#f85149" stroke-width="6"/></svg>
<div class="chip ay1" style="left:96px;top:864px;color:var(--green)">here: tri-state buffers, inverters and two clock phases</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".ax1, " + s + ".ax2, " + s + ".ay1", {{ opacity: 0 }}, 0);
  gsap.set(s + ".blk", {{ transformOrigin: "50% 50%" }});
  [["b-arr", q.arr], ["b-dec", q.dec], ["b-col", q.col], ["b-in", q.rest], ["b-clk", q.rest + 0.3]].forEach(([id, t]) => POP(s + "." + id, T + t, {{ from: 0.9 }}));
  DRAW(s + ".a-dec", T + q.dec + 0.4, 0.5); DRAW(s + ".a-col", T + q.col + 0.4, 0.5); DRAW(s + ".a-in", T + q.rest + 0.4, 0.4); DRAW(s + ".a-clk", T + q.rest + 0.7, 0.5);
  IN(s + ".ax1", T + q.usual); IN(s + ".ax2", T + q.usual + 1.4);
  DRAW(s + ".astr", T + q.boring, 0.6); tl.to(s + ".ax1, " + s + ".ax2", {{ opacity: 0.6, duration: 0.4 }}, T + q.boring + 0.3);
  IN(s + ".ay1", T + q.boring + 0.8);"""
    return m, js


# ----------------------------------------------------------------------------- one tri-state buffer, three jobs
def tristate(sid, D, c, pics, data, q=None, kicker="The periphery", ttl="One tri-state buffer per bit line"):
    q = R_(q, c, D)
    def line(cls, x, name):
        return (f'<rect x="{x - 22}" y="70" width="44" height="420" rx="10" fill="#141c28" stroke="#2a3442" stroke-width="3"/>'
                f'<rect class="lvl {cls}" x="{x - 18}" y="74" width="36" height="412" rx="7" fill="#bc8cff"/>'
                f'<text x="{x}" y="50" font-size="32" font-weight="900" text-anchor="middle" style="fill:#bc8cff">{name}</text>'
                f'<path d="M{x},490L{x},540" stroke="#8b96a5" stroke-width="5"/>'
                f'<path class="buf {cls}-buf" d="M{x - 46},620L{x + 46},620L{x},540Z" fill="#18212e" stroke="#e6edf3" stroke-width="5" stroke-linejoin="round"/>'
                f'<text class="bt {cls}-t" x="{x}" y="606" font-size="24" font-weight="900" text-anchor="middle">1</text>')
    svg = line("la", 200, "BL") + line("lb", 420, "BLB")
    svg += '<text x="310" y="690" font-size="24" text-anchor="middle" style="fill:#8b96a5">tri-state buffers (standard cells)</text>'
    cards = [("1 · precharge", "clock high: drive the line to 1"), ("2 · write", "selected line: drive 0"), ("3 · keeper", "the other line fell: hold this one at 1")]
    ch = "".join(f'<div class="card tc tc{k}" style="left:820px;top:{200 + k * 170}px;width:900px"><h3>{a}</h3><p>{b}</p></div>' for k, (a, b) in enumerate(cards))
    m = head(kicker, ttl) + f"""
<svg viewBox="0 0 640 720" style="left:120px;top:170px;width:640px;height:720px" data-layout-ignore>{svg}</svg>{ch}
<div class="big ts-static" style="left:820px;top:730px;font-size:60px;color:var(--green)">fully static</div>
<div class="note ts-n" style="left:824px;top:810px;width:900px">the clock can be stopped in either phase</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".tc, " + s + ".ts-static, " + s + ".ts-n", {{ opacity: 0 }}, 0);
  gsap.set(s + ".lvl", {{ transformOrigin: "50% 100%" }});
  const lvl = (cls, v, t, col) => {{ tl.to(s + "." + cls, {{ scaleY: v, duration: 0.6, ease: "power2.inOut" }}, t); if (col) tl.to(s + "." + cls, {{ fill: col, duration: 0.3 }}, t); }};
  const act = (cls, on, t) => tl.to(s + "." + cls + "-buf", {{ fill: on ? "#1f6f3a" : "#18212e", duration: 0.25 }}, t);
  tl.set(s + ".lvl", {{ scaleY: 0.08 }}, 0);
  // 1 precharge
  IN(s + ".tc0", T + q.pre, {{ y: 14 }}); act("la", 1, T + q.pre); act("lb", 1, T + q.pre); lvl("la", 1, T + q.pre + 0.2); lvl("lb", 1, T + q.pre + 0.2);
  // 2 write: BL driven low
  IN(s + ".tc1", T + q.write, {{ y: 14 }}); act("lb", 0, T + q.write); lvl("la", 0.05, T + q.write + 0.2, "#f85149");
  tl.to(s + ".la-t", {{ opacity: 0, duration: 0.15 }}, T + q.write);
  // back to precharged, then 3: BLB falls (a cell reads), BL is held
  lvl("la", 1, T + q.keep - 1.0, "#bc8cff"); act("la", 0, T + q.keep - 1.0);
  IN(s + ".tc2", T + q.keep, {{ y: 14 }}); lvl("lb", 0.05, T + q.keep + 0.2, "#e0a03a"); act("la", 1, T + q.keep + 0.7);
  tl.to(s + ".la-t", {{ opacity: 1, duration: 0.15 }}, T + q.keep + 0.7);
  IN(s + ".ts-static", T + q.static, {{ d: 0.6 }}); IN(s + ".ts-n", T + q.stop);"""
    return m, js


# ----------------------------------------------------------------------------- the race at the rising clock edge
def race(sid, D, c, pics, data, q=None, kicker="The periphery", ttl="The one dangerous moment", t_off=0.52, t_open=1.31, t_ff=0.3):
    q = R_(q, c, D)
    x0, ns = 500, 520                     # x of the clock edge, pixels per nanosecond
    X = lambda t: x0 + t * ns
    svg = (f'<path d="M120,560L1680,560" stroke="#2a3442" stroke-width="3"/>'
           + '<text x="1680" y="600" font-size="24" text-anchor="end" style="fill:#8b96a5">time →</text>'
           + f'<path class="dr edge" pathLength="1" d="M{X(0)},40L{X(0)},540" stroke="#e6edf3" stroke-width="5"/>'
           f'<text class="edget" x="{X(0)}" y="26" font-size="28" font-weight="900" text-anchor="middle">rising clock edge</text>'
           f'<rect class="bar-wl" x="120" y="110" width="{X(t_off) - 120:.0f}" height="70" rx="10" fill="#39c5cf" fill-opacity="0.35" stroke="#39c5cf" stroke-width="3"/>'
           f'<text class="bar-wlt" x="140" y="155" font-size="28" font-weight="700" style="fill:#39c5cf">old word line and write driver still on</text>'
           f'<rect class="bar-ff" x="{X(t_ff):.0f}" y="250" width="{1680 - X(t_ff):.0f}" height="70" rx="10" fill="#58a6ff" fill-opacity="0.35" stroke="#58a6ff" stroke-width="3"/>'
           f'<text class="bar-fft" x="{X(t_ff) + 20:.0f}" y="295" font-size="28" font-weight="700" style="fill:#58a6ff">new address and data leave the flip-flops</text>'
           f'<rect class="danger" x="{X(t_ff):.0f}" y="96" width="{X(t_off) - X(t_ff):.0f}" height="240" rx="6" fill="#f85149" fill-opacity="0.3" stroke="#f85149" stroke-width="4"/>'
           f'<text class="dangert" x="{(X(t_ff) + X(t_off)) / 2:.0f}" y="376" font-size="28" font-weight="900" text-anchor="middle" style="fill:#f85149">overlap: wrong word written</text>'
           f'<rect class="bar-lat" x="{X(t_open):.0f}" y="410" width="{1680 - X(t_open):.0f}" height="70" rx="10" fill="#3fb950" fill-opacity="0.35" stroke="#3fb950" stroke-width="3"/>'
           f'<text class="bar-latt" x="{X(t_open) + 20:.0f}" y="455" font-size="28" font-weight="700" style="fill:#3fb950">hold latches open</text>'
           f'<path class="dr marg" pathLength="1" d="M{X(t_off):.0f},445L{X(t_open):.0f},445" stroke="#e6edf3" stroke-width="4"/>'
           f'<text class="margt" x="{(X(t_off) + X(t_open)) / 2:.0f}" y="430" font-size="26" font-weight="900" text-anchor="middle">margin</text>'
           f'<text class="margt" x="{X(t_open) + 20:.0f}" y="520" font-size="26" font-weight="700" style="fill:#8b96a5">0.5 to 1.6 ns over corners (SPICE)</text>')
    m = head(kicker, ttl) + f"""
<svg viewBox="0 0 1760 640" style="left:80px;top:200px;width:1760px;height:640px" data-layout-ignore>{svg}</svg>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".edget, " + s + ".bar-wl, " + s + ".bar-wlt, " + s + ".bar-ff, " + s + ".bar-fft, " + s + ".danger, " + s + ".dangert, " + s + ".bar-lat, " + s + ".bar-latt, " + s + ".margt", {{ opacity: 0 }}, 0);
  DRAW(s + ".edge", T + q.edge, 0.5); SHOW(s + ".edget", T + q.edge + 0.3, 0.3);
  tl.fromTo(s + ".bar-ff", {{ opacity: 0, scaleX: 0, transformOrigin: "0% 50%" }}, {{ opacity: 1, scaleX: 1, duration: 0.7, ease: "power2.out" }}, T + q.ff); SHOW(s + ".bar-fft", T + q.ff + 0.5, 0.3);
  SHOW(s + ".bar-wl, " + s + ".bar-wlt", T + q.wl, 0.4);
  SHOW(s + ".danger", T + q.danger, 0.3); IN(s + ".dangert", T + q.danger + 0.2, {{ y: 8 }});
  tl.to(s + ".danger", {{ opacity: 0.35, duration: 0.25, yoyo: true, repeat: 3 }}, T + q.danger + 0.4);
  // the fix: the new values are held back
  tl.to(s + ".bar-ff, " + s + ".bar-fft", {{ opacity: 0.25, duration: 0.4 }}, T + q.fix); tl.to(s + ".danger, " + s + ".dangert", {{ opacity: 0, duration: 0.4 }}, T + q.fix);
  tl.fromTo(s + ".bar-lat", {{ opacity: 0, scaleX: 0, transformOrigin: "0% 50%" }}, {{ opacity: 1, scaleX: 1, duration: 0.7, ease: "power2.out" }}, T + q.fix + 0.5); SHOW(s + ".bar-latt", T + q.fix + 1.0, 0.3);
  DRAW(s + ".marg", T + q.fix + 1.5, 0.6); IN(s + ".margt", T + q.fix + 1.9, {{ y: 6 }});"""
    return m, js


# ----------------------------------------------------------------------------- corner table
def table(sid, D, c, pics, data, q=None, kicker="Does it work?", ttl="Post-layout SPICE at the sign-off corners"):
    q = R_(q, c, D)
    T_ = data["results"]["timing"]
    cols = [("tt", "typical", "tt · 25 °C · 1.80 V", 620), ("ss", "slow", "ss · 100 °C · 1.60 V", 1030), ("ff", "fast", "ff · −40 °C · 1.95 V", 1440)]
    rows = [("Function", lambda k: "pass", "var(--green)", None), ("Clock ↓ to data out", lambda k: f"{T_[k]['t_cq_max']:.1f}", "var(--yellow)", " ns"),
            ("Shortest passing period", lambda k: f"{T_[k]['t_min_period_sim']:g}", "var(--yellow)", " ns"),
            ("Specified period", lambda k: f"{T_[k]['min_period_spec']:g}", "var(--fg)", " ns"),
            ("Supply current at 50 MHz", lambda k: f"{T_[k]['i_avg_mA']:.2f}", "var(--fg)", " mA")]
    h = "".join(f'<div class="tb-h th{j}" style="left:{x}px">{name}</div><div class="tb-s th{j}" style="left:{x}px">{sub}</div>' for j, (k, name, sub, x) in enumerate(cols))
    body = ""
    for i, (lab, fn, col, unit) in enumerate(rows):
        y = 340 + i * 96
        body += f'<div class="tb-l tr{i}" style="top:{y + 8}px">{lab}</div>'
        for j, (k, _, _, x) in enumerate(cols):
            body += f'<div class="tb-v tr{i}" style="left:{x}px;top:{y}px;color:{col}">{fn(k)}<span style="font-size:28px;font-weight:700">{unit or ""}</span></div>'
    m = head(kicker, ttl) + h + body + '<div class="note tb-n" style="left:96px;top:840px;width:1700px">Writes, reads, a byte-masked write and a disabled cycle; all 32 outputs checked before every rising clock edge.</div>'
    js = f"""
  const q = {J(q)}, s = P + " ";
  IN(s + ".tb-h, " + s + ".tb-s", T + q.head, {{ s: 0.08, y: 10 }});
  q.rows.forEach((t, i) => IN(s + ".tr" + i, T + t, {{ s: 0.07, y: 12 }}));
  IN(s + ".tb-n", T + q.note);"""
    return m, js


# ----------------------------------------------------------------------------- closing lines
def lines(sid, D, c, pics, data, q=None, items=(), url="", kicker="Lessons", ttl="What this project taught me"):
    q = R_(q, c, D)
    body = ""
    for i, (h_, p) in enumerate(items):
        body += (f'<div class="ls-g lg{i}" style="position:absolute;left:0;top:{230 + i * 200}px;width:1920px;height:190px">'
                 f'<div class="ls-n" style="top:-34px">{i + 1}</div><div class="ls-h" style="top:0">{html.escape(h_)}</div>'
                 f'<div class="ls-p" style="top:96px">{html.escape(p)}</div></div>')
    m = head(kicker, ttl) + body + f'<div class="big ls-url mono" style="left:96px;top:850px;font-size:44px;font-weight:700;color:var(--blue);letter-spacing:0">{html.escape(url)}</div>'
    js = f"""
  const q = {J(q)}, s = P + " ";
  q.items.forEach((t, i) => {{ IN(s + ".lg" + i, T + t, {{ y: 30, d: 0.7 }}); if (i > 0) tl.to(s + ".lg" + (i - 1), {{ opacity: 0.4, duration: 0.4 }}, T + t); }});
  tl.to(s + ".ls-g", {{ opacity: 1, duration: 0.4 }}, T + q.url - 0.2); IN(s + ".ls-url", T + q.url, {{ d: 0.6 }});"""
    return m, js


# ----------------------------------------------------------------------------- code that draws the cell
def codepic(sid, D, c, pics, data, path=None, start=None, n=5, q=None, kicker="", ttl="", fs=24, hl=4, pic="cell_l1", cards=()):
    """A few lines of source on top; below, the picture they draw, revealed once per call of the function."""
    import re
    q = R_(q, c, D)
    src = open(os.path.join(ROOT, path)).read().split("\n")
    i0 = next(i for i, l in enumerate(src) if start in l)
    sel = src[i0:i0 + n]
    ind = min(len(l) - len(l.lstrip()) for l in sel if l.strip())
    sel = [re.sub(r"\s{3,}#", "   #", l[ind:]) for l in sel]
    hh = highlight("\n".join(sel), PythonLexer(), HtmlFormatter(nowrap=True, noclasses=True, style="github-dark")).split("\n")
    body = "".join(f'<div class="ln ln{i}"><span style="color:#56606e">{i0 + 1 + i:4d}  </span>{hh[i] if i < len(hh) else ""}</div>' for i in range(len(sel)))
    lh = fs * 1.6
    pw, ph = 1040, 390
    p = pics[pic]
    img = lambda cls: f'<img class="{cls}" src="{p["file"]}" style="position:absolute;left:0;top:0;width:{pw}px;height:{ph}px">'
    cd = "".join(f'<div class="card cc cc{k}" style="left:1166px;top:{486 + k * 200}px;width:658px"><h3>{html.escape(h)}</h3><p>{html.escape(t)}</p></div>' for k, (h, t) in enumerate(cards))
    m = head(kicker, ttl) + f"""
<div class="codep" style="left:96px;top:180px;width:1728px;font-size:{fs}px" data-layout-ignore><div class="fn">{html.escape(path)}</div>
<div class="hlb" style="top:{66 + hl * lh:.0f}px;height:{lh:.0f}px"></div>{body}</div>
<div class="lay cp-pic" style="left:96px;top:486px;width:{pw}px;height:{ph}px" data-layout-ignore>{img("cp-a")}{img("cp-b")}
<svg viewBox="0 0 {pw} {ph}" style="left:0;top:0;width:{pw}px;height:{ph}px"><path class="dr cp-mid" pathLength="1" d="M{pw / 2},0L{pw / 2},{ph}" stroke="#e6edf3" stroke-width="2"/>
<circle class="cp-dot" cx="{pw / 2}" cy="{ph / 2}" r="9" fill="#e6edf3" stroke="#0b0f17" stroke-width="3"/></svg>
<div class="call cp-l1" style="left:16px;top:14px;color:var(--yellow)">call 1: shape(x, y)</div>
<div class="call cp-l2" style="right:16px;bottom:14px;color:var(--cyan)">call 2: shape(W − x, H − y)</div></div>{cd}"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  tl.set(s + ".hlb, " + s + ".cc, " + s + ".cp-l1, " + s + ".cp-l2, " + s + ".cp-dot", {{ opacity: 0 }}, 0);
  tl.fromTo(s + ".ln", {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: 0.5, ease: "power1.out", stagger: 0.22 }}, T + 0.6);
  tl.fromTo(s + ".cp-a", {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 50% 0% 0%)", duration: 1.2, ease: "power2.inOut" }}, T + q.call1);
  IN(s + ".cp-l1", T + q.call1 + 0.6, {{ y: 8 }});
  SHOW(s + ".hlb", T + q.hl, 0.35);
  POP(s + ".cp-dot", T + q.call2 - 0.5); DRAW(s + ".cp-mid", T + q.call2 - 0.5, 0.5);
  tl.fromTo(s + ".cp-b", {{ clipPath: "inset(0% 0% 0% 100%)" }}, {{ clipPath: "inset(0% 0% 0% 50%)", duration: 1.2, ease: "power2.inOut" }}, T + q.call2);
  IN(s + ".cp-l2", T + q.call2 + 0.6, {{ y: 8 }});
  q.cards.forEach((t, k) => IN(s + ".cc" + k, T + t, {{ y: 16 }}));"""
    return m, js
