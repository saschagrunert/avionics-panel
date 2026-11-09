"""DIY Avionics Panel rev 1 - RP2040 directly on the board, USB-C, 4 layers.

Knob set ALT/HDG + RANGE (Alps RKJXT, turn / 4-way tilt / push) left, FREQ + FMS right, 28 keys, two
lights, BOOT as bridge pads under a hole in the case floor, SWD debug points.

Top view (component side), mm, origin top-left, y down. Layer stack: F (signals), In1 = GND plane,
In2 = 3V3 plane, B (signals). Switches, knobs and the RANGE control (THT) sit on top; every SMD part
(RP2040, flash, USB-C, regulator, diodes, passives) is on the bottom, so JLCPCB assembles one SMD side.

Footprint sources:
  RP2040 QFN-56: RP2040 datasheet fig. 165 (pads 0.20 x 0.875, pitch 0.40, 7.75/6.00, EP 3.20)
  RP2040 pinout: RP2040 datasheet fig. 3
  USB-C HRO TYPE-C-31-M-12: JLC/EasyEDA footprint of C165948 (pad row, pads 0.3/0.6 x 1.3), HRO drawing
  PEC11D-4120F-S0015: Bourns PEC11D datasheet (recommended PCB layout, holes 1.2), checked against JLC's
      footprint of C19270361
  RKJXT1F42001: Alps drawing, checked against JLC's footprint of C160841
  6x6 key switches (TE 1-1825910-4): pins 6.5 x 4.5, the 6.5 mm pairs connected inside

Bottom-side parts: seen from the top, a part on the bottom is mirrored, so its pins number clockwise.
check.py asserts that for every bottom part with three or more numbered pins.
Circuit follows Raspberry Pi's "Hardware design with RP2040" minimal design.
"""
import re

SHIFT_X = 9.0           # electronics strip + right knob column, moved right as one block from the first draft
XR = 136.0 + SHIFT_X    # right knob column (FREQ over FMS)
W, H = 160.0, 60.0      # layout: ALT/HDG over RANGE | keys | electronics strip (bottom) | FREQ over FMS
CORNER_R = 3.0
TRACE_W = 0.25
FAN_W = 0.16            # QFN / USB fan-out traces
CLEAR = 0.15
POUR_CLEAR = 0.30
EDGE_CLEAR = 0.50
VIA_D, VIA_DRILL = 0.60, 0.30
SVIA_D, SVIA_DRILL = 0.50, 0.30     # small vias (USB-C, fan-out ends): JLC standard 0.3 mm drill, 0.45 mm pad min.
MOUNT_HOLE = 3.2
MOUNTS = [(3.5, 3.5), (W - 3.5, 3.5), (3.5, H - 3.5), (W - 3.5, H - 3.5)]
PLANES = {"In1": "GND", "In2": "3V3"}

KEY_DX, KEY_DY, KEY_PAD, KEY_DRILL = 3.25, 2.25, 1.8, 1.0
DIO_DX, DIO_W, DIO_H = 1.65, 1.0, 1.3
ENC_PAD, ENC_DRILL = 1.8, 1.2   # Bourns PEC11D: pin holes 1.2 +0.1/-0
SLOT = (1.5, 2.6)

COL_PITCH = 11.85
COLS = [40.0 + COL_PITCH * k for k in range(3)] + [116.35 - COL_PITCH * k for k in (3, 2, 1, 0)]
ROWS = [12.5, 23.5, 38.0, 49.0]         # rows 2/3 lower: room for the FMS line on the plate
KEY_LABELS = [
    ["AP", "ALT", "HDG", "MIC 1", "COM 1", "CDI", "COM<>"],
    ["FD", "VS", "NAV", "MIC 2", "COM 2", "IDENT", "NAV<>"],
    ["UP", "FLC", "APR", "HOME", "FPL", "D->", "MENU"],
    ["DN", "VNV", "LVL", "SHIFT", "PROC", "CLR", "ENT"],
]
ALTHDG, RANGE = (15.0, 15.0), (15.0, 45.0)   # left: ALT/HDG dual over RANGE (RKJXT: turn, 4-way tilt, push)
FREQ, FMS = (XR, 15.0), (XR, 45.0)          # right: frequency dual over FMS dual
MCU = (122.6 + SHIFT_X, 25.0)   # RP2040 on the bottom, mirrored (pins 1-14 face the keys, bottom to top)
USB_X = 118.0 + SHIFT_X
BOOT = (MCU[0] + 0.5, 54.0)     # bridge pads on the bottom, under a hole in the case floor
# debug pads on the top side over the RP2040 (no part body there), 2 x 2 at 2 mm, reachable with the plate off
LEDS = {"SHIFT": ((COLS[3], ROWS[3] + 3.2 + 1.75), "GP12", "amber"),    # light pipes in the front plate
        "UNIT": ((COLS[3] + 4.3, ROWS[2] + 3.2 + 1.6), "GP15", "white")}

# GPIO plan (RP2040 GPIO number -> function)
# matrix lines leave the RP2040 (pins 14..2, top to bottom on the mirrored chip) in the order the
# rows/columns arrive from the key field
ROW_GP = ["GP11", "GP8", "GP5", "GP2", "GP0"]           # rows 0-3 keys, row 4: RANGE switches + ALT/HDG push
COL_GP = ["GP1", "GP3", "GP4", "GP6", "GP7", "GP9", "GP10"]
R4_COL = {"ALTHDG": 5, "FMS": 6}       # row 4: RANGE A, B, C, D, com on columns 0-4, ALT/HDG push 5, FMS push 6
PUSH_GP = {"FREQ": "GP13"}               # FREQ push: direct input (pull-up, switch to GND). GP14 is the spare pin

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
    RP[pin] = f"GP{12 + i}"                 # GPIO12-15: SHIFT light, FREQ push, spare (debug pad), UNIT light
for i, pin in enumerate(range(34, 38)):
    RP[pin] = f"GP{22 + i}"                 # GPIO22-25 (FREQ)
RP[40], RP[41] = "GP28", "GP29"             # RANGE encoder
RP[27], RP[28] = "GP16", "GP17"             # FMS inner ring
for i, pin in enumerate(range(29, 33)):
    RP[pin] = f"GP{18 + i}"                 # GPIO18-21 (ALT/HDG)
RP[38], RP[39] = "GP26", "GP27"             # FMS outer ring


class Pad:
    def __init__(self, name, net, x, y, shape, w, h, layers, drill=None, slot=None, paste=True):
        self.name, self.net, self.x, self.y = name, net, x, y
        self.shape, self.w, self.h = shape, w, h            # circle | obround | rect
        self.layers, self.drill, self.slot, self.paste = layers, drill, slot, paste

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
PREROUTED = {"QSPI_SD0", "QSPI_SD1", "QSPI_SD2", "QSPI_SD3", "QSPI_SCLK"}
FIXED_SEGS, FIXED_VIAS = [], []
BUS_PADS = set()            # pads already joined by a pre-routed matrix bus
BUS_COPPER = []             # (kind, args) of the bus copper: the router grows the net from it
BUS_NETS = set(ROW_GP) | set(COL_GP)          # pre-routed copper: (x1,y1,x2,y2,layer,net,width) / (x,y,net,d,drill)


def seg(x1, y1, x2, y2, net, layer="B", w=FAN_W):
    FIXED_SEGS.append((x1, y1, x2, y2, layer, net, w))


def via(x, y, net, d=VIA_D, drill=VIA_DRILL):
    FIXED_VIAS.append((x, y, net, d, drill))


def th(name, net, x, y, pad=ENC_PAD, drill=ENC_DRILL):
    return Pad(name, net, x, y, "circle", pad, pad, "FB", drill)


def smd(name, net, x, y, w, h, shape="rect", paste=True, layer="B"):
    return Pad(name, net, x, y, shape, w, h, layer, paste=paste)


def part(ref, value, lcsc, x, y, rot=0, side="bottom"):
    PARTS.append((ref, value, lcsc, x, y, rot, side))


def r0603(pads, ref, x, y, net1, net2, value, lcsc, vertical=False):
    """0603 resistor/capacitor; pad 1 left (or top), pad 2 right (or bottom)."""
    dx, dy = (0, 0.8) if vertical else (0.8, 0)
    w, h = (0.95, 0.8) if vertical else (0.8, 0.95)
    pads.append(smd(f"{ref}.1", net1, x - dx, y - dy, w, h))
    pads.append(smd(f"{ref}.2", net2, x + dx, y + dy, w, h))
    part(ref, value, lcsc, x, y, 90 if vertical else 0)
    return (x - dx, y - dy), (x + dx, y + dy)


def plane_via(pad_xy, net, dx, dy):
    """Short stub from an SMD pad to a via into the GND / 3V3 plane."""
    x, y = pad_xy
    seg(x, y, x + dx, y + dy, net, "B", 0.3)
    via(x + dx, y + dy, net)


def add_diode(pads, name, x, y, anode, cathode):
    pads.append(smd(name + ".A", anode, x - DIO_DX, y, DIO_W, DIO_H, "obround"))
    pads.append(smd(name + ".K", cathode, x + DIO_DX, y, DIO_W, DIO_H, "obround"))
    DIODES.append((name, x, y))
    part(name, "1N4148W", "C81598", x, y)


def add_encoder(pads, ref, cx, cy, dual, a, b, a2=None, b2=None, push_k=None, val="", lcsc="", push_d=None):
    for dx, nm, net in ((-2.5, "A", a), (0, "C", "GND"), (2.5, "B", b)):
        pads.append(th(f"{ref}.{nm}", net, cx + dx, cy + 7.5))
    pads.append(th(f"{ref}.D", push_d or ROW_GP[4], cx - 2.5, cy - 7.0))
    pads.append(th(f"{ref}.E", push_k, cx + 2.5, cy - 7.0))
    if dual:
        for dx, nm, net in ((-2.5, "A2", a2), (0, "C2", "GND"), (2.5, "B2", b2)):
            pads.append(th(f"{ref}.{nm}", net, cx + dx, cy - 9.5))
    for s in (-1, 1):
        pads.append(Pad(f"{ref}.MP{s}", None, cx + s * 5.5, cy, "obround", 2.5, 3.6, "FB",
                        drill=SLOT[0], slot=SLOT))
    part(ref, val, lcsc, cx, cy, side="top")


# Alps RKJXT1F42001 (LCSC C160841): turn (15 pulses / 30 detents), 4-way tilt, centre push. Hole pattern read
# from the Alps mounting-hole drawing, 11 x 1.0 mm, verified against JLC's footprint (below).
# Switches: "Push" is common to all; A, B, C, D close with their direction, "com" closes on every operation
# (centre push = com without A-D, decoded in firmware).
RKJXT_HOLES = {"ECOM": (-1.5, -7.8), "C": (1.5, -7.8), "COM": (-1.0, -5.78), "D": (-7.8, -1.5),
               "ENCA": (-7.8, 1.5), "LUG": (-3.8, 1.5), "ENCB": (7.8, -1.5), "B": (7.8, 1.5),
               "GND": (6.68, 3.75), "A": (-1.5, 7.8), "PUSH": (1.0, 6.98)}
# Checked against JLC's own footprint of C160841 (EasyEDA SW-TH_RKJXT1F42001): all 11 positions agree after
# correcting PUSH (x 0.5 -> 1.0) and GND (x 6.86 -> 6.68), the two the Alps drawing did not dimension.


def add_rkjxt(pads, ref, cx, cy, enc_a, enc_b):
    legs = ["A", "B", "C", "D", "COM"]                  # -> diodes -> columns 0-4, common "Push" on row 4
    for nm, (dx, dy) in RKJXT_HOLES.items():
        x, y = cx + dx, cy + dy
        if nm == "LUG":
            NPTH.append((x, y, 1.1))
            continue
        net = {"ECOM": "GND", "GND": "GND", "ENCA": enc_a, "ENCB": enc_b, "PUSH": ROW_GP[4]}.get(nm, f"{ref}_{nm}")
        pads.append(Pad(f"{ref}.{nm}", net, x, y, "circle", 1.7, 1.7, "FB", 1.0))
    for k, nm in enumerate(legs):                       # diodes in the free column between the knobs and the keys
        add_diode(pads, f"D_{ref}_{nm}", 28.5, cy - 6.0 + 3.0 * k, COL_GP[k], f"{ref}_{nm}")
    part(ref, "RKJXT1F42001", "C160841", cx, cy, side="top")


def add_led(pads, name, x, y, gpio, colour):
    """3 mm THT LED under a light pipe in the front plate; series resistor on the bottom."""
    anode = f"LED_{name}_A"
    pads.append(Pad(f"LED_{name}.A", anode, x + 1.27, y, "circle", 1.6, 1.6, "FB", 0.9))   # anode next to R pad 2
    pads.append(Pad(f"LED_{name}.K", "GND", x - 1.27, y, "rect", 1.6, 1.6, "FB", 0.9))
    # XINGLIGHT XL-302UYC (yellow 588 nm, the closest 3 mm amber, clear lens) / XL-302UWC (white, clear lens).
    # Amber about 3 mA from a 3.3 V GPIO. The white LED's forward voltage is 2.7 to 3.0 V at a few mA (3.2 V
    # typical at 20 mA), so it gets a small resistor: 22R gives roughly 2 to 7 mA over that spread, with the
    # GPIO driver's own resistance (default 4 mA drive) in series. The firmware sets both brightnesses with PWM.
    led_part, res, res_lcsc = {"amber": ("XL-302UYC", "330R", "C23138"),
                               "white": ("XL-302UWC", "22R", "C23345")}[colour]
    part(f"LED_{name}", led_part, {"XL-302UYC": "C2895466", "XL-302UWC": "C2895458"}[led_part], x, y, side="top")
    r0603(pads, f"R_{name}", x, y + 1.55, gpio, anode, res, res_lcsc)


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
FAN_END_W, FAN_SPREAD_W = 7.5, 2.15     # west (matrix) and east (knobs): 0.86 mm pitch, a via on every end (0.56 mm between holes)


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
        pads.append(smd(f"U1.F{pin}", net, ex, ey, 0.3, 0.3, "circle", paste=False))   # breakout point
    pads.append(smd("U1.EP", "GND", mx, my, 3.2, 3.2, "rect", paste=False))
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
        if net == "1V1":
            pads.append(Pad(f"U1.V{pins[0]}", "1V1", mx + vx, my + vy, "circle", 0.6, 0.6, "FB", paste=False))
    (px, py), _, _ = qfn_pad_xy(19)                         # TESTEN to the exposed pad
    seg(mx + px, my + py + 0.4375, mx + px, my - 1.6, "GND", "B", 0.2)
    part("U1", "RP2040", "C2040", mx, my)
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
    # west and east fan-out ends get a via (matrix: the last mile comes in on F)
    for p in list(pads):
        if re.match(r"U1\.F\d+$", p.name) and (abs(p.x - mx) > FAN_END or False):
            via(p.x, p.y, p.net, SVIA_D, SVIA_DRILL)
            if p.net in BUS_NETS:
                BUS_COPPER.append(("via",) + FIXED_VIAS[-1])


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
        pads.append(Pad(f"J1.SH{s}a", "GND", cx + s * 4.325, 6.28, "obround", 1.2, 2.0, "FB", drill=0.6, slot=(0.6, 1.7)))   # 1.2 wide as JLC's
        pads.append(Pad(f"J1.SH{s}b", "GND", cx + s * 4.325, 2.10, "obround", 1.2, 1.8, "FB", drill=0.6, slot=(0.6, 1.4)))
        NPTH.append((cx + s * 2.89, 5.79, 0.6))
    ye = yc + L / 2                     # 7.70: pad ends, the breakout starts here
    yo = 11.2
    yv = ye + 0.55                      # small vias just below the pads
    for sx in (-1, 1):
        plane_via((cx + sx * 3.2, ye), "GND", 0, 0.82)
    # VBUS: B4A9 runs to the regulator; A4B9 joins it over the top layer, round the far side of the pad row
    vb = [(cx + 2.4, ye), (cx + 2.4, 9.6), (LDO[0] - 1.9, 9.6), (LDO[0] - 1.1, 8.8), (LDO[0] - 1.1, LDO[1])]
    for (x1, y1), (x2, y2) in zip(vb, vb[1:]):
        seg(x1, y1, x2, y2, "VBUS", "B", 0.4)
    seg(cx - 2.4, ye, cx - 2.4, yv, "VBUS", "B", 0.3)
    for sx in (-1, 1):
        via(cx + sx * 2.4, yv, "VBUS", SVIA_D, SVIA_DRILL)
    tie = [(cx - 2.4, yv), (cx - 2.0, yv - 0.4), (cx - 2.0, 4.6), (cx + 2.0, 4.6), (cx + 2.0, yv - 0.4), (cx + 2.4, yv)]
    for (x1, y1), (x2, y2) in zip(tie, tie[1:]):
        seg(x1, y1, x2, y2, "VBUS", "F", 0.3)
    # CC: one 5.1k each; CC1 (A5) to the left resistor, CC2 (B5) to the right one
    seg(cx - 1.25, ye, cx - 1.25, 10.6, "CC1"); seg(cx - 1.25, 10.6, cx - 2.8, 11.4, "CC1")
    seg(cx + 1.75, ye, cx + 1.75, 10.0, "CC2"); seg(cx + 1.75, 10.0, cx + 1.5, 10.25, "CC2"); seg(cx + 1.5, 10.25, cx + 1.5, yo, "CC2")
    pads.append(smd("J1.E_CC2", "CC2", cx + 1.5, yo, 0.3, 0.3, "circle", paste=False))
    # D-: B7 + A7 joined on the bottom; D+: A6 + B6 joined on the top through two small vias, then out left
    seg(cx - 0.75, ye, cx - 0.75, 9.5, "USB_DN_C"); seg(cx + 0.25, ye, cx + 0.25, 9.5, "USB_DN_C")
    seg(cx - 0.75, 9.5, cx + 0.25, 9.5, "USB_DN_C"); seg(cx - 0.25, 9.5, cx - 0.25, yo, "USB_DN_C")
    pads.append(smd("J1.E_DN", "USB_DN_C", cx - 0.25, yo, 0.3, 0.3, "circle", paste=False))
    for dx in (-0.25, 0.75):
        seg(cx + dx, ye, cx + dx, yv, "USB_DP_C")
        via(cx + dx, yv, "USB_DP_C", SVIA_D, SVIA_DRILL)
    seg(cx + 0.75, yv, cx - 1.0, yv, "USB_DP_C", "F")
    seg(cx - 1.0, yv, cx - 1.25, yv + 0.25, "USB_DP_C", "F"); seg(cx - 1.25, yv + 0.25, cx - 1.25, yo, "USB_DP_C", "F")
    pads.append(Pad("J1.E_DP", "USB_DP_C", cx - 1.25, yo, "circle", 0.3, 0.3, "F", paste=False))
    part("J1", "TYPE-C-31-M-12", "C165948", cx, (yc + 2.10) / 2)    # JLC's origin: midway pad row / front shell pegs


LDO = (125.3 + SHIFT_X, 8.0)


def build():
    pads = []
    for lst in (DIODES, NPTH, PARTS, FIXED_SEGS, FIXED_VIAS, BUS_PADS, BUS_COPPER):
        lst.clear()
    # key matrix (switches on top, diodes underneath on the bottom)
    for r, y in enumerate(ROWS):
        for c, x in enumerate(COLS):
            n, kn = f"K{r}{c}", f"K{r}{c}_K"
            pads.append(th(n + ".A", ROW_GP[r], x - KEY_DX, y - KEY_DY, KEY_PAD, KEY_DRILL))
            pads.append(th(n + ".B", ROW_GP[r], x + KEY_DX, y - KEY_DY, KEY_PAD, KEY_DRILL))   # A/B bridged inside the switch
            pads.append(th(n + ".C", None, x - KEY_DX, y + KEY_DY, KEY_PAD, KEY_DRILL))
            pads.append(th(n + ".D", kn, x + KEY_DX, y + KEY_DY, KEY_PAD, KEY_DRILL))
            part(n, "1-1825910-4", "C589907", x, y, side="top")      # TE FSM8JH: 6x6 mm, 9.5 mm, round 3.10 mm plunger
            add_diode(pads, "D" + n, x, y, COL_GP[c], kn)
            BUS_PADS.update({n + ".A", n + ".B", "D" + n + ".A"})
        # row bus: one straight F line through the A/B pins of the row
        seg(COLS[0] - KEY_DX, y - KEY_DY, COLS[-1] + KEY_DX, y - KEY_DY, ROW_GP[r], "F", TRACE_W)
        BUS_COPPER.append(FIXED_SEGS[-1])
    for c, x in enumerate(COLS):    # column bus: straight B line through the diode anodes
        seg(x - DIO_DX, ROWS[0], x - DIO_DX, ROWS[-1], COL_GP[c], "B", TRACE_W)
        BUS_COPPER.append(FIXED_SEGS[-1])
    # encoders (GPIO order on the east side follows the direction each signal leaves in):
    # GP18-21 ALT/HDG (north, then west over the top), GP22-25 FREQ, GP26/27 + GP16/17 FMS, GP28/29 RANGE (south, west)
    add_encoder(pads, "ENC_ALTHDG", *ALTHDG, True, "GP18", "GP19", "GP20", "GP21", "ALTHDG_K", "PEC11D-4120F-S0015", "C19270361")
    add_encoder(pads, "ENC_FREQ", *FREQ, True, "GP24", "GP25", "GP22", "GP23", PUSH_GP["FREQ"], "PEC11D-4120F-S0015", "C19270361",
                push_d="GND")
    add_encoder(pads, "ENC_FMS", *FMS, True, "GP26", "GP27", "GP16", "GP17", "FMS_K", "PEC11D-4120F-S0015", "C19270361")
    add_diode(pads, "D_FMS", FMS[0], FMS[1] + 3.0, COL_GP[R4_COL["FMS"]], "FMS_K")      # under the knob
    add_diode(pads, "D_ALTHDG", ALTHDG[0], ALTHDG[1] + 3.0, COL_GP[R4_COL["ALTHDG"]], "ALTHDG_K")      # under the knob
    add_rkjxt(pads, "RANGE", *RANGE, "GP28", "GP29")
    for name, ((lx, ly), gp, colour) in LEDS.items():
        add_led(pads, name, lx, ly, gp, colour)
    # BOOT: bridge pads (QSPI_SS via R_BOOT), bridged with a small screwdriver through the case floor
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
    ft = 34.2
    fb = ft + 4.95
    fl = {1: "QSPI_SS", 2: "QSPI_SD1", 3: "QSPI_SD2", 4: "GND", 5: "QSPI_SD0", 6: "QSPI_SCLK", 7: "QSPI_SD3", 8: "3V3"}
    fp = {}
    for p in range(1, 9):
        if p <= 4:
            fp[p] = (fx + 1.905 - 1.27 * (p - 1), fb)
        else:
            fp[p] = (fx - 1.905 + 1.27 * (p - 5), ft)
        pads.append(smd(f"U2.{p}", fl[p], *fp[p], 0.6, 1.95))
    part("U2", "W25Q16JVSNIQ", "C2456211", fx, (ft + fb) / 2, 270)
    plane_via(fp[8], "3V3", 0, 2.475)           # vias inside the body
    plane_via(fp[4], "GND", 0, -2.475)

    def path(net, pts, w=0.2):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if (x1, y1) != (x2, y2):
                seg(x1, y1, x2, y2, net, "B", w)
    path("QSPI_SD0", [fp[5], fan["QSPI_SD0"]])
    for p in (6, 7):
        net = fl[p]; x, _ = fp[p]; ex, ey = fan[net]
        path(net, [fp[p], (x, ft - 1.2), (ex, ft - 1.2 - (x - ex)), (ex, ey)])
    for p, ydrop in ((3, 1.5), (2, 2.1), (1, 2.7)):
        net = fl[p]; x, _ = fp[p]; ex, ey = fan[net]
        path(net, [fp[p], (x, fb + ydrop), (ex, fb + ydrop), (ex, ey)])
    # BOOTSEL: QSPI_SS -> 1k (right here, so the long wire to the button is no stub on the chip select)
    r0603(pads, "R_BOOT", fan["QSPI_SS"][0] - 1.7, fb + 0.6, "QSPI_SS", "BOOT_SW", "1k", "C21190", vertical=True)


def add_support(pads):
    mx, my = MCU
    # regulator XC6206P332MR (SOT-23: 1 GND, 2 VOUT, 3 VIN), VIN facing the USB-C socket. On the bottom,
    # seen from the top, the pins run clockwise: 1 north-east, 2 south-east, 3 west.
    lx, ly = LDO
    pads.append(smd("U3.3", "VBUS", lx - 1.1, ly, 0.9, 0.6))
    pads.append(smd("U3.1", "GND", lx + 1.1, ly - 0.95, 0.9, 0.6))
    pads.append(smd("U3.2", "3V3", lx + 1.1, ly + 0.95, 0.9, 0.6))
    part("U3", "XC6206P332MR", "C5446", lx, ly, 90)
    plane_via((lx + 1.1, ly + 0.95), "3V3", 0, 1.05)
    a, b = r0603(pads, "C_IN", lx - 1.1, ly - 2.0, "GND", "VBUS", "1uF", "C15849", vertical=True)
    seg(b[0], b[1], lx - 1.1, ly, "VBUS", "B", 0.4)
    plane_via(a, "GND", 0, -1.0)
    a, b = r0603(pads, "C_OUT0", lx + 1.1, ly - 3.1, "3V3", "GND", "10uF", "C19702", vertical=True)
    seg(b[0], b[1], lx + 1.1, ly - 0.95, "GND", "B", 0.4)          # cap GND straight to the regulator's GND pin
    plane_via(a, "3V3", 0, -1.0); plane_via(b, "GND", 1.0, 0)
    # CC pull-downs 5.1k
    a, b = r0603(pads, "R_CC1", USB_X - 2.8, 12.2, "CC1", "GND", "5.1k", "C23186", vertical=True)
    plane_via(b, "GND", 1.0, 0)
    a, b = r0603(pads, "R_CC2", USB_X + 1.5, 12.9, "CC2", "GND", "5.1k", "C23186", vertical=True)
    plane_via(b, "GND", -1.0, 0)
    # crystal 12 MHz, 3225 4-pad (pins 1/3 crystal, 2/4 GND), right above XIN / XOUT. On the bottom the
    # footprint is mirrored; turned so the crystal pins land on XIN (bottom-left) and XO_R (top-right):
    # pin 1 top-right, then clockwise seen from the top. The crystal itself has no polarity.
    yx, yy = 122.0 + SHIFT_X, 15.6
    pads.append(smd("Y1.1", "XO_R", yx + 1.1, yy - 0.8, 1.4, 1.2))
    pads.append(smd("Y1.2", "GND", yx + 1.1, yy + 0.8, 1.4, 1.2))
    pads.append(smd("Y1.3", "XIN", yx - 1.1, yy + 0.8, 1.4, 1.2))
    pads.append(smd("Y1.4", "GND", yx - 1.1, yy - 0.8, 1.4, 1.2))
    seg(yx + 1.1, yy + 0.8, yx - 1.1, yy - 0.8, "GND", "B", 0.3)       # GND pads joined under the body
    plane_via((yx - 1.1, yy - 0.8), "GND", 0, -1.2)
    part("Y1", "ABM8-272-T3 12MHz", "C20625731", yx, yy)
    a, b = r0603(pads, "C_X1", 118.9 + SHIFT_X, 16.4, "GND", "XIN", "15pF", "C1644")
    plane_via(a, "GND", 0, 1.0)
    a, b = r0603(pads, "C_X2", 124.6 + SHIFT_X, 13.0, "GND", "XO_R", "15pF", "C1644", vertical=True)
    plane_via(a, "GND", 1.0, 0)
    r0603(pads, "R_X", 124.6 + SHIFT_X, 15.6, "XO_R", "XOUT", "1k", "C21190", vertical=True)
    # USB series resistors 27R next to the RP2040's USB pins (south side)
    r0603(pads, "R_DP", 125.6 + SHIFT_X, 33.2, "USB_DP", "USB_DP_C", "27R", "C25190", vertical=True)
    r0603(pads, "R_DM", 127.0 + SHIFT_X, 33.2, "USB_DM", "USB_DN_C", "27R", "C25190", vertical=True)
    # decoupling (works through the 3V3 / GND planes)
    for name, (cxx, cyy, d3, dg) in (("C_D0", (116.6 + SHIFT_X, 14.8, (-1.0, 0), (-1.0, 0))),
                                     ("C_D1", (127.4 + SHIFT_X, 12.8, (1.0, 0), (1.0, 0))),
                                     ("C_D2", (127.2 + SHIFT_X, 29.9, (1.0, 0), (1.0, 0))),
                                     ("C_D3", (MCU[0] - 4.5, 47.4, (-1.0, 0), (1.0, 0)))):
        a, b = r0603(pads, name, cxx, cyy, "3V3", "GND", "100nF", "C14663", vertical=True)
        plane_via(a, "3V3", *d3); plane_via(b, "GND", *dg)
    a, b = r0603(pads, "C_FL", 125.4 + SHIFT_X, 37.2, "3V3", "GND", "100nF", "C14663", vertical=True)
    plane_via(a, "3V3", 1.0, 0); plane_via(b, "GND", 1.0, 0)
    a, b = r0603(pads, "C_VIN", 115.6 + SHIFT_X, 44.0, "3V3", "GND", "1uF", "C15849", vertical=True)
    plane_via(a, "3V3", 1.0, 0); plane_via(b, "GND", 1.0, 0)
    for i, (cxx, cyy, val, lc) in enumerate(((120.0 + SHIFT_X, 44.6, "1uF", "C15849"),
                                              (121.4 + SHIFT_X, 44.6, "100nF", "C14663"),
                                              (122.8 + SHIFT_X, 44.6, "100nF", "C14663"))):
        a, b = r0603(pads, f"C_1V{i}", cxx, cyy, "1V1", "GND", val, lc, vertical=True)
        plane_via(b, "GND", 0, 1.0)


def add_matrix_lanes(pads):
    """Last mile from the matrix buses to the RP2040 fan-out ends (vias), planned by hand, all on F.

    Arrivals from the key field (top to bottom) are R0, C6, C5, R1, C4, C3, R2, C2, C1, R3, C0, R4 - the
    same order as the fan-out ends of GPIO11..0. Rows arrive on their own F lines; columns leave their
    B bus through a via into the free band between two key rows. Each net then turns into its own
    vertical lane; outer nets use the lanes nearest the chip, so nothing crosses."""
    end = {p.net: (p.x, p.y) for p in pads if re.match(r"U1\.F\d+$", p.name) and p.net in BUS_NETS}
    ex = end[ROW_GP[0]][0]
    lane = lambda k: ex - 0.6 - 0.45 * k
    xr = COLS[-1] + KEY_DX                      # right end of the row lines
    rowy = [y - KEY_DY for y in ROWS]
    bands = {6: ROWS[0] + 3.95, 5: ROWS[0] + 4.7, 4: ROWS[1] + 3.95, 3: ROWS[1] + 4.7,
             2: ROWS[2] + 6.3, 1: ROWS[2] + 7.05, 0: ROWS[3] + 3.6}   # rows 2/3: below the UNIT light

    def path(net, pts):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if (x1, y1) != (x2, y2):
                seg(x1, y1, x2, y2, net, "F", TRACE_W)
                BUS_COPPER.append(FIXED_SEGS[-1])
    arr = [(ROW_GP[0], rowy[0]), (COL_GP[6], bands[6]), (COL_GP[5], bands[5]), (ROW_GP[1], rowy[1]),
           (COL_GP[4], bands[4]), (COL_GP[3], bands[3]), (ROW_GP[2], rowy[2]), (COL_GP[2], bands[2]),
           (COL_GP[1], bands[1]), (ROW_GP[3], rowy[3]), (COL_GP[0], bands[0])]
    down = [a for a in arr if a[1] <= end[a[0]][1]]          # arrive above their fan-out end
    up = [a for a in arr if a[1] > end[a[0]][1]][::-1]       # arrive below, outermost first
    for group in (down, up):
        for k, (net, y0) in enumerate(group):
            x0 = xr if net in ROW_GP else COLS[COL_GP.index(net)] - DIO_DX
            pts = [(x0, y0)]
            pts += [(lane(k), y0)]
            pts += [(lane(k), end[net][1]), end[net]]
            path(net, pts)
    for c in range(7):                          # column bus -> band via
        x, y = COLS[c] - DIO_DX, bands[c]
        via(x, y, COL_GP[c]); BUS_COPPER.append(("via",) + FIXED_VIAS[-1])
    seg(COLS[0] - DIO_DX, ROWS[-1], COLS[0] - DIO_DX, bands[0], COL_GP[0], "B", TRACE_W)
    BUS_COPPER.append(FIXED_SEGS[-1])
    # row 4 (knob / joystick pushes): a short lane below the bottom-most fan-out end, the router does the rest
    r4 = ROW_GP[4]
    path(r4, [end[r4], (lane(-1) + 0.3, end[r4][1]), (lane(-1) + 0.3, 31.0)])


def fixed_gnd_links():
    return [], []


def holes_cut():
    return []


def keepouts():
    k = []
    for (x, y) in MOUNTS:
        k.append(("FB", "circle", (x, y, 3.6)))
    # inside the QFN fan-out square only the pre-routed fan-out may run on the bottom
    mx, my = MCU
    e = FAN_END - 0.3
    k.append(("B", "rect", (mx - FAN_END_W + 0.3, my - e, mx + e, my + e)))
    # USB-C contacts and their pre-routed breakout
    k.append(("B", "rect", (USB_X - 3.4, 5.8, USB_X + 3.4, 11.0)))
    k.append(("F", "rect", (USB_X - 1.3, 7.6, USB_X + 0.6, 11.0)))
    for (x, y, d) in NPTH:
        k.append(("FB", "circle", (x, y, d / 2 + 0.4)))
    return k
