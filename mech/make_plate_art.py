"""Front plate artwork for JLCCNC (1:1, mm): CNC outline + holes, laser marking, UV print.

Writes avionics-panel-rev1-plate.dxf (R12, layers CUT / LASER / UV_ORANGE) and a coloured SVG preview.
The plate is black anodised aluminium. JLCCNC laser marking is single-tone (light grey on black), so the
white legends and frame lines are LASER; the amber shift legends and knob functions are UV printed
(UV_ORANGE). Geometry follows pcb/board.py and the 3D view.
"""
import math
import sys
from pathlib import Path

import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath, TextToPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pcb"))
import board as B  # noqa: E402
import stack as S  # noqa: E402

FONTS = Path(__file__).resolve().parent / "fonts"
SEMI = FontProperties(fname=str(FONTS / "BarlowSemiCondensed-SemiBold.ttf"))
TTP = TextToPath()

OVH = S.OVH                               # plate overhangs the PCB by clearance + wall
CAP = (9.6, 6.4)
HOLE = S.KEY_HOLE
SHAFT_HOLE, RANGE_HOLE = S.SHAFT_HOLE, S.RANGE_HOLE
LIGHT_HOLES = S.LIGHT_HOLES
KNOB_R = {k: d / 2 for k, d in S.KNOB_D.items()}

SHIFT_LEGENDS = [[shift for _, shift in row] for row in S.KEY_LEGENDS]   # stack.py holds the legends
# knob legends on the side facing the keys: (position, white text, amber text or None), one type size
KNOBS = {name: (pos, *S.KNOB_LEGENDS[name])
         for name, pos in (("ALTHDG", B.ALTHDG), ("RANGE", B.RANGE), ("FREQ", B.FREQ), ("FMS", B.FMS))}

layers = {"CUT": [], "LASER": [], "UV_ORANGE": []}     # closed polygons, PCB coordinates (y down)


# ---------------- geometry helpers ----------------
def rrect(cx, cy, w, h, r, n=8):
    pts = []
    for (qx, qy, a0) in ((cx + w / 2 - r, cy - h / 2 + r, -90), (cx + w / 2 - r, cy + h / 2 - r, 0),
                         (cx - w / 2 + r, cy + h / 2 - r, 90), (cx - w / 2 + r, cy - h / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((qx + r * math.cos(a), qy + r * math.sin(a)))
    return pts


def circle(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def bar(x0, y0, x1, y1, w=0.3):
    """A straight engraved line as a thin closed outline."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


FALLBACK = FontProperties(fname=str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans-Bold.ttf"))


def _font(ch, fp):
    return FALLBACK if ch == "⇆" else fp                      # Barlow has no flip-flop arrow


def advance(ch, fp, em):
    fp = _font(ch, fp)
    if ch == " ":
        return 0.26 * em
    w, _, _ = TTP.get_text_width_height_descent(ch, fp.copy(), ismath=False)
    return w * em / fp.get_size_in_points()


def glyph(ch, fp, em, x, y, rot):
    """Outline polygons of one glyph, centred on (x, y) in y-down coordinates, rotated by rot (rad)."""
    if ch == " ":
        return []
    w = advance(ch, fp, em)
    fp = _font(ch, fp)
    tp = TextPath((0, 0), ch, size=em, prop=fp)
    out = []
    c, s = math.cos(rot), math.sin(rot)
    for poly in tp.to_polygons(closed_only=True):
        pts = []
        for gx, gy in poly:
            lx, ly = gx - w / 2, -(gy - 0.35 * em)          # centre the glyph, y down, middle of cap height
            pts.append((x + lx * c - ly * s, y + lx * s + ly * c))
        out.append(pts)
    return out


def text(layer, s, x, y, fp, em, track=0.0, align="center"):
    chars = list(s)
    ws = [advance(ch, fp, em) for ch in chars]
    total = sum(ws) + track * (len(chars) - 1)
    cx = x - total / 2 if align == "center" else x
    for ch, w in zip(chars, ws, strict=True):
        layers[layer] += glyph(ch, fp, em, cx + w / 2, y, 0.0)
        cx += w + track
    return total


def arc_text(layer, segs, cx, cy, r, mid, track):
    """Same placement as the 3D view: letters face outward on the far half, inward on the near half."""
    near = math.sin(mid) > 0.01
    chars = [(ch, fp, em) for (t, fp, em) in segs for ch in t]
    ws = [advance(ch, fp, em) + track for ch, fp, em in chars]
    total = sum(ws) - track
    acc = 0.0
    for (ch, fp, em), w in zip(chars, ws, strict=True):
        off = (acc + (w - track) / 2 - total / 2) / r
        a = mid - off if near else mid + off
        rot = a - math.pi / 2 if near else a + math.pi / 2
        layers[layer] += glyph(ch, fp, em, cx + r * math.cos(a), cy + r * math.sin(a), rot)
        acc += w


# ---------------- CUT: outline and holes ----------------
layers["CUT"].append(rrect(B.W / 2, B.H / 2, B.W + 2 * OVH, B.H + 2 * OVH, B.CORNER_R + OVH, 12))
for y in B.ROWS:
    for x in B.COLS:
        layers["CUT"].append(rrect(x, y, HOLE[0], HOLE[1], HOLE[2]))
for name in ("ALTHDG", "FREQ", "FMS"):
    layers["CUT"].append(circle(*getattr(B, name), SHAFT_HOLE / 2))
layers["CUT"].append(circle(*B.RANGE, RANGE_HOLE / 2))
for name, d in LIGHT_HOLES.items():
    (lx, ly), _, _ = B.LEDS[name]
    layers["CUT"].append(circle(lx, ly, d / 2, 36))

# ---------------- LASER: frame, titles, white knob legends, pan arrows ----------------
def em(mm):
    return mm / 0.72                                    # the 3D view sizes text by 0.72 em = mm
x0, x1 = B.COLS[0] - CAP[0] / 2 - 3.0, B.COLS[6] + CAP[0] / 2 + 3.0
y0, y1 = B.ROWS[0] - CAP[1] / 2 - 4.2, B.ROWS[3] + CAP[1] / 2 + 4.6
vAP, vRadio = (B.COLS[2] + B.COLS[3]) / 2, (B.COLS[4] + B.COLS[5]) / 2
hFMS = (B.ROWS[1] + CAP[1] / 2 + 2.6 + B.ROWS[2] - CAP[1] / 2) / 2
TITLE_EM, TITLE_TRACK = em(1.75), 0.32
titles = [("AUTOPILOT", x0 + 3.5, y0), ("AUDIO", vAP + 3.0, y0), ("RADIO", vRadio + 3.0, y0), ("FMS", vAP + 3.0, hFMS)]
gaps = {}
for t, tx, ty in titles:
    w = text("LASER", t, tx, ty, SEMI, TITLE_EM, TITLE_TRACK, align="left")
    gaps.setdefault(round(ty, 3), []).append((tx - 0.7, tx + w + 0.7))


def hline(xa, xb, y):
    """Horizontal frame line, broken where a title sits on it."""
    segs = [(xa, xb)]
    for g0, g1 in gaps.get(round(y, 3), []):
        nxt = []
        for a, b in segs:
            if g1 <= a or g0 >= b:
                nxt.append((a, b))
            else:
                if g0 > a:
                    nxt.append((a, g0))
                if g1 < b:
                    nxt.append((g1, b))
        segs = nxt
    for a, b in segs:
        layers["LASER"].append(bar(a, y, b, y))


r = 1.6
hline(x0 + r, x1 - r, y0)
hline(x0 + r, x1 - r, y1)
layers["LASER"].append(bar(x0, y0 + r, x0, y1 - r))
layers["LASER"].append(bar(x1, y0 + r, x1, y1 - r))
for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
    for i in range(6):                                       # rounded corners as short bars
        a, b = math.radians(a0 + 15 * i), math.radians(a0 + 15 * (i + 1))
        layers["LASER"].append(bar(cx + r * math.cos(a), cy + r * math.sin(a),
                                   cx + r * math.cos(b), cy + r * math.sin(b)))
layers["LASER"].append(bar(vAP, y0, vAP, y1))
hline(vAP, x1, hFMS)
layers["LASER"].append(bar(vRadio, y0, vRadio, hFMS))

for name, ((kx, ky), main, shift) in KNOBS.items():
    R = KNOB_R.get(name)
    tilt = math.radians(S.KNOB_LEGEND_TILT[name])
    mid = tilt if kx < B.W / 2 else math.pi - tilt
    r0 = 12.2 if name == "RANGE" else R + 1.9
    arc_text("LASER", [(main, SEMI, em(1.55))], kx, ky, r0, mid, 0.22)
    if shift:
        arc_text("UV_ORANGE", [(shift, SEMI, em(1.5))], kx, ky, r0 + 2.2, mid, 0.22)
rx, ry = B.RANGE
for i in range(4):                                           # pan arrows
    a = i * math.pi / 2
    c, s = math.cos(a), math.sin(a)
    px, py = rx + 9.4 * c, ry + 9.4 * s
    tri = [(0.75, 0), (-0.45, -0.7), (-0.45, 0.7)]
    layers["LASER"].append([(px + u * c - v * s, py + u * s + v * c) for u, v in tri])

# ---------------- UV_ORANGE: shift legends under the keys ----------------
for rI, y in enumerate(B.ROWS):
    for cI, x in enumerate(B.COLS):
        t = SHIFT_LEGENDS[rI][cI]
        if t:
            text("UV_ORANGE", t, x, y + CAP[1] / 2 + 1.6, SEMI, em(1.7), 0.08)


# ---------------- writers ----------------
def write_dxf(path):
    out = ["0", "SECTION", "2", "ENTITIES"]
    for layer, polys in layers.items():
        for poly in polys:
            out += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
            for x, y in poly:
                # y up, origin bottom-left
                out += ["0", "VERTEX", "8", layer, "10", f"{x + OVH:.4f}", "20", f"{B.H + OVH - y:.4f}"]
            out += ["0", "SEQEND", "8", layer]
    out += ["0", "ENDSEC", "0", "EOF"]
    Path(path).write_text("\n".join(out) + "\n")


def write_svg(path):
    colours = {"CUT": ("none", "#202020"), "LASER": ("#d8dadd", "none"), "UV_ORANGE": ("#e0952a", "none")}
    w, h = B.W + 2 * OVH, B.H + 2 * OVH
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="{-OVH} {-OVH} {w} {h}">',
            f'<rect x="{-OVH}" y="{-OVH}" width="{w}" height="{h}" fill="#2d2f33"/>']
    for layer, polys in layers.items():
        fill, stroke = colours[layer]
        d = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in poly) + " Z" for poly in polys)
        body.append(f'<path d="{d}" fill="{fill}" fill-rule="evenodd" stroke="{stroke}" stroke-width="0.12"/>')
    body.append("</svg>")
    Path(path).write_text("\n".join(body))


write_dxf("avionics-panel-rev1-plate.dxf")
write_svg("avionics-panel-rev1-plate-preview.svg")
print({k: len(v) for k, v in layers.items()}, "polygons")
