"""The panel that plays in the browser alone (viewer/play.py, which viewer/play.js runs in MicroPython with the
firmware's panel.py and buttonmap.py), here on CPython: against code.py on the simulator's stand-ins (sim.Sim), the
same input gives the same lights and buttons, in the same order and within a key scan and a few USB frames of the
same times; and its names and numbers are the simulator's. tests/test_simjs.py plays it in a browser."""
import ast
import json
import os
import re
import sys
import types

import pytest

import sim
import sim.page
from conftest import ROOT, load
from sim import LIGHTS, Sim
from sim.hardware import SWITCHES
from sim.live import DETENTS, PRESS_MIN_MS, TURN_MAX

play = load("play", "viewer/play.py")

# a key scan (code.py reads a switch up to 19.5 ms after it changed), a loop pass and two of the host's 8 ms frames
# (Sim reads the reports the host took; play.py the panel's): how far apart the two may show the same change
LATE_MS = play.P.KEY_SCAN_MS + 2 * play.P.HID_FRAME_MS + play.PASS_MS + 1
# What code.py's loop does with the panel, in order, and in the functions it calls for the keys and knobs: the
# calls of panel's methods and of code.py's own functions, the panel's attributes it sets, and its sleep, each with
# its arguments as written, by code_py_loop(). Each says what play.py does with it ("mirrored": play.py does the
# same, in the same order) or why it leaves it out. A change to code.py's loop fails the test below: look at
# play.py, then write the new list here.
LOOP = (
    ("loop", "now()"),                                           # mirrored: the pass's ms (Play.t)
    ("loop", "panel.dark = not connected"),                      # left out: USB is always there, never dark
    ("loop", "input_waiting()"),                                 # left out: the wake of a host that has suspended
    ("loop", "behind()"),                                        #   the bus, and its reads
    ("loop", "show(LIGHT_OFF, False, False)"),
    ("loop", "turns(t)"),
    ("loop", "wake(t)"),
    ("loop", "now()"),
    ("loop", "read_keys(t)"),                                    # mirrored: the keys first (Play._pass) ...
    ("loop", "turns(t)"),                                        # ... then the knobs ...
    ("loop", "panel.tick(t)"),                                   # ... then the tick ...
    ("loop", "show(panel.shift_level(t), connected and panel.unit_light, connected and (panel.freq_lit(t) if leds[2] "
             "else panel.freq_mode + 1))"),                      # ... the lights (Play._state, connected) ...
    ("loop", "panel.shift_level(t)"),
    ("loop", "panel.freq_lit(t)"),
    ("loop", "panel.fill_report(n, rep)"),                       # ... and both reports
    ("loop", "now()"),                                           # left out: the sends, their back-off and a late
    ("loop", "back_off(retry)"),                                 #   send's stall (panel.stalled)
    ("loop", "now()"),
    ("loop", "panel.stalled(late)"),
    ("loop", "asked(start)"),
    ("loop", "waited(t, True)"),
    ("loop", "time.sleep(0.001)"),                               # mirrored: PASS_MS, with the pass's own run time
    ("read_keys", "ticks_diff(b.event.timestamp, a.event.timestamp)"),   # the keypads' events in scan order: play.py
                                                                         # takes them in the order they came
    ("Source.start", "panel.release(self.names[k], t)"),         # left out: a keypad overflow lets every key go
    ("Source.next", "panel.key(self.names[k], ev.pressed, t, t + ticks_diff(ev.timestamp, clock[1]))"),
                                                                 # mirrored: at the ms the switch changed
    ("Source.next", "ticks_diff(ev.timestamp, clock[1])"),
    ("turns", "panel.turn(RINGS[i][0], -d if RINGS[i][3] else d, t)"),   # mirrored
    ("waited", "now()"),                                         # left out: after a wake request, the stall and
    ("waited", "now()"),                                         #   the steps kept (panel.stalled, keep_steps)
    ("waited", "time.sleep(0.001)"),
    ("waited", "panel.stalled(now() - t)"),
    ("waited", "now()"),
    ("waited", "panel.keep_steps()"),
    ("waited", "back_off(woke)"),
)
LOOP_FUNCTIONS = ("read_keys", "Source.start", "Source.next", "turns", "waited")   # those LOOP looks into
# (ms after the one before, action): keys, knob turns and pushes, a SHIFT tap and its session, a SHIFT lock and
# its blink, UNIT (SHIFT held with HOME), a RANGE tilt and its centre push, the FREQ modes with their counts and
# ADF's blink, the squawk digit's count, and a repeat
SCENARIO = (
    (0, "press AP"), (100, "release AP"), (300, "turn FREQ_INNER 1"), (150, "turn FREQ_INNER 1"),
    (150, "turn FREQ_INNER -1"), (300, "press FREQ_PUSH"), (100, "release FREQ_PUSH"),
    (800, "press SHIFT"), (100, "release SHIFT"), (300, "turn ALTHDG_OUTER 1"), (150, "turn ALTHDG_OUTER 2"),
    (6000, "press SHIFT"), (1300, "release SHIFT"), (1200, "press HDG"), (100, "release HDG"),
    (300, "press SHIFT"), (100, "release SHIFT"),
    (500, "press SHIFT"), (0, "press HOME"), (100, "release HOME"), (0, "release SHIFT"),
    (500, "press RANGE_COM"), (0, "press RANGE_A"), (500, "release RANGE_A"), (0, "release RANGE_COM"),
    (300, "press RANGE_COM"), (100, "release RANGE_COM"), (300, "press FREQ_PUSH"), (100, "release FREQ_PUSH"),
    (2000, "press FREQ_PUSH"), (100, "release FREQ_PUSH"), (3000, "press SHIFT"), (100, "release SHIFT"),
    (300, "turn FREQ_OUTER 1"), (8000, "press UP"), (700, "release UP"), (300, "press CDI"), (50, "release CDI"),
)
END_MS = 3000        # the run goes on this long after the last action


def changes(pairs):
    """[(ms, value)] of each change in a run of (ms, value)"""
    out = []
    for ms, value in pairs:
        if not out or out[-1][1] != value:
            out.append((ms, value))
    return out


def run_sim():
    """code.py on the stand-ins: {light: [(ms, share of full)]}, {device: [(ms, buttons)]}, code.py's globals"""
    pilot = Sim()
    for wait, line in SCENARIO:
        pilot.wait(wait)
        action, name, *detents = line.split()
        if action == "turn":
            pilot.turn(name, int(detents[0]), every=0)
        else:
            getattr(pilot, action)(name)
    pilot.wait(END_MS)
    code = pilot._board().code
    full = code["LED_DUTY"]
    lights = {n: changes((ms, round(duty / full[i], 3)) for ms, duty in pilot.light(n)) for i, n in enumerate(LIGHTS)}
    return lights, {d: changes(pilot.buttons(d)) for d in (1, 2)}, code, sim.START_MS, pilot.now


def play_js(name):
    """A number of viewer/play.js: const NAME = number;"""
    with open(os.path.join(ROOT, "viewer", "play.js"), encoding="utf-8") as f:
        return int(re.search(rf"const {name} = (\d+);", f.read())[1])


STEP_MS, IDLE_MS = play_js("STEP_MS"), play_js("IDLE_MS")


def run_play(start, end, paced=False):
    """play.py fed the same actions at the same ms, stepped every ms, or with paced as play.js steps it: at once
    after an action, and STEP_MS or, while idle() says so, IDLE_MS after the step before. The same shape as
    run_sim()'s, and the number of idle steps."""
    p, events, t = play.Play(), [], start
    for wait, line in SCENARIO:
        t += wait
        events.append((t, line))
    states, ms, idle = [], 0, 0
    while ms < end:
        acted = False
        while events and events[0][0] <= ms:
            p.act(events.pop(0)[1], ms)
            acted = True
        if out := p.step(ms):
            states.append((ms, json.loads(out)))
        if not paced:
            ms += 1
            continue
        pace = IDLE_MS if p.idle() else STEP_MS
        idle += pace == IDLE_MS and not acted
        ms = min(ms + pace, events[0][0] if events else end)
    lights = {n: changes((ms, s["lights"][n]) for ms, s in states) for n in LIGHTS}
    return lights, {d: changes((ms, s["buttons"][str(d)]) for ms, s in states) for d in (1, 2)}, idle


@pytest.fixture(scope="module")
def runs():
    lights, buttons, code, start, end = run_sim()
    return (lights, buttons), run_play(start, end)[:2], code


def same(expected, got):
    assert [v for _, v in got] == [v for _, v in expected]
    late = [(a, b) for a, b in zip(expected, got, strict=True) if abs(a[0] - b[0]) > LATE_MS]
    assert not late, late


@pytest.mark.parametrize("light", LIGHTS)
def test_the_lights_follow_code_py(runs, light):
    (lights, _), (got, _), _ = runs
    assert len(lights[light]) > 1
    same(lights[light], got[light])


@pytest.mark.parametrize("device", (1, 2))
def test_the_buttons_follow_code_py(runs, device):
    (_, buttons), (_, got), _ = runs
    assert len(buttons[device]) > 1
    same(buttons[device], got[device])


def test_the_scenario_shows_what_it_is_for(runs):
    # the SHIFT light dim (the lock, the pulse before SHIFT drops), the UNIT light, the FREQ light's flashes, a
    # held UP's repeats and a button of device 2
    (lights, buttons), _, _ = runs
    assert {v for _, v in lights["SHIFT"]} == {0, 0.25, 1} and {v for _, v in lights["UNIT"]} == {0, 1}
    assert len(lights["FREQ"]) > 10
    assert sum(b == ["UP"] for _, b in buttons[1]) > 2 and ["CDI"] in [b for _, b in buttons[2]]


def test_idle_steps_show_every_change_as_soon(runs):
    # stepped as play.js steps it, IDLE_MS apart while idle, the panel shows the same changes as stepped every ms,
    # each within a step of STEP_MS: idle() is never true while something is about to change
    *_, code = runs
    start, end = sim.START_MS, sim.START_MS + sum(wait for wait, _ in SCENARIO) + END_MS
    every_ms, paced = run_play(start, end), run_play(start, end, paced=True)
    assert paced[2] > 20                                     # (idle in the quiet stretches)
    for expected, got in ((every_ms[0], paced[0]), (every_ms[1], paced[1])):
        for key in expected:
            assert [v for _, v in got[key]] == [v for _, v in expected[key]], key
            assert all(0 <= b[0] - a[0] < STEP_MS for a, b in zip(expected[key], got[key], strict=True)), key


def test_idle_is_nothing_held_lit_or_counting():
    # a key held, the QUIET_MS after an input, SHIFT armed by a tap, the lock's blink, a FREQ count, ADF's blink and
    # a held UP's repeats are not idle; each over, it is
    p, t = play.Play(), 0
    tap = ["press {0}", "release {0}"]
    for actions, ms, idle in (([], 10, True), (["press AP"], 1500, False), (["release AP"], 800, False),
                              ([], 400, True), ([a.format("SHIFT") for a in tap], 2500, False), ([], 1000, True),
                              (["press SHIFT"], 1500, False), (["release SHIFT"], 3000, False),
                              ([a.format("SHIFT") for a in tap], 1500, True),
                              ([a.format("FREQ_PUSH") for a in tap], 300, False), ([], 1500, True),   # NAV
                              ([a.format("FREQ_PUSH") for a in tap], 5000, False),                    # ADF
                              ([a.format("FREQ_PUSH") for a in tap], 2000, True),                     # COM
                              (["press UP"], 1500, False), (["release UP"], 1500, True)):
        for line in actions:
            p.act(line, t)
            t += 100
        for now in range(t, t + ms):
            p.step(now)
        t += ms
        assert p.idle() == idle, (actions, t)
    assert not p.panel.locked and p.panel.freq_mode == 0


def test_the_shift_light_is_dim_as_code_py_makes_it(runs):
    *_, code = runs
    shares = tuple(d / code["LED_DUTY"][0] for d in code["SHIFT_DUTY"])
    assert shares == play.SHIFT_SHARE


def code_py_loop():
    """[(where, call)] of code.py's loop and of LOOP_FUNCTIONS, in their order (see LOOP)"""
    with open(os.path.join(ROOT, "firmware", "code.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            functions.update({f"{node.name}.{m.name}": m for m in node.body if isinstance(m, ast.FunctionDef)})
    [loop] = [n for top in tree.body if isinstance(top, ast.Try) for n in top.body     # the main loop: a while True
              if isinstance(n, ast.While) and isinstance(n.test, ast.Constant) and n.test.value is True]  # of a try
    out = []

    class Calls(ast.NodeVisitor):
        def __init__(self, where):
            self.where = where

        def visit_Call(self, node):
            f, args = node.func, ", ".join(ast.unparse(a) for a in node.args + node.keywords)
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("panel", "time"):
                out.append((self.where, f"{f.value.id}.{f.attr}({args})"))
            elif isinstance(f, ast.Name) and f.id in functions:
                out.append((self.where, f"{f.id}({args})"))
            self.generic_visit(node)

        def visit_AugAssign(self, node):
            target = node.target
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "panel":
                out.append((self.where, ast.unparse(node)))
            self.generic_visit(node)

        def visit_Assign(self, node):
            for target in node.targets:
                if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                        and target.value.id == "panel"):
                    out.append((self.where, f"panel.{target.attr} = {ast.unparse(node.value)}"))
            self.generic_visit(node)
    for where, body in [("loop", loop.body)] + [(name, functions[name].body) for name in LOOP_FUNCTIONS]:
        for node in body:
            Calls(where).visit(node)
    return out


def test_play_py_does_what_code_py_s_loop_does():
    # the order of the keys, the knobs, the tick, the lights and the reports, the keys' scan times, the methods of the
    # panel left out (release, stalled, keep_steps, dark), and a pass of PASS_MS: the loop's 1 ms sleep and the run
    # time the simulator gives it, with keypads that scan every KEY_SCAN_MS
    assert code_py_loop() == list(LOOP)
    assert Sim().pass_ms == play.PASS_MS == sim.PASS_MS
    with open(os.path.join(ROOT, "firmware", "code.py"), encoding="utf-8") as f:
        code = f.read()
    assert "KEY_SCAN = KEY_SCAN_MS / 1000" in code and code.count("interval=KEY_SCAN,") == 2


def test_its_names_and_numbers_are_the_simulators():
    assert (play.PASS_MS, play.PRESS_MIN_MS, play.DETENTS, play.TURN_MAX) == (sim.PASS_MS, PRESS_MIN_MS, DETENTS,
                                                                                TURN_MAX)
    assert play.TILT == sim.TILT and play.FREQ_NAMES == sim.FREQ_NAMES and list(play.SWITCHES) == SWITCHES
    with open(sim.page.GEOMETRY, encoding="utf-8") as f:
        text = f.read()
    geometry = json.loads(text[text.index("{"):text.rindex("}") + 1])
    p = play.Play(json.dumps(geometry["key_legends"]), json.dumps(list(geometry["knobs"])))
    assert p.inputs == sim.page.inputs()
    assert json.loads(p.hello()) == {"client": "browser", "build": None, "version": None, "inputs": p.inputs,
                                     "legend": None, "detents": DETENTS, "turn_max": TURN_MAX}


def test_a_click_holds_a_key_for_press_min_ms():
    # a press and its release in the same ms, as a quick tap sends them: the panel has the key down PRESS_MIN_MS,
    # as sim.live holds it, long enough for a key scan
    p = play.Play()
    p.act("press AP", 10)
    p.act("release AP", 10)
    down = [t for t in range(10, 200) if (out := p.step(t)) and json.loads(out)["buttons"]["1"] == ["AP"]]
    assert down and down[0] <= 10 + play.PASS_MS
    assert p.down == set() and p.panel.pending == {}


def test_a_page_that_goes_lets_go_and_a_new_hello_gives_the_state_again():
    p = play.Play()
    p.act("press ENT", 0)
    p.act("press UP", 0)
    p.step(100)
    assert p.down == {"ENT", "UP"} and p.held == {"ENT", "UP"}
    p.close(100)
    p.step(400)
    assert p.down == set() and p.held == set() and p.step(500) == ""
    p.hello()
    assert json.loads(p.step(500))["buttons"] == {"1": [], "2": []}


def test_wrong_actions_are_refused():
    p = play.Play()
    for line in ("press NOPE", "tap AP", "turn FREQ_INNER 0", f"turn FREQ_INNER {TURN_MAX + 1}", "turn AP 1",
                 "release", "turn FREQ_INNER x"):
        with pytest.raises(ValueError):
            p.act(line, 0)
    assert p.waiting == [] and p.held == set()
    p.act(f"turn FMS_INNER -{TURN_MAX}", 0)
    assert p.waiting == [[0, "FMS_INNER", -TURN_MAX]]


def test_an_error_in_the_panel_starts_it_again_and_says_so():
    # as code.py's handler: the panel starts again, with nothing down, and the next state names the error
    p = play.Play()
    p.act("press AP", 0)
    p.step(20)

    def fail(t):
        raise ZeroDivisionError("a test")
    p.panel.tick = fail
    state = json.loads(p.step(40))
    assert state["fault"] == "ZeroDivisionError: a test" and state["buttons"]["1"] == []
    assert p.down == set() and "fault" not in json.loads(p.hello() and p.step(60))
    p.act("release AP", 60)                  # a release of a key the panel no longer has down is dropped
    p.step(200)
    assert p.panel.pending == {}


def test_an_error_in_the_lights_or_reports_starts_the_panel_again(monkeypatch):
    # code.py shows the lights and fills the reports inside its handler too
    p = play.Play()
    p.act("press FREQ_PUSH", 0)
    p.act("release FREQ_PUSH", 100)
    p.step(300)
    assert p.panel.freq_mode == 1

    def fail(t):
        raise ZeroDivisionError("the light")
    p.panel.freq_lit = fail
    state = json.loads(p.step(320))
    assert state["fault"] == "ZeroDivisionError: the light" and state["freq"] == "COM"
    assert json.loads(p.hello() and p.step(340)).get("fault") is None
    # an error the new panel has as well goes to the caller (play.js stops the panel and says so)
    monkeypatch.setattr(play.P.Panel, "shift_level", lambda self, t: fail(t))
    with pytest.raises(ZeroDivisionError):
        p.step(360)


def test_the_version_costs_the_line_only(monkeypatch):
    # version.py as the Pages workflow fills it in, a git checkout's placeholder, and one that fails to load in any
    # way, as code.py takes it
    for text, version in (("2026-11-16, 1234abc", "2026-11-16, 1234abc"), ("$Format:%cs, %h$", None)):
        monkeypatch.setitem(sys.modules, "version", types.SimpleNamespace(VERSION=text))
        assert play.version() == version
    broken = types.ModuleType("version")
    broken.__getattr__ = lambda name: 1 / 0
    monkeypatch.setitem(sys.modules, "version", broken)
    assert play.version() is None


def test_the_pages_workflow_copies_the_files_play_js_loads():
    # play.js fetches the firmware's files from firmware/ beside the page, where the pages-pack job puts them
    with open(os.path.join(ROOT, "viewer", "play.js"), encoding="utf-8") as f:
        [files] = re.findall(r"const FIRMWARE = \[([^\]]*)\]", f.read())
    with open(os.path.join(ROOT, ".github", "workflows", "build.yml"), encoding="utf-8") as f:
        [copied] = re.findall(r"^\s*cp ((?:firmware/\S+ )+)viewer/firmware/$", f.read(), re.M)
    assert re.findall(r"'([^']+)'", files) == [name.removeprefix("firmware/") for name in copied.split()]
