"""Build Gerbers, drill files, DRC and renders from board.py + routed.json."""
import json
import math
import os
import pickle
import shutil
import zipfile

import board as B
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.textpath import TextPath

OUT = "gerbers"
shutil.rmtree(OUT, ignore_errors=True)       # the zip takes every file here: no leftovers from older runs
os.makedirs(OUT)
FONT = FontProperties(family="DejaVu Sans", weight="bold")

with open("routed.json") as f:
    d = json.load(f)
pads = B.build()
segments = [tuple(s) for s in d["segments"]]          # x1,y1,x2,y2,layer,net,width
vias = [tuple(v) for v in d["vias"]]                  # x,y,net,diameter,drill (fixed vias merged by run_route.py)

# ---------------- geometry items for the DRC ----------------
from geom import bbox, boxes_near, item_dist, pad_geom, pt_seg, rounded_rect  # noqa: E402


def copper_items():
    """All copper on the outer layers: (layer, geom, net, kind)."""
    items = []
    for p in pads:
        net = p.net or ("NC:" + p.name)
        g = pad_geom(p)
        for ly in p.layers:
            items.append((ly, g, net, "pad:" + p.name))
    for (x1, y1, x2, y2, ly, net, w) in segments:
        items.append((ly, ("cap", x1, y1, x2, y2, w / 2), net, "trace"))
    for (x, y, net, dd, _dr) in vias:
        for ly in "FB":
            items.append((ly, ("cap", x, y, x, y, dd / 2), net, "via"))
    return items


ITEMS = copper_items()

# ---------------- text -> polygons ----------------
def text_polys(s, x, y, size, mirror=False, align="center", angle=0.0):
    tp = TextPath((0, 0), s, size=size, prop=FONT)
    ext = tp.get_extents()
    polys = [np.array(p) for p in tp.to_polygons(closed_only=True)]
    if align == "center":
        ox = (ext.x0 + ext.x1) / 2
    elif align == "right":
        ox = ext.x1
    else:
        ox = ext.x0
    oy = (ext.y0 + ext.y1) / 2
    paths = [Path(p) for p in polys]
    out = []
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for i, p in enumerate(polys):
        depth = sum(1 for j, q in enumerate(paths) if j != i and q.contains_point(p[0]))
        q = p.copy()
        q[:, 0] -= ox
        q[:, 1] -= oy
        if mirror:
            q[:, 0] = -q[:, 0]
        # text path is y-up; board is y-down
        qx, qy = q[:, 0], -q[:, 1]
        rx = qx * ca - qy * sa
        ry = qx * sa + qy * ca
        out.append((depth, np.stack([rx + x, ry + y], axis=1)))
    out.sort(key=lambda t: t[0])
    return out


silk = {"F": [], "B": []}     # list of ("text", polys) or ("line", pts, width) or ("dot", x, y, diameter)
# JLCPCB's legend minimum: characters 1.0 mm high, lines 0.153 mm (6 mil) wide. Measured on the font: a capital
# letter (DejaVu Sans Bold caps are 0.73 of the size) and the stem of an "I" (0.19 of the size), so the text is
# SILK (1.4) or larger. Lowercase text is SILK_LOWER: its x-height (0.55 of the size) 0.82 mm.
SILK_MIN_H, SILK_MIN_LINE, SILK, SILK_LOWER = 1.0, 0.153, 1.4, 1.5
CAP_H = TextPath((0, 0), "H", size=1.0, prop=FONT).get_extents().height
STEM = TextPath((0, 0), "I", size=1.0, prop=FONT).get_extents().width
# JLCPCB clips the legend off pads and holes (check.py: SILK_CLEAR, 0.15 mm on the Gerbers). Each text keeps
# LEGEND_GAP between its bounding box and the mask openings on its side, every hole and the legend placed before
# it, and SILK_EDGE inside the board outline (check.py: SILK_EDGE); where its spot is taken (a via the router put
# there), it moves to the nearest free one, at most 3 mm sideways and 1 mm up or down. A line (a diode's cathode
# bar) is left out for HOLE_GAP round a via instead. The checks are plain raises: asserts vanish under -O.
LEGEND_GAP, HOLE_GAP, SILK_EDGE = 0.25, 0.2, 0.3
NUDGE = sorted(((0.25 * i, 0.25 * j) for i in range(-12, 13) for j in range(-4, 5)),
               key=lambda d: (math.hypot(d[0], 2 * d[1]), d))


# Every mask opening is its pad grown by MASK_GROW per side. Black mask needs 0.13 mm dams (JLCPCB; check.py:
# MASK_DAM), and the closest pads (the RP2040's, the USB-C contacts, C_X2 and R_X) are 0.2 mm apart: 0.035
# leaves 0.13 between them. JLCPCB's LDI exposure takes openings down to the pad size (1:1) and aligns to
# +-0.02 mm on multilayer boards, so the mask stays off every pad (check.py: MASK_MIN_GROW).
MASK_GROW = 0.035


def grown(g, d):
    return g[:5] + (g[5] + d,) if g[0] == "cap" else ("rect", g[1] - d, g[2] - d, g[3] + d, g[4] + d, 0.0)


HOLES = ([("cap", x, y, x, y, dr / 2) for (x, y, _n, _d, dr) in vias]
         + [("cap", x, y, x, y, d / 2) for (x, y, d) in B.NPTH]
         + [("cap", x, y, x, y, B.MOUNT_HOLE / 2) for (x, y) in B.MOUNTS])
HOLE_BOXES = [bbox(h) for h in HOLES]
CLEAR = {ly: [grown(pad_geom(p), MASK_GROW) for p in pads if ly in p.mask] + HOLES for ly in "FB"}


OUTLINE = rounded_rect(0, 0, B.W, B.H, B.CORNER_R)    # the Edge_Cuts polygon (outline()): its corner chords count
EDGES = [(a, b, math.dist(a, b)) for a, b in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1], strict=True) if a != b]


def edge_dist(x, y):
    """Distance of (x, y) inside the board outline to it; negative outside. The outline is convex and runs
    clockwise on the board (y down): the nearest of its edge lines, measured to the inside."""
    return min(((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])) / n for a, b, n in EDGES)


def T(layer, s, x, y, size=SILK):
    if size * CAP_H < SILK_MIN_H - 1e-6 or size * STEM < SILK_MIN_LINE:     # a plain raise: asserts vanish under -O
        raise ValueError(f"silkscreen text {s!r} too small")
    polys = text_polys(s, 0.0, 0.0, size, mirror=(layer == "B"))
    pts = np.concatenate([p for _d, p in polys])
    (x0, y0), (x1, y1) = pts.min(axis=0), pts.max(axis=0)
    for dx, dy in NUDGE:
        box = ("rect", x + dx + x0, y + dy + y0, x + dx + x1, y + dy + y1, 0.0)
        # the outline is convex: a box with its corners SILK_EDGE inside it is inside it by SILK_EDGE
        if min(edge_dist(bx, by) for bx in box[1:4:2] for by in box[2:5:2]) < SILK_EDGE:
            continue
        if all(item_dist(box, g) >= LEGEND_GAP for g in CLEAR[layer] if boxes_near(bbox(g), box[1:5], LEGEND_GAP)):
            CLEAR[layer].append(box)
            silk[layer].append(("text", [(d, p + (x + dx, y + dy)) for d, p in polys]))
            return
    raise AssertionError(f"no room for the legend {s!r} near ({x}, {y})")


# --- front silkscreen (hidden under the front plate: assembly aid only) ---
# Key legends under each key. The SHIFT light sits where the SHIFT key's legend would go, and its own name
# below it names the key as well; HOME's legend moves left, clear of the UNIT light's polarity mark.
KEY_LABEL_DX = {"SHIFT": None, "HOME": -1.5}
for r, y in enumerate(B.ROWS):
    for c, x in enumerate(B.COLS):
        dx = KEY_LABEL_DX.get(B.KEY_LABELS[r][c], 0.0)
        if dx is not None:
            T("F", B.KEY_LABELS[r][c], x + dx, y + 4.6)
for ref, (x, y) in (("ALT/HDG", B.ALTHDG), ("FREQ", B.FREQ), ("FMS", B.FMS), ("RANGE", B.RANGE)):
    T("F", ref, x, y + 2.6)
# The lights: name below, "K" at the cathode (the square pad), the polarity for whoever fits them (by hand in
# the economic variant, JLCPCB in the full one). SHIFT's "K" west of the pad; UNIT's north-west, as HOME's
# legend takes the west.
LED_K = {"SHIFT": (-2.85, 0.0), "UNIT": (-2.55, -1.6)}
for name, ((lx, ly), _gp, _colour) in B.LEDS.items():
    T("F", name, lx, ly + 1.9)
    T("F", "K", lx + LED_K[name][0], ly + LED_K[name][1])
T("F", "AVIONICS PANEL rev 1", (B.COLS[2] + B.COLS[3]) / 2, 2.6)


def line(layer, pts, w, step=0.05):
    """A legend line, left out where it would cross a via the router put there (and HOLE_GAP round it)."""
    if w < SILK_MIN_LINE:
        raise ValueError(f"silkscreen line {w} mm too thin")
    for a, b in zip(pts, pts[1:], strict=False):
        n = max(1, round(math.dist(a, b) / step))
        sb = bbox(("cap", *a, *b, w / 2))                  # only the holes that can come near this piece
        near = [h for h, hb in zip(HOLES, HOLE_BOXES, strict=True) if boxes_near(hb, sb, HOLE_GAP)]
        ok = [all(item_dist(("cap", *q, *q, w / 2), h) >= HOLE_GAP - 1e-6 for h in near)
              for q in ((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1))]
        i = 0
        while i <= n:
            if not ok[i]:
                i += 1; continue
            j = i
            while j < n and ok[j + 1]:
                j += 1
            p, q = [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in (i, j)]
            if math.dist(p, q) >= 0.3:
                silk[layer].append(("line", [p, q], w))
                CLEAR[layer].append(("cap", *p, *q, w / 2))
            i = j + 1


# --- back silkscreen: all SMD parts live here ---
# Cathode bars 0.9 mm east of the cathode pad's centre, 0.24 mm from its mask opening. Where a via would cut
# one short, the bar moves sideways by the least that keeps it whole, if that is at most 0.3 mm away from the pad
# (0.025 towards it) and leaves it BAR_GAP from every mask opening (check.py: SILK_CLEAR) and HOLE_GAP from every
# hole.
BAR_X, BAR_W, BAR_GAP = B.DIO_DX + 0.9, 0.25, 0.2
BAR_SHIFT = sorted((-0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3), key=abs)


def bar_clear(x, y, items, gap):
    g = ("cap", x, y - 0.75, x, y + 0.75, BAR_W / 2)
    return all(item_dist(g, h) >= gap - 1e-6 for h in items if boxes_near(bbox(h), bbox(g), gap))


MASK_B = [grown(pad_geom(p), MASK_GROW) for p in pads if "B" in p.mask]
for _name, x, y in B.DIODES:
    bx = x + BAR_X
    if not bar_clear(bx, y, HOLES, HOLE_GAP):
        bx = next((bx + d for d in BAR_SHIFT
                   if bar_clear(bx + d, y, HOLES, HOLE_GAP) and bar_clear(bx + d, y, MASK_B, BAR_GAP)), bx)
    line("B", [(bx, y - 0.75), (bx, y + 0.75)], BAR_W)   # cathode bar
mx, my = B.MCU
line("B", [(mx - 3.9, my + 4.6), (mx - 4.6, my + 4.6), (mx - 4.6, my + 3.9)], 0.16)   # pin 1 corner
# pin 1 dots (0.4 mm) beside pin 1 of the flash (bottom-right), the regulator (north-east) and the crystal
# (bottom-right corner), at least 0.15 mm from any mask opening; offsets from the pin 1 pad's centre
PIN1_DOT = {"U2": (0.75, 0.6), "U3": (1.05, 0.0), "Y1": (1.05, 0.95)}
for ref, (dx, dy) in PIN1_DOT.items():
    p = next(p for p in pads if p.name == f"{ref}.1")
    silk["B"].append(("dot", p.x + dx, p.y + dy, 0.4))
    CLEAR["B"].append(("cap", p.x + dx, p.y + dy, p.x + dx, p.y + dy, 0.2))
# part names beside their bodies
for ref, x, y in (("U1", mx + 4.5, my - 4.0), ("U2", mx - 3.6, 37.9), ("J1", B.USB_X - 5.3, 4.2),
                  ("U3", B.LDO[0] - 0.75, B.LDO[1] + 2.0), ("Y1", B.XTAL[0] - 2.6, 17.9)):
    T("B", ref, x, y)
T("B", "Avionics Panel rev 1 - RP2040 - USB-C", (B.COLS[2] + B.COLS[3]) / 2, 2.6, SILK_LOWER)
T("B", "BOOT: bridge", B.BOOT[0], B.BOOT[1] + 2.4, SILK_LOWER)
T("B", "while plugging in", B.BOOT[0], B.BOOT[1] + 4.35, SILK_LOWER)

# ---------------- Gerber writer ----------------
def fmt(v):
    return str(int(round(v * 1e6)))


class Gerber:
    def __init__(self, fname, func):
        self.fname = fname
        self.body = []
        self.aps = {}
        self.head = ["G04 DIY avionics panel*", f"%TF.FileFunction,{func}*%", "%FSLAX46Y46*%", "%MOMM*%"]
        self.cur = None

    def ap(self, kind, *p):
        key = (kind,) + tuple(round(v, 4) for v in p)
        if key not in self.aps:
            n = 10 + len(self.aps)
            if kind == "C":
                self.head.append(f"%ADD{n}C,{p[0]:.4f}*%")
            elif kind == "R":
                self.head.append(f"%ADD{n}R,{p[0]:.4f}X{p[1]:.4f}*%")
            else:
                self.head.append(f"%ADD{n}O,{p[0]:.4f}X{p[1]:.4f}*%")
            self.aps[key] = n
        return self.aps[key]

    def use(self, n):
        if self.cur != n:
            self.body.append(f"D{n}*")
            self.cur = n

    def pol(self, dark):
        self.body.append("%LPD*%" if dark else "%LPC*%")

    def X(self, x, y):
        return f"X{fmt(x)}Y{fmt(B.H - y)}"

    def flash(self, n, x, y):
        self.use(n)
        self.body.append(self.X(x, y) + "D03*")

    def line(self, n, pts):
        self.use(n)
        self.body.append(self.X(*pts[0]) + "D02*")
        for p in pts[1:]:
            self.body.append(self.X(*p) + "D01*")

    def region(self, pts):
        self.body.append("G36*")
        self.body.append(self.X(*pts[0]) + "D02*")
        for p in pts[1:]:
            self.body.append(self.X(*p) + "D01*")
        self.body.append(self.X(*pts[0]) + "D01*")
        self.body.append("G37*")

    def capsule(self, x1, y1, x2, y2, r):
        n = self.ap("C", 2 * r)
        if (x1, y1) == (x2, y2):
            self.flash(n, x1, y1)
        else:
            self.line(n, [(x1, y1), (x2, y2)])

    def circle_region(self, x, y, r, n=72):
        self.region([(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n))
                     for i in range(n)])

    def save(self):
        with open(os.path.join(OUT, self.fname), "w") as f:
            f.write("\n".join(self.head + ["%LPD*%", "G01*"] + self.body + ["M02*"]) + "\n")


def pad_flash(g, p, grow=0.0):
    if p.shape == "rect":
        g.flash(g.ap("R", p.w + 2 * grow, p.h + 2 * grow), p.x, p.y)
    elif p.shape == "circle":
        g.flash(g.ap("C", p.w + 2 * grow), p.x, p.y)
    else:
        g.flash(g.ap("O", p.w + 2 * grow, p.h + 2 * grow), p.x, p.y)


def copper(layer, fname, func):
    g = Gerber(fname, func)
    for p in pads:
        if layer in p.layers:
            pad_flash(g, p)
    for (x1, y1, x2, y2, ly, _net, w) in segments:
        if ly == layer:
            g.capsule(x1, y1, x2, y2, w / 2)
    for (x, y, _net, dd, _dr) in vias:
        g.capsule(x, y, x, y, dd / 2)
    g.save()


PLANE_CLEAR = 0.35      # copper-free ring around a foreign hole on an inner plane (beyond the drill)
THERMAL_GAP, THERMAL_RING, SPOKE = 0.30, 0.30, 0.40


def plane(layer, net, fname, func):
    """Inner plane: solid copper, anti-pads around every hole of another net, thermals on THT pads of its own net."""
    g = Gerber(fname, func)
    g.region(rounded_rect(B.EDGE_CLEAR + 0.2, B.EDGE_CLEAR + 0.2, B.W - B.EDGE_CLEAR - 0.2, B.H - B.EDGE_CLEAR - 0.2,
                          B.CORNER_R - B.EDGE_CLEAR))
    g.pol(False)
    thermals = []
    for p in pads:
        if not p.drill:
            continue
        if p.slot:
            sw, sh = p.slot
            if p.net == net:
                thermals.append(p)
                ring = 2 * (THERMAL_RING + THERMAL_GAP)
                g.flash(g.ap("O", sw + ring, sh + ring), p.x, p.y)
            else:
                g.flash(g.ap("O", sw + 2 * PLANE_CLEAR, sh + 2 * PLANE_CLEAR), p.x, p.y)
        else:
            if p.net == net:
                thermals.append(p)
                g.flash(g.ap("C", p.drill + 2 * (THERMAL_RING + THERMAL_GAP)), p.x, p.y)
            else:
                g.flash(g.ap("C", p.drill + 2 * PLANE_CLEAR), p.x, p.y)
    for (x, y, vnet, _d, dr) in vias:
        if vnet != net:
            g.flash(g.ap("C", dr + 2 * PLANE_CLEAR), x, y)
    for (x, y) in B.MOUNTS:
        g.circle_region(x, y, B.MOUNT_HOLE / 2 + 0.6)
    for (x, y, dd) in B.NPTH:
        g.circle_region(x, y, dd / 2 + 0.5)
    g.pol(True)
    foreign = [(q.x, q.y, max(q.slot) if q.slot else q.drill) for q in pads if q.drill and q.net != net]
    foreign += [(x, y, dr) for (x, y, vnet, _d, dr) in vias if vnet != net]
    dropped = []
    for p in thermals:
        if p.slot:
            sw, sh = p.slot
            g.flash(g.ap("O", sw + 2 * THERMAL_RING, sh + 2 * THERMAL_RING), p.x, p.y)
            lx, ly = sw / 2 + THERMAL_RING + THERMAL_GAP + 0.1, sh / 2 + THERMAL_RING + THERMAL_GAP + 0.1
        else:
            g.flash(g.ap("C", p.drill + 2 * THERMAL_RING), p.x, p.y)
            lx = ly = p.drill / 2 + THERMAL_RING + THERMAL_GAP + 0.1
        n = g.ap("C", SPOKE)
        # unplated holes and the holes of other nets near the pad (slots as a circle round their length)
        near = [(hx, hy, hd) for hx, hy, hd in B.NPTH + foreign if abs(hx - p.x) < 4 and abs(hy - p.y) < 4]
        for ex, ey in ((p.x - lx, p.y), (p.x + lx, p.y), (p.x, p.y - ly), (p.x, p.y + ly)):
            # a spoke pointing at an unplated hole (the USB-C shell pegs next to the shell pads) or at a hole of
            # another net (the RANGE control's COM pin next to its GND pin) would run into its drill or its
            # clearance: leave that one out, the other spokes carry the pad
            if all(pt_seg(hx, hy, p.x, p.y, ex, ey) > hd / 2 + SPOKE / 2 + 0.25 for hx, hy, hd in near):
                g.line(n, [(p.x, p.y), (ex, ey)])
            else:
                dropped.append(p.name)
    lost = [n for n in set(dropped) if dropped.count(n) > 2]
    if lost:
        raise ValueError(f"{layer}: thermals left with fewer than two spokes: {sorted(lost)}")
    if dropped:
        print(f"{layer}: spokes left out (an unplated hole or another net's hole in the way): {sorted(dropped)}")
    g.save()


def mask(layer, fname, func):
    g = Gerber(fname, func)
    for p in pads:
        if layer in p.mask:          # breakout points of the fan-out and the 1V1 vias on the bottom stay under the mask
            pad_flash(g, p, MASK_GROW)
    g.save()


EP_WINDOWS = [(sx * 0.95, sy * 0.95, 1.1) for sx in (-1, 1) for sy in (-1, 1)]


def paste(fname):
    g = Gerber(fname, "Paste,Bot")
    for p in pads:                   # SMD pads on the bottom, and the pin-in-paste holes of SMD parts
        if p.paste and ((p.layers == "B" and not p.drill) or p.pip):
            if p.shape == "rect":
                g.flash(g.ap("R", p.w, p.h), p.x, p.y)
            else:
                pad_flash(g, p)
        if p.name == "U1.EP":
            for (dx, dy, s) in EP_WINDOWS:
                g.flash(g.ap("R", s, s), p.x + dx, p.y + dy)
    g.save()


def silkscreen(layer, fname, func):
    g = Gerber(fname, func)
    dark = True
    for it in silk[layer]:
        if it[0] == "text":
            for depth, poly in it[1]:
                want = depth % 2 == 0
                if want != dark:
                    g.pol(want)
                    dark = want
                g.region([tuple(p) for p in poly])
            if not dark:
                g.pol(True)
                dark = True
        elif it[0] == "line":
            g.line(g.ap("C", it[2]), it[1])
        elif it[0] == "dot":
            g.flash(g.ap("C", it[3]), it[1], it[2])
    g.save()


def outline(fname):
    g = Gerber(fname, "Profile,NP")
    n = g.ap("C", 0.1)
    pts = rounded_rect(0, 0, B.W, B.H, B.CORNER_R)
    g.line(n, pts + [pts[0]])
    g.save()


def drill(fname, holes, plated, slots=()):
    tools = sorted({dd for (_, _, dd) in holes} | {sw for (_, _, sw, _) in slots})
    lines = ["M48", f"; DIY avionics panel {'PTH' if plated else 'NPTH'}", "FMAT,2", "METRIC"]
    lines.append(f"; #@! TF.FileFunction,{'Plated' if plated else 'NonPlated'},1,4,{'PTH' if plated else 'NPTH'}")
    for i, t in enumerate(tools):
        lines.append(f"T{i+1}C{t:.3f}")
    lines += ["%", "G90", "G05"]
    for i, t in enumerate(tools):
        lines.append(f"T{i+1}")
        for (x, y, dd) in holes:
            if dd == t:
                lines.append(f"X{x:.3f}Y{B.H - y:.3f}")
        for (x, y, sw, sh) in slots:          # vertical plated slots, G85 = routed slot
            if sw == t:
                d = (sh - sw) / 2
                lines.append(f"X{x:.3f}Y{B.H - (y - d):.3f}G85X{x:.3f}Y{B.H - (y + d):.3f}")
    lines.append("M30")
    with open(os.path.join(OUT, fname), "w") as f:
        f.write("\n".join(lines) + "\n")


copper("F", "avionics-F_Cu.gtl", "Copper,L1,Top")
plane("In1", "GND", "avionics-In1_Cu.g2", "Copper,L2,Inr,Plane")
plane("In2", "3V3", "avionics-In2_Cu.g3", "Copper,L3,Inr,Plane")
copper("B", "avionics-B_Cu.gbl", "Copper,L4,Bot")
mask("F", "avionics-F_Mask.gts", "Soldermask,Top")
mask("B", "avionics-B_Mask.gbs", "Soldermask,Bot")
paste("avionics-B_Paste.gbp")
silkscreen("F", "avionics-F_Silkscreen.gto", "Legend,Top")
silkscreen("B", "avionics-B_Silkscreen.gbo", "Legend,Bot")
outline("avionics-Edge_Cuts.gko")
pth = [(p.x, p.y, p.drill) for p in pads if p.drill and not p.slot] + [(x, y, dr) for (x, y, _, _, dr) in vias]
slots = [(p.x, p.y, p.slot[0], p.slot[1]) for p in pads if p.slot]
drill("avionics-PTH.drl", pth, True, slots)
drill("avionics-NPTH.drl", [(x, y, B.MOUNT_HOLE) for (x, y) in B.MOUNTS] + list(B.NPTH), False)

zpath = "avionics-panel-rev1-gerbers.zip"
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(OUT)):          # fixed timestamps: a rebuild without changes gives the same zip
        zi = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
        with open(os.path.join(OUT, f), "rb") as src:
            z.writestr(zi, src.read())
print("gerbers written:", sorted(os.listdir(OUT)))

with open("design.json", "w") as f:
    json.dump({"items": ITEMS}, f)
with open("silk.pkl", "wb") as f:
    pickle.dump(silk, f)
