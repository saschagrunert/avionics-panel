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

assert S.PCB_HOLE == B.MOUNT_HOLE, "the board's mounting holes must be the ones the glued standoffs need"


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
for sx in (-1, 1):                                          # side lugs: 13.1 across (PEC11D drawing)
    part(ax, sx * S.EC11_LUGS / 2 - (sx > 0) * 0.7, 0, 0.7, S.EC11_BODY, fc="#cfcfcf")
part(ax, -S.SLEEVE_D / 2, S.EC11_BODY, S.SLEEVE_D, S.SLEEVE_TOP - S.EC11_BODY)
part(ax, -S.OUTER_D / 2, S.SLEEVE_TOP, S.OUTER_D, S.OUTER_TOP - S.SLEEVE_TOP)
part(ax, -S.SLOT_W / 2, S.OUTER_TOP - S.SLOT_LEN, S.SLOT_W, S.SLOT_LEN, fc="white")
part(ax, -S.INNER_D / 2, S.OUTER_TOP, S.INNER_D, S.INNER_TOP - S.OUTER_TOP)
part(ax, S.INNER_FLAT - S.INNER_D / 2, S.INNER_TOP - S.FLAT_LEN, S.INNER_D - S.INNER_FLAT, S.FLAT_LEN, fc="white")
OUTER_SOLID, INNER_SOLID = K.outer_knob(), K.inner_knob()      # built once: the drawing and clearances() use them
draw(ax, OUTER_SOLID, 0, "k", dz=S.PLATE_Z1 + S.OUTER_KNOB["z0"])
draw(ax, INNER_SOLID, 0, "k", dz=S.PLATE_Z1 + S.INNER_KNOB["z0"])
ax.set_title("ALT/HDG dual knob on PEC11D-4120F-S0015")

# ---- RANGE ----
ax = axes[1]
cx, cy = PS.P(*B.RANGE)
draw(ax, plate, cy, "#1f5fa0", dx=-cx, dz=S.PLATE_Z0)
part(ax, -12, -S.PCB_T, 24, S.PCB_T, fc="#c8d8c0")
part(ax, -S.RKJXT_FOOT / 2, 0, S.RKJXT_FOOT, S.RKJXT_FRAME_GAP)   # foot and base frame (Alps' STEP)
part(ax, -S.RKJXT_FRAME / 2, S.RKJXT_FRAME_GAP, S.RKJXT_FRAME, 2.55 - S.RKJXT_FRAME_GAP)
part(ax, -S.RKJXT_FLATS / 2, 0, S.RKJXT_FLATS, S.RKJXT_BODY)  # octagon above z 4: 15.73 across flats
part(ax, -S.RKJXT_HUB[0] / 2, S.RKJXT_BODY, S.RKJXT_HUB[0], S.RKJXT_HUB_TOP - S.RKJXT_BODY)   # hub (chamfer not drawn)
part(ax, -S.LEVER_D / 2, S.LEVER_Z0, S.LEVER_D, S.LEVER_Z1 - S.LEVER_Z0)
RANGE_SOLID = K.range_knob()
draw(ax, RANGE_SOLID, 0, "k", dz=S.PLATE_Z1 + S.RANGE_KNOB["z0"])
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
part(ax, key_dy - S.CAP["h"] / 2, S.CAP["base"], S.CAP["h"], S.CAP["height"], fc="#555", ec="#222")   # key cap, plunger
pipe = move(K.light_pipe("SHIFT"), 0, 0, 0)
tp = gp_Trsf(); tp.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
draw(ax, BRepBuilderAPI_Transform(pipe, tp, True).Shape(), 0, "k", dx=0, dz=S.PIPE["z0"])
ax.set_title("SHIFT light pipe\n(front of the panel on the left)")

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


def cap_shift_room(grow=0.0, turn=0.0):
    """how far a key cap, turned by turn (deg) on its plunger, can shift in its key hole (grown by grow on width
    and height) before it touches: (least, most) over all directions (0 when it does not fit at all)."""
    c, (hw, hh, hr) = S.CAP, S.KEY_HOLE
    hole = (hw + grow, hh + grow, hr + grow / 2)
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    ox = (c["w"] / 2 - c["r"]) * np.sign(np.cos(t)) + c["r"] * np.cos(t)     # cap outline, corners dense
    oy = (c["h"] / 2 - c["r"]) * np.sign(np.sin(t)) + c["r"] * np.sin(t)
    ca, sa = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    ox, oy = ox * ca - oy * sa, ox * sa + oy * ca
    rooms = []
    for a in np.linspace(0, 2 * np.pi, 144, endpoint=False):
        lo, hi = 0.0, 2.0
        for _ in range(30):
            d = (lo + hi) / 2
            inside = rrect_sd(ox + d * np.cos(a), oy + d * np.sin(a), *hole).max() <= 0
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


def raster_section(tri, axis, value, res, grid=False):
    """solid mask of a closed mesh cut by the plane coordinate[axis] = value (even-odd fill on a res grid); with
    grid, also the plane coordinates (u, v) of every pixel centre."""
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
    mask = (np.cumsum(tog, 1)[:, :nu] % 2) == 1
    if grid:
        return mask, np.meshgrid(u0 + (np.arange(nu) + 0.5) * res, v0 + (np.arange(nv) + 0.5) * res)
    return mask


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


def thin_depth(mask, res, outside, gap=0.8, ignore=None):
    """deepest point of any part of mask narrower than gap: the pixels a disk of dia gap cannot reach, measured
    along the mask to the nearest reachable pixel (pixels in ignore do not count). A square corner gives about
    0.2."""
    r = int(round(gap / 2 / res))
    disk = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1) if dy * dy + dx * dx <= r * r]
    opened = _shifted(_shifted(mask, disk, True, outside), disk, False) & mask
    thin = mask & ~opened
    if ignore is not None:
        thin &= ~ignore
    cross = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    cover, steps = opened, 0
    while (thin & ~cover).any() and steps < 30:
        cover = _shifted(cover, cross, False) & mask
        steps += 1
    return steps * res


def body_thin(tri, res=0.1):
    """deepest thin void, deepest thin wall (0.8) and deepest wall under JLC3DP's 2.0 mm for large MJF parts
    (1.9: a 2.0 wall is 20 pixels, which a 21 pixel disk does not fit) over sections through the body mesh tri
    (board frame), with where."""
    ux = B.USB_X
    planes = [(2, z) for z in (-2.5, -4.0, -6.0, -6.5, -7.0, -7.7, -8.3, -9.0, -10.5, -12.0, -13.5)]
    uw = (MM.USB_OPEN["w"] + MM.USB_KEEP[0]) / 4        # in the walls beside the USB-C opening
    planes += [(0, x) for x in (3.5, 9.0, 15.5, 22.5, 54.0, 85.0, 112.0, ux - uw, ux, ux + uw, B.BOOT[0],
                                150.0, 156.5)]
    planes += [(1, y) for y in (-1.5, 0.5, 2.0, 3.5, 6.7, 20.0, 40.0, 47.8, 55.5, 57.0)]
    void, wall, wall2 = (0.0, "none"), (0.0, "none"), (0.0, "none")
    keep_r = MM.BOSS_R_LOW + 0.5        # the screw bosses: fastener features, checked against 1.5 by their own rows
    for axis, value in planes:
        solid, (gu, gv) = raster_section(tri, axis, value + 1e-3, res, grid=True)
        where = f"{'xyz'[axis]} {value:g}"
        dv = thin_depth(~solid, res, True)
        # walls only in x and y sections: a z section cuts the 6 deg bottom faces at a slant, so their edges
        # look like slivers there that are not thin in 3D
        dw = thin_depth(solid, res, False) if axis != 2 else 0.0
        boss = np.zeros(solid.shape, bool)
        for mx, my in B.MOUNTS:
            boss |= np.hypot(*((mx - value, my - gu) if axis == 0 else (mx - gu, my - value))) < keep_r
        dw2 = thin_depth(solid, res, False, 1.9, boss) if axis != 2 else 0.0
        void = (dv, where) if dv > void[0] else void
        wall = (dw, where) if dw > wall[0] else wall
        wall2 = (dw2, where) if dw2 > wall2[0] else wall2
    return void, wall, wall2


def crossings(shape, x):
    """heights where the vertical line at (x, 0) enters or leaves the solid (its XZ section), sorted."""
    zs = []
    for px, pz in section(shape, 0.0):
        for (x0, z0), (x1, z1) in zip(zip(px, pz, strict=True), zip(px[1:], pz[1:], strict=True), strict=False):
            if (x0 - x) * (x1 - x) < 0:
                zs.append(z0 + (z1 - z0) * (x - x0) / (x1 - x0))
    zs.sort()
    assert zs and len(zs) % 2 == 0, f"no clean section at x {x}"
    return zs


def solid_height(shape, x):
    """how much of the vertical line at (x, 0) lies inside the solid."""
    zs = crossings(shape, x)
    return sum(b - a for a, b in zip(zs[0::2], zs[1::2], strict=True))


def d_bore_len(shape, d, flat):
    """length of the D flat in a knob's D bore (flat towards +x, bore end on the axis), measured on the solid: from
    the bore end on the axis down to where the resin behind the flat ends, on a line halfway between the flat and
    the bore wall."""
    end = crossings(shape, 0.0)[0]                       # the axis enters the resin at the bore end
    x = flat / 2                                         # halfway from the flat (flat - d / 2) to the wall (d / 2)
    starts = [z for z in crossings(shape, x)[0::2] if z < end]
    return end - max(starts)


def first_cap(name):
    """triangles (n, 3, 3) of the first cap in the set's generated OBJ (caps-<set>.zip, as ordered); it sits at
    the origin of the print grid, the next one 16 mm away."""
    import zipfile
    base = f"avionics-panel-rev1-caps-{name}"
    with zipfile.ZipFile(HERE / f"{base}.zip") as z:
        lines = z.read(f"{base}.obj").decode().splitlines()
    V = np.array([[float(t) for t in ln.split()[1:4]] for ln in lines if ln.startswith("v ")])
    F = np.array([[int(t.split("/")[0]) - 1 for t in ln.split()[1:4]] for ln in lines if ln.startswith("f ")])
    near = np.all(np.abs(V[:, :2]) < 8.0, axis=1)
    return V[F[near[F].all(axis=1)]]


def ray_hit(tri, o, d):
    """distance along the ray o + t d to the nearest triangle it crosses (Moller-Trumbore), or inf."""
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    pv = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, pv)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    tv = o - tri[:, 0]
    u = np.einsum("ij,ij->i", tv, pv) * inv
    qv = np.cross(tv, e1)
    v = (qv @ d) * inv
    t = np.einsum("ij,ij->i", e2, qv) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9)
    return t[hit].min() if hit.any() else math.inf


def ray_hits(tri, origins, d):
    """ray_hit for each origin along the same direction d."""
    return np.array([ray_hit(tri, np.asarray(o, float), np.asarray(d, float)) for o in origins])


def ring(cx, cy, z, r, n=72):
    """n points on a horizontal circle of radius r round (cx, cy) at height z, and their outward directions."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    dirs = np.stack([np.cos(a), np.sin(a), np.zeros(n)], 1)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, z)], 1), dirs


def near(tri, x, y, r):
    """the triangles whose xy bounding box comes within r of (x, y): keeps the ray casts below fast."""
    lo, hi = tri[:, :, :2].min(1), tri[:, :, :2].max(1)
    return tri[(lo[:, 0] < x + r) & (hi[:, 0] > x - r) & (lo[:, 1] < y + r) & (hi[:, 1] > y - r)]


def body_measures(tri):
    """measured on the body mesh (board frame) at the four screw bosses: the counterbore radius and the boss
    wall round it towards the cavity in the PCB room (between the floor and the counterbore seat), the PA12
    between the seat and the PCB, and the flat pad round each foot (radius on the bottom plane before it steps
    into the hollow or the steel plate recess)."""
    z = (MM.Z_FLOOR_TOP + S.SEAT_Z) / 2
    cb, wall, seat = [], [], []
    for mx, my in B.MOUNTS:
        tri_m = near(tri, mx, my, 15.0)
        pts, dirs = ring(mx, my, z, 0.0)
        r_cb = min(ray_hit(tri_m, p, d) for p, d in zip(pts, dirs, strict=True))
        pts, dirs = ring(mx, my, z, r_cb + 0.01)
        cb.append(r_cb)
        # towards the cavity only (within 60 deg of the board centre); towards the corner the boss runs into the
        # outer walls, which the counterbore-to-outer-wall row checks
        to_c = np.array([B.W / 2 - mx, B.H / 2 - my]) / math.hypot(B.W / 2 - mx, B.H / 2 - my)
        inward = dirs[:, :2] @ to_c > 0.5
        wall.append(min(ray_hit(tri_m, p, d) for p, d in zip(pts[inward], dirs[inward], strict=True)) + 0.01)
        pts, _ = ring(mx, my, -S.PCB_T - 0.01, (MM.SCREW_CLEAR + MM.HEAD_R) / 2, 24)
        seat.append(ray_hits(tri_m, pts, (0, 0, -1)).min() + 0.01)
    pads = []
    for fx, fy in MM.FEET:
        tri_f = near(tri, fx, fy, 10.0)

        def flat(j, fx=fx, fy=fy, tri_f=tri_f):
            """the ring of radius 0.05 j round the foot on the bottom plane"""
            pts, _ = ring(fx, fy, 0.0, 0.05 * j, 32)
            pts[:, 2] = [MM.z_bottom(y) - 1.0 for y in pts[:, 1]]
            return np.abs(ray_hits(tri_f, pts, (0, 0, 1)) - 1.0).max() <= 0.02   # not off the bottom plane

        # the last ring on the plane, in 0.05 mm steps up to 8 mm; the pad is flat out to where it steps into the
        # hollow or the recess, so bisect as rib_width() does: lo on the plane (radius 0 is), hi off it
        lo, hi = 0, 160
        if flat(hi):
            lo = hi
        while hi - lo > 1:
            mid = (lo + hi) // 2
            lo, hi = (mid, hi) if flat(mid) else (lo, mid)
        pads.append(0.05 * lo)
    return min(cb), min(wall), min(seat), min(pads)


def plate_measures(tri):
    """measured on the plate mesh (plate frame, back face at z 0): the narrowest encoder pocket across its lugs
    (along x, 1 mm into the pocket) and the shallowest standoff pocket."""
    widths = []
    for name in ("ALTHDG", "FREQ", "FMS"):
        cx, cy = PS.P(*getattr(B, name))
        widths.append(sum(ray_hit(tri, np.array([cx, cy, 1.0]), np.array([sx, 0.0, 0.0])) for sx in (-1.0, 1.0)))
    depths = [ray_hit(tri, np.array([*PS.P(mx, my), -1.0]), np.array([0.0, 0.0, 1.0])) - 1.0 for mx, my in B.MOUNTS]
    return min(widths), min(depths)


def rib_width(name, z=1.5):
    """width of the first rib (along +x) of the generated cap of set name, z over the socket mouth: rays along +x
    hit the rib face well inside the 3.8 mm bore, or the bore wall beside the rib."""
    tri, R = first_cap(name), S.CAP_SOCKET["d"] / 2

    def on_rib(y):
        return ray_hit(tri, np.array([0.0, y, z]), np.array([1.0, 0.0, 0.0])) < math.sqrt(R * R - y * y) - 0.05
    lo, hi = 0.0, 1.0                                   # 1.0: short of the next rib (at 90 deg)
    assert on_rib(lo) and not on_rib(hi), f"cap set {name}: no rib along +x"
    for _ in range(20):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if on_rib(mid) else (lo, mid)
    return 2 * lo


def solid_radius(shape):
    """largest radius of a solid of revolution about z (its XZ section)."""
    return max(max(abs(x) for x in xs) for xs, _ in section(shape, 0.0))


def rib_profile(name, dz=0.02):
    """the generated cap's ribs, measured: (z, rib circle diameter) where all ribs touch the plunger's cone line,
    and the largest deviation of the rib circle from the set's cone (stack.cap_rib_d) there."""
    tri, sk = first_cap(name), S.CAP_SOCKET
    hs, R = sk["depth"], sk["d"] / 2
    zs, ds, dev = [], [], []
    for z in np.arange(dz, hs - dz / 2, dz):
        r = [ray_hit(tri, np.array([0.0, 0.0, z]), np.array([math.cos(a), math.sin(a), 0.0]))
             for a in np.radians(sk["rib_angles"])]
        if max(r) < R - 0.05 and z >= sk["lead"]:          # on every rib, above the lead-in
            zs.append(z); ds.append(2 * np.mean(r))
            dev.append(max(abs(2 * x - S.cap_rib_d(name, hs - z)) for x in r))
    assert zs, f"cap set {name}: no ribs found in the generated socket"
    return np.array(zs), np.array(ds), max(dev)


def cap_texture():
    """the caps' texture as ordered (caps-A.zip; every set has the same one), RGB array."""
    import io
    import zipfile

    from PIL import Image
    base = "avionics-panel-rev1-caps-A"
    with zipfile.ZipFile(HERE / f"{base}.zip") as z:
        return np.asarray(Image.open(io.BytesIO(z.read(f"{base}.png"))).convert("RGB"))


def legend_strokes(gap=S.LEGEND_STROKE_MIN):
    """Legend strokes on the generated texture: in each cap's cell, how far coloured ink that a disk of dia gap
    cannot cover reaches (thin_depth): a stroke under gap shows up over its whole length, a corner or an arrow
    tip only over a fraction of gap. The worst cap and that depth."""
    tex = cap_texture()
    cell = 512                                                     # make_caps.py: 8 x 8 cells of 512 px
    res = max(S.CAP["w"], S.CAP["h"]) / cell                       # mm per pixel
    labels = [label for row in S.KEY_LEGENDS for label, _ in row]
    worst = (0.0, "none")
    pad = int(gap / res) + 3
    for k, label in enumerate(labels):
        x0, y0 = (k % 8) * cell, (k // 8) * cell
        ink = tex[y0:y0 + cell, x0:x0 + cell].max(axis=2) > 128
        if not ink.any():
            continue
        ys, xs = np.nonzero(ink)
        m = np.pad(ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1], pad)
        d = thin_depth(m, res, False, gap)
        worst = max(worst, (d, label))
    return worst


def legend_front(label):
    """how far the label's ink reaches from the cap centre towards the front edge (mm), on the generated texture
    (texture rows run from the back edge down to the front edge)"""
    tex, cell = cap_texture(), 512
    res = max(S.CAP["w"], S.CAP["h"]) / cell
    k = [lab for row in S.KEY_LEGENDS for lab, _ in row].index(label)
    x0, y0 = (k % 8) * cell, (k // 8) * cell
    ys = np.nonzero(tex[y0:y0 + cell, x0:x0 + cell].max(axis=2) > 128)[0]
    return (ys.max() + 1 - cell / 2) * res


def cap_rows(face_lo, bow_dn):
    """key cap rows: rigid ribs on the plunger cone measured on the generated caps, four fit sets against the
    print tolerance, set marks, tactile bars and legends against JLC3DP's minimums. The plate at the key nearest
    its middle stands up to bow_dn lower (bowed towards the board)."""
    sk, c = S.CAP_SOCKET, S.CAP
    hs = sk["depth"]
    part_tol, hole_tol = 0.2, 0.3                                  # WJP: outline and holes, on the diameter
    lo_i, hi_i = S.CAP_GRIP
    sizes = sorted(S.CAP_SETS.values())
    step = max(b - a for a, b in zip(sizes, sizes[1:], strict=False))   # the widest step between two sets
    # interference on a true print (diametral) at the socket mouth, from the design: the sets' print coverage
    fit = {n: S.plunger_d(hs) - S.cap_rib_d(n, hs) for n in S.CAP_SETS}
    # set dimples: walls to the socket bore and to the cap outline, nominal and at the worst print
    mk, bar = S.CAP_MARK, S.CAP_BAR
    to_socket = min(math.hypot(x, y) - sk["d"] / 2 for x, y in mk["pos"]) - mk["d"] / 2
    to_edge = min(-rrect_sd(np.array(x), np.array(y), c["w"], c["h"], c["r"]) for x, y in mk["pos"]) - mk["d"] / 2
    dim_wall = min(to_socket, to_edge)
    dim_worst = min(to_socket - hole_tol, to_edge - part_tol / 2 - hole_tol / 2)
    ink_d, ink_at = legend_strokes()
    rib_w = min(rib_width(n) for n in S.CAP_SETS)
    rows = [
        (f"cap socket ribs {rib_w:.2f} wide (measured on the generated caps), on the socket wall over their "
         "length, beyond 1.0 (WJP)", rib_w - 1.0),
        (f"cap wall round the {sk['d']} mm socket (narrow sides), outline -{part_tol}, bore +{hole_tol}, beyond 1.0 "
         "(WJP)", (c["h"] - part_tol - sk["d"] - hole_tol) / 2 - 1.0),
        (f"cap set dimples {mk['d']} across, {mk['depth']} deep, beyond 0.8 (JLC3DP engraved detail)",
         min(mk["d"], mk["depth"]) - 0.8),
        (f"cap set dimples: wall to the socket and the outline ({dim_wall:.2f}), beyond 1.0 (WJP)", dim_wall - 1.0),
        (f"cap set dimples: wall at the worst print (outline -{part_tol}, socket and dimple +{hole_tol}), beyond "
         "0.8", dim_worst - 0.8),
        (f"tactile bars {bar['d']} wide, beyond 0.8 (JLC3DP embossed detail; only {bar['proud']} proud, see stack.py)",
         bar["d"] - 0.8),
        (f"front tactile bar ({bar['proud']} proud) hides none of the SHIFT and DN legends from "
         f"{S.CAP_VIEW_DEG:.0f} deg",
         min(S.CAP["h"] / 2 - S.CAP["cham"] - legend_front(lab) - bar["inset"] - bar["d"] / 2
             for lab in ("SHIFT", "DN")) - bar["proud"] / math.tan(math.radians(S.CAP_VIEW_DEG))),
        (f"cap legend strokes at least {S.LEGEND_STROKE_MIN} wide (WJP colour): thinner ink reaches {ink_d:.2f} "
         f"(on {ink_at}), corners and tips only, within 0.25", 0.25 - ink_d),
        (f"cap bore clears the plunger between the ribs (bore {sk['d']} -{hole_tol}, plunger {S.plunger_d(hs):.2f} "
         "at the mouth)", (sk["d"] - hole_tol - S.plunger_d(hs)) / 2),
        (f"cap seats on the plunger top: cap bottom over the switch body ({S.SWITCH_BODY_TOP:.1f}), pressed",
         c["base"] - S.KEY_TRAVEL - S.PLUNGER_TOP_TOL - S.SWITCH_BODY_TOP),
        # The plate bowed towards the board at the key nearest its middle, the board taken flat: a board bowed
        # towards the plate (PCB_BOW, SUPPORT_LIFT) lifts the caps in the middle by up to 0.15, and with it the
        # socket ceiling, a cosmetic limit (the socket stays inside the cap). The pressed cap's row is in
        # clearances(), for a firm press (stack.PRESS_FIRM).
        (f"cap socket ceiling (on the plunger top, +{S.PLUNGER_TOP_TOL}) under the lowest plate face, plate bowed "
         f"{bow_dn:.3f} down there", face_lo - bow_dn - (S.PLUNGER_TOP + S.PLUNGER_TOP_TOL)),
        (f"cap sets' grip windows ({lo_i} to {hi_i} interference) overlap from one set to the next (step {step:.2f})",
         (hi_i - lo_i) - step),
    ]
    # the generated caps (caps-<set>.zip), one per set, cut by rays from the socket axis along every rib
    for n in S.CAP_SETS:
        zs, ds, dev = rib_profile(n)
        i = S.plunger_d(hs - zs[0]) - ds[0]                        # interference at the lowest contact
        rows += [
            (f"cap set {n} as built: ribs {ds[0]:.2f} to {ds[-1]:.2f} (interference {i:.2f}), off the set's cone "
             f"by {dev:.3f}, within 0.01", 0.01 - dev),
            (f"cap set {n} as built: ribs touch the cone over {zs[-1] - zs[0]:.2f} mm (cannot rock), beyond 2.0",
             zs[-1] - zs[0] - 2.0),
            (f"cap set {n} as built: ribs stop {hs - zs[-1]:.2f} under the ceiling, below the plunger's rounded "
             f"edge ({S.PLUNGER['dz0']})", hs - zs[-1] - S.PLUNGER["dz0"]),
        ]
    # print error e (rib circle printed larger by e): interference i - e; the best set's margin to CAP_GRIP
    e_lo, e_hi = S.CAP_PRINT
    worst = min(max(min(f - e - lo_i, hi_i - (f - e)) for f in fit.values())
                for e in np.linspace(e_lo, e_hi, 301))
    rows.append((f"cap sets grip rib circles printed {-e_lo:.2f} small to {e_hi:.2f} large (one of {len(fit)} within "
                 f"{lo_i} to {hi_i})", worst))
    return rows


def key_hole_max():
    """the key hole at its largest (+KEY_HOLE_TOL on width and height, after anodising)."""
    (w, h, r), up = S.KEY_HOLE, S.KEY_HOLE_TOL[0]
    return w + up, h + up, r + up / 2


def plate_bow(x, y):
    """how far a bowed plate stands off the plane of its four standoffs at board point (x, y), per mm of bow read
    on glass (docs/mechanics.md, On arrival): the worst of a dome (the reading is the plate's corners against its
    middle), a bow along the plate (its ends against its middle) and a bow across it (its long edges against its
    middle line)."""
    hx, hy = B.W / 2 + S.OVH, B.H / 2 + S.OVH                          # plate half length and width
    sx, sy = B.W / 2 - B.MOUNTS[0][0], B.H / 2 - B.MOUNTS[0][1]         # standoffs off the middle
    dx, dy = x - B.W / 2, y - B.H / 2
    dome = (sx * sx + sy * sy - dx * dx - dy * dy) / (hx * hx + hy * hy)
    along = (sx * sx - dx * dx) / (hx * hx)
    across = (sy * sy - dy * dy) / (hy * hy)
    return max(dome, along, across, 0.0)


def rkjxt_seat(step=0.25):
    """worst seat tilt (rise per mm) of an RKJXT whose four gauge spots (stack.RKJXT_SPOT) each stand at most
    RKJXT_SEAT proud of a seated part, and how far that lifts the corners of its octagon (circumscribed, +RKJXT_TOL).
    Tilted towards u, the part rests on the far edge of its foot; a blade reads the lowest gap on its spot, so the
    spot whose nearest point reaches furthest along u bounds the tilt."""
    g, sp, e = S.RKJXT_SEAT, S.RKJXT_SPOT, S.RKJXT_FRAME / 2
    foot, corner = S.RKJXT_FOOT / 2, (S.RKJXT_ACROSS + S.RKJXT_TOL) / 2
    # the spot on the +x side (left of its middle, seen from outside, is -y), turned onto the other three sides
    spot = np.array([(x, -y) for x in (e - sp["depth"], e) for y in sp["lat"]])
    spots = [spot @ np.array([[math.cos(t), math.sin(t)], [-math.sin(t), math.cos(t)]])
             for t in np.radians((0, 90, 180, 270))]
    tilt, lift = 0.0, g
    for a in np.radians(np.arange(0.0, 360.0, step)):
        u = np.array([math.cos(a), math.sin(a)])
        t = g / (foot + max(float((p @ u).min()) for p in spots))
        tilt, lift = max(tilt, t), max(lift, t * (foot + corner))
    return tilt, lift


def mjf(length):
    """JLC3DP MJF tolerance on a length (+-): 0.3 up to 100 mm, 0.4 % above."""
    return max(0.3, 0.004 * length)


def usb_rows():
    """USB-C socket and plug in the back wall opening (make_mech.USB_OPEN, carried up as a notch)."""
    u, place, hole = MM.USB_OPEN, 0.1, S.POS_TOL["body_hole"]    # J1 placement (JLCPCB), MJF on the opening
    # the board lies anywhere in the cavity (CLEAR). Its sideways play is set by its short edges against the
    # side walls: routed (+-0.2) without edge rails, but taken as V-cut (+-PCB_VCUT_TOL), the fallback should
    # JLCPCB put rails on them: at worst one of them is that much short.
    # Against a side wall the opening sits that far plus USB_X (or W - USB_X) from the board edge, and MJF puts
    # it within mjf() of that length from the wall: this also covers a body printed large, whose gap grows
    edge = MM.CLEAR + MM.PCB_VCUT_TOL
    float_ = edge + max(mjf(B.USB_X + MM.CLEAR), mjf(B.W - B.USB_X + MM.CLEAR))   # 0.9 + 0.51 (left wall)
    j1w, j1h = MM.J1_BODY
    bot = u["z"] - u["h"] / 2                            # opening bottom
    z_tol = mjf(-S.PCB_T - bot)                         # MJF: boss top (the PCB underside) to the opening bottom
    om_w, om_h = 12.35, 6.5                              # USB-C spec: plug overmould up to 12.35 x 6.5
    ow, oh, orr = u["w"] - 2 * hole, u["h"] - 2 * hole, u["r"] - hole
    zc = -S.PCB_T - j1h / 2 - u["z"]                    # plug centre, on the socket's middle, over the opening's
    # a square overmould (no corner radius) off centre by the float and J1 in x, J1 and the body height in z:
    # least clearance to the opening, whose top is open (the notch, as wide as the opening)
    xs = np.linspace(-om_w / 2, om_w / 2, 241)
    zs = np.linspace(-om_h / 2, om_h / 2, 131)
    ex = np.concatenate([xs, xs, np.full_like(zs, -om_w / 2), np.full_like(zs, om_w / 2)])
    ez = np.concatenate([np.full_like(xs, -om_h / 2), np.full_like(xs, om_h / 2), zs, zs])
    om = 1e9
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = ex + sx * (float_ + place), ez + zc + sz * (place + z_tol)
            sd = np.minimum(rrect_sd(x, z, ow, oh, orr), rrect_sd(x, z - 50, ow, 100, 0))   # opening and notch
            om = min(om, -sd.max())
    return [
        (f"USB-C socket ({j1w} wide, {-MM.J1_FACE:.2f} past the PCB edge) passes the wall notch: board "
         f"{float_:.2f} off (cavity, V-cut edge, MJF on the opening), J1 {place}, MJF -{hole}",
         ow / 2 - j1w / 2 - float_ - place),
        (f"USB-C socket ({j1h} high under the PCB, J1 {place}) over the opening bottom (MJF -{hole}, body "
         f"height {z_tol})", (-S.PCB_T - j1h - place - z_tol) - (bot + hole)),
        (f"USB-C socket ({j1h} high, J1 {place}) over the body floor under the PCB ({MM.UNDER} room, MJF "
         f"-{mjf(MM.UNDER)})", MM.UNDER - j1h - place - mjf(MM.UNDER)),
        (f"USB-C overmould ({om_w} x {om_h}, square) in the {u['w']} x {u['h']} R{u['r']} opening: board "
         f"{float_:.2f} off, J1 {place}, body height {z_tol}, MJF -{hole}", om),
    ]


def steel_row():
    """the optional steel plate (laser cut +-0.1) in its recess (MJF), per side: outline and between notches."""
    st, (rw, rd), laser = MM.STEEL, MM.STEEL_RECESS, 0.1
    n = st["notch"]
    gaps = [(rw - mjf(rw) - st["w"] - laser) / 2, (rd - mjf(rd) - st["d"] - laser) / 2,
            (rw - 2 * n - mjf(rw - 2 * n) - (st["w"] - 2 * n) - 2 * laser) / 2]
    return (f"steel plate ({st['w']:.0f} x {st['d']:.0f}, laser +-{laser}) in its {rw:.0f} x {rd:.0f} recess (MJF "
            f"-{mjf(rw):.2f} / -{mjf(rd):.1f}), and between notches, per side", min(gaps))


def pocket_web():
    """least plate left between a standoff pocket and any other plate feature or the plate edge."""
    r = S.STANDOFF_POCKET["d"] / 2 + S.STANDOFF_POCKET["d_tol"] / 2
    w, h, cr, _ = S.EC11_POCKET
    webs = []
    for mx, my in B.MOUNTS:
        d = [rrect_sd(mx - x, my - y, *key_hole_max()) for y in B.ROWS for x in B.COLS]
        d += [rrect_sd(mx - x, my - y, w, h, cr) for x, y in (B.ALTHDG, B.FREQ, B.FMS)]
        d += [math.hypot(mx - B.RANGE[0], my - B.RANGE[1]) - S.RANGE_POCKET[0] / 2]
        d += [math.hypot(mx - lx, my - ly) - S.LIGHT_HOLES[n] / 2 for n, ((lx, ly), _g, _c) in B.LEDS.items()]
        d += [-rrect_sd(mx - B.W / 2, my - B.H / 2, B.W + 2 * S.OVH, B.H + 2 * S.OVH, B.CORNER_R + S.OVH)]
        webs.append(min(d) - r)
    return min(webs)


def clearances():
    """clearances that must stay positive, with the inner knob pushed down; each one can fail."""
    ok, ik, rk = S.OUTER_KNOB, S.INNER_KNOB, S.RANGE_KNOB
    p, es = S.PUSH_TRAVEL, S.ENC_SPREAD
    resin = 0.1                                         # resin knob, key to counterbore and bore depths (+-)
    # ---- knob walls and radial clearances, worst case: resin diameters (JLC3DP) +-0.2 outside, +-0.3 on holes;
    # a knob's bore on its shaft at the loose variant, a hole printed large and the shaft at its low limit
    # (both shafts +0/-0.1 at most) can sit off centre by bore_play; the inner shaft off the outer one by ecc
    # (assumed: the PEC11D datasheet gives no concentricity) ----
    part_tol, hole_tol, shaft_tol, ecc = 0.2, 0.3, 0.1, 0.05
    loose = max(S.FIT, *S.FIT_VARIANTS.values())
    bore_play = (loose + hole_tol + shaft_tol) / 2
    fi, ring_r, cb_d = S.FLUTES["inner"], ok["d"] / 2, K.outer_counterbore_d()

    def flute_bottom(f, r, z, h):
        """radius of the flute bottoms z over the knob's bottom (the taper narrows the knob upwards)."""
        return r * (1 - f["taper"] * z / h) - f["depth"]

    def groove(f, r):
        """flute width at half depth at the knob top (the narrowest): the printed detail."""
        return math.pi * (r * (1 - f["taper"]) - f["depth"] / 2) / f["n"]

    # thinnest walls: the inner knob at the top of its recess, the outer rings at the top of the counterbore
    rec_bot = flute_bottom(fi, ik["d"] / 2, ik["recess_top"] - ik["z0"], ik["z1"] - ik["z0"])
    rings = sorted(set(S.OUTER_FLUTES.values()))
    cb_bot = {n: flute_bottom(S.FLUTES[n], ring_r, K.outer_counterbore_top(), ok["z1"] - ok["z0"]) for n in rings}
    fp, ff = S.FLUTES["outer"], S.FLUTES["outer_fms"]
    knurls = [(n, ring_r) for n in rings] + [("inner", ik["d"] / 2), ("range", rk["d"] / 2)]
    # ---- plate: back on the standoffs (6.0 +0.2/-0.1 over the PCB top), thickness +-0.1; depths from the back.
    # Anodising (stack.ANODISE): the pocket floors keep their place to the standoff ends, the back face sits up
    # to ANODISE / 2 lower over bare floors, the front face up to ANODISE higher over anodised ones ----
    gap_up, gap_dn = S.GAP_TOL
    t_min = S.PLATE_T - S.PLATE_T_TOL
    back_metal_lo = S.PLATE_Z0 - gap_dn                 # the back the pocket depths count from, lowest
    back_lo, back_hi = back_metal_lo - S.ANODISE / 2, S.PLATE_Z0 + gap_up   # the back face itself
    face_lo = back_metal_lo + t_min                     # unanodised (anodising only raises it)
    face_up = gap_up + S.PLATE_T_TOL + S.ANODISE        # plate face over its nominal height, worst
    # ---- positions: board offset from the caps, standoffs lined up with the PCB holes ----
    pt, sc, so, sp = S.POS_TOL, S.SCREW, S.STANDOFF, S.STANDOFF_POCKET
    cap_err = math.sqrt(sum(v * v for v in S.CAP_TOL.values()))
    cap_room = cap_shift_room()[0]                      # key hole +0.1/-0 after anodising: least at nominal
    cap_room_turn = cap_shift_room(turn=S.CAP_TURN)[0]   # the same cap turned on its plunger
    cap_room_max = cap_shift_room(S.KEY_HOLE_TOL[0])[1]   # most in the largest hole
    board = cap_room_max + pt["centring"]              # board offset the caps allow (the most, diagonally)
    hole = B.MOUNT_HOLE
    hole_lo, hole_hi = (hole - pt["npth_d"]) / 2, (hole + pt["npth_d"]) / 2
    off = hole_hi - sc["d_min"] / 2 + pt["thread"]     # standoff axis off the PCB hole axis: the screw's play
    float_min = (sp["d"] - S.ANODISE) / 2 - so["ac"] / 2    # standoff float in its pocket (anodised)
    keepout = B.MOUNT_KEEPOUT                         # pcb/check.py checks the copper against the same radius
    # ---- screws: head, one washer, counterbore seat, boss, PCB, standoff thread ----
    seat_tol, pcb_tol = S.STACK_TOL["counterbore"], S.STACK_TOL["pcb"]
    w, wt = S.WASHER, S.WASHER["t"]
    seat_pcb = -S.SEAT_Z                                # counterbore seat to the PCB top (boss 1.6 + PCB 1.6)
    tip_lo = (sc["L"] - sc["L_tol"]) - (wt + w["t_tol"]) - (seat_pcb + seat_tol + pcb_tol)
    tip_hi = (sc["L"] + sc["L_tol"]) - (wt - w["t_tol"]) - (seat_pcb - seat_tol - pcb_tol)
    engaged = tip_lo - sc["tip"] - so["chamfer"]
    plug = so["L"] - so["L_tol"] - S.PLUG_DEPTH          # wax plug in the plate end while gluing: its bottom
    # head and washer recessed: the bottom plane rises to the front, so take its highest point under the
    # counterbore (the washer stays inside it) at the front mounts, with MJF +0.3
    cb_hi = MM.HEAD_R + pt["body_hole"]
    boss_floor = max(MM.z_bottom(min(my + cb_hi, B.H + MM.o)) for _, my in B.MOUNTS) + seat_tol
    head_lo = (S.SEAT_Z - seat_tol) - (wt + w["t_tol"]) - sc["head_k"]
    # ---- washer on the body: slides on the screw, held over the hole by the counterbore wall ----
    r_hole_max = MM.SCREW_CLEAR + pt["body_hole"]
    offset = MM.SCREW_OFFSET                            # screw against the widest body hole wall
    r_w_min, r_w_max = w["od_min"] / 2, w["od"] / 2
    w_off = min(offset + MM.WASHER_PLAY, cb_hi - r_w_min)   # washer centre off the body hole centre, worst
    corner = min(-rrect_sd(mx - B.W / 2, my - B.H / 2, B.W + 2 * MM.o, B.H + 2 * MM.o, B.CORNER_R + MM.o)
                 for mx, my in B.MOUNTS) - cb_hi       # counterbore to the outer body surface
    cav_w_tol = mjf(B.H + 2 * MM.CLEAR)                             # MJF on the cavity width (61 mm)
    # width: routed long edges (economic variant), or the full variant's V-cut one after its rail comes off
    w_tol = max(MM.PCB_OUTLINE_TOL, MM.PCB_VCUT_TOL)
    cav = MM.CLEAR - w_tol / 2 - cav_w_tol / 2                       # per side
    cav_len = (B.W + 2 * MM.CLEAR) * (1 - MM.BODY_SCALE_TOL)        # the cavity length, printed small
    # length: routed short edges (no rails there in either variant), or V-cut ones sanded (rails added anyway)
    pcb_len = max(B.W + MM.PCB_OUTLINE_TOL, MM.PCB_SANDED_LEN)
    # ---- assembly, body ----
    caps = [(x, y) for y in B.ROWS for x in B.COLS]
    # ---- plate bow by position (plate_bow): up to PLATE_FLAT towards the board or away from it, each counted
    # where it costs a row; the body walls are worst at the middle of the long edges ----
    bow_key = max(plate_bow(x, y) for x, y in caps)
    bow_enc = max(plate_bow(*xy) for xy in (B.ALTHDG, B.FREQ, B.FMS))
    bow_rng = plate_bow(*B.RANGE)
    bow_wall = plate_bow(B.W / 2, -S.OVH)
    # a cap pressed firmly (stack.PRESS_FIRM): the board under it dips by up to PRESS_DIP and slopes by up to
    # PRESS_SLOPE (a plate model of the bare board, see stack.py), and the cap's bottom dips under the highest plate
    # back, bowed up. The slope tilts the cap with its plunger about the board's mid-plane, so the cap moves sideways
    # in its hole by its height over that plane times the slope, most at the face edge: more than a cap at the edge
    # of its per-key allowance has, so it may rub that edge on one side (documented, docs/mechanics.md). Two rows
    # prove it cannot catch or stick: tilted, it cannot touch both sides of its hole at once (its shadow over the
    # whole wall fits in the hole, turned and printed large), and while its side is free its bottom edge stands out
    # of the line of its side only by the dip times the slope, which the broken back edge (KEY_BACK_BREAK) leads
    # back in; while its side bears on the face edge, its bottom edge is pulled inside the hole outline.
    flex, slope = S.PRESS_DIP, S.PRESS_SLOPE
    cap_dip = max(0.0, back_hi + S.PLATE_FLAT * bow_key + flex
                  - (S.CAP["base"] - S.KEY_TRAVEL - S.PLUNGER_TOP_TOL))
    face_shift = (S.PLATE_Z1 + face_up + S.PLATE_FLAT * bow_key + S.PCB_T / 2 + flex) * slope
    wall_h = S.PLATE_T + S.PLATE_T_TOL + S.ANODISE                  # thick plate, both faces anodised
    cap_print = 0.2                                                 # WJP cap outline, on the size
    cap_room_wedge = cap_shift_room(-cap_print, S.CAP_TURN)[0]      # cap printed large, turned, smallest hole
    shadow = wall_h * math.tan(slope) + S.CAP["w"] * (1 / math.cos(slope) - 1)
    # face down, the shafts on parts seated within SEAT_GAP (RKJXT_SEAT), the face bowed towards them
    protrude = (max(S.INNER_TOP + S.ENC_TOL["ge10"], S.LEVER_Z1 + S.LEVER_TOL) + max(S.SEAT_GAP, S.RKJXT_SEAT)
                - face_lo + S.PLATE_FLAT * max(bow_enc, bow_rng))
    edge = min([min(y - S.CAP["h"] / 2, B.H - y - S.CAP["h"] / 2) for _, y in caps] +
               [min(y - S.SLEEVE_D / 2, B.H - y - S.SLEEVE_D / 2) for y in (B.ALTHDG[1], B.RANGE[1])]) + S.OVH
    stl, x0 = MM.STEEL, MM.steel_x0()
    fx, fy = MM.FEET[0]
    notch = min(x0 + stl["notch"] - (fx + MM.FOOT_PAD / 2), stl["y0"] + stl["notch"] - (fy + MM.FOOT_PAD / 2))
    body_tri = body_triangles()
    (void, void_at), (wall, wall_at), (wall2, wall2_at) = body_thin(body_tri)
    cb_r, boss_wall, seat_t, pad_r = body_measures(body_tri)
    ec_w, so_depth = plate_measures(mesh_triangles(plate))
    an = S.ANODISE
    # ---- seating (stack.SEAT_GAP, RKJXT_SEAT): an encoder stands up to SEAT_GAP proud at the edge of its base or
    # is tilted by that over it; the RKJXT's gauge spots stand up to RKJXT_SEAT proud (rkjxt_seat: the worst tilt,
    # about the far edge of its foot). Lifted: the top corners rise by the gap times their reach from the far base
    # edge (the encoder lugs reach past its body, the RKJXT octagon's corners past its gauge spots). Tilted: a
    # feature at height z moves z times the tilt sideways; inside the base edge the part tilts on it rises, past
    # that edge it dips by its reach past the edge times the tilt (the outer knob's rim past the encoder's base,
    # the RANGE skirt's rim past the RKJXT's foot). A lift only raises the knobs, which helps the rows over the
    # plate, so those take the part tilted. ----
    sg = S.SEAT_GAP
    tilt_e = sg / S.EC11_BASE
    lift_e = sg * (S.EC11_BASE + S.EC11_LUGS + S.ENC_TOL["ge10"]) / 2 / S.EC11_BASE   # lug corners: 0.054
    tilt_r, lift_r = rkjxt_seat()                                                    # octagon corners: 0.064
    dip_e = (ok["d"] - S.EC11_BASE) / 2 * tilt_e        # outer knob rim past the encoder's base edge: 0.011
    dip_r = (rk["skirt_d"] - S.RKJXT_FOOT) / 2 * tilt_r   # RANGE skirt rim past the RKJXT's foot
    # ---- light pipes glued flush, LEDs under them: the rows that take the board's bow, and the plate's flatness
    # in full (PLATE_FLAT; the other rows take plate_bow at their part) ----
    pp = S.PIPE
    led_hi = S.LED_TOP + S.LED_TOL[0] + S.SUPPORT_LIFT + S.PCB_BOW   # lifted by a post, bowed up
    lt_up, lt_dn = S.LIGHT_HOLE_TOL
    pd = S.POCKET_TOL
    # MJF wall height, PCB, lowest back face, bowed towards the walls
    wall_gap = S.WALL_GAP - (seat_tol + pcb_tol + S.PLATE_Z0 - back_lo) - S.PLATE_FLAT * bow_wall
    # ---- RANGE: knob height from the lever top (+-0.3) and its bore depth (resin) ----
    rk_lo = S.PLATE_Z1 + rk["z0"] - S.LEVER_TOL - resin    # knob bottom, lowest
    push_hi = S.RANGE_PUSH[0] + S.RANGE_PUSH[1]
    a = math.radians(S.RKJXT_TILT)
    pz = S.RKJXT_FULCRUM
    skirt_low = pz + (rk_lo - pz) * math.cos(a) - rk["skirt_d"] / 2 * math.sin(a)
    # the skirt rim on the side the knob tilts away from, seen from above: radius r at the rim height h rotated
    # by the tilt about the fulcrum reaches r cos(a) - (h - fulcrum) sin(a) from the hole axis; worst with the
    # highest knob (lever +, bore deep) and the smallest skirt print
    rk_hi = S.PLATE_Z1 + rk["z0"] + S.LEVER_TOL + resin    # knob bottom, highest
    # the fulcrum sits RKJXT_FULCRUM_OFF off the axis, on the side the lever tilts to: that moves the whole knob
    # and hub by off (1 - cos a) towards the tilt, and lifts the dipping side (taken on the axis: conservative)
    f_shift = S.RKJXT_FULCRUM_OFF * (1 - math.cos(a))
    # the highest knob also on a lifted RKJXT, and moved sideways at its skirt by a tilted one
    skirt_shift = (rk_hi + lift_r - pz) * math.sin(a) + f_shift + (rk_hi + lift_r) * tilt_r
    on_board = board + pt["plate"] + pt["pcb"] + S.ENC_ON_PINS   # an encoder's axis off its plate hole
    on_board_r = board + pt["plate"] + pt["pcb"] + S.RKJXT_ON_PINS   # the RKJXT's: it floats more on its pins
    # RKJXT hub (Alps' STEP) tilted 9 deg about the fulcrum: its full-width top edge sideways at the plate
    hub_r, hub_z = S.RKJXT_HUB[0] / 2, S.RKJXT_HUB[1]
    hub_out = hub_r * math.cos(a) + (hub_z - pz) * math.sin(a) + f_shift + (hub_z + lift_r) * tilt_r   # seat tilt
    arrow_in = S.RANGE_ART["arrow_r"] + min(u for u, _v in S.RANGE_ART["arrow"])   # pan arrows' inner ends
    gen = S.PLATE_GEN_TOL                               # ISO 2768-m on untoleranced plate sizes
    # RKJXT body corner (top edge at its widest) off the RANGE pocket's wall and floor, worst of each, and off
    # the floor corner radius the drawing allows (S.POCKET_FLOOR_R); anodising narrows the pocket, and its floor
    # keeps its height (see the plate above). The same for the encoder's side lugs in their pocket (measured on
    # the plate solid).
    fr = S.POCKET_FLOOR_R

    def floor_corner(side, top):
        return fr - math.hypot(fr - side, fr - top) if max(side, top) < fr else min(side, top)
    # each part seated, lifted (side as seated) and tilted (top as seated); the corner takes the worse of the two
    rk_side0 = (S.RANGE_POCKET[0] - gen - an - S.RKJXT_ACROSS - S.RKJXT_TOL) / 2 - on_board_r
    rk_top0 = back_metal_lo + S.RANGE_POCKET[1] - S.POCKET_TOL - (S.RKJXT_BODY + 0.3) - S.PLATE_FLAT * bow_rng
    rk_side, rk_top = rk_side0 - (S.RKJXT_BODY + 0.3) * tilt_r, rk_top0 - lift_r
    rk_corner = min(floor_corner(rk_side0, rk_top), floor_corner(rk_side, rk_top0))
    ec_side0 = (ec_w - gen - an - S.EC11_LUGS - S.ENC_TOL["ge10"]) / 2 - on_board
    ec_top0 = (back_metal_lo + S.EC11_POCKET[3] - S.POCKET_TOL - (S.EC11_BODY + S.ENC_TOL["lt10"])
               - S.PLATE_FLAT * bow_enc)
    ec_side, ec_top = ec_side0 - (S.EC11_BODY + S.ENC_TOL["lt10"]) * tilt_e, ec_top0 - lift_e
    ec_corner = min(floor_corner(ec_side0, ec_top), floor_corner(ec_side, ec_top0))
    face_hi = S.PLATE_Z1 + face_up                      # the bushing's highest point in its plate hole
    # ---- outer knob, in its own frame from the slot floor its key rests on ----
    slot_tol = S.ENC_TOL["lt10"]                        # slot width and depth, +-
    key_rss = math.hypot(es["slot"], resin)            # slot floor over the PCB and the key's height in the knob
    cb_top = K.outer_counterbore_top() - K.outer_key_z0() + resin   # counterbore top, highest
    shaft_top = S.SLOT_LEN - slot_tol                   # 6 mm shaft top over the slot floor, shallow slot
    knob_top = ok["z1"] - ok["z0"] - K.outer_key_z0()                # top of the knob's bore
    key_resin = 0.2                                     # key printed up to 0.2 wide
    # ---- RANGE skirt rim measured on the knob solid, just inside its edge ----
    rim = solid_height(RANGE_SOLID, rk["skirt_d"] / 2 - 0.05)
    d_len = d_bore_len(INNER_SOLID, S.INNER_D, S.INNER_FLAT)   # inner knob D bore, measured on the solid
    rows = [
        (f"outer knob over plate (face +{face_up:.3f}, bowed {S.PLATE_FLAT * bow_enc:.3f} up there, slot floor "
         f"+-{es['slot']:.2f} and key resin, RSS, rim {dip_e:.3f} down on a tilted encoder)",
         ok["z0"] - face_up - S.PLATE_FLAT * bow_enc - key_rss - dip_e),
        (f"outer knob grip on the 6 mm shaft (slot depth -{slot_tol}, resin), beyond 3.5",
         min(knob_top, shaft_top) - cb_top - 3.5),
        (f"outer knob key ({S.KEY_W} +{key_resin} resin) in the narrowest shaft slot ({S.SLOT_W} -{slot_tol})",
         S.SLOT_W - slot_tol - (S.KEY_W + key_resin)),
        (f"outer knob key face ({S.KEY_R}) into the slot past the 6 mm shaft (-{shaft_tol}), face printed "
         f"{hole_tol / 2} back, beyond 0.4", (S.OUTER_D - shaft_tol) / 2 - (S.KEY_R + hole_tol / 2) - 0.4),
        (f"outer knob key face clear of the {S.INNER_D} inner shaft in the slot: face {hole_tol / 2} proud, "
         f"loose knob {bore_play:.2f} off, shafts {ecc}", S.KEY_R - hole_tol / 2 - bore_play - ecc - S.INNER_D / 2),
        (f"outer knob counterbore over the bushing, key on the slot floor (+-{es['slot_sleeve']:.2f}, resin)",
         K.outer_counterbore_top() - K.outer_key_z0() + (S.OUTER_TOP - S.SLOT_LEN) - S.SLEEVE_TOP
         - es["slot_sleeve"] - resin),
        (f"inner knob over outer knob, pushed (shafts +-{es['inner_outer']:.2f}, inner bore depth and outer key "
         f"height +-{resin}, RSS)", ik["z0"] - p - ok["z1"] - math.sqrt(es["inner_outer"] ** 2 + 2 * resin ** 2)),
        ("inner recess over outer shaft top, pushed",
         ik["recess_top"] - p - (S.OUTER_TOP - S.PLATE_Z1) - es["inner_shaft"]),
        (f"inner recess ({ik['recess_d']}) round the 6 mm shaft, radial: recess -{hole_tol}, loose knob "
         f"{bore_play:.2f} off, shafts {ecc}", (ik["recess_d"] - hole_tol) / 2 - S.OUTER_D / 2 - bore_play - ecc),
        (f"outer counterbore ({cb_d:.1f}) round the bushing, radial: counterbore -{hole_tol}, bushing "
         f"+{S.ENC_TOL['lt10']}, loose knob off by {bore_play:.2f}",
         (cb_d - hole_tol) / 2 - (S.SLEEVE_D + S.ENC_TOL["lt10"]) / 2 - bore_play),
        (f"inner knob wall round the recess at the flute bottoms, OD -{part_tol}, recess +{hole_tol}, beyond 1.0",
         rec_bot - part_tol / 2 - (ik["recess_d"] + hole_tol) / 2 - 1.0),
        *[(f"outer ring wall ({n}) round the counterbore at the flute bottoms, OD -{part_tol}, hole "
           f"+{hole_tol}, beyond 1.0", cb_bot[n] - part_tol / 2 - (cb_d + hole_tol) / 2 - 1.0) for n in rings],
        *[(f"{n} knob flutes: groove {groove(S.FLUTES[n], r):.2f} wide at half depth at the (tapered) top, beyond 0.8",
           groove(S.FLUTES[n], r) - 0.8) for n, r in knurls],
        (f"inner knurl finer than the outer: pitch {2 * math.pi * ik['d'] / 2 / fi['n']:.2f} vs "
         f"{2 * math.pi * ring_r / fp['n']:.2f}, beyond 10 % (ratio)",
         (2 * math.pi * ring_r / fp["n"]) / (2 * math.pi * ik["d"] / 2 / fi["n"]) - 1.1),
        (f"FMS ring told apart by feel: flutes {ff['depth'] / fp['depth']:.1f} x as deep and "
         f"{fp['n'] / ff['n']:.2f} x the pitch of the others, beyond 1.5 x (ratio)",
         min(ff["depth"] / fp["depth"], fp["n"] / ff["n"]) - 1.5),
        ("outer ring beyond the inner knob, per side (measured on the knob solids), beyond 2.0 (Garmin 2.5)",
         solid_radius(OUTER_SOLID) - solid_radius(INNER_SOLID) - 2.0),
        (f"inner knob D bore ({d_len:.2f} up from the tip, measured on the knob solid) within the shortest D flat "
         f"({S.FLAT_LEN} -{S.ENC_TOL['lt10']}), bore depth +{resin}: the bore end sets the knob height",
         S.FLAT_LEN - S.ENC_TOL["lt10"] - d_len - resin),
        (f"encoder bushing ({S.SLEEVE_D} +{S.ENC_TOL['lt10']}) in its {S.SHAFT_HOLE} plate hole (-{gen}, anodised "
         f"-{an}), radial: board {board:.2f} off, plate, PCB, pins, seat tilt {face_hi * tilt_e:.2f} at the face",
         (S.SHAFT_HOLE - gen - an - S.SLEEVE_D - S.ENC_TOL["lt10"]) / 2 - on_board - face_hi * tilt_e),
        (f"outer knob (flute bottoms at its tapered top, OD -{part_tol}) covers its {S.SHAFT_HOLE} plate hole "
         f"(+{gen}) seen from above: knob on the bushing {on_board:.2f} off, loose knob {bore_play:.2f} off, seat "
         "tilt", min(flute_bottom(S.FLUTES[n], ring_r, ok["z1"] - ok["z0"], ok["z1"] - ok["z0"]) for n in rings)
         - part_tol / 2 - (S.SHAFT_HOLE + gen) / 2 - on_board - bore_play - (S.PLATE_Z1 + ok["z0"]) * tilt_e),
        (f"encoder side lugs ({S.EC11_LUGS} +{S.ENC_TOL['ge10']}) in the {ec_w:.1f} wide pocket (measured, -{gen}, "
         f"anodised -{an}), per side: board {board:.2f} off, plate, PCB, pins, seat tilt", ec_side),
        (f"encoder lug corner clear of the pocket's floor corner (R{fr} max on the drawing), lifted ({ec_side0:.2f} "
         f"off the wall, {ec_top:.2f} off the floor) or tilted ({ec_side:.2f}, {ec_top0:.2f})", ec_corner),
        (f"RKJXT body ({S.RKJXT_ACROSS} across corners +{S.RKJXT_TOL}) in its {S.RANGE_POCKET[0]} pocket (-{gen}, "
         f"anodised -{an}), radial: board, plate, PCB, part on its pins ({S.RKJXT_ON_PINS}), seat tilt",
         rk_side),
        (f"RKJXT hub (Ø{S.RKJXT_HUB[0]}) at full tilt (fulcrum {S.RKJXT_FULCRUM_OFF} off the axis) in its "
         f"{S.RANGE_HOLE} plate hole (-{gen}, anodised -{an}), radial, same offsets and seat tilt",
         (S.RANGE_HOLE - gen - an) / 2 - hub_out - on_board_r),
        (f"RANGE knob over hub, pushed {push_hi:.1f} (lever -{S.LEVER_TOL}, bore +{resin})",
         rk_lo - push_hi - S.RKJXT_HUB_TOP),
        (f"RANGE skirt over plate at {S.RKJXT_TILT:.0f} deg, fulcrum {pz}, low knob, high plate (face +{face_up:.2f}, "
         f"bowed {S.PLATE_FLAT * bow_rng:.3f} up), rim {dip_r:.3f} down on a tilted RKJXT",
         skirt_low - S.PLATE_Z1 - face_up - S.PLATE_FLAT * bow_rng - dip_r),
        (f"RANGE skirt (Ø{rk['skirt_d']} -{part_tol}, high knob on a lifted and tilted RKJXT, rim at cos "
         f"{S.RKJXT_TILT:.0f} deg, fulcrum {S.RKJXT_FULCRUM_OFF} off the axis) still covers its {S.RANGE_HOLE} mm "
         f"plate hole (+{gen}) at full tilt, lever {on_board_r:.2f} off (board, plate, PCB, pins), loose knob "
         f"{bore_play:.2f} off it",
         (rk["skirt_d"] - part_tol) / 2 * math.cos(a) - (S.RANGE_HOLE + gen) / 2 - skirt_shift - on_board_r
         - bore_play),
        (f"RANGE pan arrows (from r {arrow_in:.2f}) outside the skirt seen square on (Ø{rk['skirt_d']} +{part_tol}), "
         f"lever {on_board_r:.2f} off, loose knob {bore_play:.2f} off it, seat tilt",
         arrow_in - (rk["skirt_d"] + part_tol) / 2 - on_board_r - bore_play - (rk_hi + lift_r) * tilt_r),
        (f"RANGE skirt rim ({rim:.2f} on the knob solid, resin -{resin}), beyond 1.0", rim - resin - 1.0),
        (f"encoder pocket (-{pd}) over encoder body (8.0 +0.3), low plate, bowed {S.PLATE_FLAT * bow_enc:.3f} down, "
         f"lugs {lift_e:.2f} up (seated within {sg})", ec_top),
        ("plate left over the encoder pockets, thin plate, beyond 1.0", t_min - S.EC11_POCKET[3] - 1.0),
        (f"RANGE pocket (-{pd}) over RKJXT body (8.6 +0.3), low plate, bowed {S.PLATE_FLAT * bow_rng:.3f} down, "
         f"corners {lift_r:.3f} up (gauge spots within {S.RKJXT_SEAT} of the reference)", rk_top),
        (f"RKJXT body corner clear of the RANGE pocket's floor corner (R{fr} max on the drawing), lifted "
         f"({rk_side0:.2f} off the wall, {rk_top:.2f} off the floor) or tilted ({rk_side:.2f}, {rk_top0:.2f})",
         rk_corner),
        ("plate left over the RANGE pocket, thin plate, beyond 0.6", t_min - S.RANGE_POCKET[1] - 0.6),
        *cap_rows(face_lo, S.PLATE_FLAT * bow_key),
        (f"cap pressed firmly ({S.PRESS_FIRM:.0f} N) comes back into its key hole: {cap_dip:.2f} under the plate back "
         f"(travel {S.KEY_TRAVEL}, plunger -{S.PLUNGER_TOP_TOL}, high plate bowed up, board {flex:.2f} down), tilted "
         f"{math.degrees(slope):.2f} deg with the bent board, lands on the {S.KEY_BACK_BREAK} edge break",
         S.KEY_BACK_BREAK - cap_dip * slope),
        (f"cap pressed firmly, tilted {math.degrees(slope):.2f} deg (up to {face_shift:.2f} sideways at the face, so "
         f"it may rub one side): it cannot wedge across its hole, turned {S.CAP_TURN:.0f} deg and printed "
         f"+{cap_print}, its shadow over the {wall_h:.2f} wall ({shadow:.3f}) within twice its shift room "
         f"({cap_room_wedge:.2f})", 2 * cap_room_wedge - shadow),
        (f"cap shift room in its key hole ({cap_room:.2f}) over per-key RSS {cap_err:.2f}", cap_room - cap_err),
        (f"cap turned {S.CAP_TURN:.0f} deg on its plunger (squared on a rule): shift room ({cap_room_turn:.2f}) over "
         f"per-key RSS {cap_err:.2f}", cap_room_turn - cap_err),
        (f"screw passes the narrowest PCB hole ({hole} -{pt['npth_d']})", hole_lo - S.SCREW_D / 2),
        (f"standoff on the board enters its pocket (pocket {sp['d']}, board {board:.2f} off, screw play)",
         float_min - (pt["plate"] + pt["pcb"] + board - (hole_lo - S.SCREW_D / 2))),
        (f"standoff end (AF {so['af_min']} min, {off:.2f} off) covers the widest PCB hole all round",
         so["af_min"] / 2 - off - hole_hi),
        (f"standoff corners (AC {so['ac']}) inside the {keepout} mm copper keep-out", keepout - so["ac"] / 2 - off),
        ("plate left in front of the standoff pockets, thin plate, beyond 1.0", t_min - sp["depth"] - 1.0),
        ("standoff pocket to the nearest plate feature or edge, beyond 1.0", pocket_web() - 1.0),
        ("boss top bears on the PCB all round its hole (MJF -0.15)",
         MM.BOSS_R - pt["body_hole"] - offset - off - hole_hi),
        (f"PCB width in the cavity (MJF -{cav_w_tol:.1f}; routed long edges +{MM.PCB_OUTLINE_TOL}, or the full "
         f"variant's V-cut rail edge +{MM.PCB_VCUT_TOL}), per side", cav),
        (f"PCB length in the cavity ({cav_len:.2f} at MJF -0.4 %): routed short edges (+{MM.PCB_OUTLINE_TOL}), or "
         f"V-cut ones sanded to {MM.PCB_SANDED_LEN} max, per side", (cav_len - pcb_len) / 2),
        (f"through-hole leads (trimmed to {S.LEAD_MAX} under the PCB) over the body floor ({MM.UNDER} room, MJF "
         f"-{mjf(MM.UNDER)})", MM.UNDER - mjf(MM.UNDER) - S.LEAD_MAX),
        *usb_rows(),
        ("body screw hole round the screw, body and PCB tolerance",
         MM.SCREW_CLEAR - pt["body_hole"] - S.SCREW_D / 2 - pt["body"] - pt["pcb"]),
        (f"washer (OD {2 * r_w_min:.2f} min) bears all round the widest body hole", r_w_min - w_off - r_hole_max),
        ("washer lies flat in the counterbore wherever the screw sits",
         MM.HEAD_R - pt["body_hole"] - r_w_max - max(0.0, offset - MM.WASHER_PLAY)),
        ("pan head (dk 4.7 min) covers the washer bore",
         sc["head_d_min"] / 2 - w["bore_max"] / 2 - MM.WASHER_PLAY),
        ("counterbore to the outer body wall (MJF), beyond 1.5 (JLC3DP fastener features)", corner - 1.5),
        (f"counterbore (R{cb_r:.2f} measured on the body) is the one the washer rows take (R{MM.HEAD_R})",
         0.05 - abs(cb_r - MM.HEAD_R)),
        (f"body boss wall round the counterbore ({boss_wall:.2f} measured on the body; counterbore and boss MJF "
         f"+-{seat_tol} on the diameter), beyond 1.5 (JLC3DP fastener features)", boss_wall - seat_tol - 1.5),
        (f"PA12 between counterbore seat and PCB ({seat_t:.2f} measured on the body), beyond 1.5 (JLC3DP fastener "
         "features)", seat_t - 1.5),
        # at MJF -0.3 the seat is 1.3: it lies flat on the PCB and only takes the screw's compression between
        # washer and board, so 1.2 is the floor there; 1.5 holds for the walls that stand free (the boss above)
        (f"PA12 between counterbore seat and PCB ({seat_t:.2f}, MJF -{seat_tol}; in compression on the PCB), "
         "beyond 1.2", seat_t - seat_tol - 1.2),
        (f"body walls under the plate, worst (MJF, PCB, standoff gap, back face over bare pocket floors, bowed "
         f"{S.PLATE_FLAT * bow_wall:.3f} down), beyond 0.2", wall_gap - 0.2),
        (f"M2.5 x {sc['L']:.0f} thread engaged in the standoff, shortest stack, beyond {S.ENGAGE_MIN}",
         engaged - S.ENGAGE_MIN),
        (f"screw tip short of the wax plug ({S.PLUG_DEPTH:.0f} deep) in the standoff's plate end, longest stack",
         plug - tip_hi),
        (f"epoxy band on the standoff sides (pocket {so_depth:.2f} deep measured on the plate, -{sp['depth_tol']}, "
         f"{sp['bare']} bare at the end), beyond 1.0", so_depth - sp["depth_tol"] - sp["bare"] - 1.0),
        ("washer and pan head recessed, front mounts, deep seat", head_lo - boss_floor),
        ("steel plate recess stays under the 2 mm floor (the floor is not thinned)",
         MM.Z_FLOOR_BOT - MM.z_bottom(stl["y0"] + MM.STEEL_RECESS[1]) - stl["depth"] / math.cos(math.atan(MM.SLOPE))),
        steel_row(),
        ("steel plate recess rim at the back wall, beyond 2.0 (JLC3DP MJF over 100 mm)", stl["y0"] + MM.o - 2.0),
        ("foot pad inside the steel plate notch, beyond 0.5", notch - 0.5),
        (f"foot pad round a {MM.FOOT_D:.0f} mm foot (flat over r {pad_r:.2f}, measured on the body), per side, "
         "beyond 0.5", pad_r - MM.FOOT_D / 2 - 0.5),
        (f"body: no void under 0.8 mm deeper than 0.4 (worst at {void_at})", 0.4 - void),
        (f"body: no wall under 0.8 mm deeper than 0.4 (worst at {wall_at})", 0.4 - wall),
        (f"body: no wall under 1.9 mm (JLC3DP MJF 2.0 over 100 mm, less the raster) deeper than 0.6 (square corners "
         f"0.4) bar the screw bosses (worst at {wall2_at})", 0.6 - wall2),
        (f"assembly blocks ({S.ASSEMBLY_BLOCK:.0f}) over the shaft tips, beyond 3", S.ASSEMBLY_BLOCK - protrude - 3),
        ("plate edge strip free for the blocks, beyond 8", edge - 8),
        (f"highest LED ({S.LED_TOP} +{S.LED_TOL[0]}) under the lowest plate back (bare pocket floors), PCB "
         f"{S.SUPPORT_LIFT:.2f} up on a post, bowed up {S.PCB_BOW}, plate bowed down {S.PLATE_FLAT}",
         back_lo - S.PLATE_FLAT - led_hi),
        (f"glued light pipe ({pp['len']} +{pp['len_tol']}) over the highest LED, thin plate, PCB and plate bowed as "
         f"above (posts {S.SUPPORT_SHORT} short, MJF 0.3)",
         face_lo - S.PLATE_FLAT - (pp["len"] + pp["len_tol"]) - led_hi),
        (f"light pipe fits its hole ({pp['clear']} under, hole +{lt_up}/-{lt_dn:g}), beyond anodising "
         f"({pp['anodise']}) and resin (+{pp['resin']})", pp["clear"] - lt_dn - pp["anodise"] - pp["resin"]),
    ]
    for name, d in S.LIGHT_HOLES.items():
        (lx, ly), _, _ = B.LEDS[name]
        rows.append((f"{name} snap-off neck ({pp['neck_d']}) inside the pipe",
                     (d - pp["clear"]) / 2 - pp["neck_d"] / 2))
        web = min(rrect_sd(lx - x, ly - y, *S.KEY_HOLE) for x, y in caps) - d / 2
        web_lo = min(rrect_sd(lx - x, ly - y, *key_hole_max()) for x, y in caps) - (d + lt_up) / 2
        rows.append((f"{name} light hole web to the next key hole ({web:.2f}), beyond 0.8 (JLCCNC recommended)",
                     web - 0.8))
        rows.append((f"{name} light hole web with both holes at +{lt_up} ({web_lo:.2f}), beyond 0.5 (JLCCNC "
                     "minimum)", web_lo - 0.5))
    for name, v in rows:
        print(f"  {name:106s} {v:5.2f} mm {'OK' if v > 0 else 'FAIL'}")
    if any(v <= 0 for _, v in rows):                 # a plain raise: asserts vanish under -O
        raise SystemExit(f"fit check failed: {[n for n, v in rows if v <= 0]}")


if __name__ == "__main__":
    clearances()
