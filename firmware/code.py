# code.py - Avionics Panel rev 1 (CircuitPython on the panel's RP2040).
# Flash the "Raspberry Pi Pico" CircuitPython build (same chip, 2 MB flash, 12 MHz crystal), then copy
# boot.py, code.py, panel.py and buttonmap.py to CIRCUITPY and replug.
# Logic: panel.py. Button numbers: buttonmap.py / BUTTONS.md. Pins: pcb/board.py.
# The Pico build drives GP25 as its status LED while booting, in safe mode and on errors; on this board
# GP25 is the FREQ outer encoder's B line, which the encoder can pull to GND. The current is limited and
# harmless, and while code.py runs the pin belongs to rotaryio. A custom board definition would avoid it.
import time

import buttonmap as BM
import keypad
import microcontroller
import pwmio
import rotaryio
import usb_hid
from panel import Panel

P = microcontroller.pin            # GPIO names work on any RP2040 build (the Pico board renames some)

# Bench test on a plain Raspberry Pi Pico: GP23, GP24, GP25 and GP29 are not on its header. With
# PICO_TEST the FREQ knob moves to GP12/13 (outer) and GP14/15 (inner), its push to GP22, the SHIFT light
# to the onboard LED (GP25), the UNIT light is printed instead, and the RANGE turn is left out. Keys,
# RANGE tilt / push (matrix row GP0), ALT/HDG and FMS use their real pins.
PICO_TEST = False

ROW_PINS = (P.GPIO11, P.GPIO8, P.GPIO5, P.GPIO2, P.GPIO0)
COL_PINS = (P.GPIO1, P.GPIO3, P.GPIO4, P.GPIO6, P.GPIO7, P.GPIO9, P.GPIO10)
FREQ_PUSH = P.GPIO13               # direct input, switch to GND
SHIFT_LED, UNIT_LED = P.GPIO12, P.GPIO15
LED_DUTY = (0x6000, 0x3000)        # SHIFT (amber), UNIT (white) brightness, 0..0xFFFF
# SHIFT light duty per panel level (off, dim, full). Dim starts at 1/4 of full: the eye is not linear, so it
# looks like about half the brightness, a clear pulse that should stay visible through the light pipe in
# daylight. Tune it on the first board with the amber LED behind its pipe: in PICO_TEST the SHIFT light is
# the Pico's green onboard LED, which says nothing about the real one.
SHIFT_DUTY = (0, LED_DUTY[0] // 4, LED_DUTY[0])

# (ring, pin A, pin B, reverse). Ring 1 of a dual encoder = pins A/B/C, ring 2 = A'/B'/C'. If outer and
# inner are swapped on the first board, swap the two ring names; if a direction is wrong, flip reverse.
RINGS = (
    ("ALTHDG_OUTER", P.GPIO18, P.GPIO19, False), ("ALTHDG_INNER", P.GPIO20, P.GPIO21, False),
    ("FREQ_OUTER", P.GPIO24, P.GPIO25, False), ("FREQ_INNER", P.GPIO22, P.GPIO23, False),
    ("FMS_OUTER", P.GPIO26, P.GPIO27, False), ("FMS_INNER", P.GPIO16, P.GPIO17, False),
    ("RANGE", P.GPIO28, P.GPIO29, False),
)
if PICO_TEST:
    RINGS = tuple(r for r in RINGS if r[0] not in ("FREQ_OUTER", "FREQ_INNER", "RANGE")) + (
        ("FREQ_OUTER", P.GPIO12, P.GPIO13, False), ("FREQ_INNER", P.GPIO14, P.GPIO15, False))
    FREQ_PUSH, SHIFT_LED, UNIT_LED = P.GPIO22, P.GPIO25, None

devices = [d for d in usb_hid.devices if d.usage_page == 0x01 and d.usage == 0x04]
if len(devices) < 2:
    raise RuntimeError("joysticks missing: copy boot.py and replug the panel")

matrix = keypad.KeyMatrix(ROW_PINS, COL_PINS, columns_to_anodes=True)   # diode anodes on the columns
direct = keypad.Keys((FREQ_PUSH,), value_when_pressed=False, pull=True)
encoders = [rotaryio.IncrementalEncoder(a, b, divisor=2) for _, a, b, _ in RINGS]   # 30 detents / 15 pulses
last = [e.position for e in encoders]
leds = [pwmio.PWMOut(SHIFT_LED, frequency=1000), pwmio.PWMOut(UNIT_LED, frequency=1000) if UNIT_LED else None]
unit_shown = None
shift_shown = None
NAMES = [n for row in BM.MATRIX for n in row]
panel = Panel()
reports = {1: bytearray(BM.SIZE[1] // 8), 2: bytearray(BM.SIZE[2] // 8)}
sent = {1: None, 2: None}
print("Avionics Panel rev 1 ready")

while True:
    t = time.monotonic_ns() // 1_000_000
    ev = matrix.events.get()
    while ev:
        panel.key(NAMES[ev.key_number], ev.pressed, t)
        ev = matrix.events.get()
    ev = direct.events.get()
    while ev:
        panel.key("FREQ_PUSH", ev.pressed, t)
        ev = direct.events.get()
    for i, enc in enumerate(encoders):
        pos = enc.position
        if pos != last[i]:
            d = pos - last[i]
            last[i] = pos
            panel.turn(RINGS[i][0], -d if RINGS[i][3] else d, t)
    panel.tick(t)
    level = panel.shift_level(t)                                     # pulses before SHIFT drops
    if level != shift_shown:                                         # only writes on a change
        shift_shown = level
        leds[0].duty_cycle = SHIFT_DUTY[level]
    if leds[1]:
        leds[1].duty_cycle = LED_DUTY[1] if panel.unit_light else 0
    elif panel.unit_light != unit_shown:
        unit_shown = panel.unit_light
        print("UNIT", 2 if unit_shown else 1)
    for n, dev in ((1, devices[0]), (2, devices[1])):
        rep = reports[n]
        for k in range(len(rep)):
            rep[k] = 0
        for b in panel.buttons(n):
            rep[b >> 3] |= 1 << (b & 7)
        if rep != sent[n]:
            try:                                 # host not ready (PC booting, asleep, charger only): retry next loop
                dev.send_report(rep)
                sent[n] = bytes(rep)
            except OSError:
                pass
    time.sleep(0.001)
