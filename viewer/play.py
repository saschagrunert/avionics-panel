"""The panel in the browser, without the simulator's program: what code.py's loop does round panel.py, for the
page's in-browser panel (viewer/play.js, which runs this with the firmware's panel.py and buttonmap.py in
MicroPython). Plain Python of the firmware's kind, so the tests run it on CPython too (tests/test_play.py, which
compare it with code.py on the simulator's stand-ins).

    play = Play(legends, knobs)     # geometry.js's key_legends and knob names, as JSON
    play.hello()                    # what sim.page's stream says first (JSON)
    play.act("press AP", t)         # an action of the page, as sim.page's act takes it, at the page's ms t
    play.step(t)                    # the loop passes up to ms t: the new state (JSON), or "" if nothing changed
    play.idle()                     # whether nothing changes before the next input: play.js steps less often then
    play.close(t)                   # the page has gone: everything it holds goes up

Of code.py: a loop pass every PASS_MS hands the panel the switches changed since the last one, at the ms they
changed (code.py's key scans), then the detents turned (turns()), ticks it, and reads the lights and both
joysticks' reports; a switch that changes to what the panel has already is dropped, as code.py's Source drops it.
The lights are code.py's duties as a share of full on: SHIFT dim is a quarter (SHIFT_DUTY). There is no USB: the
host is always there, so the lights are never dark, and nothing goes to vJoy or MobiFlight.
Of sim.live and sim.page: the actions (press NAME, release NAME, turn RING DETENTS, TURN_MAX detents at most), a
switch that changes no sooner than PRESS_MIN_MS after its last change, as a finger does, and the state the page
shows (sim.page's Page.state()). An error in the panel restarts it, as code.py's handler reloads code.py, with
the switches held up for it, and the next state says what failed ("fault").
Where it differs from code.py: changes that come in the same ms go to the panel in the order they came, where
the board's key scan puts SHIFT first within a scan and the matrix before FREQ_PUSH; there are no key scans,
USB or keypad overflows (code.py's release(), stalled(), keep_steps() and dark); and a restart after an error is
at once, where code.py waits 2 s. tests/test_play.py lists what code.py's loop does and what of it this mirrors.
"""
import json

import buttonmap as BM
import panel as P

PASS_MS = 3          # a loop pass (sim.PASS_MS)
PRESS_MIN_MS = 50    # a switch changes no sooner than this after its last change (sim.live.PRESS_MIN_MS)
DETENTS = 30         # a turn of a knob (sim.live.DETENTS) ...
TURN_MAX = DETENTS   # ... and the detents of one action at most (sim.live.TURN_MAX)
QUIET_MS = 1000      # the panel is idle no sooner than this after the last input
SHIFT_SHARE = (0, 0.25, 1)    # the SHIFT light's duty at each panel level, as a share of full (code.py's SHIFT_DUTY)
FREQ_NAMES = tuple(steps[0].split("_")[0] for steps in P.FREQ_MODES)   # COM, NAV, ADF (sim.FREQ_NAMES)
TILT = {"UP": "RANGE_A", "LEFT": "RANGE_B", "DN": "RANGE_C", "RIGHT": "RANGE_D"}   # sim.TILT
SWITCHES = tuple(name for row in BM.MATRIX for name in row) + ("FREQ_PUSH",)        # sim.hardware.SWITCHES


def key_name(label):
    """A cap's legend -> its firmware name (sim.key_name)"""
    if label == "D→":
        return "DIRECT"
    return label.replace(" ⇆", "_SWAP").replace(" ", "")


def inputs(legends, knobs):
    """The firmware's names of the caps and knobs geometry.js draws, as sim.page's inputs() gives them: legends its
    key_legends (rows of [legend, ...]), knobs its knobs' names"""
    out = {"keys": {}, "knobs": {}}
    for row in legends:
        for entry in row:
            out["keys"][entry[0]] = key_name(entry[0])
    for knob in knobs:
        if knob == "RANGE":
            out["knobs"][knob] = {"ring": "RANGE", "push": "RANGE_COM", "tilt": TILT}
        else:
            out["knobs"][knob] = {"outer": knob + "_OUTER", "inner": knob + "_INNER", "push": knob + "_PUSH"}
    return out


def version():
    """The commit of the firmware's files (version.py, as the Pages workflow fills it in), or None for a git
    checkout's placeholder or no file"""
    try:                             # a file missing, cut short or of another shape costs the line only, as in code.py
        from version import VERSION
    except Exception:
        return None
    text = str(VERSION)
    return None if text.startswith("$") else text


class Play:
    def __init__(self, legends="[]", knobs="[]"):
        self.inputs = inputs(json.loads(legends), json.loads(knobs))
        self.t = 0                   # ms of the last pass
        self.changes = {}            # switch -> ms of its last change, as the page asked for it
        self.waiting = []            # [ms, name, down or detents] in order: changes and turns for the passes to come
        self.held = set()            # switches the page holds down
        self.input_at = -QUIET_MS    # ms of the last action
        self.fault = None            # what failed, for the next state
        self.shown = None            # what the state last given showed
        self.start()

    def start(self):
        self.panel = P.Panel()
        self.down = set()            # switches the panel has down (code.py's Source.down)
        self.reports = {1: bytearray(BM.SIZE[1] // 8), 2: bytearray(BM.SIZE[2] // 8)}

    def hello(self):
        """What sim.page's stream says first, for sim.js: no client of a server, no build to reload for, no legend.
        The next step() gives the state, changed or not: the page has none yet."""
        self.shown = self.fault = None               # (a fault of a stopped panel is not this one's)
        return json.dumps({"client": "browser", "build": None, "version": version(), "inputs": self.inputs,
                           "legend": None, "detents": DETENTS, "turn_max": TURN_MAX})

    def act(self, line, t):
        """One of the page's actions at ms t; ValueError for a wrong one"""
        words = line.split()
        self.input_at = max(self.input_at, t)
        if len(words) == 2 and words[0] in ("press", "release") and words[1] in SWITCHES:
            name, down = words[1], words[0] == "press"
            at = max(t, self.changes.get(name, t - PRESS_MIN_MS) + PRESS_MIN_MS)
            self.changes[name] = at
            (self.held.add if down else self.held.discard)(name)
            self._wait(at, name, down)
        elif len(words) == 3 and words[0] == "turn" and words[1] in P.RINGS:
            detents = int(words[2])
            if not 0 < abs(detents) <= TURN_MAX:
                raise ValueError(f"turn RING DETENTS: 1 to {TURN_MAX} detents either way")
            self._wait(t, words[1], detents)
        else:
            raise ValueError("actions: press NAME, release NAME, turn RING DETENTS")

    def _wait(self, ms, name, what):
        i = len(self.waiting)
        while i and self.waiting[i - 1][0] > ms:
            i -= 1
        self.waiting.insert(i, [ms, name, what])

    def close(self, t):
        """The page has gone: what it holds goes up (sim.page's disconnect)"""
        for name in sorted(self.held):
            self.act("release " + name, t)

    def step(self, t):
        """The loop passes up to ms t, PASS_MS apart, then the state if it changed since the last one given, else
        \"\". An error in any of it, the lights and reports included, restarts the panel, as code.py's handler
        reloads code.py (here at once, not after 2 s), and the new panel's state names it; an error in that state
        too goes to the caller."""
        try:
            while self.t + PASS_MS <= t:
                self.t += PASS_MS
                self._pass(self.t)
            return self._state()
        except Exception as e:       # code.py's handler: everything up, and the panel starts again
            self.fault = f"{type(e).__name__}: {e}"
            self.start()
            return self._state()

    def _state(self):
        """The state if it changed since the last one given, else \"\""""
        panel, t = self.panel, self.t
        shown = (panel.shift_level(t), panel.unit_light, panel.freq_lit(t), panel.unit, panel.freq_mode,
                 bytes(self.reports[1]), bytes(self.reports[2]))
        if shown == self.shown and self.fault is None:
            return ""
        self.shown = shown
        state = self.read()
        if self.fault is not None:
            state["fault"], self.fault = self.fault, None
        return json.dumps(state)

    def idle(self):
        """Whether the state stays as it is until the next input: nothing held, waiting or pressed, no repeat, no
        SHIFT, no FREQ count, hold or ADF blink, and no input for QUIET_MS. The passes run as before whatever the
        answer (step() runs them up to now), so a wrong one only shows a change late."""
        panel, t = self.panel, self.t
        return (t - self.input_at >= QUIET_MS and not self.waiting and not self.held and not self.down
                and not panel.pending and not panel.shown and not panel.order and not panel.repeat
                and panel.freq_since is None and panel.shift_down is None and not panel.shift_active(t)
                and panel.freq_mode != 2 and panel._mode_from()[1] <= t and panel.lit_at < t)

    def _pass(self, t):
        """A pass of code.py's loop at ms t: the keys (read_keys), then the knobs (turns), the tick, the reports"""
        panel, turns = self.panel, []
        while self.waiting and self.waiting[0][0] <= t:
            ms, name, what = self.waiting.pop(0)
            if name in P.RINGS:
                turns.append((name, what))
            elif what != (name in self.down):
                (self.down.add if what else self.down.discard)(name)
                panel.key(name, what, t, ms)
        for ring, detents in turns:
            panel.turn(ring, detents, t)
        panel.tick(t)
        for n in self.reports:
            panel.fill_report(n, self.reports[n])

    def read(self):
        """The state as sim.page's Page.state() gives it: the lights (code.py's duties as a share of full on), the
        unit, the FREQ mode and each joystick's buttons by name"""
        panel, t = self.panel, self.t
        buttons = {}
        for n in self.reports:
            report = self.reports[n]
            buttons[str(n)] = [name for b, name in enumerate(BM.DEVICE[n]) if report[b >> 3] >> (b & 7) & 1]
        return {"lights": {"SHIFT": SHIFT_SHARE[panel.shift_level(t)], "UNIT": 1 if panel.unit_light else 0,
                           "FREQ": 1 if panel.freq_lit(t) else 0},
                "unit": panel.unit, "freq": FREQ_NAMES[panel.freq_mode], "buttons": buttons}
