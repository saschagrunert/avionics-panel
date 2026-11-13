"""Stand-ins for the CircuitPython modules boot.py and code.py import, on a virtual clock.

A Board is the panel's hardware and the PC at the other end of the cable: the switches and encoder rings a hand
moves, the lights, and a host that takes the reports. The switches and rings are wired as on the board (ROW_PINS,
COL_PINS and RING_PINS below), whatever pins the firmware names, so a wrong pin there reads nothing here either.
The clock counts whole milliseconds from code.py's start; supervisor.ticks_ms counts from power-up, BOOT_MS
earlier, and wraps at 2**29 as on the board, first 65.536 s after power-up. Only time.sleep (the loop's 1 ms plus
the pass's own run time, work_ms) and the waits of send_report move the clock on. At every millisecond the board
runs the script's actions for it, then each keypad scans if its interval is up: every 20 ticks of 1/1024 s
(19.53 ms) for interval=0.02, as CircuitPython 9.2.9 counts it. boot.py runs before code.py's 0 ms: its sleep
settles the pins and does not move the clock.

The matrix switches close a row pin to a column pin through a diode (anode on the column), and the FREQ push
closes its pin to GND. A ring's two contacts close its A and B pin to GND in quadrature, A first when it turns
clockwise, with both open or both closed on a detent; rotaryio decodes them as CircuitPython's RP2040 port does,
from the state it finds when it starts. The host polls the HID endpoint every FRAME_MS. send_report waits up to
2 s until the host is there and has taken the last report, then hands the endpoint the new one, which the host
takes at its next poll, unless it has gone by then. If the wait runs out, send_report raises OSError, or, with
the bus suspended, asks the host to resume and returns with nothing sent
(shared-module/usb_hid/Device.c:202-225). Before boot.py runs, usb_hid.devices holds CircuitPython's own
keyboard, mouse and consumer control. microcontroller.nvm is a blank flash of NVM_SIZE bytes, with the keyboard
mode stored in it for Board(keyboard=True).

The stand-ins are written after CircuitPython 9.2.9's source and not checked against a board. Where they differ
from it: dicts keep their insertion order here, not on the board (panel.py does not depend on it);
time.sleep(0.001) waits 1 ms (on the board 0 to 1 ms, to the next tick); the keypads scan between the steps of a
pass, not from a timer interrupt in the middle of one; a report the endpoint holds when the host suspends the bus
counts as taken at the poll it was due (the host takes it when it resumes); the time module has only sleep (its
monotonic_ns returns a long integer on the board, which code.py's loop keeps off); the wiring is the board's, not
the Pico bench's; the status LED on GP25, PIO and PWM slices, the heap and its collections are not modelled.
"""
import builtins
import os
import sys
from contextlib import suppress
from functools import partial
from types import SimpleNamespace

FIRMWARE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firmware")
if FIRMWARE not in sys.path:       # behind the standard library: firmware/code.py would shadow its code module
    sys.path.append(FIRMWARE)

import buttonmap as BM  # noqa: E402
import keys  # noqa: E402
import make_keys  # noqa: E402, F401 (the shortcuts' names, for the panel page)

# The board's wiring, which tests/test_pins.py compares with pcb/board.py: the matrix rows and columns in
# buttonmap.MATRIX's order, the FREQ push, and the A and B contact of each ring
ROW_PINS = ("GP11", "GP8", "GP5", "GP2", "GP0")
COL_PINS = ("GP1", "GP3", "GP4", "GP6", "GP7", "GP9", "GP10")
RING_PINS = {"ALTHDG_OUTER": ("GP18", "GP19"), "ALTHDG_INNER": ("GP20", "GP21"), "FREQ_OUTER": ("GP24", "GP25"),
             "FREQ_INNER": ("GP22", "GP23"), "FMS_OUTER": ("GP26", "GP27"), "FMS_INNER": ("GP16", "GP17"),
             "RANGE": ("GP28", "GP29")}
# where each key, push and RANGE switch closes, by its firmware name: (row pin, column pin), or a pin to GND
CONTACTS = {name: (ROW_PINS[r], COL_PINS[c]) for r, row in enumerate(BM.MATRIX) for c, name in enumerate(row)}
CONTACTS["FREQ_PUSH"] = "GP13"
SWITCHES = list(CONTACTS)
RINGS = tuple(RING_PINS)
RING_CONTACT = {pin: (ring, i) for ring, pins in RING_PINS.items() for i, pin in enumerate(pins)}
EDGES_PER_DETENT = 2       # both encoder types: 30 detents per 15 pulses of 4 edges, a detent where A equals B
# rotaryio's count for a change of state, by old state << 2 | new state, a state being A << 1 | B: 0 where both
# contacts changed at once (shared-module/rotaryio/IncrementalEncoder.c:19-36)
TRANSITIONS = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)
SETTLE_S = 0.001           # a pulled-up input reads high after a sleep this long (boot.py waits 5 ms)
# An RP2040 PADS_BANK0 GPIO register as CircuitPython leaves it for PWMOut: IE, 4 mA, SCHMITT. Its pin reset clears
# the pull-down (common-hal/microcontroller/Pin.c:76-80), PWMOut sets IE again (pico-sdk gpio_set_function).
PAD_RESET = 0x52
FRAME_MS = 8               # the host's report interval (panel.HID_FRAME_MS)
SEND_MS = 2000             # send_report waits this long for the host
NVM_SIZE = 4096            # microcontroller.nvm of CircuitPython's RP2040 builds (CIRCUITPY_INTERNAL_NVM_SIZE)
BOOT_MS = 1100             # code.py starts about this long after power-up: the 1 s safe-mode wait, boot.py, USB
TICKS_WRAP_MS = 1 << 16    # supervisor.ticks_ms starts at 2**29 - 2**16 at power-up, so it first wraps then
RESUME_MS = 30             # a host asked to resume the bus is back this long after (USB 2.0, 7.1.7.7)
# usb_hid.devices before boot.py enables its own (shared-module/usb_hid/__init__.c): the keyboard, the mouse and
# consumer control, as (usage page, usage, report ID, in report length, out report length)
DEFAULT_DEVICES = ((0x01, 0x06, 1, 8, 1), (0x01, 0x02, 2, 4, 0), (0x0C, 0x01, 3, 2, 0))


class Stop(BaseException):
    """Ends a run: its time is up, or the panel is unplugged (not an Exception: code.py's error handler must not
    catch it)"""


class ReloadException(BaseException):
    """CircuitPython's: raised in code.py when it is to start again, after supervisor.reload() or a file saved to
    CIRCUITPY"""


def gpio(pin):
    """The number of a pin "GP<n>\""""
    return int(pin[2:])


class Event:
    """keypad.Event"""

    def __init__(self, key_number, pressed, timestamp):
        self.key_number, self.pressed, self.timestamp = key_number, pressed, timestamp


class EventQueue:
    """keypad.EventQueue: holds max_events; when it is full a scan's new event is dropped and overflowed set
    (shared-module/keypad/EventQueue.c:75-80)"""

    def __init__(self, max_events=64):
        self.max_events, self.items, self.overflowed = max_events, [], False

    def record(self, event):
        if len(self.items) >= self.max_events:
            self.overflowed = True
        else:
            self.items.append(event)

    def __len__(self):
        return len(self.items)

    def get(self):
        return self.items.pop(0) if self.items else None

    def clear(self):
        self.items, self.overflowed = [], False


class Keypad:
    """What KeyMatrix and Keys share, as in CircuitPython 9.2.9 with debounce_threshold 1: a scan every interval
    reports each key that changed since the last one, in the order of the key numbers, stamped with
    supervisor.ticks_ms. A key held when the keypad starts is not reported until it is let go. reset() scans at
    once and reports every key held as a press; the next scan follows an interval later. The interval counts in
    whole ticks of 1/1024 s (keypad/__init__.c:92): 0.02 s is 20 ticks, 19.53 ms. (The board scans from its tick
    interrupt, also in the middle of a loop pass; here in the first ms of the tick, between the steps of a pass.)
    contacts: where the switch of each key number closes, as in Board.closed."""

    def __init__(self, board, contacts, interval, max_events, debounce_threshold):
        self.board, self.contacts, self.interval, self.debounce_threshold = board, contacts, interval, \
            debounce_threshold
        self.interval_ticks = int(interval * 1024)
        self.events, self.resets = EventQueue(max_events), 0
        self.state = self.read()               # the keys as the last scan read them
        self.next_scan = board.raw_ticks() + self.interval_ticks
        board.keypads.append(self)

    def read(self):
        return {k for k, contact in enumerate(self.contacts) if contact in self.board.closed}

    def reset(self):
        self.resets += 1
        self.state = set()
        self.scan(self.board.raw_ticks())

    def scan(self, tick):
        """A scan at tick (1/1024 s from power-up)"""
        now = self.read()
        for k in sorted(now ^ self.state):
            self.events.record(Event(k, k in now, self.board.ticks_ms()))
        self.state = now
        self.next_scan = tick + self.interval_ticks


class KeyMatrix(Keypad):
    """keypad.KeyMatrix: key number row * columns + column, by the order of the pins it is given"""

    def __init__(self, board, row_pins, column_pins, columns_to_anodes=True, interval=0.02, max_events=64,
                 debounce_threshold=1):
        self.rows, self.cols, self.columns_to_anodes = tuple(row_pins), tuple(column_pins), columns_to_anodes
        board.claim(*self.rows, *self.cols)
        super().__init__(board, [(r, c) for r in self.rows for c in self.cols], interval, max_events,
                         debounce_threshold)
        board.matrix = self


class Keys(Keypad):
    def __init__(self, board, pins, *, value_when_pressed, pull=True, interval=0.02, max_events=64,
                 debounce_threshold=1):
        self.pins, self.value_when_pressed, self.pull = tuple(pins), value_when_pressed, pull
        board.claim(*self.pins)
        super().__init__(board, list(self.pins), interval, max_events, debounce_threshold)
        board.direct = self


class IncrementalEncoder:
    """rotaryio.IncrementalEncoder on the RP2040. Its PIO program reads the two pins, which must be neighbours,
    the lower GPIO in bit 0, and every change of them goes through CircuitPython's decoder: an edge counts +1 or
    -1 (TRANSITIONS), and `divisor` edges in one direction move position by one and start the count again
    (shared-module/rotaryio/IncrementalEncoder.c:38-53). With pin_a on the lower GPIO the port swaps the two bits
    of each change, but not of the state it finds at the start
    (ports/raspberrypi/common-hal/rotaryio/IncrementalEncoder.c:46-55, 84-87, 110-116)."""

    def __init__(self, board, pin_a, pin_b, divisor=4):
        if abs(gpio(pin_a) - gpio(pin_b)) != 1:
            raise RuntimeError("Pins must be sequential GPIO pins")
        board.claim(pin_a, pin_b)
        self.board, self.pins, self.divisor = board, (pin_a, pin_b), divisor
        self.swapped = gpio(pin_a) < gpio(pin_b)
        self.position = self.sub_count = 0
        self.state = self.read()
        board.encoders.append(self)

    def read(self):
        """The two pins as the PIO shifts them in"""
        low, high = sorted(self.pins, key=gpio)
        return self.board.level(high) << 1 | self.board.level(low)

    def update(self):
        """The PIO's interrupt after a change of the pins"""
        new = self.read()
        if self.swapped and new in (1, 2):
            new ^= 3
        self.sub_count += TRANSITIONS[self.state << 2 | new]
        self.state = new
        if abs(self.sub_count) >= self.divisor:
            self.position += 1 if self.sub_count > 0 else -1
            self.sub_count = 0


class PWMOut:
    """pwmio.PWMOut: keeps every duty written, with its time"""

    def __init__(self, board, pin, *, duty_cycle=0, frequency=500, variable_frequency=False):
        board.claim(pin)
        self.board, self.pin, self.frequency, self._duty = board, pin, frequency, duty_cycle
        self.history = board.log()             # (ms, duty) of every write
        board.leds.append(self)

    @property
    def duty_cycle(self):
        return self._duty

    @duty_cycle.setter
    def duty_cycle(self, value):
        self._duty = value
        self.history.append((self.board.t, value))


class AddressRange:
    """memorymap.AddressRange over the RP2040's pad registers: 32-bit words, read as reset until written"""

    def __init__(self, board, *, start, length):
        self.board, self.start, self.length = board, start, length

    def __getitem__(self, key):
        assert (key.start, key.stop, self.start % 4, self.length) == (0, 4, 0, 4)   # whole aligned words only
        return self.board.regs.get(self.start, PAD_RESET).to_bytes(4, "little")

    def __setitem__(self, key, value):
        assert (key.start, key.stop, len(value)) == (0, 4, 4)
        self.board.regs[self.start] = int.from_bytes(value, "little")


class Pull:
    UP, DOWN = "up", "down"


class DigitalInOut:
    """digitalio.DigitalInOut, for boot.py's SHIFT check and code.py's look at the rings. An input reads low while
    a closed switch connects it to a row driven low, while a contact closes it to GND, or while its pull-up has
    not charged it yet (a sleep of SETTLE_S after switching to input)."""

    def __init__(self, board, pin):
        board.claim(pin)
        self.board, self.pin, self.mode, self.pull, self.out, self.released = board, pin, "in", None, None, False
        self.charged = False
        board.ios[pin] = self

    def switch_to_input(self, pull=None):
        self.mode, self.pull, self.charged = "in", pull, False

    def switch_to_output(self, value=False, drive_mode=None):
        self.mode, self.out = "out", value

    @property
    def value(self):
        assert not self.released and self.mode == "in"
        ios = self.board.ios
        for row, col in (c for c in self.board.closed if isinstance(c, tuple)):
            io = ios.get(row)
            if col == self.pin and io and not io.released and io.mode == "out" and not io.out:
                return False                   # current through the diode and the closed switch
        if not self.board.level(self.pin):
            return False
        assert self.pull == Pull.UP, f"{self.pin} floats"
        return self.charged

    def deinit(self):
        self.released = True


class Device:
    """usb_hid.Device. send_report checks the report's length, then waits as CircuitPython's does
    (shared-module/usb_hid/Device.c:202-225): up to SEND_MS until the host has the panel mounted, the bus is not
    suspended and the endpoint all devices share is free again. Then the endpoint takes the report, and the
    board's host takes it from there at its next poll, unless it goes away before. If the wait runs out, nothing
    is sent: with the bus suspended it asks the host to resume (which the host does if it lets the panel wake
    it) and returns, else it raises OSError."""

    def __init__(self, board, *, report_descriptor, usage_page, usage, report_ids, in_report_lengths,
                 out_report_lengths):
        self.board, self.report_descriptor, self.usage_page, self.usage = board, report_descriptor, usage_page, usage
        self.report_ids, self.in_report_lengths, self.out_report_lengths = report_ids, in_report_lengths, \
            out_report_lengths
        self.tries = board.log()               # ms of every call

    def send_report(self, report, report_id=None):
        b = self.board
        if len(report) != self.in_report_lengths[0]:
            raise ValueError(f"report length must be {self.in_report_lengths[0]}")
        self.tries.append(b.t)
        free = max(b.taken, b.t + b.waits.pop(b.t, 0))     # the endpoint holds the last report until then

        def ready():                                       # tud_hid_ready
            return b.usb_connected and not b.busy and b.t >= free
        end = b.t + SEND_MS
        while b.t < end and not ready():
            b.advance(1)
        if b.suspended:
            if b.wakeup:                                   # remote wakeup: the host resumes the bus
                b.suspend = (b.suspend[0], min(b.suspend[1], b.t + RESUME_MS))
            return
        if not ready():
            if b.usb_connected and b.busy:
                b.busy -= 1
            raise OSError("USB busy")
        b.taken = (b.t // FRAME_MS + 1) * FRAME_MS
        if b.quiet[0] <= b.taken < b.quiet[1]:             # the host does not poll then: at its first poll after
            b.taken = -(-b.quiet[1] // FRAME_MS) * FRAME_MS
        if all(b.mounted(t) for t in range(b.t, b.taken + 1)):   # a host that goes away before then never takes it
            b.take(b.taken, self, bytes(report))


class Board:
    def __init__(self, script=None, work_ms=0, wrap=TICKS_WRAP_MS - BOOT_MS, log=list, keyboard=False):
        self.log = log                         # makes the records below that grow with the run
        self.nvm = bytearray(b"\xff" * NVM_SIZE)
        if keyboard:                           # the mode a plug-in with HOME (UNIT) held stored before
            self.nvm[keys.MODE_BYTE] = keys.KEYBOARD
        self.boot_device = None                # usb_hid.enable's boot_device
        self.t, self.until = 0, None
        self.script = {} if script is None else script     # ms -> [action(board)]
        self.work_ms = work_ms
        self.wrap = wrap                       # ms at which supervisor.ticks_ms wraps (65.536 s after power-up)
        self.closed = set()                    # the switches held closed: (row pin, column pin), or a pin to GND
        self.rings = dict.fromkeys(RINGS, 0)   # where each ring stands, in quadrature edges: on a detent if even
        self.busy = 0                          # sends that fail next: a host that has the panel mounted and does
                                               # not poll it leaves the last report in the endpoint
        self.waits = {}                        # ms: how much longer a send in that pass finds the endpoint taken
        self.quiet = (0, 0)                    # from, to: the ms the host has the panel mounted and does not poll
        self.usb_from, self.usb_gap = 0, (0, 0)   # the host has the panel mounted from this ms, not within the gap
        self.suspend = (0, 0)                  # from, to: the ms the host has the bus suspended
        self.wakeup = True                     # the host lets the panel ask it to resume (remote wakeup)
        self.gone = False                      # unplugged: the run has ended
        self.rgb_status_brightness = 0xFF      # supervisor.runtime's, as at power-up (status_leds.c:90)
        self.taken = 0                         # ms at which the host takes the last report sent
        self.received = []                     # (ms the host took it, device, report) of every report sent
        self.keypads, self.encoders, self.leds, self.regs, self.ios = [], [], [], {}, {}
        self.matrix = self.direct = None
        self.created = []                      # the usb_hid devices boot.py made
        self.devices = [Device(self, report_descriptor=b"", usage_page=page, usage=usage, report_ids=(i,),
                               in_report_lengths=(n,), out_report_lengths=(out,))
                        for page, usage, i, n, out in DEFAULT_DEVICES]   # usb_hid.devices: boot.py enables its own
        self.calls, self.boot_sleeps, self.reloads, self.printed = [], [], log(), log()
        self.sleeps = log()                    # (ms, seconds) of every sleep in code.py
        self.code = None                       # globals of the file running or last run
        pins = SimpleNamespace(**{f"GPIO{i}": f"GP{i}" for i in range(30)})
        self.modules = {
            "digitalio": SimpleNamespace(DigitalInOut=partial(DigitalInOut, self), Pull=Pull),
            "keypad": SimpleNamespace(KeyMatrix=partial(KeyMatrix, self), Keys=partial(Keys, self)),
            "memorymap": SimpleNamespace(AddressRange=partial(AddressRange, self)),
            "microcontroller": SimpleNamespace(pin=pins, nvm=self.nvm),
            "pwmio": SimpleNamespace(PWMOut=partial(PWMOut, self)),
            "rotaryio": SimpleNamespace(IncrementalEncoder=partial(IncrementalEncoder, self)),
            "storage": SimpleNamespace(disable_usb_drive=self.call("disable_usb_drive")),
            # supervisor.runtime.usb_connected is Board.usb_connected
            "supervisor": SimpleNamespace(runtime=self, reload=self.reload, ticks_ms=self.ticks_ms,
                                          set_usb_identification=self.call("set_usb_identification")),
            "time": SimpleNamespace(sleep=self.sleep),
            "traceback": SimpleNamespace(print_exception=self.printed.append),
            "usb_cdc": SimpleNamespace(disable=self.call("usb_cdc.disable")),
            "usb_hid": SimpleNamespace(Device=self.device, enable=self.enable, devices=self.devices,
                                       set_interface_name=self.call("usb_hid.set_interface_name")),
            "usb_midi": SimpleNamespace(disable=self.call("usb_midi.disable")),
        }

    # ---------------- the hand ----------------
    def hold(self, name, down):
        """A key, push or RANGE switch (SWITCHES) closes or opens"""
        (self.closed.add if down else self.closed.discard)(CONTACTS[name])

    def key(self, name):
        """(keypad, key number) under which the firmware's keypads scan a switch, by the pins it gave them"""
        return next((pad, pad.contacts.index(CONTACTS[name])) for pad in self.keypads if CONTACTS[name] in pad.contacts)

    def turn(self, ring, detents):
        """A ring (RINGS) turns by detents, clockwise positive"""
        self.edge(ring, EDGES_PER_DETENT * detents)

    def edge(self, ring, edges):
        """A ring moves by quadrature edges, clockwise positive: one of its contacts changes with each, and the
        encoders read their pins"""
        for _ in range(abs(edges)):
            self.rings[ring] += 1 if edges > 0 else -1
            for enc in self.encoders:
                enc.update()

    def level(self, pin):
        """Whether nothing closes a pin to GND: the FREQ push, or a ring's contact. From a detent with both open,
        A is closed for the first two edges of a cycle and B for the second and third."""
        if pin in self.closed:
            return False
        if pin in RING_CONTACT:
            ring, b = RING_CONTACT[pin]
            return (self.rings[ring] - b) % 4 not in (1, 2)
        return True

    def claim(self, *pins):
        """ValueError for a pin a DigitalInOut still holds, as on the board"""
        for pin in pins:
            if pin in self.ios and not self.ios[pin].released:
                raise ValueError(f"{pin} in use")

    # ---------------- the clock ----------------
    def ticks_ms(self, t=None):
        """supervisor.ticks_ms at ms t (default now): wraps at 2**29, first at self.wrap"""
        return ((self.t if t is None else t) - self.wrap) % (1 << 29)

    def raw_ticks(self):
        """The ticks of 1/1024 s since power-up, which the keypads scan by"""
        return (self.t + BOOT_MS) * 1024 // 1000

    def advance(self, ms):
        for _ in range(ms):
            self.t += 1
            try:
                self.hand()
            except Stop:                       # (sim/live.py's hand ends the run)
                self.gone = True
                raise
            tick = self.raw_ticks()
            for pad in self.keypads:
                if tick >= pad.next_scan:
                    pad.scan(pad.next_scan)

    def hand(self):
        """What the hand does at this ms: the script's actions for it"""
        for action in self.script.get(self.t, ()):
            action(self)

    def sleep(self, seconds):
        """time.sleep in code.py. The run ends here once the next loop pass would start at or after until: the
        panel is unplugged, so that code.py's handlers on its way out find no host to send to."""
        self.sleeps.append((self.t, seconds))
        if self.t + 1 + self.work_ms >= self.until:
            self.gone = True
            raise Stop
        self.settle(seconds)
        self.advance(round(seconds * 1000) + self.work_ms)

    def boot_sleep(self, seconds):
        """time.sleep in boot.py"""
        self.boot_sleeps.append(seconds)
        self.settle(seconds)

    def settle(self, seconds):
        """A sleep: a pulled-up input charges"""
        for io in self.ios.values():
            if seconds >= SETTLE_S and io.mode == "in" and io.pull == Pull.UP and not io.released:
                io.charged = True

    # ---------------- USB and the supervisor ----------------
    @property
    def suspended(self):
        return self.suspend[0] <= self.t < self.suspend[1]

    def mounted(self, t):
        """Whether the host has the panel mounted at ms t"""
        return t >= self.usb_from and not self.usb_gap[0] <= t < self.usb_gap[1]

    @property
    def usb_connected(self):
        """supervisor.runtime.usb_connected: mounted and not suspended"""
        return not self.gone and self.mounted(self.t) and not self.suspended

    def take(self, ms, device, report):
        """The host takes a report from a device at ms"""
        self.received.append((ms, device, report))

    def device(self, **kwargs):
        """usb_hid.Device in boot.py"""
        self.created.append(Device(self, **kwargs))
        return self.created[-1]

    def enable(self, devices, boot_device=0):
        self.devices[:] = devices
        self.boot_device = boot_device

    @property
    def keyboard(self):
        """Whether boot.py made the keyboard (keyboard mode) instead of the joysticks"""
        return [d.usage for d in self.devices] == [0x06]

    def call(self, name):
        return lambda *args: self.calls.append((name,) + args)

    def reload(self):
        """supervisor.reload(), and as a script's action a file saved to CIRCUITPY: the VM restarts code.py, so
        this run ends"""
        self.reloads.append(self.t)
        raise ReloadException

    # ---------------- running the firmware ----------------
    def exec(self, name, edits=(), **modules):
        """Runs firmware/<name> with the stand-ins as its modules, imported in that file only (sys.modules stays as
        it is). edits: (old, new) source text, each once. A module set to None is one the build lacks."""
        path = os.path.join(FIRMWARE, name)
        with open(path, encoding="utf-8") as f:
            source = f.read()
        for old, new in edits:
            assert source.count(old) == 1, old
            source = source.replace(old, new)
        modules = {**self.modules, **modules}

        def load(module, *args, **kwargs):
            if module not in modules:
                return builtins.__import__(module, *args, **kwargs)
            if modules[module] is None:
                raise ImportError(module)
            return modules[module]
        self.code = {"__name__": "__main__", "__file__": path, "__builtins__": {**vars(builtins), "__import__": load}}
        exec(compile(source, path, "exec"), self.code)

    def boot(self):
        self.exec("boot.py", time=SimpleNamespace(sleep=self.boot_sleep))
        return self

    def run(self, until, edits=()):
        """Runs code.py: its loop passes up to `until` ms, or until it reloads"""
        self.until, self.gone = until, False
        with suppress(Stop, ReloadException):
            self.exec("code.py", edits)
        return self
