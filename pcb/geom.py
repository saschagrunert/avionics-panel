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
