"""Mechanical stack of the Avionics Panel rev 1: one place for every height and fit.

z = 0 is the PCB top. Part heights from the datasheets:
  Bourns PEC11D-4120F-S0015 (dual encoder): body 8 mm (11.7 x 12), unthreaded bushing dia 7 up to 13, outer
      shaft dia 6 with a 2 mm slot 2.5 deep up to 18, inner shaft dia 3.5 up to 28 with a D flat (2.5
      across) on its last 7 mm. The inner shaft pushes (stroke 0.5 +0/-0.3). Tolerances +-0.3 under 10 mm,
      +-0.5 from 10 mm.
  Alps RKJXT1F42001 (RANGE): octagonal body 17 across corners, 8.6 high, hub dia 7.2 up to 10.0 (chamfered
      to 10.5, Alps' STEP model), lever dia 2.5 with a 1.8 D flat from 12.4 to 17.4, tilts 9 degrees about a
      fulcrum 5.55 above the PCB, push stroke 0.3 +-0.2.
  TE 1-1825910-4 keys (FSM8JH, 6 x 6 mm): plunger top at 9.5, switch body top 5.90 below it, a round plunger
      that tapers about 2 degrees per side (TE's STEP model, see PLUNGER). XINGLIGHT XL-302 LEDs: about 5.3 high.

Front plate: 4 mm aluminium at z 6..10, pockets milled from below for the encoder and RANGE bodies and 4
flat-bottom pockets for glued standoffs; no threads, nothing on the front. Four M2.5 x 8 female-female hex
standoffs (5 mm across flats) are glued with non-sag epoxy into those pockets, already screwed onto the
assembled board, so the board itself is the jig; M2.5 x 8 pan-head screws come from under the body: body
boss -> PCB -> standoff thread. The standoffs alone set the plate height (standoff
length less pocket depth), the body walls stop 0.9 mm short of the plate.
"""
# datasheet values the generators share
# TE 1-1825910-4 key plunger, from TE's own STEP model of the part (dz below the plunger top): a flat top of
# radius 1.26 with a 0.3 edge radius, dia 3.12 at dz 0.29, then a cone (about 2 degrees per side) to dia 3.51
# at the switch body top (dz 5.90; the PCB is at dz 9.50). TE gives no tolerance on it.
PLUNGER_TOP = 9.5                          # above the PCB
PLUNGER = dict(top_r=1.26, edge_r=0.3, dz0=0.29, d0=3.12, dz1=5.90, d1=3.51)
PLUNGER_TOP_TOL = 0.2                      # plunger height, assumed (TE gives none; usual for 6 x 6 switches)
SWITCH_BODY_TOP = PLUNGER_TOP - PLUNGER["dz1"]   # 3.6


def plunger_d(dz):
    """plunger diameter dz below its top, on the cone (dz from 0.29 down to the switch body, 5.90)."""
    p = PLUNGER
    return p["d0"] + (p["d1"] - p["d0"]) * (dz - p["dz0"]) / (p["dz1"] - p["dz0"])


KEY_TRAVEL = 0.35                          # TE 1-1825910-4 travel 0.25 +-0.1
RKJXT_BODY, RKJXT_HUB_TOP, RKJXT_TILT = 8.6, 10.5, 9.0   # Alps RKJXT1F42001: body and hub top, tilt (deg)
RKJXT_FULCRUM = 5.55                       # Alps RKJXT1F42001: tilt fulcrum above the PCB (datasheet)
RKJXT_HUB = (7.2, 10.0)                    # Alps' STEP model: hub dia and the top of its full width (chamfer above)
RANGE_PUSH = (0.3, 0.2)                    # Alps RKJXT1F42001 push stroke 0.3 +-0.2
LEVER_TOL = 0.3                            # Alps RKJXT1F42001 lever height, +-
BODY_TILT = 6.0                            # body wedge (deg)
# key cap: outline, height and top chamfer; it sits with its socket ceiling on the plunger top and the socket
# is 2.7 deep, so its bottom is at 6.8 and a pressed cap (travel up to 0.35, plunger up to 0.2 low) still
# ends inside its key hole over the highest plate back
CAP = dict(w=9.6, h=6.4, r=1.2, height=5.7, cham=0.45, base=PLUNGER_TOP - 2.7)
# tactile bars on SHIFT, DN (front edge) and UP (back edge): closed box 1.0 wide (JLC3DP embossed detail: 0.8),
# sunk 0.05 into the top, its outer side 0.1 inside the top face. Only 0.5 proud, below JLC3DP's 0.8 for
# embossed detail (a solid 3.2 x 1.0 ridge, not fine detail): a taller front bar hides the bottom of the SHIFT
# and DN legends from the seat; check_fit.py proves it hides none at 45 deg (a review watch item, docs/status.md)
CAP_BAR = dict(w=3.2, d=1.0, proud=0.5, sink=0.05, inset=0.6)
CAP_VIEW_DEG = 45.0                        # seated eye over the cap tops: about 42 deg at a desk plus the 6 deg wedge
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
# where they never show.
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
PLATE_Z0, PLATE_Z1 = 6.0, 10.0           # 4 mm 6061; the plate top is where it always was
PLATE_T_TOL = 0.1                          # 4.0 +-0.1 on the drawing (ISO 2768-m); depths go from the back
PLATE_T = PLATE_Z1 - PLATE_Z0
OVH = 2.5                                  # plate and body overhang the PCB by clearance + wall

# through holes in the plate
KEY_HOLE = (10.2, 7.0, 1.4)                # caps are 9.6 x 6.4: 0.3 per side, see the cap budget below
KEY_HOLE_TOL = (0.1, 0.0)                  # +0.1/-0 after anodising on the drawing: never under 0.3 per side
# general tolerance ISO 2768-m (+-0.2 from 6 to 30 mm) where the drawing gives none
PLATE_GEN_TOL = 0.2
SHAFT_HOLE = 9.2                           # encoder bushing dia 7 +0.3: clears the board offset, hidden by the knob
RANGE_HOLE = 11.2                          # RKJXT hub (7.2) at full tilt, hidden under the knob skirt (check_fit)
LIGHT_HOLES = {"SHIFT": 1.8, "UNIT": 1.6}  # light pipes; webs to the neighbouring key holes in check_fit.py
LIGHT_HOLE_TOL = (0.1, 0.0)                # +0.1/-0 on the drawing: never smaller, so a pipe cannot jam

# pockets milled from the back
# w, h, corner r, depth (body 11.7 x 12 x 8.0 +-0.3, lugs, terminal blocks; pins at +-9.5): 1.2 mm of plate
# left over it (1.1 on a thin plate).
# Depths +0/-POCKET_TOL on the drawing: never deeper, so the front stays; check_fit uses the shallow end.
EC11_POCKET = (14.8, 20.0, 2.0, 2.8)
RANGE_POCKET = (19.6, 3.2)                 # dia, depth (body 17 across corners, 8.6 high): 0.8 left (0.7 thin)
RANGE_POCKET_R = 0.3                       # most floor corner radius: body corners 0.17 / 0.10 off wall / floor
RKJXT_ACROSS, RKJXT_TOL = 17.0, 0.3        # octagon across corners; tolerance assumed (as on its height)
POCKET_TOL = 0.1

# ---- fasteners: glued standoffs in the plate, hidden M2.5 pan-head screws from below ----
# Standoff: M2.5 female-female hex, 5 mm across flats (4.9 min), 5.77 across corners, 8.0 +-0.1 long, brass
# or aluminium, threaded through; the thread entry is chamfered (about 0.3).
PITCH = 0.45
STANDOFF = dict(thread="M2.5", af=5.0, af_min=4.9, ac=5.77, L=8.0, L_tol=0.1, chamfer=0.3)
# Round flat-bottom pocket in the plate back: 7.0 +0.1/-0 wide, so a standoff on the assembled board (screw
# a quarter turn back, so it can still slide by the screw's play in the PCB hole) enters it wherever the caps
# put the board: about 0.6 of float round the corners, the 0.6 to 1.0 gap filled by non-sag epoxy buttered on
# the hex sides. 2.0 +0/-0.1 deep, which leaves at least 1.9 mm of aluminium in front. The last 0.5 of the
# standoff end stays bare and the floor dry, and the weight of board and body seats the end on the bare floor,
# so the gap from the PCB top to the plate back is the standoff length less the pocket depth: 6.0 +0.2/-0.1.
# A smaller pocket (6.8) would even out the glue gap a little but leave only 0.08 of float to spare.
STANDOFF_POCKET = dict(d=7.0, d_tol=0.1, depth=2.0, depth_tol=0.1, bare=0.5)
# The plate end of each standoff is plugged while it is glued, so no epoxy gets into its thread: soft wax or
# plasticine pressed into the thread at most 2 mm deep (a toothpick marked at 2 mm), the end face scraped
# clean. A grub screw would do too, but the shortest common M2.5 one (3 mm) can meet the screw tip.
PLUG_DEPTH = 2.0
GAP_TOL = (STANDOFF["L_tol"] + STANDOFF_POCKET["depth_tol"], STANDOFF["L_tol"])   # (+, -) on PLATE_Z0
assert abs(STANDOFF["L"] - STANDOFF_POCKET["depth"] - PLATE_Z0) < 1e-9
# PCB mounting hole (pcb/board.py MOUNT_HOLE) the glued standoffs need: the screw through it lines the
# standoff up with the hole while the epoxy cures, and keeps it there on every reassembly, within the hole's
# play (2.8 to 3.2 with JLCPCB's +-0.2 on NPTH, M2.5 2.38 to 2.5): the standoff end then covers the hole all
# round and its corners stay inside the 3.6 mm copper keep-out. check_fit.py checks the board's value.
PCB_HOLE = 3.0
# Screw: M2.5 x 8 pan head (ISO 7045 or ISO 14583: dk 5.0 (4.7 min), k 1.75), length js15 (+-0.29, ISO
# 4759-1 grade A). The end has up to 2P of incomplete thread (ISO 4753), which carries no load.
SCREW = dict(d=2.5, d_min=2.38, L=8.0, L_tol=0.29, tip=2 * PITCH, head_d=5.0, head_d_min=4.7, head_k=1.75)
SCREW_D, SCREW_L = SCREW["d"], SCREW["L"]
# One DIN 125-A (ISO 7089) M3 washer (3.2 x 7.0 x 0.5 +-0.05; bore H13 to 3.38, OD h14 to 6.64) under each
# head. The counterbore round it is only a little wider, so its wall, not the screw, keeps the washer
# centred over the body hole: then it bears all round the hole even with the screw against the hole wall,
# which a pan head alone or a 6 mm M2.5 washer that slides 0.23 on the screw does not.
WASHER = dict(od=7.0, od_min=6.64, bore_max=3.38, t=0.5, t_tol=0.05)
# Stack from the counterbore seat to the PCB top (each +-): seat to boss top (JLC3DP MJF +-0.3 within 100
# mm), PCB 1.6 +-10 %.
STACK_TOL = dict(counterbore=0.3, pcb=0.16)
SEAT_Z = -3.2                              # counterbore seat: 1.6 of PA12 up to the PCB (1.3 at MJF -0.3)
ENGAGE_MIN = 2.0                           # full thread engaged in the standoff, mm (about 4 turns)
SCREW_HEAD_Z = SEAT_Z - WASHER["t"]        # nominal head bearing (for the 3D view)
# Positional budget (each +-, radial unless noted): pockets and through holes to each other (drawing
# note), PCB drill positions (JLCPCB, about 0.05; 0.075 assumed), NPTH size (JLCPCB +-0.2 on the diameter),
# M2.5 in its thread, the board offset the caps allow (their largest shift in key holes at +0.1, about 0.40
# diagonally, plus 0.05 of key pattern to screw pattern), the body over 153 mm (JLC3DP MJF +-0.4 % above
# 100 mm, so +-0.31 in x and +-0.11 in y per hole once the screws centre it) and its hole size (MJF, radial).
POS_TOL = dict(plate=0.1, pcb=0.075, npth_d=0.2, thread=0.03, centring=0.05, body=0.33, body_hole=0.15)
# The caps centre the board in the key holes during assembly; the screws then must not pull it off centre.
# Per-key errors that stay (RSS): switch holes on the PCB, switch on its pins, key hole on the plate, cap
# outline (WJP +-0.2 on size, half per side), cap on its plunger.
CAP_TOL = dict(pcb=0.075, switch=0.15, plate=0.1, cap=0.1, socket=0.05)
ENC_ON_PINS = 0.15                         # encoder (bushing) on its pins and lugs before soldering, radial
# The RKJXT floats more (radial, worst direction): Alps' STEP model has 0.7 x 0.2 blade terminals and a 0.6 x
# 0.4 frame terminal, the holes are drilled 1.1 and JLCPCB's plating finishes them 1.02 to 1.23, which lets
# the part move 0.26 at most. Its locating lug (dia 1 -0.1, 3.8 and 1.5 +-0.05 off the axis) sits in the
# 1.3 mm NPTH of JLC's footprint (+-0.2): 0.30 plus 0.07 off position, so the terminals bind first. Alps
# recommends 1.1 +0.1/-0 for the lug, which an NPTH at +-0.2 cannot hold (at 0.9 it would not take the lug),
# so the plate gives the part room instead (RANGE_POCKET, RANGE_HOLE).
RKJXT_ON_PINS = 0.26
SLEEVE_CLEAR = 0.9                         # outer knob counterbore around the fixed bushing, radial and above
WALL_GAP = 0.9                             # body walls stop short of the plate: the standoffs set its height

# encoder shafts (z above the PCB); "sleeve" is the fixed bushing
EC11_BODY, SLEEVE_TOP, OUTER_TOP, INNER_TOP = 8.0, 13.0, 18.0, 28.0
SLEEVE_D, OUTER_D, INNER_D, INNER_FLAT, FLAT_LEN, SLOT_W, SLOT_LEN = 7.0, 6.0, 3.5, 2.5, 7.0, 2.0, 2.5
PUSH_TRAVEL = 0.5
# PEC11D tolerances: +-0.3 for dimensions under 10 mm, +-0.5 from 10 mm. The outer knob rests with its key on
# the slot floor (18 - 2.5), the inner knob on the inner shaft tip (28): RSS spreads of their heights, against
# each other and against the bushing top (13). From the PCB the slot floor is body 8 (+-0.3) + shaft 10 (+-0.5)
# - slot 2.5 (+-0.3).
ENC_TOL = dict(lt10=0.3, ge10=0.5)
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
FIT = 0.0
FIT_VARIANTS = {"tight": -0.2, "loose": 0.2}   # extra outer, FMS, inner and RANGE knob each
# Garmin proportions: outer rings 17 on all three dual knobs, inner knobs 12, so 2.5 of ring shows each side.
# The outer ring ends flush with the 6 mm shaft top: no neck rises into the inner knob, since a recess round a
# neck in a 12 mm knob cannot leave 1.0 of resin on both and still clear a loose knob (check_fit.py).
OUTER_KNOB = dict(d=17.0, z0=1.0, z1=8.0)
# 1.0 over the outer knob when pushed, so the PEC11D's shaft spread (ENC_SPREAD) never makes them touch. The
# recess clears the outer shaft top when the shafts' spread lifts it into the inner knob.
INNER_KNOB = dict(d=12.0, z0=9.5, z1=19.9, recess_d=8.0, recess_top=10.8)
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
# the 3D view alike, chosen so a seated eye sees as much of each as the knobs allow (docs/controls.md).
KNOB_LEGEND_TILT = {"ALTHDG": 20, "FREQ": 10, "FMS": 20, "RANGE": 35}

# Legends, the one source for the caps (make_caps.py), the plate (make_plate_art.py), the board silkscreen
# (pcb/board.py) and the 3D view (geometry.js). Only the firmware button map (firmware/buttonmap.py,
# CircuitPython) keeps its own names; tests/test_labels.py checks they agree with these.
# The one amber: SHIFT cap legend, UV print on the plate, the SHIFT light in the 3D view. Pantone and RAL are
# the nearest swatches for the JLCCNC remark (screen values, so approximate).
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
# RANGE artwork on the plate (make_plate_art.py and the 3D view): legend arc radius (glyph centres) and the
# four pan arrows (triangle in mm, tip along the pan direction), outside the skirt with the lever off its hole
# (check_fit.py); the arrow tips stay 0.8 off the legend.
RANGE_ART = dict(legend_r=12.4, arrow_r=10.1, arrow=((0.75, 0.0), (-0.45, -0.7), (-0.45, 0.7)))

# Face-down assembly: the plate rests on two blocks under its long edges, clear of the shafts that stick out.
ASSEMBLY_BLOCK = 25.0                      # block height, mm
# Light pipes (clear resin) are glued into the plate, top flush with the face (pushed in from the back against
# a card held on the front, clear epoxy or UV glue in the gap round it at the back; not CA, it fogs clear
# resin). Under the 4 mm plate only 0.7 mm is left above the LED, too little for a collar that never touches
# the plate. XL-302 top at 5.3 +0.3/-0.1 (hand-soldered THT: seated up to 0.2 proud, body +-0.1); pipe length
# +-0.1 (SLA), plate 4.0 +-0.1 and down to PLATE_FLAT out of flat, gap 6.0 -0.1, the PCB lifted by a support
# post (SUPPORT_SHORT) and bowed up by PCB_BOW at the LEDs: the pipe bottom stays over the highest LED in the
# thinnest stack, so the PCB never pushes on it. The pipes are 3.6 long, so they end 0.4 inside the plate back.
# The pipes are glued, so they sit 0.3 under their holes (+0.1/-0) on the diameter: anodising (0.05) and
# JLC3DP's resin tolerance (+-0.2) cannot make them jam. Necks 1.1 (resin pillars 1.0 min.), on a 2.2 x 2.0
# bar. The pipes themselves (1.3 and 1.5 across, 3.6 long) are longer than JLC3DP's resin pillar guideline
# (1.0 across up to 1 mm, 2.0 up to 4 mm); the fallback is PMMA end-glow fibre (docs/ordering.md).
LED_TOP, LED_TOL = 5.3, (0.3, 0.1)
# PCB bow towards the plate at the two LEDs (both near the middle of the 153 mm span between the corner
# screws). JLCPCB, like IPC-6012, allows 0.75 % bow and twist for SMT boards (1.2 mm over 160 mm), which no
# stack here could take; a 4-layer 1.6 mm board is usually far flatter. The LED under the plate back budgets
# PCB_BOW, and the board is checked against it on arrival (docs/status.md): a board bowed more gets its LEDs
# seated flat, which gives back the 0.2 a proud LED is allowed.
PCB_BOW = 0.1
# The plate is held at its corners as well, so its flatness counts the same way: "flatness 0.1" on the drawing,
# after bead blasting and anodising (blasting one side can bow a thin plate; ISO 2768-K alone would allow 0.4
# over its 165 mm).
PLATE_FLAT = 0.1
PIPE = dict(len=3.6, len_tol=0.1, clear=0.3, neck_d=1.1, neck_len=0.6, bar=(2.2, 2.0), resin=0.2, anodise=0.05)
# The two body posts under the middle of the PCB (make_mech.py) end SUPPORT_SHORT under it, so with JLC3DP's
# MJF +-0.3 (post height against the bosses) they lift the board by at most SUPPORT_LIFT; a key press still
# bends it onto them.
SUPPORT_SHORT = 0.25
SUPPORT_LIFT = max(0.0, 0.3 - SUPPORT_SHORT)
PIPE["z0"] = PLATE_Z1 - PIPE["len"]        # 6.1: pipe bottom
