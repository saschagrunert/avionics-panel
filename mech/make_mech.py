"""Body and spacers for the Avionics Panel rev 1, exact solids (OpenCascade) -> STEP + STL for JLC3DP.

The 6 degree wedge is part of the body floor (no stick-on feet). BOOT hole in the floor, USB-C opening
in the back wall. The front plate is CNC aluminium (make_plate_step.py); every height is in stack.py.

Stack (z = 0 is the PCB top):
  body   floor -7.2 .. -5.6 at the front, walls up to z 6.7 (0.3 below the plate), 4 bosses carry the PCB at
         z -1.6 (4 mm room for the SMD parts and the USB-C socket on the underside), 2 posts support
         the middle of the PCB
  spacer 4 printed tubes, 7 mm, between the PCB top and the plate
  plate  3 mm aluminium, z 7 .. 10, blind M2.5 threads from below
  screws 4 x M2.5 x 12 from below: body boss -> PCB mounting hole -> spacer -> plate
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
from make_plate_step import rrect_prism  # noqa: E402
from occ_util import cut, cyl, export, fuse, move  # noqa: E402

CLEAR, WALL = 0.3, 2.0
UNDER = 4.0                         # room under the PCB: SMD parts, USB-C socket (3.2 mm), THT leads
FLOOR = 1.6
Z_FLOOR_TOP = -S.PCB_T - UNDER      # -5.6
Z_BOT = Z_FLOOR_TOP - FLOOR         # -7.2 at the front edge
SLOPE = math.tan(math.radians(6.0))
SCREW_CLEAR, HEAD_R, BOSS_R = 1.45, 2.8, 3.6   # M2.5 clearance, pan or socket head up to 5 mm; 0.8 mm MJF wall,
                                                # boss within the 3.6 mm routing keep-out around the mounting holes
BOOT_HOLE = 5.0                     # bridge the BOOT pads with a small screwdriver
# The PCB is held only at its corners (about 153 mm apart) and would sag 0.3 to 0.5 mm under a key press in
# the middle, about the switch travel. Two posts carry it there, at spots free of bottom parts and pins:
# between the AUTOPILOT and AUDIO blocks, and between key columns 4 and 5, midway between rows 1 and 2.
SUPPORTS = [(72.3, 30.8), (98.6, 30.8)]
SUPPORT_R = 2.5
o = CLEAR + WALL


def wedge_cutter():
    """everything below the 6 degree floor plane: z_bot(y) = Z_BOT - SLOPE * ((H + o) - y), board y."""
    y0, y1 = -o - 2, B.H + o + 2
    zb = lambda y: Z_BOT - SLOPE * ((B.H + o) - y)
    poly = BRepBuilderAPI_MakePolygon()
    for y, z in ((y0, zb(y0)), (y1, zb(y1)), (y1, -40), (y0, -40)):
        poly.Add(gp_Pnt(-o - 2, y, z))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(B.W + 2 * o + 4, 0, 0)).Shape()


def usb_cutter():
    """USB-C plug opening in the back wall (y = 0 side), plug overmould up to 12 x 6.5 mm."""
    uz = -S.PCB_T - 1.6
    sh = rrect_prism(B.USB_X, uz, 12.8, 7.2, 2.0, 0, o + 3)   # built in XY with the depth along Z
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2)   # (x, y, z) -> (x, -z, y)
    sh = BRepBuilderAPI_Transform(sh, t, True).Shape()
    return move(sh, dy=1.0)                                  # from y = 1 (inside the PCB edge) out through the wall


def body():
    cx, cy = B.W / 2, B.H / 2
    outer = rrect_prism(cx, cy, B.W + 2 * o, B.H + 2 * o, B.CORNER_R + o, -40, S.PLATE_Z0 - S.WALL_GAP)
    cav = rrect_prism(cx, cy, B.W + 2 * CLEAR, B.H + 2 * CLEAR, B.CORNER_R + CLEAR, Z_FLOOR_TOP, S.PLATE_Z0 + 1)
    shell = cut(outer, cav)
    for (mx, my) in B.MOUNTS:
        shell = fuse(shell, cyl(BOSS_R, -40, -S.PCB_T, mx, my))
    for (px, py) in SUPPORTS:          # just touch the PCB underside: the middle keys must not flex the board
        shell = fuse(shell, cyl(SUPPORT_R, Z_FLOOR_TOP - 0.5, -S.PCB_T, px, py))
    holes = [wedge_cutter(), usb_cutter(), cyl(BOOT_HOLE / 2, -41, 0, *B.BOOT)]
    for (mx, my) in B.MOUNTS:
        holes += [cyl(SCREW_CLEAR, -41, 0, mx, my), cyl(HEAD_R, -41, S.SCREW_HEAD_Z, mx, my)]
    return cut(shell, *holes)


def to_output(shape):
    m = gp_Trsf(); m.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)))   # board y (towards the user) -> -Y
    return BRepBuilderAPI_Transform(shape, m, True).Shape()


def spacer():
    sp = S.SPACER
    return cut(cyl(sp["od"] / 2, 0, sp["length"]), cyl(sp["id"] / 2, -1, sp["length"] + 1))


if __name__ == "__main__":
    export(to_output(body()), "avionics-panel-rev1-body", deflection=0.02)
    export(spacer(), "avionics-panel-rev1-spacer")
