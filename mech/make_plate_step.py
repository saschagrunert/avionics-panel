"""CNC front plate for the Avionics Panel rev 1: STEP model for JLCCNC plus a 2D drawing of the back.

6061 aluminium, milled from 12 mm stock, black anodised: a 4 mm web and five round bosses on its back (at the
four corner mounts and in the middle of the key field), each tapped M3 from its end face, 10.55 mm high in all, and
a tongue on its back edge over the USB-C socket (stack.USB_TONGUE), shorter than the bosses. Front face (+Z) is
flat: laser marking and UV print follow the DXF from make_plate_art.py, in the same coordinates. Back face (Z = 0):
pockets for the encoder and RANGE bodies, the bosses, which stand down to the PCB, and the tongue. The front is
faced first; then everything else is machined from the back in one setup, so the 4 mm web is never faced while it
is held on its bosses.

Coordinates: origin at the bottom-left corner of the plate seen from the front, X right, Y up, mm.
Needs pythonocc-core (nix-shell nix/shells.nix -A gen, from the repository root).
"""
import sys
import textwrap
from pathlib import Path

from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pcb"))
import board as B
import stack as S
from occ_util import box, cut, cyl, fuse, move, revolve, rrect_prism, volume, write_step

OVH, T = S.OVH, S.PLATE_T
PW, PH = B.W + 2 * OVH, B.H + 2 * OVH
LIGHT_TOL = f"+{S.LIGHT_HOLE_TOL[0]}/-{S.LIGHT_HOLE_TOL[1]:g}"      # light holes: never smaller
KEY_TOL = f"+{S.KEY_HOLE_TOL[0]}/-{S.KEY_HOLE_TOL[1]:g}"            # key holes, after anodising
BOSS, TAP, TONGUE = S.BOSS, S.TAP, S.USB_TONGUE
STOCK = 12.0                     # plate stock, mm: web and bosses are 10.55 (up to 10.7), the next common size
# The drawing: an A3 page, split between the plan view (above) and the text block (below). The plan view keeps at
# least DRAWING_MIN of the page height, so a longer text block fails the build instead of shrinking it unreadable.
PAGE = (16.54, 11.69)            # inches, landscape
DRAWING_MIN = 0.45


def P(x, y):
    """board coordinates (y down) -> plate coordinates (stack.plate_xy)."""
    return S.plate_xy(x, y, B.H)


def tap_hole():
    """the tapped hole of a boss as the cutter, its mouth at z = 0 going up: the countersink, the tap drill and its
    118 degree point (the thread itself is the drawing's callout)."""
    r, c, d = TAP["drill"] / 2, TAP["cham"], TAP["depth"]
    return revolve([(0, -0.5), (r + c + 0.5, -0.5), (r + c, 0), (r, c), (r, d), (0, d + TAP["point"])])


def build():
    plate = rrect_prism(PW / 2, PH / 2, PW, PH, B.CORNER_R + OVH, 0.0, T)
    h = BOSS["h"]
    for (mx, my) in B.MOUNTS:                                       # bosses down to the PCB top, all five
        plate = fuse(plate, cyl(BOSS["d"] / 2, -h, 0.01, *P(mx, my)))
    tx, ty = P(B.USB_X, -OVH)                                       # the tongue, flush with the back edge
    plate = fuse(plate, box(tx - TONGUE["w"] / 2, ty - TONGUE["d"], -TONGUE["h"], tx + TONGUE["w"] / 2, ty, 0.01))
    tools, features = [], []
    e = 0.5                                                 # through tools overshoot both faces
    for y in B.ROWS:
        for x in B.COLS:
            tools.append(rrect_prism(*P(x, y), *S.KEY_HOLE, -e, T + e))
    features.append(("key hole", f"{S.KEY_HOLE[0]} x {S.KEY_HOLE[1]} {KEY_TOL} R{S.KEY_HOLE[2]}",
                     f"through, corner R{S.KEY_HOLE_R_MAX} max",
                     len(B.ROWS) * len(B.COLS)))
    for name in ("ALTHDG", "FREQ", "FMS"):
        cx, cy = P(*getattr(B, name))
        tools.append(cyl(S.SHAFT_HOLE / 2, -e, T + e, cx, cy))
        w, hh, r, dpt = S.EC11_POCKET
        tools.append(rrect_prism(cx, cy, w, hh, r, -e, dpt))
    features.append(("encoder hole", f"dia {S.SHAFT_HOLE}", "through", 3))
    features.append(("encoder pocket", f"{S.EC11_POCKET[0]} x {S.EC11_POCKET[1]} R{S.EC11_POCKET[2]}",
                     f"{S.EC11_POCKET[3]} +0/-{S.POCKET_TOL} deep from back, floor corner R{S.POCKET_FLOOR_R} max", 3))
    cx, cy = P(*B.RANGE)
    tools.append(cyl(S.RANGE_HOLE / 2, -e, T + e, cx, cy))
    tools.append(cyl(S.RANGE_POCKET[0] / 2, -e, S.RANGE_POCKET[1], cx, cy))
    features.append(("RANGE hole", f"dia {S.RANGE_HOLE}", "through", 1))
    features.append(("RANGE pocket", f"dia {S.RANGE_POCKET[0]}",
                     f"{S.RANGE_POCKET[1]} +0/-{S.POCKET_TOL} deep from back, floor corner R{S.POCKET_FLOOR_R} max", 1))
    for name, ((lx, ly), _, _) in B.LEDS.items():
        tools.append(cyl(S.LIGHT_HOLE / 2, -e, T + e, *P(lx, ly)))
        features.append((f"{name} light hole", f"dia {S.LIGHT_HOLE} {LIGHT_TOL}", "through", 1))
    for (mx, my) in B.MOUNTS:
        tools.append(move(tap_hole(), *P(mx, my), -h))
    features.append(("boss", f"dia {BOSS['d']}, root R{BOSS['root_r']} max",
                     f"{BOSS['h']} +-{BOSS['h_tol']} high from back, end face flat", len(B.MOUNTS)))
    features.append(("tapped hole", f"{TAP['thread']} in each boss",
                     f"full thread {TAP['full']} min, drill {TAP['drill']} x {TAP['depth']} deep", len(B.MOUNTS)))
    features.append(("tongue", f"{TONGUE['w']} +-{TONGUE['tol']} x {TONGUE['d']}, root R{TONGUE['root_r']} max",
                     f"{TONGUE['h']} +-{TONGUE['tol']} long from back, outer face flush with plate edge", 1))
    return cut(plate, *tools), features


def main():
    shape, features = build()
    if not BRepCheck_Analyzer(shape).IsValid():
        raise RuntimeError("invalid solid")
    nf = 0; ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        nf += 1; ex.Next()
    vol = volume(shape)
    print(f"plate {PW:.1f} x {PH:.1f} x {T:.1f} mm web, bosses {BOSS['h']} high, {vol / 1000:.1f} cm3, "
          f"{vol * 2.70e-3:.0f} g (6061), {nf} faces; from {STOCK:.0f} mm stock, "
          f"{(PW * PH * STOCK - vol) / 1000:.0f} cm3 milled off")
    write_step(shape, "avionics-panel-rev1-plate")
    drawing(features, vol)


def drawing_notes(vol):
    """the notes on the drawing, one paragraph each."""
    t_min = S.PLATE_T - S.PLATE_T_TOL
    skin = BOSS["h"] - BOSS["h_tol"] + t_min - TAP["depth"] - TAP["point"]
    return [
        f"Material 6061 aluminium, machined from {STOCK:.0f} mm plate: the web {S.PLATE_T:.1f} +-"
        f"{S.PLATE_T_TOL} mm thick before anodising, the {len(B.MOUNTS)} bosses and the tongue on its back, "
        f"{S.BOSS['h'] + S.PLATE_T:.2f} mm high in all (the front may be faced). Outline {PW:.1f} x {PH:.1f} mm, "
        f"corner R{B.CORNER_R + OVH:.1f}. Volume {vol / 1000:.1f} cm3. Units mm, general tolerance ISO 2768-m; "
        f"flatness {S.PLATE_FLAT} over the whole web after bead blasting and anodising (the plate is held only at its "
        "bosses).",
        "Front face (+Z in the STEP) is flat: no pockets or fastener holes on the front, and no chamfers beyond "
        "the edge break below. Machining order: face the front first, then machine the back (pockets, bosses, "
        "tongue, holes), so the web is never faced while it is held on its bosses.",
        f"Positions of the {len(B.MOUNTS)} bosses and their tapped holes, of the pockets, of the tongue and of all "
        f"through holes: +-{S.POS_TOL['plate']} to each other (the key caps, the board, the parts in the pockets, "
        "the screws and the body's slot must line up).",
        f"Bosses: dia {BOSS['d']} +-{BOSS['d_tol']}, {BOSS['h']} +-{BOSS['h_tol']} high from the back face of the web "
        "(required: they set the plate height), "
        f"each end face flat and square to its hole; root R{BOSS['root_r']} max.",
        f"Tongue on the back edge: {TONGUE['w']} +-{TONGUE['tol']} wide, {TONGUE['d']} thick with its outer face "
        f"flush with the plate's edge, {TONGUE['h']} +-{TONGUE['tol']} long from the back face of the web (it ends "
        f"short of the bosses); root R{TONGUE['root_r']} max. It closes the body's slot over the USB-C socket.",
        f"Threads: {len(B.MOUNTS)} x {TAP['thread']}, one in each boss from its end face, full thread at least "
        f"{TAP['full']} deep, tap drill dia {TAP['drill']} x {TAP['depth']} deep plus the drill point, {TAP['cham']} x "
        f"90 deg countersink: at least {skin:.2f} mm of metal stays in front of the drill point. The threads must "
        f"gauge {TAP['thread']} after anodising: mask them while anodising, or cut them again afterwards. The boss "
        "end faces may be anodised or bare, but all of them alike.",
        f"Pocket depths +0, never deeper: at least {t_min - S.RANGE_POCKET[1]:.2f} mm of material must stay to the "
        "front face under every pocket; nothing may break through or mark the front face.",
        f"Encoder pockets and RANGE pocket: floor corner (inside radius between wall and floor) at most "
        f"{S.POCKET_FLOOR_R} mm; the parts' top corners come within about 0.2 mm of the pocket walls.",
        "Finish: black anodised, matte (bead blasted before anodising); the pockets may be anodised or bare, but "
        "all pockets alike (all anodised or all bare). Anodising rack contacts in one of the M3 threads (cut it "
        "again afterwards), on the back face, on the boss end faces or inside the pockets; never on the front face, "
        "the outline or the key holes.",
        "Marking on the front per avionics-panel-rev1-plate.dxf, same origin (bottom-left, seen from the front): "
        "layer LASER = laser marking, layer UV_AMBER = UV print in JLCCNC's standard orange. Layer CUT = outline "
        "and through holes for reference. DXF units mm; fill closed contours even-odd (letter counters are "
        "separate contours).",
        f"Key holes {S.KEY_HOLE[0]} x {S.KEY_HOLE[1]} {KEY_TOL} after anodising (never smaller: the key caps "
        f"centre the board in them), corners R{S.KEY_HOLE[2]}, R{S.KEY_HOLE_R_MAX} max. Light holes {LIGHT_TOL} "
        "(never smaller: the light pipes slide in them). "
        f"Deburr all edges: edge break at most {S.FRONT_BREAK} on the front outline and hole edges; on the back "
        f"edges of the key holes {S.KEY_BACK_BREAK} to {S.KEY_BACK_BREAK_MAX} (a lead-in for the key caps); the light "
        f"holes' back edges sharp, deburred only ({S.LIGHT_HOLE_BACK_BREAK} max: the light pipes' shoulders bear "
        "there).",
    ]


def drawing(features, vol):
    """A3 drawing of the back face: pockets, bosses, threads and the tongue, plus notes for the order."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    fig = plt.figure(figsize=PAGE)
    notes = drawing_notes(vol)
    # the text block under the drawing, one (text, font size, bold, monospace) per line, in figure coordinates, laid
    # out from its own height; the drawing takes the page above it
    lh = 1.3 / 72 / fig.get_figheight()                    # line height as a figure fraction, per point of font size
    block = [("Features", 8.5, True, False)]
    block += [(f"{n:<20s} {s:<32s} {d:<60s} x{q}", 7.0, False, True) for n, s, d, q in features]
    block += [("Notes", 8.5, True, False)]
    for n in notes:
        block += [(("- " if i == 0 else "  ") + line, 7.0, False, False)
                  for i, line in enumerate(textwrap.wrap(n, 270))]
    text_h = sum(fs * lh for _, fs, _, _ in block) + 2 * 0.5 * 8.5 * lh     # half a line before each heading
    bottom, top = 0.02, 0.95
    ax = fig.add_axes([0.04, bottom + text_h + 0.02, 0.92, top - bottom - text_h - 0.02])
    ax.set_aspect("equal"); ax.axis("off")
    # seen from the BACK: mirror X so the drawing matches what the machinist sees
    def M(x, y):
        return (PW - x, y)

    def rr(x, y, w, h, r, **kw):
        mx, my = M(x, y)
        ax.add_patch(FancyBboxPatch((mx - w / 2 + r, my - h / 2 + r), w - 2 * r, h - 2 * r,
                                    boxstyle=f"round,pad={r}", **kw))

    rr(PW / 2, PH / 2, PW, PH, B.CORNER_R + OVH, fc="#f2f2f2", ec="k", lw=1.2)
    for y in B.ROWS:
        for x in B.COLS:
            rr(*P(x, y), *S.KEY_HOLE, fc="white", ec="k", lw=0.6)
    w, h, r, d = S.EC11_POCKET
    for name in ("ALTHDG", "FREQ", "FMS"):
        cx, cy = P(*getattr(B, name))
        rr(cx, cy, w, h, r, fc="#c9dcf0", ec="#1f5fa0", lw=0.8, hatch="///")
        ax.add_patch(Circle(M(cx, cy), S.SHAFT_HOLE / 2, fc="white", ec="k", lw=0.6))
    lx, ly = M(*P(*B.FREQ))                         # one label for all three, above the plate (clear of the keys)
    ax.annotate(f"3 x pocket {w} x {h} R{r}, {d} +0/-{S.POCKET_TOL} deep (encoders)", (lx, ly + h / 2),
                xytext=(M(*P(B.USB_X, 0))[0] - TONGUE["w"] / 2 - 2.0, PH + 3.5), ha="right", va="center",
                fontsize=6.5, arrowprops=dict(arrowstyle="-", lw=0.5))   # ends short of the tongue's leader
    cx, cy = P(*B.RANGE)
    ax.add_patch(Circle(M(cx, cy), S.RANGE_POCKET[0] / 2, fc="#c9dcf0", ec="#1f5fa0", lw=0.8, hatch="///"))
    ax.add_patch(Circle(M(cx, cy), S.RANGE_HOLE / 2, fc="white", ec="k", lw=0.6))
    ax.annotate(f"pocket dia {S.RANGE_POCKET[0]}\n{S.RANGE_POCKET[1]} +0/-{S.POCKET_TOL} deep",
                M(cx, cy + S.RANGE_POCKET[0] / 2 + 0.5),
                ha="center", va="bottom", fontsize=6.5)
    for (lx, ly), _, _ in B.LEDS.values():
        ax.add_patch(Circle(M(*P(lx, ly)), S.LIGHT_HOLE / 2, fc="white", ec="k", lw=0.6))
    for (mx, my) in B.MOUNTS:                                        # bosses (raised) with their tapped holes
        px, py = M(*P(mx, my))
        ax.add_patch(Circle((px, py), BOSS["d"] / 2, fc="#9aa3ad", ec="k", lw=0.8))
        ax.add_patch(Circle((px, py), TAP["drill"] / 2, fc="white", ec="k", lw=0.6))
        ax.add_patch(Circle((px, py), 1.5, fc="none", ec="k", lw=0.4, ls=(0, (2, 1.5))))   # thread major dia
    tx, ty = M(*P(B.USB_X, -OVH))                                    # the tongue on the back edge
    ax.add_patch(Rectangle((tx - TONGUE["w"] / 2, ty - TONGUE["d"]), TONGUE["w"], TONGUE["d"], fc="#9aa3ad", ec="k",
                           lw=0.8))
    ax.annotate(f"tongue {TONGUE['w']} +-{TONGUE['tol']} x {TONGUE['d']}, {TONGUE['h']} +-{TONGUE['tol']} long "
                "from the back face", (tx, ty - TONGUE["d"] / 2), xytext=(tx - TONGUE["w"] / 2, PH + 7.0), ha="left",
                va="center", fontsize=6.5, arrowprops=dict(arrowstyle="-", lw=0.5))
    px, py = M(*P(*B.MOUNTS[0]))                                     # one label for all bosses, above the plate
    ax.annotate(f"{len(B.MOUNTS)} x boss dia {BOSS['d']}, {BOSS['h']} +-{BOSS['h_tol']} high, {TAP['thread']} full "
                f"thread {TAP['full']} min (drill {TAP['drill']} x {TAP['depth']})", (px, py + BOSS["d"] / 2),
                xytext=(px, PH + 3.5), ha="right" if px > PW / 2 else "left", va="center", fontsize=6.5,
                arrowprops=dict(arrowstyle="-", lw=0.5))
    ax.set_xlim(-6, PW + 6); ax.set_ylim(-4, PH + 9.5)
    ax.set_title("Avionics Panel rev 1 front plate, seen from the BACK (machined side)", fontsize=11, loc="left")

    y = bottom + text_h
    texts = []
    for t, fs, bold, mono in block:
        if bold:
            y -= 0.5 * 8.5 * lh
        texts.append(fig.text(0.04, y, t, fontsize=fs, va="top", weight="bold" if bold else "normal",
                              family="monospace" if mono else None))
        y -= fs * lh
    check_layout(fig, ax, texts)
    fig.savefig("avionics-panel-rev1-plate-drawing.pdf", metadata={"CreationDate": None})   # reproducible
    print(f"drawing written: {len(notes)} notes in {len(block)} lines, drawing {ax.get_position().height:.2f} of the "
          f"page (min {DRAWING_MIN})")


def check_layout(fig, ax, texts):
    """The drawing as the machinist gets it: every line of the text block and every label on the page, no line of
    the text block on a label, no two labels on each other, and the plan view at least DRAWING_MIN of the page high.
    A note that falls off the page or under a label would be lost; a squeezed plan view unreadable."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    page = fig.bbox
    labels = [*ax.texts, ax.title]
    bad = []
    if ax.get_position().height < DRAWING_MIN:
        bad.append(f"the plan view is {ax.get_position().height:.2f} of the page high (min {DRAWING_MIN}): the "
                   "notes take too much room")
    for t in texts + labels:
        bb = t.get_window_extent(r)
        if bb.x0 < page.x0 or bb.y0 < page.y0 or bb.x1 > page.x1 or bb.y1 > page.y1:
            bad.append(f"off the page: {t.get_text()[:60]!r}")
    for t in texts:
        bb = t.get_window_extent(r)
        for lab in labels:
            if bb.overlaps(lab.get_window_extent(r)):
                bad.append(f"{t.get_text()[:40]!r} overlaps the label {lab.get_text()[:40]!r}")
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if a.get_window_extent(r).overlaps(b.get_window_extent(r)):
                bad.append(f"the labels {a.get_text()[:40]!r} and {b.get_text()[:40]!r} overlap")
    if bad:
        raise SystemExit("plate drawing layout: " + "; ".join(bad))


if __name__ == "__main__":
    main()
