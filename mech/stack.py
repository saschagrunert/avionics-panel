"""Mechanical stack of the Avionics Panel rev 1: one place for every height and fit.

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

Front plate: milled from 12 mm 6061 stock: the 4 mm web at z 6..10, pockets milled from below for the encoder and
RANGE bodies, and four round bosses on its back at the corner mounts that stand down to the PCB top, each tapped M3
from its end face; nothing on the front. M3 x 8 flanged button-head screws (ISO 7380-2) come from under the body:
body boss -> PCB -> plate boss thread, no washers, no glue. The bosses alone set the plate height (BOSS), the body
walls stop WALL_GAP short of the plate.
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
RKJXT_FULCRUM_OFF = 4.65                   # and off the lever axis (datasheet), on the side the lever tilts to
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
# docs/building/building.md)
CAP_BAR = dict(w=3.2, d=1.0, proud=0.5, sink=0.05, inset=0.6)
# seated eye over the cap tops: about 42 deg at a desk plus the 6 deg wedge, 48 deg (docs/using/controls.md); 45 is
# the conservative value, since a flatter sightline lets the front bar hide more of the legend
CAP_VIEW_DEG = 45.0
# Cap legends (make_caps.py, the 3D view): Barlow Semi Condensed Bold (its thinnest strokes, the horizontal
# bars, are 0.121 em), grown all round by LEGEND_GROW mm, so every stroke prints at least 0.4 mm wide (JLC3DP
# full colour: coloured lines 0.4 mm min.); the D-> arrow and the flip-flop icon have lines LEGEND_LINE em wide
# before the growth. check_fit.py measures the strokes on the generated texture.
LEGEND_WEIGHT, LEGEND_GROW, LEGEND_LINE = 700, 0.055, 0.12
LEGEND_STROKE_MIN = 0.4
# Key cap socket for the full-colour resin (JLC3DP WJP: walls 1.0 mm min., pillars 1.0 mm no taller than 2.0,
# holes and gaps 1.0 min., about +-0.2 outside and +-0.3 on holes). A 3.8 mm bore (1.3 mm wall at the narrow
# cap sides, 1.05 on a print with the outline 0.2 small and the bore 0.3 large; nothing open to the outside;
# 0.1 radial left round the plunger in a bore 0.3 small) with four rigid ribs 1.2 wide along its wall,
# attached over their full length. Each rib follows the plunger's cone, so it touches the plunger over its
# whole length and the cap cannot rock; the ribs stop `relief` below the ceiling, clear of the plunger's
# rounded top edge, so the flat ceiling sits on the plunger's flat top and sets the cap height, not the fit.
# A 0.3 mm lead-in at the mouth (0.2 radial) starts the cap straight.
CAP_SOCKET = dict(d=3.8, rib_w=1.2, rib_angles=(0, 90, 180, 270), relief=0.35, lead=0.3, lead_r=0.2,
                  depth=PLUNGER_TOP - CAP["base"])
# A rigid friction fit works over a window of about 0.13 mm (CAP_GRIP), but JLC3DP's resin holes vary by
# about +-0.2 to 0.3 (JLC3DP's WJP page: +-0.1 to 0.2 on holes). So the caps come in four full sets that
# differ only in their rib circle, given here at the socket mouth (2.7 below the plunger top, where the plunger
# is 3.29): set D grips a print whose rib circle comes out 0.09 to 0.22 large, A 0.01 small to 0.12 large, B
# 0.11 small to 0.02 large, C 0.21 to 0.08 small (CAP_GRIP). The set that seats fully and holds is the one
# to fit. Each set's caps carry 1 to 4 dimples (CAP_MARK, A 1 ... D 4) on the underside, inside the key hole
# where they never show. The sets take a plunger off TE's model by as much, together with the print: TE's drawing
# allows +-0.30 on its diameter, so a plunger lot at the edge of that needs the sets moved
# (docs/architecture/mechanics.md).
# One compliant set cannot replace them in a 9.6 x 6.4 cap: springs that grip over the drawing's 0.6 and the print's
# 0.4 deflect up to 0.55 each, and two of them, one printed 0.1 thin and one 0.1 thick, hold the cap up to 0.18 off
# its plunger, twice the 0.09 the key hole leaves for that (docs/architecture/mechanics.md).
CAP_SETS = {"A": 3.15, "B": 3.25, "C": 3.35, "D": 3.05}
CAP_GRIP = (0.02, 0.15)                    # diametral interference: holds from, still seats by hand up to
CAP_PRINT = (-0.20, 0.20)                  # rib circle print error (mm on the dia) the four sets must cover
# Dimples 1.0 across (WJP holes 1.0 min.) and 0.9 deep (engraved detail 0.8 min.), one in each corner region
# between the socket and the outline, where the cap is thickest: set A uses the first, D all four.
CAP_MARK = dict(d=1.0, depth=0.9, pos=((-3.19, -1.59), (-3.19, 1.59), (3.19, 1.59), (3.19, -1.59)))


def cap_rib_d(name, dz):
    """rib circle diameter of cap set `name` dz below the plunger top (the cone shifted to the set's size)."""
    return plunger_d(dz) + CAP_SETS[name] - plunger_d(CAP_SOCKET["depth"])


PCB_T = 1.6
PLATE_Z0, PLATE_Z1 = 6.0, 10.0           # the 4 mm web of the 6061 plate; the plate top is where it always was
PLATE_T_TOL = 0.1                          # 4.0 +-0.1 before anodising (drawing); depths go from the back
PLATE_T = PLATE_Z1 - PLATE_Z0
OVH = 2.5                                  # plate and body overhang the PCB by clearance + wall

# through holes in the plate
KEY_HOLE = (10.2, 7.0, 1.4)                # caps are 9.6 x 6.4: 0.3 per side, see the cap budget below
KEY_HOLE_TOL = (0.1, 0.0)                  # +0.1/-0 after anodising on the drawing: never under 0.3 per side
KEY_BACK_BREAK = 0.1                       # edge break on the key holes' back edges, at least (drawing: 0.1 to 0.2)
# general tolerance ISO 2768-m (+-0.2 from 6 to 30 mm) where the drawing gives none
PLATE_GEN_TOL = 0.2
SHAFT_HOLE = 9.3                           # encoder bushing dia 7 +0.3: clears the board offset, hidden by the knob
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
# +-9.5): 1.2 mm of plate left over it (1.1 on a thin plate). The lugs run along w.
# Depths +0/-POCKET_TOL on the drawing: never deeper, so the front stays; check_fit uses the shallow end.
EC11_POCKET = (15.6, 20.0, 2.0, 2.8)
EC11_LUGS = 13.1                           # PEC11D width over the side lugs (+-0.5, ENC_TOL["ge10"])
RANGE_POCKET = (19.6, 3.25)                # dia, depth (body 16.4 across corners, 8.6 high): 0.75 left (0.65 thin)
POCKET_FLOOR_R = 0.3                       # most floor corner radius of the encoder and RANGE pockets (drawing)
# RKJXT octagon above z 4 (Alps' STEP model): across corners and flats; tolerance assumed (as on its height)
RKJXT_ACROSS, RKJXT_FLATS, RKJXT_TOL = 16.4, 15.73, 0.3
POCKET_TOL = 0.1

# ---- process tolerances and limits of the vendors, for check_fit.py ----
# JLC3DP SLA resin (knobs, light pipes), +-: sizes (outside diameters, the width of the outer knob's key), holes
# (on the diameter), bore depths and the height of the outer knob's key.
RESIN_TOL = dict(size=0.2, hole=0.3, depth=0.1)
# JLC3DP WJP full-colour resin (caps), +-: outline and holes, on the size.
WJP_TOL = dict(size=0.2, hole=0.3)
# JLC3DP MJF PA12 (body), +-: MJF_TOL on a length up to 100 mm, MJF_SCALE of it above.
MJF_TOL, MJF_SCALE = 0.3, 0.004
# JLCPCB, +-: the routed board outline, a V-cut edge (the full variant's rail edge), a routed cutout per side
# (assumed: the outline's +-0.2 on its size).
PCB_OUTLINE_TOL, PCB_VCUT_TOL, PCB_CUTOUT_TOL = 0.2, 0.4, 0.1
# Should JLCPCB add rails on the short edges too, those V-cut edges can be too long for the body's cavity at worst:
# they are then sanded until the board is at most this long (docs/building/building.md).
PCB_SANDED_LEN = 160.2

# ---- fasteners: bosses milled with the plate, M3 flanged button heads from below, no washers ----
# Bosses: dia 5.5 +-0.1 (ISO 2768-m), h +-h_tol high from the back face (drawing). The stack keeps PLATE_Z0 = 6.0 as
# its reference; the bosses stand 0.05 higher, 6.0 to 6.1, which centres the plate between the rows that want it low
# (knobs and RANGE skirt over the face) and those that want it high (pockets over the RKJXT and the encoders, cap
# sockets under the face, USB-C filler, body walls). At JLCCNC's default +-0.1 instead every row still passes, with
# 0.05 less on each side, bar the cosmetic cap socket ceiling, which may then stand up to 0.04 above the face on a
# plunger 0.3 high (TE's tolerance): so the drawing and the JLCCNC remark ask for +-0.05, and +-0.1 is acceptable,
# cosmetic only (docs/building/building.md). End faces flat, square to the bore. They sit on the PCB inside its copper
# keep-out (pcb/board.py MOUNT_KEEPOUT).
BOSS = dict(d=5.5, d_tol=0.1, h=6.05, h_tol=0.05, root_r=0.3)   # root_r: inside corner at the back face, at most
# Thread M3-6H from the boss end face, full thread at least `full` deep, drilled dia `drill` `depth` deep plus the
# drill point (118 deg), a `cham` x 90 deg countersink at the mouth. JLCCNC's rules: at most 3 D of thread, at least
# half the diameter unthreaded at the bottom of a blind hole (7.5 - 6.0 = 1.5). Anodised threads must be masked or
# cut again after anodising: the coating would take about 0.1 mm off the pitch diameter, more than the 6H band.
TAP = dict(thread="M3-6H", full=6.0, drill=2.5, depth=7.5, cham=0.3)
TAP["point"] = TAP["drill"] / 2 / 1.664                   # 118 deg point: r / tan 59 deg, 0.75
# Gap tolerance (+, -) on PLATE_Z0, the back face over the PCB top: the boss height alone. check_fit.py adds the
# ANODISE / 2 the back face sits lower over bare boss ends, and the front face's growth (see ANODISE).
GAP_TOL = (round(BOSS["h"] + BOSS["h_tol"] - PLATE_Z0, 6), round(PLATE_Z0 - BOSS["h"] + BOSS["h_tol"], 6))   # +0.1, -0
# PCB mounting hole (pcb/board.py MOUNT_HOLE): the plate's bosses locate the screws, and the caps centre the board
# in the key holes during the face-down drop, so the board must find its place round the screws: 3.8 (3.6 to 4.0
# with JLCPCB's +-0.2 on NPTH) passes the M3 wherever the caps put the board, and the boss end still covers the
# hole all round inside the 3.6 mm copper keep-out (check_fit.py).
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
# Positional budget (each +-, radial unless noted): bosses, pockets and through holes to each other (drawing
# note), PCB drill positions (JLCPCB, about 0.05; 0.075 assumed), NPTH size (JLCPCB +-0.2 on the diameter),
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
# Seating of the encoders and the RKJXT, checked on arrival and when hand-soldering (docs/architecture/mechanics.md).
# Encoders: the body stands flush on the board, and a SEAT_GAP feeler gauge must not slide under it. A part that
# passes stands less than that proud at the edge of its base (EC11_BASE wide), or is tilted by up to SEAT_GAP over
# that base: check_fit.py raises the top corners by the gap times their reach from the far base edge over the
# base, moves a feature at height z sideways by z times the tilt, and lowers a feature that reaches out past the
# base edge the part tilts on (the outer knob's rim) by that reach times the tilt.
# RKJXT (Alps' STEP model): it stands on a round foot (RKJXT_FOOT across), and a blade slid in from a side stops
# at its terminals, short of the foot. Its base frame (RKJXT_FRAME across) stands on moulded flanges, in Alps'
# model RKJXT_FRAME_GAP over the board, but Alps gives no tolerance on that, so the check is relative: the gap
# under the frame at four spots, against a reference read on a part pressed fully down. Economic variant: the
# same part, before it is soldered. Full variant (soldered by JLCPCB): a loose RKJXT pressed into the footprint of
# a bare board; two parts' flanges may differ by up to 0.02 (assumed: Alps gives nothing). After soldering, at
# every spot the blade (or stack) that slid in on the reference still slides in and that blade plus 0.03 does not:
# no spot stands more than RKJXT_SEAT proud of where it is on a seated part, in either variant (and none lower,
# which check_fit.py does not need).
# Spots: the flanges reach the frame edge (RKJXT_FRAME / 2 off the axis) only over a strip on each side, from
# RKJXT_SPOT["lat"][0] to [1] left of the side's middle seen from outside, the same on all four sides; at the
# middle the flange is set back and a terminal about 0.8 in stops the blade. The blade goes in RKJXT_SPOT["depth"]
# on that strip only, and reads the lowest gap under it. check_fit.py (rkjxt_seat) finds the worst tilt these
# readings let through, the part resting on the far edge of its foot, and lifts the octagon's corners by their
# reach from that edge.
SEAT_GAP = 0.05
EC11_BASE = 11.7                           # PEC11D body across the lug sides
RKJXT_FOOT, RKJXT_FRAME, RKJXT_FRAME_GAP = 13.5, 17.2, 0.40
RKJXT_SPOT = dict(lat=(0.5, 3.0), depth=0.5)
RKJXT_SEAT = 0.05                          # 0.03 + 0.02 with a loose reference part; 0.03 with the part itself
# The RKJXT floats more (radial, worst direction): Alps' STEP model has 0.7 x 0.2 blade terminals and a 0.6 x
# 0.4 frame terminal, the holes are drilled 1.1 and JLCPCB's plating finishes them 1.02 to 1.23, which lets
# the part move 0.26 at most. Its locating lug (dia 1 -0.1, 3.8 and 1.5 +-0.05 off the axis) sits in the
# 1.3 mm NPTH of JLC's footprint (+-0.2): 0.30 plus 0.07 off position, so the terminals bind first. Alps
# recommends 1.1 +0.1/-0 for the lug, which an NPTH at +-0.2 cannot hold (at 0.9 it would not take the lug),
# so the plate gives the part room instead (RANGE_POCKET, RANGE_HOLE).
RKJXT_ON_PINS = 0.26
SLEEVE_CLEAR = 0.9                         # outer knob counterbore around the fixed bushing, radial and above
# Body walls stop short of the plate: the bosses set its height. The smallest gap that never closes: MJF +-0.3 on
# the wall height over the boss tops under the PCB, PCB -0.16, the plate back up to ANODISE / 2 low over bare boss
# ends and bowed towards the walls by PLATE_FLAT (most at the middle of the long walls), and the bosses at their
# lowest: 0.57 at the drawing's +-0.05, 0.62 at JLCCNC's default +-0.1, so 0.65; check_fit.py has the row. A wall
# that touched would take the screw's clamp off the board (docs/architecture/mechanics.md, Fastening).
WALL_GAP = 0.65

# encoder shafts (z above the PCB); "sleeve" is the fixed bushing
EC11_BODY, SLEEVE_TOP, OUTER_TOP, INNER_TOP = 8.0, 13.0, 18.0, 28.0
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
# +0/-0.1, so FIT 0 leaves 0 to 0.1 real clearance on a true print. JLC3DP's resin holes vary by about
# +-0.3, so one of each knob (outer, FMS ring, inner, RANGE) also comes 0.2 tighter and 0.2 looser; a bore
# that is still too tight opens with a drill of the shaft size (6.0, 3.5, 2.5) and a needle file on the D flat.
# A single compliant bore cannot replace the variants: the friction must carry the PEC11D's detent torque (100 +-70
# gf cm, 16.7 N mm at most), which on the inner knob's D flat (1.58 from the axis to its corner) takes a spring
# preload of 10.6 N; over the bore's 0.6 and the shaft's 0.1 such a spring in the SLA resin (E about 2.7 GPa) is
# strained about 7 % at the tight end, the resin's elongation at break, and takes about 70 N to push on.
FIT = 0.0
FIT_VARIANTS = {"tight": -0.2, "loose": 0.2}   # extra outer, FMS, inner and RANGE knob each
# Garmin proportions: outer rings 17 on all three dual knobs, inner knobs 12, so 2.5 of ring shows each side.
# The outer ring ends flush with the 6 mm shaft top: no neck rises into the inner knob, since a recess round a
# neck in a 12 mm knob cannot leave 1.0 of resin on both and still clear a loose knob (check_fit.py). Its bottom
# is 1.09 over the plate, so the slot floor's spread, a high plate face (thick plate on anodised floors, bowed up)
# and its rim dipping on a tilted encoder leave about 0.02.
OUTER_KNOB = dict(d=17.0, z0=1.09, z1=8.0)
# 1.0 over the outer knob when pushed, so the PEC11D's shaft spread (ENC_SPREAD) never makes them touch. The
# recess clears the outer shaft top when the shafts' spread lifts it into the inner knob.
INNER_KNOB = dict(d=12.0, z0=9.5, z1=19.9, recess_d=8.0, recess_top=10.8)
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
# the 3D view alike, chosen so a seated eye sees as much of each as the knobs allow (docs/using/controls.md).
KNOB_LEGEND_TILT = {"ALTHDG": 20, "FREQ": 10, "FMS": 20, "RANGE": 35}

# Legends, the one source for the caps (make_caps.py), the plate (make_plate_art.py), the board silkscreen
# (pcb/board.py) and the 3D view (geometry.js). Only the firmware button map (firmware/buttonmap.py,
# CircuitPython) keeps its own names; tests/test_labels.py checks they agree with these.
# The one amber: SHIFT cap legend, UV print on the plate, the SHIFT light in the 3D view. Pantone and RAL are
# the nearest swatches for the JLCCNC remark (screen values, so approximate). JLCCNC is asked to match it and
# falls back to its standard orange: then this takes that orange, so the caps and the 3D view follow the plate.
AMBER = dict(hex="#d9a441", rgb=(217, 164, 65), ref="Pantone 7563 C, roughly RAL 1004")
# Keys: (cap label, amber shift legend under it) per key, rows top to bottom, columns left to right.
KEY_LEGENDS = [
    [("AP", "TEST"), ("ALT", "ARM"), ("HDG", "CRS CTR"), ("MIC 1", "ADF"), ("COM 1", "NAV 1"), ("CDI", "OBS"),
     ("COM ⇆", "121.5")],
    [("FD", "YD"), ("VS", ""), ("NAV", "GPSS"), ("MIC 2", "DME"), ("COM 2", "NAV 2"), ("VFR", "IDENT"),
     ("NAV ⇆", "ADF ⇆")],
    [("UP", ""), ("FLC", ""), ("APR", "BC"), ("HOME", "UNIT"), ("FPL", "VNAV"), ("D→", "MSG"), ("MENU", "NRST")],
    [("DN", ""), ("VNV", ""), ("LVL", "½ BANK"), ("SHIFT", ""), ("PROC", "TERR"), ("CLR", "MAP"), ("ENT", "")],
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
    "ALTHDG": ("ALT · HDG · PUSH SYNC", "CRS · BARO · PUSH STD"),
    "RANGE": ("RANGE · PUSH PTR", None),
    "FREQ": ("FREQ · PUSH COM/NAV/ADF", "SQUAWK · PUSH XPDR"),
    "FMS": ("FMS · PUSH CRSR", "PANEL · FLOOD · PUSH CABIN"),
}

# RANGE knob on the RKJXT lever; the skirt rim is 1.1 thick (no feather edge in resin: 1.0 left at -0.1)
LEVER_Z0, LEVER_Z1, LEVER_D, LEVER_FLAT = 12.4, 17.4, 2.5, 1.8
RANGE_KNOB = dict(d=13.6, skirt_d=16.6, z0=2.3, z1=11.0, rim=1.1)   # skirt clearance at full tilt: check_fit.py
RANGE_RELIEF = (4.0, 0.3)                  # round bore under its D bore, clear of the lever: dia, least depth
# RANGE artwork on the plate (make_plate_art.py and the 3D view): legend arc radius (glyph centres) and the
# four pan arrows (triangle in mm, tip along the pan direction), outside the skirt with the lever off its hole
# (check_fit.py); the arrow tips stay 0.8 off the legend.
RANGE_ART = dict(legend_r=12.4, arrow_r=10.1, arrow=((0.75, 0.0), (-0.45, -0.7), (-0.45, 0.7)))

# Face-down assembly: the plate rests on two blocks under its long edges, clear of the shafts that stick out.
ASSEMBLY_BLOCK = 25.0                      # block height, mm
# Lights: reverse-mount 1206 LEDs on the bottom (LiteOn LTST-C230KSKT amber, LTW-C230DS white, one package), their
# lens up in a cutout through the board (pcb/board.py LED_CUTOUT, LiteOn's land pattern), so they shine out of the
# top side. LiteOn: the lens is 1.5 long (along the pads) and 1.6 wide, 1.10 - 0.28 = 0.82 over the substrate,
# +-0.1; the die sits on the substrate, at the board underside.
LED_LENS = dict(l=1.5, w=1.6, h=0.82, tol=0.1, place=0.1, solder=0.05, die=0.3)   # place: JLCPCB's placement
# Light pipes (clear resin, JLC3DP SLA): a stepped rod that stands on the board over the cutout and goes up through
# its plate hole, held by geometry alone. The base (base_d) runs from the PCB top to a shoulder base_len up, the rod
# (the light hole less `clear`, 2.0 across: JLC3DP's resin pillar guideline is 2.0 up to 4 mm) top_len from there.
# Every length is +-len_tol (JLC3DP's resin tolerance, 0.2 within 100 mm), and the snap-off stubs under the base are
# sanded flush, no further, so up to `stub` may stay on. Lifted, the shoulder stops on the plate back round the hole,
# so the pipe is captive and never stands proud: top_len + len_tol stays under the thinnest plate. The pipe is never
# clamped either: base_len + len_tol + stub stays under the smallest gap from the board to the plate back (plate back
# low and bowed down, the board bowed up and lifted by a post). A clamp cannot be bounded: the bare board is about
# 13 (SHIFT) and 17 N/mm (UNIT) stiff at the lights, but where a post touches it (the case that closes the gap) 87 and
# 400 N/mm (a plate model of the bare board, ACM elements, clamped at the bosses), so even 0.1 mm would load the
# pipe with 9 to 40 N. In use the pipe rests on the board and its top sits 1.10 under the face in the nominal stack
# (check_fit.py has the range and how much of it shows from the seat). The rod is `clear` under its hole on the
# diameter: anodising (0.05) and the resin tolerance (+-0.2) cannot make it jam. The base (2.8 across) is wider than
# the cutout, so it stands on the board, and narrow enough to stay out from under the key holes (a firmly pressed cap
# dips under the plate back) and clear of the switch bodies (check_fit.py). The light holes' back edges are sharp,
# deburred only (LIGHT_HOLE_BACK_BREAK at most), so the shoulder sits on the flat back face. Both pipes print on one
# 2.2 x 2.0 bar under their bases (JLC3DP's resin parts start at 10 x 2 x 2 mm), on 1.0 necks (the resin minimum), so
# the visible tops are as printed.
PIPE = dict(base_d=2.8, base_len=5.35, top_len=3.65, len_tol=0.2, stub=0.1, clear=0.3, neck_d=1.0, neck_len=0.6,
            bar=(2.2, 2.0), resin=RESIN_TOL["size"], anodise=ANODISE, z0=0.0)
LIGHT_HOLE_BACK_BREAK = 0.05
PIPE["len"] = PIPE["base_len"] + PIPE["top_len"]
# Through-hole leads below the PCB, untrimmed: the keys' 3.51 +-0.30 (TE drawing) stand 2.37 under a board 0.16 thin
# at most, the PEC11D terminals about 1.9 (+0.3), the RKJXT's about 1.6; plus up to 0.3 of solder at a tip. Nothing
# is trimmed: check_fit.py checks this against the room under the board.
LEAD_MAX = 2.7
# PCB bow, either way, at its middle (the two lights sit near the middle of the 153 mm span between the corner
# screws). JLCPCB, like IPC-6012, allows 0.75 % bow and twist for SMT boards (1.2 mm over 160 mm); a 4-layer 1.6 mm
# board is usually far flatter. The light pipe rows and the pocket rows over the encoders and the RKJXT take this
# much, shaped like the plate's bow (check_fit.plate_bow, the board is held at the same four mounts).
PCB_BOW = 0.1
# The plate is held at its corners as well, so its flatness counts the same way: "flatness 0.1" on the drawing,
# after bead blasting and anodising (milling most of a 12 mm plate off one side and blasting it can bow it; ISO
# 2768-K alone would allow 0.4 over its 165 mm), either way. check_fit.py moves the plate at a part by that times
# its plate_bow() (a dome, or a bow along or across the plate, held at the bosses), in the direction that costs the
# row. The light pipe rows take PLATE_FLAT in full. Every row still passes up to about 0.17 (the light pipes' clamp
# goes first, then the body walls at 0.19), bar the cosmetic cap socket ceiling, which may then stand up to 0.05
# above the face on a plunger 0.3 high; that is what to answer should JLCCNC ask, but not with the bosses at +-0.1
# as well: then flatness up to about 0.12 (docs/building/building.md).
PLATE_FLAT = 0.1
# The two body posts under the middle of the PCB (make_mech.py) end SUPPORT_SHORT under it, so with JLC3DP's
# MJF +-0.3 (post height against the bosses) they lift the board by at most SUPPORT_LIFT; a firm press bends it
# onto them.
SUPPORT_SHORT = 0.25
SUPPORT_LIFT = max(0.0, MJF_TOL - SUPPORT_SHORT)
# A firm key press (PRESS_FIRM, about six times the switch's 1.6 N) on the bare board, from a Kirchhoff plate model
# of it (1.6 mm FR4 at 20 GPa, no stiffening by the parts, clamped at the four mounts between plate and body boss
# (with pinned mounts a normal press would sag it about 0.3), the posts up to SUPPORT_SHORT
# + 0.3 short and pushing only up): the pressed key dips up to 0.69 (the front and back rows, 18 mm from the
# posts, which do not stop them) and the board under any key slopes up to 13.8 mrad. A normal 1.6 N press sags
# it about 0.12 and 2.3 mrad. check_fit.py takes both 10 % up (FR4's flexural modulus, about 18 to 24 GPa; 18 GPa
# would need 11 %, about 0.008 mm more).
PRESS_FIRM = 10.0                          # N
PRESS_DIP, PRESS_SLOPE = 0.69 * 1.1, 0.0138 * 1.1
