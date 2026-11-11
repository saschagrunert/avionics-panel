"""Routes the rev 1 board. Usage: python3 run_route.py [seed] [x]

Writes routed.json; with any second argument routed_<seed>.json instead, so several seeds can run in parallel."""
import json
import math
import random
import re
import sys
import time

import board as B
import numpy as np
import route as R
from geom import detour_limits, net_lengths, usb_lengths

seed = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
pads = B.build()
nets = sorted({p.net for p in pads if p.net})
PLANE_NETS = set(B.PLANES.values())


def is_fixed_end(p):
    """Pads already tied to a breakout point by pre-routed copper: not router terminals."""
    if p.net == "QSPI_SS" and p.name != "R_BOOT.1":
        return True
    return (p.name in B.BUS_PADS or p.name in B.JOINED or bool(re.match(r"U1\.\d+$", p.name))
            or (p.name.startswith("J1.") and not p.name.startswith(("J1.E", "J1.SH"))))

bynet = {}
for p in pads:
    if is_fixed_end(p):
        continue
    if p.net and p.net not in PLANE_NETS and p.net not in B.PREROUTED:
        bynet.setdefault(p.net, []).append(p)

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
if seed:
    rnd.shuffle(direct)
    rnd.shuffle(matrix)

# MCU-local nets first (short, critical), then the long ones. The two USB-C lines are not among them: they lead
# the nets the rip-up below may reorder, so when they take the north fan-out's only way out to the west
# (GP12, GP13, GP15) those nets move ahead of them on the next pass
PRIO = ["QSPI_SD2", "QSPI_SCLK", "QSPI_SD0", "QSPI_SD1", "QSPI_SD3", "QSPI_SS",
        "BOOT_SW", "USB_DM", "USB_DP", "CC1", "CC2", "VBUS"]
first = [n for n in PRIO if n in bynet]
rest = [n for n in local + direct + matrix if n not in first]
keyloc = [n for n in rest if n.startswith("K") and n.endswith("_K")]
others = [n for n in rest if n not in keyloc]
MATRIX_ORDER = [f"GP{i}" for i in range(12)] + [f"GP{i}" for i in range(29, 17, -1)] + ["GP16", "GP17"]
mfirst = [n for n in MATRIX_ORDER if n in bynet and n not in first]
if seed % 2:
    mfirst.reverse()
others = [n for n in others if n not in mfirst]
order = keyloc + first + mfirst + others


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
        if net in B.BUS_NETS or net == "QSPI_SS":
            smask = np.zeros((2, R.NY, R.NX), bool)
            src = B.FIXED_SEGS if net == "QSPI_SS" else [c for c in B.BUS_COPPER if c[0] != "via"]
            srcv = B.FIXED_VIAS if net == "QSPI_SS" else [c[1:] for c in B.BUS_COPPER if c[0] == "via"]
            for (x1, y1, x2, y2, ly, n, w) in src:
                if n == net:
                    tmp = np.zeros((R.NY, R.NX), np.int8)
                    R.stamp_capsule(tmp, x1, y1, x2, y2, w / 2, 1)
                    smask[0 if ly == "F" else 1] |= tmp.astype(bool)
            for (x, y, n, d, _dr) in srcv:
                if n == net:
                    tmp = np.zeros((R.NY, R.NX), np.int8)
                    R.stamp_capsule(tmp, x, y, x, y, d / 2, 1)
                    smask[0] |= tmp.astype(bool); smask[1] |= tmp.astype(bool)
        if not router.route_tree(net, ps, smask):
            failed.append(net)
    return router, failed


def merge_fixed_vias(segments, vias):
    """Drops router vias that overlap a pre-placed via of the same net (redundant, and the drills would be too
    close) and links whatever met them to the fixed via on both layers."""
    fixed = [tuple(v) for v in B.FIXED_VIAS]
    segments, keep = [list(s) for s in segments], []
    for v in map(tuple, vias):
        near = [f for f in fixed
                if v not in fixed and f[2] == v[2] and math.hypot(f[0] - v[0], f[1] - v[1]) < (f[3] + v[3]) / 2]
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
    with open(f"routed_{seed}.json" if len(sys.argv) > 2 else "routed.json", "w") as f:
        json.dump({"segments": segments, "vias": vias, "failed": failed}, f)
    L = sum(net_lengths(router.segments).values())
    print(f"seed {seed}: failed {failed} detours {detour} vias {len(vias)} length {L:.0f} mm  "
          f"({time.time()-t0:.0f}s)")
