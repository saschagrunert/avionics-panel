"""Routes the rev 1 board. Usage: python3 run_route.py [seed] [x]

Writes routed.json; with any second argument routed_<seed>.json instead, so several seeds can run in parallel.
The file is written only when every net is routed, none with a detour and the USB pair within its limits (what
check.py accepts); otherwise the file is left as it is and the exit status is 1."""
import json
import math
import random
import re
import sys
import time

import board as B
import numpy as np
import route as R
from geom import detour_limits, item_dist, net_lengths, pad_geom, usb_lengths

seed = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
pads = B.build()
nets = sorted({p.net for p in pads if p.net})
PLANE_NETS = set(B.PLANES.values())


def is_fixed_end(p):
    """Pads already tied to a breakout point by pre-routed copper: not router terminals."""
    if p.net == "QSPI_SS" and p.name != "R_BOOT.1":
        return True
    return (p.name in B.BUS_PADS or p.name in B.JOINED or bool(re.match(r"U1\.\d+$", p.name))
            or (p.name.startswith("J1.") and not p.name.startswith("J1.SH")))

bynet = {}
for p in pads:
    if is_fixed_end(p):
        continue
    if p.net and p.net not in PLANE_NETS and p.net not in B.PREROUTED:
        bynet.setdefault(p.net, []).append(p)


def on_fixed(p):
    """True when pad p touches pre-routed copper of its net on one of its layers (a fan-out end, a line's routing
    point)."""
    g = pad_geom(p)
    return (any(n == p.net and ly in p.layers and item_dist(g, ("cap", x1, y1, x2, y2, w / 2)) <= 0
                for x1, y1, x2, y2, ly, n, w in B.FIXED_SEGS)
            or any(n == p.net and item_dist(g, ("cap", x, y, x, y, d / 2)) <= 0 for x, y, n, d, _dr in B.FIXED_VIAS))


# Nets the router grows from their pre-routed copper, like a matrix bus: every net with pre-routed copper that none
# of its router terminals is on. The chip select (its pins at the RP2040 and the flash are joined in board.py,
# R_BOOT is the router's) and VBUS_F (the fuse, C_IN, the regulator and the ESD array's VCC are joined; the UNIT
# light's resistor is the router's, wherever the line suits it). Routed among themselves alone, such terminals
# would count as routed and never reach that copper.
FIXED_NETS = {s[5] for s in B.FIXED_SEGS} | {v[2] for v in B.FIXED_VIAS}
GROWN = {net for net, ps in bynet.items()
         if net in FIXED_NETS and net not in B.BUS_NETS and not any(on_fixed(p) for p in ps)}

local, direct, matrix = [], [], []
for net, ps in bynet.items():
    pico = [p for p in ps if p.name.startswith("U1.")]
    if not pico:
        local.append(net)                     # diode <-> switch, small MCU nets
    elif len(ps) == 2:
        direct.append(net)
    else:
        matrix.append(net)

rnd = random.Random(seed)
PASSES = 25


def span(net):
    ps = bynet[net]
    return max(math.hypot(a.x - b.x, a.y - b.y) for a in ps for b in ps)


local.sort(key=span)
direct.sort(key=lambda n: -span(n))
matrix.sort(key=lambda n: span(n))

# MCU-local nets first (short, critical), then the long ones. The two USB-C lines are not among them: they lead
# the nets the rip-up below may reorder, so when they take the north fan-out's only way out to the west
# (GP12, GP13, GP15) those nets move ahead of them on the next pass. (The other QSPI lines, CC1, CC2 and VBUS
# are pre-routed in board.py: the router does not see them.)
PRIO = ["QSPI_SS", "BOOT_SW", "USB_DM", "USB_DP"]
first = [n for n in PRIO if n in bynet]
rest = [n for n in local + direct + matrix if n not in first]
keyloc = [n for n in rest if n.startswith("K") and n.endswith("_K")]
others = [n for n in rest if n not in keyloc]
MATRIX_ORDER = [f"GP{i}" for i in range(12)] + [f"GP{i}" for i in range(29, 17, -1)] + ["GP16", "GP17"]
mfirst = [n for n in MATRIX_ORDER if n in bynet and n not in first]
if seed % 2:
    mfirst.reverse()
others = [n for n in others if n not in mfirst]


def seed_stamp(smask, layers, x1, y1, x2, y2, half):
    """Marks the cells of pre-routed copper (half its width round the centre line) in the source mask on the given
    layers. The router may end a path on any of them, so none may lie beyond the copper's edge (route.seed_cells
    takes cells up to r + RES / 2 from the centre line; copper narrower than a cell keeps the cells within RES / 2):
    the path's round end then overlaps the copper by at least half its width. Stamped at w / 2, a cell could lie
    half a cell beyond the edge, where a 0.25 mm trace only touches a 0.25 mm lane at a point: an open once etched
    (check.py: thin contacts). A pad's own seed has another margin (route.route_tree)."""
    R.seed_cells(smask, layers, x1, y1, x2, y2, max(half - R.RES / 2, 0.0))


def run(order):
    router = R.Router(pads, nets)
    for (x1, y1, x2, y2, ly, net, w) in B.FIXED_SEGS:
        router.add_segment(x1, y1, x2, y2, ly, net, w)
    for (x, y, net, d, drill) in B.FIXED_VIAS:
        router.add_via(x, y, net, d, drill)
    failed = []
    for net in order:
        ps = bynet[net]
        pico = [p for p in ps if p.name.startswith("U1.")]
        if pico:
            ps = pico + [p for p in ps if p not in pico]
        smask = None
        if net in B.BUS_NETS or net in GROWN:
            smask = np.zeros((2, R.NY, R.NX), bool)
            src = B.FIXED_SEGS if net in GROWN else [c for c in B.BUS_COPPER if c[0] != "via"]
            srcv = B.FIXED_VIAS if net in GROWN else [c[1:] for c in B.BUS_COPPER if c[0] == "via"]
            for (x1, y1, x2, y2, ly, n, w) in src:
                if n == net:
                    seed_stamp(smask, [0 if ly == "F" else 1], x1, y1, x2, y2, w / 2)
            for (x, y, n, d, _dr) in srcv:
                if n == net:
                    seed_stamp(smask, [0, 1], x, y, x, y, d / 2)
        if not router.route_tree(net, ps, smask):
            failed.append(net)
    return router, failed


def merge_fixed_vias(segments, vias):
    """Drops router vias that overlap a pre-placed via of the same net or come closer to it than the copper
    clearance (redundant, and the drills would be too close: GP21's pair stood 0.1 mm apart) and links whatever met
    them to the fixed via on both layers."""
    fixed = [tuple(v) for v in B.FIXED_VIAS]
    segments, keep = [list(s) for s in segments], []
    for v in map(tuple, vias):
        near = [f for f in fixed if v not in fixed and f[2] == v[2]
                and math.hypot(f[0] - v[0], f[1] - v[1]) < (f[3] + v[3]) / 2 + B.CLEAR]
        if near:
            f = near[0]
            segments += [[v[0], v[1], f[0], f[1], ly, v[2], B.TRACE_W] for ly in "FB"]
            continue
        keep.append(list(v))
    return segments, keep


if __name__ == "__main__":
    t0 = time.time()
    fixed_first = keyloc + first
    mov = mfirst + others
    usb_c = ["USB_DN_C", "USB_DP_C"]          # the USB-C lines lead the nets the rip-up may reorder
    mov = usb_c + [n for n in mov if n not in usb_c]
    if seed >= 2:                              # diversity: shuffle the east-side nets
        east = [n for n in mov if n in [f"GP{i}" for i in range(16, 30)]]
        rnd.shuffle(east)
        it_e = iter(east)
        mov = [next(it_e) if n in east else n for n in mov]
    limit = {n: lim for n, (_tree, lim) in detour_limits(pads, bynet).items()}
    best = None
    for _it in range(PASSES):                  # rip-up and retry: nets that failed or took a detour (longer than
        router, failed = run(fixed_first + mov)   # check.py allows) go first next time, and the area round
        length = net_lengths(merge_fixed_vias(router.segments, router.vias)[0])   # them costs the others more
        detour = [n for n in bynet if n not in failed and length.get(n, 0) > limit[n]]
        if not usb_lengths(length)[1]:          # the USB pair over check.py's length or skew limit
            detour += [n for n in ("USB_DN_C", "USB_DP_C") if n not in failed + detour]
        if best is None or (len(failed), len(detour)) < (len(best[1]), len(best[2])):
            best = (router, failed, detour)
        if not failed and not detour:
            break
        for n in failed + detour:
            R.add_history(n, bynet[n])
        mov = [n for n in mov if n in failed + detour] + [n for n in mov if n not in failed + detour]
    router, failed, detour = best
    segments, vias = merge_fixed_vias(router.segments, router.vias)   # the board's vias, as routed.json has them
    L = sum(net_lengths(router.segments).values())
    print(f"seed {seed}: failed {failed} detours {detour} vias {len(vias)} length {L:.0f} mm  "
          f"({time.time()-t0:.0f}s)")
    out = f"routed_{seed}.json" if len(sys.argv) > 2 else "routed.json"
    if failed or detour:                       # a board check.py would reject: the file stays as it is
        length = net_lengths(segments)         # (the USB pair over its limits is among the detours too)
        long = sum(length.get(n, 0) > limit[n] for n in detour)
        why = [f"{n} net{'s' * (n > 1)} {what}" for n, what in ((len(failed), "not routed"), (long, "with a detour"))
               if n]
        why += [] if usb_lengths(length)[1] else ["the USB pair over its length or skew limit"]
        sys.exit(f"seed {seed}: {', '.join(why)} after {PASSES} passes, {out} not written")
    with open(out, "w") as f:
        json.dump({"segments": segments, "vias": vias}, f)
