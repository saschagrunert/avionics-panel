"""CNC front plate for the Avionics Panel rev 1: STEP model for JLCCNC plus a 2D drawing for the threads.

4 mm aluminium (6061), black anodised. Front face (+Z) is flat: laser marking and UV print follow the
DXF from make_plate_art.py, in the same coordinates. Back face (Z = 0): pockets for the encoder and
RANGE bodies and 4 blind M2.5 threads (thread milled, flat bottom). Everything is machined from the back
in one setup.

Coordinates: origin at the bottom-left corner of the plate seen from the front, X right, Y up, mm.
Needs pythonocc-core (nix-shell -p "python3.withPackages (ps: with ps; [ pythonocc-core numpy matplotlib ])").
"""
import math
import sys

from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCC.Core.GC import GC_MakeArcOfCircle
from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
from OCC.Core.GProp import GProp_GProps
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.Interface import Interface_Static
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopTools import TopTools_ListOfShape

sys.path.insert(0, "../pcb")
import board as B  # noqa: E402
import stack as S  # noqa: E402
from occ_util import pin_step_time  # noqa: E402

OVH, T = S.OVH, S.PLATE_T
PW, PH = B.W + 2 * OVH, B.H + 2 * OVH


def P(x, y):
    """board coordinates (y down) -> plate coordinates (y up, origin bottom-left)."""
    return x + OVH, B.H + OVH - y


def rrect_prism(cx, cy, w, h, r, z0, z1):
    hw, hh = w / 2, h / 2
    def pts(x, y, z=z0):
        return gp_Pnt(cx + x, cy + y, z)
    mw = BRepBuilderAPI_MakeWire()
    corners = [((hw - r, hh - r), 0), ((-hw + r, hh - r), 90), ((-hw + r, -hh + r), 180), ((hw - r, -hh + r), 270)]
    edges = []
    for (ox, oy), a in corners:
        a0, am, a1 = math.radians(a), math.radians(a + 45), math.radians(a + 90)
        arc = GC_MakeArcOfCircle(pts(ox + r * math.cos(a0), oy + r * math.sin(a0)),
                                 pts(ox + r * math.cos(am), oy + r * math.sin(am)),
                                 pts(ox + r * math.cos(a1), oy + r * math.sin(a1))).Value()
        edges.append(("arc", arc, (ox + r * math.cos(a0), oy + r * math.sin(a0)),
                      (ox + r * math.cos(a1), oy + r * math.sin(a1))))
    for i, (_, arc, _s, e) in enumerate(edges):
        mw.Add(BRepBuilderAPI_MakeEdge(arc).Edge())
        ns = edges[(i + 1) % 4][2]
        mw.Add(BRepBuilderAPI_MakeEdge(pts(*e), pts(*ns)).Edge())
    face = BRepBuilderAPI_MakeFace(mw.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, z1 - z0)).Shape()


def cyl(cx, cy, d, z0, z1):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(cx, cy, z0), gp_Dir(0, 0, 1)), d / 2, z1 - z0).Shape()


def build():
    plate = rrect_prism(PW / 2, PH / 2, PW, PH, B.CORNER_R + OVH, 0.0, T)
    tools, features = [], []
    e = 0.5                                                 # through tools overshoot both faces
    for y in B.ROWS:
        for x in B.COLS:
            tools.append(rrect_prism(*P(x, y), *S.KEY_HOLE, -e, T + e))
    features.append(("key hole", f"{S.KEY_HOLE[0]} x {S.KEY_HOLE[1]} R{S.KEY_HOLE[2]}", "through",
                     len(B.ROWS) * len(B.COLS)))
    for name in ("ALTHDG", "FREQ", "FMS"):
        cx, cy = P(*getattr(B, name))
        tools.append(cyl(cx, cy, S.SHAFT_HOLE, -e, T + e))
        w, h, r, dpt = S.EC11_POCKET
        tools.append(rrect_prism(cx, cy, w, h, r, -e, dpt))
    features.append(("encoder hole", f"dia {S.SHAFT_HOLE}", "through", 3))
    features.append(("encoder pocket", f"{S.EC11_POCKET[0]} x {S.EC11_POCKET[1]} R{S.EC11_POCKET[2]}",
                     f"{S.EC11_POCKET[3]} +0/-{S.POCKET_TOL} deep from back", 3))
    cx, cy = P(*B.RANGE)
    tools.append(cyl(cx, cy, S.RANGE_HOLE, -e, T + e))
    tools.append(cyl(cx, cy, S.RANGE_POCKET[0], -e, S.RANGE_POCKET[1]))
    features.append(("RANGE hole", f"dia {S.RANGE_HOLE}", "through", 1))
    features.append(("RANGE pocket", f"dia {S.RANGE_POCKET[0]}",
                     f"{S.RANGE_POCKET[1]} +0/-{S.POCKET_TOL} deep from back", 1))
    for name, d in S.LIGHT_HOLES.items():
        (lx, ly), _, _ = B.LEDS[name]
        tools.append(cyl(*P(lx, ly), d, -e, T + e))
        features.append((f"{name} light hole", f"dia {d}", "through", 1))
    for (mx, my) in B.MOUNTS:                                        # flat bottom: thread milled, no drill point
        tools.append(cyl(*P(mx, my), S.TAP["drill"], -e, S.TAP["hole_depth"]))
    features.append(("threaded hole", f"{S.TAP['size']}, thread milled",
                     f"full thread {S.TAP['thread_depth']} min, flat hole {S.TAP['hole_depth']} "
                     f"+0/-{S.TAP['depth_tol']}, "
                     "from back", 4))
    args, tl = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(plate)
    for t in tools:
        tl.Append(t)
    cut = BRepAlgoAPI_Cut()
    cut.SetArguments(args); cut.SetTools(tl); cut.SetRunParallel(True); cut.Build()
    assert cut.IsDone(), "boolean cut failed"
    return cut.Shape(), features


def main():
    shape, features = build()
    assert BRepCheck_Analyzer(shape).IsValid(), "invalid solid"
    props = GProp_GProps(); brepgprop.VolumeProperties(shape, props)
    nf = 0; ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        nf += 1; ex.Next()
    vol = props.Mass()
    print(f"plate {PW:.1f} x {PH:.1f} x {T:.1f} mm, {vol / 1000:.1f} cm3, {vol * 2.70e-3:.0f} g (6061), {nf} faces")

    Interface_Static.SetCVal("write.step.unit", "MM")
    Interface_Static.SetCVal("write.step.product.name", "avionics-panel-rev1-plate")
    w = STEPControl_Writer(); w.Transfer(shape, STEPControl_AsIs)
    assert w.Write("avionics-panel-rev1-plate.step") == IFSelect_RetDone
    pin_step_time("avionics-panel-rev1-plate.step")
    BRepMesh_IncrementalMesh(shape, 0.02, False, 0.2, True)
    StlAPI_Writer().Write(shape, "avionics-panel-rev1-plate-ref.stl")
    drawing(features, vol)


def drawing(features, vol):
    """A4 drawing of the back face: pockets and threads, plus notes for the order."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch

    fig = plt.figure(figsize=(11.69, 8.27))
    ax = fig.add_axes([0.04, 0.40, 0.92, 0.55])
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
    for name in ("ALTHDG", "FREQ", "FMS"):
        cx, cy = P(*getattr(B, name))
        w, h, r, d = S.EC11_POCKET
        rr(cx, cy, w, h, r, fc="#c9dcf0", ec="#1f5fa0", lw=0.8, hatch="///")
        ax.add_patch(Circle(M(cx, cy), S.SHAFT_HOLE / 2, fc="white", ec="k", lw=0.6))
        lx, ly = M(cx, cy)
        side = 1 if lx < PW / 2 else -1                     # label on the side facing the keys
        ax.annotate(f"pocket {w} x {h} R{r}\n{d} +0/-{S.POCKET_TOL} deep", (lx + side * (w / 2 + 1.0), ly),
                    ha="left" if side > 0 else "right", va="center", fontsize=6.5)
    cx, cy = P(*B.RANGE)
    ax.add_patch(Circle(M(cx, cy), S.RANGE_POCKET[0] / 2, fc="#c9dcf0", ec="#1f5fa0", lw=0.8, hatch="///"))
    ax.add_patch(Circle(M(cx, cy), S.RANGE_HOLE / 2, fc="white", ec="k", lw=0.6))
    ax.annotate(f"pocket dia {S.RANGE_POCKET[0]}\n{S.RANGE_POCKET[1]} +0/-{S.POCKET_TOL} deep",
                M(cx, cy + S.RANGE_POCKET[0] / 2 + 0.5),
                ha="center", va="bottom", fontsize=6.5)
    for name, d in S.LIGHT_HOLES.items():
        (lx, ly), _, _ = B.LEDS[name]
        ax.add_patch(Circle(M(*P(lx, ly)), d / 2, fc="white", ec="k", lw=0.6))
    for (mx, my) in B.MOUNTS:
        px, py = M(*P(mx, my))
        ax.add_patch(Circle((px, py), S.TAP["drill"] / 2, fc="#f0c9c9", ec="#a01f1f", lw=0.8))
        ax.add_patch(Circle((px, py), 1.25, fc="none", ec="#a01f1f", lw=0.6, ls=(0, (2, 1))))
        ax.annotate(f"{S.TAP['size']} thread {S.TAP['thread_depth']}\nflat hole {S.TAP['hole_depth']}", (px, py),
                    xytext=(px + (2 if px < PW / 2 else -2), py),
                    ha="left" if px < PW / 2 else "right", va="center", fontsize=6.5, color="#a01f1f")
    ax.set_xlim(-6, PW + 6); ax.set_ylim(-4, PH + 4)
    ax.set_title("Avionics Panel rev 1 front plate, seen from the BACK (machined side)", fontsize=11, loc="left")

    tx = fig.add_axes([0.04, 0.01, 0.92, 0.38]); tx.axis("off")
    rows = [f"{n:<20s} {s:<30s} {d:<52s} x{q}" for n, s, d, q in features]
    notes = [
        f"Material 6061 aluminium, {S.PLATE_T:.1f} +-{S.PLATE_T_TOL} mm. Outline {PW:.1f} x {PH:.1f} mm, "
        f"corner R{B.CORNER_R + OVH:.1f}. "
        f"Volume {vol / 1000:.1f} cm3. Units mm, general tolerance ISO 2768-m.",
        "Front face (+Z in the STEP) is flat: no pockets, chamfers or fastener holes on the front.",
        f"Positions of the 4 threads and all through holes: +-{S.POS_TOL['plate']} to each other (the key caps and "
        "the screws must line up with the board).",
        f"4 x {S.TAP['size']} blind threads from the back, THREAD MILLED in a flat-bottom hole (end mill, no "
        f"drill point): hole {S.TAP['hole_depth']} +0/-{S.TAP['depth_tol']} mm deep, full thread from "
        f"{S.TAP['entry']} to at least {S.TAP['thread_depth']} mm below the back face (deburr only, no countersink). "
        "Keep at least 0.7 mm of material to the front face under every hole and pocket (depths +0, never "
        "deeper): nothing may break through or mark the front face.",
        "Threads: mask them before anodising, or chase them after anodising (the coating makes them tight).",
        "Finish: black anodised, matte (bead blasted before anodising).",
        "Marking on the front per avionics-panel-rev1-plate.dxf, same origin (bottom-left, seen from the front): "
        "layer LASER = laser marking, layer UV_ORANGE = UV print orange. "
        "Layer CUT = outline and through holes for reference.",
        "Deburr all edges, edge break 0.2 on the front outline and hole edges.",
    ]
    y = 0.98
    tx.text(0, y, "Features", fontsize=9, weight="bold", va="top"); y -= 0.06
    for r in rows:
        tx.text(0, y, r, fontsize=7.5, family="monospace", va="top"); y -= 0.044
    y -= 0.03
    tx.text(0, y, "Notes", fontsize=9, weight="bold", va="top"); y -= 0.06
    import textwrap
    for n in notes:
        for i, line in enumerate(textwrap.wrap(n, 150)):
            tx.text(0, y, ("- " if i == 0 else "  ") + line, fontsize=7.5, va="top"); y -= 0.044
    fig.savefig("avionics-panel-rev1-plate-drawing.pdf", metadata={"CreationDate": None})   # reproducible
    fig.savefig("avionics-panel-rev1-plate-drawing.png", dpi=110)
    print("drawing written")


if __name__ == "__main__":
    main()
