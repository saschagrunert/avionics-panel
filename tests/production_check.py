"""The files to order against each other, read with readers of their own and no module of the repository:
python3 production_check.py <folder>... prints one line per comparison and RESULT <folder> pass or fail, and exits 1
if any fails (tests/test_production.py runs it on production/ and on broken copies, in the gen shell for
OpenCascade).

- the NPTH mounting holes of the drill file (its largest tool) against the plate STEP's tapped bosses and the
  body STEP's screw holes;
- the keys of CPL-full.csv against the plate STEP's key holes and those of the plate DXF's CUT layer;
- the encoders (the middle of each pair of lug slots in the PTH drill file), RANGE (its CPL-full.csv row) and the
  LED cutouts of Edge_Cuts against the plate STEP's other through holes, and those against the DXF's round holes.

Frames: the board as the Gerbers have it (mm, y up, its outline from 0, 0); the plate STEP and the DXF from the
plate's bottom-left corner (its overhang `o` past the board on every side, found from the two outlines); the body
STEP with X the board's x and Y the board's y less its height (Y = -board y, y down)."""
import csv
import math
import re
import sys
import zipfile
from collections import defaultdict

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.GeomAbs import GeomAbs_Cylinder
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods

NAME = "avionics-panel-rev1"
TOL = 0.005                     # the drill file to 0.001 mm, the DXF to 0.0001, the STEP and the Gerbers finer


def gerber_lines(txt):
    """the line segments of an outline Gerber as this project writes it (mm, %FSLAX46Y46*%, G01 only)"""
    if "%FSLAX46Y46*%" not in txt or "%MOMM*%" not in txt:
        raise ValueError("Edge_Cuts: not in mm with 6 decimals")
    out, pos = [], None
    for tok in re.findall(r"[^*%\n]+\*", txt):
        m = re.fullmatch(r"X(-?\d+)Y(-?\d+)D0([12])\*", tok.strip())
        if m:
            p = (int(m.group(1)) / 1e6, int(m.group(2)) / 1e6)
            if m.group(3) == "1":
                out.append((pos, p))
            pos = p
        elif re.match(r"G0[23]|G75|X|Y|D0", tok.strip()):
            raise ValueError(f"Edge_Cuts: {tok.strip()} not read here")
    return out


def contours(segs):
    """closed contours of chained segments, each as its points"""
    out = []
    for a, b in segs:
        if out and math.dist(out[-1][-1], a) < 1e-6:
            out[-1].append(b)
        else:
            out.append([a, b])
    return out


def drill(txt):
    """{tool diameter: [(x0, y0, x1, y1)]} of a drill file as this project writes it (METRIC, decimal point)"""
    if "\nMETRIC\n" not in txt:
        raise ValueError("drill file not METRIC")
    tools, hits, t = {}, defaultdict(list), None
    for ln in txt.splitlines():
        if m := re.fullmatch(r"T(\d+)C([\d.]+)", ln):
            tools[m.group(1)] = float(m.group(2))
        elif m := re.fullmatch(r"T(\d+)", ln):
            t = tools[m.group(1)]
        elif m := re.fullmatch(r"X(-?\d+\.\d+)Y(-?\d+\.\d+)(?:G85X(-?\d+\.\d+)Y(-?\d+\.\d+))?", ln):
            x0, y0 = float(m.group(1)), float(m.group(2))
            hits[t].append((x0, y0, *((float(m.group(3)), float(m.group(4))) if m.group(3) else (x0, y0))))
    return hits


def step_cylinders(path):
    """the plate or body STEP: its extent (x0, y0, z0, x1, y1, z1) and its cylinders along z, {(x, y): [(r, z0,
    z1)]} by axis (rounded to 1e-4)"""
    r = STEPControl_Reader()
    if r.ReadFile(path) != IFSelect_RetDone:
        raise ValueError(f"{path}: not read")
    r.TransferRoots()
    shape = r.OneShape()
    box = Bnd_Box()
    box.SetGap(0.0)
    brepbndlib.Add(shape, box, False)
    out = defaultdict(list)
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        face = topods.Face(ex.Current())
        s = BRepAdaptor_Surface(face)
        if s.GetType() == GeomAbs_Cylinder:
            c = s.Cylinder()
            d, p = c.Axis().Direction(), c.Axis().Location()
            if abs(abs(d.Z()) - 1) < 1e-9:
                fb = Bnd_Box()
                fb.SetGap(0.0)
                brepbndlib.Add(face, fb, False)
                z = fb.Get()
                out[round(p.X(), 4), round(p.Y(), 4)].append((round(c.Radius(), 4), z[2], z[5]))
        ex.Next()
    return box.Get(), out


def dxf_polys(txt):
    """{layer: [points]} of an R12 DXF of closed POLYLINEs"""
    vals = [v.strip() for v in txt.splitlines()]
    out, cur, ent = defaultdict(list), None, None
    for code, v in zip(vals[0::2], vals[1::2], strict=True):
        if code == "0":
            ent = v
            if v in ("POLYLINE", "SEQEND"):
                cur = None
        elif code == "8" and ent == "POLYLINE":
            cur = out[v]
            cur.append([])
        elif ent == "VERTEX" and cur is not None and code in ("10", "20"):
            if code == "10":
                cur[-1].append([float(v), None])
            else:
                cur[-1][-1][1] = float(v)
    return out


def match(name, want, got, tol=TOL):
    """one for one: every point of want within tol of one of got, none left over. One line, True if they match."""
    got, worst, missing = list(got), 0.0, []
    for w in want:
        k = min(range(len(got)), key=lambda i: math.dist(got[i], w), default=None)
        if k is None or math.dist(got[k], w) > tol:
            missing.append(w)
        else:
            worst = max(worst, math.dist(got.pop(k), w))
    ok = not missing and not got
    print(f"{'OK  ' if ok else 'FAIL'} {name}: {len(want)} want, worst {worst:.4f} mm"
          + (f"; missing {[tuple(round(v, 3) for v in w) for w in missing]}" if missing else "")
          + (f"; extra {[tuple(round(v, 3) for v in g) for g in got]}" if got else ""))
    return ok


def main(folder):
    with zipfile.ZipFile(f"{folder}/{NAME}-gerbers.zip") as z:
        edge = contours(gerber_lines(z.read("avionics-Edge_Cuts.gko").decode()))
        pth, npth = drill(z.read("avionics-PTH.drl").decode()), drill(z.read("avionics-NPTH.drl").decode())
    with open(f"{folder}/{NAME}-CPL-full.csv", newline="") as f:
        cpl = {r["Designator"]: (float(r["Mid X"].removesuffix("mm")), float(r["Mid Y"].removesuffix("mm")),
                                 int(r["Rotation"])) for r in csv.DictReader(f)}
    with open(f"{folder}/{NAME}-plate.dxf") as f:
        dxf = dxf_polys(f.read())
    (px0, py0, pz0, px1, py1, pz1), plate = step_cylinders(f"{folder}/{NAME}-plate.step")
    _box, body = step_cylinders(f"{folder}/{NAME}-body.step")

    def extent(c):
        xs, ys = [p[0] for p in c], [p[1] for p in c]
        return min(xs), min(ys), max(xs), max(ys)
    edge.sort(key=lambda c: extent(c)[2] - extent(c)[0], reverse=True)       # the board outline, the widest, first
    bx0, by0, bx1, by1 = extent(edge[0])
    o = ((px1 - px0) - (bx1 - bx0)) / 2
    ok = [abs(bx0) + abs(by0) < 1e-6 and abs((py1 - py0) - (by1 - by0) - 2 * o) < TOL and abs(px0) + abs(py0) < TOL]
    print(f"{'OK  ' if ok[0] else 'FAIL'} frames: board {bx1 - bx0:g} x {by1 - by0:g} from {bx0:g}, {by0:g}; plate "
          f"{px1 - px0:.3f} x {py1 - py0:.3f} from {px0:.3f}, {py0:.3f}, {o:.3f} past the board on every side")
    H = by1 - by0

    # the mounting holes: the largest unplated tool
    mounts = [(x, y) for x, y, *_ in npth[max(npth)]]
    # the plate's bosses: cylinders below its back face (z 0), each with a smaller one up its axis, the tap drill
    bosses = [xy for xy, cs in plate.items() if any(z1 < 1e-6 for _r, _z0, z1 in cs)]
    tapped = [xy for xy in bosses if len({r for r, *_ in plate[xy]}) > 1]
    ok.append(match("NPTH mounting holes = the plate STEP's bosses", [(x + o, y + o) for x, y in mounts], bosses))
    ok.append(match("the plate STEP's bosses are tapped", bosses, tapped))
    # the body's screw holes: at each mount a hole; the smallest radius there is the screw hole's, and the body has
    # it at the mounts alone
    at = [min(body, key=lambda xy, x=x, y=y: math.dist(xy, (x, y - H))) for x, y in mounts]
    screw = min(r for xy in at for r, *_ in body[xy])
    holes = [xy for xy, cs in body.items() if any(abs(r - screw) < 1e-4 for r, *_ in cs)]
    ok.append(match(f"NPTH mounting holes = the body STEP's screw holes (r {screw:g})",
                    [(x, y - H) for x, y in mounts], holes))

    # the plate's through holes: cylinders up to its front face; the key holes are the ones of four corner arcs
    front = [(xy, r) for xy, cs in plate.items() for r, _z0, z1 in cs if abs(z1 - pz1) < 1e-6]
    by_r = defaultdict(list)
    for xy, r in front:
        by_r[r].append(xy)
    keys = [k for k, v in cpl.items() if re.fullmatch(r"K\d+", k)]
    corner_r = min(by_r, key=lambda r: abs(len(by_r[r]) - 4 * len(keys)))
    corners, key_holes = sorted(by_r[corner_r]), []
    while corners:          # each key hole from its bottom-left corner: the nearest corner above, to the right
        (x, y), rest = corners[0], corners[1:]
        top = min((q[1] for q in rest if abs(q[0] - x) < 1e-6 and q[1] > y), default=None)
        right = min((q[0] for q in rest if abs(q[1] - y) < 1e-6 and q[0] > x), default=None)
        group = [(x, y), (x, top), (right, y), (right, top)]
        if None in (top, right) or not all(q in corners for q in group):
            print(f"FAIL key hole corners: no rectangle from ({x:.3f}, {y:.3f})")
            return False
        corners = [q for q in corners if q not in group]
        key_holes.append(((x + right) / 2, (y + top) / 2))
    outline = max(dxf["CUT"], key=lambda p: extent(p)[2] - extent(p)[0])
    cut = [p for p in dxf["CUT"] if p is not outline]

    def is_round(p):
        cx, cy = (extent(p)[0] + extent(p)[2]) / 2, (extent(p)[1] + extent(p)[3]) / 2
        r = [math.dist(q, (cx, cy)) for q in p]
        return max(r) - min(r) < 1e-3, (cx, cy, max(r))
    dxf_keys = [is_round(p)[1][:2] for p in cut if not is_round(p)[0]]
    dxf_round = [is_round(p)[1] for p in cut if is_round(p)[0]]
    ok.append(match(f"CPL keys = the plate STEP's key holes (corners R{corner_r:g})",
                    [(cpl[k][0] + o, cpl[k][1] + o) for k in keys], key_holes))
    ok.append(match("CPL keys = the DXF CUT layer's key holes", [(cpl[k][0] + o, cpl[k][1] + o) for k in keys],
                    dxf_keys))
    ok.append(match("the DXF CUT outline = the plate STEP's extent", [extent(outline)], [(px0, py0, px1, py1)]))

    # the round through holes: the encoders (the middle of their lug slots), RANGE, the lights (LED cutouts)
    slots = sorted(((x0 + x1) / 2, (y0 + y1) / 2) for hs in pth.values() for x0, y0, x1, y1 in hs
                   if (x0, y0) != (x1, y1))
    encoders = [((a[0] + b[0]) / 2, a[1]) for a in slots for b in slots
                if a[0] < b[0] and abs(a[1] - b[1]) < 1e-6 and 10 < b[0] - a[0] < 12]
    lights = [((c[0] + c[2]) / 2, (c[1] + c[3]) / 2) for c in map(extent, edge[1:])]
    want = encoders + [cpl["RANGE"][:2]] + lights
    def outline_corner(xy, r):
        return all(abs(min(v - lo, hi - v) - r) < 1e-3 for v, lo, hi in ((xy[0], px0, px1), (xy[1], py0, py1)))
    round_holes = [xy for xy, r in front if r != corner_r and not outline_corner(xy, r)]
    ok.append(match(f"{len(encoders)} encoders (lug slots), RANGE (CPL) and {len(lights)} LED cutouts (Edge_Cuts) = "
                    "the plate STEP's round through holes", [(x + o, y + o) for x, y in want], round_holes))
    ok.append(match("the plate STEP's round through holes = the DXF CUT layer's, centre and radius",
                    [(*xy, r) for xy, r in front if xy in round_holes], dxf_round))
    return all(ok)


if __name__ == "__main__":
    results = []
    for folder in sys.argv[1:]:
        print("==", folder)
        results.append(main(folder))
        print("RESULT", folder, "pass" if results[-1] else "fail")
    sys.exit(0 if all(results) else 1)
