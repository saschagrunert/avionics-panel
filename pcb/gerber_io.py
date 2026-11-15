"""The board's Gerber and drill files, as this generator writes them, read back (check.py, render.py): each
Gerber file as its operations (gerber_ops), as a raster of PX mm (raster, draw_ops) or as exact geometry
(vector_copper, flashes, contours), and each drill file as its hits (drill_hits) or holes (read_drill). Board mm,
y down; the files are read from gerbers/ in the working directory (pcb/)."""
import math
import re

import board as B
import numpy as np
from PIL import Image, ImageDraw

PX = 0.05
WPX, HPX = int(B.W / PX) + 1, int(B.H / PX) + 1
ARC = 16                                    # buffer segments per quarter circle: 0.0012 x the radius off


def gerber_ops(fname):
    """This generator's Gerber files as a list of operations in board mm (y down): ("dark", bool),
    ("region", [(x, y), ...]), ("flash", aperture, (x, y)) and ("line", aperture, (x0, y0), (x1, y1)), an
    aperture being (kind C / R / O, size x, size y)."""
    aps, cur, pos, region, ops = {}, None, (0.0, 0.0), None, []
    with open("gerbers/" + fname) as f:
        txt = f.read()
    for tok in re.findall(r"%[^%]*%|[^*%\n]+\*", txt):
        tok = tok.strip()
        m = re.match(r"%ADD(\d+)([COR]),([\d.]+)(?:X([\d.]+))?\*%", tok)
        if m:
            aps[int(m.group(1))] = (m.group(2), float(m.group(3)), float(m.group(4) or 0))
            continue
        if tok in ("%LPD*%", "%LPC*%"):
            ops.append(("dark", tok == "%LPD*%")); continue
        if tok == "G36*":
            region = []; continue
        if tok == "G37*":
            if len(region) > 2:
                ops.append(("region", region))
            region = None; continue
        m = re.match(r"D(\d+)\*$", tok)
        if m and int(m.group(1)) >= 10:
            cur = aps[int(m.group(1))]; continue
        m = re.match(r"X(-?\d+)Y(-?\d+)D0([123])\*", tok)
        if not m:
            continue
        p, op = (int(m.group(1)) / 1e6, B.H - int(m.group(2)) / 1e6), m.group(3)
        if region is not None:
            if op == "2":
                if len(region) > 2:
                    ops.append(("region", region))
                region = [p]
            else:
                region.append(p)
        elif op == "3":
            ops.append(("flash", cur, p))
        elif op == "1":
            ops.append(("line", cur, pos, p))
        pos = p
    return ops


def raster(fname):
    return draw_ops(gerber_ops(fname))


def pad_ops(pads):
    """Pads as flash operations of gerber_ops, for draw_ops."""
    return [("flash", ({"rect": "R", "circle": "C"}.get(p.shape, "O"), p.w, p.h), (p.x, p.y)) for p in pads]


def op_item(op):
    """A flash or line operation of gerber_ops as a geometry item (geom.py): a rectangle aperture flashed is
    ("rect", x0, y0, x1, y1, 0.0); a circle, an obround (a capsule along its longer side) and a drawn line are
    ("cap", x1, y1, x2, y2, r)."""
    k, a, b = op[1]
    if op[0] == "line":
        return ("cap", *op[2], *op[3], a / 2)
    x, y = op[2]
    if k == "R":
        return ("rect", x - a / 2, y - b / 2, x + a / 2, y + b / 2, 0.0)
    if k == "C" or a == b:
        return ("cap", x, y, x, y, a / 2)
    d = abs(a - b) / 2
    return ("cap", x - d, y, x + d, y, b / 2) if a > b else ("cap", x, y - d, x, y + d, a / 2)


def draw_ops(ops):
    img = Image.new("L", (WPX, HPX), 0)
    dr = ImageDraw.Draw(img)
    col = 255

    for op in ops:
        if op[0] == "dark":
            col = 255 if op[1] else 0
        elif op[0] == "region":
            dr.polygon([(x / PX, y / PX) for x, y in op[1]], fill=col)
        else:
            kind, *g = op_item(op)
            g = [v / PX for v in g]
            if kind == "rect":
                dr.rectangle(g[:4], fill=col)
                continue
            p0, p1, r = tuple(g[:2]), tuple(g[2:4]), g[4]
            if p0 != p1:
                dr.line([p0, p1], fill=col, width=max(1, int(round(2 * r))))
            for q in (p0, p1):
                dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=col)
    return np.array(img) > 127


def ij(x, y):
    return int(round(y / PX)), int(round(x / PX))


def flashes(fname):
    """The flashed apertures of a Gerber file that holds nothing else (paste, mask), as geometry items:
    ("rect", x0, y0, x1, y1, 0) or ("cap", x1, y1, x2, y2, r) in board coordinates."""
    out = []
    for op in gerber_ops(fname):
        if op[0] == "dark":
            if not op[1]:                   # a plain raise, as below: asserts vanish under -O
                raise ValueError(f"{fname}: clear polarity not expected")
            continue
        if op[0] != "flash":
            raise ValueError(f"{fname}: only flashes expected")
        out.append(op_item(op))
    return out


def contours(fname):
    """The closed contours of an outline Gerber, each as its list of line segments ((x0, y0), (x1, y1))."""
    out = []
    for op in gerber_ops(fname):
        if op[0] != "line":
            continue
        if out and math.dist(out[-1][-1][1], op[2]) < 1e-6:
            out[-1].append((op[2], op[3]))
        else:
            out.append([(op[2], op[3])])
    return out


def vector_copper(fname):
    """A Gerber file (a copper layer, a legend) as one shapely geometry, board mm (y down), every aperture and
    region exact. Needs shapely, imported here: render.py reads the rasters without it."""
    from shapely import make_valid
    from shapely.geometry import LineString, Point, Polygon
    from shapely.geometry import box as shapely_box
    from shapely.ops import unary_union

    out, dark, run = Polygon(), True, []

    def flush():
        nonlocal out
        if run:
            u = unary_union(run)
            out = out.union(u) if dark else out.difference(u)
            run.clear()
    for op in gerber_ops(fname):
        if op[0] == "dark":
            if op[1] != dark:
                flush()
                dark = op[1]
        elif op[0] == "region":
            run.append(make_valid(Polygon(op[1])))
        else:
            kind, *g = op_item(op)
            if kind == "rect":
                run.append(shapely_box(*g[:4]))
            else:
                spine = Point(g[:2]) if g[:2] == g[2:4] else LineString([g[:2], g[2:4]])
                run.append(spine.buffer(g[4], quad_segs=ARC))
    flush()
    return out


def drill_hits(fname):
    """The hits of a drill file as (x0, y0, x1, y1, tool diameter) in the file's mm (y up): a round hole with
    both ends in one place, a G85 slot from one end to the other."""
    tools, hits, t = {}, [], None
    with open("gerbers/" + fname) as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        m = re.match(r"T(\d+)C([\d.]+)", line)
        if m:
            tools[m.group(1)] = float(m.group(2)); continue
        m = re.match(r"T(\d+)$", line)
        if m:
            t = tools[m.group(1)]; continue
        m = re.match(r"X([\d.]+)Y([\d.]+)(?:G85X([\d.]+)Y([\d.]+))?", line)
        if m:
            x0, y0 = float(m.group(1)), float(m.group(2))
            x1, y1 = (float(m.group(3)), float(m.group(4))) if m.group(3) else (x0, y0)
            hits.append((x0, y0, x1, y1, t))
    return hits


def read_drill(fname):
    """The holes of a drill file as (x, y, diameter) in board mm (y down); a slot as circles along it."""
    holes = []
    for x0, y0, x1, y1, t in drill_hits(fname):
        n = max(1, round(math.hypot(x1 - x0, y1 - y0) / 0.1))
        holes += [(x0 + (x1 - x0) * i / n, B.H - (y0 + (y1 - y0) * i / n), t) for i in range(n + 1)]
    return holes
