"""Cross-sections through the assembled stack (plate, knobs, datasheet part outlines) -> fit-check.png.

Sections run through the ALT/HDG knob, the RANGE knob and the SHIFT light pipe (XZ plane, z = 0 is the
PCB top). Grey: PCB and part outlines from the datasheets. Blue: plate. Black: printed parts.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.GCPnts import GCPnts_QuasiUniformDeflection
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods
from OCC.Core.gp import gp_Dir, gp_Pln, gp_Pnt

sys.path.insert(0, "../pcb")
import board as B  # noqa: E402
import stack as S  # noqa: E402
import make_knobs as K  # noqa: E402
import make_plate_step as PS  # noqa: E402
import make_mech as MM  # noqa: E402
from occ_util import move  # noqa: E402


def section(shape, y):
    sec = BRepAlgoAPI_Section(shape, gp_Pln(gp_Pnt(0, y, 0), gp_Dir(0, 1, 0)))
    sec.Build()
    ex = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    while ex.More():
        c = BRepAdaptor_Curve(topods.Edge(ex.Current()))
        d = GCPnts_QuasiUniformDeflection(c, 0.005)
        if d.IsDone() and d.NbPoints() > 1:
            pts = [d.Value(i + 1) for i in range(d.NbPoints())]
            yield [p.X() for p in pts], [p.Z() for p in pts]
        ex.Next()


def draw(ax, shape, y, colour, lw=0.9, dx=0.0, dz=0.0):
    for xs, zs in section(shape, y):
        ax.plot([x + dx for x in xs], [z + dz for z in zs], color=colour, lw=lw)


def part(ax, x0, z0, w, h, **kw):
    ax.add_patch(Rectangle((x0, z0), w, h, fc=kw.get("fc", "#e4e4e4"), ec=kw.get("ec", "#888"), lw=0.6))


plate, _ = PS.build()
fig, axes = plt.subplots(1, 3, figsize=(15, 8), gridspec_kw={"width_ratios": [28, 22, 15]})

# ---- ALT/HDG dual knob ----
ax = axes[0]
cx, cy = PS.P(*B.ALTHDG)
draw(ax, plate, cy, "#1f5fa0", dx=-cx, dz=S.PLATE_Z0)
part(ax, -12, -S.PCB_T, 24, S.PCB_T, fc="#c8d8c0")
part(ax, -11.7 / 2, 0, 11.7, S.EC11_BODY)
part(ax, -S.SLEEVE_D / 2, S.EC11_BODY, S.SLEEVE_D, S.SLEEVE_TOP - S.EC11_BODY)
part(ax, -S.OUTER_D / 2, S.SLEEVE_TOP, S.OUTER_D, S.OUTER_TOP - S.SLEEVE_TOP)
part(ax, -S.SLOT_W / 2, S.OUTER_TOP - S.SLOT_LEN, S.SLOT_W, S.SLOT_LEN, fc="white")
part(ax, -S.INNER_D / 2, S.OUTER_TOP, S.INNER_D, S.INNER_TOP - S.OUTER_TOP)
part(ax, S.INNER_FLAT - S.INNER_D / 2, S.INNER_TOP - S.FLAT_LEN, S.INNER_D - S.INNER_FLAT, S.FLAT_LEN, fc="white")
draw(ax, K.outer_knob(S.KNOB_D["ALTHDG"]), 0, "k", dz=S.PLATE_Z1 + S.OUTER_KNOB["z0"])
draw(ax, K.inner_knob(), 0, "k", dz=S.PLATE_Z1 + S.INNER_KNOB["z0"])
ax.set_title("ALT/HDG dual knob on PEC11D-4120F-S0015")

# ---- RANGE ----
ax = axes[1]
cx, cy = PS.P(*B.RANGE)
draw(ax, plate, cy, "#1f5fa0", dx=-cx, dz=S.PLATE_Z0)
part(ax, -12, -S.PCB_T, 24, S.PCB_T, fc="#c8d8c0")
part(ax, -14.5 / 2, 0, 14.5, 8.6)
part(ax, -2.0, 8.6, 4.0, 10.5 - 8.6)
part(ax, -S.LEVER_D / 2, S.LEVER_Z0, S.LEVER_D, S.LEVER_Z1 - S.LEVER_Z0)
draw(ax, K.range_knob(), 0, "k", dz=S.PLATE_Z1 + S.RANGE_KNOB["z0"])
ax.set_title("RANGE knob on RKJXT1F42001 (tilt 9 deg not drawn)")

# ---- SHIFT light pipe (section along board y, through the key above it) ----
ax = axes[2]
(lx, ly), _, _ = B.LEDS["SHIFT"]
px, py = PS.P(lx, ly)
# plate section in the YZ plane: rotate the problem by sectioning at x = px with a plane normal to X
from OCC.Core.gp import gp_Ax1, gp_Trsf  # noqa: E402
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform  # noqa: E402
import math  # noqa: E402
t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(px, py, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
rot = BRepBuilderAPI_Transform(plate, t, True).Shape()        # board +y (towards the user) now points to -x
draw(ax, rot, py, "#1f5fa0", dx=-px, dz=S.PLATE_Z0)
part(ax, -6, -S.PCB_T, 12, S.PCB_T, fc="#c8d8c0")
part(ax, -1.5, 0, 3.0, S.LED_TOP)                           # LED
key_dy = ly - B.ROWS[3]                                     # key centre is this far towards the back
part(ax, key_dy - 3.2, 9.5 - 3.0, 6.4, 6.0, fc="#555", ec="#222")   # key cap (on the 9.5 mm actuator)
pipe = move(K.light_pipe("SHIFT"), 0, 0, 0)
tp = gp_Trsf(); tp.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
draw(ax, BRepBuilderAPI_Transform(pipe, tp, True).Shape(), 0, "k", dx=0, dz=S.PIPE["z0"])
ax.set_title("SHIFT light pipe (front of the panel on the left)")

for ax, xl in zip(axes, ((-14, 14), (-11, 11), (-6, 9))):
    ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_xlim(*xl); ax.set_ylim(-3, 31 if ax is axes[0] else 22)
    ax.axhline(S.PLATE_Z1, color="#1f5fa0", lw=0.3, ls=":")
fig.tight_layout()
fig.savefig("fit-check.png", dpi=110)
print("fit-check.png written")


def clearances():
    """vertical clearances that must stay positive, with the inner knob pushed down."""
    ok, ik, rk = S.OUTER_KNOB, S.INNER_KNOB, S.RANGE_KNOB
    p = S.PUSH_TRAVEL
    outer_grip = min(S.PLATE_Z1 + ok["neck_top"], S.OUTER_TOP) - (S.SLEEVE_TOP + S.SLEEVE_CLEAR)   # bore on the 6 mm shaft
    rows = [
        ("outer knob over plate", ok["z0"]),
        ("outer knob grip on the 6 mm shaft, beyond 4 mm", outer_grip - 4.0),
        ("outer knob counterbore over the sleeve top", (S.PLATE_Z1 + ok["z0"] + (S.SLEEVE_TOP - S.PLATE_Z1 - ok["z0"] + S.SLEEVE_CLEAR)) - S.SLEEVE_TOP),
        ("inner knob over outer knob, pushed", ik["z0"] - p - ok["z1"]),
        ("inner recess over outer neck, pushed", ik["recess_top"] - p - ok["neck_top"]),
        ("inner recess over outer shaft top, pushed", ik["recess_top"] - p - (S.OUTER_TOP - S.PLATE_Z1)),
        ("RANGE knob over hub, pushed", (S.LEVER_Z0 - 0.3) - 10.5 - (S.LEVER_Z0 - S.PLATE_Z1 - rk["z0"])),
        ("light pipe over LED", S.PIPE["z0"] - S.LED_TOP),
        ("encoder pocket over encoder body", S.EC11_POCKET[3] - (S.EC11_BODY - S.PLATE_Z0)),
        ("RANGE pocket over RKJXT body", S.RANGE_POCKET[1] - (8.6 - S.PLATE_Z0)),
        ("cap bottom under plate top", S.PLATE_Z1 - (9.5 - 3.0)),
        ("body walls under the plate (spacers set it)", S.WALL_GAP),
        ("body boss wall around the screw head, beyond 0.7 (MJF)", MM.BOSS_R - MM.HEAD_R - 0.7),
        ("screw tip short of the last full thread", S.PLATE_Z0 + S.TAP["thread_depth"] - (S.SCREW_HEAD_Z + S.SCREW_L)),
        ("tap lead room: full-width drill beyond the thread", S.TAP["drill_depth"] - S.TAP_POINT - S.TAP["thread_depth"] - 0.3),
        ("plate left in front of the drill point, beyond 0.6", S.PLATE_T - S.TAP["drill_depth"] - 0.6),
        ("light pipe slip fit in its hole", S.PIPE["clear"]),
    ]
    # RANGE tilted 9 degrees: the low edge of the skirt must stay above the plate. The pivot height is not
    # in the datasheet, so check it anywhere between the body and the hub top.
    import math as m
    edge_z = S.PLATE_Z1 + rk["z0"]
    for pz in (6.0, 8.6, 10.5):
        low = pz + (edge_z - pz) * m.cos(m.radians(9)) - rk["skirt_d"] / 2 * m.sin(m.radians(9))
        rows.append((f"RANGE skirt over plate at 9 deg, pivot z {pz}", low - S.PLATE_Z1))
    for n, v in rows:
        print(f"  {n:52s} {v:5.2f} mm {'OK' if v > 0 else 'FAIL'}")
    assert all(v > 0 for _, v in rows)


clearances()
