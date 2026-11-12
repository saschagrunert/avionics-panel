"""Mechanical stack of the Avionics Panel rev 1: one place for every height and fit, the legends and the layout
of the artwork.

z = 0 is the PCB top. Part heights from the datasheets:
  Bourns PEC11D-4120F-S0015 (dual encoder): body 8 mm (11.7 x 12, 13.1 over the side lugs), unthreaded
      bushing dia 7 up to 13, outer shaft dia 6 with a 2 mm slot 2.5 deep up to 18, inner shaft dia 3.5 up to
      28 with a D flat (2.5 across) on its last 7 mm. The inner shaft pushes (stroke 0.5 +0/-0.3). Tolerances
      +-0.3 under 10 mm, +-0.5 from 10 mm.
  Alps RKJXT1F42001 (RANGE): octagonal body 8.6 high, 16.4 across corners and 15.73 across flats above z 4
      (Alps' STEP model; it stands on a round foot dia 13.5, and the 17.2 mm base frame from z 0.40 to 2.55
      stays under the plate), hub dia 7.2 up to 10.0
      (chamfered to 10.5), lever dia 2.5 with a 1.8 D flat from 12.4 to 17.4, tilts 9 degrees about a fulcrum
      5.55 above the PCB and 4.65 off the axis, push stroke 0.3 +-0.2.
  TE 1-1825910-4 keys (FSM8JH, 6 x 6 mm): plunger top at 9.5, switch body top 5.90 below it, a round plunger
      that tapers about 2 degrees per side (TE's STEP model, see PLUNGER).

Front plate: milled from 12 mm 6061 stock: the 4 mm web at z 6.55..10.55, pockets milled from below for the encoder
and RANGE bodies, five round bosses on its back (at the four corner mounts and in the middle of the key field) that
stand down to the PCB top, each tapped M3 from its end face, and a tongue on its back edge that closes the body's slot
over the USB-C socket (USB_TONGUE); nothing on the front. Five M3 x 8 flanged button-head screws (ISO 7380-2) come
from under the body: body boss -> PCB -> plate boss thread, no washers, no glue. The bosses alone set the plate height
(BOSS), the body walls stop WALL_GAP short of the plate.
"""
# datasheet values the generators share
# TE 1-1825910-4 key plunger, from TE's own STEP model of the part (dz below the plunger top): a flat top of
# radius 1.26 with a 0.3 edge radius, dia 3.12 at dz 0.29, then a cone (about 2 degrees per side) to dia 3.51
# at the switch body top (dz 5.90; the PCB is at dz 9.50). TE's customer drawing (1825910 rev C10) gives the
# plunger 3.10 at the tip and 3.51 at the base, 9.50 high, under its general tolerance of +-0.30 on two-place sizes.
PLUNGER_TOP = 9.5                          # above the PCB
PLUNGER = dict(top_r=1.26, edge_r=0.3, dz0=0.29, d0=3.12, dz1=5.90, d1=3.51)
PLUNGER_TOP_TOL = 0.3                      # plunger height (TE drawing: 9.50 +-0.30)
SWITCH_BODY_TOP = PLUNGER_TOP - PLUNGER["dz1"]   # 3.6
SWITCH_BODY = 6.0                          # square body across (TE 1-1825910-4: 6 x 6 mm), for the light pipe rows


def plunger_d(dz):
    """plunger diameter dz below its top, on the cone (dz from 0.29 down to the switch body, 5.90)."""
    p = PLUNGER
    return p["d0"] + (p["d1"] - p["d0"]) * (dz - p["dz0"]) / (p["dz1"] - p["dz0"])


KEY_TRAVEL = 0.45                          # TE 1-1825910-4 travel 0.25 +0.20/-0.10 (drawing)
RKJXT_BODY, RKJXT_HUB_TOP, RKJXT_TILT = 8.6, 10.5, 9.0   # Alps RKJXT1F42001: body and hub top, tilt (deg)
RKJXT_FULCRUM = 5.55                       # Alps RKJXT1F42001: tilt fulcrum above the PCB (datasheet)
# and off the lever axis (datasheet). Alps' drawing marks it on the side the lever tilts away from, which fits the
# centre contact closing on every tilt (the lever's foot goes down, 4.65 sin 9 deg = 0.73); Alps' formal
# specification is not public, so check_fit.py takes the worse of both sides for every RANGE row.
RKJXT_FULCRUM_OFF = 4.65
RKJXT_HUB = (7.2, 10.0)                    # Alps' STEP model: hub dia and the top of its full width (chamfer above)
RANGE_PUSH = (0.3, 0.2)                    # Alps RKJXT1F42001 push stroke 0.3 +-0.2
LEVER_TOL = 0.3                            # Alps RKJXT1F42001 lever height, +-
BODY_TILT = 6.0                            # body wedge (deg)
# key cap: outline, height and top chamfer; it sits with its socket ceiling on the plunger top and the socket
# is 2.7 deep, so its bottom is at 6.8. A cap pressed firmly (travel up to 0.45, plunger up to 0.3 low, the board
# bent by PRESS_DIP) can dip under the plate back; the bent board tilts it with its plunger (PRESS_SLOPE), so a cap
# at the edge of its per-key allowance may rub the face edge of its hole on one side. check_fit.py proves that it
# cannot wedge across the hole and that its bottom edge comes back over the back edge, which is broken by
# KEY_BACK_BREAK at least (drawing)
CAP = dict(w=9.6, h=6.4, r=1.2, height=5.7, cham=0.45, base=PLUNGER_TOP - 2.7)
# tactile bars on SHIFT, DN (front edge) and UP (back edge): closed box 1.0 wide (JLC3DP embossed detail: 0.8),
# sunk 0.05 into the top, its outer side 0.1 inside the top face. Only 0.5 proud, below JLC3DP's 0.8 for
# embossed detail (a solid 3.2 x 1.0 ridge, not fine detail): a taller front bar hides the bottom of the SHIFT
# and DN legends from the seat; check_fit.py proves it hides none at 45 deg (a review question,
# docs/building/ordering.md)
CAP_BAR = dict(w=3.2, d=1.0, proud=0.5, sink=0.05, inset=0.6)
# seated eye over the cap tops: about 42 deg over a desk plus the 6 deg wedge, 48 deg over the plate; 45 is the
# conservative value, since a flatter sightline lets the front bar hide more of the legend
CAP_VIEW_DEG = 45.0
# Cap legends (make_caps.py, the 3D view): Barlow Semi Condensed Bold (its thinnest strokes, the horizontal
# bars, are 0.121 em), grown all round by LEGEND_GROW mm, so every stroke prints at least 0.4 mm wide (JLC3DP
# full colour: coloured lines 0.4 mm min.); the D-> arrow and the flip-flop icon have lines LEGEND_LINE em wide
# before the growth. check_fit.py measures the strokes on the generated texture.
LEGEND_WEIGHT, LEGEND_GROW, LEGEND_LINE = 700, 0.055, 0.12
LEGEND_STROKE_MIN = 0.4
# One legend size for every cap: the widest legend, grown, fills LEGEND_FILL of the cap top's width, and the em is
# LEGEND_EM_MAX at most (mm).
LEGEND_EM_MAX, LEGEND_FILL = 3.1, 0.84
# The direct-to arrow through the D of the "D→" cap (em): it ends `w` right of the D; its line runs `dy` over the
# middle of the capitals, from `tail` left of the D to `neck` short of the tip; its head is `head` long and `head_h`
# high each way.
DIRECT_TO = dict(w=0.55, dy=0.02, tail=0.12, neck=0.2, head=0.26, head_h=0.17)
# Key cap socket for the full-colour resin (JLC3DP WJP: walls 1.0 mm min., pillars 1.0 mm no taller than 2.0,
# holes and gaps 1.0 min., +-0.2 on the outline and on holes, WJP_TOL). A 3.8 mm bore (1.3 mm wall at the narrow
# cap sides, 1.1 on a print with the outline 0.2 small and the bore 0.2 large; nothing open to the outside;
# 0.15 radial left round the plunger in a bore 0.2 small) with four rigid ribs 1.2 wide along its wall,
# attached over their full length. Each rib follows the plunger's cone, so it touches the plunger over its
# whole length and the cap cannot rock; the ribs stop `relief` below the ceiling, clear of the plunger's
# rounded top edge, so the flat ceiling sits on the plunger's flat top and sets the cap height, not the fit.
# A 0.3 mm lead-in at the mouth (0.2 radial) starts the cap straight.
CAP_SOCKET = dict(d=3.8, rib_w=1.2, rib_angles=(0, 90, 180, 270), relief=0.35, lead=0.3, lead_r=0.2,
                  depth=PLUNGER_TOP - CAP["base"])
# A rigid friction fit works over a window of about 0.13 mm (CAP_GRIP), but JLC3DP prints holes in the full-colour
# resin within +-0.2 (WJP_TOL, CAP_PRINT). So the caps come in four full sets that
# differ only in their rib circle, given here at the socket mouth (2.7 below the plunger top, where the plunger
# is 3.29): set D grips a print whose rib circle comes out 0.09 to 0.22 large, A 0.01 small to 0.12 large, B
# 0.11 small to 0.02 large, C 0.21 to 0.08 small (CAP_GRIP). The set that seats fully and holds is the one
# to fit. Each set's caps carry 1 to 4 dimples (CAP_MARK, A 1 ... D 4) on the underside, inside the key hole
# where they never show. The sets take a plunger off TE's model by as much, together with the print: TE's drawing
# allows +-0.30 on its diameter, so a plunger lot at the edge of that needs the sets moved
# (docs/architecture/mechanics.md).
# One compliant set cannot replace them in a 9.6 x 6.4 cap: springs that grip over the drawing's 0.6 and the print's
# 0.4 deflect up to 0.55 each, and two of them, one printed 0.1 thin and one 0.1 thick, hold the cap up to 0.18 off
# its plunger, twice the 0.09 the key hole leaves for that.
# A reprint for a plunger lot off TE's model moves every set by CAP_SETS_MOVE, 0.1 per set it missed by, up to
# TE's +-0.30 on the plunger diameter (docs/building/bring-up.md); check_fit.py takes the plunger that far off.
CAP_SETS_MOVE = 0.0
CAP_SETS = {n: d + CAP_SETS_MOVE for n, d in {"A": 3.15, "B": 3.25, "C": 3.35, "D": 3.05}.items()}
CAP_GRIP = (0.02, 0.15)                    # diametral interference: holds from, still seats by hand up to
# Dimples 1.0 across (WJP holes 1.0 min.) and 0.9 deep (engraved detail 0.8 min.), one in each corner region
# between the socket and the outline, where the cap is thickest: set A uses the first, D all four.
CAP_MARK = dict(d=1.0, depth=0.9, pos=((-3.19, -1.59), (-3.19, 1.59), (3.19, 1.59), (3.19, -1.59)))


def cap_rib_d(name, dz):
    """rib circle diameter of cap set `name` dz below the plunger top (the cone shifted to the set's size)."""
    return plunger_d(dz) + CAP_SETS[name] - plunger_d(CAP_SOCKET["depth"])


PCB_T = 1.6
# The 4 mm web of the 6061 plate. Its back face stands PLATE_Z0 over the PCB top, on the bosses milled with it: their
# height is this one number (BOSS["h"]), and their tolerance (BOSS["h_tol"]) the only one on the plate's height.
PLATE_Z0, PLATE_T = 6.55, 4.0
PLATE_Z1 = PLATE_Z0 + PLATE_T              # 10.55
PLATE_T_TOL = 0.1                          # 4.0 +-0.1 before anodising (drawing); depths go from the back
OVH = 2.5                                  # plate and body overhang the PCB by clearance + wall


def plate_xy(x, y, board_h):
    """a board point (y down, the board board_h high) in the plate's frame: origin at the plate's bottom-left
    corner seen from the front, y up. The plate STEP and the DXF artwork both use it."""
    return x + OVH, board_h + OVH - y

# through holes in the plate
KEY_HOLE = (10.2, 7.0, 1.4)                # caps are 9.6 x 6.4: 0.3 per side, see the cap budget below
KEY_HOLE_R_MAX = 1.5                       # corner radius at most (drawing): a larger one takes a turned cap's room
KEY_HOLE_TOL = (0.1, 0.0)                  # +0.1/-0 after anodising on the drawing: never under 0.3 per side
KEY_BACK_BREAK, KEY_BACK_BREAK_MAX = 0.3, 0.5   # edge break on the key holes' back edges, from and to (drawing)
FRONT_BREAK = 0.2                          # edge break on the front outline and hole edges, at most (drawing)
# general tolerance ISO 2768-m (+-0.2 from 6 to 30 mm) where the drawing gives none
PLATE_GEN_TOL = 0.2
SHAFT_HOLE = 9.5                           # encoder bushing dia 7 +0.3: clears the board offset, hidden by the knob
RANGE_HOLE = 11.1                          # RKJXT hub (7.2) at full tilt, hidden under the knob skirt (check_fit)
LIGHT_HOLE = 2.3                           # light pipes; webs to the neighbouring key holes in check_fit.py
LIGHT_HOLE_TOL = (0.1, 0.0)                # +0.1/-0 on the drawing: never smaller, so a pipe cannot jam
# Black anodising grows every anodised surface by up to half of this: it takes about this much off a hole's
# diameter or a pocket's width. The key holes are toleranced after anodising on the drawing; check_fit.py takes
# it off every other hole and pocket. Heights: the drawing allows the boss end faces bare (masked with their
# threads) or anodised, all alike. The boss height counts from the back face, and both grow alike or neither does,
# so the back face keeps its place over the PCB only when the ends are anodised: over bare ends it sits up to
# ANODISE / 2 lower, and the front face stands up to ANODISE higher than on a bare plate (the anodised ends lift
# the plate by ANODISE / 2, and the front grows by as much). Each check_fit.py row takes the worse case.
ANODISE = 0.05

# pockets milled from the back
# w, h, corner r, depth (body 11.7 x 12 x 8.0 +-0.3, 13.1 +-0.5 over the side lugs, terminal blocks; pins at
# +-9.5): 1.5 mm of plate left over it (1.4 on a thin plate). The lugs run along w.
# Depths +0/-POCKET_TOL on the drawing: never deeper, so the front stays; check_fit uses the shallow end.
EC11_POCKET = (15.8, 20.0, 2.0, 2.5)
EC11_LUGS = 13.1                           # PEC11D width over the side lugs (+-0.5, ENC_TOL["ge10"])
RANGE_POCKET = (19.6, 3.05)                # dia, depth (body 16.4 across corners, 8.6 high): 0.95 left (0.85 thin)
# JLCCNC's guideline for thin walls and floors: CNC_WALL recommended, CNC_WALL_MIN its absolute minimum. The floors
# left over the pockets keep the recommended value on a thin plate; the webs between a light hole and the next key
# hole keep it as drawn and the minimum at tolerance (check_fit.py).
CNC_WALL, CNC_WALL_MIN = 0.8, 0.5
POCKET_FLOOR_R = 0.3                       # most floor corner radius of the encoder and RANGE pockets (drawing)
# RKJXT octagon above z 4 (Alps' STEP model): across corners and flats; tolerance assumed (as on its height)
RKJXT_ACROSS, RKJXT_FLATS, RKJXT_TOL = 16.4, 15.73, 0.3
POCKET_TOL = 0.1

# ---- process tolerances and limits of the vendors, for check_fit.py ----
# JLC3DP SLA resin (knobs, light pipes), +-: sizes (outside diameters, the width of the outer knob's key), holes
# (on the diameter), bore depths and the height of the outer knob's key.
RESIN_TOL = dict(size=0.2, hole=0.3, depth=0.1)
RESIN_PART_MIN = (10.0, 2.0, 2.0)          # JLC3DP's least size of a resin part, largest first
# JLC3DP WJP full-colour resin (caps), +-: outline and holes, on the size (JLC3DP's WJP design guide: 0.2 within
# 100 mm, printed holes 0.1 to 0.2 off). The caps' rib circle is such a hole: CAP_PRINT is the print error on its
# diameter that the four cap sets cover.
WJP_TOL = dict(size=0.2, hole=0.2)
CAP_PRINT = (-WJP_TOL["hole"], WJP_TOL["hole"])
# JLC3DP MJF PA12 (body), +-: MJF_TOL on a length up to 100 mm, MJF_SCALE of it above.
MJF_TOL, MJF_SCALE = 0.3, 0.004
# JLCPCB, +-: the routed board outline, a V-cut edge (the rail edge), a routed cutout per side
# (assumed: the outline's +-0.2 on its size).
PCB_OUTLINE_TOL, PCB_VCUT_TOL, PCB_CUTOUT_TOL = 0.2, 0.4, 0.1
# Should JLCPCB add rails on the short edges too, those V-cut edges can be too long for the body's cavity at worst:
# they are then sanded until the board is at most this long (docs/building/bring-up.md, On arrival).
PCB_SANDED_LEN = 160.2

# ---- fasteners: bosses milled with the plate, M3 flanged button heads from below, no washers ----
# Bosses: dia 5.5 +-0.1 (ISO 2768-m), PLATE_Z0 +-h_tol high from the back face (drawing): 6.5 to 6.6. That height
# centres the plate between the rows that want it low (knobs and RANGE skirt over the face) and those that want it
# high (pockets over the RKJXT and the encoders, cap sockets under the face, the tongue's end over the plug, body
# walls). At JLCCNC's default +-0.1 every row still passes, with 0.05 less on each side: the drawing and the JLCCNC
# remark ask for +-0.05, and +-0.1 is acceptable (docs/building/ordering.md). End faces flat, square to the bore. They
# sit on the PCB inside its copper keep-out (pcb/board.py MOUNT_KEEPOUT). Five of them: at the four corner mounts and
# at the middle one (pcb/board.py MID_MOUNT), all alike.
BOSS = dict(d=5.5, d_tol=0.1, h=PLATE_Z0, h_tol=0.05, root_r=0.3)   # root_r: inside corner at the back face, at most
# Thread M3-6H from the boss end face, full thread at least `full` deep, drilled dia `drill` `depth` deep plus the
# drill point (118 deg), a `cham` x 90 deg countersink at the mouth. JLCCNC's rules: at most 3 D of thread, at least
# half the diameter unthreaded at the bottom of a blind hole (7.5 - 6.0 = 1.5). Anodised threads must be masked or
# cut again after anodising: the coating would take about 0.1 mm off the pitch diameter, more than the 6H band.
TAP = dict(thread="M3-6H", full=6.0, drill=2.5, depth=7.5, cham=0.3)
TAP["point"] = TAP["drill"] / 2 / 1.664                   # 118 deg point: r / tan 59 deg, 0.75
# PCB mounting hole (pcb/board.py MOUNT_HOLE): the plate's bosses locate the screws, and the caps centre the board
# in the key holes during the face-down drop, so the board must find its place round the screws: 3.8 (3.6 to 4.0
# with JLCPCB's +-0.2 on NPTH) passes the M3 with the board where the caps centre it, off by no more than the
# positions on the plate and on the board, the centring and the thread (POS_TOL, 0.255 in all; check_fit.py has the
# row), and the boss end still covers the hole all round inside the 3.6 mm copper keep-out.
# Screw: M3 x 8 flanged button head, ISO 7380-2 (JLCMC EDDH-C16E1-M3-L8, 10B21 blackened, 8.8; or EDDH-S1W, A2-70):
# ISO 7380-2 gives the flange dc 6.32 to 6.9 and its rim c 0.55 to 0.7, head k 1.4 to 1.65, button dk 5.2, 2 mm
# hex; JLCMC's table gives the flange as 7 and k 1.65, so the flange is taken 6.32 to 7.0. Length js15 (+-0.29,
# ISO 4759-1 grade A), thread 6g (d 2.86 to 3.0). The end has up to 2P (1.0) of incomplete thread (ISO 4753), which
# carries no load. The flange bears on the counterbore floor round the body hole: no washer.
SCREW = dict(d=3.0, d_min=2.86, L=8.0, L_tol=0.29, tip=1.0, head_d=5.2, flange_d=7.0, flange_d_min=6.32,
             flange_c=0.55, head_k=1.65, hex=2.0)
SCREW_D, SCREW_L = SCREW["d"], SCREW["L"]
# MJF rounds the counterbore's floor corner a little (JLC3DP gives no figure; assumed at most this): where the flange
# reaches the counterbore wall (it does before the shank meets the body hole wall, a co-stop) its rim stands on that
# corner, not on a slope under the flange, as long as the rim is taller (check_fit.py)
CB_FLOOR_R = 0.2
# Stack from the counterbore seat to the PCB top (each +-): seat to boss top (JLC3DP MJF +-0.3 within 100
# mm), PCB 1.6 +-10 %.
STACK_TOL = dict(counterbore=MJF_TOL, pcb=0.16)
SEAT_Z = -3.2                              # counterbore seat: 1.6 of PA12 up to the PCB (1.3 at MJF -0.3)
ENGAGE_MIN = 2.0                           # full thread engaged in the plate boss, mm (4 turns)
SCREW_HEAD_Z = SEAT_Z                      # the flange bears on the counterbore seat (for the 3D view)
# Positional budget (each +-, radial unless noted): bosses, pockets, the tongue and through holes to each other
# (drawing note), PCB drill positions (JLCPCB, about 0.05; 0.075 assumed), NPTH size (JLCPCB +-0.2 on the diameter),
# M3 in its thread, the board offset the caps allow (their largest shift in key holes at +0.1, about 0.40
# diagonally, plus 0.05 of key pattern to screw pattern), the body over 153 mm (JLC3DP MJF +-0.4 % above
# 100 mm, so +-0.31 in x and +-0.11 in y per hole once the screws centre it) and its hole size (MJF, radial).
POS_TOL = dict(plate=0.1, pcb=0.075, npth_d=0.2, thread=0.03, centring=0.05, body=0.33, body_hole=0.15)
# The caps centre the board in the key holes during assembly; the screws then must not pull it off centre.
# Per-key errors that stay (RSS): switch holes on the PCB, switch on its pins, key hole on the plate, cap
# outline (WJP +-0.2 on size, half per side), cap on its plunger.
CAP_TOL = dict(pcb=0.075, switch=0.15, plate=0.1, cap=0.1, socket=0.05)
# A cap can turn on its round plunger (up to about 5 deg in a nominal hole before it binds); turned, it has less
# room to shift. Each row of caps is squared against a steel rule before the face-down assembly, which leaves
# about this much (deg); check_fit.py takes the shift room with the cap turned by it.
CAP_TURN = 1.0
ENC_ON_PINS = 0.15                         # encoder (bushing) on its pins and lugs before soldering, radial
# Alps' STEP model of the RKJXT, for the section drawing: it stands on a round foot (RKJXT_FOOT across), its base
# frame (RKJXT_FRAME across) RKJXT_FRAME_GAP over the board.
RKJXT_FOOT, RKJXT_FRAME, RKJXT_FRAME_GAP = 13.5, 17.2, 0.40
# The RKJXT floats more (radial, worst direction): Alps' STEP model has 0.7 x 0.2 blade terminals and a 0.6 x
# 0.4 frame terminal, the holes are drilled 1.1 and JLCPCB's plating finishes them 1.02 to 1.23, which lets
# the part move 0.26 at most. Its locating lug (dia 1 -0.1, 3.8 and 1.5 +-0.05 off the axis) sits in the
# 1.3 mm NPTH of JLC's footprint (+-0.2): 0.30 plus 0.07 off position, so the terminals bind first. Alps
# recommends 1.1 +0.1/-0 for the lug, which an NPTH at +-0.2 cannot hold (at 0.9 it would not take the lug),
# so the plate gives the part room instead (RANGE_POCKET, RANGE_HOLE).
RKJXT_ON_PINS = 0.26
SLEEVE_CLEAR = 0.9                         # outer knob counterbore around the fixed bushing, radial and above
# The tongue on the plate's back edge, over the USB-C socket (pcb/board.py USB_X): the body's back wall has a slot
# there, as wide as the plug opening and open to the top, so the socket (its face level with the cavity wall) passes
# the wall when the body goes on. The tongue fills the slot from the plate down: w +-tol wide, d thick (the wall,
# +-d_tol by ISO 2768-m, its outer face flush with the plate's edge), h +-tol long from the back face (drawing), so
# its end is the top edge
# of the plug opening, 1.05 over the PCB top and 1.05 short of the bosses' ends. It is milled with the bosses, from
# the same stock. The gaps beside it and under its end stay within USB_GAP_MAX, the board's thickness (cosmetic:
# what shows through them is the dark cavity over the board).
USB_TONGUE = dict(w=14.4, d=2.0, d_tol=0.1, h=5.5, tol=0.1, root_r=0.3)
USB_GAP_MAX = 1.6
# The body's plug opening and the slot over it are cut in from the back wall to this board y, past the board's edge:
# under the socket the floor is notched down to the opening's bottom.
USB_OPEN_IN = 1.0
# The body's column under the middle mount (make_mech.py) is a bar along board y, MID_BAR["w"] wide, with the
# corners' round boss on top and their counterbore and screw hole through it: the leads of the four keys round it
# stand 5.3 mm off its axis in x, where a round column would touch them. Leads, solder fillets and bottom-side parts
# keep LEAD_CLEAR from every part of the body in the room under the board, at the worst offsets (check_fit.py).
MID_BAR = dict(w=4.0)
LEAD_CLEAR = 0.3
# Body walls stop short of the plate: the bosses set its height. The gap must never close: MJF +-0.3 on the wall
# height over the boss tops under the PCB, PCB -0.16, the bosses at their lowest (-0.05), the plate back up to
# ANODISE / 2 low over bare boss ends and bowed towards the walls by PLATE_FLAT (most at the middle of the long
# walls) take 0.62 of it. WALL_GAP leaves 0.33 over that (check_fit.py has the row), so no wall top needs fitting. A
# wall that touched would take the screw's clamp off the board (docs/architecture/mechanics.md, Fastening).
WALL_GAP = 0.95

# encoder shafts (z above the PCB); "sleeve" is the fixed bushing
EC11_BODY, SLEEVE_TOP, OUTER_TOP, INNER_TOP = 8.0, 13.0, 18.0, 28.0
EC11_SIZE = (11.7, 12.0)                   # PEC11D body across, along board x and y
SLEEVE_D, OUTER_D, INNER_D, INNER_FLAT, FLAT_LEN, SLOT_W, SLOT_LEN = 7.0, 6.0, 3.5, 2.5, 7.0, 2.0, 2.5
PUSH_TRAVEL = 0.5
# PEC11D tolerances: +-0.3 for dimensions under 10 mm, +-0.5 from 10 mm. The outer knob rests with its key on
# the slot floor (18 - 2.5), the inner knob on the inner shaft tip (28): RSS spreads of their heights, against
# each other and against the bushing top (13). From the PCB the slot floor is body 8 (+-0.3) + shaft 10 (+-0.5)
# - slot 2.5 (+-0.3).
ENC_TOL = dict(lt10=0.3, ge10=0.5)
# Both shafts are +0/-SHAFT_TOL at most across; the inner one off the outer one by SHAFT_ECC (assumed: the
# datasheet gives no concentricity).
SHAFT_TOL, SHAFT_ECC = 0.1, 0.05
ENC_SPREAD = dict(
    inner_outer=(ENC_TOL["ge10"] ** 2 * 2 + ENC_TOL["lt10"] ** 2) ** 0.5,        # 28 vs 18 - 2.5: 0.77
    inner_shaft=(ENC_TOL["ge10"] ** 2 * 2) ** 0.5,                               # 28 vs 18: 0.71
    slot_sleeve=(ENC_TOL["ge10"] ** 2 * 2 + ENC_TOL["lt10"] ** 2) ** 0.5,        # 18 - 2.5 vs 13: 0.77
    slot=(ENC_TOL["ge10"] ** 2 + ENC_TOL["lt10"] ** 2 * 2) ** 0.5,               # 8 + 10 - 2.5 vs the PCB: 0.66
)
# Outer knob key in the shaft slot (2.0 +-0.3): 1.4 wide, so even a key printed 0.2 wide clears the narrowest
# slot (1.7); JLC3DP asks for positioning features over 1.5, which the slot does not leave room for. Its face
# is KEY_R from the axis: 0.7 into the slot from the 6 mm shaft surface (0.5 with the shaft 0.1 small and the
# key face printed 0.15 back), clear of the 3.5 mm inner shaft that runs through the slot even with a loose
# knob pushed towards it. It rests on the slot floor over its whole 1.4 x 0.7 end.
KEY_W, KEY_R = 1.4, 2.3

# knobs (heights above the plate top); resin, fits to test on the first print
# FIT is added to the datasheet nominal of bores that must grip. The shafts are toleranced +0/-0.05 and
# +0/-0.1, so FIT 0 leaves 0 to 0.1 real clearance on a true print. JLC3DP's resin holes vary by
# +-0.3 (RESIN_TOL), so one of each knob (outer, FMS ring, inner, RANGE) also comes 0.2 tighter and 0.2 looser; a
# bore that is still too tight opens with a drill of the shaft size (6.0, 3.5, 2.5) and a needle file on the D flat.
# A variant counts as fitting when its bore prints within FIT_OFF of the size drawn: up to that much under, it opens
# with the drill and the file; up to that much over, it has at most 0.25 of play on the smallest shaft and still
# turns it through its key or D flat (assumed; the first print shows). check_fit.py holds the three variants
# against the resin's tolerance with it. A reprint sets FIT to the variant that fit (docs/building/assembly.md),
# which takes out the printer's own bias: the variants come about FIT, and check_fit.py takes the resin's tolerance
# about it too, with FIT itself within that tolerance.
# A single compliant bore cannot replace the variants: the friction must carry the detent torque (PEC11D: 100 +-70
# gf cm, 16.7 N mm at most; RKJXT: 15 +-8 mN m, 23 N mm at most), which on the inner knob's D flat (1.58 from the
# axis to its corner) takes a spring preload of 10.6 N and on the RANGE lever's (1.12) about 20.5 N; over the bore's
# 0.6 and the shaft's 0.1 such a spring in the SLA resin (E about 2.7 GPa) is strained about 7 % at the tight end
# on the inner knob, the resin's elongation at break, and takes about 70 N to push on.
FIT = 0.0
FIT_VARIANTS = {"tight": -0.2, "loose": 0.2}   # extra outer, FMS, inner and RANGE knob each
FIT_OFF = 0.15
# Garmin proportions: outer rings 17 on all three dual knobs, inner knobs 12, so 2.5 of ring shows each side.
# The outer ring ends flush with the 6 mm shaft top: no neck rises into the inner knob, since a recess round a
# neck in a 12 mm knob cannot leave 1.0 of resin on both and still clear a loose knob. Its bottom
# is 1.15 over the plate, so the slot floor's spread and a high plate face (high bosses, a thick plate, anodised,
# bowed up) leave 0.24.
OUTER_KNOB = dict(d=17.0, z0=1.15, z1=7.45)
# 1.0 over the outer knob when pushed, so the PEC11D's shaft spread (ENC_SPREAD) never makes them touch. The
# recess clears the outer shaft top when the shafts' spread lifts it into the inner knob.
INNER_KNOB = dict(d=12.0, z0=8.95, z1=19.35, recess_d=8.0, recess_top=10.25)
# Its D bore ends INNER_BORE_SHORT short of the shaft's 7.0 mm D flat (+-0.3), so the bore end, not the round
# shaft under a short flat, sets the knob height (check_fit.py); below it a round bore INNER_BORE_RELIEF over the
# shaft radius.
INNER_BORE_SHORT, INNER_BORE_RELIEF = 0.7, 0.1
# Flutes (count, depth, taper of the radius to the top, top chamfer), for make_knobs.py and the 3D view. The FMS
# ring has fewer, twice as deep flutes than the other two, so FREQ and FMS (one above the other, same size)
# are told apart by feel.
# Grooves (and the lands between them) stay at least 0.8 wide at half depth (resin detail); the inner knob's
# 20 flutes are still finer than the outer rings' 24.
FLUTES = {"outer": dict(n=24, depth=0.45, taper=0.05, cham=0.8),
          "outer_fms": dict(n=14, depth=0.9, taper=0.05, cham=0.8),
          "inner": dict(n=20, depth=0.32, taper=0.06, cham=0.6),
          "range": dict(n=22, depth=0.32, taper=0.05, cham=0.6)}
OUTER_FLUTES = {"ALTHDG": "outer", "FREQ": "outer", "FMS": "outer_fms"}   # each dual knob's outer ring
# knob legends: degrees their arc is turned from the horizontal towards the user, for the plate artwork and
# the 3D view alike, chosen so a seated eye (CAP_VIEW_DEG) sees as much of each as the knobs allow.
KNOB_LEGEND_TILT = {"ALTHDG": 20, "FREQ": 10, "FMS": 20, "RANGE": 35}
# Their capitals are `size` high and `track` apart; the white arc lies `off` outside a dual knob's outer ring (RANGE:
# RANGE_ART) and the amber one `shift_off` outside the white one (arc radii to the glyph centres).
KNOB_ART = dict(size=1.55, track=0.22, off=1.9, shift_off=2.2)

# Legends, the one source for the caps (make_caps.py), the plate (make_plate_art.py), the board silkscreen
# (pcb/board.py) and the 3D view (geometry.js). Only the firmware button map (firmware/buttonmap.py,
# CircuitPython) keeps its own names; tests/test_labels.py checks they agree with these.
# The one amber: the plate's UV print is ordered in JLCCNC's standard orange, and this approximates it for the
# SHIFT cap legend, the artwork preview and the 3D view (its legends and the SHIFT light).
AMBER = dict(hex="#d9a441", rgb=(217, 164, 65))
# The amber legends under the keys on the plate (make_plate_art.py and the 3D view): the middle of their capitals dy
# below the cap's front edge, capitals `size` high, letters `track` apart. With dy 1.9 the ink starts 0.7 from the
# largest key hole (0.5 past its edge break, for the UV print's register) and ends 1.55 short of the next row's.
SHIFT_LEGEND = dict(dy=1.9, size=1.7, track=0.08)
# The plate's legends (em): their sizes are capital heights in mm, `cap` of the font's em; a space is `space` wide;
# a glyph is centred `mid` over its baseline, the middle of the capitals.
PLATE_TEXT = dict(cap=0.72, space=0.26, mid=0.35)
# The marked frame round all keys (make_plate_art.py and the 3D view): lines `line` wide, `side`, `back` and
# `front` outside the outer caps, corners of radius r. One line splits AUTOPILOT from the rest (between key columns
# 2 and 3, counted from 0 as in pcb/board.py), one AUDIO from RADIO (between columns 4 and 5) and one both from FMS
# below: it runs through the middle of what is left between key rows 1 and 2 after `fms` under row 1 for its amber
# legends.
KEY_FRAME = dict(side=3.0, back=4.2, front=4.6, fms=2.6, r=1.6, line=0.3)
# The group titles break the frame's lines: capitals `size` high, letters `track` apart, the line cleared `pad`
# on each side of the text, which starts `inset` after the group's left line (`inset_first` after the frame's
# rounded corner).
GROUP_TITLE = dict(size=1.75, track=0.32, pad=0.7, inset=3.0, inset_first=3.5)


def key_frame(cols, rows):
    """the frame round the keys at the board's key columns and rows: its sides x0, x1, y0, y1, the lines v_ap,
    v_radio (x) and h_fms (y), the group titles (text, x of its left end, y of its line), the corner radius r and
    the line width."""
    f, t = KEY_FRAME, GROUP_TITLE
    x0, x1 = cols[0] - CAP["w"] / 2 - f["side"], cols[6] + CAP["w"] / 2 + f["side"]
    y0, y1 = rows[0] - CAP["h"] / 2 - f["back"], rows[3] + CAP["h"] / 2 + f["front"]
    v_ap, v_radio = (cols[2] + cols[3]) / 2, (cols[4] + cols[5]) / 2
    h_fms = (rows[1] + CAP["h"] / 2 + f["fms"] + rows[2] - CAP["h"] / 2) / 2
    titles = [("AUTOPILOT", x0 + t["inset_first"], y0), ("AUDIO", v_ap + t["inset"], y0),
              ("RADIO", v_radio + t["inset"], y0), ("FMS", v_ap + t["inset"], h_fms)]
    return dict(x0=x0, x1=x1, y0=y0, y1=y1, v_ap=v_ap, v_radio=v_radio, h_fms=h_fms, titles=titles, r=f["r"],
                line=f["line"])


# Keys: (cap label, amber shift legend under it) per key, rows top to bottom, columns left to right.
KEY_LEGENDS = [
    [("AP", "TEST"), ("ALT", "ARM"), ("HDG", "CRS CTR"), ("MIC 1", "ADF"), ("COM 1", "NAV 1"), ("CDI", "OBS"),
     ("COM ⇆", "121.5")],
    [("FD", "YD"), ("VNV", ""), ("NAV", "GPSS"), ("MIC 2", "DME"), ("COM 2", "NAV 2"), ("VFR", "IDENT"),
     ("NAV ⇆", "ADF ⇆")],
    [("UP", ""), ("VS", ""), ("APR", "BC"), ("HOME", "UNIT"), ("FPL", "VNAV"), ("D→", "MSG"), ("MENU", "NRST")],
    [("DN", ""), ("FLC", ""), ("LVL", "½ BANK"), ("SHIFT", ""), ("PROC", "TERR"), ("CLR", "MAP"), ("ENT", "")],
]
# The flip-flop icon of "COM ⇆" and "ADF ⇆": Barlow has no such glyph and fallback fonts draw it the other
# way round, so the caps, the plate and the 3D view all fill these polygons. Units are em, from the icon's
# left edge and the middle of the cap height (0.7 em), y down: the right arrow on top, the left one below.
FLIP_W, FLIP_GAP = 0.6, 0.22                  # icon width, gap after the text


def _flip_icon(w=FLIP_W, dy=0.7 * 0.24, hl=0.22, hh=0.13, lw=0.075):
    def bar(xa, xb, y):
        return [(xa, y - lw / 2), (xb, y - lw / 2), (xb, y + lw / 2), (xa, y + lw / 2)]
    return [bar(0, w - hl, -dy), [(w, -dy), (w - hl, -dy - hh), (w - hl, -dy + hh)],
            bar(hl, w, dy), [(0, dy), (hl, dy - hh), (hl, dy + hh)]]


FLIP_ICON = _flip_icon()
CAP_FLIP_ICON = _flip_icon(lw=LEGEND_LINE)   # on the caps: lines that still print 0.4 mm wide

# Knobs: (white legend, amber legend with SHIFT or None): what the rings do, outer first, then the push.
KNOB_LEGENDS = {
    "ALTHDG": ("ALT · HDG · PUSH SYNC", "BARO · CRS · PUSH STD"),
    "RANGE": ("RANGE · PUSH PTR", None),
    "FREQ": ("FREQ · PUSH COM/NAV/ADF", "SQUAWK · PUSH XPDR"),
    "FMS": ("FMS · PUSH CRSR", "PANEL · FLOOD · PUSH CABIN"),
}

# RANGE knob on the RKJXT lever. The skirt (skirt_d) hides the plate hole; its rim is `rim` thick (no feather edge
# in resin: 1.0 left at -0.1, with 0.2 to spare); above the rim a 45 degree cone runs up to `sink` inside the
# fluted body. The underside is dished: flat over the hub (hub_d across, z0 over the plate, which gives the D bore
# its 4.6 mm on the lever), then a cone that rises by `dish` to the rim, at the tilt's own 9 degrees, so at full
# tilt the hub's corner and the rim come equally close to the plate (check_fit.py, for the fulcrum on either side).
LEVER_Z0, LEVER_Z1, LEVER_D, LEVER_FLAT = 12.4, 17.4, 2.5, 1.8
RANGE_KNOB = dict(d=13.6, skirt_d=17.3, z0=2.25, z1=10.45, rim=1.3, sink=0.3, hub_d=6.0, dish=0.9)
RANGE_RELIEF = (4.0, 0.3)                  # round bore under its D bore, clear of the lever: dia, least depth
# RANGE artwork on the plate (make_plate_art.py and the 3D view): legend arc radius (glyph centres) and the
# four pan arrows (triangle in mm, tip along the pan direction), outside the skirt with the lever off its hole
# (check_fit.py); the arrow tips stay 0.8 off the legend.
RANGE_ART = dict(legend_r=12.95, arrow_r=10.6, arrow=((0.75, 0.0), (-0.45, -0.7), (-0.45, 0.7)))

# Face-down assembly: the plate rests on two blocks under its long edges, clear of the shafts that stick out.
ASSEMBLY_BLOCK = 25.0                      # block height, mm
# Lights: reverse-mount 1206 LEDs on the bottom (LiteOn LTST-C230KSKT amber, LTW-C230DS white, one package), their
# lens up in a cutout through the board (pcb/board.py LED_CUTOUT, LiteOn's land pattern), so they shine out of the
# top side. LiteOn: the lens is 1.5 long (along the pads) and 1.6 wide, 1.10 - 0.28 = 0.82 over the substrate,
# +-0.1; the die sits on the substrate, at the board underside.
LED_LENS = dict(l=1.5, w=1.6, h=0.82, tol=0.1, place=0.1, solder=0.05, die=0.3)   # place: JLCPCB's placement
# Light pipes (clear resin, JLC3DP SLA): a stepped rod that stands on the board over the cutout and goes up through
# its plate hole, held by geometry alone. The base (base_d) runs from the PCB top to a shoulder base_len up, the rod
# (the light hole less `clear`, 2.0 across: JLC3DP's resin pillar guideline is 2.0 up to 4 mm, so the 4.35 rod is a
# review question) top_len from there. Every length is +-len_tol (JLC3DP's resin tolerance, 0.2 within 100 mm).
# Lifted, the shoulder stops on the plate back round the hole, so the pipe is captive; its top then stands over the
# face of a thin plate, by at most `proud` (check_fit.py: about half of what the key caps stand over the face). In use
# the pipe rests on the board and its top sits 0.40 under the anodised face in the nominal stack (check_fit.py has the
# range and how much of it shows from the seat). The pipe is never clamped: base_len + len_tol + stub stays under the
# smallest gap from the board to the plate back (plate back low and bowed down, the board bowed up). A clamp cannot be
# bounded: a bare board held at its corners alone is about 13 (SHIFT) and 17 N/mm (UNIT) stiff at the lights, and the
# middle mount stiffens it further, so even 0.1 mm would load the pipe with newtons. The rod is `clear` under its hole
# on the diameter: anodising (0.05) and the resin tolerance (+-0.2) cannot make it jam. The base (2.8 across) is wider
# than the cutout, so it stands on the board, and narrow enough to stay out from under the key holes (a firmly pressed
# cap dips under the plate back) and clear of the switch bodies (check_fit.py). The light holes' back edges are sharp,
# deburred only (LIGHT_HOLE_BACK_BREAK at most), so the shoulder sits on the flat back face.
# Both pipes print on one 2.2 x 2.0 bar under their bases (a resin part is RESIN_PART_MIN at least), on 1.0
# necks (the resin minimum), so the visible tops are as printed. The snap-off stubs under the bases are sanded flush,
# no further, so up to `stub` may stay on: the clamp row counts it.
PIPE = dict(base_d=2.8, base_len=5.85, top_len=4.35, len_tol=0.2, proud=1.0, stub=0.1, clear=0.3, neck_d=1.0,
            neck_len=0.6, bar=(2.2, 2.0), resin=RESIN_TOL["size"], anodise=ANODISE, z0=0.0)
LIGHT_HOLE_BACK_BREAK = 0.05
PIPE["len"] = PIPE["base_len"] + PIPE["top_len"]
# Through-hole leads below the PCB, untrimmed: the keys' 3.51 +-0.30 (TE drawing) stand 2.37 under a board 0.16 thin
# at most, the PEC11D terminals about 1.9 (+0.3), the RKJXT's about 1.6; plus up to 0.3 of solder at a tip. Nothing
# is trimmed: check_fit.py checks this against the room under the board.
LEAD_MAX = 2.7
# PCB bow, either way, at its middle (the two lights sit near the middle of the 153 mm span between the corner
# screws). JLCPCB, like IPC-6012, allows 0.75 % bow and twist for SMT boards (1.2 mm over 160 mm); a 4-layer 1.6 mm
# board is usually far flatter. The light pipe rows and the pocket rows over the encoders and the RKJXT take this
# much, shaped like the plate's bow (check_fit.plate_bow, taken as if both were held at the four corner mounts
# only; the middle mount holds them flatter).
PCB_BOW = 0.1
# The plate is held at its corners as well, so its flatness counts the same way: "flatness 0.1" on the drawing,
# after bead blasting and anodising (milling most of a 12 mm plate off one side and blasting it can bow it; ISO
# 2768-K alone would allow 0.4 over its 165 mm), either way. check_fit.py moves the plate at a part by that times
# its plate_bow() (a dome, or a bow along or across the plate, held at the corner bosses), in the direction that
# costs the row. The light pipe rows take PLATE_FLAT in full. Every row still passes up to 0.2 (the light pipes'
# clamp row goes first, just above 0.22); that is what to answer should JLCCNC ask. With the bosses at +-0.1 as
# well, up to 0.15 (docs/building/ordering.md).
PLATE_FLAT = 0.1
# The body post under the PCB (make_mech.py) ends SUPPORT_SHORT under it, so with JLC3DP's MJF +-0.3 (post height
# against the bosses) it never lifts the board. It is a backstop: with the board held at the middle mount, a firm
# press does not bend it that far.
SUPPORT_SHORT = 0.3
if SUPPORT_SHORT < MJF_TOL:
    raise ValueError("the body post could lift the board")
# A firm key press (PRESS_FIRM, about six times the switch's 1.6 N) on the bare board, from a Kirchhoff plate model
# of it (1.6 mm FR4 at 20 GPa, no stiffening by the parts, clamped at the four corner mounts, the post pushing only
# up), tied to the plate at the middle mount: a disc of 2.5 mm radius there moved as one, on the aluminium plate's
# compliance (0.0017 mm/N), and tilting against 46000 N mm/rad, far softer than a board clamped between the plate's
# boss and the body's. Every key pressed in turn, the pressed key dips up to 0.195 (0.193 rounded up; the front row,
# 18 mm in front of the middle mount) and the board under any key slopes up to 6.8 mrad (6.75); with that disc held
# rigidly it is 0.175 and 6.2. A normal 1.6 N press dips it 0.031 and slopes it 1.1 mrad. check_fit.py takes dip
# and slope 10 % up (FR4's flexural modulus, about 18 to 24 GPa; 18 GPa would need 11 %). The model is not part of
# this repository.
PRESS_FIRM = 10.0                          # N
PRESS_DIP, PRESS_SLOPE = 0.195 * 1.1, 0.0068 * 1.1
