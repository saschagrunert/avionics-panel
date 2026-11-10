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
from geom import pad_geom, pt_seg, rounded_rect  # noqa: E402


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


def T(layer, s, x, y, size=2.0, align="center", angle=0.0):
    silk[layer].append(("text", text_polys(s, x, y, size, mirror=(layer == "B"), align=align, angle=angle)))


# --- front silkscreen (hidden under the front plate: assembly aid only) ---
for r, y in enumerate(B.ROWS):
    for c, x in enumerate(B.COLS):
        T("F", B.KEY_LABELS[r][c], x, y + 4.6, 1.0)
for ref, (x, y) in (("ALT/HDG", B.ALTHDG), ("FREQ", B.FREQ), ("FMS", B.FMS), ("RANGE", B.RANGE)):
    T("F", ref, x, y + 2.6, 1.2)
for name, ((lx, ly), _gp, _colour) in B.LEDS.items():
    T("F", name, lx, ly + 1.9, 0.8)
T("F", "AVIONICS PANEL rev 1", (B.COLS[2] + B.COLS[3]) / 2, 2.6, 1.3)
# --- back silkscreen: all SMD parts live here ---
for _name, x, y in B.DIODES:
    silk["B"].append(("line", [(x + 2.55, y - 0.75), (x + 2.55, y + 0.75)], 0.25))   # cathode bar
mx, my = B.MCU
silk["B"].append(("line", [(mx - 3.9, my + 4.6), (mx - 4.6, my + 4.6), (mx - 4.6, my + 3.9)], 0.15))   # pin 1 corner
# pin 1 dots (0.4 mm) beside pin 1 of the flash (bottom-right), the regulator (north-east) and the crystal
# (bottom-right corner), at least 0.15 mm from any mask opening; offsets from the pin 1 pad's centre
PIN1_DOT = {"U2": (0.75, 0.6), "U3": (0.85, 0.0), "Y1": (1.05, 0.95)}
for ref, (dx, dy) in PIN1_DOT.items():
    p = next(p for p in pads if p.name == f"{ref}.1")
    silk["B"].append(("dot", p.x + dx, p.y + dy, 0.4))
for ref, x, y in (("U1", mx + 5.0, my + 5.0), ("U2", 126.6 - 6.2 + B.SHIFT_X, 47.6), ("J1", B.USB_X, 12.9),
                  ("U3", B.LDO[0] + 2.4, B.LDO[1] + 2.4), ("Y1", B.XTAL[0], 18.0)):
    T("B", ref, x, y, 0.9)
T("B", "Avionics Panel rev 1 - RP2040 - USB-C", (B.COLS[2] + B.COLS[3]) / 2, 2.6, 1.4)
T("B", "BOOT: bridge", B.BOOT[0], B.BOOT[1] + 2.3, 0.9)
T("B", "while plugging in", B.BOOT[0], B.BOOT[1] + 3.5, 0.9)

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
    assert not lost, f"{layer}: thermals left with fewer than two spokes: {sorted(lost)}"
    if dropped:
        print(f"{layer}: spokes left out (an unplated hole or another net's hole in the way): {sorted(dropped)}")
    g.save()


def mask(layer, fname, func):
    g = Gerber(fname, func)
    for p in pads:
        if layer in p.mask:          # breakout points of the fan-out and the 1V1 vias on the bottom stay under the mask
            pad_flash(g, p, 0.05)
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
