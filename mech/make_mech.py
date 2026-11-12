"""Body for the Avionics Panel rev 1, exact solid (OpenCascade) -> STEP + STL for JLC3DP.

The 6 degree wedge is part of the body, so no wedge feet are needed; four flat silicone feet only stop it
sliding; they go on four flat pads. The wedge is hollow from below: a 2 mm floor under the PCB, ribs down to
the desk plane (under the PCB post and the middle screw's column, and between them), the corner screw bosses joined
to the walls and a solid band along the front.
BOOT hole in the floor, USB-C opening in the back wall, open to the top as a slot of the same width so the socket
clears the wall when the body goes on; the plate's tongue (stack.USB_TONGUE) fills the slot from above. The front
plate is CNC aluminium (make_plate_step.py); every height is in stack.py.

Stack (z = 0 is the PCB top):
  body     floor -7.6 .. -5.6 (-7.2 .. -5.6 at the front edge), bottom plane from -7.2 at the front to about
           -14 at the back, walls up to z 5.6 (0.95 below the plate), 5 bosses carry the PCB at z -1.6 (4 mm
           room for the SMD parts and the USB-C socket on the underside): four in the corners and one on a
           bar-shaped column under the middle of the key field; a post 0.3 under the PCB between key columns
           4 and 5, counterbore seats at z -3.2 (1.6 mm of PA12 up to the PCB)
  plate    6061 from 12 mm stock: the 4 mm web at z 6.55 .. 10.55 and 5 bosses dia 5.5 down to the PCB top,
           tapped M3
  screws   5 x M3 x 8 flanged button head (ISO 7380-2) from below, no washer: body boss -> PCB -> plate boss
Height 17.75 mm at the front, rising to about 24.6 mm at the back.
Output frame: X right, Y away from the user (board y flipped), Z up.
"""
import math
import sys

from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf

sys.path.insert(0, "../pcb")
import board as B
import stack as S
from occ_util import box, common, cut, cyl, export, fuse, move, prism, rrect_prism, volume

# PCB to cavity wall: the cavity (161.0 x 61.0) may print 0.4 % small (JLC3DP MJF) and the routed board outline
# is +-0.2 (JLCPCB), so 0.5 per side; walls 2.0 (JLC3DP MJF: 2.0 for parts over 100 mm), so the outline
# (stack.OVH, shared with the plate) is 2.5 out from the PCB. Edge rails (docs/building/ordering.md):
# Standard assembly (70 x 70 mm minimum) puts one rail on the long edge away from J1, V-cut (stack.PCB_VCUT_TOL
# on the board width); the other three edges are routed.
CLEAR, WALL = 0.5, 2.0
if abs(CLEAR + WALL - S.OVH) > 1e-9:
    raise ValueError("the body outline must be the plate outline")
UNDER = 4.0                         # room under the PCB: SMD parts, USB-C socket (3.2 mm), THT leads (stack.LEAD_MAX)
FLOOR = 2.0                         # floor under the PCB room; the wedge below it is hollow
FRONT = 1.6                         # body under the floor top at the front edge
Z_FLOOR_TOP = -S.PCB_T - UNDER      # -5.6
Z_FLOOR_BOT = Z_FLOOR_TOP - FLOOR   # -7.6: hollow from the bottom plane up to here
Z_BOT = Z_FLOOR_TOP - FRONT         # -7.2 at the front edge
SLOPE = math.tan(math.radians(S.BODY_TILT))


def _up(v):
    return math.ceil(round(v * 20, 6)) / 20


# The body locates nothing. Its screw holes (four corners and the middle, all alike) are as small as pass the screw
# wherever the body's MJF tolerance over 153 mm and the plate's tapped bosses (the screws sit in them) put it
# (stack.POS_TOL), so the screw's flange
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
JOIN_SHORT = 0.2                    # the blocks from a boss to the walls and the middle bar end this far under the PCB
BOOT_HOLE = 5.0                     # bridge the BOOT pads with a small screwdriver
# The hollow stops where it is 1 mm high: in front of that the floor is solid down to the desk plane (BOOT hole
# and front feet). No slot or sliver under 0.8 mm anywhere: check_fit.py rasterises sections to prove it.
HOLLOW_H_MIN = 1.0
# The PCB is screwed down at its corners (about 153 mm apart) and at the middle mount (board.MID_MOUNT), between
# the AUTOPILOT and AUDIO blocks. The column there is not round like the corner bosses: the leads of the four keys
# round it stand 5.3 mm off its axis in x and reach below the counterbore seat, so it is a bar along board y,
# stack.MID_BAR["w"] wide and as long as a corner boss (BOSS_R_LOW each way), from the floor up to 0.2 under the
# PCB, with the corners' round boss (BOSS_R) on top and their counterbore and screw hole through it. The
# counterbore is wider than the bar, so it is open to the PCB room on the bar's two long sides, from the floor up
# to the seat; the bar's two ends carry the boss. An arm towards +x would reach the pull-up R_PU3. check_fit.py
# holds the column against the leads, their solder fillets and the bottom-side parts.
# One post backs the board between key columns 4 and 5, midway between rows 1 and 2 (counted from 0, as in
# board.py). Its place and size are set by what hangs under the board round it: the leads of the keys K14, K15,
# K24 and K25 (their pads 5.5 mm from its axis) and the pull-up R_PU5 (its body 4.55 mm from the axis), each of
# which may come 1.84 mm closer at the worst offsets (check_fit.py). It ends stack.SUPPORT_SHORT under the PCB, so
# the MJF tolerance cannot bow the board up towards the light pipes.
SUPPORTS = [(98.3, 30.75)]
SUPPORT_R = 2.0
SUPPORT_TOP = -S.PCB_T - S.SUPPORT_SHORT
# ribs in the hollow wedge, down to the bottom plane (board coordinates): front to back under the middle column
# and the post and between the knobs and key blocks, one across through the middle column; 2.0 thick (JLC3DP MJF,
# parts over 100 mm). Under the floor the middle column is a round sleeve (BOSS_R_LOW) on the crossing of two ribs.
RIB_T = 2.0
RIBS_X = (36.0, B.MID_MOUNT[0], SUPPORTS[0][0], 125.0)   # 125 stays clear of the BOOT hole (x 132.1)
RIBS_Y = (B.MID_MOUNT[1],)
# flat pads for four self-adhesive feet up to 10 mm across (pads 12 mm), wide apart
FOOT_D, FOOT_PAD = 10.0, 12.0
FEET = [(15.5, 6.7), (B.W - 15.5, 6.7), (15.5, 55.5), (B.W - 15.5, 55.5)]
o = CLEAR + WALL


def wedge_cutter():
    """everything below the 6 degree bottom plane (z_bottom)."""
    y0, y1 = -o - 2, B.H + o + 2
    return prism([(-o - 2, y, z) for y, z in ((y0, z_bottom(y0)), (y1, z_bottom(y1)), (y1, -40), (y0, -40))],
                 dx=B.W + 2 * o + 4)


def z_bottom(y):
    """the 6 degree bottom plane at board y."""
    return Z_BOT - SLOPE * ((B.H + o) - y)


def hollow_front():
    """board y where the hollow under the floor is HOLLOW_H_MIN high; in front of it the body is solid."""
    return math.floor(((B.H + o) - (Z_BOT - Z_FLOOR_BOT + HOLLOW_H_MIN) / SLOPE) * 10) / 10


def corner_plan(mx, my, r):
    """plan of a corner boss of radius r joined to the two walls of its corner: two rectangles (x0, y0, x1, y1)
    that run out through the walls, and the disc (x, y, r)."""
    sx, sy = (-1 if mx < B.W / 2 else 1), (-1 if my < B.H / 2 else 1)
    far = o + 10
    a = (min(mx + sx * far, mx - sx * r), min(my + sy * far, my),
         max(mx + sx * far, mx - sx * r), max(my + sy * far, my))
    b = (min(mx + sx * far, mx), min(my + sy * far, my - sy * r),
         max(mx + sx * far, mx), max(my + sy * far, my - sy * r))
    return a, b, (mx, my, r)


def corner(mx, my, r, z0, z1):
    """a boss of radius r joined to the two walls of its corner: no slot between boss and wall."""
    a, b, _ = corner_plan(mx, my, r)
    return fuse(fuse(box(a[0], a[1], z0, a[2], a[3], z1), box(b[0], b[1], z0, b[2], b[3], z1)),
                cyl(r, z0, z1, mx, my))


def foot_bridges():
    """(x0, y0, x1, y1) of the blocks that join a foot pad to the boss next to it and to the wall behind both,
    so no slot narrower than 0.8 mm is left between them (the bosses round the counterbores reach close)."""
    out = []
    for fx, fy in FEET:
        mx, my = min(B.CORNER_MOUNTS, key=lambda m: math.hypot(m[0] - fx, m[1] - fy))
        if math.hypot(mx - fx, my - fy) < BOSS_R_LOW + FOOT_PAD / 2 + 2.0:
            sy, r = (-1 if my < B.H / 2 else 1), min(BOSS_R_LOW, FOOT_PAD / 2)
            wall = B.H / 2 + sy * (B.H / 2 + o + 1)
            out.append((min(mx, fx), min(fy - sy * r, wall), max(mx, fx), max(fy - sy * r, wall)))
    return out


def hollow():
    """the wedge under the floor, inside the walls and behind the solid front band, less ribs, bosses, the middle
    column's sleeve and pads."""
    cx, cy = B.W / 2, B.H / 2
    h = rrect_prism(cx, cy, B.W + 2 * CLEAR, B.H + 2 * CLEAR, B.CORNER_R + CLEAR, -40, Z_FLOOR_BOT)
    h = cut(h, box(-o - 1, hollow_front(), -41, B.W + o + 1, B.H + o + 1, 0))
    keep = [box(x - RIB_T / 2, -o - 1, -41, x + RIB_T / 2, B.H + o + 1, 0) for x in RIBS_X]
    keep += [box(-o - 1, y - RIB_T / 2, -41, B.W + o + 1, y + RIB_T / 2, 0) for y in RIBS_Y]
    keep += [corner(mx, my, BOSS_R_LOW, -41, 0) for (mx, my) in B.CORNER_MOUNTS]
    keep += [cyl(BOSS_R_LOW, -41, 0, *B.MID_MOUNT)]
    keep += [cyl(FOOT_PAD / 2, -41, 0, fx, fy) for (fx, fy) in FEET]
    keep += [box(x0, y0, -41, x1, y1, 0) for x0, y0, x1, y1 in foot_bridges()]
    keep += [box(B.USB_X - USB_KEEP[0] / 2, -o - 1, -41, B.USB_X + USB_KEEP[0] / 2, USB_KEEP[1], 0)]
    return cut(h, *keep)


# USB-C opening in the back wall round the plug overmould (USB_PLUG): wide enough for the board anywhere in the
# cavity (its sideways play set by the short edges, taken as V-cut: one up to 0.4 short), the opening where MJF puts
# it against the cavity wall (+-0.51 over the 127.5 mm from the left wall) and J1's placement, high enough for the
# body's height tolerance under the bosses, with bottom corners small enough for a square overmould (check_fit.py).
# It runs on up through the top of the wall as a slot of the same width: JLC's C165948 puts the socket face 0.52
# past the board edge, level with the cavity wall, so a solid wall above the opening would stop the socket while the
# body goes on. The plate's tongue (stack.USB_TONGUE) hangs into the slot and is the opening's top edge.
# z: the middle of the socket; h: from the bottom at -7.4 up to 1.0, where the tongue ends on the lowest plate.
USB_OPEN = dict(w=16.2, h=8.4, r=0.5, z=-S.PCB_T - 1.6)
USB_PLUG = (12.35, 6.5)             # USB-C spec: the plug's overmould, at most (width, height)
# solid down to the desk plane under the USB-C opening, 0.8 wider than it on each side: no thin floor between the
# opening and the hollow
USB_KEEP = (USB_OPEN["w"] + 1.6, 3.0)   # width, board y up to which the floor stays solid
J1_H = 3.26                         # socket height under the PCB (HRO TYPE-C-31-M-12); its plan is board.J1_BODY
# J1's front shell tabs come up through the board at y 2.10 (board.add_usb), their pads from y 1.2; the solder
# fillets on top may spread a little past the pad, so the plate's tongue stays short of y 1.0 (check_fit.py)
J1_TABS_IN = 1.0


def usb_cutter():
    """USB-C plug opening in the back wall (y = 0 side), carried up through the top of the wall as a slot of the
    same width for the plate's tongue."""
    u = USB_OPEN
    sh = rrect_prism(B.USB_X, u["z"], u["w"], u["h"], u["r"], 0, o + 3)   # built in XY with the depth along Z
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2)   # (x, y, z) -> (x, -z, y)
    sh = BRepBuilderAPI_Transform(sh, t, True).Shape()
    slot = box(B.USB_X - u["w"] / 2, -o - 2, u["z"], B.USB_X + u["w"] / 2, S.USB_OPEN_IN, S.PLATE_Z0)
    return fuse(move(sh, dy=S.USB_OPEN_IN), slot)            # from inside the PCB edge out through the wall


def body():
    cx, cy = B.W / 2, B.H / 2
    outer = rrect_prism(cx, cy, B.W + 2 * o, B.H + 2 * o, B.CORNER_R + o, -40, S.PLATE_Z0 - S.WALL_GAP)
    cav = rrect_prism(cx, cy, B.W + 2 * CLEAR, B.H + 2 * CLEAR, B.CORNER_R + CLEAR, Z_FLOOR_TOP, S.PLATE_Z0 + 1)
    shell = cut(outer, cav)
    inside = rrect_prism(cx, cy, B.W + 2 * CLEAR + 0.2, B.H + 2 * CLEAR + 0.2, B.CORNER_R + CLEAR + 0.1, -41, 0)
    for (mx, my) in B.CORNER_MOUNTS:   # wide below the counterbore seat, BOSS_R above it; joined to the walls to -1.8
        shell = fuse(shell, common(corner(mx, my, BOSS_R_LOW, Z_FLOOR_TOP - 0.1, S.SEAT_Z), inside))
        shell = fuse(shell, common(corner(mx, my, BOSS_R, S.SEAT_Z - 0.1, -S.PCB_T - JOIN_SHORT), inside))
    # the middle column: the bar from the floor to 0.2 under the PCB (like the corners' joined part), the boss on it
    mx, my = B.MID_MOUNT
    hw = S.MID_BAR["w"] / 2
    shell = fuse(shell, box(mx - hw, my - BOSS_R_LOW, Z_FLOOR_TOP - 0.1, mx + hw, my + BOSS_R_LOW,
                            -S.PCB_T - JOIN_SHORT))
    for (mx, my) in B.MOUNTS:          # the round boss that bears on the PCB, at all five
        shell = fuse(shell, cyl(BOSS_R, S.SEAT_Z - 0.1, -S.PCB_T, mx, my))
    for (px, py) in SUPPORTS:          # just under the PCB: a backstop for a press beside the middle column
        shell = fuse(shell, cyl(SUPPORT_R, Z_FLOOR_TOP - 0.5, SUPPORT_TOP, px, py))
    holes = [wedge_cutter(), hollow(), usb_cutter(), cyl(BOOT_HOLE / 2, -41, 0, *B.BOOT)]
    for (mx, my) in B.MOUNTS:          # all five: the screw hole, and the counterbore from below up to the seat
        holes += [cyl(SCREW_CLEAR, -41, 0, mx, my), cyl(HEAD_R, -41, S.SEAT_Z, mx, my)]
    return cut(shell, *holes)


def to_output(shape):
    m = gp_Trsf(); m.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)))   # board y (towards the user) -> -Y
    return BRepBuilderAPI_Transform(shape, m, True).Shape()


if __name__ == "__main__":
    b = body()
    print(f"body {volume(b) / 1000:.1f} cm3 (PA12 about {volume(b) * 1.01e-3:.0f} g); hollow up to board y "
          f"{hollow_front()}; screw hole {2 * SCREW_CLEAR:.1f}, counterbore {2 * HEAD_R:.1f}")
    export(to_output(b), "avionics-panel-rev1-body", stl=0.02)
