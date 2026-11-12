"""Placement check before routing: clearance between all fixed copper (pads, pre-routed segments, vias) and to
the LED cutouts, and the bodies of the bottom-side parts (board.BODY): each at least board.BODY_GAP from every
other body and from every pad of another part, where that part's leads or pins sit."""
import re

import board as B
from geom import bbox, copper_items, item_dist, near_pairs, pad_geom

pads = B.build()
items = copper_items(pads, B.FIXED_SEGS, B.FIXED_VIAS)
for (x, y, d) in B.NPTH:
    for ly in "FB":
        items.append((ly, ("cap", x, y, x, y, d / 2 + 0.05), "NPTH", "npth"))
cg = 0.2 - B.CLEAR                         # the LED cutouts: CLEAR from this is JLCPCB's 0.2 from a routed edge
for (x, y, w, h, _r) in B.CUTOUTS:
    for ly in "FB":
        items.append((ly, ("rect", x - w / 2 - cg, y - h / 2 - cg, x + w / 2 + cg, y + h / 2 + cg, 0.0), "CUTOUT",
                      "cutout"))

bad = 0
for i, j in near_pairs([it[1] for it in items], 0.3):
    a, b = items[i], items[j]
    if a[0] != b[0] or a[2] == b[2]:
        continue
    d = item_dist(a[1], b[1])
    if d < B.CLEAR - 1e-6:
        bad += 1
        print(f"{d:6.3f} {a[0]} {a[2]}/{a[3]} <-> {b[2]}/{b[3]}  at {[round(v,2) for v in a[1][1:3]]}")
# edge
for it in items:
    b = bbox(it[1])
    if min(b[0], b[1], B.W - b[2], B.H - b[3]) < B.EDGE_CLEAR - 0.01:
        bad += 1; print("EDGE", it[2], it[3])
print("placement problems:", bad)


def rect_gap(a, b):
    """Edge-to-edge distance of two axis-parallel rectangles (x0, y0, x1, y1); 0 or -1.0 where they overlap."""
    return item_dist(("rect", *a, 0.0), ("rect", *b, 0.0))


# --- part bodies: a body on another body or on another part's pad lifts or tilts one of them (C_IN sat under
# a corner of U3 before). Pads as their bounding box; fan-out and breakout points (no pin) do not count: U1's
# F<pin> and V<pin> and the USB resistors' E (an encoder's E is its push pin and counts).
body = B.bodies()
refs = sorted(body)
pins = [(p.name.split(".")[0], p.name, p.rect() if p.shape == "rect" else bbox(pad_geom(p))) for p in pads
        if not re.fullmatch(r"U1\.[FV]\d+|R_D[MP]\.E", p.name)]
body_bad, near_body, near_pad = 0, (9.0, ""), (9.0, "")
for i, a in enumerate(refs):
    for b in refs[i + 1:]:
        g = rect_gap(body[a], body[b])
        near_body = min(near_body, (g, f"{a} / {b}"))
        if g < B.BODY_GAP - 1e-6:
            body_bad += 1; print(f"BODIES {a} and {b} {g:.3f} mm apart (min {B.BODY_GAP})")
    for ref, name, r in pins:
        if ref == a:
            continue
        g = rect_gap(body[a], r)
        near_pad = min(near_pad, (g, f"{a} / {name}"))
        if g < B.BODY_GAP - 1e-6:
            body_bad += 1; print(f"BODY OF {a} {g:.3f} mm from pad {name} (min {B.BODY_GAP})")
print(f"bodies: {len(body)} bottom-side parts, closest bodies {near_body[0]:.3f} mm ({near_body[1]}), closest body "
      f"to another part's pad {near_pad[0]:.3f} mm ({near_pad[1]}), min {B.BODY_GAP}; {body_bad} problems")
raise SystemExit(1 if bad or body_bad else 0)
