"""Edge-to-edge distances of capsules / rectangles (used by make.py, check.py, precheck.py)."""
import math


def pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def seg_seg_dist(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = ccw((x3, y3), (x4, y4), (x1, y1)), ccw((x3, y3), (x4, y4), (x2, y2))
    d3, d4 = ccw((x1, y1), (x2, y2), (x3, y3)), ccw((x1, y1), (x2, y2), (x4, y4))
    if (d1 * d2 < 0) and (d3 * d4 < 0):
        return 0.0
    return min(pt_seg(x1, y1, x3, y3, x4, y4), pt_seg(x2, y2, x3, y3, x4, y4),
               pt_seg(x3, y3, x1, y1, x2, y2), pt_seg(x4, y4, x1, y1, x2, y2))


def item_dist(a, b):
    """Edge-to-edge distance of two items: ("cap", x1,y1,x2,y2,r) or ("rect", x0,y0,x1,y1,0)."""
    def edges(it):
        if it[0] == "cap":
            return [it[1:5]], it[5]
        x0, y0, x1, y1 = it[1:5]
        return [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)], 0.0

    def inside(it, px, py):
        return it[0] == "rect" and it[1] <= px <= it[3] and it[2] <= py <= it[4]
    ea, ra = edges(a)
    eb, rb = edges(b)
    if inside(a, b[1], b[2]) or inside(b, a[1], a[2]):
        return -1.0
    return min(seg_seg_dist(p, q) for p in ea for q in eb) - ra - rb


def rounded_rect(x0, y0, x1, y1, r, n=12):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def pad_geom(p):
    """A board.Pad's copper as a geometry item."""
    return ("rect",) + p.rect() + (0.0,) if p.shape == "rect" else ("cap",) + p.capsule()


def bbox(g):
    """Bounding box (x0, y0, x1, y1) of a geometry item."""
    if g[0] == "rect":
        return tuple(g[1:5])
    return min(g[1], g[3]) - g[5], min(g[2], g[4]) - g[5], max(g[1], g[3]) + g[5], max(g[2], g[4]) + g[5]


def boxes_near(a, b, margin):
    """True when two bounding boxes come within margin of each other: the prefilter before item_dist."""
    return not (a[0] > b[2] + margin or b[0] > a[2] + margin or a[1] > b[3] + margin or b[1] > a[3] + margin)


def near_pairs(geoms, margin):
    """Index pairs (i, j), i < j, of the geometry items whose bounding boxes come within margin of each other."""
    bbs = [bbox(g) for g in geoms]
    for i, a in enumerate(bbs):
        for j in range(i + 1, len(bbs)):
            if boxes_near(a, bbs[j], margin):
                yield i, j


def copper_items(pads, segments, vias):
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


# ---------------- routed length against the shortest tree (check.py and run_route.py) ----------------
# A routed net may be DETOUR_FACTOR times as long as the shortest 8-direction tree over its pads, plus
# DETOUR_SLACK for getting out of the RP2040's fan-out and round the parts in the way. In the routing before
# this check the well-routed nets came to at most 1.6 times their tree (GP17) and 22 mm on a 10 mm tree (the
# hand-routed VBUS); the UNIT light (GP15) went round the whole board, 341 mm on a 58 mm tree.
DETOUR_FACTOR, DETOUR_SLACK = 1.5, 15.0


def octilinear(a, b):
    """Shortest 8-direction (0 / 45 / 90 degree) path between two points: the best the grid router can do."""
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return dx + dy - (2 - math.sqrt(2)) * min(dx, dy)


def tree_length(points):
    """Length of the minimum spanning tree over the points, octilinear distances (Prim)."""
    pts = sorted(set(points))
    if len(pts) < 2:
        return 0.0
    best = {p: octilinear(pts[0], p) for p in pts[1:]}
    total = 0.0
    while best:
        p = min(best, key=best.get)
        total += best.pop(p)
        for q in best:
            best[q] = min(best[q], octilinear(p, q))
    return total


def net_lengths(segments):
    """Trace length per net of a list of (x1, y1, x2, y2, layer, net, ...) segments."""
    out = {}
    for s in segments:
        out[s[5]] = out.get(s[5], 0.0) + math.hypot(s[2] - s[0], s[3] - s[1])
    return out


# USB: all trace on D+ (USB_DP_C from the two USB-C contacts to R_DP, USB_DP on to the RP2040) and on D- at
# most USB_MAX each, and within USB_SKEW of each other. Full speed (12 Mbit/s, 4 ns edges) would tolerate far
# more; the limits catch a router detour on the one pair that has any timing at all.
USB_MAX, USB_SKEW = 50.0, 10.0
USB_LINES = {"D+": ("USB_DP_C", "USB_DP"), "D-": ("USB_DN_C", "USB_DM")}


def usb_lengths(length):
    """({"D+": mm, "D-": mm}, within USB_MAX and USB_SKEW) from net_lengths()."""
    usb = {k: sum(length.get(n, 0.0) for n in nets) for k, nets in USB_LINES.items()}
    return usb, max(usb.values()) <= USB_MAX and abs(usb["D+"] - usb["D-"]) <= USB_SKEW


def detour_limits(pads, nets):
    """{net: (shortest tree, longest acceptable routed length)} for the given nets, over their pad centres:
    one pass over the pads for all of them."""
    pts = {}
    for p in pads:
        if p.net in nets:
            pts.setdefault(p.net, []).append((p.x, p.y))
    trees = {n: tree_length(pts.get(n, ())) for n in nets}
    return {n: (t, DETOUR_FACTOR * t + DETOUR_SLACK) for n, t in trees.items()}
