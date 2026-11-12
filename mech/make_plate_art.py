"""Front plate artwork for JLCCNC (1:1, mm): CNC outline + holes, laser marking, UV print.

Writes avionics-panel-rev1-plate.dxf (R12, layers CUT / LASER / UV_AMBER) and a coloured SVG preview.
The plate is black anodised aluminium. JLCCNC laser marking is single-tone (light grey on black), so the
white legends and frame lines are LASER; the amber shift legends and knob functions are UV printed
(UV_AMBER). Geometry follows pcb/board.py and the 3D view.
"""
import math
import sys
from pathlib import Path

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath, TextToPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pcb"))
import board as B
import stack as S
from geom import rounded_rect

FONTS = Path(__file__).resolve().parent.parent / "viewer" / "fonts"
SEMI = FontProperties(fname=str(FONTS / "BarlowSemiCondensed-SemiBold.ttf"))
TTP = TextToPath()

OVH = S.OVH                               # plate overhangs the PCB by clearance + wall
CAP = (S.CAP["w"], S.CAP["h"])
HOLE = S.KEY_HOLE
SHAFT_HOLE, RANGE_HOLE = S.SHAFT_HOLE, S.RANGE_HOLE

SHIFT_LEGENDS = [[shift for _, shift in row] for row in S.KEY_LEGENDS]   # stack.py holds the legends
# knob legends on the side facing the keys: (position, white text, amber text or None), one type size
KNOBS = {name: (pos, *S.KNOB_LEGENDS[name])
         for name, pos in (("ALTHDG", B.ALTHDG), ("RANGE", B.RANGE), ("FREQ", B.FREQ), ("FMS", B.FMS))}

layers = {"CUT": [], "LASER": [], "UV_AMBER": []}     # closed polygons, PCB coordinates (y down)


# ---------------- geometry helpers ----------------
def circle(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def bar(x0, y0, x1, y1, w=S.KEY_FRAME["line"]):
    """A straight marked line as a thin closed outline."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def advance(ch, fp, em):
    if ch == " ":
        return S.PLATE_TEXT["space"] * em
    w, _, _ = TTP.get_text_width_height_descent(ch, fp.copy(), ismath=False)
    return w * em / fp.get_size_in_points()


def glyph(ch, fp, em, x, y, rot):
    """Outline polygons of one glyph, centred on (x, y) in y-down coordinates, rotated by rot (rad)."""
    if ch == " ":
        return []
    w = advance(ch, fp, em)
    tp = TextPath((0, 0), ch, size=em, prop=fp)
    out = []
    c, s = math.cos(rot), math.sin(rot)
    for poly in tp.to_polygons(closed_only=True):
        pts = []
        for gx, gy in poly:
            lx, ly = gx - w / 2, -(gy - S.PLATE_TEXT["mid"] * em)   # centre the glyph, y down, middle of cap height
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


def flip_legend(layer, s, x, y, fp, em, track):
    """A legend ending in the flip-flop arrows ("ADF ⇆"): the text, then the icon from stack.py."""
    body = s[:-1].rstrip()
    tw = sum(advance(ch, fp, em) for ch in body) + track * (len(body) - 1)
    x0 = x - (tw + (S.FLIP_GAP + S.FLIP_W) * em) / 2
    text(layer, body, x0, y, fp, em, track, align="left")
    ix = x0 + tw + S.FLIP_GAP * em
    layers[layer] += [[(ix + px * em, y + py * em) for px, py in poly] for poly in S.FLIP_ICON]


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
layers["CUT"].append(rounded_rect(-OVH, -OVH, B.W + OVH, B.H + OVH, B.CORNER_R + OVH))
for y in B.ROWS:
    for x in B.COLS:
        layers["CUT"].append(rounded_rect(x - HOLE[0] / 2, y - HOLE[1] / 2, x + HOLE[0] / 2, y + HOLE[1] / 2,
                                            HOLE[2], 8))
for name in ("ALTHDG", "FREQ", "FMS"):
    layers["CUT"].append(circle(*getattr(B, name), SHAFT_HOLE / 2))
layers["CUT"].append(circle(*B.RANGE, RANGE_HOLE / 2))
for (lx, ly), _, _ in B.LEDS.values():
    layers["CUT"].append(circle(lx, ly, S.LIGHT_HOLE / 2, 36))

# ---------------- LASER: frame, titles, white knob legends, pan arrows ----------------
def em(mm):
    return mm / S.PLATE_TEXT["cap"]                     # a capital height in mm as the font's em
FRAME, TITLE = S.key_frame(B.COLS, B.ROWS), S.GROUP_TITLE   # stack.py holds the frame and the titles
x0, x1, y0, y1 = (FRAME[k] for k in ("x0", "x1", "y0", "y1"))
vAP, vRadio, hFMS = FRAME["v_ap"], FRAME["v_radio"], FRAME["h_fms"]
gaps = {}
for t, tx, ty in FRAME["titles"]:
    w = text("LASER", t, tx, ty, SEMI, em(TITLE["size"]), TITLE["track"], align="left")
    gaps.setdefault(round(ty, 3), []).append((tx - TITLE["pad"], tx + w + TITLE["pad"]))


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


# The frame's pieces butt against each other and never overlap, so the marking is the same whether the vendor fills
# the contours even-odd or non-zero: the straight lines stop at the corner arcs' ends, each corner is one ring
# quarter, and a line that meets another one ends at that line's edge.
r, lw = S.KEY_FRAME["r"], S.KEY_FRAME["line"]                # corner radius, line width (bar's default)
hline(x0 + r, x1 - r, y0)
hline(x0 + r, x1 - r, y1)
layers["LASER"].append(bar(x0, y0 + r, x0, y1 - r))
layers["LASER"].append(bar(x1, y0 + r, x1, y1 - r))
for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
    arc = [math.radians(a0 + 7.5 * i) for i in range(13)]    # rounded corners: a quarter of a ring each
    layers["LASER"].append([(cx + (r + lw / 2) * math.cos(a), cy + (r + lw / 2) * math.sin(a)) for a in arc]
                           + [(cx + (r - lw / 2) * math.cos(a), cy + (r - lw / 2) * math.sin(a)) for a in arc[::-1]])
layers["LASER"].append(bar(vAP, y0 + lw / 2, vAP, y1 - lw / 2))
hline(vAP + lw / 2, x1 - lw / 2, hFMS)
layers["LASER"].append(bar(vRadio, y0 + lw / 2, vRadio, hFMS - lw / 2))

for name, ((kx, ky), main, shift) in KNOBS.items():
    tilt = math.radians(S.KNOB_LEGEND_TILT[name])
    mid = tilt if kx < B.W / 2 else math.pi - tilt
    KL = S.KNOB_ART
    r0 = S.RANGE_ART["legend_r"] if name == "RANGE" else S.OUTER_KNOB["d"] / 2 + KL["off"]
    arc_text("LASER", [(main, SEMI, em(KL["size"]))], kx, ky, r0, mid, KL["track"])
    if shift:
        arc_text("UV_AMBER", [(shift, SEMI, em(KL["size"]))], kx, ky, r0 + KL["shift_off"], mid, KL["track"])
rx, ry = B.RANGE
for i in range(4):                                           # pan arrows, outside the skirt (check_fit.py)
    a = i * math.pi / 2
    c, s = math.cos(a), math.sin(a)
    px, py = rx + S.RANGE_ART["arrow_r"] * c, ry + S.RANGE_ART["arrow_r"] * s
    layers["LASER"].append([(px + u * c - v * s, py + u * s + v * c) for u, v in S.RANGE_ART["arrow"]])

# ---------------- UV_AMBER: shift legends under the keys ----------------
SL = S.SHIFT_LEGEND
for rI, y in enumerate(B.ROWS):
    for cI, x in enumerate(B.COLS):
        t = SHIFT_LEGENDS[rI][cI]
        if t.endswith("⇆"):
            flip_legend("UV_AMBER", t, x, y + CAP[1] / 2 + SL["dy"], SEMI, em(SL["size"]), SL["track"])
        elif t:
            text("UV_AMBER", t, x, y + CAP[1] / 2 + SL["dy"], SEMI, em(SL["size"]), SL["track"])


# ---------------- writers ----------------
# A minimal DXF HEADER: $INSUNITS 4 = millimetres (CAM reads it as the drawing unit; R12 readers that do not know
# it skip it), $MEASUREMENT 1 = metric.
DXF_HEADER = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "9", "$MEASUREMENT", "70", "1", "0", "ENDSEC"]


def dxf_layers():
    """the layers as the DXF has them: in the plate's frame (stack.plate_xy), y up, origin at its bottom-left
    corner."""
    return {layer: [[S.plate_xy(x, y, B.H) for x, y in poly] for poly in polys] for layer, polys in layers.items()}


def write_dxf(path):
    """R12 DXF of dxf_layers(): each polygon one closed POLYLINE on its layer, coordinates to 0.1 um."""
    out = DXF_HEADER + ["0", "SECTION", "2", "ENTITIES"]
    for layer, polys in dxf_layers().items():
        for poly in polys:
            out += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
            for x, y in poly:
                out += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{y:.4f}"]
            out += ["0", "SEQEND", "8", layer]
    out += ["0", "ENDSEC", "0", "EOF"]
    Path(path).write_text("\n".join(out) + "\n")


def write_svg(path):
    colours = {"CUT": ("none", "#202020"), "LASER": ("#d8dadd", "none"), "UV_AMBER": (S.AMBER["hex"], "none")}
    w, h = B.W + 2 * OVH, B.H + 2 * OVH
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="{-OVH} {-OVH} {w} {h}">',
            f'<rect x="{-OVH}" y="{-OVH}" width="{w}" height="{h}" fill="#2d2f33"/>']
    for layer, polys in layers.items():
        fill, stroke = colours[layer]
        d = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in poly) + " Z" for poly in polys)
        body.append(f'<path d="{d}" fill="{fill}" fill-rule="evenodd" stroke="{stroke}" stroke-width="0.12"/>')
    body.append("</svg>")
    Path(path).write_text("\n".join(body))


if __name__ == "__main__":                              # check_fit.py imports the layers
    write_dxf("avionics-panel-rev1-plate.dxf")
    write_svg("avionics-panel-rev1-plate-preview.svg")
    print({k: len(v) for k, v in layers.items()}, "polygons")
