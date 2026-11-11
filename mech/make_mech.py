"""Body for the Avionics Panel rev 1, exact solid (OpenCascade) -> STEP + STL for JLC3DP, steel plate DXF.

The 6 degree wedge is part of the body, so no wedge feet are needed; four flat silicone feet only stop it
sliding; they go on four flat pads. The wedge is hollow from below: a 2 mm floor under the PCB, ribs down to
the desk plane (under the two PCB posts and between them), the screw bosses joined to the walls, a solid band
along the front, and a recess in the bottom for an optional 2 mm steel plate as desk weight.
BOOT hole in the floor, USB-C opening in the back wall, open to the top as a wider notch so the socket clears the
wall when the board goes in; a separate filler (same print) closes that notch from the back once the body is on,
resting on the two ledges beside the opening. The front plate is CNC aluminium (make_plate_step.py); every height
is in stack.py.

Stack (z = 0 is the PCB top):
  body     floor -7.6 .. -5.6 (-7.2 .. -5.6 at the front edge), bottom plane from -7.2 at the front to about
           -14 at the back, walls up to z 5.35 (0.65 below the plate), 4 bosses carry the PCB at z -1.6 (4 mm
           room for the SMD parts and the USB-C socket on the underside), 2 posts 0.25 under the middle of
           the PCB, counterbore seats at z -3.2 (1.6 mm of PA12 up to the PCB)
  plate    6061 from 12 mm stock: the 4 mm web at z 6 .. 10 and 4 bosses dia 5.5 down to the PCB top, tapped M3
  screws   4 x M3 x 8 flanged button head (ISO 7380-2) from below, no washer: body boss -> PCB -> plate boss
Height 17.2 mm at the front, rising to about 24 mm at the back.
Output frame: X right, Y away from the user (board y flipped), Z up.
"""
import math
import sys

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

sys.path.insert(0, "../pcb")
import board as B  # noqa: E402
import stack as S  # noqa: E402
from dxf import write_dxf  # noqa: E402
from make_plate_step import rrect_prism  # noqa: E402
from occ_util import box, common, cut, cyl, export, fuse, move, volume  # noqa: E402

# PCB to cavity wall: the cavity (161.0 x 61.0) may print 0.4 % small (JLC3DP MJF) and the routed board outline
# is +-0.2 (JLCPCB), so 0.5 per side; walls 2.0 (JLC3DP MJF: 2.0 for parts over 100 mm), so the outline
# (stack.OVH, shared with the plate) is 2.5 out from the PCB
CLEAR, WALL = 0.5, 2.0
assert abs(CLEAR + WALL - S.OVH) < 1e-9, "the body outline is the plate outline"
PCB_OUTLINE_TOL, BODY_SCALE_TOL = 0.2, 0.004
# Edge rails (docs/building/building.md): the economic variant has none, so its outline is routed all round. The full
# variant (Standard assembly, 70 x 70 mm minimum) has one rail on the long edge away from J1, V-cut: +-0.4
# (JLCPCB) on the board width. Should JLCPCB add rails on the short edges anyway, those V-cut edges can be too
# long for the cavity at worst: they are then sanded until the board is at most PCB_SANDED_LEN long.
PCB_VCUT_TOL, PCB_SANDED_LEN = 0.4, 160.2
UNDER = 4.0                         # room under the PCB: SMD parts, USB-C socket (3.2 mm), THT leads (stack.LEAD_MAX)
FLOOR = 2.0                         # floor under the PCB room; the wedge below it is hollow
FRONT = 1.6                         # body under the floor top at the front edge
Z_FLOOR_TOP = -S.PCB_T - UNDER      # -5.6
Z_FLOOR_BOT = Z_FLOOR_TOP - FLOOR   # -7.6: hollow from the bottom plane up to here
Z_BOT = Z_FLOOR_TOP - FRONT         # -7.2 at the front edge
SLOPE = math.tan(math.radians(S.BODY_TILT))


def _up(v):
    return math.ceil(round(v * 20, 6)) / 20


# The body locates nothing. Its screw hole is as small as passes the screw wherever the body's MJF tolerance
# over 153 mm and the plate's tapped bosses (the screws sit in them) put it (stack.POS_TOL), so the screw's flange
# (ISO 7380-2, dc 6.32 min) still covers it all round with the screw against the hole wall.
_PT = S.POS_TOL
SCREW_CLEAR = _up(S.SCREW_D / 2 + _PT["body"] + _PT["plate"] + _PT["body_hole"])        # 2.1: hole 4.2
SCREW_OFFSET = SCREW_CLEAR + _PT["body_hole"] - S.SCREW["d_min"] / 2   # screw against the widest hole wall
# Counterbore: the flange (7.0 max) fits it wherever the screw sits; its wall stops the flange (0.55 off centre)
# before the shank meets the body hole wall (0.82), a co-stop, so the counterbore's floor corner stays sharp
# (stack.CB_FLOOR_R); the flange then still covers the hole all round. check_fit.py checks both.
HEAD_R = 4.2                        # counterbore 8.4
BOSS_R = 4.0                        # boss top on the PCB (PA12 on solder mask past the 3.6 mm copper keep-out)
# boss round the counterbore, joined to the walls: JLC3DP asks for fastener walls over 1.5, which it keeps with
# the counterbore and the boss both printed 0.3 off on the diameter (check_fit.py measures it on the body)
BOSS_R_LOW = HEAD_R + 1.9
BOOT_HOLE = 5.0                     # bridge the BOOT pads with a small screwdriver
# The hollow stops where it is 1 mm high: in front of that the floor is solid down to the desk plane (BOOT hole
# and front feet). No slot or sliver under 0.8 mm anywhere: check_fit.py rasterises sections to prove it.
HOLLOW_H_MIN = 1.0
# The PCB is held only at its corners (about 153 mm apart) and sags about 0.1 mm under a normal key press in
# the middle, 0.3 to 0.5 under about 5 N, as much as the switch travel. Two posts carry it there, at spots free
# of bottom parts and pins: between the AUTOPILOT and AUDIO blocks, and between key columns 4 and 5, midway
# between rows 1 and 2. They end stack.SUPPORT_SHORT under the PCB, so the MJF tolerance cannot bow the board
# up towards the light pipes; a firm press bends the board onto them.
SUPPORTS = [(72.3, 30.8), (98.6, 30.8)]
SUPPORT_R = 2.5
SUPPORT_TOP = -S.PCB_T - S.SUPPORT_SHORT
# ribs in the hollow wedge, down to the bottom plane (board coordinates): front to back under the posts and
# between the knobs and key blocks, one across through the posts; 2.0 thick (JLC3DP MJF, parts over 100 mm)
RIB_T = 2.0
RIBS_X = (36.0, 72.3, 98.6, 125.0)          # 125 stays clear of the BOOT hole (x 132.1)
RIBS_Y = (30.8,)
# optional steel plate as desk weight, 2 mm, in a recess parallel to the bottom plane: x centred, y from the
# back wall (2.1 mm rim left) towards the front as far as the recess stays in the hollow under the 2 mm floor,
# so every wall round it keeps JLC3DP's 2.0 mm for MJF parts over 100 mm; notched at the back corners for the
# feet. It is taped onto the ribs, the USB-C block and the back rim. The plate (w x d, steel.dxf) is `gap`
# smaller than the recess all round (recess 144 x 37); its notches match the recess's, so it fits wherever it
# sits in the recess.
STEEL = dict(w=143.0, d=36.0, t=2.0, notch=15.0, gap=0.5, depth=2.2, y0=-0.4)
STEEL_RECESS = (STEEL["w"] + 2 * STEEL["gap"], STEEL["d"] + 2 * STEEL["gap"])
# flat pads for four self-adhesive feet up to 10 mm across (pads 12 mm), wide apart, outside the steel plate
FOOT_D, FOOT_PAD = 10.0, 12.0
FEET = [(15.5, 6.7), (B.W - 15.5, 6.7), (15.5, 55.5), (B.W - 15.5, 55.5)]
o = CLEAR + WALL


def wedge_cutter():
    """everything below the 6 degree bottom plane (z_bottom)."""
    y0, y1 = -o - 2, B.H + o + 2
    poly = BRepBuilderAPI_MakePolygon()
    for y, z in ((y0, z_bottom(y0)), (y1, z_bottom(y1)), (y1, -40), (y0, -40)):
        poly.Add(gp_Pnt(-o - 2, y, z))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(B.W + 2 * o + 4, 0, 0)).Shape()


def z_bottom(y):
    """the 6 degree bottom plane at board y."""
    return Z_BOT - SLOPE * ((B.H + o) - y)


def slab_under_plane(x0, x1, y0, y1, h):
    """the volume from below the bottom plane up to h above it (vertically), for x0..x1 and y0..y1."""
    poly = BRepBuilderAPI_MakePolygon()
    for y, z in ((y0, z_bottom(y0) - 2), (y1, z_bottom(y1) - 2), (y1, z_bottom(y1) + h), (y0, z_bottom(y0) + h)):
        poly.Add(gp_Pnt(x0, y, z))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(x1 - x0, 0, 0)).Shape()


def steel_x0():
    """board x of the recess's left end."""
    return B.W / 2 - STEEL_RECESS[0] / 2


def steel_recess():
    st = STEEL
    x0, x1, y0 = steel_x0(), steel_x0() + STEEL_RECESS[0], st["y0"]
    slab = slab_under_plane(x0, x1, y0, y0 + STEEL_RECESS[1], st["depth"] / math.cos(math.atan(SLOPE)))
    n = st["notch"]
    return cut(slab, box(x0 - 1, y0 - 1, -41, x0 + n, y0 + n, 0), box(x1 - n, y0 - 1, -41, x1 + 1, y0 + n, 0))


def steel_mass():
    st = STEEL
    return (st["w"] * st["d"] - 2 * st["notch"] ** 2) * st["t"] * 7.85e-3


def hollow_front():
    """board y where the hollow under the floor is HOLLOW_H_MIN high; in front of it the body is solid."""
    return math.floor(((B.H + o) - (Z_BOT - Z_FLOOR_BOT + HOLLOW_H_MIN) / SLOPE) * 10) / 10


def corner(mx, my, r, z0, z1):
    """a boss of radius r joined to the two walls of its corner: no slot between boss and wall."""
    sx, sy = (-1 if mx < B.W / 2 else 1), (-1 if my < B.H / 2 else 1)
    far = o + 10
    a = box(min(mx + sx * far, mx - sx * r), min(my + sy * far, my), z0,
            max(mx + sx * far, mx - sx * r), max(my + sy * far, my), z1)
    b = box(min(mx + sx * far, mx), min(my + sy * far, my - sy * r), z0,
            max(mx + sx * far, mx), max(my + sy * far, my - sy * r), z1)
    return fuse(fuse(a, b), cyl(r, z0, z1, mx, my))


def foot_bridges():
    """(x0, y0, x1, y1) of the blocks that join a foot pad to the boss next to it and to the wall behind both,
    so no slot narrower than 0.8 mm is left between them (the bosses round the counterbores reach close)."""
    out = []
    for fx, fy in FEET:
        mx, my = min(B.MOUNTS, key=lambda m: math.hypot(m[0] - fx, m[1] - fy))
        if math.hypot(mx - fx, my - fy) < BOSS_R_LOW + FOOT_PAD / 2 + 2.0:
            sy, r = (-1 if my < B.H / 2 else 1), min(BOSS_R_LOW, FOOT_PAD / 2)
            wall = B.H / 2 + sy * (B.H / 2 + o + 1)
            out.append((min(mx, fx), min(fy - sy * r, wall), max(mx, fx), max(fy - sy * r, wall)))
    return out


def hollow():
    """the wedge under the floor, inside the walls and behind the solid front band, less ribs, bosses, pads."""
    cx, cy = B.W / 2, B.H / 2
    h = rrect_prism(cx, cy, B.W + 2 * CLEAR, B.H + 2 * CLEAR, B.CORNER_R + CLEAR, -40, Z_FLOOR_BOT)
    h = cut(h, box(-o - 1, hollow_front(), -41, B.W + o + 1, B.H + o + 1, 0))
    keep = [box(x - RIB_T / 2, -o - 1, -41, x + RIB_T / 2, B.H + o + 1, 0) for x in RIBS_X]
    keep += [box(-o - 1, y - RIB_T / 2, -41, B.W + o + 1, y + RIB_T / 2, 0) for y in RIBS_Y]
    keep += [corner(mx, my, BOSS_R_LOW, -41, 0) for (mx, my) in B.MOUNTS]
    keep += [cyl(FOOT_PAD / 2, -41, 0, fx, fy) for (fx, fy) in FEET]
    keep += [box(x0, y0, -41, x1, y1, 0) for x0, y0, x1, y1 in foot_bridges()]
    keep += [box(B.USB_X - USB_KEEP[0] / 2, -o - 1, -41, B.USB_X + USB_KEEP[0] / 2, USB_KEEP[1], 0)]
    return cut(h, *keep)


# USB-C opening in the back wall round the plug overmould (USB-C spec: up to 12.35 x 6.5): wide enough for the
# board anywhere in the cavity (its sideways play set by the short edges, taken as V-cut: one up to 0.4 short),
# the opening where MJF puts it against the cavity wall (+-0.51 over the 127.5 mm from the left wall) and J1's
# placement, high enough for the body's height tolerance under the bosses, with bottom corners small enough for
# a square overmould and square top corners (check_fit.py). It runs on up through the top of the wall as a notch,
# USB_LEDGE wider on each side: JLC's C165948 puts the socket face 0.52 past the board edge, level with the cavity
# wall, so a solid wall above the opening would stop the socket while the board is lowered in. Where the notch
# widens, the wall under it ends in two flat ledges level with the opening's top, for the filler below.
USB_OPEN = dict(w=15.8, h=8.4, r=0.5, z=-S.PCB_T - 1.6)   # z: centre, on the socket's middle; bottom at -7.4
USB_LEDGE = 2.5                     # ledge per side: the notch is 20.8 wide
USB_NOTCH_W = USB_OPEN["w"] + 2 * USB_LEDGE
USB_TOP = USB_OPEN["z"] + USB_OPEN["h"] / 2               # 1.0: the opening's top, the ledges
# solid down to the desk plane under the USB-C opening, 0.8 wider than it on each side: no thin floor between the
# opening and the hollow
USB_KEEP = (USB_OPEN["w"] + 1.6, 3.0)   # width, board y up to which the floor stays solid
J1_FACE = -0.52                     # socket face, board y (2.62 ahead of its front shell tabs at 2.10)
J1_BODY = (8.94, 3.26)              # socket width and height under the PCB (HRO TYPE-C-31-M-12)
# J1's front shell tabs come up through the board at y 2.10 (board.add_usb), their pads from y 1.2; the solder
# fillets on top may spread a little past the pad, so the filler stays short of y 1.0
J1_TABS_IN = 1.0
# Filler for the notch above the USB-C opening, printed with the body (MJF PA12, black). It goes in from the back
# once the body is on, the panel face up, and rests on the two ledges: its bottom is the opening's top edge, set
# by the body like the rest of the opening, and it spans the opening, so it cannot drop into the plug's path. A
# feeler gauge blade laid across the back wall pushes it flush. Nothing in the wall can stop it moving inward: a
# lip wider than the notch does not go in from outside, and a step in the notch would leave body walls under
# JLC3DP's 2.0.
# Friction on the ledges holds it against the 6 degree slope (check_fit.py), and a dab of removable adhesive putty
# (Blu Tack) on each side face holds it in use; the side gap leaves room for the putty at both MJF extremes. Not
# glue: it has to come out before the body goes back on the board (it would stop the socket on the way in), and
# press-fit ribs cannot hold over MJF's +-0.3 on both the notch and the filler (a 1.2 mm window).
# w: the notch less the putty gap on each side; d: the wall; h: from the ledges to 1.15 under the plate back, so it
# stays under it on the highest ledges; cham: lead-in on its inner vertical edges.
USB_FILLER_GAP = 0.55
USB_FILLER = dict(w=USB_NOTCH_W - 2 * USB_FILLER_GAP, d=WALL, h=3.85, cham=0.3)


def usb_cutter():
    """USB-C plug opening in the back wall (y = 0 side), carried up through the top of the wall as the wider
    notch: its top corners square, the ledges level with its top."""
    u = USB_OPEN
    sh = rrect_prism(B.USB_X, u["z"], u["w"], u["h"], u["r"], 0, o + 3)   # built in XY with the depth along Z
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2)   # (x, y, z) -> (x, -z, y)
    sh = BRepBuilderAPI_Transform(sh, t, True).Shape()
    top = box(B.USB_X - u["w"] / 2, -o - 2, u["z"], B.USB_X + u["w"] / 2, 1.0, USB_TOP + 0.01)   # square top corners
    notch = box(B.USB_X - USB_NOTCH_W / 2, -o - 2, USB_TOP, B.USB_X + USB_NOTCH_W / 2, 1.0, S.PLATE_Z0)
    return fuse(fuse(move(sh, dy=1.0), top), notch)          # from y = 1 (inside the PCB edge) out through the wall


def usb_filler():
    """the notch filler in its place (board frame): flush with the back wall, on the ledges."""
    f = USB_FILLER
    x0, x1, y0, y1, c = B.USB_X - f["w"] / 2, B.USB_X + f["w"] / 2, -o, -o + f["d"], f["cham"]
    poly = BRepBuilderAPI_MakePolygon()
    for x, y in ((x0, y0), (x1, y0), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c)):
        poly.Add(gp_Pnt(x, y, USB_TOP))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, f["h"])).Shape()


def body():
    cx, cy = B.W / 2, B.H / 2
    outer = rrect_prism(cx, cy, B.W + 2 * o, B.H + 2 * o, B.CORNER_R + o, -40, S.PLATE_Z0 - S.WALL_GAP)
    cav = rrect_prism(cx, cy, B.W + 2 * CLEAR, B.H + 2 * CLEAR, B.CORNER_R + CLEAR, Z_FLOOR_TOP, S.PLATE_Z0 + 1)
    shell = cut(outer, cav)
    inside = rrect_prism(cx, cy, B.W + 2 * CLEAR + 0.2, B.H + 2 * CLEAR + 0.2, B.CORNER_R + CLEAR + 0.1, -41, 0)
    for (mx, my) in B.MOUNTS:      # wide below the counterbore seat, BOSS_R above it; joined to the walls up to -1.8
        shell = fuse(shell, common(corner(mx, my, BOSS_R_LOW, Z_FLOOR_TOP - 0.1, S.SEAT_Z), inside))
        shell = fuse(shell, common(corner(mx, my, BOSS_R, S.SEAT_Z - 0.1, -S.PCB_T - 0.2), inside))
        shell = fuse(shell, cyl(BOSS_R, S.SEAT_Z - 0.1, -S.PCB_T, mx, my))
    for (px, py) in SUPPORTS:          # just under the PCB: a firm press in the middle bends it onto them
        shell = fuse(shell, cyl(SUPPORT_R, Z_FLOOR_TOP - 0.5, SUPPORT_TOP, px, py))
    holes = [wedge_cutter(), hollow(), steel_recess(), usb_cutter(), cyl(BOOT_HOLE / 2, -41, 0, *B.BOOT)]
    for (mx, my) in B.MOUNTS:
        holes += [cyl(SCREW_CLEAR, -41, 0, mx, my), cyl(HEAD_R, -41, S.SEAT_Z, mx, my)]
    return cut(shell, *holes)


def to_output(shape):
    m = gp_Trsf(); m.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)))   # board y (towards the user) -> -Y
    return BRepBuilderAPI_Transform(shape, m, True).Shape()


def steel_outline():
    """outline of the optional steel plate, mm, origin at its front-left corner, y towards the back."""
    st = STEEL
    w, d, n = st["w"], st["d"], st["notch"]
    return [(0, 0), (w, 0), (w, d - n), (w - n, d - n), (w - n, d), (n, d), (n, d - n), (0, d - n)]


if __name__ == "__main__":
    b = body()
    print(f"body {volume(b) / 1000:.1f} cm3 (PA12 about {volume(b) * 1.01e-3:.0f} g); hollow up to board y "
          f"{hollow_front()}; screw hole {2 * SCREW_CLEAR:.1f}, counterbore {2 * HEAD_R:.1f}; optional steel plate "
          f"{STEEL['w']:.0f} x {STEEL['d']:.0f} x {STEEL['t']:.0f} mm (recess {STEEL_RECESS[0]:.0f} x "
          f"{STEEL_RECESS[1]:.0f}) less two {STEEL['notch']:.0f} mm corner "
          f"notches, {steel_mass():.0f} g")
    export(to_output(b), "avionics-panel-rev1-body", deflection=0.02)
    f = USB_FILLER
    print(f"USB-C filler {f['w']:g} x {f['d']:g} x {f['h']:g} mm")
    export(to_output(usb_filler()), "avionics-panel-rev1-usb-filler")
    write_dxf("avionics-panel-rev1-steel.dxf", {"CUT": [steel_outline()]})   # for a laser-cutting service
