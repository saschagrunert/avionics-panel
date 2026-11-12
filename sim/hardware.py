"""Stand-ins for the CircuitPython modules boot.py and code.py import, on a virtual clock.

A Board is the panel's hardware and the PC at the other end of the cable: the switches and encoder rings a hand
moves, the lights, and a host that takes the reports. The clock counts whole milliseconds from code.py's start.
Only time.sleep (the loop's 1 ms plus the pass's own run time, work_ms) and the waits of send_report move it on.
At every millisecond the board runs the script's actions for it, then each keypad scans if its interval is up.
boot.py runs before code.py's 0 ms: its sleep settles the pins and does not move the clock.

The matrix switches close a row pin to a column pin through a diode (anode on the column), the FREQ push closes
its pin to GND. The host polls the joysticks' shared endpoint every FRAME_MS: send_report waits until the host
has taken the last report, and the host takes the new one at its next poll.
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

MATRIX_NAMES = [n for row in BM.MATRIX for n in row]   # key numbers of the matrix keypad
SWITCHES = MATRIX_NAMES + ["FREQ_PUSH"]                 # every key, push and RANGE switch, by its firmware name
RINGS = ("ALTHDG_OUTER", "ALTHDG_INNER", "FREQ_OUTER", "FREQ_INNER", "FMS_OUTER", "FMS_INNER", "RANGE")
EDGES_PER_DETENT = 2       # both encoder types: 30 detents per 15 pulses of 4 edges
SETTLE_S = 0.001           # a pulled-up column reads high after a sleep this long (boot.py waits 5 ms)
PAD_RESET = 0x56           # an RP2040 PADS_BANK0 GPIO register after reset: IE, 4 mA, PDE, SCHMITT
FRAME_MS = 8               # the host's report interval (panel.HID_FRAME_MS)


class Stop(BaseException):
    """Ends a run: its time is up, or code.py reloads (not an Exception: code.py's error handler must not catch it)"""


class Event:
    """keypad.Event"""

    def __init__(self, key_number, pressed, timestamp):
        self.key_number, self.pressed, self.timestamp = key_number, pressed, timestamp


class EventQueue:
    """keypad.EventQueue. It never fills up here: a test sets overflowed itself."""

    def __init__(self):
        self.items, self.overflowed = [], False

    def get(self):
        return self.items.pop(0) if self.items else None

    def clear(self):
        self.items, self.overflowed = [], False


class Keypad:
    """What KeyMatrix and Keys share, as in CircuitPython 9.2.9 with debounce_threshold 1: a scan every interval
    reports each key that changed since the last one, stamped with supervisor.ticks_ms. A key held when the keypad
    starts is not reported until it is let go. reset() scans at once and reports every key held as a press; the
    next scan follows an interval later. (The board scans every 20 ticks of 1/1024 s from its tick interrupt, also
    in the middle of a loop pass; here every 20 ms, between the steps of a pass.)"""

    def __init__(self, board, interval, max_events, debounce_threshold):
        self.board, self.interval, self.debounce_threshold = board, interval, debounce_threshold
        self.scan_ms = round(interval * 1000)
        self.events, self.resets = EventQueue(), 0
        self.state = self.read()               # the keys as the last scan read them
        self.next_scan = board.t + self.scan_ms
        board.keypads.append(self)

    def reset(self):
        self.resets += 1
        self.state = set()
        self.scan()

    def scan(self):
        now = self.read()
        for k in sorted(now ^ self.state):
            self.events.items.append(Event(k, k in now, self.board.ticks_ms()))
        self.state = now
        self.next_scan = self.board.t + self.scan_ms


class KeyMatrix(Keypad):
    def __init__(self, board, row_pins, column_pins, columns_to_anodes=True, interval=0.02, max_events=64,
                 debounce_threshold=1):
        self.rows, self.cols, self.columns_to_anodes = tuple(row_pins), tuple(column_pins), columns_to_anodes
        super().__init__(board, interval, max_events, debounce_threshold)
        board.matrix = self

    def contact(self, k):
        """(row pin, column pin) of key number k"""
        return self.rows[k // len(self.cols)], self.cols[k % len(self.cols)]

    def read(self):
        return {k for k in range(len(self.rows) * len(self.cols)) if self.contact(k) in self.board.closed}


class Keys(Keypad):
    def __init__(self, board, pins, *, value_when_pressed, pull=True, interval=0.02, max_events=64,
                 debounce_threshold=1):
        self.pins, self.value_when_pressed, self.pull = tuple(pins), value_when_pressed, pull
        super().__init__(board, interval, max_events, debounce_threshold)
        board.direct = self

    def read(self):
        return {k for k, p in enumerate(self.pins) if p in self.board.closed}


class IncrementalEncoder:
    """rotaryio.IncrementalEncoder: counts the ring's quadrature edges, position = edges / divisor"""

    def __init__(self, board, pin_a, pin_b, divisor=4):
        self.pins, self.divisor, self.edges = (pin_a, pin_b), divisor, 0
        board.encoders.append(self)

    @property
    def position(self):
        return self.edges // self.divisor


class PWMOut:
    """pwmio.PWMOut: keeps every duty written, with its time"""

    def __init__(self, board, pin, *, duty_cycle=0, frequency=500, variable_frequency=False):
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
    """digitalio.DigitalInOut, for boot.py's SHIFT check. A column reads low while a closed switch connects it to a
    row driven low, or while its pull-up has not charged it yet (a sleep of SETTLE_S after switching to input)."""

    def __init__(self, board, pin):
        assert pin not in board.ios or board.ios[pin].released, f"{pin} claimed twice"
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
        assert self.pull == Pull.UP, f"{self.pin} floats"
        return self.charged

    def deinit(self):
        self.released = True


class Device:
    """usb_hid.Device. send_report waits for the endpoint the joysticks share, as CircuitPython's does; the
    board's host takes the report at its next poll."""

    def __init__(self, board, *, report_descriptor, usage_page, usage, report_ids, in_report_lengths,
                 out_report_lengths):
        self.board, self.report_descriptor, self.usage_page, self.usage = board, report_descriptor, usage_page, usage
        self.report_ids, self.in_report_lengths, self.out_report_lengths = report_ids, in_report_lengths, \
            out_report_lengths
        self.tries = board.log()               # ms of every call
        board.created.append(self)

    def send_report(self, report, report_id=None):
        b, t = self.board, self.board.t
        self.tries.append(t)
        if b.busy:                             # a host that does not take it: fails after b.block ms
            b.busy -= 1
            b.advance(b.block)
            raise OSError("USB busy")
        b.advance(max(b.taken - b.t, 0))       # the endpoint still holds the last report until the host's poll
        b.taken = (b.t // FRAME_MS + 1) * FRAME_MS
        b.take(b.taken, self, bytes(report))
        b.advance(b.waits.pop(t, 0))


class Board:
    def __init__(self, script=None, work_ms=0, wrap=65536, log=list):
        self.log = log                         # makes the records below that grow with the run
        self.t, self.until = 0, None
        self.script = {} if script is None else script     # ms -> [action(board)]
        self.work_ms = work_ms
        self.wrap = wrap                       # ms at which supervisor.ticks_ms wraps (CircuitPython: 65.536 s)
        self.closed = set()                    # the switches held closed: (row pin, column pin), or a pin to GND
        self.busy = 0                          # sends that fail next, whichever device sends
        self.block = 0                         # ms a failing send waits before it fails (2000 on the board)
        self.waits = {}                        # ms: how much longer a good send in that pass waits for the host
        self.usb_from, self.usb_gap = 0, (0, 0)   # USB connected from this ms, and not within the gap
        self.taken = 0                         # ms at which the host takes the last report sent
        self.received = []                     # (ms the host took it, device, report) of every report sent
        self.keypads, self.encoders, self.leds, self.regs, self.ios = [], [], [], {}, {}
        self.matrix = self.direct = None
        self.created, self.devices = [], []    # usb_hid devices boot.py made, and those it enabled
        self.calls, self.boot_sleeps, self.reloads, self.printed = [], [], log(), log()
        self.sleeps = log()                    # (ms, seconds) of every sleep in code.py
        self.code = None                       # globals of the file running or last run
        pins = SimpleNamespace(**{f"GPIO{i}": f"GP{i}" for i in range(30)})
        self.modules = {
            "digitalio": SimpleNamespace(DigitalInOut=partial(DigitalInOut, self), Pull=Pull),
            "keypad": SimpleNamespace(KeyMatrix=partial(KeyMatrix, self), Keys=partial(Keys, self)),
            "memorymap": SimpleNamespace(AddressRange=partial(AddressRange, self)),
            "microcontroller": SimpleNamespace(pin=pins),
            "pwmio": SimpleNamespace(PWMOut=partial(PWMOut, self)),
            "rotaryio": SimpleNamespace(IncrementalEncoder=partial(IncrementalEncoder, self)),
            "storage": SimpleNamespace(disable_usb_drive=self.call("disable_usb_drive")),
            # supervisor.runtime.usb_connected is Board.usb_connected
            "supervisor": SimpleNamespace(runtime=self, reload=self.reload, ticks_ms=self.ticks_ms,
                                          set_usb_identification=self.call("set_usb_identification")),
            "time": SimpleNamespace(monotonic_ns=lambda: self.t * 1_000_000, sleep=self.sleep),
            "traceback": SimpleNamespace(print_exception=self.printed.append),
            "usb_cdc": SimpleNamespace(disable=self.call("usb_cdc.disable")),
            "usb_hid": SimpleNamespace(Device=partial(Device, self), enable=self.enable, devices=self.devices,
                                       set_interface_name=self.call("usb_hid.set_interface_name")),
            "usb_midi": SimpleNamespace(disable=self.call("usb_midi.disable")),
        }

    # ---------------- the hand ----------------
    def contact(self, name):
        """Where a switch (SWITCHES) closes: its row and column pin by its place in buttonmap.MATRIX, or the FREQ
        push's pin"""
        if name == "FREQ_PUSH":
            return self.direct.pins[0]
        return self.matrix.contact(MATRIX_NAMES.index(name))

    def hold(self, name, down):
        (self.closed.add if down else self.closed.discard)(self.contact(name))

    def turn(self, ring, detents):
        """A ring (RINGS) turns by detents, clockwise positive: the encoder on the pins code.py's RINGS gives it
        counts"""
        pins = next((a, b) for name, a, b, _ in self.code["RINGS"] if name == ring)
        for enc in self.encoders:
            if enc.pins == pins:
                enc.edges += EDGES_PER_DETENT * detents

    # ---------------- the clock ----------------
    def ticks_ms(self, t=None):
        """supervisor.ticks_ms at ms t (default now): wraps at 2**29, first at self.wrap"""
        return ((self.t if t is None else t) - self.wrap) % (1 << 29)

    def advance(self, ms):
        for _ in range(ms):
            self.t += 1
            self.hand()
            for keys in self.keypads:
                if self.t >= keys.next_scan:
                    keys.scan()

    def hand(self):
        """What the hand does at this ms: the script's actions for it"""
        for action in self.script.get(self.t, ()):
            action(self)

    def sleep(self, seconds):
        """time.sleep in code.py. The run ends here once the next loop pass would start at or after until."""
        self.sleeps.append((self.t, seconds))
        if self.t + 1 + self.work_ms >= self.until:
            raise Stop
        self.advance(round(seconds * 1000) + self.work_ms)

    def boot_sleep(self, seconds):
        """time.sleep in boot.py: a pulled-up input charges"""
        self.boot_sleeps.append(seconds)
        for io in self.ios.values():
            if seconds >= SETTLE_S and io.mode == "in" and io.pull == Pull.UP and not io.released:
                io.charged = True

    # ---------------- USB and the supervisor ----------------
    @property
    def usb_connected(self):
        return self.t >= self.usb_from and not self.usb_gap[0] <= self.t < self.usb_gap[1]

    def take(self, ms, device, report):
        """The host takes a report from a device at ms"""
        self.received.append((ms, device, report))

    def enable(self, devices):
        self.devices[:] = devices

    def call(self, name):
        return lambda *args: self.calls.append((name,) + args)

    def reload(self):
        self.reloads.append(self.t)
        raise Stop                             # the VM restarts code.py: this run ends

    # ---------------- running the firmware ----------------
    def exec(self, name, edits=(), **modules):
        """Runs firmware/<name> with the stand-ins as its modules, imported in that file only (sys.modules stays as
        it is). edits: (old, new) source text, each once. A module set to None is one the build lacks."""
        path = os.path.join(FIRMWARE, name)
        with open(path) as f:
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
        self.until = until
        with suppress(Stop):
            self.exec("code.py", edits)
        return self
