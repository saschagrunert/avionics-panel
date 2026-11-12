"""Stand-ins for the CircuitPython modules boot.py and code.py import, on a virtual clock.

A Board is the panel's hardware and the PC at the other end of the cable: the switches and encoder rings a hand
moves, the lights, and a host that takes the reports. The clock counts whole milliseconds from code.py's start;
time.monotonic_ns and supervisor.ticks_ms count from power-up, BOOT_MS earlier, as on the board, so ticks_ms
first wraps 65.536 s after power-up. Only time.sleep (the loop's 1 ms plus the pass's own run time, work_ms) and
the waits of send_report move the clock on. At every millisecond the board runs the script's actions for it, then
each keypad scans if its interval is up: every 20 ticks of 1/1024 s (19.53 ms) for interval=0.02, as
CircuitPython 9.2.9 counts it. boot.py runs before code.py's 0 ms: its sleep settles the pins and does not move
the clock.

The matrix switches close a row pin to a column pin through a diode (anode on the column), the FREQ push closes
its pin to GND. The host polls the joysticks' shared endpoint every FRAME_MS: send_report waits until the host
has taken the last report, and the host takes the new one at its next poll. The host can be away (not mounted)
or have the bus suspended: then send_report waits 2 s for it and, while suspended, asks it to resume and returns,
else it raises OSError. microcontroller.nvm is a blank flash of NVM_SIZE bytes, with the keyboard mode stored in
it for Board(keyboard=True).

Where it still differs from CircuitPython 9.2.9: dicts keep their insertion order here, not on the board (panel.py
does not depend on it); time.sleep(0.001) waits 1 ms (on the board 0 to 1 ms, to the next tick); the keypads scan
between the steps of a pass, not from a timer interrupt in the middle of one; reload() ends the run at once; an
encoder counts edges // divisor; a send that starts while USB is connected and still waits for the endpoint when
the host suspends the bus goes out here once the host is back (on the board it returns after 2 s unsent, and
code.py sends the report again once the host is back); the status LED on GP25, PIO and PWM slices, the heap and
its collections are not modelled.
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

MATRIX_NAMES = [n for row in BM.MATRIX for n in row]   # key numbers of the matrix keypad
SWITCHES = MATRIX_NAMES + ["FREQ_PUSH"]                 # every key, push and RANGE switch, by its firmware name
RINGS = ("ALTHDG_OUTER", "ALTHDG_INNER", "FREQ_OUTER", "FREQ_INNER", "FMS_OUTER", "FMS_INNER", "RANGE")
EDGES_PER_DETENT = 2       # both encoder types: 30 detents per 15 pulses of 4 edges
SETTLE_S = 0.001           # a pulled-up column reads high after a sleep this long (boot.py waits 5 ms)
# An RP2040 PADS_BANK0 GPIO register as CircuitPython leaves it for PWMOut: IE, 4 mA, SCHMITT. Its pin reset clears
# the pull-down (common-hal/microcontroller/Pin.c:76-80), PWMOut sets IE again (pico-sdk gpio_set_function).
PAD_RESET = 0x52
FRAME_MS = 8               # the host's report interval (panel.HID_FRAME_MS)
NVM_SIZE = 4096            # microcontroller.nvm of CircuitPython's RP2040 builds (CIRCUITPY_INTERNAL_NVM_SIZE)
BOOT_MS = 1100             # code.py starts about this long after power-up: the 1 s safe-mode wait, boot.py, USB
TICKS_WRAP_MS = 1 << 16    # supervisor.ticks_ms starts at 2**29 - 2**16 at power-up, so it first wraps then
RESUME_MS = 30             # a host asked to resume the bus is back this long after (USB 2.0, 7.1.7.7)


class Stop(BaseException):
    """Ends a run: its time is up, or code.py reloads (not an Exception: code.py's error handler must not catch it)"""


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
    reports each key that changed since the last one, stamped with supervisor.ticks_ms. A key held when the keypad
    starts is not reported until it is let go. reset() scans at once and reports every key held as a press; the
    next scan follows an interval later. The interval counts in whole ticks of 1/1024 s (keypad/__init__.c:92):
    0.02 s is 20 ticks, 19.53 ms. (The board scans from its tick interrupt, also in the middle of a loop pass;
    here in the first ms of the tick, between the steps of a pass.)"""

    def __init__(self, board, interval, max_events, debounce_threshold):
        self.board, self.interval, self.debounce_threshold = board, interval, debounce_threshold
        self.interval_ticks = int(interval * 1024)
        self.events, self.resets = EventQueue(max_events), 0
        self.state = self.read()               # the keys as the last scan read them
        self.next_scan = board.raw_ticks() + self.interval_ticks
        board.keypads.append(self)

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
    """usb_hid.Device. send_report checks the report's length and waits for the endpoint the joysticks share, as
    CircuitPython's does (shared-module/usb_hid/Device.c:200-225); the board's host takes the report at its next
    poll. With the host away it waits up to 2 s for it; then, if the host has the bus suspended, it asks it to
    resume (which the host does if it allows the panel to wake it) and returns, else it raises OSError."""

    def __init__(self, board, *, report_descriptor, usage_page, usage, report_ids, in_report_lengths,
                 out_report_lengths):
        self.board, self.report_descriptor, self.usage_page, self.usage = board, report_descriptor, usage_page, usage
        self.report_ids, self.in_report_lengths, self.out_report_lengths = report_ids, in_report_lengths, \
            out_report_lengths
        self.tries = board.log()               # ms of every call
        board.created.append(self)

    def send_report(self, report, report_id=None):
        b, t = self.board, self.board.t
        if len(report) != self.in_report_lengths[0]:
            raise ValueError(f"report length must be {self.in_report_lengths[0]}")
        self.tries.append(t)
        end = t + 2000
        while not b.usb_connected and b.t < end:
            b.advance(1)
        if not b.usb_connected:
            if not b.suspended:
                raise OSError("USB busy")
            if b.wakeup:                       # remote wakeup: the host resumes the bus
                b.suspend = (b.suspend[0], b.t + RESUME_MS)
            return
        if b.busy:                             # a host that does not take it: fails after b.block ms
            b.busy -= 1
            b.advance(b.block)
            raise OSError("USB busy")
        b.advance(max(b.taken - b.t, 0))       # the endpoint still holds the last report until the host's poll
        b.taken = (b.t // FRAME_MS + 1) * FRAME_MS
        b.take(b.taken, self, bytes(report))
        b.advance(b.waits.pop(t, 0))


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
        self.busy = 0                          # sends that fail next, whichever device sends
        self.block = 0                         # ms a failing send waits before it fails (2000 on the board)
        self.waits = {}                        # ms: how much longer a good send in that pass waits for the host
        self.usb_from, self.usb_gap = 0, (0, 0)   # the host has the panel mounted from this ms, not within the gap
        self.suspend = (0, 0)                  # from, to: the ms the host has the bus suspended
        self.wakeup = True                     # the host lets the panel ask it to resume (remote wakeup)
        self.rgb_status_brightness = 0xFF      # supervisor.runtime's, as at power-up (status_leds.c:90)
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
            "microcontroller": SimpleNamespace(pin=pins, nvm=self.nvm),
            "pwmio": SimpleNamespace(PWMOut=partial(PWMOut, self)),
            "rotaryio": SimpleNamespace(IncrementalEncoder=partial(IncrementalEncoder, self)),
            "storage": SimpleNamespace(disable_usb_drive=self.call("disable_usb_drive")),
            # supervisor.runtime.usb_connected is Board.usb_connected
            "supervisor": SimpleNamespace(runtime=self, reload=self.reload, ticks_ms=self.ticks_ms,
                                          set_usb_identification=self.call("set_usb_identification")),
            "time": SimpleNamespace(monotonic_ns=lambda: (self.t + BOOT_MS) * 1_000_000, sleep=self.sleep),
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

    def raw_ticks(self):
        """The ticks of 1/1024 s since power-up, which the keypads scan by"""
        return (self.t + BOOT_MS) * 1024 // 1000

    def advance(self, ms):
        for _ in range(ms):
            self.t += 1
            self.hand()
            for pad in self.keypads:
                if self.raw_ticks() >= pad.next_scan:
                    pad.scan(pad.next_scan)

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
    def suspended(self):
        return self.suspend[0] <= self.t < self.suspend[1]

    @property
    def usb_connected(self):
        """supervisor.runtime.usb_connected: mounted and not suspended"""
        return self.t >= self.usb_from and not self.usb_gap[0] <= self.t < self.usb_gap[1] and not self.suspended

    def take(self, ms, device, report):
        """The host takes a report from a device at ms"""
        self.received.append((ms, device, report))

    def enable(self, devices, boot_device=0):
        self.devices[:] = devices
        self.boot_device = boot_device

    @property
    def keyboard(self):
        """Whether boot.py made the keyboard (keyboard mode) instead of the joysticks"""
        return bool(self.devices) and self.devices[0].usage == 0x06

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
        self.until = until
        with suppress(Stop):
            self.exec("code.py", edits)
        return self
