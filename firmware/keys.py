"""Keyboard mode of the Avionics Panel rev 1: plain Python (runs in CircuitPython and on the PC).

In keyboard mode the panel is one USB keyboard instead of the two joysticks, for consoles and for MSFS without
MobiFlight: the joystick buttons of buttonmap.py send shortcuts instead, bound once in the sim's controls menu.
boot.py keeps the mode and sets up USB with what is here, code.py sends the report Keyboard builds.
`python3 make_keys.py > KEYS.md` (PC only) writes the binding table. See docs/using/keyboard.md.
"""
import buttonmap as BM

# The mode lives in microcontroller.nvm (flash: it survives power cycles and firmware updates). This byte holds
# KEYBOARD in keyboard mode; anything else, the 0xFF of a blank flash included, is the joystick mode, the
# default. boot.py switches it while HOME (amber legend UNIT) is held alone at plug-in.
MODE_BYTE, KEYBOARD, JOYSTICK = 0, 0x4B, 0xFF


def keyboard_mode(nvm, toggle=False):
    """Whether the panel runs in keyboard mode; toggle switches the stored mode first"""
    on = nvm[MODE_BYTE] == KEYBOARD
    if toggle:
        on = not on
        nvm[MODE_BYTE] = KEYBOARD if on else JOYSTICK
    return on


# The start pattern of keyboard mode: the lights take turns (0 SHIFT, 1 UNIT), BLINK_S each. In joystick mode
# they stay dark.
START, BLINK_S = (0, 1, 0, 1, 0, 1), 0.15

REPORT = 8                         # bytes: modifiers, reserved, six keys (the panel uses one), as a boot keyboard
# One keyboard without report ID: HID 1.11's boot keyboard descriptor (appendix E.6), keys 0 to 101. A host that
# switches to the boot protocol (usb_hid.enable(boot_device=1)) reads the same 8 bytes.
DESCRIPTOR = bytes((
    0x05, 0x01,                    # Usage Page (Generic Desktop)
    0x09, 0x06,                    # Usage (Keyboard)
    0xA1, 0x01,                    # Collection (Application)
    0x05, 0x07,                    #   Usage Page (Keyboard/Keypad)
    0x19, 0xE0, 0x29, 0xE7,        #   Usage Minimum (Left Control), Maximum (Right GUI)
    0x15, 0x00, 0x25, 0x01,        #   Logical Minimum (0), Maximum (1)
    0x75, 0x01, 0x95, 0x08,        #   Report Size (1), Count (8)
    0x81, 0x02,                    #   Input (Data, Var, Abs): the modifiers
    0x95, 0x01, 0x75, 0x08,        #   Report Count (1), Size (8)
    0x81, 0x01,                    #   Input (Const): reserved
    0x95, 0x05, 0x75, 0x01,        #   Report Count (5), Size (1)
    0x05, 0x08,                    #   Usage Page (LEDs)
    0x19, 0x01, 0x29, 0x05,        #   Usage Minimum (Num Lock), Maximum (Kana)
    0x91, 0x02,                    #   Output (Data, Var, Abs): the host's LEDs, unused
    0x95, 0x01, 0x75, 0x03,        #   Report Count (1), Size (3)
    0x91, 0x01,                    #   Output (Const)
    0x95, 0x06, 0x75, 0x08,        #   Report Count (6), Size (8)
    0x15, 0x00, 0x25, 0x65,        #   Logical Minimum (0), Maximum (101)
    0x05, 0x07,                    #   Usage Page (Keyboard/Keypad)
    0x19, 0x00, 0x29, 0x65,        #   Usage Minimum (0), Maximum (101)
    0x81, 0x00,                    #   Input (Data, Array, Abs): the keys
    0xC0,                          # End Collection
))

# The shortcuts: F1 to F12 and navigation keys (HID usage IDs, Keyboard/Keypad page), which mean the same on every
# layout and are in the boot keyboard's range, with Ctrl, Shift and Alt as the report's bits. MSFS is reported to
# keep left and right Ctrl and Shift apart, and its default bindings use the left ones, so the right ones open room
# that no default takes. Never right Alt (AltGr on many layouts; a sim window in MSFS 2024) or the Windows key.
LC, LS, LA, RC, RS = 0x01, 0x02, 0x04, 0x10, 0x20
F_KEYS = bytes(range(0x3A, 0x46))  # F1 to F12
F4, F5, F6, F10 = 0x3D, 0x3E, 0x3F, 0x43
NAV = bytes((0x49, 0x4A, 0x4B, 0x4E))      # Insert, Home, Page Up, Page Down
ARROWS = bytes((0x4F, 0x50, 0x51, 0x52))   # right, left, down, up


def without(keys, *left_out):
    return bytes(k for k in keys if k not in left_out)


# (modifiers, keys) in the order the functions take them. Left out: what MSFS 2024's default presets bind (left
# Ctrl alone with an F-key or a navigation key: autopilot; left Shift alone with F1 to F11: cameras; left
# Shift+Alt: head tracking pause), Shift with a navigation key or arrow, which MSFS may take for the keypad key in
# its place, Delete and End, which erase and reset in its menus, and Windows', drivers' and overlays' shortcuts:
# Ctrl+Alt with an F-key (Intel; on Linux it switches the console) and those noted below. MSFS is reported to fire
# a binding of a shortcut's parts when the shortcut itself is not bound, so the shortcuts whose parts do nothing
# in flight come first: navigation keys alone are menu keys, arrows alone turn the view; F-keys alone are
# throttle, propeller and mixture, with left Shift cameras, with left Ctrl autopilot modes (last).
GROUPS = (
    (RC, NAV), (LA, NAV), (RC | LA, NAV),
    (RC, ARROWS), (LA, ARROWS), (LC, ARROWS[:2]),               # Ctrl+Alt+arrows turn the screen (AMD)
    (RC, without(F_KEYS, F4)),                                  # Ctrl+F4 closes tabs and documents
    (RS, without(F_KEYS, F10)),                                 # Shift+F10 opens the context menu
    (RC | RS, F_KEYS),
    (RS | LA, without(F_KEYS, F4, F10)),                        # Shift+Alt+F4 closes, Alt+Shift+F10: NVIDIA
    (RC | RS | LA, F_KEYS),
    (LA, bytes((F5, F6))),                                      # Alt+F1-F4, F7-F12: Windows and overlays
    (RC | LS, F_KEYS),
    (LC | RS, F_KEYS), (LC | RS | LA, F_KEYS),
    (LC | LS, F_KEYS[4:]),                                      # Ctrl+Shift+F1-F4: mixture in 2020's presets
)
COMBOS = b"".join(bytes(b for k in keys for b in (mods, k)) for mods, keys in GROUPS)   # (modifiers, key) pairs
# The functions that take the first shortcuts, those of navigation keys and arrows: the ones the sim's controls
# may well have nothing for (so their shortcuts stay unbound), knob detents and repeated steps first
FIRST = ("FREQ_PUSH", "PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT", "PTR", "PANEL_LT_UP", "PANEL_LT_DN",
         "FLOOD_LT_UP", "FLOOD_LT_DN", "HDG_SYNC", "XPDR_MODE", "COM_121_5", "TEST", "ARM", "CRS_CTR", "GPSS",
         "HALF_BANK", "VFR", "HOME", "OBS", "MAP")
UNIT2 = 112                        # unit 2's own shortcuts from this place on: room for 8 more of device 1 before it


def _index():
    """The place in COMBOS of each button's shortcut, by device and button. SHIFT with a key that has no amber
    legend sends the key's plain shortcut (map both alike: docs/using/mapping.md). In unit 2 only COM and NAV
    (frequencies, flip-flops) have shortcuts of their own, the rest sends unit 1's: the sim's controls hold one
    set of FMS keys (the G1000 MFD's), and most aircraft have one ADF."""
    out, n = {1: bytearray(len(BM.DEVICE[1])), 2: bytearray(len(BM.DEVICE[2]))}, 0
    for name in FIRST:
        out[1][BM.BUTTON[1][name]], n = n, n + 1
    for b, name in enumerate(BM.DEVICE[1]):
        if name not in FIRST and not name.startswith("S_"):
            out[1][b], n = n, n + 1
    assert n <= UNIT2
    for b, name in enumerate(BM.DEVICE[1]):
        if name.startswith("S_"):
            out[1][b] = out[1][BM.BUTTON[1][name[2:]]]
    n = UNIT2
    for b, name in enumerate(BM.DEVICE[2]):
        if (name.startswith("COM_") or name.startswith("NAV_")) and name != "COM_121_5":   # (no tuple: MicroPython)
            out[2][b], n = n, n + 1
        else:
            out[2][b] = out[1][BM.BUTTON[1][name[2:] if name.startswith("S_") else name]]
    assert 2 * n <= len(COMBOS)
    return out


INDEX = _index()


def shortcut(dev, button):
    """(modifiers, key) a joystick button's function sends"""
    i = 2 * INDEX[dev][button]
    return COMBOS[i], COMBOS[i + 1]


class Keyboard:
    """The keyboard report of the function a solo Panel presses. Its modifiers go down a report before its key
    and come up a report after it: the host sees the key with its own modifiers only, also when another function
    follows at once (whose modifiers then replace them in a report of their own)."""

    def __init__(self, panel):
        self.panel, self.fn, self.at, self.key = panel, None, None, False

    def fill(self, report):
        """The report for this loop pass, in place (bytes 0 and 2; the others stay 0): one step per pass, and
        nothing allocated"""
        down = self.panel.pressed()
        if down != self.fn:
            if self.key:
                self.key = False                   # the key goes up, its modifiers stay for this report
            else:                                  # then the next function's modifiers, or none
                self.fn, self.at = down, None if down is None else 2 * INDEX[down[0]][down[1]]
        elif down is not None:
            self.key = True                        # its modifiers went out with the last report: now its key
        report[0] = 0 if self.at is None else COMBOS[self.at]
        report[2] = COMBOS[self.at + 1] if self.key else 0
