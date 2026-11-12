"""Labelled key caps for the Avionics Panel rev 1 (full-colour print: OBJ + MTL + PNG texture).

rev 1: one label per cap in one size (the shift legends are UV printed on the plate), amber SHIFT label.

28 caps (9.6 x 6.4 mm, 5.7 mm tall) for 6x6 mm tactile switches, 9.5 mm high with a round plunger that tapers
from 3.12 mm near its top to 3.51 mm at the switch body (TE 1-1825910-4 = FSM8JH, TE's STEP model). The socket
is a 3.8 mm bore with four rigid ribs 1.2 mm wide along its wall that follow the plunger's cone; its flat
ceiling sits on the plunger top. A rigid fit needs better than the resin prints, so there are four full sets
(stack.CAP_SETS: rib circles 3.15, 3.25, 3.35 and 3.05 mm at the socket mouth), marked with 1 to 4 dimples on
the cap underside: the set that seats fully and holds is the one to fit. Black caps, white printed labels, amber
SHIFT, every coloured stroke at least 0.4 mm wide (stack.LEGEND_*). Exact solids (OpenCascade), meshed
watertight, one shell per cap.
Writes caps-<set>.zip (OBJ, MTL and texture of the set's 28 caps).
Needs pythonocc-core (see make_plate_step.py) and pillow.
"""
import io
import math
import zipfile
from pathlib import Path

import numpy as np
import stack as S
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import topods
from occ_util import box, cut, cyl, fuse, prism, rrect_wire
from PIL import Image, ImageDraw, ImageFont

TEX = 4096
# the plate's condensed face (Barlow Semi Condensed, OFL, in viewer/fonts/), Bold on the caps (stack.LEGEND_WEIGHT)
FONT = str(Path(__file__).resolve().parent.parent / "viewer" / "fonts"
           / {700: "BarlowSemiCondensed-Bold.ttf"}[S.LEGEND_WEIGHT])
SS = 4                            # legends are drawn 4x finer, then averaged down into the texture
BLACK = (18, 18, 20)
WHITE = (245, 245, 245)

LABELS = [[label for label, _ in row] for row in S.KEY_LEGENDS]   # stack.py holds the legends
AMBER = S.AMBER["rgb"]
caps = [LABELS[r][c] for r in range(4) for c in range(7)]

KEY = dict(w=S.CAP["w"], h=S.CAP["h"], r=S.CAP["r"], height=S.CAP["height"], cham=S.CAP["cham"])
SK = S.CAP_SOCKET

CELL = 512                        # texture cell per cap (8 x 8 grid on a 4k texture)
GRID = TEX // CELL


# ---------------- solids ----------------
def rotz(shape, deg):
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(deg))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def xz_prism(pts, y0, y1):
    """a prism from a polygon in the XZ plane, from y0 to y1."""
    return prism([(x, y0, z) for x, z in pts], dy=y1 - y0)


def cap_body(p):
    """cap outline with the chamfered top, bottom at z = 0."""
    ts = BRepOffsetAPI_ThruSections(True, True)
    ts.AddWire(rrect_wire(p["w"], p["h"], p["r"], 0.0))
    ts.AddWire(rrect_wire(p["w"], p["h"], p["r"], p["height"] - p["cham"]))
    ts.AddWire(rrect_wire(p["w"] - 2 * p["cham"], p["h"] - 2 * p["cham"], max(p["r"] - p["cham"], 0.3), p["height"]))
    ts.Build()
    return ts.Shape()


def socket(p, name):
    """cap with the socket of set `name`: a bore with four rigid ribs along its wall that follow the plunger's
    cone (lead-in at the mouth, clear of the ceiling), and the set's dimples on the underside."""
    hs, R = SK["depth"], SK["d"] / 2
    hw, lead, top = SK["rib_w"] / 2, SK["lead"], hs - SK["relief"]

    def r(z):                                        # rib circle radius at height z above the cap bottom
        return S.cap_rib_d(name, hs - z) / 2
    cap = cut(cap_body(p), cyl(R, -1, hs))
    # the lead-in starts inside the profile's outer edge, also on a set moved large (stack.CAP_SETS_MOVE)
    prof = [(min(r(lead) + SK["lead_r"], R + 0.05), 0), (R + 0.1, 0), (R + 0.1, top), (r(top), top), (r(lead), lead)]
    for a in SK["rib_angles"]:
        cap = fuse(cap, rotz(xz_prism(prof, -hw, hw), a))
    m = S.CAP_MARK
    for x, y in m["pos"][:set_marks(name)]:
        cap = cut(cap, cyl(m["d"] / 2, -1, m["depth"], x, y))
    return cap


def set_marks(name):
    """how many dimples mark cap set `name`: A 1, B 2, C 3, D 4."""
    return list(S.CAP_SETS).index(name) + 1


# Tactile bars, found without looking (as in the 3D view): SHIFT and DN at the front edge, UP at the back edge.
# A box (stack.CAP_BAR) sunk 0.05 mm into the top so it fuses with the cap. Model -y is the front edge (the
# texture's bottom).
BAR = S.CAP_BAR
BAR_EDGE = {"SHIFT": -1, "DN": -1, "UP": 1}


def with_bar(cap, p, edge):
    y = edge * ((p["h"] - 2 * p["cham"]) / 2 - BAR["inset"])
    return fuse(cap, box(-BAR["w"] / 2, y - BAR["d"] / 2, p["height"] - BAR["sink"],
                         BAR["w"] / 2, y + BAR["d"] / 2, p["height"] + BAR["proud"]))


def mesh(shape, top_z, deflection=0.004):
    """welded triangles of a solid: vertices (n, 3), triangles (m, 3), and which triangles lie on the top face."""
    if not BRepCheck_Analyzer(shape).IsValid():
        raise RuntimeError("invalid cap solid")
    BRepMesh_IncrementalMesh(shape, deflection, False, 0.2, True)
    pts, tris, top = [], [], []
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        face = topods.Face(ex.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation(face, loc)
        t = loc.Transformation()
        nodes = np.array([[q.X(), q.Y(), q.Z()]
                          for q in (tri.Node(i + 1).Transformed(t) for i in range(tri.NbNodes()))])
        idx = np.array([tri.Triangle(i + 1).Get() for i in range(tri.NbTriangles())]) - 1
        if face.Orientation() == TopAbs_REVERSED:
            idx = idx[:, [0, 2, 1]]
        flat_top = bool(np.all(np.abs(nodes[:, 2] - top_z) < 1e-6))
        tris.append(idx + sum(len(a) for a in pts))
        pts.append(nodes)
        top += [flat_top] * len(idx)
        ex.Next()
    P, T = np.concatenate(pts), np.concatenate(tris)
    key = np.round(P / 1e-5).astype(np.int64)                       # weld the faces' shared edge nodes
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V, T = P[first], inv.reshape(-1)[T]
    keep = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 2] != T[:, 0])
    return V, T[keep], np.array(top)[keep]


# ---------------- texture ----------------
tex = Image.new("RGB", (TEX, TEX), BLACK)


DTO = S.DIRECT_TO                                # the D-> arrow (em), as in the 3D view


def _width_em(label, font100):
    """Legend width in em; the flip-flop icon and the direct-to arrow are drawn, not taken from the font."""
    if label == "D→":
        return font100.getlength("D") / 100 + DTO["w"]
    if label.endswith("⇆"):
        return font100.getlength(label[:-1].rstrip()) / 100 + S.FLIP_GAP + S.FLIP_W
    return font100.getlength(label) / 100


def _legend_em():
    """The one legend size (em in mm): stack.LEGEND_FILL, LEGEND_EM_MAX."""
    probe = ImageFont.truetype(FONT, 100)
    top_w = KEY["w"] - 2 * KEY["cham"]
    return min(S.LEGEND_EM_MAX,                                                        # em in mm
               min((top_w * S.LEGEND_FILL - 2 * S.LEGEND_GROW) / _width_em(t, probe) for t in caps))


def draw_label(cell, text, p):
    """Draw a legend into its texture cell: glyphs, arrow and icon grown all round by stack.LEGEND_GROW (a round
    outline), drawn SS times finer and averaged down."""
    gx, gy = cell % GRID, cell // GRID
    x0, y0 = gx * CELL, gy * CELL
    ppm = CELL / max(p["w"], p["h"])                 # pixels per mm
    if not text:
        return
    q = ppm * SS
    em, g = LEGEND_EM * q, S.LEGEND_GROW * q
    im = Image.new("L", (CELL * SS, CELL * SS), 0)
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, int(round(em)))
    # the middle of the capitals on the cap centre: the "m" anchors centre on ascender and descender, which
    # sets capitals about 0.25 mm towards the front, where the SHIFT and DN tactile bars stand
    top, bottom = font.getbbox("H", anchor="ls")[1::2]
    cx, cy, base = CELL * SS / 2, CELL * SS / 2, CELL * SS / 2 - (top + bottom) / 2

    def write(xy, t, anchor):                        # anchor "l" or "m" horizontally, on the baseline
        d.text((xy[0], base), t, font=font, fill=255, anchor=anchor[0] + "s", stroke_width=round(g),
               stroke_fill=255)

    def shape(pts):                                  # a filled polygon grown by g (round corners)
        d.polygon(pts, fill=255)
        d.line(pts + [pts[0]], fill=255, width=round(2 * g))
        for x, y in pts:
            d.ellipse((x - g, y - g, x + g, y + g), fill=255)

    def line(xa, xb, y, w):                          # a horizontal line w wide, grown by g
        shape([(xa, y - w / 2), (xb, y - w / 2), (xb, y + w / 2), (xa, y + w / 2)])
    if text == "D→":                                 # Garmin direct-to: a D with an arrow through it
        dw = font.getlength("D")
        xl = cx - (dw + DTO["w"] * em) / 2
        write((xl, cy), "D", "lm")
        y, xe = cy - DTO["dy"] * em, xl + dw + DTO["w"] * em
        line(xl - DTO["tail"] * em, xe - DTO["neck"] * em, y, S.LEGEND_LINE * em)
        xh, dh = xe - DTO["head"] * em, DTO["head_h"] * em
        shape([(xe, y), (xh, y - dh), (xh, y + dh)])
    elif text.endswith("⇆"):                         # flip-flop: text + two opposed arrows
        t = text[:-1].rstrip()
        tw, gap = font.getlength(t), S.FLIP_GAP * em
        xl = cx - (tw + gap + S.FLIP_W * em) / 2
        write((xl, cy), t, "lm")
        ix = xl + tw + gap
        for poly in S.CAP_FLIP_ICON:
            shape([(ix + x * em, cy + y * em) for x, y in poly])
    else:
        write((cx, cy), text, "mm")
    tex.paste(AMBER if text == "SHIFT" else WHITE, (x0, y0, x0 + CELL, y0 + CELL),
              im.resize((CELL, CELL), Image.BOX))


LEGEND_EM = _legend_em()


# ---------------- writers ----------------
def write_obj(f, mtl, parts):
    """parts: (V, T, top mask, UV per vertex, UV of a black pixel); one shell each. Every vertex has its UV
    (vt n for v n); faces off the top use their part's black UV, listed after the vertex UVs."""
    f.write(f"# Avionics Panel rev 1 key caps (units: mm)\nmtllib {mtl}\nusemtl caps\n")
    lines_v, lines_vt, lines_f = [], [], []
    for V, _T, _top, uv, _blk in parts:
        lines_v += [f"v {x:.4f} {y:.4f} {z:.4f}\n" for x, y, z in V]
        lines_vt += [f"vt {u:.6f} {v:.6f}\n" for u, v in uv]
    nvt = len(lines_v)
    lines_vt += [f"vt {u:.6f} {v:.6f}\n" for *_rest, (u, v) in parts]
    base = 0
    for k, (V, T, top, _uv, _blk) in enumerate(parts):
        b = nvt + k + 1
        for t, ft in zip(T + base + 1, top, strict=True):
            a, c, d = t
            lines_f.append(f"f {a}/{a} {c}/{c} {d}/{d}\n" if ft else f"f {a}/{b} {c}/{b} {d}/{b}\n")
        base += len(V)
    f.write("".join(lines_v) + "".join(lines_vt) + "".join(lines_f))


def mtl_text(png):
    return f"newmtl caps\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nillum 1\nmap_Kd {png}\n"


def zip_add(z, name, data):
    zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(zi, data)


# ---------------- build ----------------
p = KEY
for k, label in enumerate(caps):
    draw_label(k, label, p)
pitch = 16.0
black_uv = ((TEX - 8) / TEX, 8 / TEX)       # a black pixel near the corner (outside all label areas)
png_all = io.BytesIO()
tex.save(png_all, "PNG")
summary = []
for name in S.CAP_SETS:
    plain = socket(p, name)
    meshes = {}                               # one mesh per shape: plain, bar at the front, bar at the back
    parts = []
    open_edges, vol = 0, 0.0
    for k, label in enumerate(caps):
        edge = BAR_EDGE.get(label, 0)
        if edge not in meshes:
            meshes[edge] = mesh(with_bar(plain, p, edge) if edge else plain, p["height"])
        V, T, top = meshes[edge]
        x0, y0 = (k % GRID) * CELL, (k // GRID) * CELL
        ppm = CELL / max(p["w"], p["h"])     # pixels per mm, as draw_label
        # top vertices: planar projection into this cap's texture cell (image y down, model y up)
        px, py = x0 + CELL / 2 + V[:, 0] * ppm, y0 + CELL / 2 - V[:, 1] * ppm
        uv = np.stack([px / TEX, 1 - py / TEX], 1)
        # watertight: every edge used once in each direction
        e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
        fwd = {tuple(a) for a in e}
        open_edges += sum(1 for a in e if (a[1], a[0]) not in fwd)
        tri = V[T]
        vol += np.sum(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2]))) / 6
        col, row = k % 8, k // 8              # print layout: a grid of caps
        parts.append((V + np.array([col * pitch, -row * pitch, 0]), T, top, uv, black_uv))
    if open_edges:
        raise RuntimeError(f"set {name}: {open_edges} open edges")
    base = f"avionics-panel-rev1-caps-{name}"
    # one zip for full-colour printing services: model, material and texture together (fixed timestamps)
    obj = io.StringIO()
    write_obj(obj, f"{base}.mtl", parts)
    with zipfile.ZipFile(f"{base}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        zip_add(z, f"{base}.obj", obj.getvalue())
        zip_add(z, f"{base}.mtl", mtl_text(f"{base}.png"))
        zip_add(z, f"{base}.png", png_all.getvalue())
    d_top = S.cap_rib_d(name, SK["relief"])
    summary.append(f"  set {name}: {set_marks(name)} dimple(s), ribs {d_top:.2f} to {S.CAP_SETS[name]:.2f} mm, "
                   f"{len(caps)} caps, {sum(len(q[0]) for q in parts)} vertices, "
                   f"{sum(len(q[1]) for q in parts)} triangles, open edges {open_edges}, volume {vol / 1000:.2f} cm3")

print(f"socket {SK['d']} mm, {len(SK['rib_angles'])} rigid ribs {SK['rib_w']} wide on the plunger cone "
      f"(3.12 to 3.29 over the {SK['depth']:.1f} mm socket), {len(S.CAP_SETS)} sets:")
print("\n".join(summary))
print(f"legend em {LEGEND_EM:.2f} mm, cap height about {0.7 * LEGEND_EM:.2f} mm, grown by {S.LEGEND_GROW} mm")
