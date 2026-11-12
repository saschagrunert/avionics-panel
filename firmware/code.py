# code.py - Avionics Panel rev 1 (CircuitPython on the panel's RP2040).
# Flash the CircuitPython 9.2.9 "Raspberry Pi Pico" build (docs/building/bring-up.md, Flash and test, step 3; same
# chip, 2 MB flash, 12 MHz crystal), then copy boot.py, code.py, panel.py, buttonmap.py and keys.py to CIRCUITPY and
# replug.
# From then on boot.py hides CIRCUITPY and the serial console unless SHIFT is held from plugging in until
# CIRCUITPY appears (about 2 s; boot.py runs up to 1 s after power-up, docs/building/bring-up.md).
# Logic: panel.py. Button numbers: buttonmap.py / BUTTONS.md. Pins: pcb/board.py.
# The Pico build drives GP25 as its status LED, push-pull at 12 mA: high in blinks in the first second after
# power-up, after code.py stops with an error and in safe mode. On this board GP25 is the FREQ outer encoder's B
# line, which the encoder can close to GND: the 1 k resistor in series on the board limits that to 3.3 mA, and
# boot.py turns the LED's brightness to 0, so after boot.py its blinks drive the pin low (high only for an instant
# as each starts). While code.py runs the pin belongs to rotaryio.
import time
import traceback

import keypad
import microcontroller
import pwmio
import rotaryio
import supervisor
import usb_hid

try:                               # the pads' drive strength (drive_12ma below); a build without it still runs
    import memorymap
except ImportError:
    memorymap = None

P = microcontroller.pin            # GPIO names work on any RP2040 build (the Pico board renames some)

# Bench test on a plain Raspberry Pi Pico: GP23, GP24, GP25 and GP29 are not on its header. With
# PICO_TEST the FREQ knob moves to GP12/13 (outer) and GP14/15 (inner), its push to GP22, the SHIFT light
# to the onboard LED (GP25) and the UNIT light is printed instead. Keys, RANGE tilt / push (matrix row GP0),
# ALT/HDG and FMS use their real pins. The RANGE encoder stays on GP28/GP29, so the bench still runs all 7
# PIO encoders; it can't be turned there: GP29 is the Pico's VSYS / 3 divider, not on the header (about
# 1.6 V through 67 k; with rotaryio's pull-up about 2.4 V, a steady high, so it counts nothing).
PICO_TEST = False

# The keypad drives one row low at a time; CircuitPython sets a pad to 12 mA whenever it makes it an output, so
# the rows drive 12 mA and a held key reads a diode drop above GND, also with all keys of its row held.
ROW_PINS = (P.GPIO11, P.GPIO8, P.GPIO5, P.GPIO2, P.GPIO0)
COL_PINS = (P.GPIO1, P.GPIO3, P.GPIO4, P.GPIO6, P.GPIO7, P.GPIO9, P.GPIO10)
FREQ_PUSH = P.GPIO13               # direct input, switch to GND
SHIFT_LED, UNIT_LED = P.GPIO12, P.GPIO15
LED_GPIOS = (12, 15)               # their GPIO numbers: both pads drive 12 mA (drive_12ma below); GP15 only
                                   # drives Q_UNIT's gate, so its strength does not matter
# SHIFT (amber), UNIT (white) brightness, 0..0xFFFF. At full duty the amber LED takes about 13.5 mA from GP12
# through 75 R, its pad at 12 mA drive. The white one runs from VBUS_F through 390 R and Q_UNIT, a 2N7002 that GP15
# switches: about 5 mA, whatever its forward voltage bin. These duties, about 28 and 33 % of full, leave three to
# three and a half times that up to full duty for tuning on the first board (docs/architecture/electronics.md).
LED_DUTY = (0x4800, 0x5500)
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
    RINGS = tuple(r for r in RINGS if r[0] not in ("FREQ_OUTER", "FREQ_INNER")) + (
        ("FREQ_OUTER", P.GPIO12, P.GPIO13, False), ("FREQ_INNER", P.GPIO14, P.GPIO15, False))
    FREQ_PUSH, SHIFT_LED, UNIT_LED = P.GPIO22, P.GPIO25, None

PADS_BANK0 = 0x4001C000            # RP2040 pad control: one 32-bit register per GPIO, from offset 4
DRIVE_12MA = 0x30                  # its DRIVE field, bits 5:4: 3 is 12 mA (reset 1, 4 mA)
RETRY_MS, RETRY_MAX_MS = 1000, 8000      # after a failed send: wait before the next try, doubling up to this
WAKE_MS = 500                            # wait this long for a host asked to resume the bus: USB 2.0 needs 30 ms
                                         # (7.1.7.7), Linux holds the resume 40 ms, a sleeping host controller more
TICKS_PERIOD = 1 << 29                   # supervisor.ticks_ms and Event.timestamp wrap after this many ms
OUTPUTS = ()                             # (report, device) once code.py has found them: 0 the keyboard, 1 and 2
                                         # the joysticks


def drive_12ma(gpio):
    """The pad's drive strength to 12 mA, so the series resistor, not the pad, sets the LED current. CircuitPython
    has no call for it: memorymap writes the RP2040's pad register (32-bit, read, modify, write). After PWMOut, which
    leaves the drive field alone. If it fails the SHIFT light stays at the 4 mA drive, dimmer; GP15 only switches
    Q_UNIT's gate (docs/architecture/firmware.md)."""
    if memorymap is None:
        print("LED drive strength not set: no memorymap in this build")
        return
    try:
        reg = memorymap.AddressRange(start=PADS_BANK0 + 4 + 4 * gpio, length=4)
        reg[0:4] = (int.from_bytes(reg[0:4], "little") | DRIVE_12MA).to_bytes(4, "little")
    except (ValueError, RuntimeError, OSError) as e:
        print("LED drive strength not set on GP", gpio, e)


def ticks_diff(a, b):
    """a - b in ms for two supervisor.ticks_ms values less than TICKS_PERIOD / 2 apart, across a wrap"""
    return ((a - b + TICKS_PERIOD // 2) & (TICKS_PERIOD - 1)) - TICKS_PERIOD // 2


def back_off(r):
    """r: [no try before this ms, the last wait]: the next try waits RETRY_MS from now, then twice as long each time,
    up to RETRY_MAX_MS. From now: the try that failed took 2 s."""
    wait = min(2 * r[1], RETRY_MAX_MS) if r[1] else RETRY_MS
    r[0], r[1] = time.monotonic_ns() // 1_000_000 + wait, wait


class Source:
    """One keypad: passes its events to the panel and recovers from lost ones. After an overflow the keypad
    is reset and reports every key still held as a fresh press. A key the panel already has down keeps its
    press (no release and second press for the PC, which would toggle AP off again); a key it has down but
    that is not reported again within RESYNC_MS lost its release, and only that one is released, at once (no
    bounce: a real press right after it is a new press)."""

    def __init__(self, keys, names):
        self.keys, self.names = keys, names
        self.down = set()          # key numbers the panel has as pressed
        self.resync = None         # after an overflow: (end ms, key numbers reported again)

    def poll(self, t, ticks):
        """t: the pass's ms, ticks: supervisor.ticks_ms() read with it, to put the scan times on t's clock"""
        if self.keys.events.overflowed:
            self.keys.events.clear()
            self.keys.reset()
            self.resync = (t + RESYNC_MS, set())
        ev = self.keys.events.get()
        while ev:
            k = ev.key_number
            at = t + ticks_diff(ev.timestamp, ticks)
            if not ev.pressed:
                if k in self.down:                   # a key held when the keypad started sends a release only
                    self.down.discard(k)
                    panel.key(self.names[k], False, t, at)
            elif self.resync and k in self.down:
                self.resync[1].add(k)
            else:
                self.down.add(k)
                panel.key(self.names[k], True, t, at)
            ev = self.keys.events.get()
        if self.resync and t >= self.resync[0]:
            for k in [k for k in self.down if k not in self.resync[1]]:
                self.down.discard(k)
                panel.release(self.names[k], t)
            self.resync = None


def release_all():
    """All buttons (or keys) up on every device: the host keeps the last report, also after code.py has stopped."""
    if not supervisor.runtime.usb_connected:
        return
    for n, dev in OUTPUTS:
        try:                                     # noqa: SIM105 (CircuitPython has no contextlib)
            dev.send_report(ZERO[n])
        except OSError:
            pass


def input_waiting():
    """Whether a keypad has events or a ring has turned that the loop has not read yet"""
    for src in sources:
        if src.keys.events:
            return True
    for i in range(len(RINGS)):                  # noqa: SIM110 (any() would allocate a generator)
        if encoders[i].position != last[i]:
            return True
    return False


def wake():
    """Input while USB is down: asks a host that has suspended the bus to resume it, so the input reaches the PC.
    CircuitPython has no call for it: send_report waits 2 s for the host, then asks a suspended one to resume and
    returns (remote wakeup, which a host enables before it suspends an idle device; a sleeping PC decides itself
    whether the panel may wake it); with no host at all it raises OSError. The input then waits until the host is
    back, up to WAKE_MS, so that a press still lasts its PRESS_MS for the PC. A request that brings no host back
    is not repeated before a back-off, as for a failed send; the loop ends the back-off once the host is back,
    whether this request or the host itself brought it back."""
    n, dev = OUTPUTS[0]                          # joystick 1, or the keyboard
    try:                                         # noqa: SIM105 (CircuitPython has no contextlib)
        dev.send_report(reports[n])              # the last pass's: goes out if the host is back within the 2 s
    except OSError:
        pass
    end = time.monotonic_ns() // 1_000_000 + WAKE_MS
    while not supervisor.runtime.usb_connected and time.monotonic_ns() // 1_000_000 < end:
        time.sleep(0.001)
    if not supervisor.runtime.usb_connected:
        back_off(woke)


# Anything that raises, while code.py starts (a file it imports, the devices boot.py makes, the pins) or in the
# loop, must not leave a button held on the PC, nor leave the panel dead until it is replugged: release
# everything, then restart code.py (a reload keeps USB up, boot.py does not run again). The traceback comes after
# the release and may fail on its own (a MemoryError leaves little room to format it): neither may keep the panel
# from reloading. The pause before it lets Ctrl-C on the serial console (SHIFT held at plug-in) stop the loop and
# reach the REPL; an error that a reload cannot fix ("joysticks missing" or "keyboard missing" before boot.py has
# run) shows again every 2 s. No watchdog: every wait in the loop is bounded (send_report gives up after 2 s),
# and a watchdog reset is a hard reset that drops the devices off USB and runs boot.py again, which would also
# hide the drive in the middle of an update.
try:
    import buttonmap as BM
    from panel import KEY_SCAN_MS, LIGHT_OFF, Panel

    # keyboard mode (keys.py): boot.py made one keyboard instead of the joysticks. keys.py's mode byte, read here,
    # so that keys.py is imported in keyboard mode only and the joysticks keep its RAM (test_code.py checks they
    # agree)
    KEYBOARD = microcontroller.nvm[0] == 0x4B
    devices = [d for d in usb_hid.devices if d.usage_page == 0x01 and d.usage == (0x06 if KEYBOARD else 0x04)]
    if len(devices) < (1 if KEYBOARD else 2):
        raise RuntimeError(("keyboard" if KEYBOARD else "joysticks") + " missing: copy boot.py and replug the panel")
    ZERO = {1: bytes(BM.SIZE[1] // 8), 2: bytes(BM.SIZE[2] // 8)}   # made now: release_all may run out of memory
    reports = {1: bytearray(BM.SIZE[1] // 8), 2: bytearray(BM.SIZE[2] // 8)}
    if KEYBOARD:                         # report 0: the keyboard's, filled by keys.Keyboard
        import keys
        ZERO[0], reports[0] = bytes(keys.REPORT), bytearray(keys.REPORT)
    # made once: the loop and release_all allocate nothing for them
    OUTPUTS = ((0, devices[0]),) if KEYBOARD else ((1, devices[0]), (2, devices[1]))

    # Both keypads scan every KEY_SCAN s (panel.KEY_SCAN_MS: the panel's bounce window follows it), and RESYNC_MS
    # below follows it too. debounce_threshold stays at its default (1), so a press reaches the PC on the first
    # scan that reads it, and reset() reports the keys still held at once, from a scan of its own; a higher
    # threshold delays both by one scan per step (RESYNC_MS would have to grow with it). A bounce longer than a
    # scan is caught in panel.py, by the scan times of the events (Event.timestamp, on the supervisor.ticks_ms
    # clock).
    KEY_SCAN = KEY_SCAN_MS / 1000
    matrix = keypad.KeyMatrix(ROW_PINS, COL_PINS, columns_to_anodes=True, interval=KEY_SCAN)   # anodes on columns
    direct = keypad.Keys((FREQ_PUSH,), value_when_pressed=False, pull=True, interval=KEY_SCAN)
    encoders = [rotaryio.IncrementalEncoder(a, b, divisor=2) for _, a, b, _ in RINGS]   # 30 detents / 15 pulses
    last = [e.position for e in encoders]
    leds = [pwmio.PWMOut(SHIFT_LED, frequency=1000),
            pwmio.PWMOut(UNIT_LED, frequency=1000) if UNIT_LED else None]
    if not PICO_TEST:              # the Pico's onboard LED has a resistor of its own
        for gp in LED_GPIOS:
            drive_12ma(gp)
    unit_shown = None
    shift_shown = None
    panel = Panel(solo=KEYBOARD)         # keyboard mode: one shortcut at a time (keys.py)
    if KEYBOARD:
        keyboard = keys.Keyboard(panel)
    RESYNC_MS = 3 * KEY_SCAN_MS          # three scans, to spare: reset() reports the keys still held at once

    # each keypad on its own: an overflow on one leaves the keys held on the other alone
    sources = (Source(matrix, [n for row in BM.MATRIX for n in row]), Source(direct, ["FREQ_PUSH"]))
    sent = {0: None, 1: None, 2: None}
    # [no send before this ms, current back-off ms], one for both devices: they share one USB HID interface, and
    # send_report waits for that interface, so a host that doesn't poll fails both alike
    retry = [0, 0]
    woke = [0, 0]                        # the same for asking a suspended host to resume (wake)

    print("Avionics Panel rev 1 ready")
    if KEYBOARD:                   # the lights take turns at each start (keys.START), also with USB down; the loop
        for on in keys.START:      # then sets them, dark while USB is down
            for i in (0, 1):
                if leds[i]:
                    leds[i].duty_cycle = LED_DUTY[i] if i == on else 0
            time.sleep(keys.BLINK_S)
    while True:
        t = time.monotonic_ns() // 1_000_000
        if t >= woke[0] and not supervisor.runtime.usb_connected and input_waiting():
            # wake() takes 2 s or more and the input is read after it. The knobs as they stood before it go to the
            # panel first, at this pass's time, so a detent turned before a key pressed during the wait comes first
            # (a list only on this path: the loop allocates nothing otherwise)
            before = [e.position for e in encoders]
            wake()
            for i in range(len(RINGS)):
                d = before[i] - last[i]
                if d:
                    last[i] = before[i]
                    panel.turn(RINGS[i][0], -d if RINGS[i][3] else d, t)
            t = time.monotonic_ns() // 1_000_000
        ticks = supervisor.ticks_ms()
        for src in sources:
            src.poll(t, ticks)
        for i in range(len(RINGS)):                  # no enumerate(): it allocates in every pass
            pos = encoders[i].position
            if pos != last[i]:
                d = pos - last[i]
                last[i] = pos
                panel.turn(RINGS[i][0], -d if RINGS[i][3] else d, t)
        panel.tick(t)
        # USB connected: mounted and not suspended. The lights stay dark while it is not (the PC asleep, booting or
        # off, a charger) and show the panel's state again once it is; the panel itself runs on.
        connected = supervisor.runtime.usb_connected
        level = panel.shift_level(t) if connected else LIGHT_OFF     # pulses before SHIFT drops
        if level != shift_shown:                                     # only writes on a change
            shift_shown = level
            leds[0].duty_cycle = SHIFT_DUTY[level]
        unit = connected and panel.unit_light
        if unit != unit_shown:                                       # also only on a change
            unit_shown = unit
            if leds[1]:
                leds[1].duty_cycle = LED_DUTY[1] if unit_shown else 0
            else:
                print("UNIT", 2 if unit_shown else 1)
        # send_report waits up to 2 s for the host: only send while USB is connected, or the loop, the light and
        # every timer would stall
        if not connected:
            sent[0] = sent[1] = sent[2] = None       # a host that comes back assumes all released: resend
            retry[0] = retry[1] = 0
        else:                                        # the host is back, by a wake request or by itself
            woke[0] = woke[1] = 0
        for n, dev in OUTPUTS:
            rep = reports[n]
            if n:
                panel.fill_report(n, rep)
            else:
                keyboard.fill(rep)
            if connected and rep != sent[n] and t >= retry[0]:
                # A host can enumerate the panel and never poll it (Linux with nothing reading the joystick):
                # then every send blocks for 2 s and fails. Back off, so the loop runs between the tries. The
                # back-off is shared, so after a failure the other device waits too and one pass never stalls
                # for more than 2 s.
                try:
                    dev.send_report(rep)
                    sent[n] = bytes(rep)
                    retry[0] = retry[1] = 0
                except OSError:
                    back_off(retry)
        time.sleep(0.001)
except Exception as e:
    try:                                     # noqa: SIM105 (CircuitPython has no contextlib)
        release_all()
    except Exception:
        pass
    try:                                     # noqa: SIM105
        traceback.print_exception(e)
    except Exception:
        pass
    time.sleep(2)
    supervisor.reload()
except KeyboardInterrupt:                    # Ctrl-C to the REPL: nothing left held either
    release_all()
    raise
