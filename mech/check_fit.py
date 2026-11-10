"""Cross-sections through the assembled stack (plate, knobs, datasheet part outlines) -> fit-check.png.

Sections run through the ALT/HDG knob, the RANGE knob and the SHIFT light pipe (XZ plane, z = 0 is the
PCB top). Grey: PCB and part outlines from the datasheets. Blue: plate. Black: printed parts.
"""
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.GCPnts import GCPnts_QuasiUniformDeflection
from OCC.Core.gp import gp_Dir, gp_Pln, gp_Pnt
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods

HERE = Path(__file__).resolve().parent              # works from any directory
sys.path[:0] = [str(HERE), str(HERE.parent / "pcb")]
import board as B  # noqa: E402
import make_knobs as K  # noqa: E402
import make_mech as MM  # noqa: E402
import make_plate_step as PS  # noqa: E402
import stack as S  # noqa: E402
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
part(ax, -14.5 / 2, 0, 14.5, S.RKJXT_BODY)
part(ax, -2.0, S.RKJXT_BODY, 4.0, S.RKJXT_HUB_TOP - S.RKJXT_BODY)
part(ax, -S.LEVER_D / 2, S.LEVER_Z0, S.LEVER_D, S.LEVER_Z1 - S.LEVER_Z0)
draw(ax, K.range_knob(), 0, "k", dz=S.PLATE_Z1 + S.RANGE_KNOB["z0"])
ax.set_title(f"RANGE knob on RKJXT1F42001 (tilt {S.RKJXT_TILT:.0f} deg not drawn)")

# ---- SHIFT light pipe (section along board y, through the key above it) ----
ax = axes[2]
(lx, ly), _, _ = B.LEDS["SHIFT"]
px, py = PS.P(lx, ly)
# plate section in the YZ plane: rotate the problem by sectioning at x = px with a plane normal to X
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform  # noqa: E402
from OCC.Core.gp import gp_Ax1, gp_Trsf  # noqa: E402

t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(px, py, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
rot = BRepBuilderAPI_Transform(plate, t, True).Shape()        # board +y (towards the user) now points to -x
draw(ax, rot, py, "#1f5fa0", dx=-px, dz=S.PLATE_Z0)
part(ax, -6, -S.PCB_T, 12, S.PCB_T, fc="#c8d8c0")
part(ax, -1.5, 0, 3.0, S.LED_TOP)                           # LED
key_dy = ly - B.ROWS[3]                                     # key centre is this far towards the back
part(ax, key_dy - S.CAP["h"] / 2, S.CAP["base"], S.CAP["h"], 6.0, fc="#555", ec="#222")   # key cap, plunger
pipe = move(K.light_pipe("SHIFT"), 0, 0, 0)
tp = gp_Trsf(); tp.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
draw(ax, BRepBuilderAPI_Transform(pipe, tp, True).Shape(), 0, "k", dx=0, dz=S.PIPE["z0"])
ax.set_title("SHIFT light pipe (front of the panel on the left)")

for ax, xl in zip(axes, ((-14, 14), (-11, 11), (-6, 9)), strict=True):
    ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_xlim(*xl); ax.set_ylim(-3, 31 if ax is axes[0] else 22)
    ax.axhline(S.PLATE_Z1, color="#1f5fa0", lw=0.3, ls=":")
fig.tight_layout()
fig.savefig(HERE / "fit-check.png", dpi=110)
print("fit-check.png written")


def rrect_sd(x, y, w, h, r):
    """signed distance of points to a rounded rectangle centred at 0 (negative inside, positive outside)."""
    qx, qy = np.abs(x) - (w / 2 - r), np.abs(y) - (h / 2 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def cap_shift_room():
    """how far a key cap can shift in its key hole before it touches: (least, most) over all directions."""
    c = S.CAP
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    ox = (c["w"] / 2 - c["r"]) * np.sign(np.cos(t)) + c["r"] * np.cos(t)     # cap outline, corners dense
    oy = (c["h"] / 2 - c["r"]) * np.sign(np.sin(t)) + c["r"] * np.sin(t)
    rooms = []
    for a in np.linspace(0, 2 * np.pi, 144, endpoint=False):
        lo, hi = 0.0, 2.0
        for _ in range(30):
            d = (lo + hi) / 2
            inside = rrect_sd(ox + d * np.cos(a), oy + d * np.sin(a), *S.KEY_HOLE).max() <= 0
            lo, hi = (d, hi) if inside else (lo, d)
        rooms.append(lo)
    return min(rooms), max(rooms)


# ---- body: no slot of void and no wall of PA12 under 0.8 mm (powder traps, loose bosses, porous slivers) ----
def stl_triangles(path):
    with open(path, "rb") as f:
        data = f.read()
    n = int.from_bytes(data[80:84], "little")
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(data[84:84 + 50 * n], dtype=dt)["v"].astype(float)


def body_triangles():
    """the body mesh in board frame: the STL make_mech.py exported in this build, or a fresh mesh when that STL
    is missing or older than its sources."""
    stl = HERE / "avionics-panel-rev1-body.stl"
    sources = [HERE / f for f in ("make_mech.py", "stack.py", "occ_util.py", "make_plate_step.py")]
    sources.append(HERE.parent / "pcb" / "board.py")
    if stl.exists() and stl.stat().st_mtime >= max(f.stat().st_mtime for f in sources):
        tri = stl_triangles(stl)
        tri[:, :, 1] *= -1                                       # output frame (Y = -board y) back to board y
        return tri
    print("  (body STL missing or stale: meshing make_mech.body())")
    return mesh_triangles(MM.body())


def mesh_triangles(shape, deflection=0.02):
    """triangles (n, 3, 3) of an OpenCascade solid, meshed here: check the body as make_mech.py builds it now."""
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopLoc import TopLoc_Location
    BRepMesh_IncrementalMesh(shape, deflection, False, 0.15, True)
    out = []
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation(topods.Face(ex.Current()), loc)
        if tri is not None:
            t = loc.Transformation()
            nodes = np.array([[q.X(), q.Y(), q.Z()] for q in
                              (tri.Node(i + 1).Transformed(t) for i in range(tri.NbNodes()))])
            idx = np.array([tri.Triangle(i + 1).Get() for i in range(tri.NbTriangles())]) - 1
            out.append(nodes[idx])
        ex.Next()
    return np.concatenate(out)


def raster_section(tri, axis, value, res):
    """solid mask of a closed mesh cut by the plane coordinate[axis] = value (even-odd fill on a res grid)."""
    u_ax, v_ax = [a for a in range(3) if a != axis]
    d = tri[:, :, axis] - value
    d[np.abs(d) < 1e-7] = 1e-7                                   # no vertex exactly on the plane
    pts, hit = [], []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        m = d[:, a] * d[:, b] < 0
        t = np.where(m, d[:, a] / np.where(m, d[:, a] - d[:, b], 1), 0)
        pts.append(tri[:, a] + t[:, None] * (tri[:, b] - tri[:, a]))
        hit.append(m)
    pts, hit = np.stack(pts, 1), np.stack(hit, 1)
    sel = hit.sum(1) == 2
    order = np.argsort(~hit[sel], axis=1, kind="stable")[:, :2]
    seg = np.take_along_axis(pts[sel], order[:, :, None], 1)     # (n, 2, 3)
    u, v = seg[:, :, u_ax], seg[:, :, v_ax]
    u0, v0 = u.min() - 1.5, v.min() - 1.5
    nu, nv = int((u.max() + 1.5 - u0) / res) + 1, int((v.max() + 1.5 - v0) / res) + 1
    j0 = np.ceil((v.min(1) - v0) / res - 0.5).astype(int)
    j1 = np.ceil((v.max(1) - v0) / res - 0.5).astype(int)
    cnt = np.maximum(j1 - j0, 0)
    idx = np.repeat(np.arange(len(seg)), cnt)
    j = np.repeat(j0, cnt) + (np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    f = (v0 + (j + 0.5) * res - v[idx, 0]) / (v[idx, 1] - v[idx, 0])
    uc = u[idx, 0] + f * (u[idx, 1] - u[idx, 0])
    c = np.clip(np.ceil((uc - u0) / res - 0.5).astype(int), 0, nu)
    tog = np.zeros((nv, nu + 1), np.int32)
    np.add.at(tog, (j, c), 1)
    return (np.cumsum(tog, 1)[:, :nu] % 2) == 1


def _shifted(mask, offs, erode, outside=False):
    """erosion (AND) or dilation (OR) of the mask over every offset; pixels off the grid count as outside."""
    p = max(max(abs(dy), abs(dx)) for dy, dx in offs)
    pad = np.pad(mask, p, constant_values=outside)
    out = np.full(mask.shape, erode)
    h, w = mask.shape
    for dy, dx in offs:
        s = pad[p + dy:p + dy + h, p + dx:p + dx + w]
        out = (out & s) if erode else (out | s)
    return out


def thin_depth(mask, res, outside, gap=0.8):
    """deepest point of any part of mask narrower than gap: the pixels a disk of dia gap cannot reach, measured
    along the mask to the nearest reachable pixel. A square corner gives about 0.2."""
    r = int(round(gap / 2 / res))
    disk = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1) if dy * dy + dx * dx <= r * r]
    opened = _shifted(_shifted(mask, disk, True, outside), disk, False) & mask
    thin = mask & ~opened
    cross = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    cover, steps = opened, 0
    while (thin & ~cover).any() and steps < 30:
        cover = _shifted(cover, cross, False) & mask
        steps += 1
    return steps * res


def body_thin(res=0.1):
    """deepest thin void and deepest thin wall over sections through the body (board frame), with where."""
    tri = body_triangles()
    ux = B.USB_X
    planes = [(2, z) for z in (-2.5, -4.0, -6.0, -6.5, -7.0, -7.7, -8.3, -9.0, -10.5, -12.0, -13.5)]
    planes += [(0, x) for x in (3.5, 9.0, 15.5, 22.5, 54.0, 85.0, 112.0, ux - 7.0, ux, ux + 7.0, B.BOOT[0],
                                150.0, 156.5)]
    planes += [(1, y) for y in (-1.5, 0.5, 2.0, 3.5, 6.7, 20.0, 40.0, 47.8, 55.5, 57.0)]
    void, wall = (0.0, "none"), (0.0, "none")
    for axis, value in planes:
        solid = raster_section(tri, axis, value + 1e-3, res)
        where = f"{'xyz'[axis]} {value:g}"
        dv = thin_depth(~solid, res, True)
        # walls only in x and y sections: a z section cuts the 6 deg bottom faces at a slant, so their edges
        # look like slivers there that are not thin in 3D
        dw = thin_depth(solid, res, False) if axis != 2 else 0.0
        void = (dv, where) if dv > void[0] else void
        wall = (dw, where) if dw > wall[0] else wall
    return void, wall


def clearances():
    """clearances that must stay positive, with the inner knob pushed down; each one can fail."""
    ok, ik, rk = S.OUTER_KNOB, S.INNER_KNOB, S.RANGE_KNOB
    p = S.PUSH_TRAVEL
    outer_grip = min(S.PLATE_Z1 + ok["neck_top"], S.OUTER_TOP) - (S.SLEEVE_TOP + S.SLEEVE_CLEAR)
    # ---- knob walls: resin diameters (JLC3DP) +-0.2 outside, +-0.3 on holes; a bore at FIT 0 leaves up to 0.05
    # radial play on its shaft, so the two knobs of a dual can sit that far off each other twice ----
    part_tol, hole_tol, bore_play = 0.2, 0.3, 0.05
    loose = max(S.FIT, *S.FIT_VARIANTS.values())
    fo, fi = K.OUTER_FLUTES, K.INNER_FLUTES
    ring_r, cb_r = min(S.KNOB_D.values()) / 2, S.SLEEVE_D / 2 + S.SLEEVE_CLEAR
    # flute bottoms where the walls are thinnest: the taper narrows the knobs towards the top of the
    # recess (inner) and of the counterbore (outer)
    rec_bot = ik["d"] / 2 * (1 - fi["taper"] * (ik["recess_top"] - ik["z0"]) / (ik["z1"] - ik["z0"])) - fi["depth"]
    cb_bot = ring_r * (1 - fo["taper"] * K.outer_counterbore_top() / (ok["z1"] - ok["z0"])) - fo["depth"]
    # ---- plate: thickness +-PLATE_T_TOL, back on the spacer (+-0.05 from the PCB top); depths from the back ----
    sp_tol, t_tol = S.STACK_TOL["spacer"], S.PLATE_T_TOL
    t_min = S.PLATE_T - t_tol
    top_tol = sp_tol + t_tol                            # plate face against the PCB top
    # ---- screws, shimmed to fit ----
    T, sc, pt = S.TAP, S.SCREW, S.POS_TOL
    floor_hi, floor_lo = T["hole_depth"], T["hole_depth"] - T["depth_tol"]
    stop_lo = T["thread_depth"]                         # the screw may stop at the end of the full thread
    seat_tol = S.STACK_TOL["counterbore"]
    pb_tol = S.STACK_TOL["pcb"] + sp_tol                # plate back against the boss top (PCB, spacer)
    wt = S.WASHER["t"]
    # tip depth in the plate with the head washer alone, shortest and longest stack
    d_lo = (S.SEAT_Z - seat_tol) - wt + (sc["L"] - sc["L_tol"]) - (S.PLATE_Z0 + pb_tol)
    d_hi = (S.SEAT_Z + seat_tol) - wt + (sc["L"] + sc["L_tol"]) - (S.PLATE_Z0 - pb_tol)
    n_lo = 1 + max(0, math.ceil(round((d_lo - stop_lo) / wt, 6)))     # washers the shortest stack needs
    n_hi = 1 + max(0, math.ceil(round((d_hi - stop_lo) / wt, 6)))     # and the longest
    tip_min = min(d_lo, stop_lo - wt)                                  # a shimmed tip ends within a washer
    engaged = min(tip_min - sc["tip"], T["thread_depth"]) - T["entry"]
    # head and washers recessed: the bottom plane rises to the front, so take its highest point under the
    # counterbore (the washers stay inside it) at the front mounts, with MJF +0.3
    cb_hi = MM.HEAD_R + pt["body_hole"]
    boss_floor = max(MM.z_bottom(min(my + cb_hi, B.H + MM.o)) for _, my in B.MOUNTS) + seat_tol
    head_lo = (S.SEAT_Z - seat_tol) - S.WASHERS_MAX * wt - sc["head_k"]
    # ---- washer on the body: slides on the screw, held over the hole by the counterbore wall ----
    r_hole_max = MM.SCREW_CLEAR + pt["body_hole"]
    offset = MM.SCREW_OFFSET                            # screw against the widest body hole wall
    r_w_min, r_w_max = S.WASHER["od_min"] / 2, S.WASHER["od"] / 2
    w_off = min(offset + MM.WASHER_PLAY, cb_hi - r_w_min)   # washer centre off the body hole centre, worst
    # ---- positions: board offset from the caps, screw in the PCB hole, spacer ----
    cap_err = math.sqrt(sum(v * v for v in S.CAP_TOL.values()))
    cap_room, cap_room_max = cap_shift_room()
    board = cap_room_max + pt["centring"]              # board offset the caps allow (the most, diagonally)
    in_pcb = pt["plate"] + pt["pcb"] + pt["thread"] + board   # screw off the PCB hole centre, worst
    pcb_r_lo, pcb_r_hi = (B.MOUNT_HOLE - pt["npth_d"]) / 2, (B.MOUNT_HOLE + pt["npth_d"]) / 2
    sp = S.SPACER
    sp_play = (sp["id_max"] - sc["d_min"]) / 2
    corner = min(-rrect_sd(mx - B.W / 2, my - B.H / 2, B.W + 2 * MM.o, B.H + 2 * MM.o, B.CORNER_R + MM.o)
                 for mx, my in B.MOUNTS) - cb_hi       # counterbore to the outer body surface
    cav = MM.CLEAR - MM.PCB_OUTLINE_TOL / 2 - MM.BODY_SCALE_TOL * (B.W + 2 * MM.CLEAR) / 2
    # ---- assembly, body ----
    caps = [(x, y) for y in B.ROWS for x in B.COLS]
    protrude = max(S.INNER_TOP, S.LEVER_Z1) - S.PLATE_Z1 + top_tol    # shafts past the plate face, face down
    edge = min([min(y - S.CAP["h"] / 2, B.H - y - S.CAP["h"] / 2) for _, y in caps] +
               [min(y - S.SLEEVE_D / 2, B.H - y - S.SLEEVE_D / 2) for y in (B.ALTHDG[1], B.RANGE[1])]) + S.OVH
    stl, x0 = MM.STEEL, MM.steel_x0()
    fx, fy = MM.FEET[0]
    notch = min(x0 + stl["notch"] - (fx + MM.FOOT_PAD / 2), stl["y0"] + stl["notch"] - (fy + MM.FOOT_PAD / 2))
    (void, void_at), (wall, wall_at) = body_thin()
    # ---- light pipes glued flush, LEDs under them ----
    pp = S.PIPE
    led_hi = S.LED_TOP + S.LED_TOL[0]
    face_lo = S.PLATE_Z0 - sp_tol + t_min               # lowest plate face over the PCB top
    pd = S.POCKET_TOL
    back_hi = S.PLATE_Z0 + sp_tol                        # highest plate back (pocket ceilings start here)
    wall_gap = S.WALL_GAP - (seat_tol + S.STACK_TOL["pcb"] + sp_tol)   # MJF wall height, PCB, spacer
    rows = [
        (f"outer knob over plate (plate face +-{top_tol:.2f})", ok["z0"] - top_tol),
        ("outer knob grip on the 6 mm shaft, beyond 4 mm", outer_grip - 4.0),
        ("outer knob counterbore over the sleeve top",
         (S.PLATE_Z1 + ok["z0"] + (S.SLEEVE_TOP - S.PLATE_Z1 - ok["z0"] + S.SLEEVE_CLEAR)) - S.SLEEVE_TOP),
        ("inner knob over outer knob, pushed", ik["z0"] - p - ok["z1"]),
        ("inner recess over outer neck, pushed", ik["recess_top"] - p - ok["neck_top"]),
        ("inner recess over outer shaft top, pushed", ik["recess_top"] - p - (S.OUTER_TOP - S.PLATE_Z1)),
        (f"inner recess ({ik['recess_d']}) round the outer neck ({ok['neck_d']}), radial: resin, bore play",
         (ik["recess_d"] - hole_tol) / 2 - (ok["neck_d"] + part_tol) / 2 - 2 * bore_play),
        (f"outer neck wall round the 6 mm bore, loose variant (+{loose}), beyond 1.0",
         (ok["neck_d"] - S.OUTER_D - loose) / 2 - 1.0),
        ("inner knob wall round the recess at the flute bottoms, beyond 1.0", rec_bot - ik["recess_d"] / 2 - 1.0),
        ("outer knob wall round the counterbore at the flute bottoms, beyond 1.0", cb_bot - cb_r - 1.0),
        ("outer ring beyond the inner knob, per side, beyond 2.0 (Garmin 2.5)",
         ring_r - ik["d"] / 2 - 2.0),
        ("RANGE knob over hub, pushed",
         (S.LEVER_Z0 - 0.3) - S.RKJXT_HUB_TOP - (S.LEVER_Z0 - S.PLATE_Z1 - rk["z0"])),
        (f"encoder pocket (-{pd}) over encoder body (8.0 +0.3), high plate",
         S.PLATE_Z0 - sp_tol + S.EC11_POCKET[3] - pd - (S.EC11_BODY + 0.3)),
        ("plate left over the encoder pockets, thin plate, beyond 1.0", t_min - S.EC11_POCKET[3] - 1.0),
        (f"RANGE pocket (-{pd}) over RKJXT body (8.6 +0.3), low plate",
         S.PLATE_Z0 - sp_tol + S.RANGE_POCKET[1] - pd - (S.RKJXT_BODY + 0.3)),
        ("plate left over the RANGE pocket, thin plate, beyond 0.6", t_min - S.RANGE_POCKET[1] - 0.6),
        ("cap bottom under the lowest plate face", face_lo - S.CAP["base"]),
        ("pressed cap bottom still inside the key hole (travel 0.35)", S.CAP["base"] - S.KEY_TRAVEL - back_hi),
        (f"cap shift room in its key hole ({cap_room:.2f}) over per-key RSS {cap_err:.2f}", cap_room - cap_err),
        (f"PCB hole round the screw, board {board:.2f} off with the caps", pcb_r_lo - S.SCREW_D / 2 - in_pcb),
        (f"metal spacer (play {sp_play:.2f}) inside the 3.6 mm copper keep-out",
         3.6 - sp["od"] / 2 - in_pcb - sp_play),
        ("spacer overlaps the PCB round its widest hole, centred", sp["od_min"] / 2 - pcb_r_hi),
        ("boss top bears on the PCB all round its hole (MJF -0.15)",
         MM.BOSS_R - pt["body_hole"] - offset - in_pcb - pcb_r_hi),
        ("PCB fits the cavity (MJF -0.4 %, outline +0.2), per side", cav),
        ("body screw hole round the screw, body and plate tolerance",
         MM.SCREW_CLEAR - pt["body_hole"] - S.SCREW_D / 2 - pt["body"] - pt["plate"]),
        (f"washer (OD {2 * r_w_min:.2f} min) bears all round the widest body hole", r_w_min - w_off - r_hole_max),
        ("washer lies flat in the counterbore wherever the screw sits",
         MM.HEAD_R - pt["body_hole"] - r_w_max - max(0.0, offset - MM.WASHER_PLAY)),
        ("pan head (dk 4.7 min) covers the washer bore",
         sc["head_d_min"] / 2 - S.WASHER["bore_max"] / 2 - MM.WASHER_PLAY),
        ("counterbore to the outer body wall (MJF), beyond 0.8", corner - 0.8),
        ("body boss wall around the counterbore, beyond 0.8 (MJF)", MM.BOSS_R_LOW - MM.HEAD_R - 0.8),
        ("boss above the counterbore seat, beyond 0.8", -S.PCB_T - S.SEAT_Z - 0.8),
        ("body walls under the plate, worst (MJF, PCB, spacer), beyond 0.2", wall_gap - 0.2),
        (f"full thread engaged, any stack ({n_lo} to {n_hi} washers), beyond 2 turns", engaged - S.ENGAGE_MIN),
        (f"washers: longest stack, screw stopping at the thread end, needs {n_hi} of {S.WASHERS_MAX}",
         (S.WASHERS_MAX - n_hi + 0.5) * wt),
        (f"{S.WASHERS_MAX} washers and a pan head recessed, front mounts, deep seat", head_lo - boss_floor),
        ("thread mill runout under the full thread, beyond 1 pitch", floor_lo - T["thread_depth"] - S.PITCH),
        ("plate left in front of the deepest hole floor, thin plate, beyond 0.6", t_min - floor_hi - 0.6),
        ("floor left over the steel plate recess, beyond 0.8",
         MM.Z_FLOOR_TOP - MM.z_bottom(stl["y0"] + stl["d"]) - stl["depth"] - 0.8),
        ("foot pad inside the steel plate notch, beyond 0.5", notch - 0.5),
        (f"foot pad round a {MM.FOOT_D:.0f} mm foot, per side, beyond 0.5", (MM.FOOT_PAD - MM.FOOT_D) / 2 - 0.5),
        (f"body: no void under 0.8 mm deeper than 0.4 (worst at {void_at})", 0.4 - void),
        (f"body: no wall under 0.8 mm deeper than 0.4 (worst at {wall_at})", 0.4 - wall),
        (f"assembly blocks ({S.ASSEMBLY_BLOCK:.0f}) over the shaft tips, beyond 3", S.ASSEMBLY_BLOCK - protrude - 3),
        ("plate edge strip free for the blocks, beyond 8", edge - 8),
        ("highest LED (5.3 +0.4) under the lowest plate back", S.PLATE_Z0 - sp_tol - led_hi),
        ("glued light pipe over the highest LED, thin plate, long pipe",
         face_lo - (pp["len"] + pp["len_tol"]) - led_hi),
        ("light pipe slip fit, beyond anodising (2 x 0.025)", pp["clear"] - 0.05),
    ]
    for name, d in S.LIGHT_HOLES.items():
        (lx, ly), _, _ = B.LEDS[name]
        rows.append((f"{name} snap-off stub inside the hole", (d - pp["clear"]) / 2 - pp["neck_d"] / 2))
        web = min(rrect_sd(lx - x, ly - y, *S.KEY_HOLE) for x, y in caps) - d / 2
        rows.append((f"{name} light hole web to the next key hole, beyond 0.5", web - 0.5))
    # RANGE tilted fully: the low edge of the skirt must stay above the plate. The pivot height is not in the
    # datasheet, so check it anywhere between the body and the hub top.
    edge_z = S.PLATE_Z1 + rk["z0"]
    a = math.radians(S.RKJXT_TILT)
    for pz in (6.0, S.RKJXT_BODY, S.RKJXT_HUB_TOP):
        low = pz + (edge_z - pz) * math.cos(a) - rk["skirt_d"] / 2 * math.sin(a)
        rows.append((f"RANGE skirt over plate at {S.RKJXT_TILT:.0f} deg, pivot z {pz}, high plate",
                     low - S.PLATE_Z1 - top_tol))
    for n, v in rows:
        print(f"  {n:72s} {v:5.2f} mm {'OK' if v > 0 else 'FAIL'}")
    assert all(v > 0 for _, v in rows)


if __name__ == "__main__":
    clearances()
