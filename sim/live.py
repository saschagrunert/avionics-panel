"""The panel in real time, for the uhid output (sim/uhid.py) and later the panel page: the same Board as the tests,
with code.py in a thread of its own, paced to the wall clock.

    live = Live()                        # plugged in: boot.py has run
    live.act("tap", "AP")                # from any thread, before start() or after
    live.start(output)                   # code.py starts; output(device, report) gets every report the host takes
    live.light("SHIFT")                  # the light's duty now, 0 to 0xFFFF
    live.idle()                          # the actions have run and their reports are out
    live.stop()

act() takes Sim's actions by their names (press, release, tap, tilt, turn, wait), with the same inputs and timing,
and queues them: each starts when the ones before it have ended, or at once if they have. press, release and
`turn ring n 0` take no time, so the next action follows at once; tap, tilt, wait and a turn with its default
spacing take theirs. A report goes to output as device 1 or 2 and its bytes, the report ID first, at the ms the
host takes it.

An error in code.py's loop goes as on the board: its handler releases every button, prints the error (to stderr,
and kept in printed), waits 2 s and reloads, and code.py starts again on the same board. boot.py does not run
again and the switches held stay held. Anything else that ends code.py, and an error in an action queued with
do() or in the output, ends the thread: stop(), idle(), act() and do() raise it from then on.
"""
import math
import queue
import threading
import time
import traceback
from collections import deque
from functools import partial
from types import SimpleNamespace

from sim import LIGHTS, PASS_MS, Sim
from sim.hardware import Board, Stop

ACTIONS = ("press", "release", "tap", "tilt", "turn", "wait")
BEHIND_S = 0.005     # further behind the wall clock than this (a stall): go on from now, without a burst that would
                     # squeeze the pulses below a poll of the PC
# from an action until its last report is out: a scan (panel.KEY_SCAN_MS 20), the bounce window of a release
# (BOUNCE_MS 30), a pass (3) and up to four frames of the endpoint the devices share (32), with room
SETTLE_MS = 100
KEEP = 16            # the records kept of each kind (the last sends, light writes, sleeps, reloads, errors)


class Live(Board):
    def __init__(self, speed=1):
        """Plugs the panel in: boot.py runs. speed: ms of the panel per ms of the wall clock."""
        super().__init__(work_ms=PASS_MS - 1, log=partial(deque, maxlen=KEEP))
        self.speed, self.output, self.error, self.thread = speed, None, None, None
        self.actions, self.free, self.stopping = queue.SimpleQueue(), 0, threading.Event()
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
        """Waits until the actions queued before have run and their reports are out (SETTLE_MS after the last; a
        fast turn's queued detents can run on longer). False on a timeout."""
        done = threading.Event()
        self.queue({SETTLE_MS: [lambda b: done.set()]}, 0)
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

    def take(self, ms, device, report):
        n, data = self.devices.index(device) + 1, bytes(device.report_ids[:1]) + report
        self.script.setdefault(ms, []).append(lambda b: self.output(n, data))
