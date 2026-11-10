"""Placement check before routing: clearance between all fixed copper (pads, pre-routed segments, vias)."""
import board as B
from geom import bbox, boxes_near, item_dist, pad_geom

pads = B.build()
items = []
for p in pads:
    for ly in p.layers:
        items.append((ly, pad_geom(p), p.net or "NC:" + p.name, p.name))
for (x1, y1, x2, y2, ly, net, w) in B.FIXED_SEGS:
    items.append((ly, ("cap", x1, y1, x2, y2, w / 2), net, "seg"))
for (x, y, net, d, _dr) in B.FIXED_VIAS:
    for ly in "FB":
        items.append((ly, ("cap", x, y, x, y, d / 2), net, "via"))
for (x, y, d) in B.NPTH:
    for ly in "FB":
        items.append((ly, ("cap", x, y, x, y, d / 2 + 0.05), "NPTH", "npth"))

bb = [bbox(i[1]) for i in items]
bad = 0
for i in range(len(items)):
    for j in range(i + 1, len(items)):
        a, b = items[i], items[j]
        if a[0] != b[0] or a[2] == b[2] or not boxes_near(bb[i], bb[j], 0.3):
            continue
        d = item_dist(a[1], b[1])
        if d < B.CLEAR - 1e-6:
            bad += 1
            print(f"{d:6.3f} {a[0]} {a[2]}/{a[3]} <-> {b[2]}/{b[3]}  at {[round(v,2) for v in a[1][1:3]]}")
# edge
for it, b in zip(items, bb, strict=True):
    if min(b[0], b[1], B.W - b[2], B.H - b[3]) < B.EDGE_CLEAR - 0.01:
        bad += 1; print("EDGE", it[2], it[3])
print("placement problems:", bad)
raise SystemExit(1 if bad else 0)
