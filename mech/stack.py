"""Mechanical stack of the Avionics Panel rev 1: one place for every height and fit.

z = 0 is the PCB top. Part heights from the datasheets:
  Bourns PEC11D-4120F-S0015 (dual encoder): body 8 mm (11.7 x 12), unthreaded bushing dia 7 up to 13, outer
      shaft dia 6 with a 2 mm slot 2.5 deep up to 18, inner shaft dia 3.5 up to 28 with a D flat (2.5
      across) on its last 7 mm. The inner shaft pushes (stroke 0.5 +0/-0.3).
  Alps RKJXT1F42001 (RANGE): octagonal body 17 across corners, 8.6 high, hub up to 10.5, lever dia 2.5
      with a 1.8 D flat from 12.4 to 17.4, tilts 9 degrees, push stroke 0.3.
  TE 1-1825910-4 keys (FSM8JH, 6 x 6 mm): plunger dia 3.10, top at 9.5. XINGLIGHT XL-302 LEDs: about 5.3 high.

Front plate: 3 mm aluminium at z 7..10, pockets milled from below for the encoder and RANGE bodies,
4 blind M2.5 threads from below (0.8 mm of material left in front of the drill point; tighten gently). Screws M2.5 x 12
from under the body: body boss -> PCB -> 7 mm spacer -> plate; the spacers alone set the plate height,
the body walls stop 0.3 mm short of the plate. No fastener shows on the front.
"""
PCB_T = 1.6
PLATE_Z0, PLATE_Z1 = 7.0, 10.0
PLATE_T = PLATE_Z1 - PLATE_Z0
OVH = 2.3                                  # plate and body overhang the PCB by clearance + wall

# through holes in the plate
KEY_HOLE = (10.2, 7.0, 1.4)                # caps are 9.6 x 6.4
SHAFT_HOLE = 7.6                           # encoder bushing dia 7
RANGE_HOLE = 12.0                          # RKJXT lever + hub, hidden under the knob skirt
LIGHT_HOLES = {"SHIFT": 1.8, "UNIT": 1.6}  # light pipes; 0.5 mm web to the neighbouring key hole

# pockets milled from the back
# w, h, corner r, depth (body 11.7 x 12, lugs, terminal blocks; pins at +-9.5)
EC11_POCKET = (14.8, 20.0, 2.0, 1.3)
RANGE_POCKET = (18.4, 2.0)                 # dia, depth (body 17 across corners, 8.6 high)

# fasteners
# blind M2.5 from the back: drill 2.2 deep INCLUDING the 118 deg point (full width for 1.58), full thread
# 1.2 min (a bottoming tap leaves its last turns short), 0.8 mm left in front of the drill tip
TAP = dict(size="M2.5", drill=2.05, drill_depth=2.2, thread_depth=1.2)
TAP_POINT = TAP["drill"] / 2 / 1.664       # 118 deg point length (tan 59 deg = 1.664)
SCREW_L = 12.0
SCREW_MARGIN = 0.3                         # screw tip short of the last full thread: screw length and print tolerances
SCREW_HEAD_Z = PLATE_Z0 + TAP["thread_depth"] - SCREW_MARGIN - SCREW_L   # -4.1: head seat in the body boss
SLEEVE_CLEAR = 0.4                         # outer knob counterbore around the fixed bushing, radial and above
WALL_GAP = 0.3                             # body walls stop short of the plate: the spacers set its height
SPACER = dict(od=5.0, id=2.8, length=PLATE_Z0)                          # PCB top to plate bottom

# encoder shafts (z above the PCB); "sleeve" is the fixed bushing
EC11_BODY, SLEEVE_TOP, OUTER_TOP, INNER_TOP = 8.0, 13.0, 18.0, 28.0
SLEEVE_D, OUTER_D, INNER_D, INNER_FLAT, FLAT_LEN, SLOT_W, SLOT_LEN = 7.0, 6.0, 3.5, 2.5, 7.0, 2.0, 2.5
PUSH_TRAVEL = 0.5

# knobs (heights above the plate top); resin, fits to test on the first print
FIT = 0.05                                 # added to bores that must grip
FIT_VARIANTS = {"tight": -0.05, "loose": 0.15}   # extra outer-22 and inner knob each: resin prints vary
OUTER_KNOB = dict(z0=0.8, z1=8.0, neck_d=9.6, neck_top=8.6)
INNER_KNOB = dict(d=13.0, z0=8.8, z1=19.2, recess_d=10.4, recess_top=10.1)    # recess clears the neck (8.6) when pushed
KNOB_D = {"ALTHDG": 22.0, "FREQ": 22.0, "FMS": 24.0}
# knob legends: degrees their arc is turned from the horizontal towards the user, for the plate artwork and
# the 3D view alike. FMS at 5 keeps its long amber line about 3 mm off the plate edge.
KNOB_LEGEND_TILT = {"ALTHDG": 15, "FREQ": 15, "FMS": 5, "RANGE": 35}

# Legends, the one source for the caps (make_caps.py), the plate (make_plate_art.py) and the 3D view
# (geometry.js). The board silkscreen (pcb/board.py) and the firmware button map (firmware/buttonmap.py)
# keep their own copies (ASCII, CircuitPython); tests/test_labels.py checks they agree with these.
# Keys: (cap label, amber shift legend under it) per key, rows top to bottom, columns left to right.
KEY_LEGENDS = [
    [("AP", "TEST"), ("ALT", "ARM"), ("HDG", "CRS CTR"), ("MIC 1", "ADF"), ("COM 1", "NAV 1"), ("CDI", "OBS"),
     ("COM ⇆", "121.5")],
    [("FD", "YD"), ("VS", ""), ("NAV", "GPSS"), ("MIC 2", "DME"), ("COM 2", "NAV 2"), ("VFR", "IDENT"),
     ("NAV ⇆", "ADF ⇆")],
    [("UP", ""), ("FLC", ""), ("APR", "BC"), ("HOME", "UNIT"), ("FPL", "VNAV"), ("D→", "MSG"), ("MENU", "NRST")],
    [("DN", ""), ("VNV", ""), ("LVL", "½ BANK"), ("SHIFT", ""), ("PROC", "TERR"), ("CLR", "MAP"), ("ENT", "")],
]
# Knobs: (white legend, amber legend with SHIFT or None): what the rings do, outer first, then the push.
KNOB_LEGENDS = {
    "ALTHDG": ("ALT · HDG · PUSH SYNC", "CRS · BARO · PUSH STD"),
    "RANGE": ("RANGE · PUSH PTR", None),
    "FREQ": ("FREQ · PUSH COM/NAV/ADF", "SQUAWK · PUSH XPDR"),
    "FMS": ("FMS · PUSH CRSR", "PANEL · FLOOD · PUSH CABIN"),
}

# RANGE knob on the RKJXT lever
LEVER_Z0, LEVER_Z1, LEVER_D, LEVER_FLAT = 12.4, 17.4, 2.5, 1.8
RANGE_KNOB = dict(d=13.6, skirt_d=15.6, z0=1.8, z1=11.0)   # skirt clears the plate by about 0.4 mm at full tilt

# light pipes (clear resin), captive between the LED and the plate
LED_TOP = 5.3
PIPE = dict(z0=6.2, collar=(4.0, 0.8), clear=0.08)   # bottom 0.9 above the LED, collar 4 x 0.8; rod 0.08 under the hole
