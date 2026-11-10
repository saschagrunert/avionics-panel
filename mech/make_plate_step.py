"""CNC front plate for the Avionics Panel rev 1: STEP model for JLCCNC plus a 2D drawing of the back.

4 mm aluminium (6061), black anodised. Front face (+Z) is flat: laser marking and UV print follow the
DXF from make_plate_art.py, in the same coordinates. Back face (Z = 0): pockets for the encoder and
RANGE bodies and 4 round flat-bottom pockets for the glued standoffs; no threads. Everything is machined
from the back in one setup.

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
AMBER_HEX, AMBER_RGB, AMBER_REF = S.AMBER["hex"], ", ".join(map(str, S.AMBER["rgb"])), S.AMBER["ref"]
PW, PH = B.W + 2 * OVH, B.H + 2 * OVH
LIGHT_TOL = f"+{S.LIGHT_HOLE_TOL[0]}/-{S.LIGHT_HOLE_TOL[1]:g}"      # light holes: never smaller


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
        features.append((f"{name} light hole", f"dia {d} {LIGHT_TOL}", "through", 1))
    sp = S.STANDOFF_POCKET
    for (mx, my) in B.MOUNTS:                                        # flat bottom, no drill point
        tools.append(cyl(*P(mx, my), sp["d"], -e, sp["depth"]))
    features.append(("standoff pocket", f"dia {sp['d']} +{sp['d_tol']}/-0, flat bottom",
                     f"{sp['depth']} +0/-{sp['depth_tol']} deep from back", 4))
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
    """A4 drawing of the back face: pockets, plus notes for the order."""
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
    w, h, r, d = S.EC11_POCKET
    for name in ("ALTHDG", "FREQ", "FMS"):
        cx, cy = P(*getattr(B, name))
        rr(cx, cy, w, h, r, fc="#c9dcf0", ec="#1f5fa0", lw=0.8, hatch="///")
        ax.add_patch(Circle(M(cx, cy), S.SHAFT_HOLE / 2, fc="white", ec="k", lw=0.6))
    lx, ly = M(*P(*B.FREQ))                         # one label for all three, above the plate (clear of the keys)
    ax.annotate(f"3 x pocket {w} x {h} R{r}, {d} +0/-{S.POCKET_TOL} deep (encoders)", (lx, ly + h / 2),
                xytext=(lx - w / 2, PH + 3.5), ha="left", va="center", fontsize=6.5,
                arrowprops=dict(arrowstyle="-", lw=0.5))
    cx, cy = P(*B.RANGE)
    ax.add_patch(Circle(M(cx, cy), S.RANGE_POCKET[0] / 2, fc="#c9dcf0", ec="#1f5fa0", lw=0.8, hatch="///"))
    ax.add_patch(Circle(M(cx, cy), S.RANGE_HOLE / 2, fc="white", ec="k", lw=0.6))
    ax.annotate(f"pocket dia {S.RANGE_POCKET[0]}\n{S.RANGE_POCKET[1]} +0/-{S.POCKET_TOL} deep",
                M(cx, cy + S.RANGE_POCKET[0] / 2 + 0.5),
                ha="center", va="bottom", fontsize=6.5)
    for name, d in S.LIGHT_HOLES.items():
        (lx, ly), _, _ = B.LEDS[name]
        ax.add_patch(Circle(M(*P(lx, ly)), d / 2, fc="white", ec="k", lw=0.6))
    sp = S.STANDOFF_POCKET
    for (mx, my) in B.MOUNTS:
        px, py = M(*P(mx, my))
        ax.add_patch(Circle((px, py), sp["d"] / 2, fc="#c9dcf0", ec="#1f5fa0", lw=0.8, hatch="///"))
    px, py = M(*P(*B.MOUNTS[0]))                                     # one label for all four, above the plate
    ax.annotate(f"4 x pocket dia {sp['d']} +{sp['d_tol']}/-0, {sp['depth']} +0/-{sp['depth_tol']} deep, "
                "flat bottom (glued standoffs, no thread)", (px, py + sp["d"] / 2), xytext=(px, PH + 3.5),
                ha="right" if px > PW / 2 else "left", va="center", fontsize=6.5,
                arrowprops=dict(arrowstyle="-", lw=0.5))
    ax.set_xlim(-6, PW + 6); ax.set_ylim(-4, PH + 6)
    ax.set_title("Avionics Panel rev 1 front plate, seen from the BACK (machined side)", fontsize=11, loc="left")

    tx = fig.add_axes([0.04, 0.01, 0.92, 0.38]); tx.axis("off")
    rows = [f"{n:<20s} {s:<30s} {d:<52s} x{q}" for n, s, d, q in features]
    notes = [
        f"Material 6061 aluminium, {S.PLATE_T:.1f} +-{S.PLATE_T_TOL} mm. Outline {PW:.1f} x {PH:.1f} mm, "
        f"corner R{B.CORNER_R + OVH:.1f}. "
        f"Volume {vol / 1000:.1f} cm3. Units mm, general tolerance ISO 2768-m.",
        "Front face (+Z in the STEP) is flat: no pockets or fastener holes on the front, and no chamfers beyond "
        "the edge break below.",
        f"Positions of the 4 standoff pockets and all through holes: +-{S.POS_TOL['plate']} to each other (the "
        "key caps and the board must line up).",
        f"NO THREADS. 4 x round pockets dia {S.STANDOFF_POCKET['d']} +{S.STANDOFF_POCKET['d_tol']}/-0 from the "
        f"back, flat bottom (end mill, no drill point), {S.STANDOFF_POCKET['depth']} +0/-"
        f"{S.STANDOFF_POCKET['depth_tol']} mm deep; metal standoffs are glued into them later. Pocket depths "
        "+0, never deeper: at least 0.7 mm of material must stay to the front face under every pocket; "
        "nothing may break through or mark the front face.",
        "Finish: black anodised, matte (bead blasted before anodising); the pockets may be anodised.",
        "Marking on the front per avionics-panel-rev1-plate.dxf, same origin (bottom-left, seen from the front): "
        f"layer LASER = laser marking, layer UV_AMBER = UV print in amber {AMBER_HEX} (RGB {AMBER_RGB}, about "
        f"{AMBER_REF}). Layer CUT = outline and through holes for reference. DXF units mm; fill closed contours "
        "even-odd (letter counters are separate contours).",
        f"Light holes {LIGHT_TOL} (never smaller: light pipes are glued into them). Deburr all edges: edge break "
        "at most 0.2 on the front outline and hole edges.",
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
