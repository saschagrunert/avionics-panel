"""Mechanical stack of the Avionics Panel rev 1: one place for every height and fit.

z = 0 is the PCB top. Part heights from the datasheets:
  Bourns PEC11D-4120F-S0015 (dual encoder): body 8 mm (11.7 x 12), unthreaded bushing dia 7 up to 13, outer
      shaft dia 6 with a 2 mm slot 2.5 deep up to 18, inner shaft dia 3.5 up to 28 with a D flat (2.5
      across) on its last 7 mm. The inner shaft pushes (stroke 0.5 +0/-0.3).
  Alps RKJXT1F42001 (RANGE): octagonal body 17 across corners, 8.6 high, hub up to 10.5, lever dia 2.5
      with a 1.8 D flat from 12.4 to 17.4, tilts 9 degrees, push stroke 0.3.
  TE 1-1825910-4 keys (FSM8JH, 6 x 6 mm): plunger dia 3.10, top at 9.5. XINGLIGHT XL-302 LEDs: about 5.3 high.

Front plate: 4 mm aluminium at z 6..10, pockets milled from below for the encoder and RANGE bodies,
4 blind M2.5 threads from below (thread milled in a flat-bottom hole, 0.7 mm of material left in front).
Screws M2.5 x 12 (pan head, shimmed to fit) from under the body: body boss -> PCB -> 6 mm metal spacer ->
plate; the spacers alone set the plate height, the body walls stop 0.9 mm short of the plate. No fastener
shows on the front.
"""
# datasheet values the generators share
PLUNGER_TOP, PLUNGER_D = 9.5, 3.10         # TE 1-1825910-4 key plunger: top above the PCB, dia (+-0.30)
KEY_TRAVEL = 0.35                          # TE 1-1825910-4 travel 0.25 +-0.1
RKJXT_BODY, RKJXT_HUB_TOP, RKJXT_TILT = 8.6, 10.5, 9.0   # Alps RKJXT1F42001: body and hub top, tilt (deg)
BODY_TILT = 6.0                            # body wedge (deg)
# key cap: outline, height and top chamfer; socket 3.0 deep, so its bottom is at 6.5
CAP = dict(w=9.6, h=6.4, r=1.2, height=6.0, cham=0.45, base=PLUNGER_TOP - 3.0)
# tactile bars on SHIFT, DN (front edge) and UP (back edge): closed box, 0.35 proud, sunk 0.05 into the top
CAP_BAR = dict(w=3.2, d=0.55, proud=0.35, sink=0.05, inset=0.75)
# Key cap socket for the full-colour resin (JLC3DP WJP: +-0.2 within 100 mm, holes +-0.1 to 0.2, embossed
# detail 0.8 mm min.). Three ribs 0.8 wide at the tip and 0.3 high in a 3.6 mm bore, tips on a 3.05 mm circle:
# about 0.05 mm grip on a nominal 3.10 plunger. Rigid resin does not crush much, so this grips plungers of
# about 3.05 to 3.25 when the print comes out true; the +-0.30 datasheet range is wider than any rigid socket
# covers. Measure a plunger and test-print one cap first.
CAP_SOCKET = dict(d=3.6, rib_d=3.05, ribs=3, tip_w=0.8, base_w=1.2, depth=PLUNGER_TOP - CAP["base"])
PCB_T = 1.6
PLATE_Z0, PLATE_Z1 = 6.0, 10.0           # 4 mm 6061; the plate top is where it always was
PLATE_T_TOL = 0.1                          # 4.0 +-0.1 on the drawing (ISO 2768-m); depths go from the back
PLATE_T = PLATE_Z1 - PLATE_Z0
OVH = 2.3                                  # plate and body overhang the PCB by clearance + wall

# through holes in the plate
KEY_HOLE = (10.2, 7.0, 1.4)                # caps are 9.6 x 6.4: 0.3 per side, see the cap budget below
SHAFT_HOLE = 7.6                           # encoder bushing dia 7
RANGE_HOLE = 12.0                          # RKJXT lever + hub, hidden under the knob skirt
LIGHT_HOLES = {"SHIFT": 1.8, "UNIT": 1.6}  # light pipes; webs to the neighbouring key holes in check_fit.py

# pockets milled from the back
# w, h, corner r, depth (body 11.7 x 12 x 8.0 +-0.3, lugs, terminal blocks; pins at +-9.5): 1.2 mm left.
# Depths +0/-POCKET_TOL on the drawing: never deeper, so the front stays; check_fit uses the shallow end.
EC11_POCKET = (14.8, 20.0, 2.0, 2.8)
RANGE_POCKET = (18.4, 3.2)                 # dia, depth (body 17 across corners, 8.6 high): 0.8 mm left
POCKET_TOL = 0.1

# fasteners: hidden M2.5 pan-head screws from below, shimmed to fit with 0.5 mm washers
# Plate: blind M2.5 from the back, thread milled in a flat-bottom hole (no tap lead). Floor 3.2 +0/-0.1
# deep, so at least 0.7 mm of aluminium stays in front of the 3.9 mm thinnest plate; full thread from 0.1
# under the back face (deburr, no countersink) to at least 2.6, which leaves the thread mill 0.5 to 0.6 of
# runout. A screw may stop anywhere from the end of the full thread (2.6 at worst) to the floor.
PITCH = 0.45
TAP = dict(size="M2.5", drill=2.05, hole_depth=3.2, depth_tol=0.1, thread_depth=2.6, entry=0.1)
# Screw: M2.5 x 12 pan head (ISO 7045 or ISO 14583: dk 5.0 (4.7 min), k 1.75), length js15 (+-0.35, ISO
# 4759-1 grade A). The end has up to 2P of incomplete thread (ISO 4753), which carries no load. Socket heads
# (k 2.5) do not fit under four washers at the front corners.
SCREW = dict(d=2.5, d_min=2.38, L=12.0, L_tol=0.35, tip=2 * PITCH, head_d=5.0, head_d_min=4.7, head_k=1.75)
SCREW_D, SCREW_L = SCREW["d"], SCREW["L"]
# One washer type, DIN 125-A (ISO 7089) M3 (3.2 x 7.0 x 0.5; bore H13 to 3.38, OD h14 to 6.64) on the M2.5
# screw. The counterbore round it is only a little wider, so its wall, not the screw, keeps the washer
# centred over the body hole: then it bears all round the hole even with the screw against the hole wall,
# which a 6 mm M2.5 washer that slides 0.23 on the screw does not. One always goes under the head. Shim to
# fit: tighten; if the screw stops before the parts clamp, it has bottomed, so add a washer and try again.
# The shortest stack clamps on the head washer alone, the longest takes up to three more.
WASHER = dict(od=7.0, od_min=6.64, bore_max=3.38, t=0.5)
# Stack from the counterbore seat to the plate back (each +-): seat to boss top (JLC3DP MJF +-0.3 within 100
# mm), PCB 1.6 +-10 %, turned metal spacer 6.0 +-0.05.
STACK_TOL = dict(counterbore=0.3, pcb=0.16, spacer=0.05)
SEAT_Z = -2.5                              # counterbore seat (top of the counterbore, the boss underside)
ENGAGE_MIN = 2 * PITCH                     # full thread on both parts, at least 2 turns
WASHERS_MAX = 4                            # per screw, head washer included: 16 in the order plus spares
# nominal head bearing (for the 3D view): nominal stack with the head washer and one more
SCREW_HEAD_Z = SEAT_Z - 2 * WASHER["t"]
# Positional budget (each +-, radial unless noted): plate threads and through holes to each other (drawing
# note), PCB drill positions (JLCPCB, about 0.05; 0.075 assumed), NPTH size (JLCPCB +-0.2 on the diameter),
# M2.5 in its thread, the board offset the caps allow (their largest shift in the key holes, about 0.34
# diagonally, plus 0.05 of key pattern to screw pattern), the body over 153 mm (JLC3DP MJF +-0.4 % above
# 100 mm, so +-0.31 in x and +-0.11 in y per hole once the screws centre it) and its hole size (MJF, radial).
POS_TOL = dict(plate=0.1, pcb=0.075, npth_d=0.2, thread=0.03, centring=0.05, body=0.33, body_hole=0.15)
# The caps centre the board in the key holes during assembly; the screws then must not pull it off centre.
# Per-key errors that stay (RSS): switch holes on the PCB, switch on its pins, key hole on the plate, cap
# outline (WJP +-0.2 on size, half per side), cap on its plunger.
CAP_TOL = dict(pcb=0.075, switch=0.15, plate=0.1, cap=0.1, socket=0.05)
SLEEVE_CLEAR = 0.4                         # outer knob counterbore around the fixed bushing, radial and above
WALL_GAP = 0.9                             # body walls stop short of the plate: the spacers set its height
# PCB top to plate bottom. Buy metal round spacers (aluminium or brass, 5 OD, about 2.7 ID, 6.0 +-0.05
# long): 5 mm stays inside the 3.6 mm copper keep-out with the board offset and the spacer's play on the
# screw (ID up to 2.8). The printed spacer (make_mech.py, ID 2.8 for the print) is the fallback.
SPACER = dict(od=5.0, od_min=4.95, id=2.8, id_max=2.8, length=PLATE_Z0)

# encoder shafts (z above the PCB); "sleeve" is the fixed bushing
EC11_BODY, SLEEVE_TOP, OUTER_TOP, INNER_TOP = 8.0, 13.0, 18.0, 28.0
SLEEVE_D, OUTER_D, INNER_D, INNER_FLAT, FLAT_LEN, SLOT_W, SLOT_LEN = 7.0, 6.0, 3.5, 2.5, 7.0, 2.0, 2.5
PUSH_TRAVEL = 0.5

# knobs (heights above the plate top); resin, fits to test on the first print
# FIT is added to the datasheet nominal of bores that must grip. The shafts are toleranced +0/-0.05 and
# +0/-0.1, so a 0.05 FIT left 0.05 to 0.15 real clearance. FIT 0 centres the bores on 0 to 0.1, about the
# 0.05 allowance first intended for a mid-tolerance shaft; the variants sit 0.1 either side.
FIT = 0.0
FIT_VARIANTS = {"tight": -0.1, "loose": 0.1}   # extra outer, inner and RANGE knob each: resin prints vary
# Garmin proportions: outer rings 17 on all three, inner knobs 12, so 2.5 of ring shows each side. The outer
# knob's neck (8.3) leaves 1.15 of resin round its 6 mm bore (1.1 on the loose variant); the inner knob's
# recess (9.2) clears it by 0.45 radially and leaves 1.0 at its flute bottoms (1.35 at the crests).
OUTER_KNOB = dict(z0=0.8, z1=8.0, neck_d=8.3, neck_top=8.6)
INNER_KNOB = dict(d=12.0, z0=8.8, z1=19.2, recess_d=9.2, recess_top=10.1)     # recess clears the neck (8.6) when pushed
KNOB_D = {"ALTHDG": 17.0, "FREQ": 17.0, "FMS": 17.0}
# knob legends: degrees their arc is turned from the horizontal towards the user, for the plate artwork and
# the 3D view alike, chosen so a seated eye sees as much of each as the knobs allow (docs/controls.md).
KNOB_LEGEND_TILT = {"ALTHDG": 20, "FREQ": 10, "FMS": 20, "RANGE": 35}

# Legends, the one source for the caps (make_caps.py), the plate (make_plate_art.py), the board silkscreen
# (pcb/board.py) and the 3D view (geometry.js). Only the firmware button map (firmware/buttonmap.py,
# CircuitPython) keeps its own names; tests/test_labels.py checks they agree with these.
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

# Knobs: (white legend, amber legend with SHIFT or None): what the rings do, outer first, then the push.
KNOB_LEGENDS = {
    "ALTHDG": ("ALT · HDG · PUSH SYNC", "CRS · BARO · PUSH STD"),
    "RANGE": ("RANGE · PUSH PTR", None),
    "FREQ": ("FREQ · PUSH COM/NAV/ADF", "SQUAWK · PUSH XPDR"),
    "FMS": ("FMS · PUSH CRSR", "PANEL · FLOOD · PUSH CABIN"),
}

# RANGE knob on the RKJXT lever
LEVER_Z0, LEVER_Z1, LEVER_D, LEVER_FLAT = 12.4, 17.4, 2.5, 1.8
RANGE_KNOB = dict(d=13.6, skirt_d=15.6, z0=1.8, z1=11.0)   # skirt clears the plate by about 0.5 mm at full tilt

# Face-down assembly: the plate rests on two blocks under its long edges, clear of the shafts that stick out.
ASSEMBLY_BLOCK = 25.0                      # block height, mm
# Light pipes (clear resin) are glued into the plate, top flush with the face (pushed in from the back against
# tape on the front, a drop of clear epoxy or UV glue at the back; not CA, it fogs clear resin). Under the
# 4 mm plate only 0.7 mm is left above the LED, too little for a collar that never touches the plate. XL-302
# top at 5.3 +0.4/-0.1 (hand-soldered THT: seated up to 0.3 proud, body +-0.1); pipe length +-0.1 (SLA),
# plate 4.0 +-0.1, spacer +-0.05: the pipe bottom stays at least 0.1 over the highest LED in the thinnest
# stack, so the PCB never pushes on it.
LED_TOP, LED_TOL = 5.3, (0.4, 0.1)
PIPE = dict(len=3.95, len_tol=0.1, clear=0.08, neck_d=0.6)
PIPE["z0"] = PLATE_Z1 - PIPE["len"]        # 6.05: pipe bottom
