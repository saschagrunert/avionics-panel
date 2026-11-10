"""Button map of the Avionics Panel rev 1: names -> joystick button numbers on the two USB devices.

Plain Python (runs in CircuitPython and on the PC). `python3 make_buttons.py > BUTTONS.md` (PC only) writes
the table for setting up MobiFlight. Numbers here are 0-based; Windows and MobiFlight show them +1.

Device 1 carries everything that is not tied to a unit, plus unit 1. Device 2 carries the unit 2
copies of the unit controls (FMS keys and knob, CDI / OBS, flip-flops, frequency knob).
"""

# physical key matrix (rows GP11, GP8, GP5, GP2, GP0 x columns GP1, GP3, GP4, GP6, GP7, GP9, GP10)
MATRIX = (
    ("AP", "ALT", "HDG", "MIC1", "COM1", "CDI", "COM_SWAP"),
    ("FD", "VS", "NAV", "MIC2", "COM2", "VFR", "NAV_SWAP"),
    ("UP", "FLC", "APR", "HOME", "FPL", "DIRECT", "MENU"),
    ("DN", "VNV", "LVL", "SHIFT", "PROC", "CLR", "ENT"),
    ("RANGE_A", "RANGE_B", "RANGE_C", "RANGE_D", "RANGE_COM", "ALTHDG_PUSH", "FMS_PUSH"),
)

# amber (SHIFT) legends; keys without one send "S_<name>". HOME + SHIFT is UNIT (firmware state, no button).
SHIFTED = {
    "AP": "TEST", "ALT": "ARM", "HDG": "CRS_CTR", "FD": "YD", "NAV": "GPSS", "APR": "BC", "LVL": "HALF_BANK",
    "MIC1": "ADF_AUDIO", "COM1": "NAV1_AUDIO", "MIC2": "DME_AUDIO", "COM2": "NAV2_AUDIO",
    "CDI": "OBS", "COM_SWAP": "COM_121_5", "VFR": "IDENT", "NAV_SWAP": "ADF_SWAP",
    "FPL": "VNAV", "DIRECT": "MSG", "MENU": "NRST", "PROC": "TERR", "CLR": "MAP",
}
UNIT_KEYS = ("CDI", "COM_SWAP", "NAV_SWAP", "HOME", "FPL", "DIRECT", "MENU", "PROC", "CLR", "ENT")
REPEAT_KEYS = ("UP", "DN")
PLAIN_KEYS = ("AP", "ALT", "HDG", "FD", "VS", "NAV", "UP", "FLC", "APR", "DN", "VNV", "LVL",
              "MIC1", "COM1", "MIC2", "COM2", "VFR")


def shifted(name):
    return SHIFTED.get(name, "S_" + name)


def _turn(base, fast=None):
    """Turn buttons of one knob function: slow step, plus the fast (coarse) step if it accelerates."""
    out = [base + "_UP", base + "_DN"]
    if fast:
        out += [fast + "_UP", fast + "_DN"]
    return out


# Device 1 buttons that do not belong to a unit, in a fixed order: the order is the button number. Frozen
# from the first build on: new buttons go at the end of a device (see LIGHTING), retired ones keep their
# slot, and a key whose plain and shifted functions trade places keeps the numbers of its functions.
# Joined with +, not *-unpacking: MicroPython (and so CircuitPython) has no * inside a list literal.
DEVICE1_ONLY = (
    # plain keys (PLAIN_KEYS), then their shifted functions in the same order
    ["AP", "ALT", "HDG", "FD", "VS", "NAV", "UP", "FLC", "APR", "DN", "VNV", "LVL", "MIC1", "COM1", "MIC2", "COM2",
     "VFR",
     "TEST", "ARM", "CRS_CTR", "YD", "S_VS", "GPSS", "S_UP", "S_FLC", "BC", "S_DN", "S_VNV", "HALF_BANK",
     "ADF_AUDIO", "NAV1_AUDIO", "DME_AUDIO", "NAV2_AUDIO", "IDENT"]
    # ALT / HDG knob; with SHIFT: CRS / BARO, push STD
    + _turn("ALT_100", "ALT_1000") + _turn("HDG_1", "HDG_10") + ["HDG_SYNC"]
    + _turn("CRS_1", "CRS_10") + _turn("BARO") + ["BARO_STD"]
    # RANGE: turn, tilt (pan), push (pointer); shifted copies are free for own mappings
    + ["RANGE_CW", "RANGE_CCW", "PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT", "PTR",
       "S_RANGE_CW", "S_RANGE_CCW", "S_PAN_UP", "S_PAN_DN", "S_PAN_LEFT", "S_PAN_RIGHT", "S_PTR"]
    # frequency knob with SHIFT: squawk (octal). Outer ring: digits 1-2, inner ring: digits 3-4.
    # Slow turn = the second digit of the pair, fast turn = the first.
    + _turn("SQK_D2", "SQK_D1") + _turn("SQK_D4", "SQK_D3") + ["XPDR_MODE"]
)
# FMS knob with SHIFT: cockpit lighting, the same in every unit, so on device 1 only. Outer ring: panel /
# instrument lights, inner ring: glareshield flood, push: cabin (dome) light. One step per detent; the
# profile sets the step size.
LIGHTING = _turn("PANEL_LT") + _turn("FLOOD_LT") + ["CABIN_LT"]


def _unit():
    keys = list(UNIT_KEYS) + [shifted(k) for k in UNIT_KEYS if k != "HOME"]
    fms = ["FMS_OUTER_CW", "FMS_OUTER_CCW", "FMS_INNER_CW", "FMS_INNER_CCW", "FMS_CRSR"]   # SHIFT: LIGHTING
    freq = _turn("COM_MHZ") + _turn("COM_KHZ") + _turn("NAV_MHZ") + _turn("NAV_KHZ")
    freq += _turn("ADF_100") + _turn("ADF_1", "ADF_10") + ["FREQ_PUSH"]
    return keys + fms + freq


UNIT_NAMES = _unit()
# Button numbers are frozen from the first build on (see DEVICE1_ONLY), so MobiFlight mappings keep working;
# test_panel.py holds a snapshot.
DEVICE = {1: DEVICE1_ONLY + UNIT_NAMES + LIGHTING, 2: list(UNIT_NAMES)}
BUTTON = {dev: {n: i for i, n in enumerate(names)} for dev, names in DEVICE.items()}
SIZE = {1: 128, 2: 64}                     # buttons per device (report: SIZE / 8 bytes)
assert len(DEVICE[1]) <= SIZE[1] and len(DEVICE[2]) <= SIZE[2]
assert all(len(set(n)) == len(n) for n in DEVICE.values()), "duplicate button name"
# every function a plain key, its SHIFT and the device-1 knobs send has a button
assert all(n in DEVICE1_ONLY for k in PLAIN_KEYS for n in (k, shifted(k))), "plain key without a button"

