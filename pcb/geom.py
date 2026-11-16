"""Edge-to-edge distances of capsules / rectangles, the stroke width of a legend, the copper paths of a net and
the routed lengths (used by make.py, check.py, precheck.py and run_route.py)."""
import heapq
import itertools
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


def copper_graph(net, pads, segments, vias, planes=()):
    """Nodes (pad centres, segment ends, vias, plane points) and edges (copper length) of one net: its pads, its
    segments and vias, joined where they touch, and through its plane if planes (the plane nets) names it; without
    planes the outer-layer copper and the vias alone."""
    on_plane = net in planes
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
    """{node: shortest copper length from start} over a copper_graph()"""
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


# ---------------- routed length against the shortest tree (check.py and run_route.py) ----------------
# A routed net may be DETOUR_FACTOR times as long as the shortest 8-direction tree over its pads, plus
# DETOUR_SLACK for getting out of the RP2040's fan-out and round the parts in the way. In the routing before
# this check the well-routed nets came to at most 1.6 times their tree (GP17) and 22 mm on a 10 mm tree (the
# hand-routed VBUS); the UNIT light (GP15) went round the whole board, 341 mm on a 58 mm tree.
DETOUR_FACTOR, DETOUR_SLACK = 1.5, 15.0

# JLCPCB publishes no legend-to-outline figure. It keeps copper 0.2 mm from a routed edge and mills the outline
# to +-0.2 mm: legend closer than SILK_EDGE to the outline may be clipped or run off the edge (make.py places
# the legend inside it, check.py measures it).
SILK_EDGE = 0.3
# The edge with JLCPCB's rail (the long edge away from J1, at y = board.H) is V-cut, to +-0.4 mm, and the groove
# reaches about 0.12 mm in from it on each face: the legend keeps SILK_VCUT from it.
SILK_VCUT = 0.6


def thin_parts(shape, width, arc=16):
    """Where a shapely shape (text outlines, a legend) is thinner than width: a point in each of its pieces that
    comes apart, vanishes or loses a counter when it is eroded by width / 2 (a stroke or a neck under width), and
    in each part a disc of that diameter cannot reach, bar corners and tips (parts under width x width in area)."""
    out = []
    for q in getattr(shape, "geoms", [shape]):
        if q.geom_type != "Polygon" or q.is_empty:
            continue
        core = q.buffer(-width / 2, quad_segs=arc)
        if core.geom_type != "Polygon" or core.is_empty or len(core.interiors) != len(q.interiors):
            out.append(q.representative_point())
            continue
        lost = q.difference(core.buffer(width / 2, quad_segs=arc))
        out += [t.representative_point() for t in getattr(lost, "geoms", [lost]) if t.area >= width * width]
    return [(pt.x, pt.y) for pt in out]


def stroke_width(shape, most, tol=1e-3):
    """The width of the thinnest stroke or neck of a shapely shape, up to `most`: the largest width, to within
    tol below it, at which thin_parts() finds nothing."""
    lo, hi = 0.0, most
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if thin_parts(shape, mid) else (mid, hi)
    return lo


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


# USB: each line along its signal path, from a USB-C contact through the ESD array (in at the pad on J1's side,
# out at the other) and the 27 R resistor to the RP2040's pin, at most USB_MAX, and D+ within USB_SKEW of D- on
# the same row of contacts: a plug uses one row, A or B, by the way it is turned, and the other row's contact is a
# stub. All trace on each line's nets, stubs included, stays within USB_MAX as well. Vias count 0 mm, on the
# paths and in the totals: D+ crosses four vias from row A (two from row B) and has four on its nets, D- two, about
# 6.4 and 3.2 mm of barrel in the 1.6 mm board left out. The limits catch router detours, not a timing budget:
# full speed (12 Mbit/s, 4 ns edges) tolerates far more.
USB_MAX, USB_SKEW = 50.0, 10.0
# per line: its legs, (net, pads in order along it), {row} for the contact's row
USB_PATHS = {"D+": (("USB_DP_C", ("J1.{row}6", "U4.6", "U4.1", "R_DP.2")), ("USB_DP", ("R_DP.1", "U1.47"))),
             "D-": (("USB_DN_C", ("J1.{row}7", "U4.4", "U4.3", "R_DM.2")), ("USB_DM", ("R_DM.1", "U1.46")))}
USB_NETS = {"D+": ("USB_DP_C", "USB_DP"), "D-": ("USB_DN_C", "USB_DM")}


def usb_paths(pads, segments, vias):
    """({row: {"D+": mm, "D-": mm}} along the signal paths of USB_PATHS, for the rows A and B of J1's contacts,
    within USB_MAX and USB_SKEW): each leg the shortest copper path between its pads' centres (none: inf)."""
    layer = {p.name: p.layers[0] for p in pads}
    graphs = {net: copper_graph(net, pads, segments, vias) for legs in USB_PATHS.values() for net, _ in legs}
    out = {}
    for row in "AB":
        out[row] = {}
        for line, legs in USB_PATHS.items():
            total = 0.0
            for net, names in legs:
                nodes = [("pad", n, layer[n]) for n in (n.format(row=row) for n in names)]
                for a, b in itertools.pairwise(nodes):
                    total += shortest(graphs[net], a).get(b, math.inf)
            out[row][line] = total
    ok = all(max(r.values()) <= USB_MAX and abs(r["D+"] - r["D-"]) <= USB_SKEW for r in out.values())
    return out, ok


def usb_totals(length):
    """{"D+": mm, "D-": mm}: all trace on each line's nets (USB_NETS), its stubs too, from net_lengths()."""
    return {k: sum(length.get(n, 0.0) for n in nets) for k, nets in USB_NETS.items()}


def detour_limits(pads, nets):
    """{net: (shortest tree, longest acceptable routed length)} for the given nets, over their pad centres:
    one pass over the pads for all of them."""
    pts = {}
    for p in pads:
        if p.net in nets:
            pts.setdefault(p.net, []).append((p.x, p.y))
    trees = {n: tree_length(pts.get(n, ())) for n in nets}
    return {n: (t, DETOUR_FACTOR * t + DETOUR_SLACK) for n, t in trees.items()}
