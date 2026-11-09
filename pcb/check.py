"""Independent checks on the generated Gerbers:
1. rasterise each Gerber file (own minimal parser)
2. electrical check: shorts and opens per net, using the rasterised copper + drills
3. geometric clearance DRC on the design primitives
4. renders of front and back
5. pin order of the bottom-side parts (mirrored footprints)
"""
import json
import math
import re

import board as B
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

PX = 0.05
WPX, HPX = int(B.W / PX) + 1, int(B.H / PX) + 1


def raster(fname):
    img = Image.new("L", (WPX, HPX), 0)
    dr = ImageDraw.Draw(img)
    aps, cur, pos, region, dark = {}, None, (0, 0), None, True
    with open("gerbers/" + fname) as f:
        txt = f.read()

    def P(x, y):
        return (x / 1e6 / PX, (B.H - y / 1e6) / PX)

    for tok in re.findall(r"%[^%]*%|[^*%\n]+\*", txt):
        tok = tok.strip()
        m = re.match(r"%ADD(\d+)([COR]),([\d.]+)(?:X([\d.]+))?\*%", tok)
        if m:
            aps[int(m.group(1))] = (m.group(2), float(m.group(3)), float(m.group(4) or 0))
            continue
        if tok == "%LPD*%":
            dark = True; continue
        if tok == "%LPC*%":
            dark = False; continue
        if tok == "G36*":
            region = []; continue
        if tok == "G37*":
            if len(region) > 2:
                dr.polygon(region, fill=255 if dark else 0)
            region = None; continue
        m = re.match(r"D(\d+)\*$", tok)
        if m and int(m.group(1)) >= 10:
            cur = aps[int(m.group(1))]; continue
        m = re.match(r"X(-?\d+)Y(-?\d+)D0([123])\*", tok)
        if m:
            x, y, op = int(m.group(1)), int(m.group(2)), m.group(3)
            p = P(x, y)
            col = 255 if dark else 0
            if region is not None:
                if op == "2":
                    if len(region) > 2:
                        dr.polygon(region, fill=col)
                    region = [p]
                else:
                    region.append(p)
            elif op == "3":
                k, a, b = cur
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
            elif op == "1":
                r = cur[1] / 2 / PX
                dr.line([pos, p], fill=col, width=max(1, int(round(2 * r))))
                for q in (pos, p):
                    dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=col)
            pos = p
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

    # --- geometric clearance DRC (outer layers) ---
    from geom import item_dist, seg_seg_dist  # noqa
    with open("design.json") as f:
        items = json.load(f)["items"]
    worst, viol = 9, 0

    def bbox(it):
        g = it[1]
        if g[0] == "rect":
            return g[1], g[2], g[3], g[4]
        r = g[5]
        return min(g[1], g[3]) - r, min(g[2], g[4]) - r, max(g[1], g[3]) + r, max(g[2], g[4]) + r
    bbs = [bbox(it) for it in items]
    for i in range(len(items)):
        a, ba = items[i], bbs[i]
        for j in range(i + 1, len(items)):
            b, bb = items[j], bbs[j]
            if a[0] != b[0] or a[2] == b[2]:
                continue
            if ba[0] > bb[2] + 0.5 or bb[0] > ba[2] + 0.5 or ba[1] > bb[3] + 0.5 or bb[1] > ba[3] + 0.5:
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
    from geom import item_dist as _dist
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
            gap = _dist(gi, gj)
            same = ni == nj
            if gap < hmin[same][0]:
                hmin[same] = (gap, (round(gi[1], 2), round(gi[2], 2), ni, nj))
            if gap < (0.254 if same else 0.5) - 1e-6:
                viol += 1; print("HOLES TOO CLOSE", ni, nj, (round(gi[1], 2), round(gi[2], 2)), round(gap, 3))
    print(f"holes: closest different nets {hmin[False][0]:.3f} mm (min 0.5), "
          f"same net {hmin[True][0]:.3f} mm (min 0.254)")
    print(f"DRC: worst copper clearance {worst:.3f} mm, {viol} violations")
    pin_bad = pin_order(pads)
    print(f"pin order (bottom parts): {pin_bad} problems")
    for ly, img in ras.items():
        np.save(f"raster{ly}.npy", img)
    import sys
    sys.exit(1 if (bad or floating or viol or pin_bad) else 0)
