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
part(ax, -S.SLEEVE_D / 2, S.EC11_BODY, S.SLEEVE_D, S.SLEEVE_TOP - S.EC11_BODY)
part(ax, -S.OUTER_D / 2, S.SLEEVE_TOP, S.OUTER_D, S.OUTER_TOP - S.SLEEVE_TOP)
part(ax, -S.SLOT_W / 2, S.OUTER_TOP - S.SLOT_LEN, S.SLOT_W, S.SLOT_LEN, fc="white")
part(ax, -S.INNER_D / 2, S.OUTER_TOP, S.INNER_D, S.INNER_TOP - S.OUTER_TOP)
part(ax, S.INNER_FLAT - S.INNER_D / 2, S.INNER_TOP - S.FLAT_LEN, S.INNER_D - S.INNER_FLAT, S.FLAT_LEN, fc="white")
draw(ax, K.outer_knob(), 0, "k", dz=S.PLATE_Z1 + S.OUTER_KNOB["z0"])
draw(ax, K.inner_knob(), 0, "k", dz=S.PLATE_Z1 + S.INNER_KNOB["z0"])
ax.set_title("ALT/HDG dual knob on PEC11D-4120F-S0015")

# ---- RANGE ----
ax = axes[1]
cx, cy = PS.P(*B.RANGE)
draw(ax, plate, cy, "#1f5fa0", dx=-cx, dz=S.PLATE_Z0)
part(ax, -12, -S.PCB_T, 24, S.PCB_T, fc="#c8d8c0")
flats = S.RKJXT_ACROSS * math.cos(math.pi / 8)               # octagon: 17 across corners, 15.7 across flats
part(ax, -flats / 2, 0, flats, S.RKJXT_BODY)
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


def cap_shift_room(grow=0.0):
    """how far a key cap can shift in its key hole (grown by grow on width and height) before it touches:
    (least, most) over all directions."""
    c, (hw, hh, hr) = S.CAP, S.KEY_HOLE
    hole = (hw + grow, hh + grow, hr + grow / 2)
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    ox = (c["w"] / 2 - c["r"]) * np.sign(np.cos(t)) + c["r"] * np.cos(t)     # cap outline, corners dense
    oy = (c["h"] / 2 - c["r"]) * np.sign(np.sin(t)) + c["r"] * np.sin(t)
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


def body_thin(res=0.1):
    """deepest thin void, deepest thin wall (0.8) and deepest wall under JLC3DP's 2.0 mm for large MJF parts
    (1.9: a 2.0 wall is 20 pixels, which a 21 pixel disk does not fit) over sections through the body (board
    frame), with where."""
    tri = body_triangles()
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


def solid_height(shape, x):
    """how much of the vertical line at (x, 0) lies inside the solid: its XZ section crossed at x."""
    zs = []
    for px, pz in section(shape, 0.0):
        for (x0, z0), (x1, z1) in zip(zip(px, pz, strict=True), zip(px[1:], pz[1:], strict=True), strict=False):
            if (x0 - x) * (x1 - x) < 0:
                zs.append(z0 + (z1 - z0) * (x - x0) / (x1 - x0))
    zs.sort()
    assert zs and len(zs) % 2 == 0, f"no clean section at x {x}"
    return sum(b - a for a, b in zip(zs[0::2], zs[1::2], strict=True))


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


def cap_rows(face_lo, back_hi):
    """key cap rows: rigid ribs on the plunger cone measured on the generated caps, four fit sets against the
    print tolerance, set marks, tactile bars and legends against JLC3DP's minimums."""
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
    rows = [
        (f"cap socket ribs {sk['rib_w']} wide, on the socket wall over their length, beyond 1.0 (WJP)",
         sk["rib_w"] - 1.0),
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
        # These two rows take board and plate flat: a cap is coaxial with its plunger and smaller than its key
        # hole, so the PCB bow and plate flatness budgets (PCB_BOW, PLATE_FLAT, SUPPORT_LIFT) only move it a
        # little up or down in the hole; they matter for the LED rows below, where the pipe sits over the LED.
        (f"cap socket ceiling (on the plunger top, +{S.PLUNGER_TOP_TOL}) under the lowest plate face",
         face_lo - (S.PLUNGER_TOP + S.PLUNGER_TOP_TOL)),
        (f"pressed cap still inside its key hole (travel {S.KEY_TRAVEL}, plunger -{S.PLUNGER_TOP_TOL}, high plate)",
         c["base"] - S.KEY_TRAVEL - S.PLUNGER_TOP_TOL - back_hi),
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


def mjf(length):
    """JLC3DP MJF tolerance on a length (+-): 0.3 up to 100 mm, 0.4 % above."""
    return max(0.3, 0.004 * length)


def usb_rows():
    """USB-C socket and plug in the back wall opening (make_mech.USB_OPEN, carried up as a notch)."""
    u, place, hole = MM.USB_OPEN, 0.1, S.POS_TOL["body_hole"]    # J1 placement (JLCPCB), MJF on the opening
    # the board lies anywhere in the cavity (CLEAR). Its sideways play is set by its short edges against the
    # side walls, and those are V-cut and sanded (+-PCB_VCUT_TOL): at worst one of them is that much short.
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
    # ---- plate: back on the standoffs (6.0 +0.2/-0.1 over the PCB top), thickness +-0.1; depths from the back
    gap_up, gap_dn = S.GAP_TOL
    t_min = S.PLATE_T - S.PLATE_T_TOL
    back_lo, back_hi = S.PLATE_Z0 - gap_dn, S.PLATE_Z0 + gap_up
    face_lo = back_lo + t_min
    face_up = gap_up + S.PLATE_T_TOL                    # plate face over its nominal height, worst
    # ---- positions: board offset from the caps, standoffs lined up with the PCB holes ----
    pt, sc, so, sp = S.POS_TOL, S.SCREW, S.STANDOFF, S.STANDOFF_POCKET
    cap_err = math.sqrt(sum(v * v for v in S.CAP_TOL.values()))
    cap_room = cap_shift_room()[0]                      # key hole +0.1/-0 after anodising: least at nominal
    cap_room_max = cap_shift_room(S.KEY_HOLE_TOL[0])[1]   # most in the largest hole
    board = cap_room_max + pt["centring"]              # board offset the caps allow (the most, diagonally)
    hole = B.MOUNT_HOLE
    hole_lo, hole_hi = (hole - pt["npth_d"]) / 2, (hole + pt["npth_d"]) / 2
    off = hole_hi - sc["d_min"] / 2 + pt["thread"]     # standoff axis off the PCB hole axis: the screw's play
    float_min = (sp["d"] - 0.05) / 2 - so["ac"] / 2    # standoff float in its pocket (anodising -0.05)
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
    cav = MM.CLEAR - MM.PCB_OUTLINE_TOL / 2 - cav_w_tol / 2           # the routed long edges, per side
    cav_len = (B.W + 2 * MM.CLEAR) * (1 - MM.BODY_SCALE_TOL)        # the cavity length, printed small
    vcut = (cav_len - (B.W + MM.PCB_VCUT_TOL)) / 2                   # V-cut short edges as they come, per side
    # ---- assembly, body ----
    caps = [(x, y) for y in B.ROWS for x in B.COLS]
    protrude = max(S.INNER_TOP + S.ENC_TOL["ge10"], S.LEVER_Z1 + S.LEVER_TOL) - face_lo   # face down
    edge = min([min(y - S.CAP["h"] / 2, B.H - y - S.CAP["h"] / 2) for _, y in caps] +
               [min(y - S.SLEEVE_D / 2, B.H - y - S.SLEEVE_D / 2) for y in (B.ALTHDG[1], B.RANGE[1])]) + S.OVH
    stl, x0 = MM.STEEL, MM.steel_x0()
    fx, fy = MM.FEET[0]
    notch = min(x0 + stl["notch"] - (fx + MM.FOOT_PAD / 2), stl["y0"] + stl["notch"] - (fy + MM.FOOT_PAD / 2))
    (void, void_at), (wall, wall_at), (wall2, wall2_at) = body_thin()
    # ---- light pipes glued flush, LEDs under them: the only rows that take the bow and flatness budgets (the
    # cap rows are for a flat board and plate, see cap_rows) ----
    pp = S.PIPE
    led_hi = S.LED_TOP + S.LED_TOL[0] + S.SUPPORT_LIFT + S.PCB_BOW   # lifted by a post, bowed up
    lt_up, lt_dn = S.LIGHT_HOLE_TOL
    pd = S.POCKET_TOL
    wall_gap = S.WALL_GAP - (seat_tol + pcb_tol + gap_dn)   # MJF wall height, PCB, standoff gap
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
    skirt_shift = (rk_hi - pz) * math.sin(a)
    on_board = board + pt["plate"] + pt["pcb"] + S.ENC_ON_PINS   # an encoder's axis off its plate hole
    on_board_r = board + pt["plate"] + pt["pcb"] + S.RKJXT_ON_PINS   # the RKJXT's: it floats more on its pins
    # RKJXT hub (Alps' STEP) tilted 9 deg about the fulcrum: its full-width top edge sideways at the plate
    hub_r, hub_z = S.RKJXT_HUB[0] / 2, S.RKJXT_HUB[1]
    hub_out = hub_r * math.cos(a) + (hub_z - pz) * math.sin(a)
    arrow_in = S.RANGE_ART["arrow_r"] + min(u for u, _v in S.RANGE_ART["arrow"])   # pan arrows' inner ends
    gen = S.PLATE_GEN_TOL                               # ISO 2768-m on untoleranced plate sizes
    # RKJXT body corner (top edge at its widest) off the RANGE pocket's wall and floor, worst of each, and off
    # the floor corner radius the drawing allows (S.RANGE_POCKET_R)
    rk_side = (S.RANGE_POCKET[0] - gen - S.RKJXT_ACROSS - S.RKJXT_TOL) / 2 - on_board_r
    rk_top = back_lo + S.RANGE_POCKET[1] - S.POCKET_TOL - (S.RKJXT_BODY + 0.3)
    fr = S.RANGE_POCKET_R
    rk_corner = fr - math.hypot(fr - rk_side, fr - rk_top) if max(rk_side, rk_top) < fr else min(rk_side, rk_top)
    # ---- outer knob, in its own frame from the slot floor its key rests on ----
    slot_tol = S.ENC_TOL["lt10"]                        # slot width and depth, +-
    key_rss = math.hypot(es["slot"], resin)            # slot floor over the PCB and the key's height in the knob
    cb_top = K.outer_counterbore_top() - K.outer_key_z0() + resin   # counterbore top, highest
    shaft_top = S.SLOT_LEN - slot_tol                   # 6 mm shaft top over the slot floor, shallow slot
    knob_top = ok["z1"] - ok["z0"] - K.outer_key_z0()                # top of the knob's bore
    key_resin = 0.2                                     # key printed up to 0.2 wide
    # ---- RANGE skirt rim measured on the knob solid, just inside its edge ----
    rim = solid_height(RANGE_SOLID, rk["skirt_d"] / 2 - 0.05)
    rows = [
        (f"outer knob over plate (face +{face_up:.1f}, slot floor +-{es['slot']:.2f} and key resin, RSS)",
         ok["z0"] - face_up - key_rss),
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
        ("outer ring beyond the inner knob, per side, beyond 2.0 (Garmin 2.5)", ring_r - ik["d"] / 2 - 2.0),
        (f"encoder bushing ({S.SLEEVE_D} +{S.ENC_TOL['lt10']}) in its {S.SHAFT_HOLE} plate hole (-{gen}), radial: "
         f"board {board:.2f} off, plate, PCB, pins",
         (S.SHAFT_HOLE - gen - S.SLEEVE_D - S.ENC_TOL["lt10"]) / 2 - on_board),
        (f"RKJXT body ({S.RKJXT_ACROSS} across corners +{S.RKJXT_TOL}) in its {S.RANGE_POCKET[0]} pocket (-{gen}), "
         f"radial: board, plate, PCB, part on its pins ({S.RKJXT_ON_PINS})",
         rk_side),
        (f"RKJXT hub (Ø{S.RKJXT_HUB[0]}) at full tilt in its {S.RANGE_HOLE} plate hole (-{gen}), radial, same offsets",
         (S.RANGE_HOLE - gen) / 2 - hub_out - on_board_r),
        (f"RANGE knob over hub, pushed {push_hi:.1f} (lever -{S.LEVER_TOL}, bore +{resin})",
         rk_lo - push_hi - S.RKJXT_HUB_TOP),
        (f"RANGE skirt over plate at {S.RKJXT_TILT:.0f} deg, fulcrum {pz}, low knob, high plate",
         skirt_low - S.PLATE_Z1 - face_up),
        (f"RANGE skirt (Ø{rk['skirt_d']} -{part_tol}, high knob, rim at cos {S.RKJXT_TILT:.0f} deg) still covers its "
         f"{S.RANGE_HOLE} mm plate hole (+{gen}) at full tilt, lever {on_board_r:.2f} off (board, plate, PCB, "
         f"pins), loose knob {bore_play:.2f} off it",
         (rk["skirt_d"] - part_tol) / 2 * math.cos(a) - (S.RANGE_HOLE + gen) / 2 - skirt_shift - on_board_r
         - bore_play),
        (f"RANGE pan arrows (from r {arrow_in:.2f}) outside the skirt seen square on (Ø{rk['skirt_d']} +{part_tol}), "
         f"lever {on_board_r:.2f} off, loose knob {bore_play:.2f} off it",
         arrow_in - (rk["skirt_d"] + part_tol) / 2 - on_board_r - bore_play),
        (f"RANGE skirt rim ({rim:.2f} on the knob solid, resin -{resin}), beyond 1.0", rim - resin - 1.0),
        (f"encoder pocket (-{pd}) over encoder body (8.0 +0.3), low plate",
         back_lo + S.EC11_POCKET[3] - pd - (S.EC11_BODY + 0.3)),
        ("plate left over the encoder pockets, thin plate, beyond 1.0", t_min - S.EC11_POCKET[3] - 1.0),
        (f"RANGE pocket (-{pd}) over RKJXT body (8.6 +0.3), low plate",
         rk_top),
        (f"RKJXT body corner clear of the RANGE pocket's floor corner (R{S.RANGE_POCKET_R} max on the drawing), "
         f"{rk_side:.2f} off the wall and {rk_top:.2f} off the floor", rk_corner),
        ("plate left over the RANGE pocket, thin plate, beyond 0.6", t_min - S.RANGE_POCKET[1] - 0.6),
        *cap_rows(face_lo, back_hi),
        (f"cap shift room in its key hole ({cap_room:.2f}) over per-key RSS {cap_err:.2f}", cap_room - cap_err),
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
        (f"PCB width in the cavity (MJF -{cav_w_tol:.1f}, routed long edges +{MM.PCB_OUTLINE_TOL}), per side", cav),
        (f"PCB length in the cavity ({cav_len:.2f} at MJF -0.4 %), V-cut short edges (+-{MM.PCB_VCUT_TOL}: "
         f"{vcut:+.2f} as they come) sanded to {MM.PCB_SANDED_LEN} max, per side", (cav_len - MM.PCB_SANDED_LEN) / 2),
        *usb_rows(),
        ("body screw hole round the screw, body and PCB tolerance",
         MM.SCREW_CLEAR - pt["body_hole"] - S.SCREW_D / 2 - pt["body"] - pt["pcb"]),
        (f"washer (OD {2 * r_w_min:.2f} min) bears all round the widest body hole", r_w_min - w_off - r_hole_max),
        ("washer lies flat in the counterbore wherever the screw sits",
         MM.HEAD_R - pt["body_hole"] - r_w_max - max(0.0, offset - MM.WASHER_PLAY)),
        ("pan head (dk 4.7 min) covers the washer bore",
         sc["head_d_min"] / 2 - w["bore_max"] / 2 - MM.WASHER_PLAY),
        ("counterbore to the outer body wall (MJF), beyond 1.5 (JLC3DP fastener features)", corner - 1.5),
        ("body boss wall around the counterbore, beyond 1.5 (JLC3DP fastener features)",
         MM.BOSS_R_LOW - MM.HEAD_R - 1.5),
        (f"PA12 between counterbore seat and PCB ({seat_pcb - S.PCB_T:.1f}), beyond 1.5 (JLC3DP fastener features)",
         seat_pcb - S.PCB_T - 1.5),
        (f"PA12 between counterbore seat and PCB ({seat_pcb - S.PCB_T:.1f}, MJF -{seat_tol}), beyond 1.2",
         seat_pcb - S.PCB_T - seat_tol - 1.2),
        ("body walls under the plate, worst (MJF, PCB, standoff gap), beyond 0.2", wall_gap - 0.2),
        (f"M2.5 x {sc['L']:.0f} thread engaged in the standoff, shortest stack, beyond {S.ENGAGE_MIN}",
         engaged - S.ENGAGE_MIN),
        (f"screw tip short of the wax plug ({S.PLUG_DEPTH:.0f} deep) in the standoff's plate end, longest stack",
         plug - tip_hi),
        (f"epoxy band on the standoff sides (pocket -{sp['depth_tol']}, {sp['bare']} bare at the end), beyond 1.0",
         sp["depth"] - sp["depth_tol"] - sp["bare"] - 1.0),
        ("washer and pan head recessed, front mounts, deep seat", head_lo - boss_floor),
        ("steel plate recess stays under the 2 mm floor (the floor is not thinned)",
         MM.Z_FLOOR_BOT - MM.z_bottom(stl["y0"] + MM.STEEL_RECESS[1]) - stl["depth"] / math.cos(math.atan(MM.SLOPE))),
        steel_row(),
        ("steel plate recess rim at the back wall, beyond 2.0 (JLC3DP MJF over 100 mm)", stl["y0"] + MM.o - 2.0),
        ("foot pad inside the steel plate notch, beyond 0.5", notch - 0.5),
        (f"foot pad round a {MM.FOOT_D:.0f} mm foot, per side, beyond 0.5", (MM.FOOT_PAD - MM.FOOT_D) / 2 - 0.5),
        (f"body: no void under 0.8 mm deeper than 0.4 (worst at {void_at})", 0.4 - void),
        (f"body: no wall under 0.8 mm deeper than 0.4 (worst at {wall_at})", 0.4 - wall),
        (f"body: no wall under 1.9 mm (JLC3DP MJF 2.0 over 100 mm, less the raster) deeper than 0.6 (square corners "
         f"0.4) bar the screw bosses (worst at {wall2_at})", 0.6 - wall2),
        (f"assembly blocks ({S.ASSEMBLY_BLOCK:.0f}) over the shaft tips, beyond 3", S.ASSEMBLY_BLOCK - protrude - 3),
        ("plate edge strip free for the blocks, beyond 8", edge - 8),
        (f"highest LED ({S.LED_TOP} +{S.LED_TOL[0]}) under the lowest plate back, PCB {S.SUPPORT_LIFT:.2f} up on a "
         f"post, bowed up {S.PCB_BOW}, plate bowed down {S.PLATE_FLAT}", back_lo - S.PLATE_FLAT - led_hi),
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
    assert all(v > 0 for _, v in rows), [n for n, v in rows if v <= 0]


if __name__ == "__main__":
    clearances()
