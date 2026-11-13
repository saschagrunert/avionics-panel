"""CNC front plate for the Avionics Panel rev 1: STEP model for JLCCNC plus a 2D drawing, the back with its
features and the notes on sheet 1, the front with its marking on sheet 2.

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

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pcb"))
import board as B
import make_plate_art as PA
import stack as S
from occ_util import box, cut, cyl, fuse, move, revolve, rrect_prism, volume, write_step

NAME = "avionics-panel-rev1-plate"          # the STEP, the DXF and the drawing share it: JLCCNC pairs them by name

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


def measures(shape):
    """a solid's face count, volume and extent (x0, y0, z0, x1, y1, z1)."""
    nf = 0; ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        nf += 1; ex.Next()
    box_ = Bnd_Box(); box_.SetGap(0.0)
    brepbndlib.Add(shape, box_, False)
    return nf, volume(shape), box_.Get()


def read_back(shape, name):
    """The STEP file as written, read again: its solid must be the one built. mech/check_fit.py measures the
    plate it builds from build(); this ties the ordered file to it."""
    r = STEPControl_Reader()
    if r.ReadFile(name + ".step") != IFSelect_RetDone:
        raise RuntimeError(f"{name}.step cannot be read back")
    r.TransferRoots()
    (nf, vol, ext), (nf2, vol2, ext2) = measures(shape), measures(r.OneShape())
    if nf != nf2 or abs(vol - vol2) > 1e-3 or max(abs(a - b) for a, b in zip(ext, ext2, strict=True)) > 1e-4:
        raise RuntimeError(f"{name}.step is not the solid built: {nf2} faces, {vol2:.3f} mm3, extent {ext2} against "
                           f"{nf} faces, {vol:.3f} mm3, {ext}")
    print(f"{name}.step read back: {nf2} faces, {vol2 / 1000:.2f} cm3, the solid built")


def main():
    shape, features = build()
    if not BRepCheck_Analyzer(shape).IsValid():
        raise RuntimeError("invalid solid")
    nf, vol, _ext = measures(shape)
    print(f"plate {PW:.1f} x {PH:.1f} x {T:.1f} mm web, bosses {BOSS['h']} high, {vol / 1000:.1f} cm3, "
          f"{vol * 2.70e-3:.0f} g (6061), {nf} faces; from {STOCK:.0f} mm stock, "
          f"{(PW * PH * STOCK - vol) / 1000:.0f} cm3 milled off")
    write_step(shape, NAME)
    read_back(shape, NAME)
    drawing(features, vol)


def drawing_notes(vol):
    """the notes on the drawing, one paragraph each."""
    t_min = S.PLATE_T - S.PLATE_T_TOL
    skin = BOSS["h"] - BOSS["h_tol"] + t_min - TAP["depth"] - TAP["point"]
    return [
        f"Geometry per {NAME}.step. This drawing adds what the model does not carry: tolerances, threads, edge "
        f"breaks, finish and, on sheet 2, the marking ({NAME}.dxf).",
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
        f"90 deg countersink: at least {skin:.2f} mm of metal stays in front of the drill point. Plug the threads "
        f"through bead blasting and anodising: they must gauge {TAP['thread']} afterwards. The boss end faces may be "
        "anodised or bare, but all of them alike.",
        f"Pocket depths +0, never deeper: at least {t_min - S.RANGE_POCKET[1]:.2f} mm of material must stay to the "
        "front face under every pocket; nothing may break through or mark the front face.",
        f"Encoder pockets and RANGE pocket: floor corner (inside radius between wall and floor) at most "
        f"{S.POCKET_FLOOR_R} mm; the parts' top corners come within about 0.2 mm of the pocket walls.",
        "Finish: black anodised, matte (bead blasted before anodising); the pockets may be anodised or bare, but "
        "all pockets alike (all anodised or all bare). Anodising rack contacts on the back face, on the boss end "
        "faces or inside the pockets; never on the front face, the outline or the key holes.",
        f"Key holes {S.KEY_HOLE[0]} x {S.KEY_HOLE[1]} {KEY_TOL} after anodising (never smaller: the key caps "
        f"centre the board in them), corners R{S.KEY_HOLE[2]}, R{S.KEY_HOLE_R_MAX} max. Light holes dia "
        f"{S.LIGHT_HOLE} {LIGHT_TOL} before anodising (never smaller: the light pipes slide in them, with room for "
        "the coating). "
        f"Deburr all edges: edge break at most {S.FRONT_BREAK} on the front outline and hole edges; on the back "
        f"edges of the key holes {S.KEY_BACK_BREAK} to {S.KEY_BACK_BREAK_MAX} (a lead-in for the key caps); the light "
        f"holes' back edges sharp, deburred only ({S.LIGHT_HOLE_BACK_BREAK} max: the light pipes' shoulders bear "
        "there).",
    ]


def marking_notes():
    """the notes on sheet 2, the marking, one paragraph each."""
    r, g, b = S.AMBER["rgb"]
    k = 1 - max(r, g, b) / 255
    cmyk = [round(100 * (1 - v / 255 - k) / (1 - k)) for v in (r, g, b)] + [round(100 * k)]
    n = {layer: len(polys) for layer, polys in PA.layers.items()}
    return [
        f"Marking on the front face per {NAME}.dxf, at 1:1 in mm, from the same origin as this view and the model: "
        "the plate's bottom-left corner seen from the front, X to the right, Y up. Position it by the outline.",
        f"Layer LASER ({n['LASER']} closed contours, shown light): laser marking. Layer UV_AMBER ({n['UV_AMBER']} "
        f"closed contours, shown in its colour): UV print, amber, sRGB {r} / {g} / {b} ({S.AMBER['hex'].upper()}), "
        f"CMYK {' / '.join(map(str, cmyk))}. Layer CUT ({n['CUT']} closed contours): the outline and the through "
        "holes, for reference; cut per the model.",
        "Fill the closed contours even-odd: a contour inside a letter is its counter, not ink. No stroke of the "
        f"marking is under {S.MARK_STROKE_MIN} mm wide.",
    ]


def title_block(fig, sheet):
    """the title block in the top right corner of a sheet."""
    return fig.text(0.96, 0.985, "\n".join([
        "Avionics Panel rev 1: front plate", "6061 aluminium, black anodised, matte; units mm, ISO 2768-m unless noted",
        f"Model {NAME}.step, marking {NAME}.dxf", f"{NAME}.pdf, sheet {sheet} of 2"]),
        ha="right", va="top", fontsize=6.5, linespacing=1.35,
        bbox=dict(boxstyle="square,pad=0.5", fc="white", ec="k", lw=0.6))


def text_block(fig, block, bottom):
    """a text block of (text, font size, bold, monospace) lines from the bottom of a sheet up: its texts and its
    height as a fraction of the page (half a line before each heading)."""
    lh = 1.3 / 72 / fig.get_figheight()                    # line height as a figure fraction, per point of font size
    height = sum(fs * lh for _, fs, _, _ in block) + sum(0.5 * 8.5 * lh for _, _, bold, _ in block if bold)
    y, texts = bottom + height, []
    for t, fs, bold, mono in block:
        if bold:
            y -= 0.5 * 8.5 * lh
        texts.append(fig.text(0.04, y, t, fontsize=fs, va="top", weight="bold" if bold else "normal",
                              family="monospace" if mono else None))
        y -= fs * lh
    return texts, height


def wrapped(notes):
    return [(("- " if i == 0 else "  ") + line, 7.0, False, False)
            for n in notes for i, line in enumerate(textwrap.wrap(n, 270))]


def front_sheet(plt):
    """Sheet 2: the front face with its marking, as the DXF has it (make_plate_art.dxf_layers)."""
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    from shapely.geometry.polygon import orient

    fig = plt.figure(figsize=PAGE)
    block = [("Marking", 8.5, True, False), *wrapped(marking_notes())]
    bottom, top = 0.02, 0.93
    texts, text_h = text_block(fig, block, bottom)
    ax = fig.add_axes([0.04, bottom + text_h + 0.02, 0.92, top - bottom - text_h - 0.02])
    ax.set_aspect("equal"); ax.axis("off")

    def patch(shape, **kw):
        """a shapely shape as one patch: every piece's outside one way round, its holes the other"""
        verts, codes = [], []
        for q in getattr(shape, "geoms", [shape]):
            q = orient(q)
            for ring in (q.exterior, *q.interiors):
                pts = list(ring.coords)
                verts += pts
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), **kw))

    layers = PA.dxf_layers()
    patch(PA.filled(layers["CUT"]), fc="#2d2f33", ec="k", lw=0.8)      # the plate, its holes open
    patch(PA.filled(layers["LASER"]), fc="#f2f2f2", ec="none")
    patch(PA.filled(layers["UV_AMBER"]), fc=S.AMBER["hex"], ec="none")
    ax.plot([-4, 4], [0, 0], color="k", lw=0.6); ax.plot([0, 0], [-4, 4], color="k", lw=0.6)   # the origin
    ax.annotate("0, 0: origin of the DXF and the model", (0, 0), xytext=(-4.5, -3.2), ha="left", va="top",
                fontsize=6.5)
    ax.annotate("", (0, PH + 2.5), (PW, PH + 2.5), arrowprops=dict(arrowstyle="<->", lw=0.5))
    ax.text(PW / 2, PH + 3.2, f"{PW:.1f}", ha="center", va="bottom", fontsize=6.5)
    ax.annotate("", (PW + 2.5, 0), (PW + 2.5, PH), arrowprops=dict(arrowstyle="<->", lw=0.5))
    ax.text(PW + 3.2, PH / 2, f"{PH:.1f}", ha="left", va="center", fontsize=6.5)
    ax.set_xlim(-6, PW + 8); ax.set_ylim(-6, PH + 6)
    ax.set_title("Avionics Panel rev 1 front plate, seen from the FRONT (marked side)", fontsize=11, loc="left")
    check_layout(fig, ax, [*texts, title_block(fig, 2)])
    return fig


def drawing(features, vol):
    """A3 drawing, two sheets: the back face with its pockets, bosses, threads and tongue and the notes for the
    order, and the front face with its marking."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

    fig = plt.figure(figsize=PAGE)
    notes = drawing_notes(vol)
    # the text block under the drawing, laid out from its own height; the drawing takes the page above it
    block = [("Features", 8.5, True, False)]
    block += [(f"{n:<20s} {s:<32s} {d:<60s} x{q}", 7.0, False, True) for n, s, d, q in features]
    block += [("Notes", 8.5, True, False), *wrapped(notes)]
    bottom, top = 0.02, 0.93
    texts, text_h = text_block(fig, block, bottom)
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
    check_layout(fig, ax, [*texts, title_block(fig, 1)])
    front = front_sheet(plt)
    with PdfPages(f"{NAME}.pdf", metadata={"CreationDate": None}) as pdf:     # reproducible
        pdf.savefig(fig)
        pdf.savefig(front)
    print(f"drawing written: 2 sheets, {len(notes)} notes in {len(block)} lines, the back view "
          f"{ax.get_position().height:.2f} of its page (min {DRAWING_MIN})")


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
