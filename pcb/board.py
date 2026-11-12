"""DIY Avionics Panel rev 1 - RP2040 directly on the board, USB-C, 4 layers.

Knob set ALT/HDG + RANGE (Alps RKJXT, turn / 4-way tilt / push) left, FREQ + FMS right, 28 keys, two
lights, BOOT as bridge pads under a hole in the body floor, SWD debug points.

Top view (component side), mm, origin top-left, y down. Layer stack: F (signals), In1 = GND plane,
In2 = 3V3 plane, B (signals). Switches, knobs and the RANGE control (THT) sit on top; every SMD part (RP2040,
flash, USB-C, regulator, diodes, passives, the two reverse-mount LEDs that shine up through cutouts in the board)
is on the bottom, so JLCPCB assembles one SMD side. The through-hole parts are soldered by hand (hand-soldering)
or fitted by JLCPCB from a top-side CPL (full assembly); docs/building/ordering.md has both.

Footprint sources:
  RP2040 QFN-56: RP2040 datasheet fig. 165 (pads 0.20 x 0.875, pitch 0.40, 7.75/6.00, EP 3.20)
  RP2040 pinout: RP2040 datasheet fig. 3
  USB-C HRO TYPE-C-31-M-12: JLC/EasyEDA footprint of C165948 (pad row, pads 0.3/0.6 x 1.3), HRO drawing
  PEC11D-4120F-S0015: Bourns PEC11D datasheet (recommended PCB layout, holes 1.2), checked against JLC's
      footprint of C19270361
  RKJXT1F42001: Alps drawing, checked against JLC's footprint of C160841
  W25Q16JVSNIQ (SOIC-8 150 mil): JLC's footprint of C2456211 (rows 5.37 apart, pads 0.63 x 1.87, pitch 1.27)
  6x6 key switches (TE 1-1825910-4): pins 6.5 x 4.5, the 6.5 mm pairs connected inside

Bottom-side parts: seen from the top, a part on the bottom is mirrored, so its pins number clockwise.
CPL rotations follow JLCPCB's convention for the bottom side (the one KiBot's JLCPCB rotation filter and
the kicad-jlcpcb-tools plugin write: 180 minus KiCad's bottom-side angle): seen from the bottom, a part is
JLC's library footprint (its top view) turned counter-clockwise by the CPL rotation, just like a top-side
part seen from the top. Seen from the top, as this file works, that is the footprint mirrored left to right,
then turned clockwise. check.py fits every bottom-side part's JLC footprint (stored in footprints/) onto
our pads that way: each JLC pad must land on our pad with the same number.
Top-side CPL rotations (the through-hole parts in full assembly) follow JLCPCB's top-side convention: seen from
the top, the part is JLC's library footprint turned counter-clockwise by the rotation, its origin on the CPL
position. check.py fits each JLC hole pattern that way onto our holes, pin by pin.
Circuit follows Raspberry Pi's "Hardware design with RP2040" minimal design.
"""
import importlib.util
import os
import re
from itertools import pairwise


def _load(name, path):
    """a module by file path, without putting its directory on sys.path"""
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(os.path.abspath(__file__)), path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_STACK = _load("_avionics_stack", "../mech/stack.py")   # the one source of the key legends

XR = 145.0              # right knob column (FREQ over FMS)
W, H = 160.0, 60.0      # layout: ALT/HDG over RANGE | keys | electronics strip (bottom) | FREQ over FMS
CORNER_R = 3.0
TRACE_W = 0.25
FAN_W = 0.16            # QFN / USB fan-out traces
CLEAR = 0.15
EDGE_CLEAR = 0.50
VIA_D, VIA_DRILL = 0.60, 0.30
SVIA_D, SVIA_DRILL = 0.50, 0.30     # small vias (USB-C, fan-out ends): JLC standard 0.3 mm drill, 0.45 mm pad min.
MOUNT_HOLE = 3.8      # round the M3 screw: the board floats on the screws, where the caps centre it (mech/stack.py)
CORNER_MOUNTS = [(3.5, 3.5), (W - 3.5, 3.5), (3.5, H - 3.5), (W - 3.5, H - 3.5)]
# The fifth mount, in the middle of the key field: the widest spot between the pins of the four keys round it
# (K12, K13, K22, K23: pin centres 5.3 mm off in x and 5.0 in y), with no bottom-side part within 6.9 mm. The
# same hole, keep-out, plate boss and screw as at the corners.
MID_MOUNT = (72.25, 30.75)
MOUNTS = CORNER_MOUNTS + [MID_MOUNT]
# no copper on F and B within this radius of a mounting-hole centre: the plate boss and the body boss press on
# the board there (precheck.py holds the fixed copper and the bottom-side part bodies to it, check.py measures it
# on the Gerbers, mech/check_fit.py fits the plate boss inside it)
MOUNT_KEEPOUT = 3.6
PLANES = {"In1": "GND", "In2": "3V3"}

KEY_DX, KEY_DY, KEY_PAD, KEY_DRILL = 3.25, 2.25, 1.8, 1.0
DIO_DX, DIO_W, DIO_H = 1.65, 1.0, 1.3
ENC_PAD, ENC_DRILL = 1.8, 1.2   # Bourns PEC11D: pin holes 1.2 +0.1/-0
# the encoders' lug slots, Bourns' recommended 1.5 x 2.6 (+0.1 / -0) and JLC's own footprint's: 1.73 long to 1
# wide, under JLCPCB's 2:1 for slots, but 1.3 wide or 3.0 long would leave both (ordering.md's review questions)
SLOT = (1.5, 2.6)

COL_PITCH = 11.85
# Key columns and rows count from 0 in this file, as in COLS, ROWS and the key names (K12: row 1, column 2).
COLS = [40.0 + COL_PITCH * k for k in range(3)] + [116.35 - COL_PITCH * k for k in (3, 2, 1, 0)]
ROWS = [12.5, 23.5, 38.0, 49.0]         # rows 2/3 lower: room for the FMS line on the plate
# Column pull-ups (10k to 3V3, one per column): the RP2040's own pull-ups (50 to 80k) with 20 to 30 pF of column
# copper and diodes recover too slowly between two rows of a KeyMatrix scan (about 1 us). On each column bus,
# midway between key rows 1 and 2, clear of the key pads and of the body's post and middle column under the board.
PULLUP_Y = 31.0
KEY_LABELS = [[label.replace(" ⇆", "<>").replace("→", "->") for label, _ in row]   # silkscreen: ASCII
              for row in _STACK.KEY_LEGENDS]
ALTHDG, RANGE = (15.0, 15.0), (15.0, 45.0)   # left: ALT/HDG dual over RANGE (RKJXT: turn, 4-way tilt, push)
FREQ, FMS = (XR, 15.0), (XR, 45.0)          # right: frequency dual over FMS dual
MCU = (131.6, 25.0)             # RP2040 on the bottom, mirrored (pins 1-14 face the keys, bottom to top)
USB_X = 127.0
BOOT = (MCU[0] + 0.5, 54.0)     # bridge pads on the bottom, under a hole in the body floor
# Light pipes in the front plate over the LEDs. In the 4 mm aluminium plate each light hole keeps at least 0.8 mm
# to the next key hole, JLCCNC's recommended wall (0.5 mm is its minimum). Each LED is a reverse-mount 1206 on the
# bottom that shines up through a cutout in the board (LED_CUTOUT); its light pipe stands on the board over it,
# with a base wide enough to stand on the board round the cutout, clear of the switch bodies and out from under
# the key holes (mech/check_fit.py): SHIFT 5.75 mm below its key's centre; UNIT midway between key rows 2 and 3
# and 5.5 mm east of column 3, in the gap between the caps of columns 3 and 4 (its middle is COL_PITCH / 2,
# 5.925 mm), where the SHIFT cap does not stand in front of it.
LEDS = {"SHIFT": ((COLS[3], ROWS[3] + 5.75), "GP12", "amber"),
        "UNIT": ((COLS[3] + 5.5, (ROWS[2] + ROWS[3]) / 2), "GP15", "white")}
# The LEDs that lie with the cathode east and the anode and the series resistor west (add_led); the others have
# the cathode west. UNIT: east of it the resistor would lie on the column 4 bus, 4.7 mm from the LED's centre.
LED_CATHODE_EAST = {"UNIT"}
# The LEDs switched by a low-side N-FET from VBUS_F instead of driven from their GPIO (add_led_switch): the FET's
# place, in the free band between key rows 1 and 2 above the LED, clear of the body's post and middle column
LED_SWITCH = {"UNIT": (87.0, 31.5)}
# The cutout under each LED: 2.2 mm along the pads by 2.4 mm across, R0.5 corners (a 1.0 mm router), round LiteOn's
# 1.5 x 1.6 mm lens (LiteOn's land pattern: 2.1 x 2.3, sharp corners); in the Edge_Cuts layer. The pads stop
# LED_CUT_CLEAR short of it, JLCPCB's copper-to-routed-edge minimum, and still reach 0.3 mm under the terminals on
# the LED's face (0.75 to 1.6 mm off its centre; LiteOn's own pattern reaches 0.55 mm under them).
LED_CUTOUT = (2.2, 2.4, 0.5)
LED_CUT_CLEAR = 0.2
LED_PAD = (1.15, 1.6)                   # along, across; inner edge at LED_CUTOUT[0] / 2 + LED_CUT_CLEAR
CUTOUTS = []                            # (x, y, w, h, r) of every cutout in the board, filled by build()

# GPIO plan (RP2040 GPIO number -> function)
# matrix lines leave the RP2040 (pins 14..2, top to bottom on the mirrored chip) in the order the
# rows/columns arrive from the key field
ROW_GP = ["GP11", "GP8", "GP5", "GP2", "GP0"]           # rows 0-3 keys, row 4: RANGE switches + ALT/HDG push
COL_GP = ["GP1", "GP3", "GP4", "GP6", "GP7", "GP9", "GP10"]
R4_COL = {"ALTHDG": 5, "FMS": 6}       # row 4: RANGE A, B, C, D, com on columns 0-4, ALT/HDG push 5, FMS push 6
PUSH_GP = {"FREQ": "GP13"}               # FREQ push: direct input (pull-up, switch to GND). GP14 is spare

# RP2040 QFN-56 pin -> net
RP = {1: "3V3", 10: "3V3", 22: "3V3", 33: "3V3", 42: "3V3", 49: "3V3", 48: "3V3", 43: "3V3", 44: "3V3",
      45: "1V1", 23: "1V1", 50: "1V1", 19: "GND",
      24: "SWCLK", 25: "SWDIO", 26: "3V3",     # SWD to debug pads (a probe can reset the chip over SWD)
      20: "XIN", 21: "XOUT", 46: "USB_DM", 47: "USB_DP",
      51: "QSPI_SD3", 52: "QSPI_SCLK", 53: "QSPI_SD0", 54: "QSPI_SD2", 55: "QSPI_SD1", 56: "QSPI_SS"}
for i, pin in enumerate(range(2, 10)):
    RP[pin] = f"GP{i}"                      # GPIO0-7 on pins 2-9
for i, pin in enumerate(range(11, 15)):
    RP[pin] = f"GP{8 + i}"                  # GPIO8-11 on pins 11-14
for i, pin in enumerate(range(15, 19)):
    RP[pin] = f"GP{12 + i}"                 # GPIO12-15: SHIFT light, FREQ push, spare (fan-out only, NC), UNIT light
for i, pin in enumerate(range(34, 38)):
    RP[pin] = f"GP{22 + i}"                 # GPIO22-25 (FREQ)
RP[40], RP[41] = "GP28", "GP29"             # RANGE encoder
RP[27], RP[28] = "GP16", "GP17"             # FMS inner ring
for i, pin in enumerate(range(29, 33)):
    RP[pin] = f"GP{18 + i}"                 # GPIO18-21 (ALT/HDG)
RP[38], RP[39] = "GP26", "GP27"             # FMS outer ring


class Pad:
    def __init__(self, name, net, x, y, shape, w, h, layers, drill=None, slot=None, paste=True, mask=True, pip=False):
        self.name, self.net, self.x, self.y = name, net, x, y
        self.shape, self.w, self.h = shape, w, h            # circle | obround | rect
        self.layers, self.drill, self.slot, self.paste = layers, drill, slot, paste
        # pin-in-paste: a plated hole of an assembled SMD part (the USB-C shell tabs) that gets bottom paste and
        # is reflowed with the part
        self.pip = pip
        # layers with a mask opening: True = all of the pad's layers, False = a routing point under the mask
        self.mask = layers if mask is True else (mask or "")

    def capsule(self):
        if self.shape == "circle":
            return (self.x, self.y, self.x, self.y, self.w / 2)
        if self.w >= self.h:
            r, d = self.h / 2, (self.w - self.h) / 2
            return (self.x - d, self.y, self.x + d, self.y, r)
        r, d = self.w / 2, (self.h - self.w) / 2
        return (self.x, self.y - d, self.x, self.y + d, r)

    def rect(self):
        return (self.x - self.w / 2, self.y - self.h / 2, self.x + self.w / 2, self.y + self.h / 2)


DIODES, NPTH, PARTS = [], [], []
FOOTPRINT = {}              # ref -> footprint name for the BOM (bottom-side parts)
CPL_XY = {}                 # ref -> (x, y) of JLC's footprint origin where it is not the part position (top side)
PREROUTED = {"QSPI_SD0", "QSPI_SD1", "QSPI_SD2", "QSPI_SD3", "QSPI_SCLK", "1V1", "XIN", "XOUT", "XO_R"}
FIXED_SEGS, FIXED_VIAS = [], []
BUS_PADS = set()            # pads already joined by a pre-routed matrix bus
JOINED = set()              # other pads joined to a routing point by pre-routed copper (not router terminals)
BUS_COPPER = []             # (kind, args) of the bus copper: the router grows the net from it
BUS_NETS = set(ROW_GP) | set(COL_GP)          # pre-routed copper: (x1,y1,x2,y2,layer,net,width) / (x,y,net,d,drill)


def seg(x1, y1, x2, y2, net, layer="B", w=FAN_W):
    FIXED_SEGS.append((x1, y1, x2, y2, layer, net, w))


def path(net, pts, layer="B", w=FAN_W):
    """Pre-routed copper from point to point; a point repeated adds nothing."""
    for (x1, y1), (x2, y2) in pairwise(pts):
        if (x1, y1) != (x2, y2):
            seg(x1, y1, x2, y2, net, layer, w)


def via(x, y, net, d=VIA_D, drill=VIA_DRILL):
    FIXED_VIAS.append((x, y, net, d, drill))


def th(name, net, x, y, pad=ENC_PAD, drill=ENC_DRILL):
    return Pad(name, net, x, y, "circle", pad, pad, "FB", drill)


def smd(name, net, x, y, w, h, shape="rect", paste=True, layer="B", mask=True):
    return Pad(name, net, x, y, shape, w, h, layer, paste=paste, mask=mask)


def part(ref, value, lcsc, x, y, rot=0, side="bottom", foot=None, origin=None):
    """A part for the BOM / CPL. Bottom-side parts are assembled by JLCPCB and need their footprint name; rot is
    the CPL rotation in JLCPCB's convention for the part's side (module docstring). origin: where JLC's footprint
    has its origin, the CPL position, if not at (x, y) (a top-side part placed by JLC in full assembly)."""
    if not foot and side != "top":                # a plain raise: asserts vanish under -O
        raise ValueError(f"{ref}: bottom-side part without a footprint")
    PARTS.append((ref, value, lcsc, x, y, rot, side))
    FOOTPRINT[ref] = foot
    if origin:
        CPL_XY[ref] = origin


def cpl(ref, x, y, rot, side):
    """One CPL row for JLCPCB: designator, Mid X, Mid Y (mm, from the board's bottom-left corner seen from the top,
    y up), layer and rotation, at JLC's footprint origin (CPL_XY, else the part position)."""
    ox, oy = CPL_XY.get(ref, (x, y))
    return ref, round(ox, 3), round(H - oy, 3), "Top" if side == "top" else "Bottom", rot % 360


CHIP = {"0603": (0.8, 0.8, 0.95), "0402": (0.5, 0.6, 0.55)}   # pad centre offset, pad length, pad width (mm)


def chip(pads, ref, x, y, net1, net2, value, lcsc, vertical=False, size="0603", flip=False):
    """Two-pad chip resistor / capacitor; pad 1 left (or top), pad 2 right (or bottom), the other way round with
    flip. JLC's footprint has pad 1 on the left; on the bottom that is rotation 180 (pad 1 left), 270 (pad 1 on
    top), 0 (pad 1 right) or 90 (pad 1 at the bottom)."""
    off, length, width = CHIP[size]
    dx, dy = (0, off) if vertical else (off, 0)
    if flip:
        dx, dy = -dx, -dy
    w, h = (width, length) if vertical else (length, width)
    pads.append(smd(f"{ref}.1", net1, x - dx, y - dy, w, h))
    pads.append(smd(f"{ref}.2", net2, x + dx, y + dy, w, h))
    part(ref, value, lcsc, x, y, (270 if vertical else 180) - (180 if flip else 0), foot=size)
    return (x - dx, y - dy), (x + dx, y + dy)


def plane_via(pad_xy, net, dx, dy, d=VIA_D):
    """Short stub from an SMD pad to a via into the GND / 3V3 plane."""
    x, y = pad_xy
    seg(x, y, x + dx, y + dy, net, "B", 0.3)
    via(x + dx, y + dy, net, d)


def add_diode(pads, name, x, y, anode, cathode):
    pads.append(smd(name + ".A", anode, x - DIO_DX, y, DIO_W, DIO_H, "obround"))
    pads.append(smd(name + ".K", cathode, x + DIO_DX, y, DIO_W, DIO_H, "obround"))
    DIODES.append((name, x, y))
    part(name, "1N4148W", "C81598", x, y, foot="SOD-123")


def add_encoder(pads, ref, cx, cy, dual, a, b, a2=None, b2=None, push_k=None, val="", lcsc="", push_d=None):
    for dx, nm, net in ((-2.5, "A", a), (0, "C", "GND"), (2.5, "B", b)):
        pads.append(th(f"{ref}.{nm}", net, cx + dx, cy + 7.5))
    pads.append(th(f"{ref}.D", push_d or ROW_GP[4], cx - 2.5, cy - 7.0))
    pads.append(th(f"{ref}.E", push_k, cx + 2.5, cy - 7.0))
    if dual:
        for dx, nm, net in ((-2.5, "A2", a2), (0, "C2", "GND"), (2.5, "B2", b2)):
            pads.append(th(f"{ref}.{nm}", net, cx + dx, cy - 9.5))
    for s in (-1, 1):       # metal mounting lugs on GND through the plane: an ESD path from the shaft
        pads.append(Pad(f"{ref}.MP{s}", "GND", cx + s * 5.5, cy, "obround", 2.5, 3.6, "FB",
                        drill=SLOT[0], slot=SLOT))
    # JLC's footprint of C19270361 has its origin midway between the outer pin rows (y +7.5 and -9.5), 1 mm north
    # of the shaft; rotation 0 has its switch pins (4, 5) on the north side, as here
    part(ref, val, lcsc, cx, cy, side="top", origin=(cx, cy - 1.0))


# Alps RKJXT1F42001 (LCSC C160841): turn (15 pulses / 30 detents), 4-way tilt, centre push. Hole pattern read
# from the Alps mounting-hole drawing (seen from the insertion side), verified against JLC's footprint (below).
# Alps gives the pin holes as 1.0 +0.2/-0; JLCPCB's plated holes may finish up to 0.08 mm under the drill, so
# they are drilled 1.1 (JLC's footprint: 1.2), the 1.7 mm pads keep a 0.3 mm ring. The locating hole for the
# 1 mm peg (1 -0.1) is a 1.3 mm NPTH, as in JLC's footprint: Alps asks for 1.1 +0.1/-0, which JLCPCB's +-0.2
# on NPTH cannot hold (at 0.9 the peg would not go in). The part floats up to 0.26 mm on its pins before
# soldering; the plate gives it that room (mech/stack.py RKJXT_ON_PINS).
# Switches: "Push" is common to all; A, B, C, D close with their direction, "com" closes on every operation
# (centre push = com without A-D, decoded in firmware).
RKJXT_HOLES = {"ECOM": (-1.5, -7.8), "C": (1.5, -7.8), "COM": (-1.0, -5.78), "D": (-7.8, -1.5),
               "ENCA": (-7.8, 1.5), "LUG": (-3.8, 1.5), "ENCB": (7.8, -1.5), "B": (7.8, 1.5),
               "GND": (6.86, 3.75), "A": (-1.5, 7.8), "PUSH": (1.0, 6.98)}
RKJXT_LUG = 1.3
RKJXT_PAD, RKJXT_DRILL = 1.7, 1.1
# Checked against JLC's own footprint of C160841 (EasyEDA SW-TH_RKJXT1F42001): all 11 positions and the
# locating hole agree (the Alps drawing puts the frame ground at x 6.86, y 3.75); check.py fits it on every run.


def add_rkjxt(pads, ref, cx, cy, enc_a, enc_b):
    legs = ["A", "B", "C", "D", "COM"]                  # -> diodes -> columns 0-4, common "Push" on row 4
    for nm, (dx, dy) in RKJXT_HOLES.items():
        x, y = cx + dx, cy + dy
        if nm == "LUG":
            NPTH.append((x, y, RKJXT_LUG))
            continue
        net = {"ECOM": "GND", "GND": "GND", "ENCA": enc_a, "ENCB": enc_b, "PUSH": ROW_GP[4]}.get(nm, f"{ref}_{nm}")
        pads.append(Pad(f"{ref}.{nm}", net, x, y, "circle", RKJXT_PAD, RKJXT_PAD, "FB", RKJXT_DRILL))
    for k, nm in enumerate(legs):                       # diodes in the free column between the knobs and the keys
        add_diode(pads, f"D_{ref}_{nm}", 28.5, cy - 6.0 + 3.0 * k, COL_GP[k], f"{ref}_{nm}")
    part(ref, "RKJXT1F42001", "C160841", cx, cy, side="top")


def add_led(pads, name, x, y, gpio, colour, cathode_east=False, switch=None):
    """Reverse-mount 1206 LED on the bottom under a light pipe, its lens up in a cutout through the board, and its
    series resistor beside it. LiteOn's C230 package (LTST-C230KSKT amber, LTW-C230DS white), pad 1 of JLC's
    footprint the cathode: cathode west and anode east (pad 1 on the left, rotation 180 on the bottom), or with
    cathode_east the mirror image (pad 1 on the right, rotation 0). The cathode goes to GND and the resistor to the
    GPIO, or with switch (the FET's place) the cathode to the FET and the resistor to VBUS_F (add_led_switch)."""
    w, h, r = LED_CUTOUT
    CUTOUTS.append((x, y, w, h, r))
    pl, pw = LED_PAD
    off = w / 2 + LED_CUT_CLEAR + pl / 2
    k = 1 if cathode_east else -1                           # the cathode's side: +1 east, -1 west
    anode, cathode = f"LED_{name}_A", f"LED_{name}_K" if switch else "GND"
    pads.append(smd(f"LED_{name}.K", cathode, x + k * off, y, pl, pw))
    pads.append(smd(f"LED_{name}.A", anode, x - k * off, y, pl, pw))
    if not switch:                                      # beyond the cathode, room for the silk bar between
        plane_via((x + k * off, y), "GND", k * (pl / 2 + 0.95), 0)
    # Amber about 13.5 mA from GP12 at 12 mA drive strength (the firmware sets it), 75 R (the basic part between 51
    # and 100): 6.8 to 17.2 mA over the GPIO's output resistance and the LED's forward voltage (the low end with
    # 2.4 V across the LED and the pad's 57 ohm at most: (3.3 - 2.4) / (75 + 57)), under its 30 mA.
    # White: forward voltage 2.8 to 3.6 V at 20 mA (+-0.1 per bin, and JLCPCB cannot choose the bin), too close to
    # the 3.3 V supply: on a GPIO a top-bin part got 1 to 2 mA. So it runs from VBUS_F (4.23 to 5.5 V: USB's 4.40
    # to 5.5 V less up to 0.17 V over R_IN and the fuse) through 390 R and the FET. A typical LED (3.2 V at 20 mA)
    # on 5.0 V gets 5.0 mA, the 2.8 V and 3.6 V bins 6.0 and 4.1 mA; the extremes are 2.2 mA (4.40 V, 3.7 V, the
    # resistor 1 % high, 24 ohm in a FET at its highest threshold, below) and 7.7 mA (5.5 V, 2.7 V, 1 % low, the
    # FET at 0 ohm). These assume the forward voltage falls by 0.415 V per decade of current below 20 mA; whatever
    # the slope, the current stays under 5.5 V / 386 ohm = 14.2 mA, below the LED's 20 mA. The firmware sets both
    # brightnesses with PWM (docs/architecture/electronics.md).
    led_part, lcsc, res, res_lcsc = {"amber": ("LTST-C230KSKT", "C125108", "75R", "C4275"),
                                     "white": ("LTW-C230DS", "C575513", "390R", "C23151")}[colour]
    part(f"LED_{name}", led_part, lcsc, x, y, 0 if cathode_east else 180, foot="1206 reverse")
    # The resistor in line beyond the anode pad, its anode end 0.3 mm from it (the same net) and its GPIO (VBUS_F)
    # end beyond. Beside, not below: SHIFT is near the board edge, every part body but J1's stays 2.5 mm from it
    # (JLCPCB's terms).
    roff, rlen, _ = CHIP["0603"]
    chip(pads, f"R_{name}", x - k * (off + pl / 2 + 0.3 + rlen / 2 + roff), y, "VBUS_F" if switch else gpio, anode,
         res, res_lcsc, flip=not cathode_east)
    if switch:
        add_led_switch(pads, name, *switch, gpio, cathode)


# The low-side switch of an LED on VBUS_F: a 2N7002 (basic part; threshold 1.0 to 2.5 V, at most 7 ohm at 5 V gate
# and 50 mA) between the LED's cathode and GND, its gate on the GPIO, so the GPIO high still lights the LED. 3.23 V
# on the gate (the regulator's low end) leaves 0.73 V over the highest threshold: about 15 mA at least in
# saturation and 24 ohm at most at the LED's few mA (square law from 7 ohm at 5 V and 2.5 V over the threshold), so
# the LED's current is set by its resistor. The 10 k pull-down holds the gate low while the pin floats (from reset
# until code.py drives it), so the LED stays off; with the pin high it takes 0.33 mA. JLC's footprint of C8545: pad
# 1 G and pad 2 S on one side, pad 3 D on the other; at rotation 90 on the bottom, seen from the top, D is south
# (towards the LED), G north-west and S north-east.
def add_led_switch(pads, name, qx, qy, gpio, drain):
    ref = f"Q_{name}"
    pads.append(smd(f"{ref}.1", gpio, qx - 0.95, qy - 1.0, 0.65, 1.0))
    pads.append(smd(f"{ref}.2", "GND", qx + 0.95, qy - 1.0, 0.65, 1.0))
    pads.append(smd(f"{ref}.3", drain, qx, qy + 1.0, 0.65, 1.0))
    part(ref, "2N7002", "C8545", qx, qy, 90, foot="SOT-23")
    plane_via((qx + 0.95, qy - 1.0), "GND", 0, -1.2)
    # the pull-down west of the gate, in line with it (its GND end west, its own via south of it)
    roff, rlen, _ = CHIP["0603"]
    gnd, g = chip(pads, f"R_{name}_PD", qx - 0.95 - 0.325 - 0.375 - rlen / 2 - roff, qy - 1.0, "GND", gpio, "10k",
                  "C25804")
    seg(*g, qx - 0.95, qy - 1.0, gpio, "B", TRACE_W)
    plane_via(gnd, "GND", 0, 1.2)
    JOINED.update((f"{ref}.2", f"R_{name}_PD.2"))   # on the gate's (the GPIO's) and the GND via's fixed copper


# ---------------- RP2040 (bottom side, mirrored top-to-bottom) ----------------
def qfn_top(pin):
    """Pad centre / outward normal / lateral offset of QFN-56 pad `pin` for a chip on top (datasheet view)."""
    k = (pin - 1) % 14
    side = (pin - 1) // 14
    o = -2.6 + 0.4 * k
    r = 3.4375
    if side == 0:
        return (-r, o), (-1, 0), o
    if side == 1:
        return (o, r), (0, 1), o
    if side == 2:
        return (r, -o), (1, 0), -o
    return (-o, -r), (0, -1), -o


def qfn_pad_xy(pin):
    """Same for the chip mounted on the bottom, seen from the top: mirrored in y.
    West: pins 1-14 bottom to top; north: 15-28 left to right; east: 29-42 top to bottom; south: 43-56."""
    (px, py), (nx, ny), lat = qfn_top(pin)
    return (px, -py), (nx, -ny), (-lat if nx else lat)


FAN_END, FAN_SPREAD = 6.2, 1.5          # north / east / south
# west (matrix) and east (knobs): 0.86 mm pitch, a via on every end (0.56 mm between holes)
FAN_END_W, FAN_SPREAD_W = 7.5, 2.15


def add_rp2040(pads):
    mx, my = MCU
    for pin in range(1, 57):
        (px, py), (nx, ny), lat = qfn_pad_xy(pin)
        w, h = (0.875, 0.20) if nx else (0.20, 0.875)
        net = RP.get(pin)
        pads.append(smd(f"U1.{pin}", net, mx + px, my + py, w, h))
        if net is None or net in ("3V3", "1V1", "GND"):
            continue
        if nx:
            ox, oy = mx + nx * 3.875, my + lat
        else:
            ox, oy = mx + lat, my + ny * 3.875
        sx, sy = ox + nx * 0.4, oy + ny * 0.4
        fe, fs = (FAN_END_W, FAN_SPREAD_W) if nx else (FAN_END, FAN_SPREAD)
        ex = mx + nx * fe + (0 if nx else lat * fs)
        ey = my + ny * fe + (lat * fs if nx else 0)
        seg(ox, oy, sx, sy, net)
        seg(sx, sy, ex, ey, net)
        pads.append(smd(f"U1.F{pin}", net, ex, ey, 0.3, 0.3, "circle", paste=False, mask=False))   # breakout point
    pads.append(smd("U1.EP", "GND", mx, my, 3.2, 3.2, "rect", paste=False))
    # its four GND vias: tented on the top, open on the bottom inside the pad's mask opening, in the cross between
    # its four paste windows (make.py EP_WINDOWS), each hole 0.25 mm from them. Some solder may run into them;
    # JLCPCB X-rays the QFN, and filled and capped vias would cost extra for little.
    for vx, vy in ((-0.8, 0), (0.8, 0), (0, -0.8), (0, 0.8)):
        via(mx + vx, my + vy, "GND")
    inner = 2.45

    def stub_to(pin, vx, vy):
        (px, py), (nx, ny), lat = qfn_pad_xy(pin)
        ix, iy = mx + px - nx * 0.4375, my + py - ny * 0.4375
        jx, jy = ix - nx * 0.35, iy - ny * 0.35
        seg(ix, iy, jx, jy, RP[pin], "B", 0.2)
        seg(jx, jy, mx + vx, my + vy, RP[pin], "B", 0.2)

    groups = [  # (pins, via position (top-side layout, mirrored below), net)
        ((1,), (-inner, -2.2), "3V3"), ((10,), (-inner, 1.0), "3V3"),
        ((22,), (-0.4, inner), "3V3"), ((23,), (1.1, inner), "1V1"), ((26,), (2.2, inner), "3V3"),
        ((33,), (inner, 1.0), "3V3"), ((42, 43, 44), (2.3, -2.3), "3V3"),
        ((45,), (1.3, -inner), "1V1"), ((48, 49), (0.4, -inner), "3V3"), ((50,), (-0.7, -inner), "1V1"),
    ]
    for pins, (vx, vy), net in groups:
        vy = -vy
        for p in pins:
            stub_to(p, vx, vy)
        via(mx + vx, my + vy, net)
        if net == "1V1":            # probe points on the top; tented on the bottom, next to the QFN pads
            pads.append(Pad(f"U1.V{pins[0]}", "1V1", mx + vx, my + vy, "circle", 0.6, 0.6, "FB", paste=False,
                            mask="F"))
    (px, py), _, _ = qfn_pad_xy(19)                         # TESTEN to the exposed pad
    seg(mx + px, my + py + 0.4375, mx + px, my - 1.6, "GND", "B", 0.2)
    part("U1", "RP2040", "C2040", mx, my, 180, foot="LQFN-56 7x7")
    # SWD debug points: SWCLK and SWDIO end in exposed 0.6 / 0.7 mm pads (bottom) at the north fan-out, for
    # thin wires to an SWD probe (GND: the USB-C shell; the probe resets the chip over SWD). There is no
    # room for larger pads or vias: the lanes around the RP2040 are full. SWDIO's pad sits 0.8 mm further out.
    for p in pads:
        m = re.match(r"U1\.F(2[45])$", p.name)
        if m:
            if m.group(1) == "25":
                seg(p.x, p.y, p.x, p.y - 0.8, p.net)
                p.y -= 0.8
            p.w = p.h = 0.7 if m.group(1) == "25" else 0.6
            p.mask = p.layers                               # exposed: the probe wires solder here
    # west and east fan-out ends get a via (matrix: the last mile comes in on F); GP25's ends in its series
    # resistor instead (add_gp25_resistor)
    for p in list(pads):
        if re.match(r"U1\.F\d+$", p.name) and abs(p.x - mx) > FAN_END and p.net != "GP25":
            via(p.x, p.y, p.net, SVIA_D, SVIA_DRILL)
            if p.net in BUS_NETS:
                BUS_COPPER.append(("via",) + FIXED_VIAS[-1])
    # GP13 (FREQ push, off to the north-east) starts on the top layer: on the bottom it would cross the way out
    # to the west of its neighbours GP12 and GP15
    p = next(p for p in pads if p.name == f"U1.F{next(k for k, n in RP.items() if n == PUSH_GP['FREQ'])}")
    via(p.x, p.y, p.net, SVIA_D, SVIA_DRILL)
    p.layers = "F"
    add_gp25_resistor(pads)


# GP25 is the FREQ outer ring's B line and, on the stock Pico build of CircuitPython the panel runs, the status LED
# (MICROPY_HW_LED_STATUS): CircuitPython drives it high, push-pull, at 12 mA drive strength, while it starts (4 x
# 125 ms after each power-up), on entering the REPL and in endless blinks after an error in code.py and in safe mode.
# Half the encoder's detents rest with B closed to GND (C), so straight on the contact that is a short of well over
# 30 mA (RP2040 datasheet figure 171), against the PEC11D's 10 mA contact rating and 50 mA for all GPIOs together.
# R_GP25 (1 k) in series limits it to 3.3 mA; against rotaryio's 50 to 80 k pull-up a closed contact still reads at
# most 3.3 V x 1 / 51 = 0.07 V, far under the 0.8 V input low limit. It sits at the end of GP25's fan-out, in place
# of the via there, so the whole line out to the encoder (GP25_R) is behind it.
def add_gp25_resistor(pads):
    p = next(p for p in pads if p.name == f"U1.F{next(k for k, n in RP.items() if n == 'GP25')}")
    off = CHIP["0603"][0]
    a, _ = chip(pads, "R_GP25", p.x + 0.7 + off, p.y, "GP25", "GP25_R", "1k", "C21190")
    seg(p.x, p.y, *a, "GP25", "B", FAN_W)
    JOINED.add("R_GP25.1")


# ---------------- USB-C on the bottom ----------------
# JLC's footprint of C165948 (top view, opening towards +y): A1B12 at x -3.2 ... B1A12 at +3.2, pad row 0.77 mm
# behind the rear shell slots. On the bottom with the opening towards the y = 0 edge that is the same
# footprint mirrored in y: x stays, so A1B12 sits at -3.2 seen from the top.
def add_usb(pads):
    cx = USB_X
    yc, L = 6.28 + 0.77, 1.3
    contacts = [(-3.2, 0.6, "GND", "A1B12"), (-2.4, 0.6, "VBUS", "A4B9"), (-1.75, 0.3, None, "B8"),
                (-1.25, 0.3, "CC1", "A5"), (-0.75, 0.3, "USB_DN_C", "B7"), (-0.25, 0.3, "USB_DP_C", "A6"),
                (0.25, 0.3, "USB_DN_C", "A7"), (0.75, 0.3, "USB_DP_C", "B6"), (1.25, 0.3, None, "A8"),
                (1.75, 0.3, "CC2", "B5"), (2.4, 0.6, "VBUS", "B4A9"), (3.2, 0.6, "GND", "B1A12")]
    for dx, w, net, nm in contacts:
        pads.append(smd(f"J1.{nm}", net, cx + dx, yc, w, L))
    for s in (-1, 1):
        # shell pads 1.2 wide, as in JLC's footprint; pin-in-paste: paste over the whole pad on the bottom. That
        # is about 0.12 mm3 of solder for about 0.8 mm3 of slot, a bottom fillet at most: the four tabs, which
        # take the plug's load, are soldered from the top by hand as well (docs/building/assembly.md). Each pad
        # reaches 0.2 mm beyond the ends of its slot, JLCPCB's recommended ring (JLC's footprint: 0.15 at the rear
        # pair).
        pads.append(Pad(f"J1.SH{s}a", "GND", cx + s * 4.325, 6.28, "obround", 1.2, 2.1, "FB",
                        drill=0.6, slot=(0.6, 1.7), pip=True))
        pads.append(Pad(f"J1.SH{s}b", "GND", cx + s * 4.325, 2.10, "obround", 1.2, 1.8, "FB",
                        drill=0.6, slot=(0.6, 1.4), pip=True))
        NPTH.append((cx + s * 2.89, 5.79, 0.6))
    ye = yc + L / 2                     # 7.70: pad ends, the breakout starts here
    yv = VBUS_VIA_Y                     # small vias just below the pads
    plane_via((cx - 3.2, ye), "GND", 0, 0.82)
    # B1A12 shares C_IN's GND via (add_support): its own, below the pad, would sit on R_IN
    seg(cx + 3.2, ye, LDO[0] - 3.4, LDO[1], "GND", "B", 0.3)
    # VBUS: B4A9 runs straight down into R_IN and on through the fuse F1 (add_protection); A4B9 joins it over the
    # top layer, round the far side of the pad row
    seg(cx + 2.4, ye, cx + 2.4, yv, "VBUS", "B", 0.4)
    seg(cx - 2.4, ye, cx - 2.4, yv, "VBUS", "B", 0.3)
    for sx in (-1, 1):
        via(cx + sx * 2.4, yv, "VBUS", SVIA_D, SVIA_DRILL)
    # The tie turns between the shell pegs, as close to the pad row as it can: the top layer over J1 is the only
    # way west for the lines that cross it (the bottom under the shell is kept free)
    yt = 5.6
    path("VBUS", [(cx - 2.4, yv), (cx - 2.0, yv - 0.4), (cx - 2.0, yt), (cx + 2.0, yt), (cx + 2.0, yv - 0.4),
                  (cx + 2.4, yv)], "F", 0.3)
    # CC: one 5.1k each, all on fixed copper. CC1 (A5) turns west under the VBUS via to R_CC1, CC2 (B5) runs
    # straight down between the ESD array and the fuse to R_CC2.
    a, b = chip(pads, "R_CC1", cx - 3.4, 10.4, "CC1", "GND", "5.1k", "C23186", vertical=True)
    plane_via(b, "GND", -1.0, 0)
    path("CC1", [(cx - 1.25, ye), (cx - 1.25, 9.1), (cx - 1.75, a[1]), a])
    # (an 0402 below the fuse, clear of the crystal). Its GND pad shares the crystal's GND via (add_crystal): a via
    # of its own sat 0.02 mm from that one.
    a, b = chip(pads, "R_CC2", cx + 2.9, 13.45, "CC2", "GND", "5.1k", "C25905", size="0402")
    seg(*b, *XTAL_GND_VIA, "GND", "B", 0.3)
    path("CC2", [(cx + 1.75, ye), (cx + 1.75, a[1] - 0.25), (cx + 2.0, a[1]), a])
    JOINED.update(("R_CC1.1", "R_CC2.1"))
    add_protection(pads)
    # JLC's origin: midway between the pad row and the front shell pegs
    part("J1", "TYPE-C-31-M-12", "C165948", cx, (yc + 2.10) / 2, 180, foot="USB-C 16P")


# USB protection right behind J1 (issue #14). U4, an SRV05-4 ESD array (SOT-23-6, four channels with steering
# diodes to its VCC pin and a clamp from VCC to GND), takes D+ and D- straight through: each line comes from J1
# into one pad, crosses under the body to the opposite pad and leaves from there (pins 6 -> 1 for D+, 4 -> 3 for
# D-, two channels per line), so the array is in line, with no stub. R_IN (1 ohm, the hot-plug damping) and F1,
# a 0.5 A PTC fuse (1206), sit in VBUS between J1 and everything else; VBUS_F is the protected side (C_IN, the
# regulator, and U4's VCC pin, so its clamp is the one on VBUS_F). A short there (a shorted clamp, U4 placed
# turned by 180 degrees) burns R_IN open, long before F1 trips: R_IN is the sacrificial element for shorts
# behind it, F1 covers slow overloads (docs/architecture/electronics.md). U4 centred under the D- contact B7's
# column: pins 4 / 3 at USB_X - 0.75, 6 / 1 at USB_X + 1.15, VCC (pin 5) towards J1, GND (pin 2) away from it.
ESD = (127.2, 11.7)
ESD_PX, ESD_PY = 0.95, 1.2          # SOT-23-6: pad columns 0.95 apart, rows 2.4 apart (JLC's footprint of C7420376)
FUSE = (131.0, 12.05)               # F1 centre: its pin 1 under R_IN, clear of CC2 to the west
R_IN = (129.55, 9.8)                # R_IN centre (0603, vertical): in B4A9's line, between its via and the fuse
FUSE_PX = 1.5                       # pad centres east and west of FUSE (Bourns: 1.0 x 1.6 pads, 2.0 apart)
# The two VBUS vias below J1's VBUS contacts: the one in B4A9's line keeps a 0.13 mm strip of solder mask to
# R_IN's pad opening below it (check.py: tented vias), and both keep as much to the contacts' openings above
VBUS_VIA_Y = 8.15


def add_protection(pads):
    cx, ye, yv = USB_X, 7.70, 8.25
    ex, ey = ESD
    pins = {1: (ESD_PX, ESD_PY, "USB_DP_C"), 2: (0, ESD_PY, "GND"), 3: (-ESD_PX, ESD_PY, "USB_DN_C"),
            4: (-ESD_PX, -ESD_PY, "USB_DN_C"), 5: (0, -ESD_PY, "VBUS_F"), 6: (ESD_PX, -ESD_PY, "USB_DP_C")}
    for n, (dx, dy, net) in pins.items():           # on the bottom, seen from the top: pin 1 south-east
        pads.append(smd(f"U4.{n}", net, ex + dx, ey + dy, 0.55, 1.2))
    part("U4", "SRV05-4", "C7420376", ex, ey, 0, foot="SOT-23-6")
    xn, xp, yi, yx = ex - ESD_PX, ex + ESD_PX, ey - ESD_PY, ey + ESD_PY
    # D-: B7 straight down into pin 4, A7 joins it below the D+ via; D+: B6 down to a via over pin 6's column, and
    # A6, boxed in by the D- contacts, joins it there over the top layer. Both cross under the body to the exits.
    path("USB_DN_C", [(cx - 0.75, ye), (xn, yi)])
    path("USB_DN_C", [(cx + 0.25, ye), (cx + 0.25, 8.8), (cx - 0.75, 8.8)])
    yd = yv + 0.6                                   # the D+ via, on pin 6's column
    path("USB_DP_C", [(cx + 0.75, ye), (cx + 0.75, yd - (xp - cx - 0.75)), (xp, yd), (xp, yi)])
    path("USB_DP_C", [(cx - 0.25, ye), (cx - 0.25, yv)])
    via(cx - 0.25, yv, "USB_DP_C", SVIA_D, SVIA_DRILL)
    path("USB_DP_C", [(cx - 0.25, yv), (xp - 0.6, yv), (xp, yd)], "F")
    via(xp, yd, "USB_DP_C", SVIA_D, SVIA_DRILL)
    for x, net in ((xn, "USB_DN_C"), (xp, "USB_DP_C")):
        path(net, [(x, yi), (x, yx)], w=0.2)
    # VCC: a small via between the lines, right above pin 5, and over the top layer east to a via on the VBUS_F
    # line from the fuse to the regulator (add_support: down from C_IN's pad row at 45 degrees to U3's VIN)
    yc5 = yi - 0.6 - 0.165 - SVIA_D / 2             # 0.165 mm from pin 5's pad: 0.13 of mask to its opening
    via(ex, yc5, "VBUS_F", SVIA_D, SVIA_DRILL)
    path("VBUS_F", [(ex, yc5), (ex, yi)], w=0.3)
    vf = (FUSE[0] + FUSE_PX + 0.4, LDO[1] + 1.2)    # on that line, 0.275 mm from C_IN's pad
    path("VBUS_F", [(ex, yc5), (vf[0] - (yc5 - vf[1]), yc5), vf], "F", 0.3)
    via(*vf, "VBUS_F", SVIA_D, SVIA_DRILL)
    # GND: its own via under the body, between the two rows
    seg(ex, yx, ex, ey, "GND", "B", 0.3)
    via(ex, ey, "GND")
    JOINED.update(("U4.4", "U4.5", "U4.6"))         # on J1's fixed copper; the exits U4.3 / U4.1 are router terminals
    # R_IN and F1 in series between J1 (VBUS) and the rest (VBUS_F: C_IN, the regulator and U4's VCC, add_support).
    # R_IN (1 ohm) damps the ringing of the cable's inductance with C_IN when VBUS is switched on hard; anywhere in
    # the series path does the same, and only here, in B4A9's line above the fuse, is there room for it.
    a, b = chip(pads, "R_IN", *R_IN, "VBUS", "VBUS_R", "1R", "C22936", vertical=True)
    fx, fy = FUSE
    seg(cx + 2.4, VBUS_VIA_Y, *a, "VBUS", "B", 0.4)
    seg(*b, fx - FUSE_PX, fy, "VBUS_R", "B", 0.4)
    pads.append(smd("F1.1", "VBUS_R", fx - FUSE_PX, fy, 1.0, 1.6))
    pads.append(smd("F1.2", "VBUS_F", fx + FUSE_PX, fy, 1.0, 1.6))
    part("F1", "MF-NSMF050-2", "C75464", fx, fy, 180, foot="1206")
    JOINED.update(("R_IN.1", "R_IN.2", "F1.1", "F1.2"))


# J1's metal shell seen from the top (HRO drawing: 8.94 wide, 7.35 long), its face 0.52 mm past the board edge
# (mech/check_fit.py and the 3D view take its face and width from here). It is grounded with only solder mask
# between it and the bottom copper, so nothing but J1's own pads may run under it (keepouts(); check.py measures
# it on the Gerbers).
J1_BODY = (USB_X - 4.47, -0.52, USB_X + 4.47, -0.52 + 7.35)
LDO = (134.4, 8.0)              # VIN pad 1.0 mm clear of J1's hand-soldered shell tab (check.py)
LDO_PX = 1.2                    # U3's pad centres east and west of LDO (add_support); the breakouts end there

# Nominal package bodies of the bottom-side parts by footprint name: (x, y) in JLC's footprint frame at
# rotation 0, swapped at 90 / 270. From JLC's package names where they give them (SOT-23-3_L2.9-W1.6,
# SOT-23-6_L2.9-W1.6, SOP-8_L4.9-W3.9, SOD-123F_L2.7-W1.6, CRYSTAL-SMD_4P-L3.2-W2.5, LQFN-56_L7.0-W7.0), which
# match the datasheets' nominal sizes (the 2N7002's SOT-23-3_L2.9-W1.3 fits in the regulator's); the chips at their
# EIA sizes (0603: 1.6 x 0.8, 0402: 1.0 x 0.5, the PTC fuse's 1206: 3.2 x 1.6, Bourns 3.0 to 3.4 x 1.4 to 1.8); J1
# is J1_BODY.
# Leads reaching past a body (SOT-23, SOIC, SOD-123) sit on their pads: precheck.py keeps every body BODY_GAP
# clear of every other body and of every pad of another part.
BODY = {"0603": (1.6, 0.8), "0402": (1.0, 0.5), "1206": (3.2, 1.6), "SOD-123": (2.7, 1.6), "SOT-23": (1.6, 2.9),
        "SOT-23-6": (2.9, 1.6), "SOIC-8 150mil": (4.9, 3.9), "LQFN-56 7x7": (7.0, 7.0), "3225 4-pad": (3.2, 2.5),
        "1206 reverse": (3.2, 1.6)}
BODY_GAP = 0.2


def bodies():
    """{ref: (x0, y0, x1, y1)} of every bottom-side part's body, seen from the top (after build())."""
    out = {}
    for ref, _value, _lcsc, x, y, rot, side in PARTS:
        if side != "bottom":
            continue
        if ref == "J1":
            out[ref] = J1_BODY
            continue
        w, h = BODY[FOOTPRINT[ref]]
        if rot % 180 == 90:
            w, h = h, w
        out[ref] = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    return out
XTAL = (130.7, 15.6)                # crystal centre, over the XIN fan-out end
XTAL_GND_VIA = (XTAL[0] + 1.1, XTAL[1] - 2.0)    # above the crystal's top-right GND pad; R_CC2's GND pad shares it


def build():
    pads = []
    for lst in (DIODES, NPTH, CUTOUTS, PARTS, FOOTPRINT, CPL_XY, FIXED_SEGS, FIXED_VIAS, BUS_PADS, JOINED,
                BUS_COPPER):
        lst.clear()
    # key matrix (switches on top, diodes underneath on the bottom)
    for r, y in enumerate(ROWS):
        for c, x in enumerate(COLS):
            n, kn = f"K{r}{c}", f"K{r}{c}_K"
            pads.append(th(n + ".A", ROW_GP[r], x - KEY_DX, y - KEY_DY, KEY_PAD, KEY_DRILL))
            # A/B bridged inside the switch
            pads.append(th(n + ".B", ROW_GP[r], x + KEY_DX, y - KEY_DY, KEY_PAD, KEY_DRILL))
            pads.append(th(n + ".C", None, x - KEY_DX, y + KEY_DY, KEY_PAD, KEY_DRILL))
            pads.append(th(n + ".D", kn, x + KEY_DX, y + KEY_DY, KEY_PAD, KEY_DRILL))
            part(n, "1-1825910-4", "C589907", x, y, side="top")      # TE FSM8JH: 6x6 mm, 9.5 mm, round plunger
            add_diode(pads, "D" + n, x, y, COL_GP[c], kn)
            BUS_PADS.update({n + ".A", n + ".B", "D" + n + ".A"})
        # row bus: one straight F line through the A/B pins of the row
        seg(COLS[0] - KEY_DX, y - KEY_DY, COLS[-1] + KEY_DX, y - KEY_DY, ROW_GP[r], "F", TRACE_W)
        BUS_COPPER.append(FIXED_SEGS[-1])
    for c, x in enumerate(COLS):    # column bus: straight B line through the diode anodes
        seg(x - DIO_DX, ROWS[0], x - DIO_DX, ROWS[-1], COL_GP[c], "B", TRACE_W)
        BUS_COPPER.append(FIXED_SEGS[-1])
        # 10k pull-up to 3V3 on the bus, between key rows 1 and 2: pad 1 sits on the bus line, pad 2 has a 3V3 via
        _, b = chip(pads, f"R_PU{c}", x - DIO_DX + CHIP["0603"][0], PULLUP_Y, COL_GP[c], "3V3", "10k", "C25804")
        plane_via(b, "3V3", 1.0, 0)
        BUS_PADS.add(f"R_PU{c}.1")
    # encoders (GPIO order on the east side follows the direction each signal leaves in):
    # GP18-21 ALT/HDG (north, then west over the top), GP22-25 FREQ, GP26/27 + GP16/17 FMS, GP28/29 RANGE (south, west)
    enc = ("PEC11D-4120F-S0015", "C19270361")
    add_encoder(pads, "ENC_ALTHDG", *ALTHDG, True, "GP18", "GP19", "GP20", "GP21", "ALTHDG_K", *enc)
    # (FREQ's outer B line is GP25 behind its series resistor, add_gp25_resistor)
    add_encoder(pads, "ENC_FREQ", *FREQ, True, "GP24", "GP25_R", "GP22", "GP23", PUSH_GP["FREQ"], *enc, push_d="GND")
    add_encoder(pads, "ENC_FMS", *FMS, True, "GP26", "GP27", "GP16", "GP17", "FMS_K", *enc)
    add_diode(pads, "D_FMS", FMS[0], FMS[1] + 3.0, COL_GP[R4_COL["FMS"]], "FMS_K")      # under the knob
    add_diode(pads, "D_ALTHDG", ALTHDG[0], ALTHDG[1] + 3.0, COL_GP[R4_COL["ALTHDG"]], "ALTHDG_K")      # under the knob
    add_rkjxt(pads, "RANGE", *RANGE, "GP28", "GP29")
    for name, ((lx, ly), gp, colour) in LEDS.items():
        add_led(pads, name, lx, ly, gp, colour, cathode_east=name in LED_CATHODE_EAST, switch=LED_SWITCH.get(name))
    # BOOT: bridge pads (QSPI_SS via R_BOOT), bridged with a small screwdriver through the body floor
    bx, by = BOOT
    pads.append(smd("JP_BOOT.1", "BOOT_SW", bx - 0.9, by, 1.2, 1.8, paste=False))
    pads.append(smd("JP_BOOT.2", "GND", bx + 0.9, by, 1.2, 1.8, paste=False))
    plane_via((bx + 0.9, by), "GND", 1.4, 0)

    # ---------------- electronics strip (bottom) ----------------
    add_rp2040(pads)
    add_usb(pads)
    add_flash(pads)
    add_support(pads)
    add_matrix_lanes(pads)
    return pads


def add_flash(pads):
    """W25Q16JVSNIQ on the bottom below the RP2040, hand-routed QSPI.
    Seen from the top the bottom part numbers clockwise; it sits with pin 1 bottom-right:
    top row (facing the RP2040) SD0 SCLK SD3 VCC, bottom row GND SD2 SD1 SS. SD0/SCLK/SD3 go straight
    up, SD2/SD1/SS come round the left side - the order matches the RP2040 fan-out, nothing crosses."""
    fan = {p.net: (p.x, p.y) for p in pads if re.match(r"U1\.F5[1-6]$", p.name)}
    fx = fan["QSPI_SD0"][0] + 1.905
    ft = MCU[1] + FAN_END + 4.0                 # 4 mm below the fan-out ends: room for C_1V1 at pin 50
    fb = ft + 5.37                              # pad rows 5.37 apart, as JLC's footprint of C2456211
    fl = {1: "QSPI_SS", 2: "QSPI_SD1", 3: "QSPI_SD2", 4: "GND", 5: "QSPI_SD0", 6: "QSPI_SCLK", 7: "QSPI_SD3", 8: "3V3"}
    fp = {}
    for p in range(1, 9):
        if p <= 4:
            fp[p] = (fx + 1.905 - 1.27 * (p - 1), fb)
        else:
            fp[p] = (fx - 1.905 + 1.27 * (p - 5), ft)
        pads.append(smd(f"U2.{p}", fl[p], *fp[p], 0.6, 1.87))
    part("U2", "W25Q16JVSNIQ", "C2456211", fx, (ft + fb) / 2, 0, foot="SOIC-8 150mil")
    plane_via(fp[8], "3V3", 0, (fb - ft) / 2)   # vias inside the body
    plane_via(fp[4], "GND", 0, -(fb - ft) / 2)

    path("QSPI_SD0", [fp[5], fan["QSPI_SD0"]], w=0.2)
    for p in (6, 7):
        net = fl[p]; x, _ = fp[p]; ex, ey = fan[net]
        path(net, [fp[p], (x, ft - 1.2), (ex, ft - 1.2 - (x - ex)), (ex, ey)], w=0.2)
    for p, ydrop in ((3, 1.5), (2, 2.1), (1, 2.7)):
        net = fl[p]; x, _ = fp[p]; ex, ey = fan[net]
        path(net, [fp[p], (x, fb + ydrop), (ex, fb + ydrop), (ex, ey)], w=0.2)
    # BOOTSEL: QSPI_SS -> 1k (right here, so the long wire to the button is no stub on the chip select)
    chip(pads, "R_BOOT", fan["QSPI_SS"][0] - 1.7, fb + 0.6, "QSPI_SS", "BOOT_SW", "1k", "C21190", vertical=True)
    a, b = chip(pads, "C_FL", 134.6, ft + 3.0, "3V3", "GND", "100nF", "C14663", vertical=True)
    plane_via(a, "3V3", 1.0, 0); plane_via(b, "GND", 1.0, 0)


def add_support(pads):
    mx, my = MCU
    # regulator XC6206P332MR (SOT-23: 1 GND, 2 VOUT, 3 VIN), VIN facing the USB-C socket. On the bottom,
    # seen from the top, the pins run clockwise: 1 north-east, 2 south-east, 3 west.
    # pads 1.1 x 0.6 from 0.65 to 1.75 off the centre line: JLC's footprint reaches 1.77, the leads up to 1.5
    # (Torex: 2.8 +-0.2 over the leads), so the joint gets a toe fillet
    lx, ly = LDO
    px = LDO_PX
    pads.append(smd("U3.3", "VBUS_F", lx - px, ly, 1.1, 0.6))
    pads.append(smd("U3.1", "GND", lx + px, ly - 0.95, 1.1, 0.6))
    pads.append(smd("U3.2", "3V3", lx + px, ly + 0.95, 1.1, 0.6))
    part("U3", "XC6206P332MR", "C5446", lx, ly, 180, foot="SOT-23")
    plane_via((lx + px, ly + 0.95), "3V3", 0, 1.05)
    # C_IN west of U3, between J1's shell tab and the VIN pin, its VBUS_F pad on the line from the fuse and its GND
    # pad towards the (GND) tab: the VBUS_F pad 1.9 mm from the hand-soldered tab (0.8 mm before, a bridge to GND),
    # and the way north past U3 stays free for the lines over the top (C_IN sat in it, north of U3). 10 uF, the
    # part of C_OUT0. When VBUS is switched on hard (a live USB-A port), the cable's inductance rings with C_IN;
    # R_IN (1 ohm, add_protection) in series with the cable and the fuse damps it, so the modelled input stays
    # under the XC6206's 7.0 V absolute maximum. The model's cable is 0.3 to 3 uH and 0.05 to 0.4 ohm, the fuse
    # 0.15 to 0.7 ohm; its other assumptions and its peaks are in docs/architecture/electronics.md. 10 uF is
    # USB 2.0's limit for a device at attach, and the regulator's output capacitors add to it.
    a, b = chip(pads, "C_IN", lx - 2.5, ly + 0.8, "GND", "VBUS_F", "10uF", "C19702", vertical=True)
    plane_via(a, "GND", -0.9, 0, SVIA_D)            # small: a 0.13 mm mask strip to C_IN's GND pad opening
    vx = lx - px                        # U3's VIN pad centre
    fx = FUSE[0] + FUSE_PX              # the fuse's VBUS_F pad
    path("VBUS_F", [b, (fx, b[1]), (vx, b[1] - (vx - fx)), (vx, ly)], w=0.4)
    seg(fx, FUSE[1], fx, b[1], "VBUS_F", "B", 0.4)
    JOINED.update(("U3.3", "C_IN.2"))   # both on the fixed VBUS_F line from the fuse: no router terminals
    a, b = chip(pads, "C_OUT0", lx + px, ly - 3.1, "3V3", "GND", "10uF", "C19702", vertical=True)
    seg(b[0], b[1], lx + px, ly - 0.95, "GND", "B", 0.4)           # cap GND straight to the regulator's GND pin
    plane_via(a, "3V3", 0, -1.0); plane_via(b, "GND", 1.0, 0)
    add_crystal(pads)
    d2, ybelow = add_core_caps(pads)
    add_io_caps(pads)
    # USB series resistors 27R next to the RP2040's USB pins (south side), below the capacitors in the corner:
    # D- on top, D+ below, the RP2040 side on the left. The lines from the USB-C come down on the top layer and
    # land on two vias just below the resistors (D- between the pads, D+ under its pad), clear of the pads and
    # west of the lane the east-side lines take south; the router ends them there.
    xr = d2[0] - 0.6
    (_, dm2), (_, dp2) = [chip(pads, ref, xr, ybelow + dy, net, net_c, "27R", "C25190")
                          for ref, dy, net, net_c in (("R_DM", 0.475, "USB_DM", "USB_DN_C"),
                                                      ("R_DP", 1.875, "USB_DP", "USB_DP_C"))]
    yv = dp2[1] + 1.225
    for ref, net_c, (vx, vy), pts in (("R_DM", "USB_DN_C", (xr, yv), [(xr, dm2[1]), dm2]),
                                      ("R_DP", "USB_DP_C", (dp2[0] + 0.1, yv), [dp2])):
        path(net_c, [(vx, vy)] + pts, w=TRACE_W)
        via(vx, vy, net_c)
        pads.append(Pad(f"{ref}.E", net_c, vx, vy, "circle", 0.3, 0.3, "F", paste=False, mask=False))
        JOINED.add(f"{ref}.2")
    # decoupling on the 3V3 / GND planes, besides the capacitor at each IOVDD pin (add_io_caps). C_D0 sat north-west
    # of the chip, where the USB lines now leave the ESD array; the pins it shared have capacitors of their own.
    for name, (cxx, cyy, d3, dg) in (("C_D1", (136.4, 12.8, (1.0, 0), (1.0, 0))),
                                     ("C_D2", (*d2, (1.0, 0), (1.0, 0))),        # next to pins 42-44, 1 uF
                                     ("C_D3", (MCU[0] - 4.5, 47.4, (-1.0, 0), (1.0, 0)))):
        # C_D2 at VREG_VIN (pin 44) is 1 uF: RP2040 datasheet 2.9.3 / 2.10.1, 1 uF close to VREG_VIN
        val, lc = ("1uF", "C15849") if name == "C_D2" else ("100nF", "C14663")
        a, b = chip(pads, name, cxx, cyy, "3V3", "GND", val, lc, vertical=True)
        plane_via(a, "3V3", *d3); plane_via(b, "GND", *dg)
    # bulk capacitor on the 3V3 plane at the matrix side of the chip (C_OUT0 is the bulk at the regulator)
    a, b = chip(pads, "C_BULK", 124.6, 44.0, "3V3", "GND", "1uF", "C15849", vertical=True)
    plane_via(a, "3V3", 1.0, 0); plane_via(b, "GND", 1.0, 0)


def add_crystal(pads):
    """12 MHz crystal ABM8-272-T3 (3225 4-pad) right above XIN / XOUT, with its load capacitors and the 1k, all on
    hand-routed copper. Abracon's drawing (bottom view): #1 top-left and #3 bottom-right are the crystal, #2
    and #4 GND. JLC's footprint of C20625731 has pin 1 bottom-left in its top view, so on the bottom at
    rotation 0 (mirrored left to right), seen from the top: 1 bottom-right (XO_R), 2 bottom-left (GND), 3
    top-left (XIN), 4 top-right (GND). XIN comes straight up from its fan-out end between the two lower pads;
    XOUT runs from its fan-out end east to the 1k 1.8 mm south of the crystal centre, clear of the crystal body
    and pads, XO_R from the 1k round the east side of the crystal and up to C_X2. The two GND pads each go to
    the plane: the top-right one through its own via, the bottom-left one through C_X1's GND pad and via."""
    yx, yy = XTAL
    ends = {p.net: (p.x, p.y) for p in pads if re.match(r"U1\.F2[01]$", p.name)}
    if abs(ends["XIN"][0] - yx) > 1e-6:
        raise ValueError("the crystal must sit centred over the XIN fan-out end")
    pads.append(smd("Y1.1", "XO_R", yx + 1.1, yy + 0.8, 1.4, 1.2))
    pads.append(smd("Y1.2", "GND", yx - 1.1, yy + 0.8, 1.4, 1.2))
    pads.append(smd("Y1.3", "XIN", yx - 1.1, yy - 0.8, 1.4, 1.2))
    pads.append(smd("Y1.4", "GND", yx + 1.1, yy - 0.8, 1.4, 1.2))
    part("Y1", "ABM8-272-T3 12MHz", "C20625731", yx, yy, 0, foot="3225 4-pad")
    plane_via((yx + 1.1, yy - 0.8), "GND", 0, XTAL_GND_VIA[1] - (yy - 0.8))
    cx, rx = yx - 2.8, yx + 3.1                         # C_X1 west of the crystal, R_X and C_X2 east of it
    a, b = chip(pads, "C_X1", cx, yy, "XIN", "GND", "15pF", "C1644", vertical=True)
    seg(*a, yx - 1.1, yy - 0.8, "XIN", "B", TRACE_W)
    seg(*b, yx - 1.1, yy + 0.8, "GND", "B", 0.3)
    plane_via(b, "GND", -1.0, 0)
    a, _ = chip(pads, "C_X2", rx, yy - 2.6, "GND", "XO_R", "15pF", "C1644", vertical=True)
    plane_via(a, "GND", 1.0, 0)
    (_, r1), (_, r2) = chip(pads, "R_X", rx, yy, "XO_R", "XOUT", "1k", "C21190", vertical=True)
    ex, ey = ends["XIN"]
    path("XIN", [(ex, ey), (ex, yy), (yx - 1.1, yy - 0.8)], w=TRACE_W)
    ex, ey = ends["XOUT"]
    path("XOUT", [(ex, ey), (ex, yy + 1.8), (rx - 1.0, yy + 1.8), (rx, r2)], w=TRACE_W)
    path("XO_R", [(yx + 1.1, yy + 0.8), (rx - 0.9, yy + 0.8), (rx - 0.9, r1), (rx, r1), (rx, yy - 1.8)], w=TRACE_W)


def add_core_caps(pads):
    """Decoupling at the RP2040's south-east pins, as in Raspberry Pi's minimal design, all on pre-routed
    copper. The corner east of the USB fan-out holds C_D2 (1 uF, 3V3: VREG_VIN wants 1 uF) where it always
    was, fed straight from pin 42 and through the 3V3 via of pins 42-44 (IOVDD, ADC_AVDD, VREG_VIN), and
    beside it two 0402 capacitors fed straight from pin 45: C_1V0 (1 uF, VREG_VOUT) and C_1V2 (100 nF). C_1V1
    (100 nF, DVDD) sits right below pin 50, between the QSPI and USB fan-outs. Every capacitor has its own GND
    via. Pin 23 (DVDD, north side) joins over the top layer: V23 -> V45 -> V50 over the chip. Returns C_D2's
    centre and the top of the free band below the corner, for the USB resistors."""
    mx, my = MCU
    yo = my + 3.875                                     # outer end of the south QFN pads
    x45 = mx + qfn_pad_xy(45)[0][0]
    x50 = mx + qfn_pad_xy(50)[0][0]
    # corner: feed along under pins 44 / 43, the two 0402 hang from it (1V1 on top), C_D2 east of them
    yf = yo + 0.425
    c1, c2 = x45 + 1.125, x45 + 1.925                   # 0402 columns, 0.25 mm apart (0.18 mm mask dam)
    for name, x, val, lc in (("C_1V0", c1, "1uF", "C52923"), ("C_1V2", c2, "100nF", "C1525")):
        chip(pads, name, x, yf + 0.65, "1V1", "GND", val, lc, vertical=True, size="0402")
    # down, then clear of pin 46's fan-out
    path("1V1", [(x45, yo), (x45, yf - 0.25), (x45 + 0.25, yf), (c2, yf)], w=TRACE_W)
    for x in (c1, c2):  # GND vias right below the 0402 GND pads, small: 0.2 mm from R_DM's USB_DM pad
        plane_via((x, yf + 1.15), "GND", 0, 0.75, SVIA_D)
    # C_D2: 3V3 pad at y 29.1, GND pad at 30.7; its 3V3 pad 0.3 mm from C_1V2's 1V1 pad beside it, so a solder
    # bridge between the two (core supply to 3.3 V) is no likelier than between any other pair of parts
    d2 = (x45 + 2.975, my + 4.9)
    # pin 42's outer end straight to C_D2's 3V3 pad, below pin 41's fan-out (pins 43 / 44 join through their via)
    x42, y42 = mx + 3.875, my + qfn_pad_xy(42)[0][1]
    path("3V3", [(x42, y42), (x42 + 0.325, y42 + 0.325), (d2[0], d2[1] - 0.8)], w=TRACE_W)
    # below pins 50 and 49, between the fan-outs of pins 51 and 47: two 0402 0.25 mm apart, C_1V1 (DVDD, pin 50)
    # straight below its pin and C_IO49 (IOVDD pin 49, with USB_VDD pin 48 beside it) east of it
    x49, x48 = (mx + qfn_pad_xy(n)[0][0] for n in (49, 48))
    yc = yo + 2.025                                     # far enough down for the fan-outs to have spread
    a, b = chip(pads, "C_1V1", x50, yc, "1V1", "GND", "100nF", "C1525", vertical=True, size="0402")
    seg(x50, yo, *a, "1V1", "B", TRACE_W)
    plane_via(b, "GND", 0, 1.0)
    a, b = chip(pads, "C_IO49", x50 + 0.8, yc, "3V3", "GND", "100nF", "C1525", vertical=True, size="0402")
    # pin 49 down and across to pin 48's line at a right angle (a 45 degree join left an acute notch)
    path("3V3", [(x49, yo), (x49, yo + 0.6), (x48, yo + 0.6)], w=0.2)
    seg(x48, yo, *a, "3V3", "B", 0.2)
    plane_via(b, "GND", 0, 1.0)
    # the three 1V1 vias joined on the top layer, round the 3V3 via of pins 48/49 and the exposed pad's vias
    v23, v45, v50 = [next((p.x, p.y) for p in pads if p.name == f"U1.V{n}") for n in (23, 45, 50)]
    yl = v45[1] - 0.75
    path("1V1", [v23, (v23[0] + 0.5, v23[1] + 0.5), (v23[0] + 0.5, yl), (v50[0], yl), v50], "F", TRACE_W)
    seg(v45[0], v45[1], v45[0], yl, "1V1", "F", TRACE_W)
    return d2, yf + 1.9 + 0.3 + 0.15                     # below the 0402 GND vias


def add_io_caps(pads):
    """One 100 nF (0402) per IOVDD pin, as in Raspberry Pi's minimal design (issue #15), each on its own trace
    from the pin and with its own GND via. Pin 42 has C_D2 (add_core_caps), pin 49 C_IO49 (with USB_VDD, pin 48).
    The others sit inside the fan-out, where no pin of theirs fans out:
    - pin 1 (west, the corner pin): below pin 2's fan-out line, south-west of the pin
    - pin 10 (west): along the pin's own fan-out lane (it has no signal), the capacitor in the lane just past the
      fan-out vias, where that pin's via would be; the matrix lanes on the top layer leave that row free
    - pin 22 (north): in the gap above pins 22 and 23 (DVDD) between the fan-outs of pins 21 and 24
    Pin 33 (east) has none: the same spot east of the fan-out is the only way north for the ALT/HDG and FREQ lines
    (GP18 to GP23), between the fan-out vias and the FREQ encoder's pin A 3.4 mm further east. A capacitor there,
    with its GND via south, north or north-east of it, left one of GP20 to GP24 unrouted on every seed from 1 to
    14. Pin 33 drops into the 3V3 plane through its via under the chip, as before (check.py: PLANE_SHARED)."""
    mx, my = MCU

    def outer(pin):
        (px, py), (nx, ny), lat = qfn_pad_xy(pin)
        return mx + px + nx * 0.4375, my + py + ny * 0.4375, nx, ny, lat
    # pin 1: straight from the pad's outer end, 45 degrees down to the capacitor
    ox, oy, *_ = outer(1)
    a, b = chip(pads, "C_IO1", ox - 0.725, oy + 1.2, "3V3", "GND", "100nF", "C1525", vertical=True, size="0402")
    path("3V3", [(ox, oy), a], w=0.2)
    plane_via(b, "GND", 0, 1.0)
    # pin 10: the fan-out line the pin would have, then on into the capacitor's 3V3 pad 0.45 mm past the via
    # column; the GND pad beyond it, its via 1 mm further west
    ox, oy, nx, _ny, lat = outer(10)
    ex, ey = mx + nx * FAN_END_W, my + lat * FAN_SPREAD_W
    a, b = chip(pads, "C_IO10", ex - 0.95, ey, "GND", "3V3", "100nF", "C1525", size="0402")
    path("3V3", [(ox, oy), (ox + nx * 0.4, oy), (ex, ey), b])
    plane_via(a, "GND", -1.0, 0)
    # pin 22: up from the pad's outer end, the capacitor 0.2 mm east of the pin, its GND via above it
    ox, oy, *_ = outer(22)
    a, b = chip(pads, "C_IO22", ox + 0.2, oy - 1.225, "GND", "3V3", "100nF", "C1525", vertical=True, size="0402")
    path("3V3", [(ox, oy), (ox, oy - 0.525), b], w=0.2)
    plane_via(a, "GND", 0, -1.0)


def add_matrix_lanes(pads):
    """Last mile from the matrix buses to the RP2040 fan-out ends (vias), planned by hand, all on F.

    Arrivals from the key field (top to bottom) are R0, C6, C5, R1, C4, C3, R2, C2, C1, R3, C0, R4 - the
    same order as the fan-out ends of GPIO11..0. Rows arrive on their own F lines; columns leave their
    B bus through a via into the free band between two key rows. Each net then turns into its own
    vertical lane; outer nets use the lanes nearest the chip, so nothing crosses."""
    end = {p.net: (p.x, p.y) for p in pads if re.match(r"U1\.F\d+$", p.name) and p.net in BUS_NETS}
    ex = end[ROW_GP[0]][0]
    def lane(k):
        return ex - 0.6 - 0.45 * k
    xr = COLS[-1] + KEY_DX                      # right end of the row lines
    rowy = [y - KEY_DY for y in ROWS]
    bands = {6: ROWS[0] + 3.95, 5: ROWS[0] + 4.7, 4: ROWS[1] + 3.95, 3: ROWS[1] + 4.7,
             2: ROWS[2] + 3.6, 1: ROWS[3] - 3.55, 0: ROWS[3] + 3.6}   # rows 2/3: either side of the UNIT cutout

    def lane_path(net, pts):
        n = len(FIXED_SEGS)
        path(net, pts, "F", TRACE_W)
        BUS_COPPER.extend(FIXED_SEGS[n:])
    arr = [(ROW_GP[0], rowy[0]), (COL_GP[6], bands[6]), (COL_GP[5], bands[5]), (ROW_GP[1], rowy[1]),
           (COL_GP[4], bands[4]), (COL_GP[3], bands[3]), (ROW_GP[2], rowy[2]), (COL_GP[2], bands[2]),
           (COL_GP[1], bands[1]), (ROW_GP[3], rowy[3]), (COL_GP[0], bands[0])]
    down = [a for a in arr if a[1] <= end[a[0]][1]]          # arrive above their fan-out end
    up = [a for a in arr if a[1] > end[a[0]][1]][::-1]       # arrive below, outermost first
    for group in (down, up):
        for k, (net, y0) in enumerate(group):
            x0 = xr if net in ROW_GP else COLS[COL_GP.index(net)] - DIO_DX
            lane_path(net, [(x0, y0), (lane(k), y0), (lane(k), end[net][1]), end[net]])
    for c in range(7):                          # column bus -> band via
        x, y = COLS[c] - DIO_DX, bands[c]
        via(x, y, COL_GP[c]); BUS_COPPER.append(("via",) + FIXED_VIAS[-1])
    seg(COLS[0] - DIO_DX, ROWS[-1], COLS[0] - DIO_DX, bands[0], COL_GP[0], "B", TRACE_W)
    BUS_COPPER.append(FIXED_SEGS[-1])
    # row 4 (knob / joystick pushes): a short lane below the bottom-most fan-out end, the router does the rest
    r4 = ROW_GP[4]
    lane_path(r4, [end[r4], (lane(-1) + 0.3, end[r4][1]), (lane(-1) + 0.3, 31.0)])


def route_bias():
    """Soft routing costs: (layers, rect, pays(net), extra cost per grid step). The band between the north
    fan-out ends and the crystal is the only way out to the west for GP12, GP13 and GP15; any other net
    crossing it (the USB-C lines take it on their way south) pays extra, so it
    goes round the east side when it can.
    The ALT/HDG lines (GP18-21) leave the east fan-out north and cross over J1 on the top layer (the bottom
    under its shell is kept free). Between the two they pay for the top layer, so they run north on the bottom
    and change layers north-east of J1: on the top layer they would wall off GP13 (FREQ push, which starts on
    the top layer at the north fan-out and runs north-east). For the same reason the USB-C lines pay for the
    top layer north-east of GP13's start, so they come down west of it and cross the fan-out south of it."""
    mx, my = MCU
    north_west = {RP[p] for p in range(15, 19)}                         # GP12-15
    alt_hdg = {RP[p] for p in range(29, 33)}                            # GP18-21
    usb_c = {"USB_DN_C", "USB_DP_C"}
    return [("FB", (mx - FAN_END_W, my - FAN_END - 4.0, mx - 1.0, my - FAN_END + 0.3),
             lambda n: n not in north_west, 2.0),
            ("F", (J1_BODY[2] + 1.0, 5.0, W, my - FAN_END), lambda n: n in alt_hdg, 2.0),
            ("F", (mx - 2.5, 10.0, mx + 6.0, my - FAN_END), lambda n: n in usb_c, 3.0)]


def keepouts():
    k = []
    for (x, y) in MOUNTS:
        k.append(("FB", "circle", (x, y, MOUNT_KEEPOUT)))
    # inside the QFN fan-out square only the pre-routed fan-out may run on the bottom
    mx, my = MCU
    e = FAN_END - 0.3
    k.append(("B", "rect", (mx - FAN_END_W + 0.3, my - e, mx + e, my + e)))
    # USB-C: the shell (J1_BODY), the contacts and their pre-routed breakout into the ESD array, with the VBUS and
    # D+ links on the top layer
    k.append(("B", "rect", J1_BODY))
    k.append(("B", "rect", (USB_X - 3.4, 5.8, USB_X + 3.4, ESD[1] - ESD_PY)))
    k.append(("F", "rect", (USB_X - 2.6, 7.6, USB_X + 1.4, ESD[1] - ESD_PY - 0.5)))
    for (x, y, d) in NPTH:
        k.append(("FB", "circle", (x, y, d / 2 + 0.4)))
    # the LED cutouts: copper JLCPCB's 0.2 mm from the routed edge, and the router's clearance on top
    for (x, y, w, h, _r) in CUTOUTS:
        e = LED_CUT_CLEAR + CLEAR
        k.append(("FB", "rect", (x - w / 2 - e, y - h / 2 - e, x + w / 2 + e, y + h / 2 + e)))
    return k
