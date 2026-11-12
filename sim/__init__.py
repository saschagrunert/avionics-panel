"""The panel without the hardware: the firmware's own files (boot.py, code.py, panel.py, buttonmap.py) on the
stand-in hardware of sim/hardware.py, on virtual time.

A Sim is a scenario. Each action happens at the scenario's current ms, `now`, which starts at START_MS after
code.py's start and only moves on, with wait() and with the actions that take time. Reading what the PC saw runs
boot.py and code.py up to `now`; after more actions it runs them again from the start, which gives the same
result for the part before. An error in code.py's loop is raised, not hidden by the reload code.py does on the
board.

    sim = Sim()
    sim.turn("FREQ_INNER", 2)
    sim.tap("COM_SWAP")
    sim.presses(1)      # ["COM_KHZ_UP", "COM_KHZ_UP", "COM_SWAP"]

Inputs go by their firmware names: the keys, pushes and RANGE switches as in buttonmap.MATRIX plus FREQ_PUSH
(COM1 is COM 1, COM_SWAP is COM ⇆, DIRECT is D→, ALTHDG_PUSH the ALT/HDG push, RANGE_COM the RANGE centre), the
rings as in code.py's RINGS (FREQ_INNER); key_name() gives a cap's from its legend. Buttons go by their BUTTONS.md
names.

Sim(keyboard=True) runs the keyboard mode (keys.py), from after its start pattern. The keyboard is device 1 there:
typed() reads the functions its shortcuts stand for, and buttons(), presses() and held() name them too, each
shared shortcut by the function it stands for (canonical()).
"""
from sim.hardware import BM, RINGS, SWITCHES, Board, keys

START_MS = 107       # the scenario starts this long after code.py, off the keypads' 20 ms scans
PATTERN_MS = 960     # ... and this much later in keyboard mode, after its start pattern (keys.START, 6 x 152 ms
                     # here): a multiple of the 3 ms pass and the 20 ms key scan, so it meets both in the same phase
PASS_MS = 3          # a loop pass: its 1 ms sleep plus its own run time (a few ms, docs/using/controls.md)
TAP_MS = 100         # a tap holds a key or push this long ...
PAUSE_MS = 300       # ... and the next action follows this long after its release
DETENT_MS = 150      # a slow turn: time between detents (the coarse step needs less than panel.FAST_MS)
POLL_MS = 31.25      # MobiFlight reads the joysticks this often (panel.POLL_MS rounds it up) ...
POLL_OFFSET_MS = 11  # ... first at this ms
# a RANGE tilt closes "com" and its direction: away from the pilot A, left B, towards C, right D (Alps drawing)
TILT = {"UP": "RANGE_A", "LEFT": "RANGE_B", "DN": "RANGE_C", "RIGHT": "RANGE_D"}
LIGHTS = ("SHIFT", "UNIT")
# (modifiers, key) -> (device, button name): what each shortcut of the keyboard mode stands for. A shortcut that
# buttons share (keys.py) stands for the first of them: device 1's, a key's plain function.
FUNCTIONS = {}
for _dev, _names in BM.DEVICE.items():
    for _b, _name in enumerate(_names):
        FUNCTIONS.setdefault(keys.shortcut(_dev, _b), (_dev, _name))
MODIFIERS = keys.LC | keys.LS | keys.LA | keys.RC | keys.RS


def canonical(device, name):
    """The function a button's shortcut stands for in keyboard mode: the button itself, or the one it shares its
    shortcut with"""
    return FUNCTIONS[keys.shortcut(device, BM.BUTTON[device][name])]


def key_name(label):
    """A cap's legend (mech/stack.py's KEY_LEGENDS) -> its firmware name: COM ⇆ -> COM_SWAP, D→ -> DIRECT,
    MIC 1 -> MIC1"""
    return {"D→": "DIRECT"}.get(label, label.replace(" ⇆", "_SWAP").replace(" ", ""))


def typed(reports):
    """(ms, device, name) of every function a run of keyboard reports (ms, report) types, in order. ValueError for
    what a host could take for another shortcut: two keys at once, modifiers that change under a key or as it goes
    down, or a shortcut of no function. (Everything may go up at once.)"""
    out, last = [], bytes(keys.REPORT)
    for ms, r in reports:
        if len(r) != keys.REPORT or r[1] or any(r[3:]) or r[0] & ~MODIFIERS:
            raise ValueError(f"{ms} ms: not one key and its modifiers: {r.hex()}")
        if r[0] != last[0] and r[2]:
            raise ValueError(f"{ms} ms: the modifiers change with a key down: {last.hex()} to {r.hex()}")
        if r[2] and r[2] != last[2]:
            if last[2]:
                raise ValueError(f"{ms} ms: one key replaces another: {last.hex()} to {r.hex()}")
            if (r[0], r[2]) not in FUNCTIONS:
                raise ValueError(f"{ms} ms: a shortcut of no function: {r.hex()}")
            out.append((ms, *FUNCTIONS[r[0], r[2]]))
        last = r
    return out


class Sim:
    def __init__(self, keyboard=False):
        self.keyboard, self.pass_ms, self.script, self.board = keyboard, PASS_MS, {}, None
        self.now = START_MS + (PATTERN_MS if keyboard else 0)

    def _at(self, ms, action):
        self.script.setdefault(ms, []).append(action)
        self.board = None

    # ---------------- the pilot ----------------
    def wait(self, ms):
        if ms < 0:
            raise ValueError("time only moves on")
        if ms:
            self.now += ms
            self.board = None

    def press(self, name):
        """A key, push or RANGE switch (SWITCHES) goes down"""
        self._switch(name, True)

    def release(self, name):
        self._switch(name, False)

    def _switch(self, name, down):
        if name not in SWITCHES:
            raise ValueError(f"no switch {name!r}")
        self._at(self.now, lambda b: b.hold(name, down))

    def tap(self, name, hold=TAP_MS, then=PAUSE_MS):
        self.press(name)
        self.wait(hold)
        self.release(name)
        self.wait(then)

    def tilt(self, way, hold=TAP_MS, then=PAUSE_MS):
        """Tilts RANGE "UP" (away), "DN", "LEFT" or "RIGHT", and lets it go after hold ms"""
        if way not in TILT:
            raise ValueError(f"no tilt {way!r}")
        for name in ("RANGE_COM", TILT[way]):
            self.press(name)
        self.wait(hold)
        for name in ("RANGE_COM", TILT[way]):
            self.release(name)
        self.wait(then)

    def turn(self, ring, detents, every=DETENT_MS):
        """Turns a ring (RINGS) by detents, clockwise positive, one detent every `every` ms from now (0: all in
        the same ms); now moves on by detents x every"""
        if ring not in RINGS:
            raise ValueError(f"no ring {ring!r}")
        if every < 0:
            raise ValueError("time only moves on")
        step = 1 if detents > 0 else -1
        for i in range(abs(detents)):
            self._at(self.now + i * every, lambda b: b.turn(ring, step))
        self.wait(abs(detents) * every)

    # ---------------- what the PC sees ----------------
    def _board(self):
        """The board after boot.py and code.py ran up to now. An error in code.py is raised: its handler prints it
        (the stand-in keeps it) before it waits and reloads, so also when the run ends before the reload."""
        if self.board is None:
            board = Board(self.script, work_ms=self.pass_ms - 1, keyboard=self.keyboard).boot().run(self.now)
            if board.printed:
                raise board.printed[0]
            self.board = board
        return self.board

    def reports(self, device):
        """(ms, bytes) of every report the PC took from device 1 or 2 before now, as on the wire: the report ID (a
        joystick's), then one bit per button, or the keyboard's 8 bytes"""
        dev = self._board().devices[device - 1]
        return [(ms, bytes(i for i in dev.report_ids[:1] if i) + data) for ms, d, data in self.board.received
                if d is dev and ms < self.now]

    def buttons(self, device):
        """(ms, names) of every report from device 1 or 2: the buttons pressed, by name, in button order. In
        keyboard mode the keyboard's reports, with the function of the shortcut down if it is one of device's."""
        if self.keyboard:
            out = []
            for ms, r in self.reports(1):
                dev, name = FUNCTIONS.get((r[0], r[2]), (None, None))
                out.append((ms, [name] if dev == device else []))
            return out
        return [(ms, [BM.DEVICE[device][b] for b in range(8 * len(r) - 8) if r[1 + b // 8] >> b % 8 & 1])
                for ms, r in self.reports(device)]

    def typed(self):
        """(ms, device, name) of every function the keyboard typed before now (keyboard mode), as typed() reads them"""
        return typed(self.reports(1))

    def _polls(self, device):
        """(ms, buttons pressed) at each of MobiFlight's polls before now"""
        reports, out, names, k, t = self.buttons(device), [], [], 0, POLL_OFFSET_MS
        while t < self.now:
            while k < len(reports) and reports[k][0] <= t:
                names = reports[k][1]
                k += 1
            out.append((t, names))
            t += POLL_MS
        return out

    def polled(self, device):
        """(ms of the poll, name) of every button of device 1 or 2 MobiFlight saw go down, in order: a press that
        falls between two of its polls is not among them"""
        out, before = [], []
        for t, names in self._polls(device):
            out += [(t, n) for n in names if n not in before]
            before = names
        return out

    def presses(self, device):
        """The buttons of device 1 or 2 MobiFlight saw go down, in order"""
        return [n for _, n in self.polled(device)]

    def held(self, device):
        """The buttons of device 1 or 2 down at MobiFlight's last poll before now"""
        polls = self._polls(device)
        return polls[-1][1] if polls else []

    def light(self, name):
        """(ms, duty) of every duty written to the "SHIFT" or "UNIT" light before now, after the keyboard mode's
        start pattern (one duty per light and step)"""
        history = self._board().leds[LIGHTS.index(name)].history[len(keys.START) if self.keyboard else 0:]
        return [(ms, d) for ms, d in history if ms < self.now]
