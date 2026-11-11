"""Independent checks on the generated Gerbers:
1. rasterise each Gerber file (own minimal parser)
2. electrical check: shorts and opens per net, using the rasterised copper + drills
3. geometric clearance DRC on the design primitives
4. renders of front and back
5. pin order of the bottom-side parts (mirrored footprints)
6. drills and annular rings against JLCPCB's limits, no hole at or in an SMD pad or a paste opening (bar a
   pin-in-paste hole in its own opening), paste on every assembled pad and nowhere else
7. solder mask dams (between openings on the mask Gerbers) against JLCPCB's black minimum, and every opening
   clear of its pad by the mask's registration
8. copper path from every RP2040 supply pin to its nearest decoupling capacitor, one capacitor of its own per
   IOVDD pin over the outer layers, and every decoupling capacitor with its own plane vias
9. routed length of every net against its shortest tree (no detours), USB D+ / D- length and skew
10. JLCPCB's footprint of every bottom-side part on our pads at its CPL rotation (pad numbers, positions)
11. no copper on F or B within the mounting-hole keep-out (standoff end, body boss), only the plane inside
12. no exposed SMD pad of another net near a through-hole pad (solder bridges; hand-soldered in either variant)
13. JLCPCB's footprint of every through-hole part against our holes (positions, drills reported), and at its
   top-side CPL position and rotation (full variant) on our holes pin by pin
14. no copper on B under J1's shell but J1's own pads
15. the legend clear of mask openings and holes, and inside the board outline by SILK_EDGE
16. USB protection: the ESD array in line on D+ and D- right behind J1, the damping resistor and the fuse in
    VBUS ahead of every load
(precheck.py checks the placement before routing: fixed copper clearances and the bottom-side part bodies.)
"""
import functools
import heapq
import json
import math
import re

import board as B
import numpy as np
from geom import (
    DETOUR_FACTOR,
    DETOUR_SLACK,
    USB_MAX,
    USB_SKEW,
    bbox,
    boxes_near,
    detour_limits,
    item_dist,
    net_lengths,
    pad_geom,
    pt_seg,
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


def read_drill(fname):
    tools, holes, t = {}, [], None
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
            n = max(1, round(math.hypot(x1 - x0, y1 - y0) / 0.1))      # a G85 slot: circles along it
            holes += [(x0 + (x1 - x0) * i / n, B.H - (y0 + (y1 - y0) * i / n), t) for i in range(n + 1)]
    return holes


def pin_order(pads):
    """A part on the bottom, seen from the top, is mirrored: its pins must number clockwise. Rotating
    cannot fix a footprint that is not mirrored, so check every bottom part with 3+ numbered pins (the
    shoelace sum is positive for clockwise in y-down coordinates), and the USB-C contact order."""
    bad = 0
    byref = {}
    for p in pads:
        m = re.match(r"(\w+)\.(\d+)$", p.name)
        if m:
            byref.setdefault(m.group(1), {})[int(m.group(2))] = (p.x, p.y)
    for ref, value, _lcsc, _x, _y, _rot, side in B.PARTS:
        pins = byref.get(ref, {})
        if side != "bottom" or len(pins) < 3:
            continue
        pts = [pins[k] for k in sorted(pins)]
        area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=True))
        ok = area > 0
        bad += not ok
        verdict = "clockwise, OK" if ok else "COUNTER-CLOCKWISE: footprint not mirrored"
        print(f"  {ref:4s} {value:20s} {len(pts):2d} pins  {verdict}")
    j = {p.name: (p.x, p.y) for p in pads if p.name.startswith("J1.")}
    oy = (j["J1.SH1b"][1] + j["J1.SH-1b"][1]) / 2 - j["J1.A1B12"][1]      # pad row -> opening (front shell pads)
    ax = j["J1.A1B12"][0] - j["J1.B1A12"][0]
    ok = -oy * ax < 0                      # cross(opening, B1->A1): > 0 for the top-view footprint, < 0 mirrored
    bad += not ok
    print(f"  J1   USB-C contact order   {'mirrored, OK' if ok else 'NOT MIRRORED: D+/D- swapped'}")
    return bad


# Footprint fit: every bottom-side part's JLCPCB library footprint (footprints/<LCSC>.json, saved from JLC's
# EasyEDA library by footprints/fetch.py, so this runs offline) is placed the way JLCPCB places a bottom part
# (board.py docstring: seen from the top, mirrored left to right, then turned clockwise by the CPL rotation).
# Every JLC pad must land on our pad of the same number, centres within FP_POS_TOL and every edge within
# FP_EDGE_TOL, and our part may have no pad JLC's lacks. A wrong rotation or pin assignment puts a pad of
# another number there or misses by a pitch (0.4 mm on the RP2040, 1.27 mm on the flash); the tolerances take
# our own land sizes (diodes, SOT-23, 0603, 0402 differ from JLC's by up to 0.22 mm at an edge).
FP_POS_TOL, FP_EDGE_TOL = 0.15, 0.25
FP_PIN = {"C81598": {"K": "1", "A": "2"}, "C2040": {"EP": "57"},          # our pad name -> JLC's pad number
          "C165948": {"SH1a": "1", "SH1b": "2", "SH-1b": "3", "SH-1a": "4"}}


def jlc_place(x, y, rot):
    """A JLC footprint point (top view, y down) on the bottom side at CPL rotation rot, seen from the top."""
    a = math.radians(rot)
    return (-x * math.cos(a) - y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


@functools.cache
def jlc_pads(lcsc):
    """the pads of JLC's footprint of one part (footprints/<LCSC>.json), read once per part type."""
    with open(f"footprints/{lcsc}.json") as f:
        return json.load(f)["pads"]


def footprint_fit(ref, lcsc, cx, cy, rot, ours):
    """(worst centre offset, worst edge offset, problems) of JLC's footprint at rotation rot on our pads."""
    ref_pads = jlc_pads(lcsc)
    alias = FP_PIN.get(lcsc, {})
    mine = {alias.get(pin, pin): p for pin, p in ours.items()}
    worst_c, worst_e, bad = 0.0, 0.0, []
    for num, x, y, w, h in ref_pads:
        dx, dy = jlc_place(x, y, rot)
        X, Y = cx + dx, cy + dy
        if round(rot) % 180 == 90:
            w, h = h, w
        p = mine.get(num)
        if p is None:
            bad.append(f"JLC pad {num} has no pad {ref}.{num} on the board"); continue
        c = math.hypot(p.x - X, p.y - Y)
        e = max(abs(p.x - p.w / 2 - (X - w / 2)), abs(p.x + p.w / 2 - (X + w / 2)),
                abs(p.y - p.h / 2 - (Y - h / 2)), abs(p.y + p.h / 2 - (Y + h / 2)))
        worst_c, worst_e = max(worst_c, c), max(worst_e, e)
        if c > FP_POS_TOL or e > FP_EDGE_TOL:
            near = min((q for q in mine.values()), key=lambda q: math.hypot(q.x - X, q.y - Y))
            bad.append(f"JLC pad {num} lands at ({X:.2f}, {Y:.2f}), {c:.2f} mm from {p.name} ({p.net}), "
                       f"edges off by {e:.2f}; nearest is {near.name} ({near.net})")
    extra = set(mine) - {r[0] for r in ref_pads}
    bad += [f"{ref}.{n} is not in JLC's footprint" for n in sorted(extra)]
    return worst_c, worst_e, bad


def footprints(pads):
    """Every bottom-side part against JLC's footprint at its CPL rotation (see FP_POS_TOL above)."""
    bad = 0
    byref = {}
    for p in pads:
        ref, pin = p.name.split(".", 1)
        if not re.fullmatch(r"[FV]\d+|E", pin):
            byref.setdefault(ref, {})[pin] = p
    types = {}
    for ref, value, lcsc, x, y, rot, side in B.PARTS:
        if side != "bottom":
            continue
        t = types.setdefault(lcsc, {"value": value, "refs": [], "rots": set(), "c": 0.0, "e": 0.0})
        t["refs"].append(ref); t["rots"].add(rot % 360)
        c, e, probs = footprint_fit(ref, lcsc, x, y, rot, byref.get(ref, {}))
        t["c"], t["e"] = max(t["c"], c), max(t["e"], e)
        if probs:
            bad += 1
            fits = [r for r in (0, 90, 180, 270) if not footprint_fit(ref, lcsc, x, y, r, byref.get(ref, {}))[2]]
            more = f"; {len(probs) - 2} more" if len(probs) > 2 else ""
            print(f"FOOTPRINT {ref} ({lcsc}) at CPL rotation {rot}: " + "; ".join(probs[:2]) + more
                  + f". Rotations that fit: {fits or 'none'}")
    for lcsc, t in sorted(types.items(), key=lambda kv: kv[1]["refs"][0]):
        refs = t["refs"][0] + (f" and {len(t['refs']) - 1} more" if len(t["refs"]) > 1 else "")
        rots = "/".join(str(r) for r in sorted(t["rots"]))
        print(f"  {lcsc:9s} {t['value']:20s} {refs:22s} CPL {rots:7s} centres within {t['c']:.3f} mm, "
              f"edges within {t['e']:.3f} mm")
    print(f"footprints: {len(types)} JLC footprints on {sum(len(t['refs']) for t in types.values())} bottom-side "
          f"parts (tolerance {FP_POS_TOL} centre, {FP_EDGE_TOL} edge), {bad} problems")
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
# bridge from an iron-soldered pin to an SMD pad of another net is a short that is hard to see and to clear (an
# LED's GND pad 0.28 mm from its resistor's GPIO pad was one). J1's four shell tabs (pin-in-paste) are filled
# with solder by hand from the top too, and the excess comes out on the bottom (docs/mechanics.md). Every exposed
# SMD pad of another net keeps HAND_SMD_MIN of copper from every hand-soldered pad: room for the iron's tip and a
# fillet.
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


# Through-hole parts: JLC's footprint (footprints/<LCSC>.json, "holes" and "npth") against our holes, twice.
# By position only, as a hand-soldered part is placed: for each of the four rotations the hole pattern is moved
# onto ours by its centroid; it fits when every JLC hole lands on one of our holes of the part, centres within
# FP_POS_TOL, with none of ours left over, and every unplated JLC hole on one of ours. The drills are reported
# side by side: ours follow the part's datasheet.
# And as JLCPCB places it in the full variant (Standard assembly, both sides): JLC's footprint at the top-side
# CPL position and rotation (board.cpl, as make_bom.py writes it; JLC's top convention: seen from the top, the
# footprint turned counter-clockwise by the rotation, its origin on the CPL position). Every JLC hole must land
# on our hole of the pin TH_PIN names for it, within FP_POS_TOL, every unplated one on one of ours, and none of
# ours may be left over. A wrong rotation misses the holes or, on a symmetric hole pattern, puts a pin on the
# wrong hole: the LEDs' cathode on the anode pad, an encoder's A on B.
TH_PIN = {                                  # JLC's pin number -> our pins it may land on
    # key: pins 1-2 and 3-4 are joined inside, so 0 and 180 are the same switch (the 6.5 x 4.5 pattern misses at 90)
    "C589907": dict.fromkeys("1234", ("A", "B", "C", "D")),
    "C19270361": {"1": ("A2",), "2": ("C2",), "3": ("B2",), "4": ("D",), "5": ("E",), "6": ("A",), "7": ("C",),
                  "8": ("B",), "9": ("MP-1",), "10": ("MP1",)},     # JLC's symbol: 1-3 and 6-8 A C B, 4 / 5 switch
    "C160841": {"5": ("PUSH",), "6": ("COM",), "7": ("ENCB",), "8": ("ENCA",), "9": ("ECOM",), "10": ("GND",),
                "A": ("A",), "B": ("B",), "C": ("C",), "D": ("D",)},
    "C2895466": {"1": ("K",), "2": ("A",)},                         # amber: pin 1 is the cathode
    "C2895458": {"1": ("A",), "2": ("K",)},                         # white: pin 1 is the anode
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
    for num, hx, hy, _d, _slot in fp["holes"]:
        dx, dy = jlc_top(hx, hy, rot)
        X, Y = cx + dx, cy + dy
        p = min(ours, key=lambda q, X=X, Y=Y: math.hypot(q.x - X, q.y - Y))
        c = math.hypot(p.x - X, p.y - Y)
        worst = max(worst, c)
        if c > FP_POS_TOL:
            bad.append(f"JLC pin {num} lands at ({X:.2f}, {B.H - Y:.2f}), {c:.2f} mm from the nearest hole {p.name}")
        elif p.name.split(".", 1)[1] not in pins.get(num, ()):
            bad.append(f"JLC pin {num} lands on {p.name} ({p.net}), not on {'/'.join(pins.get(num, ('?',)))}")
        used.add(p.name)
    for hx, hy, _d in fp["npth"]:
        dx, dy = jlc_top(hx, hy, rot)
        c = min((math.hypot(nx - cx - dx, ny - cy - dy) for nx, ny, _d in B.NPTH), default=9.0)
        worst = max(worst, c)
        if c > FP_POS_TOL:
            bad.append(f"JLC's unplated hole lands {c:.2f} mm from ours")
    bad += [f"{p.name} has no JLC pin" for p in ours if p.name not in used]
    return worst, bad


def tht_footprints(pads):
    bad = 0
    types = {}
    for ref, value, lcsc, x, y, rot, side in B.PARTS:
        if side != "top":
            continue
        with open(f"footprints/{lcsc}.json") as f:
            fp = json.load(f)
        ours = [p for p in pads if p.name.split(".")[0] == ref and p.drill]
        npth = [(nx, ny, d) for nx, ny, d in B.NPTH if math.hypot(nx - x, ny - y) < 12.0]
        fits = []
        for r in (0, 90, 180, 270):
            jl = [(h[0], *jlc_top(h[1], h[2], r), h[3]) for h in fp["holes"]]
            if len(jl) != len(ours):
                continue
            ox = sum(p.x for p in ours) / len(ours) - sum(h[1] for h in jl) / len(jl)
            oy = sum(p.y for p in ours) / len(ours) - sum(h[2] for h in jl) / len(jl)
            worst, used = 0.0, set()
            for _n, hx, hy, _d in jl:
                p = min(ours, key=lambda q, hx=hx, hy=hy: math.hypot(q.x - hx - ox, q.y - hy - oy))
                used.add(p.name)
                worst = max(worst, math.hypot(p.x - hx - ox, p.y - hy - oy))
            for hx, hy, _d in fp["npth"]:
                qx, qy = jlc_top(hx, hy, r)
                worst = max(worst, min((math.hypot(nx - qx - ox, ny - qy - oy) for nx, ny, _d in npth), default=9.0))
            if worst <= FP_POS_TOL and len(used) == len(ours):
                fits.append((r, worst))
        t = types.setdefault(lcsc, {"value": value, "refs": [], "worst": 0.0, "rots": set(), "ours": set(),
                                    "jlc": {h[3] for h in fp["holes"]}, "cpl": set(), "cw": 0.0, "off": set()})
        t["refs"].append(ref)
        t["ours"] |= {p.drill for p in ours}
        if not fits:
            bad += 1
            print(f"THROUGH-HOLE FOOTPRINT {ref} ({lcsc}): JLC's holes do not fit ours at any rotation")
            continue
        t["worst"] = max(t["worst"], min(w for _r, w in fits))
        t["rots"] |= {r for r, _w in fits}
        _ref, mx, my, layer, crot = B.cpl(ref, x, y, rot, side)
        cx, cy = mx, B.H - my                                   # back from JLC's frame (y up) to the board's
        cw, probs = cpl_fit(ref, lcsc, fp, cx, cy, crot, ours)
        if layer != "Top":
            raise ValueError(f"{ref}: through-hole part not on the top in the CPL")
        t["cpl"].add(crot); t["cw"] = max(t["cw"], cw); t["off"].add((round(cx - x, 2), round(cy - y, 2)))
        if probs:
            bad += 1
            ok = [r for r in (0, 90, 180, 270) if not cpl_fit(ref, lcsc, fp, cx, cy, r, ours)[1]]
            more = f"; {len(probs) - 2} more" if len(probs) > 2 else ""
            print(f"TOP CPL {ref} ({lcsc}) at CPL ({mx:.3f}, {my:.3f}) rotation {crot}: " + "; ".join(probs[:2]) + more
                  + f". Rotations that fit there: {ok or 'none'}")
    def mm(v):
        return "/".join(f"{d:g}" for d in sorted(v))
    for lcsc, t in sorted(types.items(), key=lambda kv: kv[1]["refs"][0]):
        refs = t["refs"][0] + (f" and {len(t['refs']) - 1} more" if len(t["refs"]) > 1 else "")
        rots, cpl = ("/".join(map(str, sorted(t[k]))) or "-" for k in ("rots", "cpl"))
        off = "/".join(f"{dx:+g},{dy:+g}" for dx, dy in sorted(t["off"]))
        print(f"  {lcsc:9s} {t['value']:20s} {refs:16s} fits at {rots:7s} centres within {t['worst']:.3f} mm; "
              f"drills ours {mm(t['ours'])}, JLC {mm(t['jlc'])}; top CPL {cpl}, origin {off} from the part "
              f"(y down), pins within {t['cw']:.3f} mm")
    print(f"through-hole footprints: {len(types)} JLC footprints on {sum(len(t['refs']) for t in types.values())} "
          f"top-side parts (tolerance {FP_POS_TOL}), by position and at the full variant's top-side CPL, "
          f"{bad} problems")
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
        for i in range(len(ops)):
            for j in range(i + 1, len(ops)):
                if not boxes_near(bbs[i], bbs[j], 0.2):
                    continue
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
    planed = planes and net in B.PLANES.values()
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
            if planed:
                edge(("pad", p.name, "B"), ("plane", p.x, p.y), 0.0)
    for x1, y1, x2, y2, ly, n, w in segments:
        if n == net:
            a, b = ("pt", ly, round(x1, 4), round(y1, 4)), ("pt", ly, round(x2, 4), round(y2, 4))
            edge(a, b, math.hypot(x2 - x1, y2 - y1))
            items[ly].append((("cap", x1, y1, x2, y2, w / 2), [(a, (x1, y1)), (b, (x2, y2))]))
    for x, y, n, d, _dr in vias:
        if n == net:
            edge(("via", x, y, "F"), ("via", x, y, "B"), 0.0)
            if planed:
                edge(("via", x, y, "B"), ("plane", x, y), 0.0)
            for ly in "FB":
                items[ly].append((("cap", x, y, x, y, d / 2), [(("via", x, y, ly), (x, y))]))
    for its in items.values():                 # touching copper: join the anchors through the contact
        bbs = [bbox(g) for g, _a in its]
        for i, (ga, anchors_a) in enumerate(its):
            for j in range(i + 1, len(its)):
                gb, anchors_b = its[j]
                if not boxes_near(bbs[i], bbs[j], 1e-3) or item_dist(ga, gb) > 1e-3:
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


def cut_islands(ras, pth, cut):
    """The copper islands with the pads `cut` removed from the bottom copper: F and B labelled on their own, joined
    through every plated hole. Returns the labels and find(), which maps (layer, label) to its island."""
    b = ras["B"] & ~ndimage.binary_dilation(draw_ops(pad_ops(cut)))
    lab = {"F": ndimage.label(ras["F"])[0], "B": ndimage.label(b)[0]}
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for x, y, _d in pth:
        f, k = lab["F"][ij(x, y)], lab["B"][ij(x, y)]
        if f and k:
            parent[find(("F", f))] = find(("B", k))
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


def silk_edge():
    """Every legend shape inside the board outline (the Edge_Cuts Gerber) by SILK_EDGE. Measured on the Gerber
    vertices: the outline is convex, so a shape's closest point to it is a vertex of a region, or an end of a line
    or a dot less its radius. Not on the raster, which ends at the board edge and would not see legend beyond it."""
    edge = [(op[2], op[3]) for op in gerber_ops("avionics-Edge_Cuts.gko") if op[0] == "line"]
    inside = Path([a for a, _b in edge] + [edge[-1][1]])
    ax, ay, bx, by = (np.array(v) for v in zip(*[(*a, *b) for a, b in edge], strict=True))
    ux, uy = bx - ax, by - ay
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
            u = np.clip(((px - ax) * ux + (py - ay) * uy) / (ux * ux + uy * uy), 0, 1)
            d = np.hypot(px - (ax + u * ux), py - (ay + u * uy)).min(axis=1)
            d = np.where(inside.contains_points(q), d, -d) - r      # negative: beyond the outline
            i = int(d.argmin())
            worst[side] = min(worst[side], float(d[i]))
            if d[i] < SILK_EDGE - 1e-6:
                bad += 1
                print(f"LEGEND AT THE BOARD EDGE on {side} at ({q[i, 0]:.2f}, {q[i, 1]:.2f}), {d[i]:.2f} mm inside "
                      "the outline")
    print(f"legend to board outline: closest F {worst['F']:.2f} mm, B {worst['B']:.2f} mm (min {SILK_EDGE}); "
          f"{bad} problems")
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
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

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

    # --- mounting holes: the standoff end and the body boss press on the board round each screw hole, so no
    # copper on F or B within B.MOUNT_KEEPOUT of a hole centre; on the inner layers only the plane itself
    # (under the laminate, cut back round the hole) may reach into it. Measured on the Gerbers.
    ko, ko_bad = B.MOUNT_KEEPOUT, 0
    reach = ko + 3.0                             # look 3 mm past the keep-out to report the closest copper
    ko_near = dict.fromkeys(LAYERS, math.inf)
    # the plane copper by its net (the electrical check above): every piece connected to the plane net
    plane_px = {ly: np.isin(lab[ly], [c for c in range(1, ncomp[ly] + 1) if comp_nets.get(find((ly, c))) == {pnet}])
                for ly, pnet in B.PLANES.items()}
    r = int(reach / PX)
    for mx, my in B.MOUNTS:
        i0, j0 = ij(mx, my)
        ii, jj = np.mgrid[max(i0 - r, 0):min(i0 + r + 1, HPX), max(j0 - r, 0):min(j0 + r + 1, WPX)]
        d = np.hypot(jj * PX - mx, ii * PX - my)
        inside = d <= ko
        for ly in LAYERS:
            win = ras[ly][ii, jj] & (d <= reach)
            if win.any():
                ko_near[ly] = min(ko_near[ly], float(d[win].min()))
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
    ko_near["planes"] = min(ko_near[ly] for ly in B.PLANES)
    near = {ly: f"{v:.2f} mm" if v < math.inf else f"none within {reach:.1f} mm" for ly, v in ko_near.items()}
    print(f"mount keep-out: closest copper to a mounting-hole centre F {near['F']}, B {near['B']} (min {ko}); "
          f"inner planes from {near['planes']}, plane copper only; {ko_bad} violations")
    bad += ko_bad

    # --- geometric clearance DRC (outer layers) ---
    with open("design.json") as f:
        items = json.load(f)["items"]
    worst, viol = 9, 0

    bbs = [bbox(it[1]) for it in items]
    for i in range(len(items)):
        a, ba = items[i], bbs[i]
        for j in range(i + 1, len(items)):
            b, bb = items[j], bbs[j]
            if a[0] != b[0] or a[2] == b[2] or not boxes_near(ba, bb, 0.5):
                continue
            dd = item_dist(a[1], b[1])
            worst = min(worst, dd)
            if dd < B.CLEAR - 1e-6:
                viol += 1
                print("CLEARANCE", round(dd, 3), a[2], a[3], b[2], b[3], a[0])
    for it, bb in zip(items, bbs, strict=True):
        e = min(bb[0], bb[1], B.W - bb[2], B.H - bb[3])
        if e < B.EDGE_CLEAR - 0.05:
            viol += 1; print("NEAR EDGE", it[2], it[3], round(e, 2))
        for (x, y) in B.MOUNTS:
            dist = item_dist(it[1], ("cap", x, y, x, y, B.MOUNT_HOLE / 2))
            if dist < 0.4:
                viol += 1; print("NEAR MOUNT", it[2], round(dist, 2))
        for (x, y, dd) in B.NPTH:
            dist = item_dist(it[1], ("cap", x, y, x, y, dd / 2))
            if dist < 0.15:
                viol += 1; print("NEAR NPTH", it[2], it[3], round(dist, 2))
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
    hole_bad += silk_edge()
    pin_bad = pin_order(pads)
    print(f"pin order (bottom parts): {pin_bad} problems")
    pin_bad += footprints(pads)
    pin_bad += tht_footprints(pads)
    for ly, img in ras.items():
        np.save(f"raster{ly}.npy", img)
    import sys
    sys.exit(1 if (bad or floating or viol or hole_bad or pin_bad) else 0)
