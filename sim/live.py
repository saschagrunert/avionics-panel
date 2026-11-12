"""The panel in real time, for the uhid output (sim/uhid.py) and the panel page (sim/page.py): the same Board as
the tests, with code.py in a thread of its own, paced to the wall clock.

    live = Live()                        # plugged in: boot.py has run (Live(keyboard=True): in keyboard mode)
    live.act("tap", "AP")                # from any thread, before start() or after
    live.start(output)                   # code.py starts; output(device, report) gets every report the host takes
    live.light("SHIFT")                  # the light's duty now, 0 to 0xFFFF
    live.idle()                          # the actions have run and their reports are out
    live.stop()

act() takes Sim's actions by their names (press, release, tap, tilt, turn, wait), with the same inputs and timing,
and queues them: each starts when the ones before it have ended, or at once if they have. press, release and
`turn ring n 0` take no time, so the next action follows at once; tap, tilt, wait and a turn with its default
spacing take theirs. parse() reads an action from a line of text, as the page sends them and from_stdin() reads
them for sim.uhid and sim.vjoy. A switch changes no sooner than PRESS_MIN_MS after its last change, on the
panel's clock, as a finger does: a click shorter than a key scan would be lost, and clicks that reach a panel
running late all at once would be one press (code.py takes a gap that short for a bounce). A report goes to
output as device 1 or 2 and its bytes as on the wire, at the ms the host takes it: a joystick's report ID first,
and in keyboard mode device 1, the keyboard, with its 8 bytes and no report ID.

An error in code.py's loop goes as on the board: its handler releases every button, prints the error (to stderr,
and kept in printed), waits 2 s and reloads, and code.py starts again on the same board. boot.py does not run
again and the switches held stay held. Anything else that ends code.py, and an error in an action queued with
do() or in the output, ends the thread: stop(), idle(), act() and do() raise it from then on.
"""
import math
import queue
import re
import sys
import threading
import time
import traceback
from collections import deque
from functools import partial
from types import SimpleNamespace

from sim import LIGHTS, PASS_MS, TILT, Sim
from sim.hardware import RINGS, SWITCHES, Board, Stop

ACTIONS = ("press", "release", "tap", "tilt", "turn", "wait")
USAGE = {"press": "press NAME", "release": "release NAME", "tap": "tap NAME [HOLD_MS]",
         "tilt": "tilt UP|DN|LEFT|RIGHT [HOLD_MS]", "turn": "turn RING DETENTS [EVERY_MS]", "wait": "wait MS"}
# the names each field takes, and what they are
NAMES = {"NAME": ("switch", SWITCHES), "RING": ("ring", RINGS), "UP|DN|LEFT|RIGHT": ("tilt", TILT)}
TURN_MAX = 30        # detents in one action at most: a turn of the knob
PRESS_MIN_MS = 50    # more than two key scans (panel.KEY_SCAN_MS 20)
BEHIND_S = 0.005     # further behind the wall clock than this (a stall): go on from now, without a burst that would
                     # squeeze the pulses below a poll of the PC
# from an action until its last report is out: a scan (panel.KEY_SCAN_MS 20), the bounce window of a release
# (BOUNCE_MS 30), a pass (3) and up to four frames of the endpoint the devices share (32), with room
SETTLE_MS = 100
KEEP = 16            # the records kept of each kind (the last sends, light writes, sleeps, reloads, errors)
LINES = {**USAGE, "lights": "lights"}   # what from_stdin() takes


def parse(line, usage=USAGE):
    """(action, arguments) of a line in one of usage's forms, such as `tap AP 500`; None for a blank line.
    ValueError with the usage for a wrong one, also for a name the panel does not have and a turn of more than
    TURN_MAX detents."""
    words = line.split()
    if not words:
        return None
    if words[0] not in usage:
        raise ValueError("actions: " + ", ".join(usage.values()))
    form = usage[words[0]]
    fields = [f.strip("[]") for f in form.split()[1:]]
    if not form.count(" ") - form.count("[") <= len(words) - 1 <= len(fields):
        raise ValueError(f"usage: {form}")
    args = []
    for field, word in zip(fields, words[1:], strict=False):
        if field in NAMES:
            if word not in NAMES[field][1]:
                raise ValueError(f"usage: {form} (the panel has no {NAMES[field][0]} {word!r})")
        elif not re.fullmatch(r"-?[0-9]+", word):
            raise ValueError(f"usage: {form} ({field} is a whole number)")
        elif field == "DETENTS" and abs(int(word)) > TURN_MAX:
            raise ValueError(f"usage: {form} ({TURN_MAX} detents at most)")
        args.append(word if field in NAMES else int(word))
    return words[0], args


def from_stdin(live, output, prog):
    """Runs live into output (its send and close) on the actions read from stdin, one per line (LINES), until the
    input ends; `lights` prints both lights' duty once the actions before it have taken effect. Exits with prog's
    message when the panel stops."""
    sys.stdin.reconfigure(errors="replace")
    live.start(output.send)
    try:
        try:
            for line in sys.stdin:
                try:
                    action = parse(line, LINES)
                    if action and action[0] == "lights":
                        live.act("wait", SETTLE_MS)
                        live.do(lambda b: print(f"SHIFT {b.light('SHIFT'):#06x} UNIT {b.light('UNIT'):#06x}",
                                                flush=True))
                    elif action:
                        live.act(action[0], *action[1])
                except ValueError as e:
                    print(f"{line.strip()}: {e}", file=sys.stderr)
            live.idle()
        finally:
            try:
                live.stop()
            finally:
                output.close()
    except KeyboardInterrupt:
        pass
    except Exception as e:                             # the panel stopped: the output or code.py itself failed
        sys.exit(f"{prog}: {e.__cause__ or e}")


class Live(Board):
    def __init__(self, speed=1, keyboard=False):
        """Plugs the panel in: boot.py runs. speed: ms of the panel per ms of the wall clock. keyboard: the
        keyboard mode is stored, as after a plug-in with HOME (UNIT) held."""
        super().__init__(work_ms=PASS_MS - 1, log=partial(deque, maxlen=KEEP), keyboard=keyboard)
        self.speed, self.output, self.error, self.thread = speed, None, None, None
        self.actions, self.free, self.stopping = queue.SimpleQueue(), 0, threading.Event()
        self.changes = {}                      # the ms of each switch's last change
        self.modules["traceback"] = SimpleNamespace(print_exception=self.print_exception)
        self.boot()

    def print_exception(self, e):
        self.printed.append(e)
        traceback.print_exception(e)

    # ---------------- any thread ----------------
    def act(self, name, *args, **kwargs):
        """Queues Sim's action name (ACTIONS) with its arguments. A wrong input raises here."""
        if name not in ACTIONS:
            raise ValueError(f"no action {name!r}")
        pilot = Sim()
        pilot.now = 0
        getattr(pilot, name)(*args, **kwargs)
        self.queue(pilot.script, pilot.now)

    def do(self, action):
        """Queues action(board), run in code.py's thread"""
        self.queue({0: [action]}, 0)

    def queue(self, script, length):
        self.check()
        self.actions.put((script, length))

    def check(self):
        """Raises once the thread has ended"""
        if self.error:
            raise RuntimeError(f"the panel stopped: {self.error!r}") from self.error
        if self.stopping.is_set() or self.thread and not self.thread.is_alive():
            raise RuntimeError("the panel stopped")

    def idle(self, timeout=None):
        """Waits until the actions queued before have run and their reports are out (SETTLE_MS after the last, or
        after a switch change that waits for PRESS_MIN_MS; a fast turn's queued detents can run on longer). False on
        a timeout."""
        done = threading.Event()

        def settle(b):
            last = max([b.t, *b.changes.values()])         # (no switch may have changed yet)
            b.script.setdefault(last + SETTLE_MS, []).append(lambda b: done.set())
        self.do(settle)
        end = math.inf if timeout is None else time.monotonic() + timeout
        while not done.wait(min(0.05, max(end - time.monotonic(), 0))):
            self.check()
            if time.monotonic() >= end:
                return False
        return True

    def light(self, name):
        """The duty of the "SHIFT" or "UNIT" light now (0 until code.py has made it)"""
        leds = self.leds
        return leds[LIGHTS.index(name)].duty_cycle if len(leds) == len(LIGHTS) else 0

    def start(self, output):
        if self.thread:
            raise RuntimeError("started already")
        self.output = output
        self.thread = threading.Thread(target=self.main, name="code.py", daemon=True)
        self.thread.start()
        return self

    def stop(self, timeout=5):
        """Unplugs the panel: code.py stops where it is"""
        self.stopping.set()
        if self.thread:
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise TimeoutError(f"code.py still runs after {timeout} s")
        if self.error:
            raise self.error

    # ---------------- code.py's thread ----------------
    def main(self):
        self.start_s = time.monotonic()            # code.py's 0 ms
        try:
            while not self.stopping.is_set():      # a reload starts code.py again, which makes its own keypads
                self.keypads, self.encoders, self.leds = [], [], []
                self.run(math.inf)
        except BaseException as e:                 # an error outside code.py's loop: the board stops there too
            self.error = e

    def hand(self):
        if self.stopping.is_set():
            raise Stop
        ahead = self.start_s + self.t / 1000 / self.speed - time.monotonic()
        if ahead > 0:
            time.sleep(ahead)
        elif ahead < -BEHIND_S:
            self.start_s -= ahead
        while not self.actions.empty():
            script, length = self.actions.get()
            start = max(self.t, self.free)
            for ms, actions in script.items():
                self.script.setdefault(start + ms, []).extend(actions)
            self.free = start + length
        for action in self.script.pop(self.t, ()):
            try:
                action(self)
            except Exception as e:                 # a queued action or the output, not code.py: ends the run
                self.error = e
                self.stopping.set()
                raise Stop from e

    def hold(self, name, down):
        """A switch closes or opens PRESS_MIN_MS after its last change at the soonest, so also after its changes
        still waiting"""
        at = max(self.t, self.changes.get(name, -PRESS_MIN_MS) + PRESS_MIN_MS)
        self.changes[name] = at
        if at > self.t:
            self.script.setdefault(at, []).append(lambda b: Board.hold(b, name, down))
        else:
            super().hold(name, down)

    def take(self, ms, device, report):
        n, data = self.devices.index(device) + 1, bytes(i for i in device.report_ids[:1] if i) + report
        self.script.setdefault(ms, []).append(lambda b: self.output(n, data))
