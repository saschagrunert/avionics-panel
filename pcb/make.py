"""Build the Gerbers and drill files from board.py + routed.json."""
import json
import math
import os
import shutil
import zipfile

import board as B
import numpy as np
from geom import SILK_EDGE, SILK_VCUT, bbox, boxes_near, item_dist, pad_geom, pt_seg, rounded_rect, stroke_width
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from shapely import make_valid
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

OUT = "gerbers"
shutil.rmtree(OUT, ignore_errors=True)       # the zip takes every file here: no leftovers from older runs
os.makedirs(OUT)
FONT = FontProperties(family="DejaVu Sans", weight="bold")

with open("routed.json") as f:
    d = json.load(f)
pads = B.build()
segments = [tuple(s) for s in d["segments"]]          # x1,y1,x2,y2,layer,net,width
vias = [tuple(v) for v in d["vias"]]                  # x,y,net,diameter,drill (fixed vias merged by run_route.py)

# ---------------- text -> polygons ----------------
def text_polys(s, size, mirror=False):
    """The text's outlines centred on the origin as (depth, polygon): an odd depth is a counter inside a letter."""
    tp = TextPath((0, 0), s, size=size, prop=FONT)
    ext = tp.get_extents()
    polys = [np.array(p) for p in tp.to_polygons(closed_only=True)]
    ox, oy = (ext.x0 + ext.x1) / 2, (ext.y0 + ext.y1) / 2
    paths = [Path(p) for p in polys]
    out = []
    for i, p in enumerate(polys):
        depth = sum(1 for j, q in enumerate(paths) if j != i and q.contains_point(p[0]))
        q = p.copy()
        q[:, 0] -= ox
        q[:, 1] -= oy
        if mirror:
            q[:, 0] = -q[:, 0]
        out.append((depth, np.stack([q[:, 0], -q[:, 1]], axis=1)))    # the text path is y up, the board y down
    out.sort(key=lambda t: t[0])
    return out


silk = {"F": [], "B": []}     # list of ("text", polys) or ("line", pts, width) or ("dot", x, y, diameter)
# JLCPCB's legend minimum: characters 1.0 mm high, lines 0.153 mm (6 mil) wide. Measured on the font: a capital
# letter (DejaVu Sans Bold caps are 0.73 of the size), a lowercase letter (the x-height, 0.55 of the size), and on
# each text's own outlines its thinnest stroke or neck (geom.stroke_width). Each text is SILK (1.4) or the smallest
# size in 0.05 steps above it at which it passes.
SILK_MIN_H, SILK_MIN_LINE, SILK = 1.0, 0.153, 1.4
CAP_H = TextPath((0, 0), "H", size=1.0, prop=FONT).get_extents().height
X_H = TextPath((0, 0), "x", size=1.0, prop=FONT).get_extents().height


def text_shape(polys):
    """The outlines of text_polys() as one shapely shape: the letters less their counters."""
    out = Polygon()
    for depth, p in polys:
        g = make_valid(Polygon(p))
        out = out.difference(g) if depth % 2 else out.union(g)
    return out


def legend_size(s):
    """The size of the legend text s: SILK, or as much larger as its height and its thinnest stroke need, in 0.05 mm
    steps. The stroke is measured at size 1, to 0.0002 below its width, and grows with the size."""
    need = [SILK, SILK_MIN_H / CAP_H, SILK_MIN_LINE / stroke_width(text_shape(text_polys(s, 1.0)), 0.3, 2e-4)]
    need += [SILK_MIN_H / X_H] if any(c.islower() for c in s) else []
    return math.ceil(max(need) * 20 - 1e-9) / 20
# JLCPCB clips the legend off pads and holes (check.py: SILK_CLEAR, 0.15 mm on the Gerbers). Each text keeps
# LEGEND_GAP between its bounding box and the mask openings on its side, every hole and the legend placed before
# it, geom.SILK_EDGE inside the board outline and geom.SILK_VCUT inside its V-cut edge; where its spot is taken
# (a via the router put there), it moves to the nearest free one, at most 3 mm sideways and 1 mm up or down. A
# line (a diode's cathode bar) is left out for HOLE_GAP round a via instead. The checks are plain raises:
# asserts vanish under -O.
LEGEND_GAP, HOLE_GAP = 0.25, 0.2
NUDGE = sorted(((0.25 * i, 0.25 * j) for i in range(-12, 13) for j in range(-4, 5)),
               key=lambda d: (math.hypot(d[0], 2 * d[1]), d))


# Every mask opening is its pad grown by the pad's `grow` per side: board.MASK_GROW, or what a fiducial's opening
# takes.
def grown(g, d):
    return g[:5] + (g[5] + d,) if g[0] == "cap" else ("rect", g[1] - d, g[2] - d, g[3] + d, g[4] + d, 0.0)


HOLES = ([("cap", x, y, x, y, dr / 2) for (x, y, _n, _d, dr) in vias]
         + [("cap", x, y, x, y, d / 2) for (x, y, d) in B.NPTH]
         + [("cap", x, y, x, y, B.MOUNT_HOLE / 2) for (x, y) in B.MOUNTS]
         + [("rect", x - w / 2, y - h / 2, x + w / 2, y + h / 2, 0.0) for (x, y, w, h, _r) in B.CUTOUTS])
HOLE_BOXES = [bbox(h) for h in HOLES]
CLEAR = {ly: [grown(pad_geom(p), p.grow) for p in pads if ly in p.mask] + HOLES for ly in "FB"}


OUTLINE = rounded_rect(0, 0, B.W, B.H, B.CORNER_R)    # the Edge_Cuts polygon (outline()): its corner chords count
EDGES = [(a, b, math.dist(a, b)) for a, b in zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1], strict=True) if a != b]


def edge_dist(x, y):
    """Distance of (x, y) inside the board outline to it; negative outside. The outline is convex and runs
    clockwise on the board (y down): the nearest of its edge lines, measured to the inside."""
    return min(((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])) / n for a, b, n in EDGES)


def T(layer, s, x, y):
    polys = text_polys(s, legend_size(s), mirror=(layer == "B"))
    pts = np.concatenate([p for _d, p in polys])
    (x0, y0), (x1, y1) = pts.min(axis=0), pts.max(axis=0)
    for dx, dy in NUDGE:
        box = ("rect", x + dx + x0, y + dy + y0, x + dx + x1, y + dy + y1, 0.0)
        # the outline is convex: a box with its corners SILK_EDGE inside it is inside it by SILK_EDGE
        if min(edge_dist(bx, by) for bx in box[1:4:2] for by in box[2:5:2]) < SILK_EDGE or B.H - box[4] < SILK_VCUT:
            continue
        if all(item_dist(box, g) >= LEGEND_GAP for g in CLEAR[layer] if boxes_near(bbox(g), box[1:5], LEGEND_GAP)):
            CLEAR[layer].append(box)
            silk[layer].append(("text", [(d, p + (x + dx, y + dy)) for d, p in polys]))
            return
    raise AssertionError(f"no room for the legend {s!r} near ({x}, {y})")


# --- front silkscreen (hidden under the front plate: assembly aid only) ---
# Key legends under each key. The SHIFT light's cutout sits where the SHIFT key's legend would go, and its own
# name beside it names the key as well.
KEY_LABEL_DX = {"SHIFT": None}
for r, y in enumerate(B.ROWS):
    for c, x in enumerate(B.COLS):
        dx = KEY_LABEL_DX.get(B.KEY_LABELS[r][c], 0.0)
        if dx is not None:
            T("F", B.KEY_LABELS[r][c], x + dx, y + 4.6)
for ref, (x, y) in (("ALT/HDG", B.ALTHDG), ("FREQ", B.FREQ), ("FMS", B.FMS), ("RANGE", B.RANGE)):
    T("F", ref, x, y + 2.6)
# The lights: the name beside each cutout (the LED is on the bottom, its light pipe stands on the top over the
# cutout)
for name, ((lx, ly), _gp, _colour) in B.LEDS.items():
    T("F", name, lx + 4.0, ly)
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


MASK_B = [grown(pad_geom(p), p.grow) for p in pads if "B" in p.mask]
for _name, x, y in B.DIODES:
    bx = x + BAR_X
    if not bar_clear(bx, y, HOLES, HOLE_GAP):
        bx = next((bx + d for d in BAR_SHIFT
                   if bar_clear(bx + d, y, HOLES, HOLE_GAP) and bar_clear(bx + d, y, MASK_B, BAR_GAP)), bx)
    line("B", [(bx, y - 0.75), (bx, y + 0.75)], BAR_W)   # cathode bar
# the LEDs' cathode bars on the cathode pad's outer side (away from the anode), between it and its GND via
for name in B.LEDS:
    k, a = (next(p for p in pads if p.name == f"LED_{name}.{pin}") for pin in "KA")
    bx = k.x + math.copysign(k.w / 2 + k.grow + BAR_GAP + BAR_W / 2, k.x - a.x)
    line("B", [(bx, k.y - 0.75), (bx, k.y + 0.75)], BAR_W)
mx, my = B.MCU
# pin 1 corner, close to the chip: C_IO1 (pin 1's capacitor) sits further out
line("B", [(mx - 3.2, my + 3.95), (mx - 3.9, my + 3.95), (mx - 3.9, my + 3.25)], 0.16)
# pin 1 dots (0.4 mm) beside pin 1 of the flash (bottom-right), the regulator (north-east), the crystal
# (bottom-right corner) and the ESD array (below its pin 1, the south-east one), at least 0.15 mm from any mask
# opening; offsets from the pin 1 pad's centre
PIN1_DOT = {"U2": (0.75, 0.6), "U3": (1.05, 0.0), "Y1": (1.05, 0.95), "U4": (0.0, 1.0)}
for ref, (dx, dy) in PIN1_DOT.items():
    p = next(p for p in pads if p.name == f"{ref}.1")
    silk["B"].append(("dot", p.x + dx, p.y + dy, 0.4))
    CLEAR["B"].append(("cap", p.x + dx, p.y + dy, p.x + dx, p.y + dy, 0.2))
# part names beside their bodies, each at the first of its spots with room (the router's vias decide which)
NAME_SPOTS = {"U1": [(mx + 4.5, my - 4.0)], "U2": [(mx - 3.6, 37.9)], "J1": [(B.USB_X - 5.3, 4.2)],
              "U3": [(B.LDO[0] - 0.75, B.LDO[1] + 2.0), (B.LDO[0] + 2.6, B.LDO[1]), (B.LDO[0], B.LDO[1] + 3.6)],
              "Y1": [(B.XTAL[0] - 2.6, 17.9)], "U4": [(B.ESD[0] - 2.6, B.ESD[1])]}
# (F1 has no spot clearly its own between R_IN, R_CC2, the crystal and C_X2: docs/building/bring-up.md describes it)
for ref, spots in NAME_SPOTS.items():
    for i, (x, y) in enumerate(spots):
        try:
            T("B", ref, x, y)
            break
        except AssertionError:
            if i == len(spots) - 1:
                raise
T("B", *B.TITLE)
# two lines between the BOOT pads and the board's V-cut edge, the second without descenders, so it keeps
# geom.SILK_VCUT from that edge
T("B", "BOOT: hold bridged,", B.BOOT[0], B.BOOT[1] + 2.2)
T("B", "then connect USB", B.BOOT[0], B.BOOT[1] + 4.35)

# ---------------- Gerber writer ----------------
def fmt(v):
    return str(int(round(v * 1e6)))


class Gerber:
    """One Gerber X2 file. Its attributes say what it is, so JLCPCB's import need not guess from the name: the
    layer (FileFunction), whether the image is the material (Positive) or where it is not (Negative: the solder
    mask's openings), and what wrote it."""
    def __init__(self, fname, func, polarity="Positive"):
        self.fname = fname
        self.body = []
        self.aps = {}
        self.head = ["G04 DIY avionics panel*", "%TF.GenerationSoftware,DIY avionics panel,pcb/make.py*%",
                     f"%TF.FileFunction,{func}*%", f"%TF.FilePolarity,{polarity}*%", "%FSLAX46Y46*%", "%MOMM*%"]
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

    def save(self):
        with open(os.path.join(OUT, self.fname), "w") as f:
            f.write("\n".join(self.head + ["%LPD*%", "G01*"] + self.body + ["M02*"]) + "\n")


def circle_pts(x, y, r, n=72):
    """A circle as a region's polygon."""
    return [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


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
PLANE_CUT = (0.5, 0.4)  # plane copper back from an LED cutout's routed edge: along the pads, across
THERMAL_GAP, THERMAL_RING, SPOKE = 0.30, 0.30, 0.40
# Plane copper narrower than PLANE_MIN_W, where two clearances nearly meet (a sliver of 0.03 mm between the RANGE
# control's ECOM thermal and its COM pin's clearance), and any piece of plane that only such necks held (a 0.5 mm2
# island of 3V3 between the exposed pad's four GND vias), is cleared, as a CAM step would: a sliver can lift off
# and carries nothing. check.py measures what is left (thin contacts).
PLANE_MIN_W = 0.2


def shape(kind, w, h, x, y):
    """A flashed aperture (C or O, the obround upright or across) as shapely geometry."""
    if kind == "C" or w == h:
        return Point(x, y).buffer(w / 2, quad_segs=16)
    d = abs(w - h) / 2
    spine = [(x - d, y), (x + d, y)] if w > h else [(x, y - d), (x, y + d)]
    return LineString(spine).buffer(min(w, h) / 2, quad_segs=16)


def plane(layer, net, fname, func):
    """Inner plane: solid copper, anti-pads around every hole of another net, thermals on THT pads of its own net,
    and nothing narrower than PLANE_MIN_W."""
    g = Gerber(fname, func)
    edge = rounded_rect(B.EDGE_CLEAR + 0.2, B.EDGE_CLEAR + 0.2, B.W - B.EDGE_CLEAR - 0.2, B.H - B.EDGE_CLEAR - 0.2,
                        B.CORNER_R - B.EDGE_CLEAR)
    g.region(edge)
    g.pol(False)
    clears = []                                 # the same clearances as shapely geometry

    def clear(kind, w, x, y, h=None):
        g.flash(g.ap(kind, w, h or w) if kind == "O" else g.ap(kind, w), x, y)
        clears.append(shape(kind, w, h or w, x, y))

    def clear_region(pts):
        g.region(pts)
        clears.append(Polygon(pts))
    thermals = []
    for p in pads:
        if not p.drill:
            continue
        if p.slot:
            sw, sh = p.slot
            if p.net == net:
                thermals.append(p)
                ring = 2 * (THERMAL_RING + THERMAL_GAP)
                clear("O", sw + ring, p.x, p.y, sh + ring)
            else:
                clear("O", sw + 2 * PLANE_CLEAR, p.x, p.y, sh + 2 * PLANE_CLEAR)
        else:
            if p.net == net:
                thermals.append(p)
                clear("C", p.drill + 2 * (THERMAL_RING + THERMAL_GAP), p.x, p.y)
            else:
                clear("C", p.drill + 2 * PLANE_CLEAR, p.x, p.y)
    for (x, y, vnet, _d, dr) in vias:
        if vnet != net:
            clear("C", dr + 2 * PLANE_CLEAR, x, y)
    for (x, y) in B.MOUNTS:
        clear_region(circle_pts(x, y, B.MOUNT_HOLE / 2 + 0.6))
    for (x, y, dd) in B.NPTH:
        clear_region(circle_pts(x, y, dd / 2 + 0.5))
    for (x, y, w, h, r) in B.CUTOUTS:            # the LED cutouts: plane copper PLANE_CUT back from the routed edge
        ex, ey = PLANE_CUT
        clear_region(rounded_rect(x - w / 2 - ex, y - h / 2 - ey, x + w / 2 + ex, y + h / 2 + ey, r + ex))
    # what the clearances leave, opened by PLANE_MIN_W / 2: the plane is its largest piece, everything else of the
    # copper (slivers, the corners next to them, islands) is cleared too
    copper = Polygon(edge).difference(unary_union(clears))
    opened = copper.buffer(-PLANE_MIN_W / 2, quad_segs=16).buffer(PLANE_MIN_W / 2, quad_segs=16)
    main = max(getattr(opened, "geoms", [opened]), key=lambda q: q.area)
    cut = copper.difference(main)
    cut = [q for q in getattr(cut, "geoms", [cut]) if q.geom_type == "Polygon" and q.area > 1e-4]
    own = [(x, y, dr) for (x, y, vnet, _d, dr) in vias if vnet == net]
    for q in cut:
        if q.interiors:                         # a plain raise: asserts vanish under -O
            raise ValueError(f"{layer}: a piece to clear with a hole at {q.representative_point()}")
        for x, y, dr in own:                    # a via of the plane's net in it would lose its plane
            if q.distance(Point(x, y)) < dr / 2:
                raise ValueError(f"{layer}: the {net} via at ({x:.2f}, {y:.2f}) is in plane copper that is cleared")
        # 5 um larger, so it overlaps the flashed clearances round it, which the polygons above only approximate
        g.region(list(q.buffer(0.005, quad_segs=4).exterior.coords)[:-1])
    if cut:
        print(f"{layer}: plane copper narrower than {PLANE_MIN_W} mm cleared at {len(cut)} places, "
              f"{sum(q.area for q in cut):.2f} mm2")
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
            # clearance: leave that one out, the other spokes carry the pad. So does one ending off the plane.
            if (all(pt_seg(hx, hy, p.x, p.y, ex, ey) > hd / 2 + SPOKE / 2 + 0.25 for hx, hy, hd in near)
                    and main.contains(Point(ex, ey))):
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
    g = Gerber(fname, func, "Negative")
    for p in pads:
        if layer in p.mask:          # breakout points of the fan-out and the 1V1 vias on the bottom stay under the mask
            pad_flash(g, p, p.grow)
    g.save()


EP_WINDOWS = [(sx * 0.95, sy * 0.95, 1.1) for sx in (-1, 1) for sy in (-1, 1)]


def paste(fname):
    g = Gerber(fname, "Paste,Bot")
    for p in pads:                   # SMD pads on the bottom, and the pin-in-paste holes of SMD parts
        if p.paste and ((p.layers == "B" and not p.drill) or p.pip):
            pad_flash(g, p)
        if p.name == "U1.EP":
            for (dx, dy, s) in EP_WINDOWS:
                g.flash(g.ap("R", s, s), p.x + dx, p.y + dy)
    g.save()


def silkscreen(layer, fname, func):
    g = Gerber(fname, func)
    # an aperture even where the legend is all regions (the top's text): a Gerber that defines none reads as
    # RS-274D to some viewers (gerbv)
    g.ap("C", SILK_MIN_LINE)
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
    for (x, y, w, h, r) in B.CUTOUTS:            # the LED cutouts, milled out of the board
        pts = rounded_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, r)
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
plane("In1", "GND", "avionics-In1_Cu.g2", "Copper,L2,Inr")
plane("In2", "3V3", "avionics-In2_Cu.g3", "Copper,L3,Inr")
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
