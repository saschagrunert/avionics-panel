"""Cross-sections through the assembled stack (plate, knobs, datasheet part outlines) -> fit-check.png.

Sections run through the ALT/HDG knob, the RANGE knob and the SHIFT light pipe (XZ plane, z = 0 is the
PCB top). Grey: PCB and part outlines from the datasheets. Blue: plate. Black: printed parts.
"""
import functools
import io
import math
import sys
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.GCPnts import GCPnts_QuasiUniformDeflection
from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pln, gp_Pnt, gp_Trsf
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods
from PIL import Image

HERE = Path(__file__).resolve().parent              # works from any directory
sys.path[:0] = [str(HERE), str(HERE.parent / "pcb")]
import board as B  # noqa: E402
import make_knobs as K  # noqa: E402
import make_mech as MM  # noqa: E402
import make_plate_art as PA  # noqa: E402
import make_plate_step as PS  # noqa: E402
import stack as S  # noqa: E402
from geom import item_dist, pad_geom  # noqa: E402
from occ_util import face_meshes  # noqa: E402


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


def draw_sections(plate, outer, inner, range_knob):
    """fit-check.png: the sections through the ALT/HDG knob, the RANGE knob and the SHIFT light pipe."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 8), gridspec_kw={"width_ratios": [28, 22, 15]})

    # ---- ALT/HDG dual knob ----
    ax = axes[0]
    cx, cy = PS.P(*B.ALTHDG)
    draw(ax, plate, cy, "#1f5fa0", dx=-cx, dz=S.PLATE_Z0)
    part(ax, -12, -S.PCB_T, 24, S.PCB_T, fc="#c8d8c0")
    part(ax, -S.EC11_SIZE[0] / 2, 0, S.EC11_SIZE[0], S.EC11_BODY)
    for sx in (-1, 1):                                          # side lugs: 13.1 across (PEC11D drawing)
        part(ax, sx * S.EC11_LUGS / 2 - (sx > 0) * 0.7, 0, 0.7, S.EC11_BODY, fc="#cfcfcf")
    part(ax, -S.SLEEVE_D / 2, S.EC11_BODY, S.SLEEVE_D, S.SLEEVE_TOP - S.EC11_BODY)
    part(ax, -S.OUTER_D / 2, S.SLEEVE_TOP, S.OUTER_D, S.OUTER_TOP - S.SLEEVE_TOP)
    part(ax, -S.SLOT_W / 2, S.OUTER_TOP - S.SLOT_LEN, S.SLOT_W, S.SLOT_LEN, fc="white")
    part(ax, -S.INNER_D / 2, S.OUTER_TOP, S.INNER_D, S.INNER_TOP - S.OUTER_TOP)
    part(ax, S.INNER_FLAT - S.INNER_D / 2, S.INNER_TOP - S.FLAT_LEN, S.INNER_D - S.INNER_FLAT, S.FLAT_LEN, fc="white")
    draw(ax, outer, 0, "k", dz=S.PLATE_Z1 + S.OUTER_KNOB["z0"])
    draw(ax, inner, 0, "k", dz=S.PLATE_Z1 + S.INNER_KNOB["z0"])
    ax.set_title("ALT/HDG dual knob on PEC11D-4120F-S0015")

    # ---- RANGE ----
    ax = axes[1]
    cx, cy = PS.P(*B.RANGE)
    draw(ax, plate, cy, "#1f5fa0", dx=-cx, dz=S.PLATE_Z0)
    part(ax, -12, -S.PCB_T, 24, S.PCB_T, fc="#c8d8c0")
    part(ax, -S.RKJXT_FOOT / 2, 0, S.RKJXT_FOOT, S.RKJXT_FRAME_GAP)   # foot and base frame (Alps' STEP)
    part(ax, -S.RKJXT_FRAME / 2, S.RKJXT_FRAME_GAP, S.RKJXT_FRAME, 2.55 - S.RKJXT_FRAME_GAP)
    part(ax, -S.RKJXT_FLATS / 2, 0, S.RKJXT_FLATS, S.RKJXT_BODY)  # octagon above z 4: 15.73 across flats
    part(ax, -S.RKJXT_HUB[0] / 2, S.RKJXT_BODY, S.RKJXT_HUB[0], S.RKJXT_HUB_TOP - S.RKJXT_BODY)   # hub, no chamfer
    part(ax, -S.LEVER_D / 2, S.LEVER_Z0, S.LEVER_D, S.LEVER_Z1 - S.LEVER_Z0)
    draw(ax, range_knob, 0, "k", dz=S.PLATE_Z1 + S.RANGE_KNOB["z0"])
    ax.set_title(f"RANGE knob on RKJXT1F42001 (tilt {S.RKJXT_TILT:.0f} deg not drawn)")

    # ---- SHIFT light pipe (section along board y, through the key above it) ----
    ax = axes[2]
    (lx, ly), _, _ = B.LEDS["SHIFT"]
    px, py = PS.P(lx, ly)
    # plate section in the YZ plane: rotate the problem by sectioning at x = px with a plane normal to X
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(px, py, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
    rot = BRepBuilderAPI_Transform(plate, t, True).Shape()        # board +y (towards the user) now points to -x
    draw(ax, rot, py, "#1f5fa0", dx=-px, dz=S.PLATE_Z0)
    cw = B.LED_CUTOUT[1]                                        # the cutout across the pads (along board y)
    part(ax, -6, -S.PCB_T, 6 - cw / 2, S.PCB_T, fc="#c8d8c0")
    part(ax, cw / 2, -S.PCB_T, 6 - cw / 2, S.PCB_T, fc="#c8d8c0")
    ll = S.LED_LENS
    part(ax, -0.8, -S.PCB_T - 0.28, 1.6, 0.28)                  # reverse-mount LED: substrate under the board,
    part(ax, -ll["w"] / 2, -S.PCB_T, ll["w"], ll["h"], fc="#f3d58a")   # its lens up in the cutout
    key_dy = ly - B.ROWS[3]                                     # key centre is this far towards the back
    part(ax, key_dy - S.CAP["h"] / 2, S.CAP["base"], S.CAP["h"], S.CAP["height"], fc="#555", ec="#222")   # key cap
    tp = gp_Trsf(); tp.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), -math.pi / 2)
    draw(ax, BRepBuilderAPI_Transform(K.light_pipe(), tp, True).Shape(), 0, "k", dx=0, dz=S.PIPE["z0"])   # on the board
    ax.set_title("SHIFT light pipe\n(front of the panel on the left)")

    for ax, xl in zip(axes, ((-14, 14), (-11, 11), (-6, 9)), strict=True):   # z from under the LED
        ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_xlim(*xl); ax.set_ylim(-3, 31 if ax is axes[0] else 22)
        ax.axhline(S.PLATE_Z1, color="#1f5fa0", lw=0.3, ls=":")
    fig.tight_layout()
    fig.savefig(HERE / "fit-check.png", dpi=110)
    print("fit-check.png written")


def rrect_sd(x, y, w, h, r):
    """signed distance of points to a rounded rectangle centred at 0 (negative inside, positive outside)."""
    qx, qy = np.abs(x) - (w / 2 - r), np.abs(y) - (h / 2 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def cap_shift_room(grow=0.0, turn=0.0, r=None):
    """how far a key cap, turned by turn (deg) on its plunger, can shift in its key hole (grown by grow on width
    and height, its corner radius r if given) before it touches: (least, most) over all directions (0 when it does
    not fit at all)."""
    c, (hw, hh, hr) = S.CAP, S.KEY_HOLE
    hole = (hw + grow, hh + grow, (hr if r is None else r) + grow / 2)
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
    """the body mesh in board frame, from the STL make_mech.py wrote (build.sh runs it first)."""
    tri = stl_triangles(HERE / "avionics-panel-rev1-body.stl")
    tri[:, :, 1] *= -1                                           # output frame (Y = -board y) back to board y
    return tri


def mesh_triangles(shape, deflection=0.02):
    """triangles (n, 3, 3) of an OpenCascade solid, meshed here."""
    return np.concatenate([nodes[idx] for _, nodes, idx in face_meshes(shape, deflection, 0.15)])


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
    uw = (MM.USB_OPEN["w"] + MM.USB_KEEP[0]) / 4        # in the walls beside the USB-C opening and its slot
    planes += [(0, x) for x in (3.5, 9.0, 15.5, 22.5, 54.0, 85.0, 112.0, ux - uw, ux, ux + uw, B.BOOT[0], 150.0,
                                156.5)]
    planes += [(1, y) for y in (-1.5, 0.5, 2.0, 3.5, 6.7, 20.0, 40.0, 47.8, 55.5, 57.0)]
    cx, cy = B.MID_MOUNT                                # through the middle column and beside its axis
    planes += [(0, cx), (0, cx + 1.5), (0, cx + 3.0), (1, cy), (1, cy + 3.0), (1, cy + 5.0)]
    void, wall, wall2 = (0.0, "none"), (0.0, "none"), (0.0, "none")
    keep_r = MM.BOSS_R_LOW + 0.5        # the screw bosses: fastener features, checked against 1.5 by their own rows
    for axis, value in planes:
        solid, (gu, _) = raster_section(tri, axis, value + 1e-3, res, grid=True)
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
    if not zs or len(zs) % 2:
        raise ValueError(f"no clean section at x {x}")
    return zs


def d_bore_len(shape, d, flat):
    """length of the D flat in a knob's D bore (flat towards +x, bore end on the axis), measured on the solid: from
    the bore end on the axis down to where the resin behind the flat ends, on a line halfway between the flat and
    the bore wall."""
    end = crossings(shape, 0.0)[0]                       # the axis enters the resin at the bore end
    x = flat / 2                                         # halfway from the flat (flat - d / 2) to the wall (d / 2)
    starts = [z for z in crossings(shape, x)[0::2] if z < end]
    return end - max(starts)


@functools.cache
def set_caps(name):
    """triangles (n, 3, 3) of each cap in the set's generated OBJ (caps-<set>.zip, as ordered), each moved to the
    origin: the caps sit on the print grid stack.CAP_LAYOUT, in the order of stack.KEY_LEGENDS."""
    base = f"avionics-panel-rev1-caps-{name}"
    with zipfile.ZipFile(HERE / f"{base}.zip") as z:
        lines = z.read(f"{base}.obj").decode().splitlines()
    V = np.array([[float(t) for t in ln.split()[1:4]] for ln in lines if ln.startswith("v ")])
    F = np.array([[int(t.split("/")[0]) - 1 for t in ln.split()[1:4]] for ln in lines if ln.startswith("f ")])
    tri, pitch, n = V[F], S.CAP_LAYOUT["pitch"], S.CAP_LAYOUT["per_row"]
    col, row = np.round(tri.mean(1)[:, :2] / (pitch, -pitch)).astype(int).T
    k = col + n * row
    return [tri[k == i] - (pitch * (i % n), -pitch * (i // n), 0.0) for i in range(k.max() + 1)]


def first_cap(name):
    """triangles (n, 3, 3) of the first cap of set name (set_caps)."""
    return set_caps(name)[0]


def cap_measures(name):
    """measured on the first cap of set name (first_cap): its size over all (w, h, height) and how deep it is at
    each of the CAP_MARK positions (0 where it has no dimple), by rays up from under the cap."""
    tri = first_cap(name)
    v = tri.reshape(-1, 3)
    up = np.array([0.0, 0.0, 1.0])
    return v.max(0) - v.min(0), [ray_hit(tri, np.array([x, y, -1.0]), up) - 1.0 for x, y in S.CAP_MARK["pos"]]


def cap_build_rows():
    """the generated caps (first_cap of each set) against stack.CAP and stack.CAP_MARK: the outline, the height and
    the set's dimples, the first 1 to 4 of CAP_MARK's positions by the set's place in CAP_SETS."""
    c, mk = S.CAP, S.CAP_MARK
    sizes, off = [], 0.0
    for k, n in enumerate(S.CAP_SETS):
        size, depths = cap_measures(n)
        sizes.append(size)
        off = max(off, *np.abs(size - (c["w"], c["h"], c["height"])),
                  *(abs(d - (mk["depth"] if i <= k else 0.0)) for i, d in enumerate(depths)))
    lo, hi = np.min(sizes, axis=0), np.max(sizes, axis=0)
    return [(f"caps as built: {lo[0]:.2f} to {hi[0]:.2f} x {lo[1]:.2f} to {hi[1]:.2f}, {lo[2]:.2f} to {hi[2]:.2f} "
             f"high, set dimples (1 to {len(S.CAP_SETS)}) off by up to {off:.3f} (the first cap of each set, "
             f"measured) are the stack's ({c['w']} x {c['h']}, {c['height']}, {mk['depth']} deep)", 0.01 - off)]


def cap_bar_rows():
    """the tactile bars on the generated caps (set_caps, every cap of each set) against stack.CAP_BAR_EDGE and
    CAP_BAR, set by set: which edge each one stands on (the mesh over the top face; model -y is the front), how far
    proud, and its top face (the vertices over the cap top) against the stack's bar (w, d, inset)."""
    labels = [lab for row in S.KEY_LEGENDS for lab, _ in row]
    c, b = S.CAP, S.CAP_BAR
    top, yb = c["height"], (c["h"] - 2 * c["cham"]) / 2 - b["inset"]    # yb: the bar's middle off the cap's middle
    got, proud, off = set(), [], 0.0
    for n in S.CAP_SETS:
        for lab, tri in zip(labels, set_caps(n), strict=True):
            v = tri.reshape(-1, 3)
            bar = v[v[:, 2] > top + 0.01, :2]
            if len(bar):
                e = 1 if bar[:, 1].max() < 0 else -1 if bar[:, 1].min() > 0 else 0
                got.add((n, lab, e))
                proud.append(v[:, 2].max() - top)
                y = -e * yb
                off = max(off, *np.abs(np.r_[bar.min(0), bar.max(0)]
                                       - (-b["w"] / 2, y - b["d"] / 2, b["w"] / 2, y + b["d"] / 2)))
    want = {(n, lab, e) for n in S.CAP_SETS for lab, e in S.CAP_BAR_EDGE.items() if e}

    def say(bars):
        return ", ".join(f"{lab} {('back', 'middle', 'front')[e + 1]}" for lab, e in
                         sorted(bars, key=lambda t: labels.index(t[0]))) or "none"

    def by_set(bars):
        return ", ".join(f"set {n} {say({(lab, e)})}" for n, lab, e in sorted(bars)) or "none"
    found = (f"{say({(lab, e) for _, lab, e in got})} in each set, none on the other caps" if got == want
             else f"missing {by_set(want - got)}, extra {by_set(got - want)}")
    p = b["proud"]
    return [(f"cap tactile bars as built: {found}, {min(proud, default=0):.2f} to "
             f"{max(proud, default=0):.2f} proud, their tops {off:.3f} off (every cap of each set, measured) are the "
             f"stack's ({say((lab, e) for lab, e in S.CAP_BAR_EDGE.items() if e)}; {b['w']} x {b['d']}, inset "
             f"{b['inset']}, {p} proud)",
             0.01 - max([off, *(abs(v - p) for v in proud)]) if got == want else -1.0)]


def knob_solids():
    """every knob STEP make_knobs.py wrote (build.sh runs it first), {(FLUTES name, fit variant or "nominal"):
    solid}."""
    kinds = {K.outer_knob: "outer", K.inner_knob: "inner", K.range_knob: "range"}
    out = {}
    for name, solid, args in K.parts():
        if solid not in kinds:
            continue
        kind = args[0] if solid is K.outer_knob and args else kinds[solid]     # outer_knob's flutes, if given
        r = STEPControl_Reader()
        if r.ReadFile(str(HERE / f"{name}.step")) != IFSelect_RetDone:
            raise SystemExit(f"check_fit.py: no {name}.step, run make_knobs.py first")
        r.TransferRoots()
        out[kind, next((t for t in S.FIT_VARIANTS if name.endswith(f"-{t}")), "nominal")] = r.OneShape()
    return out


def knob_measures(tri, kind):
    """measured on a knob's mesh (bottom at z 0): the bore's diameter (the largest reading over TURN, from the
    axis), the outer knob's key width (None on the others) and the flute depth at each flute (crest to trough,
    rays in from outside), half a millimetre under the top chamfer."""
    f = S.FLUTES[kind]
    if kind == "inner":
        ik = S.INNER_KNOB
        h, top = ik["z1"] - ik["z0"], S.INNER_TOP - S.PLATE_Z1 - ik["z0"]          # the bore ends on the shaft tip
        zb = top - K.inner_d_len() / 2
    elif kind == "range":
        rk = S.RANGE_KNOB
        h, lever0, lever1 = rk["z1"] - rk["z0"], S.LEVER_Z0 - S.PLATE_Z1 - rk["z0"], S.LEVER_Z1 - S.PLATE_Z1 - rk["z0"]
        zb = (max(lever0, S.RANGE_RELIEF[1]) + lever1) / 2
    else:
        h = S.OUTER_KNOB["z1"] - S.OUTER_KNOB["z0"]
        zb = (K.outer_key_z0() + h) / 2                                         # beside the key
    bore = max(across(tri, (0.0, 0.0, zb), d)[0] for d in TURN)
    key = None
    if kind.startswith("outer"):
        key = across(tri, ((S.KEY_R + bore / 2) / 2, 0.0, zb), np.array([0.0, 1.0, 0.0]))[0]   # inside the key
    zf, far = h - f["cham"] - 0.5, 20.0

    def radius(a):
        d = np.array([math.cos(a), math.sin(a), 0.0])
        return far - ray_hit(tri, np.array([far * d[0], far * d[1], zf]), -d)
    a, e = 2 * math.pi / f["n"], 1e-4                       # e: off the crest and trough edges of the mesh
    flutes = [radius(k * a + e) - radius((k + 0.5) * a + e) for k in range(f["n"])]
    return bore, key, flutes


def knob_rows(meshes):
    """every knob as make_knobs.py writes it (meshes: {(FLUTES name, variant): mesh}) against the stack: the bore
    (the shaft, FIT and the variant's offset), the outer knobs' key width and the flute depth."""
    rows = []
    for kind, shaft in {"outer": S.OUTER_D, "outer_fms": S.OUTER_D, "inner": S.INNER_D, "range": S.LEVER_D}.items():
        tags = [t for k, t in meshes if k == kind]
        if sorted(tags) != sorted(["nominal", *S.FIT_VARIANTS]):
            rows.append((f"{kind} knob: make_knobs.py writes the fit variants {tags}", -1.0))
            continue
        got = {t: knob_measures(meshes[kind, t], kind) for t in tags}
        want = {t: shaft + S.FIT + S.FIT_VARIANTS.get(t, 0.0) for t in tags}
        f = S.FLUTES[kind]
        flutes = [d for _b, _k, fl in got.values() for d in fl]
        keys = [k for _b, k, _fl in got.values() if k is not None]
        off = max(*(abs(got[t][0] - want[t]) for t in tags), *(abs(d - f["depth"]) for d in flutes),
                  *(abs(k - S.KEY_W) for k in keys))
        rows.append((f"{kind} knob as built ({', '.join(tags)}): bores "
                     f"{', '.join(f'Ø{got[t][0]:.2f}' for t in tags)}, flutes {min(flutes):.2f} to {max(flutes):.2f} "
                     "deep" + (f", key {min(keys):.2f} to {max(keys):.2f} wide" if keys else "")
                     + f" (measured on the solids) are the stack's ({', '.join(f'Ø{want[t]:g}' for t in tags)}, "
                     f"{f['depth']}" + (f", {S.KEY_W}" if keys else "") + ")", 0.01 - off))
    return rows


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


def across(tri, c, d):
    """the two walls seen from the point c along +-d: (distance between them, their middle off c)."""
    a, b = ray_hit(tri, np.array(c), -np.asarray(d)), ray_hit(tri, np.array(c), np.asarray(d))
    return a + b, (b - a) / 2


def fit_circle(pts):
    """centre (2,) and radius of the circle fitted to the points (n, 2) by least squares, NaN for fewer than
    three."""
    if len(pts) < 3:
        return np.full(2, math.nan), math.nan
    m = pts.mean(0)
    p = pts - m
    (a, b, c), *_ = np.linalg.lstsq(np.c_[2 * p, np.ones(len(p))], (p * p).sum(1), rcond=None)
    return m + (a, b), math.sqrt(c + a * a + b * b)


def corner_arcs(p):
    """the corners of a rounded rectangle given as points (n, 2) round it: the points off its bounding box's
    sides, in four groups by quarter. The DXF's corners are such points, each on its arc (geom.rounded_rect)."""
    lo, hi = p.min(0), p.max(0)
    off = ((p - lo > 1e-4) & (hi - p > 1e-4)).all(1)
    q = (p > (lo + hi) / 2) @ (1, 2)
    return [p[off & (q == k)] for k in range(4)]


def through_holes(tri):
    """how many holes go through a closed mesh: its genus, from V - E + F = 2 - 2 g with the faces' meshes joined
    at their shared edges."""
    _, idx = np.unique(np.round(tri.reshape(-1, 3), 6), axis=0, return_inverse=True)
    f = idx.reshape(-1, 3)
    edges = np.unique(np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1), axis=0)
    return (2 - (idx.max() + 1 - len(edges) + len(f))) // 2


def ring(cx, cy, z, r, n=72):
    """n points on a horizontal circle of radius r round (cx, cy) at height z, and their outward directions."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    dirs = np.stack([np.cos(a), np.sin(a), np.zeros(n)], 1)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, z)], 1), dirs


def near(tri, x, y, r):
    """the triangles whose xy bounding box comes within r of (x, y): keeps the ray casts below fast."""
    lo, hi = tri[:, :, :2].min(1), tri[:, :, :2].max(1)
    return tri[(lo[:, 0] < x + r) & (hi[:, 0] > x - r) & (lo[:, 1] < y + r) & (hi[:, 1] > y - r)]


# A round wall is facets on a mesh, and a ray across it can only read its diameter small: a diameter measured on a
# mesh is the largest reading over these directions.
TURN = [np.array([math.cos(t), math.sin(t), 0.0]) for t in np.radians(np.arange(0.0, 180.0, 2.0))]


def body_measures(tri):
    """measured on the body mesh (board frame), as a dict. At the five screw bosses: the counterbore radius `cb`
    (least and most; at the middle column along the bar, where it has a wall), the seat's height `seat_z` (from
    below, up the counterbore beside the screw hole) and the PA12 between the seat and the PCB `seat_t`. At the four
    corner bosses the boss wall round the counterbore towards the cavity, in the PCB room, `wall`. The middle
    column's bar in plan `bar` (x0, y0, x1, y1) and its wall beyond the counterbore `bar_wall`. The wall tops
    `wall_top` (least and most, one on each wall), the USB-C slot in the back wall `slot` (its width at two heights,
    least and most, whether it is open at the wall top, and how far its middle is off the socket's axis), the post's
    top `post_top`, and the flat pad round each foot `pad` (radius on the bottom plane before it steps into the
    hollow)."""
    z = (MM.Z_FLOOR_TOP + S.SEAT_Z) / 2                 # in the PCB room, below the counterbore seats
    up, down = np.array([0.0, 0.0, 1.0]), np.array([0.0, 0.0, -1.0])
    ex, ey = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
    r_seat = (MM.SCREW_CLEAR + MM.HEAD_R) / 2           # on the seat, between the screw hole and the counterbore
    cb, wall, seat_t, seat_z = [], [], [], []
    for mx, my in B.MOUNTS:
        tri_m = near(tri, mx, my, 15.0)
        if (mx, my) == B.MID_MOUNT:                     # along the bar only: across it the counterbore is open
            r_cb = min(ray_hit(tri_m, np.array([mx, my, z]), d) for d in (ey, -ey))
            x0, x1 = (mx + sx * ray_hit(tri_m, np.array([mx, my + r_cb + 0.5, z]), sx * ex) for sx in (-1.0, 1.0))
            y0, y1 = (my + sy * (r_cb + 0.5 + ray_hit(tri_m, np.array([mx, my + sy * (r_cb + 0.5), z]), sy * ey))
                      for sy in (-1.0, 1.0))
            bar, bar_wall = (x0, y0, x1, y1), min(y1 - my, my - y0) - r_cb
        else:
            pts, dirs = ring(mx, my, z, 0.0)
            r_cb = min(ray_hit(tri_m, q, d) for q, d in zip(pts, dirs, strict=True))
            pts, dirs = ring(mx, my, z, r_cb + 0.01)
            # towards the cavity only (within 60 deg of the board centre); towards the corner the boss runs into
            # the outer walls, which the counterbore-to-outer-wall row checks
            to_c = np.array([B.W / 2 - mx, B.H / 2 - my]) / math.hypot(B.W / 2 - mx, B.H / 2 - my)
            inward = dirs[:, :2] @ to_c > 0.5
            wall.append(min(ray_hit(tri_m, q, d) for q, d in zip(pts[inward], dirs[inward], strict=True)) + 0.01)
        cb.append(r_cb)
        pts, _ = ring(mx, my, -S.PCB_T - 0.01, r_seat, 24)
        seat_t.append(ray_hits(tri_m, pts, (0, 0, -1)).min() + 0.01)
        seat_z += [ray_hit(tri_m, np.array([mx, my + sy * r_seat, -30.0]), up) - 30.0 for sy in (-1.0, 1.0)]
    mid_w = MM.o - MM.WALL / 2                          # the middle of a wall, out from the board's edge
    tops = [20.0 - ray_hit(near(tri, x, y, 5.0), np.array([x, y, 20.0]), down)
            for x, y in ((B.W / 2, -mid_w), (B.W / 2, B.H + mid_w), (-mid_w, B.H / 2), (B.W + mid_w, B.H / 2))]
    tri_u = near(tri, B.USB_X, -mid_w, 15.0)
    wall_z = S.PLATE_Z0 - S.WALL_GAP
    sides = [[ray_hit(tri_u, np.array([B.USB_X, -mid_w, zz]), sx * ex) for sx in (-1.0, 1.0)]
             for zz in (2.0, wall_z - 0.3)]             # the slot's two sides from the socket's axis, at two heights
    widths = [a + b for a, b in sides]
    is_open = all(ray_hit(tri_u, np.array([B.USB_X + dx, -mid_w, 2.0]), up) == math.inf
                  for dx in (-min(widths) / 2 + 0.3, 0.0, min(widths) / 2 - 0.3))
    posts = [20.0 - ray_hit(near(tri, x, y, 5.0), np.array([x, y, 20.0]), down) for x, y in MM.SUPPORTS]
    pads = []
    for fx, fy in MM.FEET:
        tri_f = near(tri, fx, fy, 10.0)

        def flat(j, fx=fx, fy=fy, tri_f=tri_f):
            """the ring of radius 0.05 j round the foot on the bottom plane"""
            pts, _ = ring(fx, fy, 0.0, 0.05 * j, 32)
            pts[:, 2] = [MM.z_bottom(y) - 1.0 for y in pts[:, 1]]
            return np.abs(ray_hits(tri_f, pts, (0, 0, 1)) - 1.0).max() <= 0.02   # not off the bottom plane

        # the last ring on the plane, in 0.05 mm steps up to 8 mm; the pad is flat out to where it steps into the
        # hollow, so bisect as rib_width() does: lo on the plane (radius 0 is), hi off it
        lo, hi = 0, 160
        if flat(hi):
            lo = hi
        while hi - lo > 1:
            mid = (lo + hi) // 2
            lo, hi = (mid, hi) if flat(mid) else (lo, mid)
        pads.append(0.05 * lo)
    return dict(cb=(min(cb), max(cb)), wall=min(wall), seat_t=min(seat_t), seat_z=(min(seat_z), max(seat_z)),
                bar=bar, bar_wall=bar_wall, wall_top=(min(tops), max(tops)),
                slot=(min(widths), max(widths), is_open, max(abs(b - a) / 2 for a, b in sides)), post_top=posts,
                pad=min(pads))


def plate_measures(tri):
    """measured on the plate mesh (plate frame, back face at z 0), as a dict, each feature found by rays from fixed
    points beside it, each diameter the largest reading over TURN. The encoder pockets: across the lugs `ec_w` and
    along `ec_h` (1 mm into the pocket) and their depth `ec_depth` (least and most of the three each); the RANGE
    pocket's diameter `rp_d` and depth `rp_depth`; how far the worst pocket's middle is off its part's axis
    `pocket_off`. The light holes `lights`: name -> (how far off its place, diameter). The
    bosses: how far the worst is off its place `boss_off`, their diameters `boss_d` and heights `boss_h` (least and
    most; the height from below, between the tapped hole and the boss edge) and the deepest tapped hole `tap` (up
    its axis from the boss end to the drill point). The tongue `tongue`: off its place along the edge `x`, its
    outer face off the plate's back edge (the DXF outline) `out`, and its size w, d, h. Over the pockets: the key
    holes `keys` (width w and height h, least and most, and the worst middle off its key), the encoder holes
    `shaft` (diameter, least and most) and the RANGE hole `range_d`, the worst of those holes off its part's axis
    `hole_off`. The through holes of the DXF's CUT layer `cut`, each where the DXF has it: the worst middle off
    and size off; how many the DXF has `cut_n` and the plate `through`; the plate's extent off the DXF's outline
    `extent`. The corner radii of every key hole `key_r` and of the outline `out_r`, each a pair of lists (in the
    DXF, on the plate)."""
    ex, ey, up = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    z0 = -20.0

    def opening(x, y, z, round_):
        """the hole or pocket round (x, y) at height z: its middle off (x, y) and its width and height (a round
        one: its diameter for both)"""
        t = near(tri, x, y, 15.0)
        (w, ox), (h, oy) = across(t, (x, y, z), ex), across(t, (x, y, z), ey)
        if round_:
            w = h = max(across(t, (x + ox, y + oy, z), d)[0] for d in TURN)
        return ox, oy, w, h

    def from_outside(c, d, reach):
        """a part that stands alone round the point c, found from `reach` away on both sides along d: (its size,
        its middle off c)"""
        a, b = (reach - ray_hit(tri, np.array(c) + sg * reach * d, -sg * d) for sg in (-1.0, 1.0))
        return a + b, (b - a) / 2

    ec_w, ec_h, ec_depth, pocket_off = [], [], [], []
    for name in ("ALTHDG", "FREQ", "FMS"):
        cx, cy = PS.P(*getattr(B, name))
        ox, oy, w, h = opening(cx, cy, 1.0, False)
        ec_w.append(w); ec_h.append(h); pocket_off.append(math.hypot(ox, oy))
        ec_depth.append(ray_hit(tri, np.array([cx + S.EC11_POCKET[0] / 2 - 1.0, cy, z0]), up) + z0)
    cx, cy = PS.P(*B.RANGE)
    ox, oy, rp_d, _ = opening(cx, cy, 1.0, True)
    pocket_off.append(math.hypot(ox, oy))
    rp_depth = ray_hit(tri, np.array([cx + (S.RANGE_HOLE + S.RANGE_POCKET[0]) / 4, cy, z0]), up) + z0
    lights = {}
    for name, ((lx, ly), _g, _c) in B.LEDS.items():
        ox, oy, dia, _ = opening(*PS.P(lx, ly), S.PLATE_T / 2, True)
        lights[name] = (math.hypot(ox, oy), dia)
    zf = (max(S.EC11_POCKET[3], S.RANGE_POCKET[1]) + S.PLATE_T) / 2         # over every pocket floor
    keys = [opening(*PS.P(x, y), zf, False) for y in B.ROWS for x in B.COLS]
    shaft = [opening(*PS.P(*getattr(B, n)), zf, True) for n in ("ALTHDG", "FREQ", "FMS")]
    rng = opening(*PS.P(*B.RANGE), zf, True)
    cut_layer = PA.dxf_layers()["CUT"]
    outline = max(cut_layer, key=lambda p: np.ptp(np.array(p), axis=0).prod())

    xy = np.unique(tri[:, :, :2].reshape(-1, 2), axis=0)

    def corners(p):
        """the corner radii of a rounded rectangle in the DXF (points p) and on the plate there: the circle fitted
        to the mesh's vertices (each on its face) in the corner's quarter within 0.25 of the DXF's arc."""
        dxf, plate = [], []
        for arc in corner_arcs(p):
            c, r = fit_circle(arc)
            w = xy - c
            on = (w * (arc.mean(0) - c) > 0).all(1) & (np.abs(np.hypot(*w.T) - r) < 0.25)
            dxf.append(r); plate.append(fit_circle(xy[on])[1])
        return dxf, plate

    cut_off, cut_size, key_r = 0.0, 0.0, [[], []]
    out_r = corners(np.array(outline))
    for poly in cut_layer:
        if poly is outline:
            continue
        p = np.array(poly)
        (hx, hy), (w, h) = (p.max(0) + p.min(0)) / 2, np.ptp(p, axis=0)
        r = np.hypot(*(p - (hx, hy)).T)
        is_round = r.max() - r.min() < 1e-3
        ox, oy, mw, mh = opening(hx, hy, zf, is_round)
        cut_off, cut_size = max(cut_off, math.hypot(ox, oy)), max(cut_size, abs(mw - w), abs(mh - h))
        if not is_round:                                    # the key holes, the only ones not round
            dxf, plate = corners(p)
            key_r[0] += dxf; key_r[1] += plate
    v = tri.reshape(-1, 3)
    o = np.array(outline)
    extent = float(np.abs(np.concatenate([v[:, :2].min(0) - o.min(0), v[:, :2].max(0) - o.max(0)])).max())
    rb = (S.TAP["drill"] / 2 + S.TAP["cham"] + S.BOSS["d"] / 2) / 2      # between the countersink and the boss edge
    zb = -S.BOSS["h"] / 2
    offs, dias, heights, depths = [], [], [], []
    for mx, my in B.MOUNTS:
        px, py = PS.P(mx, my)
        ox, oy = from_outside((px, py, zb), ex, 6.0)[1], from_outside((px, py, zb), ey, 6.0)[1]
        offs.append(math.hypot(ox, oy))
        dias.append(max(from_outside((px + ox, py + oy, zb), d, 6.0)[0] for d in TURN))   # across its own middle
        end = ray_hit(tri, np.array([px + rb, py, z0]), up) + z0                 # the boss end face
        heights.append(-end)
        tip = ray_hit(tri, np.array([px, py, z0]), up) + z0                      # the drill point's tip
        depths.append(tip - end)
    tg = S.USB_TONGUE
    tx, ty = PS.P(B.USB_X, -S.OVH)
    c = (tx, ty - tg["d"] / 2, -tg["h"] / 2)                             # the tongue's middle
    (w, x_off), (d, y_off) = from_outside(c, ex, tg["w"] / 2 + 6.0), from_outside(c, ey, tg["d"] / 2 + 6.0)
    # its outer face against the plate's back edge, the DXF outline's largest y
    tongue = dict(x=x_off, out=c[1] + y_off + d / 2 - o[:, 1].max(), w=w, d=d,
                  h=-(ray_hit(tri, np.array([tx, ty - tg["d"] / 2, z0]), up) + z0))
    return dict(ec_w=(min(ec_w), max(ec_w)), ec_h=(min(ec_h), max(ec_h)), ec_depth=(min(ec_depth), max(ec_depth)),
                rp_d=rp_d, rp_depth=rp_depth, pocket_off=max(pocket_off), lights=lights, boss_off=max(offs),
                boss_d=(min(dias), max(dias)),
                boss_h=(min(heights), max(heights)), tap=max(depths), tongue=tongue,
                keys=dict(w=(min(k[2] for k in keys), max(k[2] for k in keys)),
                          h=(min(k[3] for k in keys), max(k[3] for k in keys)),
                          off=max(math.hypot(k[0], k[1]) for k in keys)),
                shaft=(min(s[2] for s in shaft), max(s[2] for s in shaft)), range_d=rng[2],
                hole_off=max(math.hypot(s[0], s[1]) for s in [*shaft, rng]), cut=(cut_off, cut_size),
                cut_n=len(cut_layer) - 1, through=through_holes(tri), extent=extent, key_r=key_r, out_r=out_r)


def turned_measures(range_knob, pipe):
    """measured on the RANGE knob and the light pipe (solids of revolution, their XZ sections): the knob's skirt
    diameter, the dish (how far the rim's bottom edge is over the hub's flat) and the rim's thickness at its edge;
    the pipe's base and rod diameters, the base's length up to the shoulder and the whole length."""
    sk = solid_radius(range_knob)
    edge = crossings(range_knob, sk - 0.001)
    knob = dict(skirt_d=2 * sk, dish=edge[0] - crossings(range_knob, S.RANGE_KNOB["hub_d"] / 2 - 0.05)[0],
                rim=edge[1] - edge[0])
    base_r, axis = solid_radius(pipe), crossings(pipe, 0.0)
    rod_r = max(abs(x) for xs, zs in section(pipe, 0.0) for x, zz in zip(xs, zs, strict=True) if zz > axis[-1] - 1.0)
    base = crossings(pipe, (rod_r + base_r) / 2)
    return knob, dict(base_d=2 * base_r, rod_d=2 * rod_r, base_len=base[-1] - base[0], len=axis[-1] - axis[0])


def pair_measures(tri):
    """measured on the mesh of the light pipe pair as it is ordered (make_knobs.light_pipe_pair): the necks' diameter
    (least and most of the two) and length (the gap between the bar and a base, beside the neck), the bar's section
    (width, height) and the part's size over all, largest first."""
    pp, pitch = S.PIPE, K.PIPE_PITCH
    ey, ez = np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    neck_d = [max(across(tri, (x, 0.0, -pp["neck_len"] / 2), d)[0] for d in TURN) for x in (0.0, pitch)]
    beside = (pp["neck_d"] + pp["bar"][0]) / 4                           # between a neck and the bar's edge
    neck_len = [ray_hit(tri, np.array([x + beside, 0.0, -1e-3]), -ez) + 1e-3 for x in (0.0, pitch)]
    mid = (pitch / 2, 0.0, -pp["neck_len"] - pp["bar"][1] / 2)           # inside the bar
    size = sorted((tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)).tolist(), reverse=True)
    return dict(neck_d=(min(neck_d), max(neck_d)), neck_len=(min(neck_len), max(neck_len)),
                bar=(across(tri, mid, ey)[0], across(tri, mid, ez)[0]), size=size)


def rib_width(name, z=1.5):
    """width of the first rib (along +x) of the generated cap of set name, z over the socket mouth: rays along +x
    hit the rib face well inside the 3.8 mm bore, or the bore wall beside the rib."""
    tri, R = first_cap(name), S.CAP_SOCKET["d"] / 2

    def on_rib(y):
        return ray_hit(tri, np.array([0.0, y, z]), np.array([1.0, 0.0, 0.0])) < math.sqrt(R * R - y * y) - 0.05
    lo, hi = 0.0, 1.0                                   # 1.0: short of the next rib (at 90 deg)
    if not on_rib(lo) or on_rib(hi):
        raise ValueError(f"cap set {name}: no rib along +x")
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
    if not zs:
        raise ValueError(f"cap set {name}: no ribs found in the generated socket")
    return np.array(zs), np.array(ds), max(dev)


def cap_texture():
    """the caps' texture as ordered (caps-A.zip; every set has the same one), RGB array."""
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
    part_tol, hole_tol = S.WJP_TOL["size"], S.WJP_TOL["hole"]
    lo_i, hi_i = S.CAP_GRIP
    sizes = sorted(S.CAP_SETS.values())
    step = max(b - a for a, b in zip(sizes, sizes[1:], strict=False))   # the widest step between two sets
    # the plunger the sets are for: TE's model, or as far off it as a reprint moved them (stack.CAP_SETS_MOVE)
    move = S.CAP_SETS_MOVE
    plunger = S.plunger_d(hs) + move
    # interference on a true print (diametral) at the socket mouth, from the design: the sets' print coverage
    fit = {n: plunger - S.cap_rib_d(n, hs) for n in S.CAP_SETS}
    # set dimples: walls to the socket bore and to the cap outline, nominal and at the worst print
    mk, bar = S.CAP_MARK, S.CAP_BAR
    front = [lab for lab, edge in S.CAP_BAR_EDGE.items() if edge == 1]       # the caps with a front bar
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
        (f"front tactile bar ({bar['proud']} proud) hides none of the {' and '.join(front)} legends from "
         f"{S.CAP_VIEW_DEG:.0f} deg",
         min(S.CAP["h"] / 2 - S.CAP["cham"] - legend_front(lab) - bar["inset"] - bar["d"] / 2
             for lab in front) - bar["proud"] / math.tan(math.radians(S.CAP_VIEW_DEG))),
        (f"cap legend strokes at least {S.LEGEND_STROKE_MIN} wide (WJP colour): thinner ink reaches {ink_d:.2f} "
         f"(on {ink_at}), corners and tips only, within 0.25", 0.25 - ink_d),
        (f"cap bore clears the plunger between the ribs (bore {sk['d']} -{hole_tol}, plunger {plunger:.2f} "
         "at the mouth)", (sk["d"] - hole_tol - plunger) / 2),
        (f"cap seats on the plunger top: cap bottom over the switch body ({S.SWITCH_BODY_TOP:.1f}), pressed",
         c["base"] - S.KEY_TRAVEL - S.PLUNGER_TOP_TOL - S.SWITCH_BODY_TOP),
        # The plate bowed towards the board at the key nearest its middle, the board taken flat: a board bowed
        # towards the plate (PCB_BOW) lifts the caps in the middle by up to 0.1, and with it the
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
        i = S.plunger_d(hs - zs[0]) + move - ds[0]                 # interference at the lowest contact
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
                 f"{lo_i} to {hi_i}), on a plunger {move:+.2f} off TE's model", worst))
    rows.append((f"cap sets moved {move:+.2f} (stack.CAP_SETS_MOVE), up to TE's +-0.30 on the plunger diameter",
                 0.35 - abs(move)))                       # three 0.1 steps either way, not a fourth
    return rows


def key_hole_max():
    """the key hole at its largest (+KEY_HOLE_TOL on width and height, after anodising)."""
    (w, h, r), up = S.KEY_HOLE, S.KEY_HOLE_TOL[0]
    return w + up, h + up, r + up / 2


def plate_bow(x, y):
    """how far a bowed plate stands off the plane of its four corner bosses at board point (x, y), per mm of bow (the
    drawing's flatness): the worst of a dome (the reading is the plate's corners against its
    middle), a bow along the plate (its ends against its middle) and a bow across it (its long edges against its
    middle line). The middle boss, which holds the plate and the board together there, is left out: it only
    makes both flatter."""
    hx, hy = B.W / 2 + S.OVH, B.H / 2 + S.OVH                          # plate half length and width
    sx, sy = B.W / 2 - B.CORNER_MOUNTS[0][0], B.H / 2 - B.CORNER_MOUNTS[0][1]   # corner bosses off the middle
    dx, dy = x - B.W / 2, y - B.H / 2
    dome = (sx * sx + sy * sy - dx * dx - dy * dy) / (hx * hx + hy * hy)
    along = (sx * sx - dx * dx) / (hx * hx)
    across = (sy * sy - dy * dy) / (hy * hy)
    return max(dome, along, across, 0.0)


def mjf(length):
    """JLC3DP MJF tolerance on a length (+-): stack.MJF_TOL up to 100 mm, MJF_SCALE of it above."""
    return max(S.MJF_TOL, S.MJF_SCALE * length)


def usb_rows():
    """USB-C socket and plug in the back wall opening (make_mech.USB_OPEN, carried up as a slot): its sides and
    bottom. Its top edge is the plate's tongue (tongue_rows)."""
    u, place, hole = MM.USB_OPEN, S.LED_LENS["place"], S.POS_TOL["body_hole"]   # J1's placement, MJF on the opening
    # the board lies anywhere in the cavity (CLEAR). Its sideways play is set by its short edges against the
    # side walls: routed (+-0.2) without edge rails, but taken as V-cut (+-PCB_VCUT_TOL), the fallback should
    # JLCPCB put rails on them: at worst one of them is that much short.
    # Against a side wall the opening sits that far plus USB_X (or W - USB_X) from the board edge, and MJF puts
    # it within mjf() of that length from the wall: this also covers a body printed large, whose gap grows
    edge = MM.CLEAR + S.PCB_VCUT_TOL
    float_ = edge + max(mjf(B.USB_X + MM.CLEAR), mjf(B.W - B.USB_X + MM.CLEAR))   # 0.9 + 0.51 (left wall)
    j1w, j1h = B.J1_BODY[2] - B.J1_BODY[0], MM.J1_H     # the socket face is at board y J1_BODY[1]
    bot = u["z"] - u["h"] / 2                            # opening bottom
    z_tol = mjf(-S.PCB_T - bot)                         # MJF: boss top (the PCB underside) to the opening bottom
    om_w, om_h = MM.USB_PLUG
    ow, oh, orr = u["w"] - 2 * hole, u["h"] - 2 * hole, u["r"] - hole
    zc = -S.PCB_T - j1h / 2 - u["z"]                    # plug centre, on the socket's middle, over the opening's
    # a square overmould (no corner radius) off centre by the float and J1 in x, J1 and the body height in z:
    # least clearance to the opening's sides and bottom (above its middle the opening is a slot with straight
    # sides); J1 and the body both hang from the PCB underside, so the PCB thickness drops out
    xs = np.linspace(-om_w / 2, om_w / 2, 241)
    zs = np.linspace(-om_h / 2, om_h / 2, 131)
    ex = np.concatenate([xs, xs, np.full_like(zs, -om_w / 2), np.full_like(zs, om_w / 2)])
    ez = np.concatenate([np.full_like(xs, -om_h / 2), np.full_like(xs, om_h / 2), zs, zs])
    om = 1e9
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = ex + sx * (float_ + place), ez + zc + sz * (place + z_tol)
            sd = np.minimum(rrect_sd(x, z, ow, oh, orr), np.where(z > 0, np.abs(x) - ow / 2, np.inf))   # the slot
            om = min(om, -sd.max())
    return [
        (f"USB-C socket ({j1w:.2f} wide, {-B.J1_BODY[1]:.2f} past the PCB edge) passes the wall slot: board "
         f"{float_:.2f} off (cavity, V-cut edge, MJF on the opening), J1 {place}, MJF -{hole}",
         ow / 2 - j1w / 2 - float_ - place),
        (f"USB-C socket ({j1h} high under the PCB, J1 {place}) over the opening bottom (MJF -{hole}, body "
         f"height {z_tol})", (-S.PCB_T - j1h - place - z_tol) - (bot + hole)),
        (f"USB-C socket ({j1h} high, J1 {place}) over the body floor under the PCB ({MM.UNDER} room, MJF "
         f"-{mjf(MM.UNDER)})", MM.UNDER - j1h - place - mjf(MM.UNDER)),
        (f"USB-C overmould ({om_w} x {om_h}, square) in the {u['w']} wide opening (R{u['r']} below, open to the "
         f"tongue above): board {float_:.2f} off, J1 {place}, body height {z_tol}, MJF -{hole}", om),
    ]


def tongue_rows(back_lo, back_hi, bow, board, slot, measured):
    """the plate's tongue (stack.USB_TONGUE) in the body's slot over the USB-C opening: its sides in the slot, its
    end over the plug and the board, its inner face short of J1's shell tabs. back_lo, back_hi: the plate's back
    face at its lowest and highest; bow: the plate's bow at the tongue, either way; board: the board off the
    plate's hole pattern, at most (the caps, the plate, the PCB); slot: the slot's width as built, least and most
    (body_measures); measured: the tongue on the plate solid (plate_measures)."""
    t, hole, pt = S.USB_TONGUE, S.POS_TOL["body_hole"], S.POS_TOL
    place, pcb_tol = S.LED_LENS["place"], S.STACK_TOL["pcb"]         # J1's placement
    om_w, om_h = MM.USB_PLUG
    slot_lo, slot_hi = slot[0] - 2 * hole, slot[1] + 2 * hole
    # the slot against the tongue with the body centred on its screws, as it is put on by eye before they are
    # tightened: MJF from the middle of the screw pattern, and the tongue against the bosses on the plate. The
    # screws' play (make_mech.SCREW_OFFSET) lets the body sit further off, up to where the tongue stops it.
    x_off = mjf(abs(B.USB_X - B.W / 2)) + pt["plate"]
    side = (slot_lo - t["w"] - t["tol"]) / 2 - x_off
    side_hi = (slot_hi - t["w"] + t["tol"]) / 2 + x_off
    end_lo = back_lo - bow - t["h"] - t["tol"]                      # the tongue's end over the PCB top
    end_hi = back_hi + bow - t["h"] + t["tol"]
    # the plug on the socket's middle, the socket hanging under a thin board (the plate stands on the board's top)
    om_top = -S.PCB_T + pcb_tol - MM.J1_H / 2 + om_h / 2 + place
    # the tongue's inner face, how far outside the board's back edge: the board that far towards it, the tongue thick
    inner = S.OVH - t["d"] - t["d_tol"] - board
    m = measured
    return [
        (f"plate tongue {m['w']:.2f} x {m['d']:.2f}, {m['h']:.2f} long, {abs(m['x']):.2f} off its place over the "
         f"socket and {abs(m['out']):.2f} off the plate's edge (measured on the plate) is the stack's ({t['w']} x "
         f"{t['d']}, {t['h']})", 0.01 - max(abs(m["w"] - t["w"]), abs(m["d"] - t["d"]), abs(m["h"] - t["h"]),
                                           abs(m["x"]), abs(m["out"]))),
        (f"USB-C tongue ({t['w']} +{t['tol']}) in the {slot[0]:.2f} slot (measured on the body, MJF -{2 * hole:.1f}), "
         f"per side, the slot {x_off:.2f} off it (MJF, plate) with the body centred on its screws by eye", side),
        (f"USB-C tongue side gap at most {side_hi:.2f} with the body centred on its screws (slot +{2 * hole:.1f}, "
         f"tongue -{t['tol']}, off the other way), within {S.USB_GAP_MAX}", S.USB_GAP_MAX - side_hi),
        (f"USB-C tongue end ({end_lo:.2f} over the PCB top at its lowest: low plate bowed {bow:.3f} down, tongue "
         f"+{t['tol']}) over the plug overmould's top ({om_top:.2f}: PCB -{pcb_tol}, J1 {place})", end_lo - om_top),
        ("USB-C tongue end over the PCB top, where the board reaches under it", end_lo),
        (f"USB-C tongue end at most {end_hi:.2f} over the PCB top (tongue -{t['tol']}, high plate bowed up): the gap "
         f"over the plug within {S.USB_GAP_MAX}", S.USB_GAP_MAX - end_hi),
        (f"USB-C tongue ({t['w']} -{t['tol']}) covers the plug overmould ({om_w}) across, the board {board:.2f} off "
         f"the plate, J1 {place}", (t["w"] - t["tol"]) / 2 - om_w / 2 - board - place),
        (f"USB-C tongue's inner face ({t['d']} +{t['d_tol']} thick, the board {board:.2f} towards it) short "
         f"of J1's shell tabs and their fillets ({MM.J1_TABS_IN} in from the board edge)", MM.J1_TABS_IN + inner),
        (f"USB-C tongue ({t['h']} +{t['tol']}) shorter than the bosses ({S.BOSS['h']} -{S.BOSS['h_tol']}): it never "
         "reaches the board and needs no thicker stock", S.BOSS["h"] - S.BOSS["h_tol"] - t["h"] - t["tol"]),
        (f"USB-C tongue {t['d']} thick, {t['h']} long: within 4 x its thickness (milling; a ratio)",
         4 - t["h"] / t["d"], ""),
    ]


def plan_item(f):
    """a feature of the body in plan, a rectangle (x0, y0, x1, y1) or a disc (x, y, r), as a geom.py item."""
    return ("cap", f[0], f[1], f[0], f[1], f[2]) if len(f) == 3 else ("rect", *f, 0.0)


def under_board(pads):
    """what hangs under the board, in plan: (name, geom.py item, how far it can be off its place on the board) of
    every through-hole lead, taken as wide as its solder fillet can get (its pad), and of every bottom-side
    part's body (board.bodies())."""
    on_pins = {"K": S.CAP_TOL["switch"], "ENC": S.ENC_ON_PINS, "RANGE": S.RKJXT_ON_PINS, "J1": S.LED_LENS["place"]}
    leads = [(q.name, pad_geom(q), next(v for k, v in on_pins.items() if q.name.startswith(k)))
             for q in pads if q.drill]
    return leads + [(ref, ("rect", *r, 0.0), S.LED_LENS["place"]) for ref, r in B.bodies().items()]


def cavity_play():
    """how far the board can lie off the body's middle while the body is lowered over it, no screw in yet (the
    board against a cavity wall): in x (a large cavity, a board routed short) and in y (MJF on the cavity width,
    the board with a V-cut edge short)."""
    play_x = ((B.W + 2 * MM.CLEAR) * (1 + S.MJF_SCALE) - (B.W - S.PCB_OUTLINE_TOL)) / 2
    cav_h = B.H + 2 * MM.CLEAR
    play_y = (cav_h + mjf(cav_h) - (B.H - max(S.PCB_OUTLINE_TOL, S.PCB_VCUT_TOL))) / 2
    return play_x, play_y


def room_rows(pads, board_off, bar):
    """the body's features in the room under the board against every through-hole lead (as wide as its pad, for its
    solder fillet) and every bottom-side part: the post, the corner bosses with the blocks that join them to the
    walls, and the middle column (its bar as built, `bar` from body_measures, and its round boss). Each feature at
    its widest, printed large. With the screws in, it is off its screw by the hole's play (the post by MJF from the
    nearest hole as well) and the board off the screw by board_off. While the body is lowered over the board, the
    board lies against the cavity walls: up to the cavity's play in x and y at once for the post and the column,
    which sit where MJF puts them in the cavity, and for a corner boss up to where MJF puts it from its two walls.
    Each row is the least over all leads and parts, of the worse of the two cases."""
    pt = S.POS_TOL
    grow, col_off = pt["body_hole"], MM.SCREW_OFFSET
    items = under_board(pads)
    play = cavity_play()
    wall = B.CORNER_MOUNTS[0][0] + MM.CLEAR             # a corner boss from its walls (a length, MJF)
    in_corner = (MM.CLEAR + mjf(wall) + S.PCB_OUTLINE_TOL / 2,
                 MM.CLEAR + mjf(wall) + max(S.PCB_OUTLINE_TOL, S.PCB_VCUT_TOL) / 2)
    mid = B.MID_MOUNT

    def in_cavity(x, y):
        return mjf(math.hypot(x - B.W / 2, y - B.H / 2))            # a feature off its place in the cavity (MJF)

    # (name, its shapes, off its screw with the screws in, the board's play while lowered, off its place then)
    feats = [("body post", [(px, py, MM.SUPPORT_R)],
              col_off + mjf(min(math.hypot(px - mx, py - my) for mx, my in B.MOUNTS)), play, in_cavity(px, py))
             for px, py in MM.SUPPORTS]
    feats += [("corner bosses and their blocks",
               [f for mx, my in B.CORNER_MOUNTS for f in MM.corner_plan(mx, my, MM.BOSS_R_LOW)], col_off, in_corner,
               0.0),
              ("middle column (its bar and round boss)", [bar, (*mid, MM.BOSS_R)], col_off, play, in_cavity(*mid))]
    rows = []
    for what, shapes, screwed, (px_, py_), lowered in feats:
        shapes = [plan_item(f) for f in shapes]
        worst = (math.inf, "none", 0.0, 0.0, 0.0)
        for name, g, on in items:
            gap = min(item_dist(f, g) for f in shapes)
            if gap > 8.0:
                continue
            fixed = gap - (screwed + board_off + pt["pcb"] + on)
            moved = [(g[0], g[1] + dx, g[2] + dy, g[3] + dx, g[4] + dy, g[5])
                     for dx in (-px_, 0.0, px_) for dy in (-py_, 0.0, py_)]
            going_on = min(item_dist(f, q) for f in shapes for q in moved) - (lowered + pt["pcb"] + on)
            worst = min(worst, (min(fixed, going_on) - grow - S.LEAD_CLEAR, name, gap, fixed, going_on))
        margin, name, gap, fixed, going_on = worst
        rows.append((f"{what} (MJF +{grow} per side) clear of the leads' solder fillets and the bottom-side parts: "
                     f"the closest at the worst offsets is {name}, {gap:.2f} off, {fixed:.2f} left with the screws in "
                     f"(hole play, board, PCB, part) and {going_on:.2f} while the body goes on (the board against the "
                     f"cavity walls), beyond {S.LEAD_CLEAR}", margin))
    return rows


def legend_gap():
    """least distance from the amber legends' outlines (make_plate_art.py's UV_AMBER layer) to the edge of a hole
    in the plate, the key and light holes at their largest: the gap and which holes."""
    lt = (S.LIGHT_HOLE + S.LIGHT_HOLE_TOL[0]) / 2
    best = (math.inf, "none")
    for poly in PA.layers["UV_AMBER"]:
        pts = np.array(poly + poly[:1])
        seg = np.diff(pts, axis=0)
        n = np.maximum(np.ceil(np.hypot(seg[:, 0], seg[:, 1]) / 0.02).astype(int), 1)   # a point every 0.02 mm
        x, y = np.concatenate([np.linspace(a, b, k, endpoint=False)
                               for a, b, k in zip(pts, pts[1:], n, strict=False)]).T
        d = [(float(rrect_sd(x - kx, y - ky, *key_hole_max()).min()), "key holes") for ky in B.ROWS for kx in B.COLS]
        d += [(float((np.hypot(x - lx, y - ly) - lt).min()), "light holes") for (lx, ly), _g, _c in B.LEDS.values()]
        d += [(float((np.hypot(x - kx, y - ky) - (S.SHAFT_HOLE + S.PLATE_GEN_TOL) / 2).min()), "encoder holes")
              for kx, ky in (B.ALTHDG, B.FREQ, B.FMS)]
        d += [(float((np.hypot(x - B.RANGE[0], y - B.RANGE[1]) - (S.RANGE_HOLE + S.PLATE_GEN_TOL) / 2).min()),
               "RANGE hole")]
        best = min(best, min(d))
    return best


def boss_wall_rows():
    """the plate's corner bosses between the cavity walls. The body sits on its screws, which the bosses
    locate: each body hole stays within the screw's play of its axis (the hole 0.15 large on the radius, the M3 at
    its smallest), and MJF puts the hole within 0.3 of its 4.0 from the walls (a length). At the end of that play
    a boss stays clear of the wall; and with the body anywhere its screws let it sit, the four bosses fit between
    the walls at once across the cavity (MJF on its length and width, the bosses where the plate puts them)."""
    pt, sc, bo = S.POS_TOL, S.SCREW, S.BOSS
    r = (bo["d"] + bo["d_tol"]) / 2
    play = MM.SCREW_CLEAR + pt["body_hole"] - sc["d_min"] / 2
    a = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    cav = (B.W + 2 * MM.CLEAR, B.H + 2 * MM.CLEAR, B.CORNER_R + MM.CLEAR)
    corners = B.CORNER_MOUNTS
    wall = float(-rrect_sd(np.array(corners[0][0] - B.W / 2), np.array(corners[0][1] - B.H / 2), *cav))
    room = min(float(-rrect_sd(mx + play * np.cos(a) - B.W / 2, my + play * np.sin(a) - B.H / 2, *cav).max())
               for mx, my in corners)
    xs, ys = sorted({mx for mx, _ in corners}), sorted({my for _, my in corners})
    span = min(cav[0] - mjf(cav[0]) - (xs[-1] - xs[0]), cav[1] - mjf(cav[1]) - (ys[-1] - ys[0])) / 2 - r - pt["plate"]
    return [(f"plate corner bosses (Ø{bo['d']} +{bo['d_tol']}) clear of the cavity walls ({wall:.1f}, MJF "
             f"-{mjf(wall)}) at the end of the body's {play:.2f} screw play", room - mjf(wall) - r),
            ("plate corner bosses fit between the cavity walls at once (MJF on the cavity, plate positions), per "
             "side", span)]


def boss_web():
    """least plate web left between a boss (any of the five, with its root radius) and any pocket, through hole
    or the plate edge."""
    bo = S.BOSS
    r = (bo["d"] + bo["d_tol"]) / 2 + bo["root_r"]
    w, h, cr, _ = S.EC11_POCKET
    webs = []
    for mx, my in B.MOUNTS:
        d = [rrect_sd(mx - x, my - y, *key_hole_max()) for y in B.ROWS for x in B.COLS]
        d += [rrect_sd(mx - x, my - y, w, h, cr) for x, y in (B.ALTHDG, B.FREQ, B.FMS)]
        d += [math.hypot(mx - B.RANGE[0], my - B.RANGE[1]) - S.RANGE_POCKET[0] / 2]
        d += [math.hypot(mx - lx, my - ly) - S.LIGHT_HOLE / 2 for (lx, ly), _g, _c in B.LEDS.values()]
        d += [-rrect_sd(mx - B.W / 2, my - B.H / 2, B.W + 2 * S.OVH, B.H + 2 * S.OVH, B.CORNER_R + S.OVH)]
        webs.append(min(d) - r)
    return min(webs)


def pipe_gaps(back_lo, back_hi):
    """the gap from the board top to the plate back at a light (the light pipes' rows): smallest (the plate back at its
    lowest and bowed PLATE_FLAT down, the board bowed PCB_BOW up) and largest (both the other way); the room left
    over the pipe's base in the smallest (base long and grown in its first week, a sanded stub left on), and its
    shoulder's distance off the plate back in the largest (base short)."""
    pp = S.PIPE
    g_min = back_lo - S.PLATE_FLAT - S.PCB_BOW
    g_max = back_hi + S.PLATE_FLAT + S.PCB_BOW
    return (g_min, g_max, g_min - (pp["base_len"] + pp["len_tol"] + S.RESIN_DRIFT + pp["stub"]),
            g_max - (pp["base_len"] - pp["len_tol"]))


def visible(recess, a, r_hole, off, light=None, caps=(), view=S.CAP_VIEW_DEG, n=161):
    """the share of a light pipe's top (radius a, off the hole's axis by `off` towards the seat, +y on the board)
    that an eye at `view` degrees sees through its hole (radius r_hole) from `recess` below the face: a point of the
    top is seen when the sightline from it leaves the hole at the face and then passes over every key cap in its way
    (the caps at `caps`, the light's hole axis at `light` in board coordinates; the face at its nominal height)."""
    u = np.linspace(-a, a, n)
    x, y = np.meshgrid(u, u)
    top = x * x + y * y <= a * a
    rise = math.tan(math.radians(view))
    seen = top & (x * x + (y + off + recess / rise) ** 2 <= r_hole * r_hole)
    if light is not None:
        c = S.CAP
        cap_top = c["base"] + c["height"]
        face = S.BOSS["h"] + S.PLATE_T + S.ANODISE
        px, py = light[0] + x, light[1] + y + off                    # the top's points on the board
        for dy in np.arange(0.0, 12.0, 0.05):                        # along the sightline towards the seat
            z = face - recess + dy * rise
            for kx, ky in caps:
                inside = -rrect_sd(px - kx, py + dy - ky, c["w"], c["h"], c["r"])   # depth inside the outline
                height = cap_top - np.maximum(0.0, c["cham"] - inside)          # its 45 deg top chamfer
                seen &= ~((inside > 0) & (z < height))
    return seen.sum() / top.sum()


def pipe_rows(back_lo, back_hi, face_lo, board, caps):
    """The light pipes (stack.PIPE) over the reverse-mount LEDs in their board cutouts (board.LED_CUTOUT). Each
    stands on the board, captive under the plate: the rows for how far its top can stand proud, never clamped, the
    top's depth under the face and how much of it shows from the seat, the shoulder, the cutout under the base, the
    LED's lens and light under it, and the base against the switch bodies and the key holes (a firmly pressed cap
    dips under the plate back). Every pipe length at +-len_tol (JLC3DP's resin), a sanded stub left on. The plate
    takes PLATE_FLAT in full here, the board PCB_BOW either way. face_lo: the plate face at its lowest."""
    pp, ll, pt = S.PIPE, S.LED_LENS, S.POS_TOL
    lt_up = S.LIGHT_HOLE_TOL[0]
    t_min, t_max = S.PLATE_T - S.PLATE_T_TOL, S.PLATE_T + S.PLATE_T_TOL
    base_lo, base_hi = (pp["base_d"] - pp["resin"]) / 2, (pp["base_d"] + pp["resin"]) / 2
    cw, ch, cr = B.LED_CUTOUT
    route = S.PCB_CUTOUT_TOL
    g_min, g_max, room, off = pipe_gaps(back_lo, back_hi)
    # the top against the face with the shoulder on the plate back (lifted, the panel upside down): proud of the
    # thinnest bare plate with a long rod, deepest under the thickest plate anodised on both faces with a short rod;
    # in use, resting on the board: nominal (a 4.0 plate anodised on both faces, the bosses and the pipe as drawn),
    # highest (a long pipe on a board bowed up, under the lowest face of a plate bowed down) and deepest (the
    # shoulder `off` the plate back); lifted and highest with the first week's growth (RESIN_DRIFT)
    lifted = pp["top_len"] + pp["len_tol"] + S.RESIN_DRIFT - t_min
    bear_hi = t_max + S.ANODISE - (pp["top_len"] - pp["len_tol"])
    nominal = S.PLATE_T + S.ANODISE - pp["top_len"] + S.BOSS["h"] - pp["base_len"]
    in_use = pp["len"] + pp["len_tol"] + S.RESIN_DRIFT + pp["stub"] + S.PCB_BOW - (face_lo - S.PLATE_FLAT)
    deep = bear_hi + off
    rows = [
        (f"light pipe proud at most {pp['proud']}: lifted onto its shoulder, the top ({pp['top_len']} "
         f"+{pp['len_tol']}, +{S.RESIN_DRIFT} in its first week) stands {lifted:.2f} over the thinnest plate face "
         f"({t_min}); in use, on the board, {in_use:.2f} at most ({nominal:.2f} under the face in the nominal stack)",
         pp["proud"] - max(lifted, in_use)),
        (f"light pipe never clamped: its base ({pp['base_len']} +{pp['len_tol']}, +{S.RESIN_DRIFT} in its first week, "
         f"a {pp['stub']} stub left on) under the smallest gap ({g_min:.3f}: plate back low, bowed {S.PLATE_FLAT} "
         f"down, board {S.PCB_BOW:.2f} up)", room),
        (f"LED lens ({ll['h']} +{ll['tol']} over the substrate, solder {ll['solder']}) inside the thinnest board "
         f"(-{S.STACK_TOL['pcb']}), under the pipe base", S.PCB_T - S.STACK_TOL["pcb"] - ll["h"] - ll["tol"]
         - ll["solder"]),
        (f"light pipe base (Ø{pp['base_d']} -{pp['resin']}) cannot drop into the LED cutout ({cw} x {ch}, routed "
         f"+{2 * route})", 2 * base_lo - (min(cw, ch) + 2 * route)),
    ]
    # the lens (+tol) in the cutout (routed small, R at its corners), the LED placed off by `place`
    hw, hh = (cw - 2 * route) / 2, (ch - 2 * route) / 2
    a = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    lx_, ly_ = (ll["l"] + ll["tol"]) / 2, (ll["w"] + ll["tol"]) / 2
    corners = np.array([(sx * lx_, sy * ly_) for sx in (-1, 1) for sy in (-1, 1)])
    lens = max(float(rrect_sd(corners[:, 0] + ll["place"] * math.cos(t), corners[:, 1] + ll["place"] * math.sin(t),
                              2 * hw, 2 * hh, cr).max()) for t in a)
    rows.append((f"LED lens ({ll['l']} x {ll['w']} +{ll['tol']}, placed {ll['place']} off) clear of its cutout ({cw} x "
                 f"{ch} R{cr}, routed -{route} per side)", -lens))
    lens_depth = S.PCB_T - S.STACK_TOL["pcb"] - ll["h"] - ll["tol"] - ll["solder"]
    d = S.LIGHT_HOLE
    for name, ((lx, ly), _, _) in B.LEDS.items():
        rod = d - pp["clear"]
        float_ = (d + lt_up - (rod - pp["resin"])) / 2              # the pipe off its hole's axis, at most
        on_board = float_ + board + pt["plate"] + pt["pcb"]           # and off the cutout's centre
        reach = base_hi + float_                                      # its base edge from the hole's axis
        sw = S.SWITCH_BODY / 2 + S.CAP_TOL["switch"]
        sw_gap = min(float(rrect_sd(np.array(lx - x), np.array(ly - y), 2 * sw, 2 * sw, 0.0)) for x, y in caps)
        key_gap = min(rrect_sd(lx - x, ly - y, *key_hole_max()) for x, y in caps)
        # off the cutout's centre by on_board across it (its narrow way, routed large), the base's centre may lie
        # over the cutout: it then rests on the cutout's near edge and can tip about it, as far as the rod in its
        # hole lets it (the shortest length in it, the shoulder off the plate back at worst); the base's far rim
        # dips by its distance from that edge times the tilt
        in_hole = pp["top_len"] - pp["len_tol"] - max(0.0, off)
        tilt = 2 * float_ / in_hole
        lever = max(0.0, (min(cw, ch) / 2 + route) - (on_board - base_lo))
        dip = lever * tilt
        r_seat = (d + lt_up) / 2
        a_min = (rod - pp["resin"]) / 2
        # the key caps in front of the light (towards the seat) can shade it too: the UNIT light stands behind the
        # gap between the SHIFT cap and the next column, clear of both
        near_caps = [(x, y) for x, y in caps if 0 < y - ly < 12 and abs(x - lx) < 10]
        seen_lift = visible(bear_hi, a_min, r_seat, r_seat - a_min, (lx, ly), near_caps)   # rod against near side
        seen_nom = visible(nominal, rod / 2, d / 2, 0.0, (lx, ly), near_caps)
        seen_near = visible(nominal, a_min, r_seat, r_seat - a_min, (lx, ly), near_caps)
        seen_deep = visible(deep, a_min, r_seat, r_seat - a_min, (lx, ly), near_caps)
        seen_open = visible(nominal, rod / 2, d / 2, 0.0)                   # the hole alone
        rows += [
            (f"{name} pipe shoulder (Ø{pp['base_d']} -{pp['resin']}) cannot pass its {d} hole (+{lt_up})",
             2 * base_lo - d - lt_up),
            (f"{name} pipe shoulder on the flat plate back: beyond its hole (+{lt_up}) and the hole's back edge break "
             f"({S.LIGHT_HOLE_BACK_BREAK} at most, drawing)", base_lo - r_seat - S.LIGHT_HOLE_BACK_BREAK),
            (f"{name} pipe base (Ø{pp['base_d']} -{pp['resin']}) on the board round the cutout ({cw} x {ch} +"
             f"{2 * route}): {on_board:.2f} off its centre it may tip about the cutout's edge, but the rod "
             f"({in_hole:.2f} in its hole) holds it within {math.degrees(tilt):.1f} deg, so its rim dips {dip:.2f}, "
             f"above the LED lens ({lens_depth:.2f} under the board top)", lens_depth - dip),
            (f"{name} pipe base over the LED: covers the die ({ll['die']}) with the pipe {float_:.2f} off its hole and "
             f"the board {board:.2f} off the plate (plate, PCB, LED placed {ll['place']})",
             base_lo - on_board - ll["place"] - ll["die"] / 2),
            (f"{name} pipe base (reach {reach + board + pt['plate'] + pt['pcb']:.2f} from the board's light axis) "
             f"clear of the switch bodies ({S.SWITCH_BODY} +{S.CAP_TOL['switch']} on its pins)",
             sw_gap - reach - board - pt["plate"] - pt["pcb"]),
            (f"{name} pipe base (reach {reach:.2f}, hole positions +-{pt['plate']}) out from under the key holes "
             f"(+{S.KEY_HOLE_TOL[0]}): a firmly pressed cap dips under the plate back inside its hole's outline",
             key_gap - reach - pt["plate"]),
            (f"{name} light seen from {S.CAP_VIEW_DEG:.0f} deg in use, resting on the board, past its hole and the "
             f"key caps in front: {100 * seen_nom:.0f} % of its top in the nominal stack ({nominal:.2f} deep; "
             f"{100 * seen_open:.0f} % past the hole alone, {100 * seen_near:.0f} % with the rod against the near "
             f"side), {100 * seen_deep:.0f} % at the worst depth ({deep:.2f}, the shoulder {off:.2f} off the plate "
             f"back), {100 * seen_lift:.0f} % lifted onto its shoulder ({bear_hi:.2f}); reported, at least half "
             "nominal (a ratio)", seen_nom - 0.5, ""),
        ]
    return rows


def clearances(plate, outer, inner, range_knob, knobs):
    """clearances that must stay positive, with the inner knob pushed down; each one can fail. Measured where a
    row says so: on the plate and knob solids, the body STL and the cap zips. knobs: the mesh of every knob
    make_knobs.py writes, {(FLUTES name, fit variant): mesh}."""
    ok, ik, rk = S.OUTER_KNOB, S.INNER_KNOB, S.RANGE_KNOB
    p, es = S.PUSH_TRAVEL, S.ENC_SPREAD
    resin = S.RESIN_TOL["depth"]                        # resin knob, key to counterbore and bore depths (+-)
    # ---- knob walls and radial clearances, worst case (stack.RESIN_TOL, SHAFT_TOL, SHAFT_ECC): a knob's bore on
    # its shaft at the loose variant, a hole printed large and the shaft at its low limit can sit off centre by
    # bore_play; the inner shaft off the outer one by ecc. FIT takes out the printer's own bias (a reprint at the
    # variant that fit, stack.FIT), so the bores print within the resin's tolerance about the variants' offsets ----
    part_tol, hole_tol, shaft_tol, ecc = S.RESIN_TOL["size"], S.RESIN_TOL["hole"], S.SHAFT_TOL, S.SHAFT_ECC
    loose = max(0.0, *S.FIT_VARIANTS.values())
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
    # ---- plate: back on the bosses (PLATE_Z0 +-BOSS["h_tol"] over the PCB top), thickness +-0.1; depths from the
    # back. Anodising (stack.ANODISE): the back face sits up to ANODISE / 2 lower over bare boss ends, the front face
    # up to ANODISE higher over anodised ones ----
    h_tol = S.BOSS["h_tol"]
    t_min = S.PLATE_T - S.PLATE_T_TOL
    back_metal_lo = S.PLATE_Z0 - h_tol                  # the back the pocket depths count from, lowest
    back_lo, back_hi = back_metal_lo - S.ANODISE / 2, S.PLATE_Z0 + h_tol   # the back face itself
    face_lo = back_metal_lo + t_min                     # unanodised (anodising only raises it)
    face_up = h_tol + S.PLATE_T_TOL + S.ANODISE         # plate face over its nominal height, worst
    # ---- positions: board offset from the caps; the plate's bosses locate the screws, the board floats on them ----
    pt, sc, bo, tp = S.POS_TOL, S.SCREW, S.BOSS, S.TAP
    cap_err = math.sqrt(sum(v * v for v in S.CAP_TOL.values()))
    r_max = S.KEY_HOLE_R_MAX                            # the key holes' corners at their largest (drawing)
    cap_room = cap_shift_room(r=r_max)[0]               # key hole +0.1/-0 after anodising: least at nominal
    cap_room_turn = cap_shift_room(turn=S.CAP_TURN, r=r_max)[0]   # the same cap turned on its plunger
    cap_room_creep = cap_shift_room(turn=S.CAP_CREEP, r=r_max)[0]   # crept round in use
    # a whole set printed large (WJP's outline error as a bias), squared: against the other per-key errors
    cap_room_set = cap_shift_room(-S.WJP_TOL["size"], S.CAP_TURN, r_max)[0]
    cap_err_set = math.sqrt(sum(v * v for k, v in S.CAP_TOL.items() if k != "cap"))
    cap_room_max = cap_shift_room(S.KEY_HOLE_TOL[0])[1]   # most in the largest hole
    board = cap_room_max + pt["centring"]              # board offset the caps allow (the most, diagonally)
    hole = B.MOUNT_HOLE
    hole_lo, hole_hi = (hole - pt["npth_d"]) / 2, (hole + pt["npth_d"]) / 2
    # the caps put the board where they centre it, the bosses the screws where the plate has them: the PCB hole
    # must pass the screw there (key pattern to boss pattern on the plate, the board's holes, centring, thread)
    need = pt["plate"] + pt["pcb"] + pt["centring"] + pt["thread"]
    off = hole_hi - sc["d_min"] / 2 + pt["thread"]     # the board off a screw's axis, at most (its hole's play)
    boss_lo, boss_hi = (bo["d"] - bo["d_tol"]) / 2, (bo["d"] + bo["d_tol"]) / 2
    keepout = B.MOUNT_KEEPOUT                         # pcb/check.py checks the copper against the same radius
    # ---- screws: flange on the counterbore seat, body boss, PCB, plate boss thread ----
    seat_tol, pcb_tol = S.STACK_TOL["counterbore"], S.STACK_TOL["pcb"]
    seat_pcb = -S.SEAT_Z                                # counterbore seat to the PCB top (boss 1.6 + PCB 1.6)
    tip_lo = (sc["L"] - sc["L_tol"]) - (seat_pcb + seat_tol + pcb_tol)   # into the plate boss, from its end face
    tip_hi = (sc["L"] + sc["L_tol"]) - (seat_pcb - seat_tol - pcb_tol)
    engaged = tip_lo - sc["tip"] - tp["cham"]
    # flange and head recessed: the bottom plane rises to the front, so take its highest point under the
    # counterbore (the flange stays inside it) at the front mounts, with MJF +0.3
    cb_hi = MM.HEAD_R + pt["body_hole"]
    boss_floor = max(MM.z_bottom(min(my + cb_hi, B.H + MM.o)) for _, my in B.MOUNTS) + seat_tol
    head_lo = (S.SEAT_Z - seat_tol) - sc["head_k"]
    # ---- flange on the body, no washer: the shank against the widest hole wall, or the flange against the
    # counterbore wall, whichever comes first ----
    r_hole_max = MM.SCREW_CLEAR + pt["body_hole"]
    offset = MM.SCREW_OFFSET                            # screw against the widest body hole wall
    fl_lo, fl_hi = sc["flange_d_min"] / 2, sc["flange_d"] / 2
    co_stop = MM.HEAD_R - pt["body_hole"] - fl_hi       # the largest flange meets the smallest counterbore's wall
    fl_off = min(offset, cb_hi - fl_lo)                 # the screw off the body hole's axis, at most
    corner = min(-rrect_sd(mx - B.W / 2, my - B.H / 2, B.W + 2 * MM.o, B.H + 2 * MM.o, B.CORNER_R + MM.o)
                 for mx, my in B.CORNER_MOUNTS) - cb_hi   # counterbore to the outer body surface
    cav_w_tol = mjf(B.H + 2 * MM.CLEAR)                             # MJF on the cavity width (61 mm)
    # width: the routed long edge, or the V-cut one after its rail comes off
    w_tol = max(S.PCB_OUTLINE_TOL, S.PCB_VCUT_TOL)
    cav = MM.CLEAR - w_tol / 2 - cav_w_tol / 2                       # per side
    cav_len = (B.W + 2 * MM.CLEAR) * (1 - S.MJF_SCALE)        # the cavity length, printed small
    # length: routed short edges (no rails there), or V-cut ones sanded (rails added anyway)
    pcb_len = max(B.W + S.PCB_OUTLINE_TOL, S.PCB_SANDED_LEN)
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
    # of its per-key allowance has, so it may rub that edge on one side (documented,
    # docs/architecture/mechanics.md). Two rows prove it cannot catch or stick: tilted, it cannot touch both sides
    # of its hole at once (its shadow over the whole wall fits in the hole, turned and printed large), and while its
    # side is free its bottom edge stands out of the line of its side only by the dip times the slope, which the
    # broken back edge (KEY_BACK_BREAK) leads back in; while its side bears on the face edge, its bottom edge is
    # pulled inside the hole outline.
    flex, slope = S.PRESS_DIP, S.PRESS_SLOPE
    cap_dip = max(0.0, back_hi + S.PLATE_FLAT * bow_key + flex
                  - (S.CAP["base"] - S.KEY_TRAVEL - S.PLUNGER_TOP_TOL))
    face_shift = (S.PLATE_Z1 + face_up + S.PLATE_FLAT * bow_key + S.PCB_T / 2 + flex) * slope
    wall_h = S.PLATE_T + S.PLATE_T_TOL + S.ANODISE                  # thick plate, both faces anodised
    cap_print = S.WJP_TOL["size"]                                     # cap outline, on the size
    cap_room_wedge = cap_shift_room(-cap_print, S.CAP_TURN, r_max)[0]   # cap printed large, turned, smallest hole
    shadow = wall_h * math.tan(slope) + S.CAP["w"] * (1 / math.cos(slope) - 1)
    # face down, the shaft tips over the lowest face, bowed towards them
    protrude = (max(S.INNER_TOP + S.ENC_TOL["ge10"], S.LEVER_Z1 + S.LEVER_TOL)
                - face_lo + S.PLATE_FLAT * max(bow_enc, bow_rng))
    edge = min([min(y - S.CAP["h"] / 2, B.H - y - S.CAP["h"] / 2) for _, y in caps] +
               [min(y - S.SLEEVE_D / 2, B.H - y - S.SLEEVE_D / 2) for y in (B.ALTHDG[1], B.RANGE[1])]) + S.OVH
    body_tri = body_triangles()
    (void, void_at), (wall, wall_at), (wall2, wall2_at) = body_thin(body_tri)
    bm = body_measures(body_tri)
    pm = plate_measures(mesh_triangles(plate))
    kh = pm["keys"]
    kr, orr, r_out = np.array(pm["key_r"]), np.array(pm["out_r"]), B.CORNER_R + S.OVH
    pipe = K.light_pipe()
    pair_m = pair_measures(mesh_triangles(K.light_pipe_pair()))
    knob_m, pipe_m = turned_measures(range_knob, pipe)
    (bx0, by0, bx1, by1), (mid_x, mid_y) = bm["bar"], B.MID_MOUNT
    an = S.ANODISE
    pads = B.build()                                    # every pad of the board, for what hangs under it
    pp, d = S.PIPE, S.LIGHT_HOLE
    lt_up, lt_dn = S.LIGHT_HOLE_TOL
    pd = S.POCKET_TOL
    # MJF wall height, PCB, lowest back face, bowed towards the walls
    wall_gap = back_lo - bm["wall_top"][1] - seat_tol - pcb_tol - S.PLATE_FLAT * bow_wall
    # ---- knob bores: the variants (stack.FIT_VARIANTS) against the resin's tolerance on holes: for a bore printed
    # anywhere within it about FIT, how far the nearest variant ends up from the size drawn
    fits = [0.0, *S.FIT_VARIANTS.values()]
    fit_off = max(min(abs(v + e) for v in fits) for e in np.linspace(-hole_tol, hole_tol, 601))
    legend_off, legend_at = legend_gap()
    # ---- RANGE: knob height from the lever top (+-0.3) and its bore depth (resin). A kept RANGE knob has at most
    # stack.RANGE_PLAY on the lever: off the lever's axis by half of it, and pushed sideways at full tilt it cocks on
    # its D bore (its length on the lever's flat, measured on the solid) by that play over the length, the way the
    # lever tilts, about the bore's middle. The lever's centre push (stack.RANGE_PUSH) may go down at full tilt
    # too (Alps does not say it cannot) ----
    rk_lo = S.PLATE_Z1 + rk["z0"] - S.LEVER_TOL - resin    # knob bottom, lowest
    push_hi = S.RANGE_PUSH[0] + S.RANGE_PUSH[1]
    a = math.radians(S.RKJXT_TILT)
    pz = S.RKJXT_FULCRUM
    poff = S.RKJXT_FULCRUM_OFF
    rk_len = d_bore_len(range_knob, S.LEVER_D, S.LEVER_FLAT)
    cock, rk_off = S.RANGE_PLAY / rk_len, S.RANGE_PLAY / 2
    rk_mid = (S.LEVER_Z1 - S.LEVER_TOL - rk_len / 2, S.LEVER_Z1 + S.LEVER_TOL - rk_len / 2)   # the bore's middle

    def turned(r, h, cr, cz, ang):
        """the point (r, h) turned by ang about (cr, cz), its top towards +r"""
        return (cr + (r - cr) * math.cos(ang) + (h - cz) * math.sin(ang),
                cz + (h - cz) * math.cos(ang) - (r - cr) * math.sin(ang))

    def tilted(r, h, side, cocked=0.0, push=0.0, mid=0.0):
        """where a point of the knob or the hub, r off the lever's axis towards the tilt and h over the PCB, is at
        full tilt: (sideways from the axis, height); the knob cocked on the lever by `cocked` (rad) about the bore's
        middle at height `mid`, and the lever pushed in by `push`. side: the fulcrum on the side the lever tilts to
        (1) or on the other (-1); Alps' drawing shows the second, its specification is not public
        (stack.RKJXT_FULCRUM_OFF), so every row takes the worse of the two."""
        r, h = turned(r, h, 0.0, mid, cocked)
        return turned(r, h - push, side * poff, pz, a)

    # the underside on the side the knob dips to: the hub's corner and the rim's bottom edge (the dish between them
    # is a straight line), on the lowest knob, the skirt printed large and the dish shallow, cocked and pushed
    under = ((rk["hub_d"] / 2, rk_lo), ((rk["skirt_d"] + part_tol) / 2, rk_lo + rk["dish"] - resin))
    skirt_lows = {side: min(tilted(r, h, side, cock, push_hi, rk_mid[0])[1] for r, h in under) for side in (1, -1)}
    skirt_low = min(skirt_lows.values())
    # the skirt rim on the side the knob tilts away from, seen from above: its bottom edge is the outline; worst
    # with the highest knob (lever +, bore deep) and the smallest skirt print, cocked and pushed or not
    rk_hi = S.PLATE_Z1 + rk["z0"] + rk["dish"] + S.LEVER_TOL + resin    # the rim's bottom edge, highest
    rim_r = (rk["skirt_d"] - part_tol) / 2
    skirt_cover = min(-tilted(-rim_r, rk_hi, side, c, p, rk_mid[1])[0]
                      for side in (1, -1) for c in (0.0, cock) for p in (0.0, push_hi))
    # a diagonal: Alps gives 9 deg for the four directions only. Should the lever reach 9 deg on both axes at once
    # (12.6 deg), the nominal knob over the nominal plate, the fulcrum along the diagonal as far off the axis as on
    # the axes, or by half or twice that, pushed or not
    a_diag = math.atan(math.hypot(math.tan(a), math.tan(a)))
    rk_nom = S.PLATE_Z1 + rk["z0"]
    diag = {p: min(turned(r, h - p, side * poff * k, pz, a_diag)[1] - S.PLATE_Z1
                   for r, h in ((rk["hub_d"] / 2, rk_nom), (rk["skirt_d"] / 2, rk_nom + rk["dish"]))
                   for side in (1, -1) for k in (0.5 ** 0.5, 1.0, 2 ** 0.5))
            for p in (0.0, S.RANGE_PUSH[0])}
    on_board = board + pt["plate"] + pt["pcb"] + S.ENC_ON_PINS   # an encoder's axis off its plate hole
    on_board_r = board + pt["plate"] + pt["pcb"] + S.RKJXT_ON_PINS   # the RKJXT's: it floats more on its pins
    # RKJXT hub (Alps' STEP) tilted 9 deg about the fulcrum: its full-width top edge sideways at the plate
    hub_r, hub_z = S.RKJXT_HUB[0] / 2, S.RKJXT_HUB[1]
    hub_out = max(tilted(hub_r, hub_z, side)[0] for side in (1, -1))
    arrow_in = S.RANGE_ART["arrow_r"] + min(u for u, _v in S.RANGE_ART["arrow"])   # pan arrows' inner ends
    gen = S.PLATE_GEN_TOL                               # ISO 2768-m on untoleranced plate sizes
    # RKJXT body corner (top edge at its widest) off the RANGE pocket's wall and floor, worst of each, and off
    # the floor corner radius the drawing allows (S.POCKET_FLOOR_R); anodising narrows the pocket, and its floor
    # keeps its height (see the plate above). The same for the encoder's side lugs in their pocket (measured on
    # the plate solid).
    fr = S.POCKET_FLOOR_R

    def floor_corner(side, top):
        return fr - math.hypot(fr - side, fr - top) if max(side, top) < fr else min(side, top)
    rk_side = (pm["rp_d"] - gen - an - S.RKJXT_ACROSS - S.RKJXT_TOL) / 2 - on_board_r
    # the pockets as built (plate_measures), their floors anodised over bare boss ends (an / 2 lower, which the
    # drawing allows); the board bowed towards the plate there too, by PCB_BOW in the same shape
    rk_top = (back_metal_lo + pm["rp_depth"] - S.POCKET_TOL - an / 2 - (S.RKJXT_BODY + S.RKJXT_TOL)
              - (S.PLATE_FLAT + S.PCB_BOW) * bow_rng)
    ec_w = pm["ec_w"][0]
    ec_side = (ec_w - gen - an - S.EC11_LUGS - S.ENC_TOL["ge10"]) / 2 - on_board
    ec_top = (back_metal_lo + pm["ec_depth"][0] - S.POCKET_TOL - an / 2 - (S.EC11_BODY + S.ENC_TOL["lt10"])
              - (S.PLATE_FLAT + S.PCB_BOW) * bow_enc)
    # ---- outer knob, in its own frame from the slot floor its key rests on ----
    slot_tol = S.ENC_TOL["lt10"]                        # slot width and depth, +-
    key_rss = math.hypot(es["slot"], resin)            # slot floor over the PCB and the key's height in the knob
    cb_top = K.outer_counterbore_top() - K.outer_key_z0() + resin   # counterbore top, highest
    shaft_top = S.SLOT_LEN - slot_tol                   # 6 mm shaft top over the slot floor, shallow slot
    knob_top = ok["z1"] - ok["z0"] - K.outer_key_z0()                # top of the knob's bore
    key_resin = S.RESIN_TOL["size"]                       # key printed up to this much wide
    # the ring's lash about the shaft with the key's sides against the slot's walls, where they meet the shaft's
    # surface (the furthest out both reach), in all
    detent = 360 / S.ENC_DETENTS
    lash_nom = math.degrees((S.SLOT_W - S.KEY_W) / (S.OUTER_D / 2))
    lash_max = math.degrees((S.SLOT_W + slot_tol - S.KEY_W + key_resin) / ((S.OUTER_D - shaft_tol) / 2))
    # ---- RANGE skirt rim measured on the knob solid, at its edge (its thinnest: the top slopes up from there) ----
    rim = knob_m["rim"]
    d_len = d_bore_len(inner, S.INNER_D, S.INNER_FLAT)   # inner knob D bore, measured on the solid
    rows = [
        (f"outer knob over plate (face +{face_up:.3f}, bowed {S.PLATE_FLAT * bow_enc:.3f} up there, slot floor "
         f"+-{es['slot']:.2f} and key resin, RSS)", ok["z0"] - face_up - S.PLATE_FLAT * bow_enc - key_rss),
        (f"outer knob grip on the 6 mm shaft above the counterbore (slot depth -{slot_tol}, resin), beyond "
         f"{S.OUTER_GRIP_MIN}", min(knob_top, shaft_top) - cb_top - S.OUTER_GRIP_MIN),
        (f"outer knob key ({S.KEY_W} +{key_resin} resin) in the narrowest shaft slot ({S.SLOT_W} -{slot_tol})",
         S.SLOT_W - slot_tol - (S.KEY_W + key_resin)),
        (f"outer ring lash, should its bore not grip: the key ({S.KEY_W}) in the slot ({S.SLOT_W}) turns "
         f"{lash_nom:.1f} deg in all at the shaft's surface, {lash_max:.1f} at worst (key -{key_resin}, slot "
         f"+{slot_tol}, shaft -{shaft_tol}), against {detent:.0f} deg a detent: within one, nominal (a kept ring must "
         "not turn without its shaft)", detent - lash_nom, "°"),
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
         solid_radius(outer) - solid_radius(inner) - 2.0),
        (f"inner knob D bore ({d_len:.2f} up from the tip, measured on the knob solid) within the shortest D flat "
         f"({S.FLAT_LEN} -{S.ENC_TOL['lt10']}), bore depth +{resin}: the bore end sets the knob height",
         S.FLAT_LEN - S.ENC_TOL["lt10"] - d_len - resin),
        (f"knob bore variants ({', '.join(f'{v:+.1f}' for v in sorted(fits))}) over the resin's +-{hole_tol} on "
         f"holes: one of them prints within {fit_off:.2f} of the size drawn, within {S.FIT_OFF} (stack.FIT_OFF, an "
         "assumption about the printed bores, not a measurement)",
         S.FIT_OFF - fit_off),
        (f"knob FIT {S.FIT:+.1f} (the variants about it; a reprint takes the one that fit) within the resin's "
         f"+-{hole_tol} on holes", hole_tol - abs(S.FIT)),
        (f"encoder bushing ({S.SLEEVE_D} +{S.ENC_TOL['lt10']}) in its {S.SHAFT_HOLE} plate hole (-{gen}, anodised "
         f"-{an}), radial: board {board:.2f} off, plate, PCB, pins",
         (S.SHAFT_HOLE - gen - an - S.SLEEVE_D - S.ENC_TOL["lt10"]) / 2 - on_board),
        (f"outer knob (flute bottoms at its tapered top, OD -{part_tol}) covers its {S.SHAFT_HOLE} plate hole "
         f"(+{gen}) seen from above: knob on the bushing {on_board:.2f} off, loose knob {bore_play:.2f} off",
         min(flute_bottom(S.FLUTES[n], ring_r, ok["z1"] - ok["z0"], ok["z1"] - ok["z0"]) for n in rings)
         - part_tol / 2 - (S.SHAFT_HOLE + gen) / 2 - on_board - bore_play),
        (f"encoder side lugs ({S.EC11_LUGS} +{S.ENC_TOL['ge10']}) in the {ec_w:.1f} wide pocket (measured, -{gen}, "
         f"anodised -{an}), per side: board {board:.2f} off, plate, PCB, pins", ec_side),
        (f"encoder lug corner clear of the pocket's floor corner (R{fr} max on the drawing): {ec_side:.2f} off the "
         f"wall, {ec_top:.2f} off the floor", floor_corner(ec_side, ec_top)),
        (f"RKJXT body ({S.RKJXT_ACROSS} across corners +{S.RKJXT_TOL}) in its {S.RANGE_POCKET[0]} pocket (-{gen}, "
         f"anodised -{an}), radial: board, plate, PCB, part on its pins ({S.RKJXT_ON_PINS})", rk_side),
        (f"RKJXT hub (Ø{S.RKJXT_HUB[0]}) at full tilt in its {S.RANGE_HOLE} plate hole (-{gen}, anodised -{an}), "
         f"radial, same offsets; the fulcrum {poff} off the axis on either side, the worse",
         (S.RANGE_HOLE - gen - an) / 2 - hub_out - on_board_r),
        (f"RANGE knob over hub, pushed {push_hi:.1f} (lever -{S.LEVER_TOL}, bore +{resin})",
         rk_lo - push_hi - S.RKJXT_HUB_TOP),
        (f"RANGE knob's underside (the hub's corner and the dished skirt's rim, skirt +{part_tol}, dish -{resin}) "
         f"over the plate at {S.RKJXT_TILT:.0f} deg, cocked {math.degrees(cock):.1f} deg on the lever "
         f"({S.RANGE_PLAY} play over its {rk_len:.2f} D bore) and pushed {push_hi:.1f}, low knob, high plate (face "
         f"+{face_up:.2f}, bowed {S.PLATE_FLAT * bow_rng:.3f} up): the fulcrum ({pz} up, {poff} off the axis) on the "
         f"side it tilts away from, the worse; on the other side {skirt_lows[1] - skirt_lows[-1]:.2f} more",
         skirt_low - S.PLATE_Z1 - face_up - S.PLATE_FLAT * bow_rng),
        (f"RANGE skirt (Ø{rk['skirt_d']} -{part_tol}, high knob) still covers its {S.RANGE_HOLE} mm plate hole "
         f"(+{gen}) at full tilt, cocked and pushed or not, the fulcrum on either side, the worse: lever "
         f"{on_board_r:.2f} off (board, plate, PCB, pins), the knob {rk_off:.3f} off it ({S.RANGE_PLAY} play)",
         skirt_cover - (S.RANGE_HOLE + gen) / 2 - on_board_r - rk_off),
        (f"RANGE pan arrows (from r {arrow_in:.2f}) outside the skirt seen square on (Ø{rk['skirt_d']} +{part_tol}), "
         f"lever {on_board_r:.2f} off, the knob {rk_off:.3f} off it",
         arrow_in - (rk["skirt_d"] + part_tol) / 2 - on_board_r - rk_off),
        (f"RANGE knob's underside over the plate on a diagonal, should the lever reach {S.RKJXT_TILT:.0f} deg on "
         f"both axes ({math.degrees(a_diag):.1f} deg), nominal (Alps gives no diagonal limit): {diag[0.0]:.2f}, "
         f"pushed {S.RANGE_PUSH[0]} {diag[S.RANGE_PUSH[0]]:.2f}",
         diag[S.RANGE_PUSH[0]]),
        (f"RANGE knob as built: skirt Ø{knob_m['skirt_d']:.2f}, dished {knob_m['dish']:.2f} (measured on the knob "
         f"solid) are the stack's (Ø{rk['skirt_d']}, {rk['dish']})",
         0.01 - max(abs(knob_m["skirt_d"] - rk["skirt_d"]), abs(knob_m["dish"] - rk["dish"]))),
        (f"RANGE skirt rim ({rim:.2f} at its edge, on the knob solid, resin -{resin}), beyond 1.0", rim - resin - 1.0),
        (f"plate pockets as built: encoders {pm['ec_w'][0]:.2f} x {pm['ec_h'][0]:.2f}, {pm['ec_depth'][0]:.2f} deep, "
         f"RANGE Ø{pm['rp_d']:.2f}, {pm['rp_depth']:.2f} deep, the worst {pm['pocket_off']:.3f} off its part's axis "
         "(measured on the plate) are the stack's",
         0.01 - max(*(abs(v - n) for k, n in (("ec_w", S.EC11_POCKET[0]), ("ec_h", S.EC11_POCKET[1]),
                                              ("ec_depth", S.EC11_POCKET[3])) for v in pm[k]),
                    abs(pm["rp_depth"] - S.RANGE_POCKET[1]), abs(pm["rp_d"] - S.RANGE_POCKET[0]), pm["pocket_off"])),
        (f"key holes as built: {kh['w'][0]:.2f} to {kh['w'][1]:.2f} x {kh['h'][0]:.2f} to {kh['h'][1]:.2f}, the "
         f"worst {kh['off']:.3f} off its key (all {len(caps)}, measured on the plate) are the stack's "
         f"({S.KEY_HOLE[0]} x {S.KEY_HOLE[1]})",
         0.01 - max(*(abs(v - S.KEY_HOLE[0]) for v in kh["w"]), *(abs(v - S.KEY_HOLE[1]) for v in kh["h"]),
                    kh["off"])),
        (f"encoder holes Ø{pm['shaft'][0]:.2f} to Ø{pm['shaft'][1]:.2f}, RANGE hole Ø{pm['range_d']:.2f}, the worst "
         f"{pm['hole_off']:.3f} off its part's axis (measured on the plate) are the stack's (Ø{S.SHAFT_HOLE}, "
         f"Ø{S.RANGE_HOLE})",
         0.01 - max(*(abs(v - S.SHAFT_HOLE) for v in pm["shaft"]), abs(pm["range_d"] - S.RANGE_HOLE), pm["hole_off"])),
        (f"plate through holes where the DXF's CUT layer has them (all {pm['cut_n']}; the plate has {pm['through']}, "
         f"measured on the plate): the worst {pm['cut'][0]:.3f} off and {pm['cut'][1]:.3f} off in size, the plate's "
         f"extent {pm['extent']:.3f} off the DXF's outline",
         0.01 - max(*pm["cut"], pm["extent"]) if pm["cut_n"] == pm["through"] else -1.0),
        (f"plate corners as built (all {kr.shape[1] // 4} key holes, {kr.shape[1]} corners), in the DXF's CUT "
         f"layer: key holes R{np.min(kr[0]):.3f} to R{np.max(kr[0]):.3f}, outline R{np.min(orr[0]):.3f} to "
         f"R{np.max(orr[0]):.3f}; on the plate: key holes R{np.min(kr[1]):.3f} to R{np.max(kr[1]):.3f}, outline "
         f"R{np.min(orr[1]):.3f} to R{np.max(orr[1]):.3f} (measured) are the stack's (R{S.KEY_HOLE[2]}, R{r_out:g})",
         0.01 - np.abs(np.r_[kr.ravel() - S.KEY_HOLE[2], orr.ravel() - r_out]).max()),
        (f"encoder pocket (-{pd}, its floor anodised over bare boss ends) over encoder body ({S.EC11_BODY} "
         f"+{S.ENC_TOL['lt10']}), low plate, bowed {S.PLATE_FLAT * bow_enc:.3f} down, board "
         f"{S.PCB_BOW * bow_enc:.3f} up", ec_top),
        (f"plate left over the encoder pockets, thin plate, beyond {S.CNC_WALL} (JLCCNC recommended; "
         f"{S.CNC_WALL_MIN} is its minimum)", t_min - S.EC11_POCKET[3] - S.CNC_WALL),
        (f"RANGE pocket (-{pd}, its floor anodised over bare boss ends) over RKJXT body ({S.RKJXT_BODY} "
         f"+{S.RKJXT_TOL}), low plate, bowed {S.PLATE_FLAT * bow_rng:.3f} down, board {S.PCB_BOW * bow_rng:.3f} up",
         rk_top),
        (f"RKJXT body corner clear of the RANGE pocket's floor corner (R{fr} max on the drawing): {rk_side:.2f} off "
         f"the wall, {rk_top:.2f} off the floor", floor_corner(rk_side, rk_top)),
        (f"plate left over the RANGE pocket, thin plate, beyond {S.CNC_WALL} (JLCCNC recommended; {S.CNC_WALL_MIN} "
         "is its minimum)", t_min - S.RANGE_POCKET[1] - S.CNC_WALL),
        (f"amber legends {legend_off:.2f} from the nearest hole edge ({legend_at}, at their largest), beyond the "
         f"front edge break ({S.FRONT_BREAK} at most): what is left is for the UV print's register, which JLCCNC "
         "does not state", legend_off - S.FRONT_BREAK),
        *cap_rows(face_lo, S.PLATE_FLAT * bow_key),
        *cap_build_rows(),
        *cap_bar_rows(),
        *knob_rows(knobs),
        (f"cap pressed firmly ({S.PRESS_FIRM:.0f} N) comes back into its key hole: {cap_dip:.2f} under the plate back "
         f"(travel {S.KEY_TRAVEL}, plunger -{S.PLUNGER_TOP_TOL}, high plate bowed up, board {flex:.2f} down), tilted "
         f"{math.degrees(slope):.2f} deg with the bent board, lands on the {S.KEY_BACK_BREAK} edge break",
         S.KEY_BACK_BREAK - cap_dip * slope),
        (f"cap pressed firmly, tilted {math.degrees(slope):.2f} deg (up to {face_shift:.2f} sideways at the face, so "
         f"it may rub one side): it cannot wedge across its hole, turned {S.CAP_TURN:.0f} deg and printed "
         f"+{cap_print}, its shadow over the {wall_h:.2f} wall ({shadow:.3f}) within twice its shift room "
         f"({cap_room_wedge:.2f})", 2 * cap_room_wedge - shadow),
        (f"cap shift room in its key hole ({cap_room:.2f}, corners R{r_max} at most) over per-key RSS {cap_err:.2f}",
         cap_room - cap_err),
        (f"cap turned {S.CAP_TURN:.0f} deg on its plunger (squared on a rule): shift room ({cap_room_turn:.2f}) over "
         f"per-key RSS {cap_err:.2f}", cap_room_turn - cap_err),
        (f"cap crept round to {S.CAP_CREEP} deg on its plunger in use (stack.CAP_CREEP): shift room "
         f"({cap_room_creep:.2f}) over per-key RSS {cap_err:.2f}", cap_room_creep - cap_err),
        (f"a whole cap set printed +{cap_print} on its outline (WJP, a per-set bias, taken linearly), turned "
         f"{S.CAP_TURN:.0f} deg: shift room ({cap_room_set:.2f}) over the RSS of the other per-key errors "
         f"({cap_err_set:.2f})", cap_room_set - cap_err_set),
        (f"M3 passes the narrowest PCB hole ({hole} -{pt['npth_d']}) where the caps centre the board (plate, PCB, "
         f"centring, thread: {need:.3f})", hole_lo - S.SCREW_D / 2 - need),
        (f"plate boss end (Ø{bo['d']} -{bo['d_tol']}) covers the widest PCB hole all round, the board {off:.2f} off "
         "the screw", boss_lo - off - hole_hi),
        (f"plate boss (Ø{bo['d']} +{bo['d_tol']}, the board {off:.2f} off) inside the {keepout} mm copper keep-out",
         keepout - boss_hi - off),
        *boss_wall_rows(),
        (f"plate boss (any of the {len(B.MOUNTS)}, root R{bo['root_r']}) to the nearest pocket, hole or plate edge, "
         "beyond 1.0", boss_web() - 1.0),
        (f"plate bosses {pm['boss_h'][0]:.3f} to {pm['boss_h'][1]:.3f} high, Ø{pm['boss_d'][0]:.2f} to "
         f"Ø{pm['boss_d'][1]:.2f}, the worst {pm['boss_off']:.3f} off its place (all {len(B.MOUNTS)}, measured on the "
         f"plate) are the stack's ({bo['h']}, Ø{bo['d']})",
         0.01 - max(*(abs(v - bo["h"]) for v in pm["boss_h"]), pm["boss_off"],
                    *(abs(v - bo["d"]) for v in pm["boss_d"]))),
        ("body boss tops bear on the PCB all round its holes (all five; MJF -0.15)",
         MM.BOSS_R - pt["body_hole"] - offset - off - hole_hi),
        (f"PCB width in the cavity (MJF -{cav_w_tol:.1f}; routed long edge +{S.PCB_OUTLINE_TOL}, or the V-cut rail "
         f"edge +{S.PCB_VCUT_TOL}), per side", cav),
        (f"PCB length in the cavity ({cav_len:.2f} at MJF -{100 * S.MJF_SCALE:g} %): routed short edges "
         f"(+{S.PCB_OUTLINE_TOL}), or V-cut ones sanded until the board drops in ({S.PCB_SANDED_LEN} at most), "
         "per side",
         (cav_len - pcb_len) / 2),
        (f"through-hole leads (untrimmed, up to {S.LEAD_MAX} under the PCB) over the body floor ({MM.UNDER} room, MJF "
         f"-{mjf(MM.UNDER)})", MM.UNDER - mjf(MM.UNDER) - S.LEAD_MAX),
        *room_rows(pads, board + pt["plate"], bm["bar"]),
        (f"middle column as built: bar {bx1 - bx0:.2f} x {by1 - by0:.2f} on the middle mount (measured on the body) "
         f"is the stack's ({S.MID_BAR['w']} x {2 * MM.BOSS_R_LOW:g})",
         0.01 - max(abs(bx1 - bx0 - S.MID_BAR["w"]), abs(by1 - by0 - 2 * MM.BOSS_R_LOW),
                    abs((bx0 + bx1) / 2 - mid_x), abs((by0 + by1) / 2 - mid_y))),
        (f"middle column: bar wall beyond the counterbore ({bm['bar_wall']:.2f} by {bx1 - bx0:.2f} across, measured "
         f"on the body, MJF +-{seat_tol} on the diameter and the width), beyond 1.5 (JLC3DP fastener features)",
         min(bm["bar_wall"], bx1 - bx0) - seat_tol - 1.5),
        (f"body as built: wall tops at {bm['wall_top'][0]:.2f} to {bm['wall_top'][1]:.2f}, post top at "
         f"{max(bm['post_top']):.2f}, counterbore seats at {bm['seat_z'][0]:.2f} to {bm['seat_z'][1]:.2f} (all five; "
         f"measured on the body) are the stack's ({S.PLATE_Z0 - S.WALL_GAP:.2f}, {MM.SUPPORT_TOP:.2f}, {S.SEAT_Z})",
         0.01 - max(*(abs(v - (S.PLATE_Z0 - S.WALL_GAP)) for v in bm["wall_top"]),
                    *(abs(v - MM.SUPPORT_TOP) for v in bm["post_top"]), *(abs(v - S.SEAT_Z) for v in bm["seat_z"]))),
        (f"body slot as built: {bm['slot'][0]:.2f} to {bm['slot'][1]:.2f} wide, {bm['slot'][3]:.3f} off the socket's "
         f"axis and {'open' if bm['slot'][2] else 'CLOSED'} at the wall top (measured on the body) is the plug "
         f"opening's ({MM.USB_OPEN['w']})",
         (0.01 - max(*(abs(v - MM.USB_OPEN["w"]) for v in bm["slot"][:2]), bm["slot"][3])) if bm["slot"][2] else -1.0),
        *usb_rows(),
        *tongue_rows(back_lo, back_hi, S.PLATE_FLAT * plate_bow(B.USB_X, -S.OVH), board + pt["plate"] + pt["pcb"],
                     bm["slot"], pm["tongue"]),
        (f"body screw holes ({2 * MM.SCREW_CLEAR:.1f} -{2 * pt['body_hole']}) round the M3 where the bosses put it: "
         f"the corner ones, the furthest from the middle of the pattern (body {pt['body']}, plate {pt['plate']})",
         MM.SCREW_CLEAR - pt["body_hole"] - S.SCREW_D / 2 - pt["body"] - pt["plate"]),
        (f"flange (dc {2 * fl_lo:.2f} min, no washer) covers the widest body hole all round, the screw {fl_off:.2f} "
         "off (all five)",
         fl_lo - fl_off - r_hole_max),
        (f"flange (dc {2 * fl_hi:.1f} max) fits the smallest counterbore, {co_stop:.2f} off centre at most; against "
         f"its wall the rim (c {sc['flange_c']} min) stands taller than the floor corner (R{S.CB_FLOOR_R} max)",
         min(co_stop, sc["flange_c"] - S.CB_FLOOR_R)),
        ("counterbore to the outer body wall (MJF), beyond 1.5 (JLC3DP fastener features)", corner - 1.5),
        (f"counterbores (R{bm['cb'][0]:.2f} to R{bm['cb'][1]:.2f} measured on the body, all five) are the one the "
         f"flange rows take (R{MM.HEAD_R})", 0.05 - max(abs(v - MM.HEAD_R) for v in bm["cb"])),
        (f"corner boss wall round the counterbore ({bm['wall']:.2f} measured on the body; counterbore and boss MJF "
         f"+-{seat_tol} on the diameter), beyond 1.5 (JLC3DP fastener features)", bm["wall"] - seat_tol - 1.5),
        (f"PA12 between counterbore seat and PCB ({bm['seat_t']:.2f} measured on the body, all five), beyond 1.5 "
         "(JLC3DP fastener features)", bm["seat_t"] - 1.5),
        (f"body walls ({S.PLATE_Z0 - bm['wall_top'][1]:.2f} under the plate, as built) never touch it (MJF "
         f"{seat_tol}, PCB -{pcb_tol}, boss "
         f"-{h_tol:g}, back face over bare boss ends, bowed {S.PLATE_FLAT * bow_wall:.3f} down)", wall_gap),
        (f"M3 x {sc['L']:.0f} full thread engaged in the plate boss (tip {tip_lo:.2f} in, less {sc['tip']} incomplete "
         f"and the {tp['cham']} countersink), shortest stack, beyond {S.ENGAGE_MIN}", engaged - S.ENGAGE_MIN),
        (f"screw tip ({tip_hi:.2f} into the boss, longest stack) short of the end of the full thread ({tp['full']})",
         tp["full"] - tip_hi),
        (f"plate in front of the tap drill point ({pm['tap']:.2f} deep measured on the plate), low boss, thin plate, "
         "beyond 1.0", bo["h"] - bo["h_tol"] + t_min - pm["tap"] - 1.0),
        ("flange and button head recessed (all five; the front mounts are the worst), deep seat",
         head_lo - boss_floor),
        (f"foot pad round a {MM.FOOT_D:.0f} mm foot (flat over r {bm['pad']:.2f}, measured on the body), per side, "
         "beyond 0.5", bm["pad"] - MM.FOOT_D / 2 - 0.5),
        (f"body: no void under 0.8 mm deeper than 0.4 (worst at {void_at})", 0.4 - void),
        (f"body: no wall under 0.8 mm deeper than 0.4 (worst at {wall_at})", 0.4 - wall),
        (f"body: no wall under 1.9 mm (JLC3DP MJF 2.0 over 100 mm, less the raster) deeper than 0.6 (square corners "
         f"0.4) bar the screw bosses (worst at {wall2_at})", 0.6 - wall2),
        (f"assembly blocks ({S.ASSEMBLY_BLOCK:.0f}) over the shaft tips, beyond 3", S.ASSEMBLY_BLOCK - protrude - 3),
        ("plate edge strip free for the blocks, beyond 8", edge - 8),
        (f"light pipe fits its hole ({pp['clear']} under, hole +{lt_up}/-{lt_dn:g}), beyond anodising "
         f"({pp['anodise']}) and resin (+{pp['resin']})", pp["clear"] - lt_dn - pp["anodise"] - pp["resin"]),
        (f"light pipe as built: base Ø{pipe_m['base_d']:.2f} x {pipe_m['base_len']:.2f}, rod Ø{pipe_m['rod_d']:.2f}, "
         f"{pipe_m['len']:.2f} long in all (measured on the pipe solid) is the stack's (Ø{pp['base_d']} x "
         f"{pp['base_len']}, Ø{d - pp['clear']:g}, {pp['len']:g})",
         0.01 - max(abs(pipe_m["base_d"] - pp["base_d"]), abs(pipe_m["base_len"] - pp["base_len"]),
                    abs(pipe_m["rod_d"] - (d - pp["clear"])), abs(pipe_m["len"] - pp["len"]))),
        (f"light pipe pair as built: necks Ø{pair_m['neck_d'][0]:.2f} x {pair_m['neck_len'][0]:.2f}, bar "
         f"{pair_m['bar'][0]:.2f} x {pair_m['bar'][1]:.2f} (measured on the pair's mesh) are the stack's "
         f"(Ø{pp['neck_d']} x {pp['neck_len']}, {pp['bar'][0]} x {pp['bar'][1]})",
         0.01 - max(*(abs(v - pp["neck_d"]) for v in pair_m["neck_d"]),
                    *(abs(v - pp["neck_len"]) for v in pair_m["neck_len"]),
                    *(abs(v - n) for v, n in zip(pair_m["bar"], pp["bar"], strict=True)))),
        (f"light pipe pair {' x '.join(f'{v:.1f}' for v in pair_m['size'])} over all (measured), beyond JLC3DP's "
         f"least resin part ({' x '.join(f'{v:g}' for v in S.RESIN_PART_MIN)})",
         min(v - n for v, n in zip(pair_m["size"], S.RESIN_PART_MIN, strict=True))),
        (f"light pipe snap-off necks ({pp['neck_d']}, the resin minimum) inside the base bottom (-{pp['resin']})",
         (pp["base_d"] - pp["resin"]) / 2 - pp["neck_d"] / 2),
        *pipe_rows(back_lo, back_hi, face_lo, board, caps),
    ]
    for name, ((lx, ly), _, _) in B.LEDS.items():
        off_, dia = pm["lights"][name]
        rows.append((f"{name} light hole as built: Ø{dia:.2f}, {off_:.3f} off its place over the LED (measured on "
                     f"the plate) is the stack's (Ø{d})", 0.01 - max(off_, abs(dia - d))))
        web = min(rrect_sd(lx - x, ly - y, *S.KEY_HOLE) for x, y in caps) - d / 2
        web_lo = (min(rrect_sd(lx - x, ly - y, *key_hole_max()) for x, y in caps) - (d + lt_up) / 2
                  - pt["plate"])
        rows.append((f"{name} light hole web to the next key hole ({web:.2f}), beyond {S.CNC_WALL} (JLCCNC "
                     "recommended)", web - S.CNC_WALL))
        rows.append((f"{name} light hole web with both holes at +{lt_up} and {pt['plate']} off position "
                     f"({web_lo:.2f}), beyond {S.CNC_WALL_MIN} (JLCCNC minimum)", web_lo - S.CNC_WALL_MIN))
        # on the back face the key hole's edge break (the lead-in for the cap) takes its width off that web: what
        # stays flat must still carry the pipe's shoulder, the ring between the hole and the base's rim
        seat = (pp["base_d"] - pp["resin"]) / 2 - d / 2
        rows.append((f"{name} light hole: back face left flat between it and the next key hole's back edge break "
                     f"({S.KEY_BACK_BREAK_MAX} at most), {web_lo - S.KEY_BACK_BREAK_MAX:.2f}, beyond the pipe "
                     f"shoulder's ring ({seat:.2f}) and the light hole's own break ({S.LIGHT_HOLE_BACK_BREAK})",
                     web_lo - S.KEY_BACK_BREAK_MAX - seat - S.LIGHT_HOLE_BACK_BREAK))
    rows = [(r[0], r[1], r[2] if len(r) > 2 else "mm") for r in rows]   # a margin in mm unless a row says
    for name, v, unit in rows:
        print(f"  {name:106s} {v:6.3f} {unit:2s} {'OK' if v > 0 else 'FAIL'}")
    if any(not v > 0 for _, v, _ in rows):           # NaN fails too; a plain raise: asserts vanish under -O
        raise SystemExit(f"fit check failed: {[n for n, v, _ in rows if not v > 0]}")


if __name__ == "__main__":
    plate, _ = PS.build()
    knobs = knob_solids()
    outer, inner, range_knob = knobs["outer", "nominal"], knobs["inner", "nominal"], knobs["range", "nominal"]
    draw_sections(plate, outer, inner, range_knob)
    clearances(plate, outer, inner, range_knob, {k: mesh_triangles(s) for k, s in knobs.items()})
