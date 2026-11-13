# code.py - Avionics Panel rev 1 (CircuitPython 9.2.9 on the panel's RP2040).
# Installing and updating: docs/building/bring-up.md. How it works: docs/architecture/firmware.md.
# Logic: panel.py. Button numbers: buttonmap.py / BUTTONS.md. Keyboard mode: keys.py. Pins: pcb/board.py.
import time
import traceback

import digitalio
import keypad
import microcontroller
import pwmio
import rotaryio
import supervisor
import usb_hid

try:                               # the pad's drive strength (drive_12ma below); a build without it still runs
    import memorymap
except ImportError:
    memorymap = None

P = microcontroller.pin            # GPIO names work on any RP2040 build (the Pico board renames some)

# The bench on a plain Raspberry Pi Pico (docs/building/bring-up.md, Pico bench): the FREQ knob moves to GP12/13
# (outer) and GP14/15 (inner), its push to GP22 and the SHIFT light to the onboard LED (GP25); the UNIT light is
# printed instead. RANGE stays on GP28/GP29, so the bench runs all 7 PIO encoders, but GP29 is not on the header.
PICO_TEST = False

# The key matrix, rows and columns as in buttonmap.MATRIX (docs/architecture/electronics.md, GPIO map)
ROW_PINS = (P.GPIO11, P.GPIO8, P.GPIO5, P.GPIO2, P.GPIO0)
COL_PINS = (P.GPIO1, P.GPIO3, P.GPIO4, P.GPIO6, P.GPIO7, P.GPIO9, P.GPIO10)
# The keypad reports the changes of one scan row by row, in the order it is given the pins. SHIFT's row and
# column go first, so SHIFT comes before a key pressed in the same scan: the key is shifted.
SCAN_ROWS, SCAN_COLS = (3, 0, 1, 2, 4), (3, 0, 1, 2, 4, 5, 6)
FREQ_PUSH = P.GPIO13               # direct input, switch to GND
SHIFT_LED, UNIT_LED = P.GPIO12, P.GPIO15
SHIFT_LED_GPIO = 12                # its GPIO number, for drive_12ma
# SHIFT (amber), UNIT (white) brightness, 0..0xFFFF: about 28 and 33 % of full, with room to tune both ways on
# the first board (docs/architecture/electronics.md, Lights)
LED_DUTY = (0x4800, 0x5500)
# SHIFT light duty per panel level (off, dim, full). Dim is 1/4 of full: the eye is not linear, so it looks like
# about half the brightness.
SHIFT_DUTY = (0, LED_DUTY[0] // 4, LED_DUTY[0])

# (ring, pin A, pin B, reverse). Ring 1 of a dual encoder = pins A/B/C, ring 2 = A'/B'/C'. If outer and
# inner are swapped on the first board, swap the two ring names; if a direction is wrong, flip reverse.
# GP25 is also the Pico build's status LED (docs/architecture/firmware.md, Pins).
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
SEND_WAIT_MS = 2000                      # send_report waits this long for the host before it gives up
WAKE_MS = 500                            # wait this long for a host asked to resume the bus: USB 2.0 needs 30 ms
                                         # (7.1.7.7), Linux holds the resume 40 ms, a sleeping host controller more
DETENT_MS = 500                          # a ring between two detents at the start gets this long to reach one
MAX_EVENTS = 320                         # each keypad's event queue: more than a switch that changes with every
                                         # scan makes in the little over 5 s it can go unread
                                         # (docs/architecture/firmware.md, Keys and switch bounce)
TICKS_PERIOD = 1 << 29                   # supervisor.ticks_ms and Event.timestamp wrap after this many ms
OUTPUTS = ()                             # (report, device) once code.py has found them: 0 the keyboard, 1 and 2
                                         # the joysticks
clock = [0, supervisor.ticks_ms()]       # ms since code.py started, and supervisor.ticks_ms() then (now())


def drive_12ma(gpio):
    """The pad's drive strength to 12 mA, so the series resistor, not the pad, sets the SHIFT light's current.
    CircuitPython has no call for it: memorymap writes the RP2040's pad register (32-bit, read, modify, write).
    After PWMOut, which leaves the drive field alone. If it fails the light stays at the 4 mA drive, dimmer."""
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


def now():
    """The loop's clock, brought up to date: ms since code.py started, counted on from supervisor.ticks_ms()
    across its wrap. It stays a small integer for 2**30 ms (12.4 days), so reading it allocates nothing
    (time.monotonic_ns() returns a long integer)."""
    ticks = supervisor.ticks_ms()
    clock[0] += ticks_diff(ticks, clock[1])
    clock[1] = ticks
    return clock[0]


def back_off(r):
    """r: [no try before this ms, the last wait]: the next try waits RETRY_MS from now, then twice as long each time,
    up to RETRY_MAX_MS. From now: the try that failed took 2 s."""
    wait = min(2 * r[1], RETRY_MAX_MS) if r[1] else RETRY_MS
    r[0], r[1] = now() + wait, wait


class Source:
    """One keypad, its events read one ahead into an Event of its own (get_into, which leaves nothing on the
    heap). If events were lost (more than MAX_EVENTS between two loop passes), every key of the keypad goes up
    at once, and the keypad, reset, reports the ones still held again, as new presses."""

    def __init__(self, keys, names):
        self.keys, self.names = keys, names
        self.down = set()          # key numbers the panel has as pressed
        self.event = keypad.Event()
        self.ready = False         # self.event holds an event not yet passed on

    def start(self, t):
        """Reads the first event of this pass; t: the pass's ms"""
        events = self.keys.events
        if events.overflowed:
            events.clear()
            self.keys.reset()
            for k in self.down:
                panel.release(self.names[k], t)
            self.down.clear()
        self.ready = events.get_into(self.event)

    def next(self, t):
        """Passes the event read to the panel, and reads the next"""
        ev = self.event
        k = ev.key_number
        # Only what changes a key for the panel: a key held when the keypad started sends a release only, and a
        # scan between the clear and the reset of an overflow reports a key that the reset reports again
        if ev.pressed != (k in self.down):
            if ev.pressed:
                self.down.add(k)
            else:
                self.down.discard(k)
            panel.key(self.names[k], ev.pressed, t, t + ticks_diff(ev.timestamp, clock[1]))
        self.ready = self.keys.events.get_into(ev)


def read_keys(t):
    """Passes the events of both keypads to the panel in the order they were scanned (Event.timestamp), the
    matrix first within a ms: a pass that waited for the host reads seconds of them at once, and a FREQ push
    scanned before a SHIFT tap stays plain. clock[1] is supervisor.ticks_ms() at t, which puts the scan times on
    t's clock."""
    a, b = sources
    a.start(t)
    b.start(t)
    while a.ready or b.ready:
        if a.ready and not (b.ready and ticks_diff(b.event.timestamp, a.event.timestamp) < 0):
            a.next(t)
        else:
            b.next(t)


def make_encoders():
    """One rotaryio encoder per ring, counting a detent every two edges (divisor 2: 30 detents and 15 pulses per
    turn). rotaryio counts from the state it starts in, and started between two detents it would lose the first
    detent after every reversal. So each encoder is made while its ring rests on a detent, where its A and B
    contacts read alike, after waiting for that, up to DETENT_MS for all rings together."""
    ios = [digitalio.DigitalInOut(pin) for ring in RINGS for pin in ring[1:3]]
    for io in ios:
        io.switch_to_input(pull=digitalio.Pull.UP)
    time.sleep(0.001)                                # the pull-ups charge the lines
    end = now() + DETENT_MS
    out = []
    for i in range(len(RINGS)):
        a, b = ios[2 * i], ios[2 * i + 1]
        while a.value != b.value and now() < end:
            time.sleep(0.001)
        if a.value != b.value:
            print(RINGS[i][0], "is between two detents: it loses a detent when it turns back, until the next start")
        a.deinit()                                   # free the pins for rotaryio
        b.deinit()
        out.append(rotaryio.IncrementalEncoder(RINGS[i][1], RINGS[i][2], divisor=2))
    return out


def release_all():
    """All buttons (or keys) up on every device: the host keeps the last report, also after code.py has stopped."""
    if not supervisor.runtime.usb_connected:
        return
    for n, dev in OUTPUTS:
        try:
            dev.send_report(ZERO[n])
        except OSError:
            pass


def input_waiting():
    """Whether a keypad has events or a ring has turned that the loop has not read yet"""
    for src in sources:
        if src.keys.events:
            return True
    for i in range(len(RINGS)):
        if encoders[i].position != last[i]:
            return True
    return False


def turns(t):
    """Passes the detents each ring has turned since the last call to the panel"""
    for i in range(len(RINGS)):                      # no enumerate(): it allocates in every pass
        d = encoders[i].position - last[i]
        if d:
            last[i] += d
            panel.turn(RINGS[i][0], -d if RINGS[i][3] else d, t)


def show(level, unit):
    """The SHIFT light at a level of panel.py and the UNIT light on or off, each written only on a change"""
    if level != shown[0]:
        shown[0] = level
        leds[0].duty_cycle = SHIFT_DUTY[level]
    if unit != shown[1]:
        shown[1] = unit
        if leds[1]:
            leds[1].duty_cycle = LED_DUTY[1] if unit else 0
        else:
            print("UNIT", 2 if unit else 1)


def behind():
    """Whether the host has something other than what the panel shows: a report that differs from the one last
    sent, or in keyboard mode another function down (keyboard.fn keeps the host's while USB is down) or only
    the modifiers of its shortcut. Not after a request the host refused, until the host has been back: then only
    input asks again."""
    if woke[1]:
        return False
    if KEYBOARD:
        return panel.pressed() != keyboard.fn or (keyboard.fn is not None and not sent[0][2])
    return reports[1] != sent[1] or reports[2] != sent[2]


def asked(start):
    """Whether a send_report that began at start and returned without an error asked the host to resume and
    sent nothing: in CircuitPython 9.2.9 only one that waited out its 2 s and found the bus suspended does"""
    return now() - start >= SEND_WAIT_MS


def wake(t):
    """Asks a host that has suspended the bus to resume it, so that what the panel has for it reaches the PC
    (docs/architecture/firmware.md, USB). CircuitPython has no call for it: send_report waits 2 s for the host,
    then asks a suspended one to resume and returns; with no host at all it raises OSError, and nothing was
    asked. t: the pass's ms"""
    n, dev = OUTPUTS[0]
    start = now()
    try:
        # What goes out if the host is back within the 2 s: the report the last pass worked out for joystick 1,
        # or every key of the keyboard up, which is what a host that was away is taken to have (keys.Keyboard)
        dev.send_report(reports[n] if n else ZERO[n])
    except OSError:
        waited(t, False)
    else:
        waited(t, asked(start))


def waited(t, suspended):
    """After a request to resume: a send that asked a suspended host (suspended), one that found no host at
    all, or one that went out to a host back meanwhile. Waits up to WAKE_MS for a suspended host, then stalls
    the panel by the whole wait since t, so that the presses and gaps it shows start for the PC then, and a
    press still lasts its PRESS_MS; the knob steps queued so far stay, as after any wait for the host. A request
    that brings no host back is not repeated before a back-off, which the loop ends once the host is back. A
    host that is back may have re-enumerated meanwhile, with no pass to see USB down: it gets the joysticks'
    reports again. A keyboard's host that had suspended the bus kept its report: a shortcut still held goes on
    from that report (sent[0]), and does not go down a second time."""
    end = now() + (WAKE_MS if suspended else 0)
    while not supervisor.runtime.usb_connected and now() < end:
        time.sleep(0.001)
    panel.stalled(now() - t)
    panel.keep_steps()
    if not supervisor.runtime.usb_connected:
        back_off(woke)
        return
    unsent[1] = unsent[2] = True
    if suspended:
        unsent[0] = False


# Whatever ends code.py must not leave a button held on the PC: an error, while it starts or in the loop,
# releases everything and restarts code.py after 2 s (docs/architecture/firmware.md, Errors).
try:
    # The mode follows the devices boot.py made: the two joysticks, or one keyboard and nothing else (keys.py).
    # Before boot.py has run, CircuitPython has a keyboard of its own, with a mouse and consumer control.
    kinds = [(d.usage_page, d.usage) for d in usb_hid.devices]
    KEYBOARD = kinds == [(0x01, 0x06)]
    if not KEYBOARD and kinds != [(0x01, 0x04), (0x01, 0x04)]:
        raise RuntimeError("joysticks missing: copy boot.py and replug the panel")

    import buttonmap as BM
    from panel import KEY_SCAN_MS, LATE_MS, LIGHT_OFF, Panel

    ZERO = {1: bytes(BM.SIZE[1] // 8), 2: bytes(BM.SIZE[2] // 8)}   # made now: release_all may run out of memory
    reports = {1: bytearray(BM.SIZE[1] // 8), 2: bytearray(BM.SIZE[2] // 8)}
    if KEYBOARD:                         # report 0: the keyboard's, filled by keys.Keyboard
        import keys  # only in keyboard mode: the joysticks keep its RAM
        ZERO[0], reports[0] = bytes(keys.REPORT), bytearray(keys.REPORT)
    # Made once, as everything the loop needs: a pass that only keeps time leaves nothing on the heap, which
    # fills, and is collected, only as keys, knobs and repeats change buttons.
    OUTPUTS = ((0, usb_hid.devices[0]),) if KEYBOARD else ((1, usb_hid.devices[0]), (2, usb_hid.devices[1]))
    # sent[n]: the report the host has of device n, unless unsent[n]: then it has none of this panel's yet (at
    # the start), or USB was down since, after which a host assumes all released or still has an older one.
    # While USB is down, behind() compares it with the panel's. again[n], read while unsent[n]: a late send asked
    # for it since USB was last down (below)
    sent = {n: bytearray(len(reports[n])) for n in reports}
    unsent = [True, True, True]
    again = [False, False, False]

    # Both keypads scan every KEY_SCAN s (docs/architecture/firmware.md, Keys and switch bounce).
    # debounce_threshold stays at its default (1): a press reaches the PC on the first scan that reads it, and
    # panel.py takes care of a bounce by the scan times of the events (Event.timestamp, on the
    # supervisor.ticks_ms clock).
    KEY_SCAN = KEY_SCAN_MS / 1000
    matrix = keypad.KeyMatrix([ROW_PINS[r] for r in SCAN_ROWS], [COL_PINS[c] for c in SCAN_COLS],
                              columns_to_anodes=True, interval=KEY_SCAN, max_events=MAX_EVENTS)
    direct = keypad.Keys((FREQ_PUSH,), value_when_pressed=False, pull=True, interval=KEY_SCAN,
                         max_events=MAX_EVENTS)
    encoders = make_encoders()
    last = [e.position for e in encoders]    # each ring's position as the panel has it
    leds = [pwmio.PWMOut(SHIFT_LED, frequency=1000),
            pwmio.PWMOut(UNIT_LED, frequency=1000) if UNIT_LED else None]
    if not PICO_TEST:              # the Pico's onboard LED has a resistor of its own
        drive_12ma(SHIFT_LED_GPIO)
    shown = [None, None]                 # the SHIFT light's level and the UNIT light as last written (show())
    panel = Panel(solo=KEYBOARD)         # keyboard mode: one shortcut at a time (keys.py)
    if KEYBOARD:
        keyboard = keys.Keyboard(panel)

    # each keypad on its own: an overflow on one leaves the keys held on the other alone
    sources = (Source(matrix, [BM.MATRIX[r][c] for r in SCAN_ROWS for c in SCAN_COLS]),
               Source(direct, ["FREQ_PUSH"]))
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
        t = now()
        # USB connected: mounted and not suspended. While it is not (the PC asleep, booting or off, a charger)
        # the lights stay dark and SHIFT does not apply (dark means plain); the panel itself runs on.
        connected = supervisor.runtime.usb_connected
        panel.dark = not connected
        if connected:                                # the host is back, by a wake request or by itself
            woke[0] = woke[1] = 0
        else:                                        # a host that comes back gets every report again
            unsent[0] = unsent[1] = unsent[2] = True
            again[1] = again[2] = False
            retry[0] = retry[1] = 0
        # With USB down and no back-off running, the panel asks the host to resume when input waits or the host
        # has something other than what the panel shows (behind()): a press, a step or a release that plays out
        # after the host suspended the bus. Then only a pass that asks reads input: what comes in right after the
        # check stays in the keypads and encoders for the next pass, which then asks.
        asking = not connected and t >= woke[0]
        if not asking or input_waiting() or behind():
            if asking:
                # wake() takes 2 s or more and the rest of the input is read after it. The lights go dark before
                # it, not after. The knobs as they stand go to the panel first, at this pass's time, so a detent
                # turned before a key pressed during the wait comes first; and those steps stay if the knob
                # turns back during the wait.
                show(LIGHT_OFF, False)
                turns(t)
                wake(t)
                t = now()
            read_keys(t)
            turns(t)
        panel.tick(t)
        show(panel.shift_level(t), connected and panel.unit_light)   # the amber light pulses before SHIFT drops
        for n, dev in OUTPUTS:
            rep = reports[n]
            if n:
                panel.fill_report(n, rep)
            elif supervisor.runtime.usb_connected:
                keyboard.fill(rep, None if unsent[0] else sent[0])
            else:
                continue                             # keyboard.fn keeps the function the host has (behind())
            # send_report waits up to 2 s for the host, so only while USB is connected, read anew for each send.
            # A host that has the panel mounted and never polls it fails every send after those 2 s: back off,
            # for both devices, so that the loop runs between the tries.
            changed = rep != sent[n]
            if (changed or unsent[n]) and t >= retry[0] and supervisor.runtime.usb_connected:
                start = now()
                try:
                    dev.send_report(rep)
                except OSError:
                    back_off(retry)
                else:
                    late = now() - t                 # since the time this pass worked the report out for
                    if supervisor.runtime.usb_connected:
                        if late > LATE_MS:
                            # The PC gets this report, and what the pass has yet to send, later than the
                            # presses and gaps allow for: they start anew for the PC. And the host may have
                            # gone and come back anew meanwhile, with no pass to see it: it gets the other
                            # joystick's report again. Not after a report that itself only went out again for
                            # that reason: a host that takes every report late would get them without end.
                            panel.stalled(late)
                            if changed or not again[n]:
                                unsent[1] = unsent[2] = again[1] = again[2] = True
                        for i in range(len(rep)):
                            sent[n][i] = rep[i]
                        unsent[n] = False
                        retry[0] = retry[1] = 0
                    elif asked(start):
                        # The host suspended the bus during the send: send_report waited out its 2 s, asked
                        # the host to resume and sent nothing. That is the request: the panel waits for the host
                        # as after wake(), and the report goes out again once the host is back.
                        waited(t, True)
                    if late > LATE_MS:               # the other device's report in the next pass: the sends of
                        break                        # one pass wait for the host once, 2.5 s at most
        time.sleep(0.001)
except Exception as e:
    try:
        release_all()
    except Exception:
        pass
    try:
        traceback.print_exception(e)
    except Exception:
        pass
    time.sleep(2)
    supervisor.reload()
except BaseException:                        # Ctrl-C to the REPL, and CircuitPython's reload after a file was saved
    release_all()                            # to CIRCUITPY (ReloadException): nothing left held either
    raise
