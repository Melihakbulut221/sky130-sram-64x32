"""Scene templates for the HyperFrames compositions.

Every scene function returns (markup, script). The script runs inside
    (function (T, D, c, P) { ... })(start, duration, [sentence cues], '#sN')
with the shared GSAP timeline `tl` and the helpers below. Times in a scene are relative to
its own start, so `T + x` places a tween.
"""
import html
import json

from . import assets as A

CSS = """
:root{--bg:#0b0f17;--panel:#121923;--panel2:#18212e;--line:#2a3442;--fg:#e6edf3;--mut:#8b96a5;--blue:#58a6ff;--green:#3fb950;
--orange:#e0a03a;--red:#f85149;--purple:#bc8cff;--cyan:#39c5cf;--yellow:#e3b341}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;background:var(--bg)}
#root{position:relative;width:1920px;height:1080px;font-family:Inter,sans-serif;color:var(--fg);overflow:hidden}
#bg{position:absolute;inset:0;background:radial-gradient(1300px 760px at 28% 18%,#17233a 0%,#0b0f17 62%)}
.scene,.stage{position:absolute;inset:0}
.kick{position:absolute;left:96px;top:52px;font-size:22px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--blue)}
.ttl{position:absolute;left:96px;top:84px;font-size:50px;font-weight:700;letter-spacing:-.02em;white-space:nowrap}
.ttl span{display:inline-block;white-space:pre}
#capband{position:absolute;left:0;right:0;bottom:0;height:170px;background:linear-gradient(to top,rgba(5,8,13,.94) 35%,rgba(5,8,13,0))}
.cap p{position:absolute;left:170px;right:170px;bottom:30px;min-height:90px;display:flex;flex-wrap:wrap;align-items:center;align-content:center;
justify-content:center;font-size:31px;line-height:1.36;color:#f0f4f8;font-weight:400}
.cap .cw{white-space:pre}
#progress i{position:absolute;left:0;top:0;width:1920px;height:5px;background:var(--blue);transform-origin:0 50%}
svg{position:absolute;overflow:visible}
svg text{font-family:Inter,sans-serif;fill:var(--fg)}
.dr{fill:none;stroke-dasharray:1;stroke-dashoffset:1;stroke-linecap:round;stroke-linejoin:round}
.fl{fill:none;stroke-dasharray:.025 .045;stroke-linecap:round}
.tag{display:inline-block;padding:14px 26px;border:2px solid var(--line);border-radius:999px;font-size:30px;background:rgba(18,25,35,.86);white-space:nowrap}
.chip{position:absolute;padding:10px 20px;border-radius:12px;font-size:26px;font-weight:700;background:var(--panel2);border:2px solid var(--line);white-space:nowrap}
.mono{font-family:'JetBrains Mono',monospace}
.panel{position:absolute;background:var(--panel);border:2px solid var(--line);border-radius:18px;overflow:hidden}
.big{position:absolute;font-weight:900;letter-spacing:-.03em;white-space:nowrap}
.note{position:absolute;font-size:28px;color:var(--mut);line-height:1.35}
/* title */
.t-bgwrap{position:absolute;inset:0;overflow:hidden;opacity:.55}
.t-bg{position:absolute;left:0;top:0;width:1920px;height:1080px}
.t-shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(11,15,23,.97) 0%,rgba(11,15,23,.8) 46%,rgba(11,15,23,.25) 100%)}
.t-h1{position:absolute;left:110px;top:290px;font-size:132px;font-weight:900;letter-spacing:-.035em;white-space:nowrap}
.t-h1 span{display:inline-block;white-space:pre}
.t-sub{position:absolute;left:116px;top:466px;font-size:44px;color:var(--blue);font-weight:700;white-space:nowrap}
.t-tags{position:absolute;left:116px;top:566px;display:flex;gap:18px}
/* cell */
.mode{position:absolute;left:1390px;top:210px;font-size:92px;font-weight:900;letter-spacing:-.03em}
.modesub{position:absolute;left:1394px;top:330px;width:450px;font-size:32px;line-height:1.35;color:#aab4c0}
.rule{position:absolute;left:1390px;font-size:32px;font-weight:700;padding:14px 22px;border-radius:14px;border:2px solid var(--line);background:var(--panel2);white-space:nowrap}
/* layout pictures */
.lay{position:absolute;overflow:hidden;border-radius:14px;border:2px solid var(--line);background:#0d1117}
.lay img{position:absolute;left:0;top:0}
.call{position:absolute;font-size:26px;font-weight:700;padding:6px 14px;border-radius:10px;background:rgba(8,11,16,.92);border:2px solid currentColor;white-space:nowrap}
/* terminal */
.term{position:absolute;background:#0a0d12;border:2px solid var(--line);border-radius:16px;font-family:'JetBrains Mono',monospace;font-size:31px;line-height:1.55;padding:74px 38px 30px;overflow:hidden}
.term:before{content:"";position:absolute;left:0;top:0;right:0;height:46px;background:var(--panel2)}
.term .row{white-space:pre;color:var(--fg)}
.term .cmd{color:var(--blue)} .term .ok{color:var(--green);font-weight:700} .term .dim{color:var(--mut)}
"""

HELPERS = r"""
const tl = gsap.timeline({ paused: true });
const Q = (s) => document.querySelector(s);
function IN(sel, t, o) { o = o || {}; tl.fromTo(sel, { opacity: 0, y: o.y == null ? 18 : o.y, filter: "blur(8px)" },
  { opacity: 1, y: 0, filter: "blur(0px)", duration: o.d || 0.5, ease: o.ease || "expo.out", stagger: o.s || 0 }, t); }
function POP(sel, t, o) { o = o || {}; tl.fromTo(sel, { opacity: 0, scale: o.from || 0.8 },
  { opacity: 1, scale: 1, duration: o.d || 0.5, ease: "back.out(1.5)", stagger: o.s || 0 }, t); }
function FADE(sel, t, to, d) { tl.to(sel, { opacity: to, duration: d || 0.3, ease: "power2.inOut" }, t); }
function SHOW(sel, t, d, s) { tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: d || 0.3, ease: "power2.out", stagger: s || 0 }, t); }
function OUT(sel, t, d) { tl.to(sel, { opacity: 0, filter: "blur(6px)", duration: d || 0.22, ease: "power2.in" }, t); }
function DRAW(sel, t, d, ease, s) { tl.fromTo(sel, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: d || 0.8, ease: ease || "power2.inOut", stagger: s || 0 }, t); }
function FLOW(sel, t, d, laps) { tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: 0.25 }, t);
  tl.fromTo(sel, { strokeDashoffset: 0 }, { strokeDashoffset: -(laps || 2), duration: d, ease: "none" }, t);
  tl.to(sel, { opacity: 0, duration: 0.25 }, t + d - 0.25); }
function COUNT(sel, t, a, b, d, dec) { tl.fromTo(sel, { textContent: a }, { textContent: b, duration: d || 0.9, ease: "power2.out", snap: { textContent: dec ? 0.1 : 1 }, immediateRender: false }, t); }
function WIPE(sel, t, d) { tl.fromTo(sel, { clipPath: "inset(0% 100% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: d || 0.9, ease: "power2.inOut" }, t); }
function STAGE(P, T, D, last) {
  tl.fromTo(P + "-st", { opacity: 0, scale: 1.02, filter: "blur(10px)" }, { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.45, ease: "power3.out" }, T);
  if (!last) tl.to(P + "-st", { opacity: 0, filter: "blur(8px)", duration: 0.2, ease: "power2.in" }, T + D - 0.22);
  if (Q(P + " .kick")) { SHOW(P + " .kick", T + 0.1, 0.3); IN(P + " .ttl span", T + 0.18, { s: 0.045, d: 0.4, y: 0 }); }
}
function CAP(sel, t, d) {
  tl.fromTo(sel + " .cw", { opacity: 0, filter: "blur(4px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.16, ease: "power2.out", stagger: 0.016 }, t);
  tl.to(sel, { opacity: 0, duration: 0.1 }, t + d - 0.11);
}
function PATHD(xs, ys, fx, fy) { let s = ""; for (let i = 0; i < xs.length; i++) s += (i ? "L" : "M") + fx(xs[i]).toFixed(1) + "," + fy(ys[i]).toFixed(1); return s; }
function SVGEL(parent, tag, attrs) { const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]); Q(parent).appendChild(e); return e; }
"""


def head(kicker, title):
    words = "".join(f"<span>{html.escape(w)} </span>" for w in title.split())
    return f'<div class="kick">{html.escape(kicker)}</div><div class="ttl">{words}</div>'


def J(x):
    return json.dumps(x, separators=(",", ":"))


def R_(x, c, D):
    """Scene arguments may be given as functions of the sentence cues and the scene duration."""
    return x(c, D) if callable(x) else x


# ----------------------------------------------------------------------------- title
def title(sid, D, c, pics, data, tags_at=None):
    m = f"""
<div class="t-bgwrap" data-layout-ignore><img class="t-bg" id="{sid}-bg" src="{pics['z4_chip']['file']}"></div>
<div class="t-shade" data-layout-ignore></div>
<h1 class="t-h1"><span>A </span><span>6T </span><span>SRAM </span><span>in </span><span>130&nbsp;nm</span></h1>
<p class="t-sub">64 words × 32 bits on SkyWater SKY130, built with open tools</p>
<div class="t-tags"><span class="tag">custom cell array, generated from Python</span><span class="tag">standard-cell periphery</span>
<span class="tag">DRC · LVS · SPICE sign-off</span></div>"""
    js = f"""
  tl.fromTo(P + "-bg", {{ scale: 1.14 }}, {{ scale: 1.0, duration: D, ease: "none" }}, T);
  IN(P + " .t-h1 span", T + 0.35, {{ s: 0.08, d: 0.55, y: 0 }});
  IN(P + " .t-sub", T + 1.2, {{ d: 0.6 }});
  POP(P + " .tag", T + {tags_at if tags_at is not None else 'Math.min(c.length > 1 ? c[1] : 3.0, D - 2.2)'}, {{ s: 0.28 }});"""
    return m, js


# ----------------------------------------------------------------------------- the 6T cell
def _mos(x, y, typ, g):
    """Path strings of a vertical MOSFET symbol at (x, y); g = +1 puts the gate on the right."""
    gx = x + g * 26
    px = x + g * 40
    d = [f"M{x},{y - 70}L{x},{y - 30}L{gx},{y - 30}", f"M{x},{y + 70}L{x},{y + 30}L{gx},{y + 30}",
         f"M{gx},{y - 42}L{gx},{y + 42}", f"M{px},{y - 32}L{px},{y + 32}"]
    start = px + g * 16 if typ == "p" else px
    d.append(f"M{start},{y}L{x + g * 90},{y}")
    bub = f'<circle class="dr" pathLength="1" cx="{px + g * 8}" cy="{y}" r="8"/>' if typ == "p" else ""
    return d, bub


def cell(sid, D, c, pics, data, q=None, kicker="The cell", ttl="Six transistors, one bit"):
    q = R_(q, c, D)
    xl, xr, yp, yn, ym = 520, 880, 220, 480, 350
    out = [head(kicker, ttl), '<svg id="%s-svg" viewBox="0 0 1400 700" style="left:40px;top:170px;width:1340px;height:670px" data-layout-ignore>' % sid]
    P = lambda cls, d, col, w=5, extra="": f'<path class="dr {cls}" pathLength="1" d="{d}" stroke="{col}" stroke-width="{w}" {extra}/>'
    fg, mut = "#e6edf3", "#8b96a5"
    out.append(P("rail", "M430,90L970,90", "#f85149", 5) + P("rail", "M430,610L970,610", "#58a6ff", 5))
    for side, x, g in (("invL", xl, 1), ("invR", xr, -1)):
        for typ, y in (("p", yp), ("n", yn)):
            d, bub = _mos(x, y, typ, g)
            out += [P(side, k, fg) for k in d] + [bub.replace('class="dr"', f'class="dr {side}" stroke="{fg}" stroke-width="5"')]
        out.append(P(side, f"M{x},{yp - 70}L{x},90", fg) + P(side, f"M{x},{yp + 70}L{x},{yn - 70}", fg) + P(side, f"M{x},{yn + 70}L{x},610", fg))
        out.append(P(side, f"M{x + g * 90},{yp}L{x + g * 90},{yn}", fg))
    out.append(P("xqb", f"M{xr},330L{xl + 90},330", "#3fb950", 6) + P("xq", f"M{xl},370L{xr - 90},370", "#e3b341", 6))
    # pass gates, bit lines, word line
    out.append(P("pg", f"M200,{ym}L300,{ym}", fg) + P("pg", f"M380,{ym}L{xl},{ym}", fg) + P("pg pgch", f"M300,{ym}L380,{ym}", fg, 7)
               + P("pg", f"M300,{ym - 22}L380,{ym - 22}", fg) + P("pg pglead", f"M340,{ym - 22}L340,150", fg))
    out.append(P("pg", f"M1200,{ym}L1100,{ym}", fg) + P("pg", f"M1020,{ym}L{xr},{ym}", fg) + P("pg pgch", f"M1100,{ym}L1020,{ym}", fg, 7)
               + P("pg", f"M1100,{ym - 22}L1020,{ym - 22}", fg) + P("pg pglead", f"M1060,{ym - 22}L1060,150", fg))
    out.append(P("bl blL", "M200,40L200,670", "#bc8cff", 7) + P("bl blR", "M1200,40L1200,670", "#bc8cff", 7) + P("wl", "M120,150L1280,150", "#39c5cf", 7))
    # animated currents
    out.append(f'<path class="fl flow-read" pathLength="1" d="M200,60L200,{ym}L{xl},{ym}L{xl},610" stroke="#e0a03a" stroke-width="12" opacity="0"/>')
    out.append(f'<path class="fl flow-write" pathLength="1" d="M{xr},90L{xr},{ym}L1200,{ym}L1200,660" stroke="#f85149" stroke-width="12" opacity="0"/>')
    # storage nodes: the stored value is written inside the node
    for nid, x, col in (("q", xl, "#e3b341"), ("qb", xr, "#3fb950")):
        out.append(f'<g class="node n{nid}"><circle cx="{x}" cy="{ym}" r="27" fill="{col}" stroke="#0b0f17" stroke-width="4"/>'
                   f'<text class="val v{nid}1" x="{x}" y="{ym + 13}" font-size="36" font-weight="900" text-anchor="middle" opacity="0" style="fill:#0b0f17">1</text>'
                   f'<text class="val v{nid}0" x="{x}" y="{ym + 13}" font-size="36" font-weight="900" text-anchor="middle" opacity="0" style="fill:#0b0f17">0</text></g>')
    T_ = lambda cls, x, y, s, col=fg, size=30, w=700, anchor="middle": f'<text class="{cls}" x="{x}" y="{y}" font-size="{size}" font-weight="{w}" style="fill:{col}" text-anchor="{anchor}">{s}</text>'
    out.append(T_("nl", xl - 44, ym - 34, "Q", "#e3b341", 44) + T_("nl", xr + 58, ym - 34, "QB", "#3fb950", 44))
    out.append(T_("dl", xl - 46, yp + 10, "PU", mut, 28) + T_("dl", xl - 46, yn + 10, "PD", mut, 28)
               + T_("dl", xr + 46, yp + 10, "PU", mut, 28) + T_("dl", xr + 46, yn + 10, "PD", mut, 28))
    out.append(T_("pl", 322, ym - 44, "PG", mut, 28, anchor="end") + T_("pl", 1078, ym - 44, "PG", mut, 28, anchor="start"))
    out.append(T_("bll", 200, 28, "BL", "#bc8cff", 36) + T_("bll", 1200, 28, "BLB", "#bc8cff", 36) + T_("wll", 1300, 162, "WL", "#39c5cf", 36, anchor="start"))
    out.append(T_("rl", 990, 100, "VDD", "#f85149", 30, anchor="start") + T_("rl", 990, 620, "GND", "#58a6ff", 30, anchor="start"))
    # read: bit-line level badges, bump meter
    out.append('<g class="badge b-vdd" opacity="0"><rect x="120" y="60" width="62" height="34" rx="8" fill="#1d1430" stroke="#bc8cff" stroke-width="2"/>'
               '<text x="151" y="85" font-size="22" font-weight="700" text-anchor="middle" fill="#bc8cff">VDD</text>'
               '<rect x="1218" y="60" width="62" height="34" rx="8" fill="#1d1430" stroke="#bc8cff" stroke-width="2"/>'
               '<text x="1249" y="85" font-size="22" font-weight="700" text-anchor="middle" fill="#bc8cff">VDD</text></g>')
    out.append('<g class="badge b-wl" opacity="0"><rect x="1290" y="176" width="84" height="38" rx="8" fill="#0d2a2e" stroke="#39c5cf" stroke-width="2"/>'
               '<text x="1332" y="203" font-size="24" font-weight="700" text-anchor="middle" fill="#39c5cf">ON</text></g>')
    out.append(f'<g class="badge b-bump" opacity="0"><rect x="{xl - 300}" y="{ym + 34}" width="250" height="50" rx="10" fill="#2e2110" stroke="#e0a03a" stroke-width="2"/>'
               f'<text class="bumptxt" x="{xl - 175}" y="{ym + 68}" font-size="28" font-weight="700" text-anchor="middle" style="fill:#e0a03a">0 lifted to 0.18 V</text></g>')
    out.append('<g class="badge b-zero" opacity="0"><rect x="1218" y="630" width="150" height="38" rx="8" fill="#2e1114" stroke="#f85149" stroke-width="2"/>'
               '<text x="1293" y="657" font-size="24" font-weight="700" text-anchor="middle" fill="#f85149">forced to 0</text></g>')
    out.append("</svg>")
    out.append('<div class="mode m-hold">Hold</div><div class="mode m-read" style="color:var(--orange)">Read</div>'
               '<div class="mode m-write" style="color:var(--red)">Write</div>')
    out.append('<div class="modesub ms-hold">Two inverters in a loop keep the bit.</div>'
               '<div class="modesub ms-read">The side that stores 0 discharges its bit line, and the pass gate lifts that 0.</div>'
               '<div class="modesub ms-write">One bit line is forced low; the pass gate fights the pull-up.</div>')
    out.append('<div class="rule r1" style="top:520px;color:var(--orange)">pull-down &gt; pass gate</div>'
               '<div class="rule r2" style="top:600px;color:var(--red)">pass gate &gt; pull-up</div>'
               '<div class="rule r3" style="top:700px;color:var(--fg);font-size:38px">PD &gt; PG &gt; PU</div>')
    js = f"""
  const q = {J(q)}, s = P + " ";
  const at = (k, d) => (q[k] == null ? d : q[k]);
  DRAW(s + ".rail", T + 0.3, 0.5); DRAW(s + ".invL", T + 0.45, 0.7, null, 0.02); DRAW(s + ".invR", T + 0.7, 0.7, null, 0.02);
  SHOW(s + ".rl", T + 0.7, 0.3); SHOW(s + ".dl", T + 1.2, 0.3, 0.05);
  DRAW(s + ".xq", T + at("cross", 1.4), 0.6); DRAW(s + ".xqb", T + at("cross", 1.4) + 0.25, 0.6);
  SHOW(s + ".node", T + at("cross", 1.4) + 0.6, 0.3, 0.1); SHOW(s + ".nl", T + at("cross", 1.4) + 0.7, 0.3);
  gsap.set(s + ".nq", {{ svgOrigin: "{xl} {ym}" }}); gsap.set(s + ".nqb", {{ svgOrigin: "{xr} {ym}" }});
  tl.set(s + ".m-read, " + s + ".m-write, " + s + ".ms-read, " + s + ".ms-write, " + s + ".rule", {{ opacity: 0 }}, 0);
  IN(s + ".m-hold", T + 0.9); IN(s + ".ms-hold", T + 1.1);
  // the two stable states
  const st = T + at("states", 2.4);
  SHOW(s + ".vq1, " + s + ".vqb0", st, 0.3);
  tl.to(s + ".vq1, " + s + ".vqb0", {{ opacity: 0, duration: 0.2 }}, st + 1.1); SHOW(s + ".vq0, " + s + ".vqb1", st + 1.2, 0.3);
  tl.fromTo(s + ".nq", {{ scale: 1 }}, {{ scale: 1.5, duration: 0.18, yoyo: true, repeat: 1 }}, st + 1.1);
  tl.fromTo(s + ".nqb", {{ scale: 1 }}, {{ scale: 1.5, duration: 0.18, yoyo: true, repeat: 1 }}, st + 1.1);
  // pass gates and lines
  const pg = T + at("pg", 4.2);
  DRAW(s + ".pg", pg, 0.6, null, 0.03); DRAW(s + ".bl", pg + 0.3, 0.7); DRAW(s + ".wl", pg + 0.5, 0.8);
  SHOW(s + ".pl, " + s + ".bll, " + s + ".wll", pg + 0.8, 0.3, 0.06);
  if (q.read != null) {{
    const r = T + q.read;
    OUT(s + ".m-hold, " + s + ".ms-hold", r - 0.25); IN(s + ".m-read", r); IN(s + ".ms-read", r + 0.2);
    SHOW(s + ".b-vdd", r + 0.2, 0.3);
    tl.to(s + ".wl", {{ strokeWidth: 12, duration: 0.3 }}, T + at("wlon", q.read + 1.0)); SHOW(s + ".b-wl", T + at("wlon", q.read + 1.0), 0.3);
    tl.to(s + ".pgch", {{ stroke: "#39c5cf", duration: 0.3 }}, T + at("wlon", q.read + 1.0));
    const f = T + at("flow", q.read + 1.6), fd = at("flowdur", 3.4);
    FLOW(s + ".flow-read", f, fd, 2.2);
    tl.to(s + ".blL", {{ stroke: "#5b4a80", duration: fd * 0.8, ease: "power1.in" }}, f + 0.2);
    SHOW(s + ".b-bump", T + at("bump", q.read + 3.0), 0.3);
    tl.fromTo(s + ".nq", {{ scale: 1 }}, {{ scale: 1.7, duration: 0.25, yoyo: true, repeat: 3 }}, T + at("bump", q.read + 3.0));
    IN(s + ".r1", T + at("rule1", q.read + 4.4));
  }}
  if (q.write != null) {{
    const w = T + q.write;
    OUT(s + ".m-read, " + s + ".ms-read", w - 0.25); IN(s + ".m-write", w); IN(s + ".ms-write", w + 0.2);
    FADE(s + ".b-bump, " + s + ".b-vdd", w - 0.2, 0, 0.2);
    tl.to(s + ".blL", {{ stroke: "#bc8cff", duration: 0.3 }}, w);
    SHOW(s + ".b-zero", w + 0.3, 0.3); tl.to(s + ".blR", {{ stroke: "#f85149", duration: 0.3 }}, w + 0.3);
    const f = T + at("fight", q.write + 0.9), fd = at("fightdur", 3.0);
    FLOW(s + ".flow-write", f, fd, 2.0);
    tl.to(s + ".vqb1, " + s + ".vq0", {{ opacity: 0, duration: 0.2 }}, f + fd - 0.5); SHOW(s + ".vqb0, " + s + ".vq1", f + fd - 0.4, 0.3);
    tl.fromTo(s + ".nqb", {{ scale: 1 }}, {{ scale: 1.7, duration: 0.2, yoyo: true, repeat: 1 }}, f + fd - 0.5);
    IN(s + ".r2", T + at("rule2", q.write + 2.4));
    if (q.both != null) IN(s + ".r3", T + q.both);
  }}"""
    return "".join(out), js


# ----------------------------------------------------------------------------- butterfly curves
def butterfly(sid, D, c, pics, data, q=None, kicker="The cell", ttl="How much noise can the cell take?"):
    q = R_(q, c, D)
    m = head(kicker, ttl) + f"""
<svg id="{sid}-plot" viewBox="0 0 760 760" style="left:120px;top:176px;width:700px;height:700px" data-layout-ignore></svg>
<div class="big bf-num" style="left:960px;top:300px;font-size:150px;color:var(--blue)"><span class="bf-val">0</span><span style="font-size:60px;font-weight:700"> mV</span></div>
<div class="big bf-what" style="left:968px;top:240px;font-size:40px;font-weight:700;color:var(--mut)">static noise margin</div>
<div class="chip bf-c1" style="left:966px;top:500px;color:var(--blue)">hold: word line off</div>
<div class="chip bf-c2" style="left:966px;top:574px;color:var(--orange)">read: word line on, bit lines at VDD</div>
<div class="chip bf-c3" style="left:966px;top:648px;color:var(--red)">read, worst process corner</div>
<div class="note bf-n" style="left:966px;top:740px;width:820px">The largest square between the two inverter curves: the noise voltage the cell survives.</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ", B = DATA.butterfly, pl = P + "-plot";
  const fx = (v) => 90 + v / 1.9 * 640, fy = (v) => 690 - v / 1.9 * 640;
  SVGEL(pl, "path", {{ d: "M90,50L90,690L730,690", stroke: "#2a3442", "stroke-width": 3, fill: "none" }});
  for (let v = 0.5; v < 1.9; v += 0.5) {{
    SVGEL(pl, "path", {{ d: "M" + fx(v) + ",690L" + fx(v) + ",50M90," + fy(v) + "L730," + fy(v), stroke: "#1b2431", "stroke-width": 2, fill: "none" }});
    SVGEL(pl, "text", {{ x: fx(v), y: 722, "font-size": 22, "text-anchor": "middle", fill: "#8b96a5" }}).textContent = v.toFixed(1);
    SVGEL(pl, "text", {{ x: 74, y: fy(v) + 8, "font-size": 22, "text-anchor": "end", fill: "#8b96a5" }}).textContent = v.toFixed(1);
  }}
  SVGEL(pl, "text", {{ x: 410, y: 756, "font-size": 24, "text-anchor": "middle", fill: "#8b96a5" }}).textContent = "V(QB)  [V]";
  SVGEL(pl, "text", {{ x: 30, y: 370, "font-size": 24, "text-anchor": "middle", fill: "#8b96a5", transform: "rotate(-90 30 370)" }}).textContent = "V(Q)  [V]";
  function curves(key, col, cls) {{
    const d = B[key];
    SVGEL(pl, "path", {{ class: "dr " + cls, pathLength: 1, d: PATHD(d.vin, d.fl, fx, fy), stroke: col, "stroke-width": 5 }});
    SVGEL(pl, "path", {{ class: "dr " + cls, pathLength: 1, d: PATHD(d.fr, d.vin, fx, fy), stroke: col, "stroke-width": 5, opacity: 0.6 }});
    const r = SVGEL(pl, "rect", {{ class: "sq " + cls + "-sq", x: fx(d.sq[0]), y: fy(d.sq[1] + d.sq[2]), width: d.sq[2] / 1.9 * 640, height: d.sq[2] / 1.9 * 640,
      fill: col, "fill-opacity": 0.22, stroke: col, "stroke-width": 3, opacity: 0 }});
    return d;
  }}
  const h = curves("hold_tt", "#58a6ff", "c-hold"), r = curves("read_tt", "#e0a03a", "c-read"), w = curves("read_sf", "#f85149", "c-worst");
  tl.set(s + ".bf-c2, " + s + ".bf-c3", {{ opacity: 0 }}, 0);
  const t0 = T + (q.curves == null ? 0.9 : q.curves);
  DRAW(s + ".c-hold", t0, 1.1, "power2.inOut", 0.5);
  const tsq = T + (q.square == null ? (q.curves || 0.9) + 2.0 : q.square);
  IN(s + ".bf-what", t0 + 0.2); IN(s + ".bf-num", tsq - 0.15); IN(s + ".bf-c1", t0 + 1.2); IN(s + ".bf-n", t0 + 1.6);
  POP(s + ".c-hold-sq", tsq, {{ from: 0.2 }}); COUNT(s + ".bf-val", tsq, 0, Math.round(h.snm * 1000), 0.9);
  if (q.read != null) {{
    const tr = T + q.read;
    FADE(s + ".c-hold, " + s + ".c-hold-sq", tr, 0.14, 0.4);
    DRAW(s + ".c-read", tr + 0.1, 0.9, "power2.inOut", 0.3); POP(s + ".c-read-sq", tr + 1.0, {{ from: 0.2 }});
    COUNT(s + ".bf-val", tr + 0.6, Math.round(h.snm * 1000), Math.round(r.snm * 1000), 0.9);
    tl.to(s + ".bf-num", {{ color: "#e0a03a", duration: 0.4 }}, tr + 0.6); IN(s + ".bf-c2", tr + 0.6);
  }}
  if (q.worst != null) {{
    const tw = T + q.worst;
    FADE(s + ".c-read, " + s + ".c-read-sq", tw, 0.2, 0.4);
    DRAW(s + ".c-worst", tw + 0.1, 0.9, "power2.inOut", 0.3); POP(s + ".c-worst-sq", tw + 1.0, {{ from: 0.2 }});
    COUNT(s + ".bf-val", tw + 0.6, Math.round(r.snm * 1000), Math.round(w.snm * 1000), 0.9);
    tl.to(s + ".bf-num", {{ color: "#f85149", duration: 0.4 }}, tw + 0.6); IN(s + ".bf-c3", tw + 0.6);
  }}"""
    return m, js


# ----------------------------------------------------------------------------- cell layout, layer by layer
def layers(sid, D, c, pics, data, q=None, kicker="The layout", ttl="One cell, drawn with the logic design rules"):
    q = R_(q, c, D)
    from video import script as L
    pw, ph = A.PANEL
    p = pics["cell_l5"]
    X0, Y0 = L.CELL[0], L.CELL[1]
    g = lambda x, y: A.px(p["box"], p["size"], X0 + x, Y0 + y)
    cx1, cy1 = g(0, L.CH)
    cx2, cy2 = g(L.CW, 0)
    left, top = 120, 190
    imgs = "".join(f'<img class="ly ly{k}" src="{pics[f"cell_l{k}"]["file"]}" width="{pw}" height="{ph}">' for k in range(1, 6))
    calls = [("k-n", 0.6, 0.70, "n strips: pull-down + pass gate", "#3fb950", "l1"), ("k-p", 2.42, 0.10, "p strips in one n-well: pull-ups", "#3fb950", "l1"),
             ("k-poly", 1.2, 0.215, "one poly = one inverter gate", "#f85149", "l2"), ("k-x", 2.42, 0.455, "cross-coupling contacts", "#e3b341", "l3"),
             ("k-wl", 3.6, 0.455, "word line (metal 1)", "#58a6ff", "l4"), ("k-bl", 0.485, 0.05, "bit line (metal 2)", "#bc8cff", "l5")]
    call_html = ""
    for cid, x, y, txt, col, _ in calls:
        px_, py_ = g(x, y)
        call_html += (f'<div class="call {cid}" style="left:{left + px_ + 26:.0f}px;top:{top + py_ - 62:.0f}px;color:{col}">{txt}</div>'
                      f'<svg class="{cid}-dot" style="left:{left + px_ - 12:.0f}px;top:{top + py_ - 12:.0f}px;width:24px;height:24px" data-layout-ignore>'
                      f'<circle cx="12" cy="12" r="8" fill="{col}" stroke="#0b0f17" stroke-width="3"/></svg>')
    legend = [("n-well + diffusion", "l1"), ("poly gates", "l2"), ("contacts + local interconnect", "l3"), ("metal 1", "l4"), ("metal 2", "l5")]
    leg = "".join(f'<span class="tag lg lg-{k}" style="font-size:23px;padding:8px 18px">{t}</span>' for t, k in legend)
    m = head(kicker, ttl) + f"""
<div class="lay" style="left:{left}px;top:{top}px;width:{pw}px;height:{ph}px" data-layout-ignore>{imgs}</div>
<svg style="left:{left}px;top:{top}px;width:{pw}px;height:{ph}px" viewBox="0 0 {pw} {ph}" data-layout-ignore>
<rect class="dr cellbox" pathLength="1" x="{cx1:.1f}" y="{cy1:.1f}" width="{cx2 - cx1:.1f}" height="{cy2 - cy1:.1f}" stroke="#e3b341" stroke-width="5"/></svg>
<div class="call cb-l" style="left:{left + cx1 + 10:.0f}px;top:{top + cy1 - 54:.0f}px;color:var(--yellow)">one cell: {L.CW:.2f} × {L.CH:.2f} µm</div>
{call_html}
<div style="position:absolute;left:{left}px;top:{top + ph + 18}px;display:flex;gap:12px">{leg}</div>
<div class="cmp" style="position:absolute;left:1180px;top:{top + 60}px;width:600px;height:330px" data-layout-ignore>
  <div class="panel" style="left:0;top:0;width:600px;height:330px;background:rgba(10,13,18,.94)"></div>
  <div class="cmp-a" style="position:absolute;left:44px;bottom:66px;width:150px;height:98px;background:rgba(88,166,255,.28);border:3px solid var(--blue)"></div>
  <div class="cmp-b" style="position:absolute;left:250px;bottom:66px;width:300px;height:114px;background:rgba(227,179,65,.28);border:3px solid var(--yellow)"></div>
  <div class="cmp-ta" style="position:absolute;left:44px;bottom:22px;font-size:24px;color:var(--blue);font-weight:700">foundry cell</div>
  <div class="cmp-tb" style="position:absolute;left:250px;bottom:22px;font-size:24px;color:var(--yellow);font-weight:700">this cell: {L.R['cell_area']:.2f} µm²</div>
  <div class="cmp-h" style="position:absolute;left:44px;top:26px;font-size:34px;font-weight:900">≈ 2× the area</div>
  <div class="cmp-s" style="position:absolute;left:44px;top:74px;font-size:24px;color:var(--mut)">the price of using no rule waivers</div>
</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  const at = (k, d) => T + (q[k] == null ? d : q[k]);
  tl.set(s + ".call, " + s + ".lg, " + s + ".cmp, " + s + "svg[class$='-dot']", {{ opacity: 0 }}, 0);
  const lt = [at("l1", 0.6), at("l2", 1.5), at("l3", 2.4), at("l4", 3.3), at("l5", 4.0)];
  for (let k = 1; k <= 5; k++) {{ WIPE(s + ".ly" + k, lt[k - 1], 0.9); IN(s + ".lg-l" + k, lt[k - 1] + 0.2, {{ d: 0.4, y: 8 }}); }}
  DRAW(s + ".cellbox", at("box", 0.9), 0.9); IN(s + ".cb-l", at("box", 0.9) + 0.5);
  const calls = {J([(cid, lay) for cid, _, _, _, _, lay in calls])};
  calls.forEach(([id, lay]) => {{
    if (q[id] == null) return;
    POP(s + "." + id + "-dot", T + q[id]); IN(s + "." + id, T + q[id] + 0.1, {{ y: 10 }});
    if (q[id + "_out"] != null) {{ OUT(s + "." + id + ", " + s + "." + id + "-dot", T + q[id + "_out"]); }}
  }});
  if (q.cmp != null) {{
    SHOW(s + ".cmp", T + q.cmp, 0.3);
    tl.fromTo(s + ".cmp-a", {{ scaleY: 0, transformOrigin: "50% 100%" }}, {{ scaleY: 1, duration: 0.5, ease: "power3.out" }}, T + q.cmp + 0.2);
    tl.fromTo(s + ".cmp-b", {{ scaleX: 0, scaleY: 0, transformOrigin: "0% 100%" }}, {{ scaleX: 1, scaleY: 1, duration: 0.7, ease: "power3.out" }}, T + q.cmp + 0.6);
    if (q.cmp_out != null) OUT(s + ".cmp", T + q.cmp_out);
  }}"""
    return m, js


# ----------------------------------------------------------------------------- deep zoom through the layout
def zoom(sid, D, c, pics, data, chain="chain_cell", way=None, overlays=(), kicker="The layout", ttl="From one cell to the array"):
    """way: [(time, level index), ...] camera waypoints. overlays: [(time, html, style, out time or None)]."""
    way, overlays = R_(way, c, D), R_(overlays, c, D)
    lv = pics[chain]
    L0, B0, R0, T0 = lv[-1]["box"]
    k = 1920 / (R0 - L0)
    imgs, frames = "", []
    for i, e in reversed(list(enumerate(lv))):
        l, b, r, t = e["ibox"]
        imgs += (f'<img class="zi zi{i}" src="{e["file"]}" style="position:absolute;left:{(l - L0) * k:.3f}px;top:{(T0 - t) * k:.3f}px;'
                 f'width:{(r - l) * k:.3f}px;height:{(t - b) * k:.3f}px">')
    for e in lv:
        l, b, r, t = e["box"]
        sc = (R0 - L0) / (r - l)
        frames.append(dict(s=sc, x=-(l - L0) * k * sc, y=-(T0 - t) * k * sc, cov=(e["ibox"][2] - e["ibox"][0]) / (R0 - L0)))
    ov = "".join(f'<div class="zo zo{j}" style="position:absolute;{st}">{h_}</div>' for j, (_, h_, st, _) in enumerate(overlays))
    m = f"""
<div style="position:absolute;inset:0;overflow:hidden" data-layout-ignore><div class="world" id="{sid}-world" style="position:absolute;left:0;top:0;width:1920px;height:1080px">{imgs}</div></div>
<div style="position:absolute;left:0;top:0;right:0;height:200px;background:linear-gradient(to bottom,rgba(8,11,16,.94),rgba(8,11,16,0))" data-layout-ignore></div>
{head(kicker, ttl)}{ov}"""
    js = f"""
  const F = {J(frames)}, way = {J(way)}, s = P + " ", wd = P + "-world";
  gsap.set(wd, {{ transformOrigin: "0 0" }});
  const ez = gsap.parseEase("power2.inOut");
  gsap.set(wd, {{ scale: F[way[0][1]].s, x: F[way[0][1]].x, y: F[way[0][1]].y }});
  for (let i = 0; i < way[0][1]; i++) gsap.set(s + ".zi" + i, {{ opacity: 0 }});
  for (let j = 1; j < way.length; j++) {{
    const a = F[way[j - 1][1]], b = F[way[j][1]];
    if (a === b) continue;
    const t0 = T + way[j - 1][0], dur = way[j][0] - way[j - 1][0];
    const zoomEase = (p) => (a.s * Math.pow(b.s / a.s, ez(p)) - a.s) / (b.s - a.s);      // even zoom speed in log scale
    tl.fromTo(wd, {{ scale: a.s, x: a.x, y: a.y }}, {{ scale: b.s, x: b.x, y: b.y, duration: dur, ease: zoomEase, immediateRender: false }}, t0);
    const when = (sc) => {{ const e = Math.log(sc / a.s) / Math.log(b.s / a.s); let lo = 0, hi = 1;
      for (let n = 0; n < 30; n++) {{ const mid = (lo + hi) / 2; if (ez(mid) < e) lo = mid; else hi = mid; }} return t0 + lo * dur; }};
    // a level fades out just before it stops covering the frame (zooming out), or fades in once it covers it (zooming in)
    for (let i = 0; i < F.length - 1; i++) {{
      const s1 = 1.5 / F[i].cov, s2 = 1.08 / F[i].cov, lo = Math.min(a.s, b.s), hi = Math.max(a.s, b.s);
      if (s2 >= hi || s1 <= lo) continue;
      const u1 = Math.min(hi, Math.max(lo, s1)), u2 = Math.min(hi, Math.max(lo, s2));
      const ta = when(u1), tb = when(u2);
      if (b.s < a.s) tl.fromTo(s + ".zi" + i, {{ opacity: 1 }}, {{ opacity: 0, duration: Math.max(0.05, tb - ta), ease: "none", immediateRender: false }}, ta);
      else tl.fromTo(s + ".zi" + i, {{ opacity: 0 }}, {{ opacity: 1, duration: Math.max(0.05, ta - tb), ease: "none", immediateRender: false }}, tb);
    }}
  }}
  const ov = {J([(t, o) for (t, _, _, o) in overlays])};
  tl.set(s + ".zo", {{ opacity: 0 }}, 0);
  ov.forEach(([t, o], j) => {{ IN(s + ".zo" + j, T + t, {{ y: 14 }}); if (o != null) OUT(s + ".zo" + j, T + o); }});"""
    return m, js


# ----------------------------------------------------------------------------- timing diagram
def timing(sid, D, c, pics, data, q=None, kicker="The periphery", ttl="One clock, two phases, no self-timed pulses"):
    q = R_(q, c, D)
    x0, per = 330, 600                     # left edge and pixels per clock period
    rows = [("clk", 70, "#8b96a5"), ("inputs", 180, "#58a6ff"), ("word line", 290, "#39c5cf"), ("bit line", 400, "#bc8cff"), ("dout", 510, "#3fb950")]

    def wave(y, pts):
        return "M" + "L".join(f"{x0 + a * per:.1f},{y - b * 56:.1f}" for a, b in pts)
    e = 0.03
    W = {
        "clk": [(0, 0), (0.1, 0), (0.1 + e, 1), (0.6, 1), (0.6 + e, 0), (1.1, 0), (1.1 + e, 1), (1.6, 1), (1.6 + e, 0), (2.1, 0), (2.1 + e, 1), (2.3, 1)],
        "inputs": [(0, 0.5), (0.04, 1), (1.0, 1), (1.03, 0.5), (1.06, 1), (2.0, 1), (2.03, 0.5), (2.06, 1), (2.3, 1)],
        "inputs2": [(0, 0.5), (0.04, 0), (1.0, 0), (1.03, 0.5), (1.06, 0), (2.0, 0), (2.03, 0.5), (2.06, 0), (2.3, 0)],
        "word line": [(0, 0), (0.66, 0), (0.69, 1), (1.14, 1), (1.17, 0), (1.66, 0), (1.69, 1), (2.14, 1), (2.17, 0), (2.3, 0)],
        "bit line": [(0, 1), (0.71, 1), (0.84, 0.04), (1.18, 0.04), (1.3, 1), (1.7, 1), (1.76, 0), (2.18, 0), (2.3, 0.7)],
        "dout": [(0, 0.5), (0.04, 1), (0.88, 1), (0.92, 0.5), (0.95, 0), (2.3, 0)],
        "dout2": [(0, 0.5), (0.04, 0), (0.88, 0), (0.92, 0.5), (0.95, 1), (2.3, 1)],
    }
    svg = []
    for name, y, col in rows:
        svg.append(f'<text class="tm-l" x="{x0 - 30}" y="{y - 18}" font-size="30" font-weight="700" text-anchor="end" fill="{col}">{name}</text>')
        svg.append(f'<path class="dr tm-w" pathLength="1" d="{wave(y, W[name])}" stroke="{col}" stroke-width="5"/>')
        if name + "2" in W:
            svg.append(f'<path class="dr tm-w" pathLength="1" d="{wave(y, W[name + "2"])}" stroke="{col}" stroke-width="5"/>')
    bands = [(0.1, 0.6, "clk high|precharge + decode", "#e0a03a", "hi"), (0.6, 1.1, "clk low|read", "#3fb950", "lo"),
             (1.1, 1.6, "clk high|precharge + decode", "#e0a03a", "hi"), (1.6, 2.1, "clk low|write", "#f85149", "lo")]
    for a, b, txt, col, cls in bands:
        svg.append(f'<g class="tm-b tm-{cls}" opacity="0"><rect x="{x0 + a * per + 8}" y="-10" width="{(b - a) * per}" height="545" fill="{col}" fill-opacity="0.10" stroke="{col}" '
                   f'stroke-opacity="0.5" stroke-width="2"/><text x="{x0 + (a + b) / 2 * per + 8}" y="576" font-size="22" font-weight="700" text-anchor="middle" style="fill:#8b96a5">{txt.split("|")[0]}</text>'
                   f'<text x="{x0 + (a + b) / 2 * per + 8}" y="612" font-size="27" font-weight="700" text-anchor="middle" style="fill:{col}">{txt.split("|")[1]}</text></g>')
    svg.append(f'<path class="tm-ph" d="M{x0},-20L{x0},550" stroke="#e6edf3" stroke-width="3" opacity="0"/>')
    m = head(kicker, ttl) + f"""
<div class="tm-wrap" id="{sid}-wrap" style="position:absolute;left:0;top:210px;width:1920px;height:640px" data-layout-ignore>
<svg viewBox="0 0 1920 640" style="left:0;top:0;width:1920px;height:640px">{''.join(svg)}</svg></div>
<div class="chip tm-x1" style="left:1240px;top:150px;color:var(--mut);text-decoration:line-through">sense amplifier</div>
<div class="chip tm-x2" style="left:1500px;top:150px;color:var(--mut);text-decoration:line-through">self-timed pulse</div>
<div class="chip tm-slow" style="left:1240px;top:150px;color:var(--green)">phase too short? slow the clock down</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  const at = (k, d) => T + (q[k] == null ? d : q[k]);
  tl.set(s + ".tm-x1, " + s + ".tm-x2, " + s + ".tm-slow", {{ opacity: 0 }}, 0);
  SHOW(s + ".tm-l", T + 0.4, 0.3, 0.08);
  const d0 = at("draw", 0.8), dd = q.drawdur || 4.5;
  DRAW(s + ".tm-w", d0, dd, "none");
  tl.fromTo(s + ".tm-ph", {{ opacity: 0, x: 0 }}, {{ opacity: 0.8, x: {2.3 * per}, duration: dd, ease: "none" }}, d0);
  tl.to(s + ".tm-ph", {{ opacity: 0, duration: 0.3 }}, d0 + dd);
  if (q.strike != null) {{ IN(s + ".tm-x1", T + q.strike); IN(s + ".tm-x2", T + q.strike + 0.5); OUT(s + ".tm-x1, " + s + ".tm-x2", T + (q.strike_out || q.strike + 4)); }}
  SHOW(s + ".tm-hi", at("hi", 5.6), 0.5, 0.15); SHOW(s + ".tm-lo", at("lo", 7.6), 0.5, 0.15);
  if (q.slow != null) {{
    IN(s + ".tm-slow", T + q.slow);
    tl.fromTo(P + "-wrap", {{ scaleX: 1, transformOrigin: "{x0}px 50%" }}, {{ scaleX: 1.1, duration: 1.2, ease: "power2.inOut" }}, T + q.slow + 0.3);
  }}"""
    return m, js


# ----------------------------------------------------------------------------- the complete memory
def chip(sid, D, c, pics, data, q=None, kicker="From RTL to GDS", ttl="The complete memory"):
    q = R_(q, c, D)
    from video import script as L
    p = pics["z4_chip"]
    fx0, fy0, fw = 200, 140, 1520
    fh = fw * 1080 / 1920
    g = lambda x, y: tuple(v * fw / 1920 for v in A.px(p["box"], (1920, 1080), x, y))
    R = L.R
    boxes = [("array", L.MACRO[0], L.MACRO[1], L.MACRO[2], L.MACRO[3], "6T array · custom layout", "#e3b341"),
             ("dec", 6, L.MY, L.MX - 1, L.MY + R["macro_h"], "row decoder", "#39c5cf"),
             ("col", 6, 11, L.FULL[2] - 6, L.MY - 1, "column circuits, registers, clocking · standard cells", "#bc8cff")]
    svg, lab = "", ""
    for cid, x1, y1, x2, y2, txt, col in boxes:
        ax, ay = g(x1, y2)
        bx, by = g(x2, y1)
        svg += f'<rect class="dr cb-{cid}" pathLength="1" x="{ax:.1f}" y="{ay:.1f}" width="{bx - ax:.1f}" height="{by - ay:.1f}" stroke="{col}" stroke-width="6" rx="6"/>'
        lab += f'<div class="call cl-{cid}" style="left:{fx0 + ax + 14:.0f}px;top:{fy0 + ay + 14:.0f}px;color:{col}">{txt}</div>'
    tools = "".join(f'<span class="tag tl-t" style="font-size:24px;padding:8px 18px">{t}</span>' for t in ("Yosys", "OpenROAD", "Magic", "KLayout", "Netgen"))
    m = f"""{head(kicker, ttl)}
<div style="position:absolute;left:{fx0}px;top:{fy0}px;width:{fw}px;height:{fh:.0f}px;overflow:hidden" data-layout-ignore>
<img id="{sid}-img" src="{p['file']}" style="position:absolute;left:0;top:0;width:{fw}px;height:{fh:.0f}px"></div>
<svg viewBox="0 0 {fw} {fh:.0f}" style="left:{fx0}px;top:{fy0}px;width:{fw}px;height:{fh:.0f}px" data-layout-ignore>{svg}</svg>{lab}
<div class="chip ch-size" style="left:96px;top:880px;color:var(--fg)">{R['die_w']:g} × {R['die_h']:g} µm · {R['mosfets']:,} transistors</div>
<div style="position:absolute;right:96px;top:64px;display:flex;gap:10px">{tools}</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ";
  const at = (k, d) => T + (q[k] == null ? d : q[k]);
  tl.fromTo(P + "-img", {{ scale: 1.05 }}, {{ scale: 1.0, duration: D, ease: "none" }}, T);
  tl.set(s + ".call, " + s + ".ch-size, " + s + ".tl-t", {{ opacity: 0 }}, 0);
  [["array", at("array", 0.8)], ["dec", at("dec", 1.8)], ["col", at("col", 2.6)]].forEach(([id, t]) => {{ DRAW(s + ".cb-" + id, t, 0.9); IN(s + ".cl-" + id, t + 0.5, {{ y: 8 }}); }});
  IN(s + ".tl-t", at("tools", 1.2), {{ s: 0.18, y: -10 }});
  IN(s + ".ch-size", at("size", 4.2));"""
    return m, js


# ----------------------------------------------------------------------------- sign-off terminal
def signoff(sid, D, c, pics, data, rows=None, q=None, kicker="Sign-off", ttl="The final layout", stamp=None, th=680):
    q = R_(q, c, D)
    """rows: [(text, css class, result text or None)]; each row types in, its result pops."""
    lines = ""
    for i, (txt, cls, res) in enumerate(rows):
        r = f'<span class="ok res res{i}">{html.escape(res)}</span>' if res else ""
        lines += f'<div class="row {cls} rw rw{i}"><span class="typ typ{i}">{html.escape(txt) or "&nbsp;"}</span>{r}</div>'
    st = f'<div class="big sg-stamp" style="left:1290px;top:330px;font-size:70px;color:var(--green);line-height:1.2;white-space:pre-line">{stamp}</div>' if stamp else ""
    m = head(kicker, ttl) + f'<div class="term" style="left:96px;top:190px;width:1130px;height:{th}px" data-layout-ignore>{lines}</div>{st}'
    js = f"""
  const q = {J(q or {})}, s = P + " ", n = {len(rows)};
  const t0 = T + (q.start == null ? 0.7 : q.start), span = (q.span || Math.min(D - 3.2, n * 0.62));
  for (let i = 0; i < n; i++) {{
    const t = t0 + span * i / n;
    tl.fromTo(s + ".typ" + i, {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: 0.45, ease: "none" }}, t);
    if (Q(s + ".res" + i)) POP(s + ".res" + i, t + 0.5, {{ from: 0.5, d: 0.35 }});
  }}
  if (Q(s + ".sg-stamp")) IN(s + ".sg-stamp", T + (q.stamp == null ? t0 - T + span + 0.3 : q.stamp), {{ d: 0.6 }});"""
    return m, js


# ----------------------------------------------------------------------------- post-layout waveforms
def waves(sid, D, c, pics, data, q=None, kicker="Does it work?", ttl="Post-layout SPICE: write, then read"):
    q = R_(q, c, D)
    rows = [("clk", [("clk", "#8b96a5")]), ("word lines", [("wl21", "#39c5cf"), ("wl42", "#e3b341")]), ("bit lines", [("bl0", "#bc8cff"), ("blb0", "#e0a03a")]),
            ("cell", [("q_42_0", "#e3b341"), ("qb_42_0", "#3fb950")]), ("dout", [("dout0", "#58a6ff"), ("dout1", "#3fb950")])]
    names = {"wl21": "WL[21]", "wl42": "WL[42]", "bl0": "BL[0]", "blb0": "BLB[0]", "q_42_0": "Q", "qb_42_0": "QB", "dout0": "dout[0]", "dout1": "dout[1]"}
    lab = ""
    for i, (name, sigs) in enumerate(rows):
        y = 60 + i * 118
        lab += f'<text x="300" y="{y + 44}" font-size="28" font-weight="700" text-anchor="end" fill="#8b96a5">{name}</text>'
        for j, (sg, col) in enumerate(sigs):
            if sg in names:
                lab += f'<text x="{1650 + 0}" y="{y + 30 + j * 34}" font-size="24" font-weight="700" fill="{col}">{names[sg]}</text>'
    marks = "".join(f'<g class="wv-m wv-m{k}" opacity="0"><path d="M{x},20L{x},640" stroke="#2a3442" stroke-width="2" stroke-dasharray="6 6"/>'
                    f'<text x="{x + 10}" y="18" font-size="24" font-weight="700" fill="#e6edf3">{t}</text></g>'
                    for k, (x, t) in enumerate([(330 + (60 - 58) / 66 * 1300, "write word 42"), (330 + (80 - 58) / 66 * 1300, "read word 21"), (330 + (100 - 58) / 66 * 1300, "read word 42")]))
    m = head(kicker, ttl) + f"""
<svg id="{sid}-w" viewBox="0 0 1920 680" style="left:0;top:180px;width:1920px;height:680px" data-layout-ignore>{lab}{marks}
<path class="wv-ph" d="M330,20L330,640" stroke="#e6edf3" stroke-width="3" opacity="0"/></svg>
<div class="chip wv-t" style="left:1180px;top:118px;color:var(--blue)">clock ↓ to data out: <span class="wv-n">0.0</span> ns</div>
<div class="chip wv-t2" style="left:1180px;top:118px;color:var(--orange)">slow corner: <span class="wv-n2">0.0</span> ns</div>"""
    js = f"""
  const q = {J(q)}, s = P + " ", Wv = DATA.waves, sv = P + "-w", rows = {J(rows)};
  const fx = (t) => 330 + (t - 58) / 66 * 1300;
  rows.forEach(([name, sigs], i) => {{
    const y0 = 60 + i * 118 + 70, fy = (v) => y0 - v / 1.8 * 62;
    SVGEL(sv, "path", {{ d: "M330," + y0 + "L1630," + y0, stroke: "#1b2431", "stroke-width": 2, fill: "none" }});
    sigs.forEach(([sg, col]) => SVGEL(sv, "path", {{ class: "dr wv-p", pathLength: 1, d: PATHD(Wv.t, Wv.sig[sg], fx, fy), stroke: col, "stroke-width": 4 }}));
  }});
  tl.set(s + ".wv-t, " + s + ".wv-t2", {{ opacity: 0 }}, 0);
  const d0 = T + (q.draw == null ? 0.8 : q.draw), dd = q.drawdur || Math.max(4, D - 5);
  DRAW(s + ".wv-p", d0, dd, "none");
  tl.fromTo(s + ".wv-ph", {{ opacity: 0, x: 0 }}, {{ opacity: 0.85, x: 1300, duration: dd, ease: "none" }}, d0);
  tl.to(s + ".wv-ph", {{ opacity: 0, duration: 0.3 }}, d0 + dd);
  [0, 1, 2].forEach((k) => SHOW(s + ".wv-m" + k, d0 + dd * ([60, 80, 100][k] - 58) / 66, 0.3));
  if (q.tcq != null) {{ IN(s + ".wv-t", T + q.tcq); COUNT(s + ".wv-n", T + q.tcq + 0.1, 0, {data['results']['timing']['tt']['t_cq_max']:.1f}, 0.8, true); }}
  if (q.tcq_ss != null) {{ OUT(s + ".wv-t", T + q.tcq_ss - 0.2); IN(s + ".wv-t2", T + q.tcq_ss); COUNT(s + ".wv-n2", T + q.tcq_ss + 0.1, 0, {data['results']['timing']['ss']['t_cq_max']:.1f}, 0.8, true); }}"""
    return m, js


# ----------------------------------------------------------------------------- closing
def wrap(sid, D, c, pics, data, q=None, kicker="Status", ttl="What you get, and what is still missing", items=(), warn=(), url=None):
    q = R_(q, c, D)
    it = "".join(f'<div class="chip wr-i" style="position:relative;display:block;margin-bottom:20px;font-weight:400;font-size:32px;padding:16px 26px">{html.escape(t)}</div>' for t in items)
    wn = "".join(f'<div class="chip wr-w" style="position:relative;display:block;margin-bottom:20px;font-weight:700;font-size:34px;padding:16px 26px;color:var(--orange);border-color:rgba(224,160,58,.5);white-space:normal">{html.escape(t)}</div>' for t in warn)
    u = f'<div class="big wr-url mono" style="left:96px;top:800px;font-size:46px;font-weight:700;color:var(--blue);letter-spacing:0">{html.escape(url)}</div>' if url else ""
    m = head(kicker, ttl) + f"""
<div class="wr-h1" style="position:absolute;left:96px;top:190px;font-size:30px;font-weight:700;color:var(--green);letter-spacing:.08em">IN THE REPOSITORY</div>
<div style="position:absolute;left:96px;top:244px;width:880px">{it}</div>
<div class="wr-h2" style="position:absolute;left:1010px;top:190px;font-size:30px;font-weight:700;color:var(--orange);letter-spacing:.08em">NOT DONE</div>
<div style="position:absolute;left:1010px;top:244px;width:800px">{wn}</div>{u}"""
    js = f"""
  const q = {J(q or {})}, s = P + " ";
  const at = (k, d) => T + (q[k] == null ? d : q[k]);
  SHOW(s + ".wr-h1", at("items", 0.6), 0.3); IN(s + ".wr-i", at("items", 0.6) + 0.15, {{ s: q.istep || 0.35, y: 14 }});
  SHOW(s + ".wr-h2", at("warn", 3.5), 0.3); IN(s + ".wr-w", at("warn", 3.5) + 0.15, {{ s: q.wstep || 0.6, y: 14 }});
  if (Q(s + ".wr-url")) IN(s + ".wr-url", at("url", D - 3.5), {{ d: 0.6 }});"""
    return m, js
