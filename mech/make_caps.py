"""Labelled key caps for the Avionics Panel rev 1 (full-colour print: OBJ + MTL + PNG texture).

rev 1: one label per cap in one size (the shift legends are engraved on the plate), amber SHIFT label.

28 caps (9.6 x 6.4 mm, 6 mm tall) for 6x6 mm tactile switches, 9.5 mm high with a round 3.10 +-0.30 mm
plunger (TE 1-1825910-4 = FSM8JH). The socket is a 3.6 mm bore with three ribs, 0.8 mm wide at the tip
(the process's minimum detail), reaching in to 3.05 mm: see stack.CAP_SOCKET for the range it grips.
Test-print one cap first: the cap sits 2.5 mm proud of the plate. Black caps, white printed labels, amber SHIFT.
Exact (watertight) meshes, one shell per cap.
"""
import math
import zipfile
from pathlib import Path

import numpy as np
import stack as S
from PIL import Image, ImageDraw, ImageFont

TEX = 4096
# the plate's condensed face (Barlow Semi Condensed, OFL, in fonts/), weight 600 as in the 3D view
FONT = str(Path(__file__).resolve().parent / "fonts/BarlowSemiCondensed-SemiBold.ttf")
BLACK = (18, 18, 20)
WHITE = (245, 245, 245)

LABELS = [[label for label, _ in row] for row in S.KEY_LEGENDS]   # stack.py holds the legends
AMBER = (217, 164, 65)
caps = [LABELS[r][c] for r in range(4) for c in range(7)]

# low and wide, like the real boxes
_SK = S.CAP_SOCKET
KEY = dict(w=S.CAP["w"], h=S.CAP["h"], r=S.CAP["r"], height=S.CAP["height"], cham=S.CAP["cham"],
           sock=(_SK["d"], _SK["rib_d"]), sock_d=_SK["depth"])
RIB = dict(n=_SK["ribs"], tip_w=_SK["tip_w"], base_w=_SK["base_w"])   # socket ribs: flat tip, width at the wall

CELL = 512                        # texture cell per cap (8 x 8 grid on a 4k texture)
GRID = TEX // CELL


def rrect_loop(w, h, r, n=8, seg=(7, 12)):
    """Closed CCW loop of a rounded rectangle centred at 0 (fixed vertex count 4*(n+1) + 2*(seg[0]+seg[1]-2)).
    The straight edges are split into seg (short, long) pieces, so the bottom ring to the socket stays local."""
    pts = []
    corners = ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
               (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180))
    for k, (cx, cy, a0) in enumerate(corners):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        nx, ny, na = corners[(k + 1) % 4]
        nxt = (nx + r * math.cos(math.radians(na)), ny + r * math.sin(math.radians(na)))
        s = seg[k % 2]                                   # right and left edges short, top and bottom long
        x0, y0 = pts[-1]
        pts += [(x0 + (nxt[0] - x0) * i / s, y0 + (nxt[1] - y0) * i / s) for i in range(1, s)]
    return np.array(pts)


def ribbed_loop(d, d_rib, n=60):
    """CCW socket loop: circle of dia d with RIB["n"] trapezoid ribs reaching in to dia d_rib (first one at +y)."""
    R, r = d / 2, d_rib / 2
    a_tip, a_base = RIB["tip_w"] / 2 / r, RIB["base_w"] / 2 / R
    ribs = [math.pi / 2 + 2 * math.pi * k / RIB["n"] for k in range(RIB["n"])]
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n + 1e-9
        if all(abs((t - c + math.pi) % (2 * math.pi) - math.pi) > a_base + 0.02 for c in ribs):
            pts.append((t, R))
    for c in ribs:
        rt = r / math.cos(a_tip)                         # flat tip at distance r from the centre
        pts += [(c - a_base, R), (c - a_tip, rt), (c + a_tip, rt), (c + a_base, R)]
    pts.sort(key=lambda p: p[0] % (2 * math.pi))
    return np.array([(rr * math.cos(t), rr * math.sin(t)) for t, rr in pts])


def zipper(outer_ids, inner_ids, P):
    """Triangulate the ring between two star-shaped loops around (0,0), CCW, by angle."""
    def ang(i):
        return math.atan2(P[i][1], P[i][0]) % (2 * math.pi)
    o = sorted(outer_ids, key=ang)
    q = sorted(inner_ids, key=ang)
    T = []
    i = j = 0
    no, ni = len(o), len(q)
    while i < no or j < ni:
        a0, a1 = o[i % no], o[(i + 1) % no]
        b0, b1 = q[j % ni], q[(j + 1) % ni]
        na = ang(a1) + (2 * math.pi if i + 1 >= no else 0)
        nb = ang(b1) + (2 * math.pi if j + 1 >= ni else 0)
        if (na <= nb and i < no) or j >= ni:
            T.append((a0, a1, b0)); i += 1
        else:
            T.append((a0, b1, b0)); j += 1
    return T


def orient(T, P, want_z):
    out = []
    for t in T:
        p0, p1, p2 = (np.array(P[k]) for k in t)
        nz = np.cross(p1 - p0, p2 - p0)[2]
        out.append(t if nz * want_z > 0 else (t[0], t[2], t[1]))
    return out


def cap_mesh(p):
    outer = rrect_loop(p["w"], p["h"], p["r"])
    topl = rrect_loop(p["w"] - 2 * p["cham"], p["h"] - 2 * p["cham"], max(p["r"] - p["cham"], 0.3))
    sock = ribbed_loop(*p["sock"])
    m, k = len(outer), len(sock)
    H, Hs, Hc = p["height"], p["sock_d"], p["height"] - p["cham"]
    V = [(x, y, 0.0) for x, y in outer] + [(x, y, Hc) for x, y in outer] + \
        [(x, y, H) for x, y in topl] + [(x, y, 0.0) for x, y in sock] + \
        [(x, y, Hs) for x, y in sock] + [(0.0, 0.0, H), (0.0, 0.0, Hs)]
    S0, S1, CT, CS = 3 * m, 3 * m + k, 3 * m + 2 * k, 3 * m + 2 * k + 1
    T = []
    for i in range(m):
        j = (i + 1) % m
        T += [(i, j, m + j), (i, m + j, m + i)]
        T += [(m + i, m + j, 2 * m + j), (m + i, 2 * m + j, 2 * m + i)]
        T += [(2 * m + i, 2 * m + j, CT)]
    for i in range(k):
        j = (i + 1) % k
        T += [(S0 + j, S0 + i, S1 + i), (S0 + j, S1 + i, S1 + j)]   # socket wall (faces inward)
    T += orient([(S1 + i, S1 + (i + 1) % k, CS) for i in range(k)], V, -1)   # socket ceiling, normal down
    ring = zipper(list(range(m)), list(range(S0, S0 + k)), V)
    assert ring == orient(ring, V, 1), "bottom ring folds over: refine the outer loop"
    T += orient(ring, V, -1)                                             # bottom ring, normal down
    return np.array(V), np.array(T)


# Tactile bars, found without looking (as in the 3D view): SHIFT and DN at the front edge, UP at the back edge.
# A closed box, 0.35 mm proud, sunk 0.05 mm into the top so the printer fuses it with the cap. Model -y is the
# front edge (the texture's bottom).
BAR = S.CAP_BAR
BAR_EDGE = {"SHIFT": -1, "DN": -1, "UP": 1}


def bar_mesh(p, edge):
    y = edge * ((p["h"] - 2 * p["cham"]) / 2 - BAR["inset"])
    x0, x1, y0, y1 = -BAR["w"] / 2, BAR["w"] / 2, y - BAR["d"] / 2, y + BAR["d"] / 2
    z0, z1 = p["height"] - BAR["sink"], p["height"] + BAR["proud"]
    V = [(x, yy, z) for z in (z0, z1) for x, yy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    T = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),            # bottom (down), top (up)
         (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return np.array(V), np.array(T)


# ---------------- texture ----------------
tex = Image.new("RGB", (TEX, TEX), BLACK)
dr = ImageDraw.Draw(tex)


ARROW_EM = 0.55                                  # the D-> arrow (em), as in the 3D view


def _width_em(label, font100):
    """Legend width in em; the flip-flop icon and the direct-to arrow are drawn, not taken from the font."""
    if label == "D→":
        return font100.getlength("D") / 100 + ARROW_EM
    if label.endswith("⇆"):
        return font100.getlength(label[:-1].rstrip()) / 100 + S.FLIP_GAP + S.FLIP_W
    return font100.getlength(label) / 100


def _legend_em():
    """One legend size for every cap: the widest legend fills 84 % of the cap top (about 2.0 mm cap height)."""
    probe = ImageFont.truetype(FONT, 100)
    top_w = KEY["w"] - 2 * KEY["cham"]
    return min(3.1, min(top_w * 0.84 / _width_em(t, probe) for t in caps))     # em size in mm


def draw_label(cell, text, p):
    gx, gy = cell % GRID, cell // GRID
    x0, y0 = gx * CELL, gy * CELL
    ppm = CELL / max(p["w"], p["h"])                 # pixels per mm
    if not text:
        return x0, y0, ppm
    em = LEGEND_EM * ppm
    font = ImageFont.truetype(FONT, int(round(em)))
    colour = AMBER if text == "SHIFT" else WHITE
    cx, cy = x0 + CELL / 2, y0 + CELL / 2 + 0.04 * em
    if text == "D→":                                 # Garmin direct-to: a D with an arrow through it
        dw = font.getlength("D")
        xl = cx - (dw + ARROW_EM * em) / 2
        dr.text((xl, cy), "D", font=font, fill=colour, anchor="lm")
        y, xe = cy - 0.02 * em, xl + dw + ARROW_EM * em
        dr.line([(xl - 0.12 * em, y), (xe - 0.2 * em, y)], fill=colour, width=max(1, round(0.085 * em)))
        dr.polygon([(xe, y), (xe - 0.26 * em, y - 0.17 * em), (xe - 0.26 * em, y + 0.17 * em)], fill=colour)
    elif text.endswith("⇆"):                         # flip-flop: text + two opposed arrows
        t = text[:-1].rstrip()
        tw, gap = font.getlength(t), S.FLIP_GAP * em
        xl = cx - (tw + gap + S.FLIP_W * em) / 2
        dr.text((xl, cy), t, font=font, fill=colour, anchor="lm")
        ix = xl + tw + gap
        for poly in S.FLIP_ICON:
            dr.polygon([(ix + x * em, cy + y * em) for x, y in poly], fill=colour)
    else:
        dr.text((cx, cy), text, font=font, fill=colour, anchor="mm")
    return x0, y0, ppm


LEGEND_EM = _legend_em()

# ---------------- assemble OBJ ----------------
allV, allT, allUV = [], [], []
pitch = 16.0
black_uv = ((TEX - 8) / TEX, 8 / TEX)       # a black pixel near the corner (outside all label areas)
for k, label in enumerate(caps):
    p = KEY
    V, T = cap_mesh(p)
    m = len(rrect_loop(p["w"], p["h"], p["r"]))
    topmask = np.zeros(len(V), bool)
    topmask[2 * m:3 * m] = True
    topmask[len(V) - 2] = True
    x0, y0, ppm = draw_label(k, label, p)
    uv = np.tile(np.array(black_uv), (len(V), 1))
    # top vertices: planar projection into this cap's texture cell (image y down, model y up)
    u = (x0 + CELL / 2 + V[:, 0] * ppm) / TEX
    v = 1 - (y0 + CELL / 2 - V[:, 1] * ppm) / TEX
    uv[topmask] = np.stack([u, v], 1)[topmask]
    if label in BAR_EDGE:                    # bar: its own black shell on the top face
        Vb, Tb = bar_mesh(p, BAR_EDGE[label])
        T = np.concatenate([T, Tb + len(V)])
        V = np.concatenate([V, Vb])
        uv = np.concatenate([uv, np.tile(np.array(black_uv), (len(Vb), 1))])
    # place caps on a grid for printing
    col, row = k % 8, k // 8
    off = np.array([col * pitch, -row * pitch, 0])
    base = sum(len(a) for a in allV)
    allV.append(V + off)
    allUV.append(uv)
    allT.append(T + base)

# top-face triangles must only use top UVs; side faces touching the top loop need black UVs
# -> duplicate the top-loop vertices: separate vertex set for UV purposes
V = np.concatenate(allV)
UV = np.concatenate(allUV)
T = np.concatenate(allT)

# faces fully on the top get the label UVs, all others black
face_top = np.all(np.abs(V[T][:, :, 2] - V[T][:, :, 2].max(axis=1, keepdims=True)) < 1e-9, axis=1) & \
    np.all(UV[T][:, :, 0] != black_uv[0], axis=1)

with open("avionics-panel-rev1-caps.mtl", "w") as f:
    f.write("newmtl caps\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nillum 1\nmap_Kd avionics-panel-rev1-caps.png\n")
with open("avionics-panel-rev1-caps.obj", "w") as f:
    f.write("# Avionics Panel rev 1 key caps (units: mm)\nmtllib avionics-panel-rev1-caps.mtl\nusemtl caps\n")
    for x, y, z in V:
        f.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
    for u, v in UV:
        f.write(f"vt {u:.6f} {v:.6f}\n")
    f.write(f"vt {black_uv[0]:.6f} {black_uv[1]:.6f}\n")
    blk = len(UV) + 1
    for t, ft in zip(T, face_top, strict=True):
        a, b, c = t + 1
        if ft:
            f.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")
        else:
            f.write(f"f {a}/{blk} {b}/{blk} {c}/{blk}\n")
tex.save("avionics-panel-rev1-caps.png")
# one zip for full-colour printing services: model, material and texture together (fixed timestamps)
with zipfile.ZipFile("avionics-panel-rev1-caps.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in ("avionics-panel-rev1-caps.obj", "avionics-panel-rev1-caps.mtl", "avionics-panel-rev1-caps.png"):
        zi = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
        with open(f, "rb") as src:
            z.writestr(zi, src.read())

# checks: watertight per cap, positive volume
e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
fwd = {tuple(a) for a in e}
open_edges = sum(1 for a in e if (a[1], a[0]) not in fwd)
tri = V[T]
vol = np.sum(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2]))) / 6
sk = ribbed_loop(*KEY["sock"])
sock_in = min(np.linalg.norm(a + np.clip(-a @ (b - a) / ((b - a) @ (b - a)), 0, 1) * (b - a))
              for a, b in zip(sk, np.roll(sk, -1, 0), strict=True))
print(f"socket {KEY['sock'][0]} mm, {RIB['n']} ribs, inscribed dia {2 * sock_in:.2f} mm "
      f"(plunger {S.PLUNGER_D:.2f} +-0.30)")
print(f"legend em {LEGEND_EM:.2f} mm, cap height about {0.7 * LEGEND_EM:.2f} mm")
print(f"{len(caps)} caps, {len(V)} vertices, {len(T)} triangles, open edges {open_edges}, "
      f"volume {vol/1000:.2f} cm3, top faces {face_top.sum()}")
