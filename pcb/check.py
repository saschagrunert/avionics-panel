"""Independent checks on the generated Gerbers:
1. rasterise each Gerber file (own minimal parser)
2. electrical check: shorts and opens per net, using the rasterised copper + drills
3. the outer copper Gerbers against the design primitives (the pads of board.py, the segments and vias of
   routed.json): every pad flashed in its place, shape and size, every via and trace as routed, and nothing
   else; then the geometric clearance DRC on those primitives
4. drills and annular rings against JLCPCB's limits, no hole at or in an SMD pad or a paste opening (bar a
   pin-in-paste hole in its own opening), paste on every assembled pad and nowhere else
5. solder mask dams (between openings on the mask Gerbers) against JLCPCB's black minimum, and every opening
   clear of its pad by the mask's registration
6. copper path from every RP2040 supply pin to its nearest decoupling capacitor, one capacitor of its own per
   IOVDD pin over the outer layers, and every decoupling capacitor with its own plane vias
7. routed length of every net against its shortest tree (no detours), USB D+ / D- length and skew
8. JLCPCB's footprint of every bottom-side part on our pads at its place and rotation in the CPL file (pad
   numbers, positions; the cathode and anode of the diodes and LEDs by the pin names of JLC's symbol)
9. no copper on F or B within the keep-out of each mounting hole (plate boss, body boss), only the plane
   inside, and copper on every layer clear of the LED cutouts
10. no exposed SMD pad of another net near a through-hole pad (solder bridges where a pad is soldered by hand:
    J1's shell tabs after full assembly, every through-hole pad with the hand-soldering option)
11. JLCPCB's footprint of every through-hole part at its top-side position and rotation in the CPL file (full
   assembly) on our holes pin by pin, each hole within TH_DRILL_TOL of JLC's in size
12. no copper on B under J1's shell but J1's own pads
13. the legend clear of mask openings and holes, inside the board outline and outside the LED cutouts by
   SILK_EDGE
14. USB protection: the ESD array in line on D+ and D- right behind J1, the damping resistor and the fuse in
    VBUS ahead of every load
15. the drill files against the model: every pad hole, slot and via plated, the mounting holes and the parts'
    peg holes unplated, each in its place and size, and nothing else
16. the Edge_Cuts Gerber against the model: the board outline and every LED cutout in its place, size and
    corner radius, and nothing else
17. a cathode bar in the bottom legend at every diode and LED, beyond its cathode pad on the side away from the
    anode
18. the BOM and CPL files as make_bom.py wrote them: JLCPCB's headers, each BOM line's designators in the CPL
    with Quantity their count and the Comment and LCSC of board.py, the hand-soldering files the bottom side of
    the full ones, every part of board.py on its side (8 and 11 read their parts from these files, and fail
    unless they fit every part of their side)
(precheck.py checks the placement before routing: fixed copper clearances, the bottom-side part bodies and the
mounting holes' keep-outs.)
"""
import csv
import functools
import heapq
import json
import math
import re
import sys

import board as B
import numpy as np
from geom import (
    DETOUR_FACTOR,
    DETOUR_SLACK,
    USB_MAX,
    USB_SKEW,
    bbox,
    boxes_near,
    copper_items,
    detour_limits,
    item_dist,
    near_pairs,
    net_lengths,
    pad_geom,
    pt_seg,
    rounded_rect,
    usb_lengths,
)
from matplotlib.path import Path
from PIL import Image, ImageDraw
from scipy import ndimage

PX = 0.05
WPX, HPX = int(B.W / PX) + 1, int(B.H / PX) + 1


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


def draw_ops(ops):
    img = Image.new("L", (WPX, HPX), 0)
    dr = ImageDraw.Draw(img)
    col = 255

    def P(q):
        return (q[0] / PX, q[1] / PX)

    for op in ops:
        if op[0] == "dark":
            col = 255 if op[1] else 0
        elif op[0] == "region":
            dr.polygon([P(q) for q in op[1]], fill=col)
        elif op[0] == "flash":
            (k, a, b), p = op[1], P(op[2])
            if k == "C":
                r = a / 2 / PX
                dr.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)
            elif k == "R":
                w, h = a / 2 / PX, b / 2 / PX
                dr.rectangle([p[0] - w, p[1] - h, p[0] + w, p[1] + h], fill=col)
            else:
                w, h = a / PX, b / PX
                r = min(w, h) / 2
                if w >= h:
                    q1, q2 = (p[0] - w / 2 + r, p[1]), (p[0] + w / 2 - r, p[1])
                else:
                    q1, q2 = (p[0], p[1] - h / 2 + r), (p[0], p[1] + h / 2 - r)
                dr.line([q1, q2], fill=col, width=int(round(2 * r)))
                for q in (q1, q2):
                    dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=col)
        else:
            r = op[1][1] / 2 / PX
            p0, p1 = P(op[2]), P(op[3])
            dr.line([p0, p1], fill=col, width=max(1, int(round(2 * r))))
            for q in (p0, p1):
                dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=col)
    return np.array(img) > 127


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


# Footprint fit: every bottom-side part's JLCPCB library footprint (footprints/<LCSC>.json, saved from JLC's
# EasyEDA library by footprints/fetch.py, so this runs offline) is placed the way JLCPCB places a bottom part
# (board.py docstring: seen from the top, mirrored left to right, then turned clockwise by the CPL rotation).
# Every JLC pad must land on our pad of the same number, centres within FP_POS_TOL and every edge within
# FP_EDGE_TOL, and our part may have no pad JLC's lacks. A wrong rotation or pin assignment puts a pad of
# another number there or misses by a pitch (0.4 mm on the RP2040, 1.27 mm on the flash); the tolerances take
# our own land sizes (diodes, SOT-23, 0603, 0402 differ from JLC's by up to 0.22 mm at an edge).
FP_POS_TOL, FP_EDGE_TOL = 0.15, 0.25
# Our pad name -> JLC's pad number, where we name a pad JLC numbers: the RP2040's exposed pad and J1's shell tabs.
FP_PIN = {"C2040": {"EP": "57"}, "C165948": {"SH1a": "1", "SH1b": "2", "SH-1b": "3", "SH-1a": "4"}}
# The diodes and LEDs: our pads are K and A. Which of JLC's pads is the cathode is read from JLC's own symbol of
# the part (the "pins" of footprints/<LCSC>.json, pad number and pin name): it names the cathode K, C or -, the
# anode A or +. Each part type is looked up on its own, so a footprint with the anode on pad 1 fits the other
# way round and a part placed against it fails.
POLARITY = {"K": ("K", "C", "-"), "A": ("A", "+")}
# The reverse-mount LEDs (LiteOn's C230 package): our pads stop JLCPCB's 0.2 mm short of the cutout (board.py
# LED_CUTOUT), 1.3 mm from the LED's centre. JLC's footprint of the amber LTST-C230KSKT (C125108) runs them to
# 0.05 mm from its 1.9 mm cutout (1.0 from the centre); JLC's footprint of the white LTW-C230DS (C575513), the
# same package, draws its pads 0.33 mm into a 2.3 mm round hole (0.82 from the centre). So each pad differs from
# JLC's at its inner edge, the one towards the cutout, by 0.3 and 0.48, and with it at its centre by 0.18 and
# 0.24; its outer edge and its width agree with JLC's to 0.07 mm. FP_TOL gives each LED that much at the centre
# and at the inner edge alone (centre, inner edge): the other three edges keep FP_EDGE_TOL, so another package's
# footprint in the LED's place fails (a SOD-123F's pads are 0.3 mm narrower on either side). An LED the wrong
# way round misses by 3.5 mm and more.
FP_TOL = {"C125108": (0.2, 0.32), "C575513": (0.25, 0.5)}


def jlc_place(x, y, rot):
    """A JLC footprint point (top view, y down) on the bottom side at CPL rotation rot, seen from the top."""
    a = math.radians(rot)
    return (-x * math.cos(a) - y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


@functools.cache
def jlc_footprint(lcsc):
    """JLC's footprint of one part (footprints/<LCSC>.json), read once per part type."""
    with open(f"footprints/{lcsc}.json") as f:
        return json.load(f)


def jlc_number(lcsc, pin):
    """JLC's pad number for our pad `pin` of a part: FP_PIN's where we name the pad, for K and A the pad of the
    one pin JLC's symbol names so (POLARITY; None unless there is exactly one), else the pin itself, a number."""
    if pin in FP_PIN.get(lcsc, {}):
        return FP_PIN[lcsc][pin]
    if pin in POLARITY:
        nums = [num for num, name in jlc_footprint(lcsc)["pins"] if name in POLARITY[pin]]
        return nums[0] if len(nums) == 1 else None
    return pin


def footprint_fit(ref, lcsc, cx, cy, rot, ours):
    """(worst centre offset, worst edge offset, worst inner edge offset, problems) of JLC's footprint at rotation
    rot on our pads. The inner edge, the one towards the part's centre, counts on its own for a part in FP_TOL
    (else it is one of the edges)."""
    ref_pads = jlc_footprint(lcsc)["pads"]
    mine, worst_c, worst_e, worst_i, bad = {}, 0.0, 0.0, 0.0, []
    for pin, p in ours.items():
        num = jlc_number(lcsc, pin)
        if num is None:
            bad.append(f"JLC's symbol of {lcsc} has no single pin named {' / '.join(POLARITY[pin])} for {p.name}")
        else:
            mine[num] = p
    pos_tol, inner_tol = FP_TOL.get(lcsc, (FP_POS_TOL, None))
    for num, x, y, w, h in ref_pads:
        dx, dy = jlc_place(x, y, rot)
        X, Y = cx + dx, cy + dy
        if round(rot) % 180 == 90:
            w, h = h, w
        p = mine.get(num)
        if p is None:
            bad.append(f"JLC pad {num} has no pad {ref}.{num} on the board"); continue
        c = math.hypot(p.x - X, p.y - Y)
        edges = [abs(p.x - p.w / 2 - (X - w / 2)), abs(p.x + p.w / 2 - (X + w / 2)),     # west, east,
                 abs(p.y - p.h / 2 - (Y - h / 2)), abs(p.y + p.h / 2 - (Y + h / 2))]     # north, south
        inner = 0.0
        if inner_tol is not None:       # JLC's pad west of the part's centre: its east edge, and so on
            inner = edges.pop(int(cx > X) if abs(X - cx) > abs(Y - cy) else 2 + (cy > Y))
        e = max(edges)
        worst_c, worst_e, worst_i = max(worst_c, c), max(worst_e, e), max(worst_i, inner)
        if c > pos_tol or e > FP_EDGE_TOL or inner > (inner_tol or 0.0):
            near = min((q for q in mine.values()), key=lambda q: math.hypot(q.x - X, q.y - Y))
            bad.append(f"JLC pad {num} lands at ({X:.2f}, {Y:.2f}), {c:.2f} mm from {p.name} ({p.net}), "
                       f"edges off by {e:.2f}" + (f", the inner edge by {inner:.2f}" if inner_tol else "")
                       + f"; nearest is {near.name} ({near.net})")
    extra = set(mine) - {r[0] for r in ref_pads}
    bad += [f"{ref}.{n} is not in JLC's footprint" for n in sorted(extra)]
    return worst_c, worst_e, worst_i, bad


# The headers JLCPCB's assembly upload takes, column for column.
CPL_HEADER = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
BOM_HEADER = ["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"]


def read_csv(fname, header):
    """The rows of a CSV file that make_bom.py wrote, as dicts by its header, which must be `header`."""
    with open(fname, newline="") as f:
        r = csv.DictReader(f)
        if r.fieldnames != header:
            raise SystemExit(f"ASSEMBLY FILES: {fname} has the header {r.fieldnames}, JLCPCB takes {header}")
        return list(r)


def assembly_files():
    """The BOM and CPL files as uploaded to JLCPCB, read back: the parts of full assembly as {ref: (value, LCSC,
    x, y, rotation, layer)} (x, y in board mm, y down; from CPL-full.csv and BOM-full.csv), and how many problems
    it found between the files and with board.PARTS. Each BOM line's designators are CPL rows of its variant, Quantity
    their count, Comment and LCSC those of board.py; the hand-soldering CPL is the bottom rows of the full one;
    every part of board.py is in the full files on its side, and nothing else."""
    bad, cpl, bom = [], {}, {}
    for v in ("", "-full"):
        rows = read_csv(f"avionics-panel-rev1-CPL{v}.csv", CPL_HEADER)
        cpl[v] = {r["Designator"]: r for r in rows}
        if len(cpl[v]) != len(rows):
            bad.append(f"CPL{v}.csv names a designator twice")
        bom[v] = read_csv(f"avionics-panel-rev1-BOM{v}.csv", BOM_HEADER)
        seen = []
        for line in bom[v]:
            refs = line["Designator"].split(",")
            seen += refs
            if int(line["Quantity"]) != len(refs):
                bad.append(f"BOM{v}.csv: {line['Comment']} has Quantity {line['Quantity']} for {len(refs)} designators")
        if sorted(seen) != sorted(cpl[v]):
            bad.append(f"BOM{v}.csv and CPL{v}.csv differ in {sorted(set(seen) ^ set(cpl[v]))} or name one twice")
    full = cpl["-full"]
    if cpl[""] != {ref: r for ref, r in full.items() if r["Layer"] == "Bottom"}:
        bad.append("CPL.csv is not the bottom rows of CPL-full.csv")
    if any(line not in bom["-full"] for line in bom[""]):
        bad.append("a line of BOM.csv is not in BOM-full.csv")
    lines = {ref: (line["Comment"], line["LCSC Part #"])
             for line in bom["-full"] for ref in line["Designator"].split(",")}
    want = {ref: (value, lcsc) for ref, value, lcsc, *_r in B.PARTS}
    if lines != want:
        bad.append(f"BOM-full.csv's Comment or LCSC differs from board.py's for "
                   f"{sorted(r for r in lines.keys() | want.keys() if lines.get(r) != want.get(r))}")
    sides = {ref: {"top": "Top", "bottom": "Bottom"}[side] for ref, *_r, side in B.PARTS}
    if {ref: r["Layer"] for ref, r in full.items()} != sides:
        bad.append("CPL-full.csv does not place every part of board.py on its side (Layer Top or Bottom)")
    # the footprint fits take the parts on their own side; fitted_all() counts the others as missing
    parts = {ref: (*lines[ref], float(r["Mid X"].removesuffix("mm")), B.H - float(r["Mid Y"].removesuffix("mm")),
                   int(r["Rotation"]), r["Layer"]) for ref, r in full.items()
             if ref in lines and r["Layer"] == sides.get(ref)}
    for p in bad:
        print("ASSEMBLY FILES:", p)
    print(f"assembly files: BOM-full and CPL-full {len(full)} parts, BOM and CPL {len(cpl[''])} (the bottom side), "
          f"{len(bad)} problems")
    return parts, len(bad)


def fitted_all(types, side):
    """1 (a problem) unless the footprint fit took as many parts as board.py has on that side, else 0."""
    n, want = sum(len(t["refs"]) for t in types.values()), sum(p[-1] == side for p in B.PARTS)
    if n != want:
        print(f"FOOTPRINT FIT: {n} {side}-side parts fitted from the CPL, board.py has {want}")
    return int(n != want)


def footprints(pads, parts):
    """Every bottom-side part against JLC's footprint at its place and rotation in the CPL (see FP_POS_TOL above);
    parts: assembly_files()."""
    bad = 0
    byref = {}
    for p in pads:
        ref, pin = p.name.split(".", 1)
        if not re.fullmatch(r"[FV]\d+|E", pin):
            byref.setdefault(ref, {})[pin] = p
    types = {}
    for ref, (value, lcsc, x, y, rot, layer) in parts.items():
        if layer != "Bottom":
            continue
        t = types.setdefault(lcsc, {"value": value, "refs": [], "rots": set(), "c": 0.0, "e": 0.0, "i": 0.0})
        t["refs"].append(ref); t["rots"].add(rot % 360)
        c, e, inner, probs = footprint_fit(ref, lcsc, x, y, rot, byref.get(ref, {}))
        t["c"], t["e"], t["i"] = max(t["c"], c), max(t["e"], e), max(t["i"], inner)
        if probs:
            bad += 1
            fits = [r for r in (0, 90, 180, 270) if not footprint_fit(ref, lcsc, x, y, r, byref.get(ref, {}))[3]]
            more = f"; {len(probs) - 2} more" if len(probs) > 2 else ""
            print(f"FOOTPRINT {ref} ({lcsc}) at CPL rotation {rot}: " + "; ".join(probs[:2]) + more
                  + f". Rotations that fit: {fits or 'none'}")
    for lcsc, t in sorted(types.items(), key=lambda kv: kv[1]["refs"][0]):
        refs = t["refs"][0] + (f" and {len(t['refs']) - 1} more" if len(t["refs"]) > 1 else "")
        rots = "/".join(str(r) for r in sorted(t["rots"]))
        print(f"  {lcsc:9s} {t['value']:20s} {refs:22s} CPL {rots:7s} centres within {t['c']:.3f} mm, "
              f"edges within {t['e']:.3f} mm" + (f", inner edges within {t['i']:.3f} mm" if lcsc in FP_TOL else ""))
    leds = "".join(f"; {types[lcsc]['value']} {c} centre, {i} inner edge" for lcsc, (c, i) in FP_TOL.items()
                   if lcsc in types)
    bad += fitted_all(types, "bottom")
    print(f"footprints: {len(types)} JLC footprints on {sum(len(t['refs']) for t in types.values())} bottom-side "
          f"parts (tolerance {FP_POS_TOL} centre, {FP_EDGE_TOL} edge{leds}), {bad} problems")
    return bad


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
        (k, a, b), (x, y) = op[1], op[2]
        if k == "R":
            out.append(("rect", x - a / 2, y - b / 2, x + a / 2, y + b / 2, 0.0))
        elif k == "C":
            out.append(("cap", x, y, x, y, a / 2))
        elif a >= b:
            out.append(("cap", x - (a - b) / 2, y, x + (a - b) / 2, y, b / 2))
        else:
            out.append(("cap", x, y - (b - a) / 2, x, y + (b - a) / 2, a / 2))
    return out


# The outer copper Gerbers against the design primitives. The clearance DRC, the footprint fits, the hand-solder
# distances and the lengths are worked out on the primitives (the pads of board.py, the segments and vias of
# routed.json), so the Gerbers must hold exactly that copper: every pad flashed on each of its layers in its
# shape, size and place, every via flashed on both, every segment drawn in its width from end to end, and
# nothing else. COPPER_TOL takes the Gerber number format (aperture sizes to 0.0001 mm). The inner planes are
# drawn from the same pads and vias; they are measured on the raster (plane clearance, keep-outs, cutouts).
COPPER_TOL = 2e-4


def copper_model(pads, segments, vias):
    """The flashes and lines of the F and B copper Gerbers against the pads, vias and segments, one for one."""
    bad, counts = 0, []
    for layer, fname in (("F", "avionics-F_Cu.gtl"), ("B", "avionics-B_Cu.gbl")):
        want = [(("flash", {"rect": "R", "circle": "C"}.get(p.shape, "O")),
                 (p.w, p.w if p.shape == "circle" else p.h, p.x, p.y), f"pad {p.name}")
                for p in pads if layer in p.layers]
        want += [(("flash", "C"), (v[3], v[3], v[0], v[1]), f"via ({v[2]})") for v in vias]
        for x1, y1, x2, y2, ly, net, w in segments:
            if ly != layer:
                continue
            if (x1, y1) == (x2, y2):                # make.py flashes a segment without length
                want.append((("flash", "C"), (w, w, x1, y1), f"trace point ({net})"))
            else:
                want.append((("line", "C"), (w, x1, y1, x2, y2), f"trace ({net})"))
        got = {}
        for op in gerber_ops(fname):
            if op[0] == "flash":
                (k, a, b), (x, y) = op[1], op[2]
                got.setdefault(("flash", k), []).append((a, a if k == "C" else b, x, y))
            elif op[0] == "line":
                got.setdefault(("line", op[1][0]), []).append((op[1][1], *op[2], *op[3]))
            elif op != ("dark", True):
                bad += 1; print(f"COPPER {layer}: a {'region' if op[0] == 'region' else 'clear polarity'} on the "
                                "Gerber, the model has none")
        for key, vals, what in want:
            pool = got.get(key, [])
            hit = next((i for i, g in enumerate(pool)
                        if max(abs(a - b) for a, b in zip(g, vals, strict=True)) < COPPER_TOL), None)
            if hit is None:
                bad += 1
                print(f"COPPER {layer}: {what} is not on the Gerber as modelled, a {key[0]} {key[1]} "
                      + " ".join(f"{v:g}" for v in vals))
            else:
                pool.pop(hit)
        for key, pool in got.items():
            for g in pool:
                bad += 1
                print(f"COPPER {layer}: a {key[0]} {key[1]} " + " ".join(f"{v:g}" for v in g)
                      + " on the Gerber is not in the model")
        counts.append(f"{layer} {sum(k[0][0] == 'flash' for k in want)} flashes and "
                      f"{sum(k[0][0] == 'line' for k in want)} traces")
    print(f"copper Gerbers against the model: {', '.join(counts)} (pads, vias, segments), compared one for one in "
          f"place, shape and size (within {COPPER_TOL:g} mm); {bad} problems")
    return bad


# The drill files against the model. The hole checks below measure the plated holes of the file against the copper
# round them, and the footprint fits, the keep-outs and the hole distances work on the model's holes, so the files
# must hold exactly those: plated, every pad's hole in its drill, every slot from end to end in its width (along
# the pad's long side) and every via; unplated, the mounting holes (board.MOUNTS, board.MOUNT_HOLE) and the
# parts' peg holes (board.NPTH). DRILL_TOL takes the drill file's number format (0.001 mm).
DRILL_TOL = 1e-3


def drill_model(pads, vias):
    """The hits of the two drill files against the holes of the model, one for one in place and size."""
    plated = [((p.x, p.y, p.x, p.y, p.drill), f"the hole of {p.name}") for p in pads if p.drill and not p.slot]
    for p in pads:
        if p.slot:
            d, tall = (p.slot[1] - p.slot[0]) / 2, p.h >= p.w
            plated.append(((p.x - d * (not tall), p.y - d * tall, p.x + d * (not tall), p.y + d * tall, p.slot[0]),
                           f"the slot of {p.name}"))
    plated += [((v[0], v[1], v[0], v[1], v[4]), f"a via ({v[2]})") for v in vias]
    unplated = [((x, y, x, y, B.MOUNT_HOLE), "a mounting hole") for x, y in B.MOUNTS]
    unplated += [((x, y, x, y, d), "a peg hole") for x, y, d in B.NPTH]
    bad = 0

    def at(x0, y0, x1, y1):
        return f"at ({x0:.3f}, {y0:.3f})" + (f" to ({x1:.3f}, {y1:.3f})" if (x0, y0) != (x1, y1) else "")
    for fname, want in (("avionics-PTH.drl", plated), ("avionics-NPTH.drl", unplated)):
        got = [(x0, B.H - y0, x1, B.H - y1, t) for x0, y0, x1, y1, t in drill_hits(fname)]
        for (*ends, size), what in want:
            there = [g for g in got if any(max(abs(a - b) for a, b in zip(g[:4], e, strict=True)) < DRILL_TOL
                                           for e in (ends, ends[2:] + ends[:2]))]       # a slot from either end
            hit = next((g for g in there if abs(g[4] - size) < DRILL_TOL), None)
            if hit is None:
                bad += 1
                print(f"DRILL {fname}: {what} {at(*ends)}, {size:g} mm in the model, is "
                      + (f"{there[0][4]:g} mm in the file" if there else "not in the file"))
            if there:
                got.remove(hit or there[0])
        for *ends, t in got:
            bad += 1; print(f"DRILL {fname}: a {t:g} mm hole {at(*ends)} in the file is not in the model")
    print(f"drill files against the model: {len(plated)} plated ({sum(bool(p.slot) for p in pads)} slots, "
          f"{len(vias)} vias), {len(unplated)} unplated ({len(B.MOUNTS)} mounting holes), compared one for one in "
          f"place and size (within {DRILL_TOL:g} mm); {bad} problems")
    return bad


# JLCPCB keeps copper this far from a routed edge (the LED cutouts; the outline has its own EDGE_CLEAR)
ROUTED_EDGE_CU = 0.2
# JLCPCB standard process (no surcharge): 0.3 mm smallest plated drill, 0.5 mm smallest unplated hole,
# via pad at least 0.15 mm over the drill (0.45 mm on 0.3), component pads with a wider ring
MIN_DRILL, MIN_NPTH = 0.3, 0.5
MIN_RING_VIA, MIN_RING_PAD = 0.075, 0.15
VIA_PAD_MIN = 0.1           # hole copper to SMD pad copper or a paste opening, any net: no via in a pad
THERMAL = {"U1.EP"}         # exposed pad: its GND vias are meant to be there, clear of its paste windows


def assembled(p, bottom_refs):
    """A pad JLCPCB solders: a pin of a bottom-side part (not a fan-out point, 1V1 probe via, USB resistor
    breakout point or SWD wire pad; those carry the part's name but no part pin), or a pin-in-paste hole of one
    (the USB-C shell tabs)."""
    ref, pin = p.name.split(".", 1)
    if p.pip:
        return ref in bottom_refs and "B" in p.layers
    return (ref in bottom_refs and not p.drill and p.layers == "B"
            and not re.fullmatch(r"[FV]\d+|E", pin))


def box_in(fb, pb):
    """bounding box fb inside bounding box pb."""
    return fb[0] > pb[0] - 1e-6 and fb[1] > pb[1] - 1e-6 and fb[2] < pb[2] + 1e-6 and fb[3] < pb[3] + 1e-6


def holes_and_paste(pads, vias, pth, npth):
    """Drills against JLCPCB's limits, no hole copper at or in an SMD pad or a paste opening (bar a pin-in-paste
    hole's own), paste on every assembled pad and on nothing else. Measured on the drill files and the paste
    Gerber."""
    bad = 0
    bottom = {ref for ref, *_r, side in B.PARTS if side == "bottom"}
    paste = flashes("avionics-B_Paste.gbp")
    # --- drill sizes and annular rings: every plated hole matched to the via or pad around it
    ring_min = {"via": 9.0, "pad": 9.0}
    hole_cu = {}                                # what -> (geometry of the copper around the hole, net)
    for x, y, t in sorted(set(pth)):            # read_drill lists a round hole twice, a slot as samples
        v = next((v for v in vias if abs(v[0] - x) < 1e-3 and abs(v[1] - y) < 1e-3), None)
        if v:
            ring, kind = (v[3] - t) / 2, "via"
            hole_cu[f"via {v[2]} at ({x:.2f}, {y:.2f})"] = (("cap", x, y, x, y, v[3] / 2), v[2])
        else:
            p = next((p for p in pads if p.drill and item_dist(pad_geom(p), ("cap", x, y, x, y, 0)) < 0), None)
            if p is None:
                print(f"PLATED HOLE WITHOUT PAD at ({x:.2f}, {y:.2f})"); bad += 1; continue
            if p.slot:                          # make.py drills slots along y only, so the pad must be tall
                if p.h < p.w:
                    raise ValueError(f"{p.name}: slot along a wide pad, make.py only drills vertical slots")
                ring = min(p.w - p.slot[0], p.h - p.slot[1]) / 2
            else:
                ring = (min(p.w, p.h) - t) / 2
            kind = "pad"
            hole_cu[p.name] = (pad_geom(p), p.net)
        ring_min[kind] = min(ring_min[kind], ring)
        if t < MIN_DRILL - 1e-6:
            print(f"DRILL TOO SMALL {t} at ({x:.2f}, {y:.2f})"); bad += 1
        if ring < (MIN_RING_VIA if kind == "via" else MIN_RING_PAD) - 1e-6:
            print(f"ANNULAR RING {ring:.3f} mm ({kind}) at ({x:.2f}, {y:.2f})"); bad += 1
    for x, y, t in npth:
        if t < MIN_NPTH - 1e-6:
            print(f"UNPLATED HOLE TOO SMALL {t} at ({x:.2f}, {y:.2f})"); bad += 1
    print(f"drills: smallest plated {min(t for *_xy, t in pth):.2f} mm (min {MIN_DRILL}), unplated "
          f"{min(t for *_xy, t in npth):.2f} mm (min {MIN_NPTH}); annular ring vias {ring_min['via']:.3f} mm "
          f"(min {MIN_RING_VIA}), pads {ring_min['pad']:.3f} mm (min {MIN_RING_PAD})")
    # --- hole copper vs SMD pads (fan-out breakout points under the mask are not pads) and paste openings
    smd = [p for p in pads if not p.drill and len(p.layers) == 1 and (p.mask or p.paste)]
    near = 9.0

    def gap(d):
        return f"{d:.3f} mm from" if d >= 0 else "overlaps"
    for what, (g, net) in hole_cu.items():
        gb = bbox(g)
        for p in smd:
            if p.name in THERMAL and net == p.net:
                continue
            pg = pad_geom(p)
            if not boxes_near(bbox(pg), gb, 1):
                continue
            d = item_dist(g, pg)
            near = min(near, d)
            if d < VIA_PAD_MIN - 1e-6:
                print(f"HOLE AT PAD: {what} {gap(d)} {p.name}"); bad += 1
        own = next((p for p in pads if p.name == what and p.pip), None)   # pin-in-paste: paste on its own pad
        for f in paste:
            if not boxes_near(bbox(f), gb, 1) or (own and box_in(bbox(f), bbox(pad_geom(own)))):
                continue
            d = item_dist(g, f)
            near = min(near, d)
            if d < VIA_PAD_MIN - 1e-6:
                print(f"HOLE AT PASTE: {what} {gap(d)} the paste opening at ({f[1]:.2f}, {f[2]:.2f})"); bad += 1
    # --- paste: every opening inside an assembled pad, every assembled pad with paste
    pasted = set()
    for f in paste:
        fb = bbox(f)
        p = next((p for p in pads if "B" in p.layers and (not p.drill or p.pip) and box_in(fb, bbox(pad_geom(p)))),
                 None)
        if p is None or not assembled(p, bottom):
            where = p.name if p else "no pad"
            print(f"PASTE ON {where} at ({(fb[0] + fb[2]) / 2:.2f}, {(fb[1] + fb[3]) / 2:.2f})"); bad += 1
            continue
        pasted.add(p.name)
    nopaste = [p.name for p in pads if assembled(p, bottom) and p.name not in pasted]
    for name in nopaste:
        print(f"NO PASTE on {name}"); bad += 1
    n_asm = sum(assembled(p, bottom) for p in pads)
    print(f"pads and holes: closest hole copper to an SMD pad or paste {near:.3f} mm (min {VIA_PAD_MIN}); "
          f"paste on {len(pasted)} of {n_asm} assembled pads, {len(paste)} openings; {bad} problems")
    return bad


# The through-hole parts on the top are soldered by hand from the bottom, where the SMD parts sit: a solder
# bridge from an iron-soldered pin to an SMD pad of another net is a short that is hard to see and to clear (a
# through-hole LED's GND pad 0.28 mm from its resistor's GPIO pad was one). J1's four shell tabs (pin-in-paste)
# are filled with solder by hand from the top too, and the excess comes out on the bottom (docs/building/assembly.md).
# Every exposed SMD pad of another net keeps HAND_SMD_MIN of copper from every hand-soldered pad: room for the
# iron's tip and a fillet.
HAND_SMD_MIN = 1.0


def hand_solder(pads):
    """Exposed SMD pads (a mask opening) of another net near the plated holes of the top-side (hand-soldered)
    parts and J1's shell tabs, measured copper to copper."""
    top = {ref for ref, *_r, side in B.PARTS if side == "top"}
    tht = [p for p in pads if p.drill and not p.pip and p.name.split(".")[0] in top]
    tht += [p for p in pads if p.pip and p.name.startswith("J1.SH")]     # the shell tabs
    smd = [p for p in pads if not p.drill and len(p.layers) == 1 and p.layers in p.mask]
    bad, near = 0, (9.0, "")
    for t in tht:
        tg = pad_geom(t)
        tb = bbox(tg)
        for p in smd:
            if p.net == t.net and p.net:
                continue
            pg = pad_geom(p)
            if not boxes_near(bbox(pg), tb, HAND_SMD_MIN + 0.5):
                continue
            d = item_dist(tg, pg)
            near = min(near, (d, f"{t.name} ({t.net}) to {p.name} ({p.net})"))
            if d < HAND_SMD_MIN - 1e-6:
                bad += 1
                print(f"HAND-SOLDERED PAD {t.name} ({t.net}) {d:.3f} mm from SMD pad {p.name} ({p.net})")
    print(f"hand soldering: {len(tht)} hand-soldered pads, closest SMD pad of another net {near[0]:.3f} mm "
          f"(min {HAND_SMD_MIN}), {near[1]}; {bad} problems")
    return bad


# Through-hole parts: JLC's footprint (footprints/<LCSC>.json, "holes" and "npth") against our holes, as JLCPCB
# places it in full assembly (Standard assembly, both sides): at the top-side CPL position and rotation
# (CPL-full.csv as make_bom.py wrote it; JLC's top convention: seen from the top, the footprint turned
# counter-clockwise by the rotation, its origin on the CPL position). Every JLC hole must land on our hole of the
# pin TH_PIN names for it, within FP_POS_TOL, every unplated one on one of ours, and none of ours may be left
# over. A wrong rotation misses the holes or, on a symmetric hole pattern, puts a pin on the wrong hole: an
# encoder's A on B. That also places a hand-soldered part.
# The hole sizes: ours follow the part's datasheet, JLC's are its library's choice for the same pin, and each of
# ours (a round hole's drill, a slot's width and length, the unplated peg hole) must be within TH_DRILL_TOL of
# JLC's. That is the span of JLCPCB's plated-hole tolerance (+0.13 / -0.08 mm): up to it, our hole can finish the
# size JLC's own would. The pins differ by less (keys 1.0 against JLC's 1.2, PEC11D 1.2 against 1.1, RKJXT 1.1
# against 1.2); a hole further off is a mistyped drill or a hole for another pin.
TH_DRILL_TOL = 0.13 + 0.08
TH_PIN = {                                  # JLC's pin number -> our pins it may land on
    # key: pins 1-2 and 3-4 are joined inside, so 0 and 180 are the same switch (the 6.5 x 4.5 pattern misses at 90)
    "C589907": dict.fromkeys("1234", ("A", "B", "C", "D")),
    "C19270361": {"1": ("A2",), "2": ("C2",), "3": ("B2",), "4": ("D",), "5": ("E",), "6": ("A",), "7": ("C",),
                  "8": ("B",), "9": ("MP-1",), "10": ("MP1",)},     # JLC's symbol: 1-3 and 6-8 A C B, 4 / 5 switch
    "C160841": {"5": ("PUSH",), "6": ("COM",), "7": ("ENCB",), "8": ("ENCA",), "9": ("ECOM",), "10": ("GND",),
                "A": ("A",), "B": ("B",), "C": ("C",), "D": ("D",)},
}


def jlc_top(x, y, rot):
    """A JLC footprint point (top view, y down) on the top side at CPL rotation rot (counter-clockwise seen from
    the top), from the footprint origin."""
    a = math.radians(rot)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def cpl_fit(ref, lcsc, fp, cx, cy, rot, ours):
    """(worst centre offset, problems) of JLC's footprint with its origin at (cx, cy), top-side rotation rot."""
    worst, used, bad = 0.0, set(), []
    pins = TH_PIN.get(lcsc)
    if pins is None:
        return 9.0, [f"no TH_PIN entry for {lcsc}"]
    for num, hx, hy, d, slot in fp["holes"]:
        dx, dy = jlc_top(hx, hy, rot)
        X, Y = cx + dx, cy + dy
        p = min(ours, key=lambda q, X=X, Y=Y: math.hypot(q.x - X, q.y - Y))
        c = math.hypot(p.x - X, p.y - Y)
        worst = max(worst, c)
        mine = p.slot or (p.drill, 0.0)                         # width and length, as JLC's drill and slot length
        if c > FP_POS_TOL:
            bad.append(f"JLC pin {num} lands at ({X:.2f}, {B.H - Y:.2f}), {c:.2f} mm from the nearest hole {p.name}")
        elif p.name.split(".", 1)[1] not in pins.get(num, ()):
            bad.append(f"JLC pin {num} lands on {p.name} ({p.net}), not on {'/'.join(pins.get(num, ('?',)))}")
        elif max(abs(mine[0] - d), abs(mine[1] - slot)) > TH_DRILL_TOL + 1e-6:
            bad.append(f"{p.name} is drilled {mine[0]:g}" + (f" x {mine[1]:g}" if mine[1] else "") + f", JLC's pin "
                       f"{num} {d:g}" + (f" x {slot:g}" if slot else "") + f": over {TH_DRILL_TOL:g} mm apart")
        used.add(p.name)
    for hx, hy, d in fp["npth"]:
        dx, dy = jlc_top(hx, hy, rot)
        c, hole_d = min(((math.hypot(nx - cx - dx, ny - cy - dy), hole_d) for nx, ny, hole_d in B.NPTH),
                        default=(9.0, 0.0))
        worst = max(worst, c)
        if c > FP_POS_TOL:
            bad.append(f"JLC's unplated hole lands {c:.2f} mm from ours")
        elif abs(hole_d - d) > TH_DRILL_TOL + 1e-6:
            bad.append(f"the unplated hole is {hole_d:g}, JLC's {d:g}: over {TH_DRILL_TOL:g} mm apart")
    bad += [f"{p.name} has no JLC pin" for p in ours if p.name not in used]
    return worst, bad


def tht_footprints(pads, parts):
    """Every top-side part against JLC's footprint at its place and rotation in CPL-full.csv (see TH_PIN above);
    parts: assembly_files()."""
    bad = 0
    types = {}
    at = {ref: (x, y) for ref, _v, _l, x, y, *_r in B.PARTS}
    for ref, (value, lcsc, cx, cy, crot, layer) in parts.items():
        if layer != "Top":
            continue
        fp = jlc_footprint(lcsc)
        ours = [p for p in pads if p.name.split(".")[0] == ref and p.drill]
        t = types.setdefault(lcsc, {"value": value, "refs": [], "ours": set(), "jlc": {h[3] for h in fp["holes"]},
                                    "cpl": set(), "cw": 0.0, "off": set()})
        t["refs"].append(ref)
        t["ours"] |= {p.drill for p in ours}
        cw, probs = cpl_fit(ref, lcsc, fp, cx, cy, crot, ours)
        x, y = at[ref]
        t["cpl"].add(crot); t["cw"] = max(t["cw"], cw); t["off"].add((round(cx - x, 2), round(cy - y, 2)))
        if probs:
            bad += 1
            ok = [r for r in (0, 90, 180, 270) if not cpl_fit(ref, lcsc, fp, cx, cy, r, ours)[1]]
            more = f"; {len(probs) - 2} more" if len(probs) > 2 else ""
            print(f"TOP CPL {ref} ({lcsc}) at CPL ({cx:.3f}, {B.H - cy:.3f}) rotation {crot}: " + "; ".join(probs[:2])
                  + more + f". Rotations that fit there: {ok or 'none'}")
    def mm(v):
        return "/".join(f"{d:g}" for d in sorted(v))
    for lcsc, t in sorted(types.items(), key=lambda kv: kv[1]["refs"][0]):
        refs = t["refs"][0] + (f" and {len(t['refs']) - 1} more" if len(t["refs"]) > 1 else "")
        cpl = "/".join(map(str, sorted(t["cpl"])))
        off = "/".join(f"{dx:+g},{dy:+g}" for dx, dy in sorted(t["off"]))
        print(f"  {lcsc:9s} {t['value']:20s} {refs:16s} drills ours {mm(t['ours'])}, JLC {mm(t['jlc'])}; top CPL "
              f"{cpl}, origin {off} from the part (y down), pins within {t['cw']:.3f} mm")
    bad += fitted_all(types, "top")
    print(f"through-hole footprints: {len(types)} JLC footprints on {sum(len(t['refs']) for t in types.values())} "
          f"top-side parts (tolerance {FP_POS_TOL}, hole sizes within {TH_DRILL_TOL:g} of JLC's), at the top-side "
          f"CPL of full assembly, {bad} problems")
    return bad


# JLCPCB, black (and white) solder mask with 1 oz outer copper: the narrowest dam it keeps between two openings
# (0.10 for green, red, yellow, blue and purple). The board is ordered black.
MASK_DAM = 0.13
# JLCPCB exposes the mask of multilayer boards by LDI, aligned to +-0.02 mm (their blog "Basic Design of Solder
# Mask"; the capabilities page gives no figure, other blogs +-0.025 to +-0.05): an opening at least 0.025 mm larger
# than its pad on every side keeps the mask off the pad wherever it lands (their capabilities allow 1:1, this keeps
# the pads whole).
MASK_MIN_GROW = 0.025
# and at most JLCPCB's usual 0.05 mm per side: with the 0.15 mm copper clearance (board.CLEAR) an opening then stays
# at least 0.10 mm from other copper, over their 0.09 mm opening-to-trace minimum
MASK_MAX_GROW = 0.05


def outline_pts(g, n=72):
    """Points on the outline of a geometry item: a rectangle's corners, round a capsule every 360/n degrees."""
    if g[0] == "rect":
        return [(g[1], g[2]), (g[3], g[2]), (g[1], g[4]), (g[3], g[4])]
    _, x1, y1, x2, y2, r = g
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n) for cx, cy in ((x1, y1), (x2, y2))]


def inset(g, x, y):
    """How far inside the geometry item the point lies (negative: outside)."""
    if g[0] == "rect":
        return min(x - g[1], g[3] - x, y - g[2], g[4] - y)
    return g[5] - pt_seg(x, y, *g[1:5])


# Pads whose mask openings differ from their copper layers, on purpose: the routing points of the fan-out and of the
# USB lines at the 27R resistors stay under the mask (but the SWD pads U1.F24 and U1.F25, exposed), and the 1V1
# probe pads are open on the top only. Every other pad must be open on each of its layers (the ESD array, the fuse
# and R_IN have no routing points), so a pad dropped from the mask in board.py fails here, not only one the writer
# missed.
MASK_EXCEPT = ((re.compile(r"U1\.F(?!2[45]$)\d+|R_D[MP]\.E"), ""), (re.compile(r"U1\.V\d+"), "F"))


def mask_dams(pads):
    """Solder mask dams measured on the mask Gerbers: no two openings closer than MASK_DAM, and no openings of
    pads on different nets touching (one merged opening leaves no dam at all). Every opening reaches
    MASK_MIN_GROW beyond its pad's copper all round, and every pad is open on its layers (MASK_EXCEPT aside).
    Prints the count of dams at the minimum."""
    bad = 0
    for p in pads:
        want = next((m for rx, m in MASK_EXCEPT if rx.fullmatch(p.name)), p.layers)
        if set(p.mask) != set(want):
            bad += 1; print(f"MASK OPENING ON {p.mask or 'no layer'} FOR {p.name}, ITS LAYERS ARE {p.layers}")
    for layer, fname in (("F", "avionics-F_Mask.gts"), ("B", "avionics-B_Mask.gbs")):
        ops = flashes(fname)
        bbs = [bbox(g) for g in ops]
        nets, grow, opened = [], 9.0, set()
        for g, b in zip(ops, bbs, strict=True):     # the pad each opening belongs to: same centre
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            p = next((p for p in pads if layer in p.mask and abs(p.x - cx) < 1e-3 and abs(p.y - cy) < 1e-3), None)
            nets.append(p and (p.net or "NC:" + p.name))
            if p is None:
                bad += 1; print(f"MASK OPENING WITHOUT PAD on {layer} at ({cx:.2f}, {cy:.2f})")
                continue
            opened.add(p.name)
            m = round(min(inset(g, x, y) for x, y in outline_pts(pad_geom(p))), 4) + 0   # + 0: no "-0.000"
            grow = min(grow, m)
            if m < MASK_MIN_GROW - 1e-4:
                bad += 1; print(f"MASK OPENING {m:.3f} mm OVER {p.name} on {layer} (min {MASK_MIN_GROW})")
            if m > MASK_MAX_GROW + 1e-4:     # (m is the narrowest margin; an opening grown evenly has it all round)
                bad += 1; print(f"MASK OPENING {m:.3f} mm OVER {p.name} on {layer} (max {MASK_MAX_GROW})")
        for p in pads:
            if layer in p.mask and p.name not in opened:
                bad += 1; print(f"PAD WITHOUT MASK OPENING: {p.name} on {layer}")
        at_min, worst = 0, 9.0
        for i, j in near_pairs(ops, 0.2):
            d = item_dist(ops[i], ops[j])
            where = f"on {layer} at ({ops[i][1]:.2f}, {ops[i][2]:.2f})"
            if d <= 1e-6:
                if nets[i] != nets[j]:
                    bad += 1; print(f"MASK OPENINGS MERGED, NO DAM between {nets[i]} and {nets[j]} {where}")
                continue
            worst = min(worst, d)
            if d < MASK_DAM - 1e-4:
                bad += 1; print(f"MASK DAM {d:.3f} mm {where}")
            elif d < MASK_DAM + 1e-4:
                at_min += 1
        narrow = f"{worst:.3f} mm" if worst < 9 else "none under 0.2 mm"
        print(f"mask {layer}: {len(ops)} openings, narrowest dam {narrow} (min {MASK_DAM}, black), "
              f"{at_min} at exactly {MASK_DAM}; openings at least {grow:.3f} mm beyond their pads "
              f"({MASK_MIN_GROW} to {MASK_MAX_GROW})")
    return bad


# Decoupling, measured as the copper path from the RP2040 pin to the capacitor pad: trace length on the outer
# layers plus, through a plane, the straight distance from via to via (pad centre to pad centre).
# - Pins with a capacitor of their own: the IOVDD pins 1 on C_IO1, 10 on C_IO10, 22 on C_IO22, 42 with ADC_AVDD
#   43 and VREG_VIN 44 on C_D2 (1 uF) and 49 with USB_VDD 48 on C_IO49, VREG_VOUT 45 on C_1V0 and DVDD 50 on
#   C_1V1: at most OWN_CAP_MAX of copper. Raspberry Pi's minimal design puts each capacitor right at its
#   pin; the limit keeps the supply side of the loop at about 2 nH, the order of the capacitor's own ESL plus its
#   GND via (a 0.25 mm trace 0.2 mm over the 3V3 plane has about 0.3 nH/mm). The C_IO capacitors have no 3V3 via
#   of their own (cap_vias): their pin feeds the plane through its via under the chip, so those pins (1, 10, 22,
#   48, 49) must also reach the 3V3 plane within PLANE_ENTRY_MAX of copper.
# - Exceptions, no capacitor of their own: IOVDD 33 and RUN 26 (tied to 3V3) drop straight into the 3V3 plane (at
#   most PLANE_ENTRY_MAX of copper to the via) and share the capacitors on it; east of pin 33's fan-out lane is
#   the only way north for the ALT/HDG and FREQ lines, and no seed routed them past a capacitor there
#   (board.add_io_caps). DVDD 23 on the north side has no room between the crystal and the fan-out (C_IO22 takes
#   the gap above pins 22 and 23); it reaches the 1V1 capacitors over the top layer through V23. Its path is
#   reported, not limited.
OWN_CAP_MAX = 6.0
# - The regulator's input and output want 1 uF at the pin (RP2040 datasheet 2.9.3 / 2.10.1): the nearest
#   capacitor of VREG_VIN (44) and VREG_VOUT (45) must be at least CAP_MIN_UF.
CAP_MIN_UF = {44: 1.0, 45: 1.0}
PLANE_ENTRY_MAX = 2.0
PLANE_SHARED = {26, 33}
NO_ROOM = {23}
CAP_VIA_MAX = 1.0          # every decoupling capacitor: its own plane via at most one stub from the pad centre
# - One capacitor per IOVDD pin (issue #15): each IOVDD pin but 33 (above) reaches a capacitor of its own over the
#   outer-layer copper alone (no plane in the path), within OWN_CAP_MAX, and no two IOVDD pins reach the same one
#   first. A capacitor that only the plane brings within reach, or one shared by two IOVDD pins, fails.
IOVDD = (1, 10, 22, 42, 49)


def centre_line(g):
    """The centre line of a geometry item: a capsule's spine, a rectangle's centre."""
    if g[0] == "rect":
        c = ((g[1] + g[3]) / 2, (g[2] + g[4]) / 2)
        return c, c
    return (g[1], g[2]), (g[3], g[4])


def closest_pair(sa, sb):
    """Nearly the closest points of two segments (from the four end-to-segment projections)."""
    def proj(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
        return (a[0] + t * dx, a[1] + t * dy)
    cands = [(p, proj(p, *sb)) for p in sa] + [(proj(q, *sa), q) for q in sb]
    return min(cands, key=lambda c: math.dist(*c))


def copper_graph(net, pads, segments, vias, planes=True):
    """Nodes (pad centres, segment ends, vias, plane points) and edges (copper length) of one net; with
    planes=False the outer-layer copper and the vias alone."""
    on_plane = planes and net in B.PLANES.values()
    adj = {}

    def edge(a, b, d):
        adj.setdefault(a, []).append((b, d))
        adj.setdefault(b, []).append((a, d))

    items = {"F": [], "B": []}                 # (geometry, [(node, (x, y))]) per outer layer
    for p in pads:
        if p.net != net:
            continue
        for ly in p.layers:
            items[ly].append((pad_geom(p), [(("pad", p.name, ly), (p.x, p.y))]))
        if p.drill:                            # plated hole: both layers and the plane
            edge(("pad", p.name, "F"), ("pad", p.name, "B"), 0.0)
            if on_plane:
                edge(("pad", p.name, "B"), ("plane", p.x, p.y), 0.0)
    for x1, y1, x2, y2, ly, n, w in segments:
        if n == net:
            a, b = ("pt", ly, round(x1, 4), round(y1, 4)), ("pt", ly, round(x2, 4), round(y2, 4))
            edge(a, b, math.hypot(x2 - x1, y2 - y1))
            items[ly].append((("cap", x1, y1, x2, y2, w / 2), [(a, (x1, y1)), (b, (x2, y2))]))
    for x, y, n, d, _dr in vias:
        if n == net:
            edge(("via", x, y, "F"), ("via", x, y, "B"), 0.0)
            if on_plane:
                edge(("via", x, y, "B"), ("plane", x, y), 0.0)
            for ly in "FB":
                items[ly].append((("cap", x, y, x, y, d / 2), [(("via", x, y, ly), (x, y))]))
    for its in items.values():                 # touching copper: join the anchors through the contact
        for i, j in near_pairs([g for g, _a in its], 1e-3):
            (ga, anchors_a), (gb, anchors_b) = its[i], its[j]
            if item_dist(ga, gb) > 1e-3:
                continue
            ca, cb = closest_pair(centre_line(ga), centre_line(gb))
            for a, pa in anchors_a:
                for b, pb in anchors_b:
                    if a != b:
                        edge(a, b, math.dist(pa, ca) + math.dist(ca, cb) + math.dist(cb, pb))
    plane = [k for k in adj if k[0] == "plane"]
    for i, a in enumerate(plane):              # across the plane: via to via in a straight line
        for b in plane[i + 1:]:
            edge(a, b, math.hypot(a[1] - b[1], a[2] - b[2]))
    return adj


def shortest(adj, start):
    dist, heap = {start: 0.0}, [(0.0, start)]
    while heap:
        d, n = heapq.heappop(heap)
        if d > dist[n]:
            continue
        for m, w in adj.get(n, ()):
            if d + w < dist.get(m, math.inf):
                dist[m] = d + w
                heapq.heappush(heap, (d + w, m))
    return dist


def microfarads(value):
    """'100nF' -> 0.1, '1uF' -> 1.0, '15pF' -> 1.5e-05"""
    m = re.fullmatch(r"([\d.]+)([pnu])F", value)
    return float(m.group(1)) * {"p": 1e-6, "n": 1e-3, "u": 1.0}[m.group(2)]


def decoupling(pads, segments, vias):
    bad = 0
    value = {ref: microfarads(v) for ref, v, *_r in B.PARTS if ref.startswith("C_")}
    caps = [p for p in pads if re.fullmatch(r"C_\w+\.\d", p.name)]
    print("decoupling: RP2040 supply pin -> nearest capacitor on its net, copper path (trace + via to via)")
    graphs = {}
    pins = sorted((int(p.name[3:]), p) for p in pads
                  if re.fullmatch(r"U1\.\d+", p.name) and p.net in ("3V3", "1V1"))
    for pin, p in pins:
        if p.net not in graphs:
            graphs[p.net] = copper_graph(p.net, pads, segments, vias)
        dist = shortest(graphs[p.net], ("pad", p.name, "B"))
        d, c = min((dist.get(("pad", c.name, "B"), math.inf), c.name) for c in caps if c.net == p.net)
        if pin in PLANE_SHARED:
            entry = min((v for k, v in dist.items() if k[0] == "plane"), default=math.inf)
            ok = entry <= PLANE_ENTRY_MAX
            rule = f"exception: shared through the plane, pin to plane {entry:.2f} mm (max {PLANE_ENTRY_MAX})"
        elif pin in NO_ROOM:
            ok = d < math.inf
            rule = "exception: no room at the pin, over the top layer"
        else:
            ok = d <= OWN_CAP_MAX
            rule = f"own capacitor (max {OWN_CAP_MAX})"
            if re.fullmatch(r"C_IO\d+\.\d", c):         # its 3V3 side is this pin's trace: the pin feeds the plane
                entry = min((v for k, v in dist.items() if k[0] == "plane"), default=math.inf)
                ok = ok and entry <= PLANE_ENTRY_MAX
                rule += f", pin to plane {entry:.2f} mm (max {PLANE_ENTRY_MAX})"
        uf = value[c.split(".")[0]]
        if pin in CAP_MIN_UF:
            ok = ok and uf >= CAP_MIN_UF[pin]
            rule += f", at least {CAP_MIN_UF[pin]:g} uF"
        bad += not ok
        print(f"  pin {pin:2d} {p.net}  {d:5.2f} mm  {c:8s} {uf:g} uF  {rule}  {'OK' if ok else 'FAIL'}")
    # one capacitor per IOVDD pin, over the outer-layer copper alone
    surface = copper_graph("3V3", pads, segments, vias, planes=False)
    supply = dict(pins)
    own = {}
    for pin in IOVDD:
        if supply[pin].net != "3V3":            # a plain raise: asserts vanish under -O
            raise ValueError(f"IOVDD pin {pin} is on {supply[pin].net}, not 3V3")
        dist = shortest(surface, ("pad", supply[pin].name, "B"))
        own[pin] = min((dist.get(("pad", c.name, "B"), math.inf), c.name.split(".")[0]) for c in caps
                       if c.net == "3V3")
    users = {}
    for pin, (_d, ref) in own.items():
        users.setdefault(ref, []).append(pin)
    for pin, (d, ref) in own.items():
        shared = [q for q in users[ref] if q != pin and d < math.inf]
        ok = d <= OWN_CAP_MAX and not shared
        bad += not ok
        why = f", also pin {shared[0]}'s" if shared else ""
        print(f"  IOVDD pin {pin:2d}: own capacitor {ref if d < math.inf else 'none':7s} {d:5.2f} mm of outer-layer "
              f"copper (max {OWN_CAP_MAX}){why}  {'OK' if ok else 'FAIL'}")
    return bad


def cap_vias(pads, vias):
    """Every decoupling capacitor (one pad on GND, the other on a supply) has its own via into the GND plane
    and, if its supply is a plane (3V3), into that plane too: at most CAP_VIA_MAX from the pad centre and
    nearer to that pad than to any other capacitor pad on the net. The IOVDD capacitors (C_IO<pin>) take their
    3V3 over the trace from their pin, which drops into the plane at the pin: their GND via only."""
    bad, n = 0, 0
    byref = {}
    for p in pads:
        if re.fullmatch(r"C_\w+\.\d", p.name):
            byref.setdefault(p.name.split(".")[0], []).append(p)
    for _ref, ps in sorted(byref.items()):
        nets = {p.net for p in ps}
        if "GND" not in nets or not nets & {"3V3", "1V1", "VBUS_F"}:
            continue                            # crystal load capacitors
        n += 1
        for p in ps:
            if p.net not in B.PLANES.values() or (p.net == "3V3" and re.fullmatch(r"C_IO\d+\.\d", p.name)):
                continue
            rivals = [q for q in pads if q.net == p.net and q is not p and re.fullmatch(r"C_\w+\.\d", q.name)]
            own = [v for v in vias if v[2] == p.net and math.hypot(v[0] - p.x, v[1] - p.y) <= CAP_VIA_MAX + 1e-6
                   and all(math.hypot(v[0] - q.x, v[1] - q.y) > math.hypot(v[0] - p.x, v[1] - p.y) for q in rivals)]
            if not own:
                bad += 1; print(f"NO OWN {p.net} VIA within {CAP_VIA_MAX} mm of {p.name}")
    print(f"capacitor vias: {n} decoupling capacitors, each plane pad with its own via within {CAP_VIA_MAX} mm "
          f"(the IOVDD capacitors' 3V3 pads: the trace from their pin), {bad} problems")
    return bad


def lengths(pads, segments):
    """Every net's routed length against geom.detour_limits (DETOUR_FACTOR times its shortest tree plus
    DETOUR_SLACK), and the USB pair."""
    bad = 0
    length = net_lengths(segments)
    rows = []
    limits = detour_limits(pads, {p.net for p in pads if p.net} - set(B.PLANES.values()))
    for net, (tree, lim) in sorted(limits.items()):
        got = length.get(net, 0.0)
        rows.append((got / lim, net, got, tree, lim))
        if got > lim + 1e-6:
            bad += 1
            print(f"DETOUR {net}: {got:.1f} mm routed, shortest tree {tree:.1f}, limit {lim:.1f}")
    rows.sort(reverse=True)
    print(f"lengths: {len(rows)} nets, routed length at most {DETOUR_FACTOR} x shortest tree + {DETOUR_SLACK:.0f} "
          "mm; closest to the limit: " + ", ".join(f"{n} {g:.1f} / {lim:.1f}" for _r, n, g, _t, lim in rows[:4]))
    usb, ok = usb_lengths(length)
    skew = abs(usb["D+"] - usb["D-"])
    bad += not ok
    print(f"USB: D+ {usb['D+']:.1f} mm, D- {usb['D-']:.1f} mm (max {USB_MAX:.0f}), skew {skew:.1f} mm "
          f"(max {USB_SKEW:.0f})  {'OK' if ok else 'FAIL'}")
    return bad


def j1_shell(ras_b, pads):
    """No copper on the bottom under J1's grounded shell (board.J1_BODY) but J1's own pads: a trace there has
    only the solder mask between it and the shell. Measured on the bottom copper Gerber."""
    x0, y0, x1, y1 = B.J1_BODY
    own = ndimage.binary_dilation(draw_ops(pad_ops([p for p in pads if p.name.startswith("J1.") and "B" in p.layers])))
    i0, j0 = ij(max(x0, 0.0), max(y0, 0.0))
    i1, j1 = ij(x1, y1)
    foreign = ras_b & ~own
    hit = foreign[i0:i1 + 1, j0:j1 + 1]
    bad = 0
    lab, n = ndimage.label(hit)
    for c in range(1, n + 1):
        ys, xs = np.nonzero(lab == c)
        bad += 1
        print(f"COPPER UNDER J1 on B at ({(xs.mean() + j0) * PX:.2f}, {(ys.mean() + i0) * PX:.2f}), "
              f"{len(xs) * PX * PX:.2f} mm2")
    if bad:
        print(f"J1 shell: foreign bottom copper under it; {bad} problems")
        return bad
    # the closest foreign copper outside the shell, for the report
    ys, xs = np.nonzero(foreign)
    dx = np.maximum(np.maximum(x0 - xs * PX, xs * PX - x1), 0)
    dy = np.maximum(np.maximum(y0 - ys * PX, ys * PX - y1), 0)
    print(f"J1 shell: no bottom copper under it but J1's pads, closest other copper {np.hypot(dx, dy).min():.2f} mm "
          f"from its outline; 0 problems")
    return bad


# USB protection (issue #14), on the Gerbers and the routed copper:
# - The ESD array U4 is in line on D+ and D-: with its pads cut out of the bottom copper, J1's contacts of a line
#   no longer reach that line's 27R resistor (outer layers joined through the plated holes), so no copper runs
#   past the array; and its pad on the line is at most ESD_MAX of copper from each of J1's contacts.
# - The damping resistor R_IN and the fuse F1 are in series on VBUS ahead of every load, U4's clamp (VCC, pin 5)
#   included: J1 -> R_IN -> F1 -> VBUS_F (C_IN, U3, U4's VCC). Each net of the chain holds only the pads it should
#   (VBUS_CHAIN), and with either part's pads cut out of the bottom copper, the copper on its input side (from J1,
#   from R_IN) no longer reaches any pad on its output side, and no copper island touches the rims of both of its
#   pads (nothing runs past or across it). So a shorted clamp, or U4 turned by 180 degrees, sits behind both:
#   R_IN burns open, the host's port and cable are protected.
ESD_MAX = 5.0
USB_PROT = {"D+": (("J1.A6", "J1.B6"), "U4.6", "R_DP.2"), "D-": (("J1.A7", "J1.B7"), "U4.4", "R_DM.2")}
# part, net of its pin 1, net of its pin 2, a pad on its input side
VBUS_CHAIN = (("R_IN", "VBUS", "VBUS_R", "J1.B4A9"), ("F1", "VBUS_R", "VBUS_F", "R_IN.2"))
CHAIN_PADS = {"VBUS": {"R_IN.1"}, "VBUS_R": {"R_IN.2", "F1.1"}}            # besides J1's contacts on VBUS
LOADS = {"C_IN.2", "U3.3", "U4.5"}              # on VBUS_F, besides the fuse's pin 2


def union_find():
    """(find, union) over hashable keys: find(a) is the key that stands for a's set, union(a, b) joins two sets."""
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)
    return find, union


def cut_islands(ras, pth, cut):
    """The copper islands with the pads `cut` removed from the bottom copper: F and B labelled on their own, joined
    through every plated hole. Returns the labels and find(), which maps (layer, label) to its island."""
    b = ras["B"] & ~ndimage.binary_dilation(draw_ops(pad_ops(cut)))
    lab = {"F": ndimage.label(ras["F"])[0], "B": ndimage.label(b)[0]}
    find, union = union_find()
    for x, y, _d in pth:
        f, k = lab["F"][ij(x, y)], lab["B"][ij(x, y)]
        if f and k:
            union(("F", f), ("B", k))
    return lab, find


def reached(ras, pth, cut, pads, start):
    """The pads of `pads` that the copper of pad `start` reaches with the pads `cut` removed from the bottom copper."""
    lab, find = cut_islands(ras, pth, cut)

    def comp(p):
        ly = "B" if "B" in p.layers else "F"
        c = lab[ly][ij(p.x, p.y)]
        return find((ly, c)) if c else None
    home = comp(start)
    return {p.name for p in pads if home is not None and comp(p) == home}


def bridged(ras, pth, a, b):
    """True when, with pads a and b cut out of the bottom copper, one copper island touches the rims of both: copper
    joining a part's own two pads, which cutting them alone would hide."""
    lab, find = cut_islands(ras, pth, [a, b])

    def rim(p):
        m = ndimage.binary_dilation(draw_ops(pad_ops([p])))
        ring = ndimage.binary_dilation(m, iterations=2) & ~m
        return {find(("B", int(c))) for c in np.unique(lab["B"][ring]) if c}
    return bool(rim(a) & rim(b))


def usb_protection(ras, pth, pads, segments, vias):
    bad = 0
    by = {p.name: p for p in pads}
    esd = [p for p in pads if p.name.startswith("U4.")]
    for line, (contacts, entry, res) in USB_PROT.items():
        net = by[entry].net
        dist = shortest(copper_graph(net, pads, segments, vias), ("pad", entry, "B"))
        d = max(dist.get(("pad", c, "B"), math.inf) for c in contacts)
        past = sorted(set().union(*(reached(ras, pth, esd, pads, by[c]) for c in contacts)) & {res})
        ok = d <= ESD_MAX and not past
        bad += not ok
        print(f"  USB {line}: ESD array pad {entry} {d:.2f} mm of copper from J1 (max {ESD_MAX}), "
              f"{'copper runs past the array to ' + res if past else 'no copper past it'}  {'OK' if ok else 'FAIL'}")
    on = {n: {p.name for p in pads if p.net == n and not p.name.startswith("J1.")} for n in CHAIN_PADS}
    loads = {p.name for p in pads if p.net == "VBUS_F"} - {"F1.2"}
    wrong = [f"{n}: {', '.join(sorted(on[n]))}" for n in CHAIN_PADS if on[n] != CHAIN_PADS[n]]
    wrong += [f"{ref} {by[ref + '.1'].net} -> {by[ref + '.2'].net}" for ref, n1, n2, _s in VBUS_CHAIN
              if (by[ref + ".1"].net, by[ref + ".2"].net) != (n1, n2)]
    wrong += [f"VBUS_F: {', '.join(sorted(loads))}"] if loads != LOADS else []
    for k, (ref, _n1, _n2, start) in enumerate(VBUS_CHAIN):
        after = {n2 for _r, _n1, n2, _s in VBUS_CHAIN[k:]}
        beyond = {p.name for p in pads if p.net in after and not p.name.startswith(ref + ".")}
        past = sorted(reached(ras, pth, [by[ref + ".1"], by[ref + ".2"]], pads, by[start]) & beyond)
        wrong += [f"copper runs past {ref} to {', '.join(past)}"] if past else []
        wrong += [f"copper joins {ref}'s pads"] if bridged(ras, pth, by[ref + ".1"], by[ref + ".2"]) else []
    bad += bool(wrong)
    print("  VBUS: J1 -> " + " -> ".join(ref for ref, *_n in VBUS_CHAIN) + f" -> {', '.join(sorted(LOADS))}, "
          f"nothing past or across either part  {'OK' if not wrong else 'FAIL: ' + '; '.join(wrong)}")
    print(f"USB protection: {bad} problems")
    return bad


# JLCPCB clips the legend off pads and holes. Every legend pixel keeps SILK_CLEAR from every mask opening on its
# side and from every hole, measured on the Gerbers (to 0.05 mm, the raster).
SILK_CLEAR = 0.15


def silk_clear(pth, npth):
    bad = 0
    holes = draw_ops([("flash", ("C", d, d), (x, y)) for x, y, d in pth + npth])
    for side, (sk, mk) in {"F": ("avionics-F_Silkscreen.gto", "avionics-F_Mask.gts"),
                           "B": ("avionics-B_Silkscreen.gbo", "avionics-B_Mask.gbs")}.items():
        legend = raster(sk)
        dist = ndimage.distance_transform_edt(~(raster(mk) | holes)) * PX
        lab, n = ndimage.label(legend & (dist < SILK_CLEAR - 1e-6))
        for c in range(1, n + 1):
            ys, xs = np.nonzero(lab == c)
            bad += 1
            print(f"LEGEND ON A PAD OR HOLE on {side} at ({xs.mean() * PX:.2f}, {ys.mean() * PX:.2f}), "
                  f"{dist[lab == c].min():.2f} mm")
        print(f"legend {side}: closest to a mask opening or hole {dist[legend].min():.2f} mm (min {SILK_CLEAR})")
    return bad


# JLCPCB publishes no legend-to-outline figure. It keeps copper 0.2 mm from a routed edge and mills the outline to
# +-0.2 mm: legend closer than SILK_EDGE to the outline may be clipped or run off the edge (make.py: T()).
SILK_EDGE = 0.3


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


def edge_cuts():
    """The Edge_Cuts Gerber against the model: the board outline and every LED cutout (board.CUTOUTS), each one
    contour in its place and size with its corners rounded as modelled, vertex for vertex the polygon make.py
    draws (geom.rounded_rect), and no other contour. The cutout checks work on board.CUTOUTS, so JLCPCB must mill
    exactly those."""
    cs = contours("avionics-Edge_Cuts.gko")
    want = [(B.W / 2, B.H / 2, B.W, B.H, B.CORNER_R, "the board outline")]
    want += [(*c, f"the LED cutout at ({c[0]:g}, {c[1]:g})") for c in B.CUTOUTS]
    bad = 0
    for x, y, w, h, r, what in want:
        pts = rounded_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, r)
        hit = next((c for c in cs if len(c) == len(pts) and all(
            math.dist(a, p) < COPPER_TOL and math.dist(b, q) < COPPER_TOL
            for (a, b), p, q in zip(c, pts, pts[1:] + pts[:1], strict=True))), None)
        if hit is None:
            bad += 1; print(f"EDGE CUTS: {what}, {w:g} x {h:g} mm R{r:g}, is not on the Gerber as modelled")
        else:
            cs.remove(hit)
    for c in cs:
        (x0, y0), (x1, y1) = (f([a for a, _b in c], axis=0) for f in (np.min, np.max))
        bad += 1
        print(f"EDGE CUTS: a contour round ({(x0 + x1) / 2:g}, {(y0 + y1) / 2:g}), {x1 - x0:g} x {y1 - y0:g} mm, on "
              "the Gerber is not in the model")
    print(f"Edge_Cuts against the model: the outline {B.W:g} x {B.H:g} mm R{B.CORNER_R:g} and {len(B.CUTOUTS)} LED "
          f"cutouts, vertex for vertex (within {COPPER_TOL:g} mm); {bad} problems")
    return bad


def silk_edge():
    """Every legend shape inside the board outline (the Edge_Cuts Gerber) and outside each LED cutout by
    SILK_EDGE. Measured on the Gerber vertices: the outline and the cutouts are convex, so a shape's closest point
    to them is a vertex of a region, or an end of a line or a dot less its radius. Not on the raster, which ends at
    the board edge and would not see legend beyond it."""
    def width(c):
        return max(a[0] for a, _b in c) - min(a[0] for a, _b in c)
    cs = sorted(contours("avionics-Edge_Cuts.gko"), key=width, reverse=True)   # the outline, the widest, first
    if len(cs) != 1 + len(B.CUTOUTS):
        print(f"EDGE CUTS: {len(cs)} contours, expected the outline and {len(B.CUTOUTS)} cutouts")
        return 1
    loops = []
    for k, edge in enumerate(cs):
        ax, ay, bx, by = (np.array(v) for v in zip(*[(*a, *b) for a, b in edge], strict=True))
        loops.append((Path([a for a, _b in edge] + [edge[-1][1]]), ax, ay, bx - ax, by - ay, k == 0))
    bad, worst = 0, {}
    for side, fname in (("F", "avionics-F_Silkscreen.gto"), ("B", "avionics-B_Silkscreen.gbo")):
        shapes, dark = [], True                    # (points, radius) of every dark legend shape
        for op in gerber_ops(fname):
            if op[0] == "dark":
                dark = op[1]
            elif not dark:
                continue                           # a letter's counter, inside the letter
            elif op[0] == "region":
                shapes.append((op[1], 0.0))
            elif op[0] == "line":
                shapes.append(([op[2], op[3]], op[1][1] / 2))
            elif op[0] == "flash":
                shapes.append(([op[2]], math.hypot(op[1][1], op[1][2]) / 2 if op[1][0] == "R" else op[1][1] / 2))
        worst[side] = math.inf
        for pts, r in shapes:
            q = np.array(pts)
            px, py = q[:, :1], q[:, 1:]
            for inside, ax, ay, ux, uy, outline in loops:
                u = np.clip(((px - ax) * ux + (py - ay) * uy) / (ux * ux + uy * uy), 0, 1)
                d = np.hypot(px - (ax + u * ux), py - (ay + u * uy)).min(axis=1)
                ins = inside.contains_points(q)
                d = np.where(ins if outline else ~ins, d, -d) - r      # negative: off the board
                i = int(d.argmin())
                worst[side] = min(worst[side], float(d[i]))
                if d[i] < SILK_EDGE - 1e-6:
                    bad += 1
                    where = "AT THE BOARD EDGE" if outline else "AT AN LED CUTOUT"
                    print(f"LEGEND {where} on {side} at ({q[i, 0]:.2f}, {q[i, 1]:.2f}), {d[i]:.2f} mm from it")
    print(f"legend to board outline and LED cutouts: closest F {worst['F']:.2f} mm, B {worst['B']:.2f} mm (min "
          f"{SILK_EDGE}); {bad} problems")
    return bad


# The cathode marks that JLCPCB's placement preview is checked against (docs/building/ordering.md): every diode
# and LED has a bar in the bottom legend beyond its cathode pad K, on the side away from its anode pad A, at most
# CATHODE_BAR from the pad's outer edge and alongside at least half of that edge. make.py leaves a bar out round
# a via and in a cutout (HOLE_GAP); one left out altogether, or drawn at the anode, fails here.
CATHODE_BAR = 1.0


def cathode_bars(pads):
    by = {p.name: p for p in pads}
    lines = [op[2:] for op in gerber_ops("avionics-B_Silkscreen.gbo") if op[0] == "line"]
    bad, short, n = 0, (9.0, ""), 0
    for k in pads:
        if not k.name.endswith(".K"):
            continue
        n += 1
        a = by[k.name[:-1] + "A"]
        d = math.dist((k.x, k.y), (a.x, a.y))
        ux, uy = (k.x - a.x) / d, (k.y - a.y) / d                   # from the anode to the cathode
        out, half = (k.w / 2, k.h / 2) if abs(ux) > abs(uy) else (k.h / 2, k.w / 2)   # half the pad that way, across
        along = 0.0
        for ends in lines:                                          # each end: beyond the outer edge, along it
            t = [(x - k.x) * ux + (y - k.y) * uy - out for x, y in ends]
            s = sorted(max(-half, min(half, (y - k.y) * ux - (x - k.x) * uy)) for x, y in ends)
            if all(0 < v <= CATHODE_BAR for v in t):
                along += s[1] - s[0]
        short = min(short, (along, k.name))
        if along < half - 1e-6:
            bad += 1
            print(f"NO CATHODE BAR AT {k.name}: {along:.2f} mm of legend line beyond the pad, away from {a.name} "
                  f"(min {half:.2f})")
    print(f"cathode bars: {n} diodes and LEDs, each with a bar in the bottom legend beyond its K pad, away from "
          f"its A pad; the shortest {short[0]:.2f} mm alongside {short[1]} (min half its edge); {bad} problems")
    return bad


def ij(x, y):
    return int(round(y / PX)), int(round(x / PX))


if __name__ == "__main__":
    LAYERS = {"F": "avionics-F_Cu.gtl", "In1": "avionics-In1_Cu.g2", "In2": "avionics-In2_Cu.g3",
              "B": "avionics-B_Cu.gbl"}
    ras = {ly: raster(f) for ly, f in LAYERS.items()}
    pth = read_drill("avionics-PTH.drl")
    npth = read_drill("avionics-NPTH.drl")
    pads = B.build()
    with open("routed.json") as f:
        rd = json.load(f)

    # --- electrical check ---
    lab, ncomp = {}, {}
    for ly, img in ras.items():
        lab[ly], ncomp[ly] = ndimage.label(img)
    find, union = union_find()
    probes = []   # (net, layer, x, y)
    for p in pads:
        for ly in p.layers:
            probes.append((p.net or "NC:" + p.name, ly, p.x, p.y))
    for x1, y1, x2, y2, ly, net, _w in rd["segments"]:
        probes.append((net, ly, (x1 + x2) / 2, (y1 + y2) / 2))
    for x, y, net, _d, _dr in rd["vias"]:
        probes += [(net, "F", x, y), (net, "B", x, y)]
    for ly, net in B.PLANES.items():           # one probe in each plane (a quiet spot)
        probes.append((net, ly, 2.0, B.H / 2))
    slots = [(p.x, p.y) for p in pads if p.slot]
    for (x, y, _d) in pth + [(sx, sy, 0) for sx, sy in slots]:   # plated holes join every layer they touch
        hit = [(ly, lab[ly][ij(x, y)]) for ly in LAYERS if lab[ly][ij(x, y)]]
        for h in hit[1:]:
            union(hit[0], h)
    bad = 0
    comp_nets = {}
    for net, ly, x, y in probes:
        c = lab[ly][ij(x, y)]
        if c == 0:                                  # thin diagonal lines: look one pixel around
            i0, j0 = ij(x, y)
            win = lab[ly][i0 - 1:i0 + 2, j0 - 1:j0 + 2]
            c = int(win.max())
        if c == 0:
            print("PROBE NOT ON COPPER", net, ly, x, y); bad += 1; continue
        comp_nets.setdefault(find((ly, c)), set()).add(net)
    for nets in comp_nets.values():
        if len(nets) > 1:
            print("SHORT between", sorted(nets)); bad += 1
    net_comps = {}
    for comp, nets in comp_nets.items():
        for n in nets:
            net_comps.setdefault(n, set()).add(comp)
    for n, cs in net_comps.items():
        if len(cs) > 1 and not n.startswith("NC:"):
            print("OPEN on net", n, len(cs), "pieces"); bad += 1
    # copper islands nobody probes (floating plane pieces etc.)
    floating = 0
    for ly in LAYERS:
        sizes = ndimage.sum(np.ones_like(lab[ly]), lab[ly], range(1, ncomp[ly] + 1))
        for c in range(1, ncomp[ly] + 1):
            if find((ly, c)) not in comp_nets and sizes[c - 1] * PX * PX > 0.5:
                floating += 1
                ys, xs = np.nonzero(lab[ly] == c)
                print("FLOATING copper", ly, f"{sizes[c-1]*PX*PX:.1f} mm2 at",
                      round(xs.mean() * PX, 1), round(ys.mean() * PX, 1))
    print(f"electrical: {len(net_comps)} nets, {bad} problems, {floating} floating islands")

    # --- inner planes: every hole of another net (and every unplated hole) keeps clear of the plane copper.
    # Measured on the Gerbers: the distance from each drill hole to the nearest plane pixel, minus its radius.
    PLANE_MIN = 0.2                              # JLCPCB inner layer, hole to copper
    owners = [(p.x, p.y, p.net) for p in pads if p.drill] + [(v[0], v[1], v[2]) for v in rd["vias"]]

    def hole_net(x, y):                          # the pad or via the hole belongs to (slots: their pad)
        return min(owners, key=lambda o: (o[0] - x) ** 2 + (o[1] - y) ** 2)[2]

    plane_worst, plane_bad = 9.9, 0
    for ly, pnet in B.PLANES.items():
        dist = ndimage.distance_transform_edt(~ras[ly]) * PX
        holes = [(x, y, d, hole_net(x, y)) for x, y, d in pth] + [(x, y, d, None) for x, y, d in npth]
        for x, y, d, hnet in holes:
            if hnet == pnet:
                continue
            gap = dist[ij(x, y)] - d / 2
            plane_worst = min(plane_worst, gap)
            if gap < PLANE_MIN:
                plane_bad += 1
                print(f"PLANE CLEARANCE {ly} ({pnet}): hole of {hnet} at ({x:.2f}, {y:.2f}) {gap:.3f} mm")
    print(f"inner planes: closest foreign hole {plane_worst:.3f} mm from plane copper (min {PLANE_MIN}), "
          f"{plane_bad} violations")
    bad += plane_bad

    # --- mounting holes: the plate boss and the body boss press on the board round each screw hole, so no
    # copper on F or B within B.MOUNT_KEEPOUT of a hole centre; on the inner layers only the plane itself
    # (under the laminate, cut back round the hole) may reach into it. Measured on the Gerbers.
    ko, ko_bad = B.MOUNT_KEEPOUT, 0
    reach = ko + 3.0                             # look 3 mm past the keep-out to report the closest copper
    ko_near = dict.fromkeys(LAYERS, math.inf)
    # the plane copper by its net (the electrical check above): every piece connected to the plane net
    plane_px = {ly: np.isin(lab[ly], [c for c in range(1, ncomp[ly] + 1) if comp_nets.get(find((ly, c))) == {pnet}])
                for ly, pnet in B.PLANES.items()}
    r = int(reach / PX)

    def near_mm(v):
        return f"{v:.2f} mm" if v < math.inf else f"none within {reach:.1f} mm"

    for mx, my in B.MOUNTS:
        i0, j0 = ij(mx, my)
        ii, jj = np.mgrid[max(i0 - r, 0):min(i0 + r + 1, HPX), max(j0 - r, 0):min(j0 + r + 1, WPX)]
        d = np.hypot(jj * PX - mx, ii * PX - my)
        inside = d <= ko
        here = dict.fromkeys(LAYERS, math.inf)   # this hole's closest copper
        for ly in LAYERS:
            win = ras[ly][ii, jj] & (d <= reach)
            if win.any():
                here[ly] = float(d[win].min())
                ko_near[ly] = min(ko_near[ly], here[ly])
            hit = win & inside
            if not hit.any():
                continue
            if ly in B.PLANES:                   # the plane's own copper is fine, nothing else
                if (hit & ~plane_px[ly][ii, jj]).any():
                    ko_bad += 1
                    print(f"MOUNT KEEP-OUT {ly}: copper other than the {B.PLANES[ly]} plane within {ko} mm "
                          f"of the hole at ({mx}, {my})")
            else:
                ko_bad += 1
                print(f"MOUNT KEEP-OUT {ly}: copper {d[hit].min():.2f} mm from the hole centre at ({mx}, {my}) "
                      f"(keep-out {ko})")
        print(f"  mounting hole at ({mx:g}, {my:g}): closest copper F {near_mm(here['F'])}, B {near_mm(here['B'])}, "
              f"inner planes {near_mm(min(here[ly] for ly in B.PLANES))}")
    ko_near["planes"] = min(ko_near[ly] for ly in B.PLANES)
    near = {ly: near_mm(v) for ly, v in ko_near.items()}
    print(f"mount keep-out: {len(B.MOUNTS)} holes, closest copper to a hole centre F {near['F']}, B {near['B']} "
          f"(min {ko}); inner planes from {near['planes']}, plane copper only; {ko_bad} violations")
    bad += ko_bad

    # --- LED cutouts (milled through the board, in Edge_Cuts): no copper inside on any layer, the inner planes
    # pulled back by PLANE_MIN and more, on the Gerbers; the outer layers to the design items in the DRC below
    cut_ops = [("region", rounded_rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, r)) for x, y, w, h, r in B.CUTOUTS]
    cut_px = draw_ops(cut_ops)
    cut_dist = ndimage.distance_transform_edt(~cut_px) * PX
    cut_bad, cut_near = 0, {}
    for ly, img in ras.items():
        d = cut_dist[img]
        cut_near[ly] = float(d.min()) if d.size else math.inf
        lim = PLANE_MIN if ly in B.PLANES else 0.0
        if cut_near[ly] < lim + PX / 2 - 1e-6 or (img & cut_px).any():
            cut_bad += 1
            print(f"LED CUTOUT {ly}: copper {cut_near[ly]:.2f} mm from a cutout (min {lim})")
    print(f"LED cutouts: {len(B.CUTOUTS)}, closest copper F {cut_near['F']:.2f}, B {cut_near['B']:.2f}, planes "
          f"{min(cut_near[ly] for ly in B.PLANES):.2f} mm (raster {PX}); {cut_bad} violations")
    bad += cut_bad

    # --- the outer copper Gerbers and the drill files hold the design primitives, and the geometric clearance DRC
    # on those ---
    bad += copper_model(pads, rd["segments"], rd["vias"])
    bad += drill_model(pads, rd["vias"])
    items = copper_items(pads, rd["segments"], rd["vias"])
    worst, viol = 9, 0
    for i, j in near_pairs([it[1] for it in items], 0.5):
        a, b = items[i], items[j]
        if a[0] != b[0] or a[2] == b[2]:
            continue
        dd = item_dist(a[1], b[1])
        worst = min(worst, dd)
        if dd < B.CLEAR - 1e-6:
            viol += 1
            print("CLEARANCE", round(dd, 3), a[2], a[3], b[2], b[3], a[0])
    for it in items:
        bb = bbox(it[1])
        # the board edge: bounding boxes against the outline's straight sides, exact on the primitives, so the
        # tolerance is rounding alone (as in precheck.py). At the rounded corners the corner holes' keep-outs
        # reach to within 0.11 mm of the outline, less than any trace is wide.
        e = min(bb[0], bb[1], B.W - bb[2], B.H - bb[3])
        if e < B.EDGE_CLEAR - 1e-6:
            viol += 1; print("NEAR EDGE", it[2], it[3], round(e, 3))
        for (x, y, dd) in B.NPTH:
            dist = item_dist(it[1], ("cap", x, y, x, y, dd / 2))
            if dist < 0.15:
                viol += 1; print("NEAR NPTH", it[2], it[3], round(dist, 2))
        for (x, y, w, h, _r) in B.CUTOUTS:        # JLCPCB: copper 0.2 mm from a routed edge
            if not boxes_near(bb, (x - w / 2, y - h / 2, x + w / 2, y + h / 2), 1.0):
                continue
            dist = item_dist(it[1], ("rect", x - w / 2, y - h / 2, x + w / 2, y + h / 2, 0.0))
            if dist < ROUTED_EDGE_CU - 1e-6:
                viol += 1; print("NEAR LED CUTOUT", it[2], it[3], round(dist, 3))
    # hole to hole, by net (JLCPCB: 0.5 mm between holes of different nets, 0.254 mm on the same net).
    # Plated holes carry their net; NPTH and mounting holes count as their own net. Slots are capsules.
    holes = [(("cap", v[0], v[1], v[0], v[1], v[4] / 2), v[2]) for v in rd["vias"]]
    for p in pads:
        if p.drill and not p.slot:
            holes.append((("cap", p.x, p.y, p.x, p.y, p.drill / 2), p.net or "NC:" + p.name))
        elif p.slot:
            w, ln = p.slot
            d = (ln - w) / 2
            g = ("cap", p.x, p.y - d, p.x, p.y + d, w / 2) if p.h >= p.w else ("cap", p.x - d, p.y, p.x + d, p.y, w / 2)
            holes.append((g, p.net or "NC:" + p.name))
    for k, (x, y, dd) in enumerate(list(B.NPTH) + [(mx, my, B.MOUNT_HOLE) for (mx, my) in B.MOUNTS]):
        holes.append((("cap", x, y, x, y, dd / 2), f"NPTH{k}"))
    hmin = {True: (9, None), False: (9, None)}           # same net?, (gap, where)
    for i in range(len(holes)):
        gi, ni = holes[i]
        for j in range(i + 1, len(holes)):
            gj, nj = holes[j]
            if abs(gi[1] - gj[1]) > 3 or abs(gi[2] - gj[2]) > 3:
                continue
            gap = item_dist(gi, gj)
            same = ni == nj
            if gap < hmin[same][0]:
                hmin[same] = (gap, (round(gi[1], 2), round(gi[2], 2), ni, nj))
            if gap < (0.254 if same else 0.5) - 1e-6:
                viol += 1; print("HOLES TOO CLOSE", ni, nj, (round(gi[1], 2), round(gi[2], 2)), round(gap, 3))
    print(f"holes: closest different nets {hmin[False][0]:.3f} mm (min 0.5), "
          f"same net {hmin[True][0]:.3f} mm (min 0.254)")
    print(f"DRC: worst copper clearance {worst:.3f} mm, {viol} violations")
    hole_bad = holes_and_paste(pads, rd["vias"], pth, npth)
    hole_bad += mask_dams(pads)
    hole_bad += hand_solder(pads)
    hole_bad += decoupling(pads, rd["segments"], rd["vias"])
    hole_bad += cap_vias(pads, rd["vias"])
    hole_bad += lengths(pads, rd["segments"])
    hole_bad += j1_shell(ras["B"], pads)
    hole_bad += usb_protection(ras, pth, pads, rd["segments"], rd["vias"])
    hole_bad += silk_clear(pth, npth)
    hole_bad += edge_cuts()
    hole_bad += silk_edge()
    hole_bad += cathode_bars(pads)
    parts, pin_bad = assembly_files()
    pin_bad += footprints(pads, parts)
    pin_bad += tht_footprints(pads, parts)
    sys.exit(1 if (bad or floating or viol or hole_bad or pin_bad) else 0)
