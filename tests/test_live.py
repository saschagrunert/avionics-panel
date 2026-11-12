"""The simulator in real time (sim/live.py): code.py in a thread of its own, actions queued by their names, every
report the host takes to an output. The panel runs SPEED times faster than the wall clock. Each test queues its
actions before start(), so their timing on the panel's clock is fixed, and checks what reached the output and in
what order, not when."""
import threading

import pytest

from sim import BM, typed
from sim.hardware import keys
from sim.live import PRESS_MIN_MS, TURN_MAX, Live, parse

SPEED = 25           # a tap with its pause (400 ms) takes about 16 ms
TIMEOUT_S = 5


def run(live):
    """Starts code.py: the list it returns gets (device, buttons by name) of every report, after checking its
    report ID and length"""
    out = []

    def output(device, report):
        assert report[0] == (4, 5)[device - 1] and len(report) == 1 + BM.SIZE[device] // 8
        out.append((device, [BM.DEVICE[device][b] for b in range(BM.SIZE[device]) if report[1 + b // 8] >> b % 8 & 1]))
    live.start(output)
    return out


def finish(live):
    assert live.idle(TIMEOUT_S)
    live.stop()
    assert not live.thread.is_alive()


def test_actions_reach_the_output_in_order():
    live = Live(speed=SPEED)
    for action in (("tap", "AP"), ("turn", "ALTHDG_OUTER", 2), ("tilt", "UP"), ("tap", "COM_SWAP", 100, 0)):
        live.act(*action)                      # the last without a pause: idle() still waits for its release
    out = run(live)
    finish(live)
    # both devices once at the start (nothing sent yet), then device 1 only: COM ⇆ is unit 1's
    assert out == [(1, []), (2, []), (1, ["AP"]), (1, []), (1, ["ALT_100_UP"]), (1, []), (1, ["ALT_100_UP"]),
                   (1, []), (1, ["PAN_UP"]), (1, []), (1, ["COM_SWAP"]), (1, [])]


def test_keyboard_mode_sends_the_keyboards_reports():
    # Live(keyboard=True): device 1 is the keyboard, its reports 8 bytes without a report ID; the start pattern
    # comes first, then the shortcut of the tap with its modifiers around it
    live = Live(speed=SPEED, keyboard=True)
    live.act("wait", 1000)
    live.act("tap", "SHIFT")
    live.act("tap", "HOME")
    live.act("turn", "FREQ_INNER", 1)
    out = []
    live.start(lambda device, report: out.append((device, report)))
    finish(live)
    assert {device for device, _ in out} == {1} and {len(report) for _, report in out} == {keys.REPORT}
    assert [(d, n) for _, d, n in typed(enumerate(r for _, r in out))] == [(2, "COM_KHZ_UP")]
    assert out[-1] == (1, bytes(keys.REPORT))


def test_the_lights_can_be_read_at_any_time():
    # read on the panel's clock, after each tap (SHIFT drops after 3 s), and at the end from this thread
    live = Live(speed=SPEED)
    seen = []
    for key in ("SHIFT", "HOME"):              # SHIFT + HOME: unit 2, the UNIT light on, SHIFT off
        live.act("tap", key)
        live.do(lambda b: seen.append((b.light("SHIFT"), b.light("UNIT"))))
    run(live)
    finish(live)
    shift, unit = live.code["LED_DUTY"]
    assert seen == [(shift, 0), (0, unit)] and (live.light("SHIFT"), live.light("UNIT")) == (0, unit)


def test_a_click_shorter_than_a_key_scan_still_counts():
    # two clicks in the same ms, as they reach a panel that runs late: each change of AP waits PRESS_MIN_MS on the
    # panel's clock after the one before, so both count
    live = Live(speed=SPEED)
    for action in ("press", "release", "press", "release"):
        live.act(action, "AP")
    seen = []
    live.do(lambda b: seen.append(b.changes["AP"] - b.t))
    out = run(live)
    finish(live)
    assert seen == [3 * PRESS_MIN_MS] and out == [(1, []), (2, []), (1, ["AP"]), (1, []), (1, ["AP"]), (1, [])]


def test_idle_waits_also_before_any_switch_changed():
    live = Live(speed=SPEED)
    live.act("turn", "FREQ_INNER", 1, 0)
    out = run(live)
    finish(live)                               # idle() with no switch changed yet
    assert [names for _, names in out if names] == [["COM_KHZ_UP"]]


def test_lines_of_actions_are_read_with_their_names_checked():
    assert parse("tap AP 500") == ("tap", ["AP", 500]) and parse("  ") is None
    assert parse("turn FREQ_INNER -3") == ("turn", ["FREQ_INNER", -3]) and parse("tilt UP") == ("tilt", ["UP"])
    for line, why in (("fly", "actions: "), ("tap", "usage: tap"), ("tap AP1", "no switch 'AP1'"),
                      ("tap AP x", "HOLD_MS is a whole number"), ("tap AP --3", "whole number"),
                      ("tap AP ²", "whole number"), ("tap AP 1 2", "usage: tap"), ("tilt up", "no tilt 'up'"),
                      ("turn FREQ inner 1", "no ring 'FREQ'"), (f"turn RANGE {TURN_MAX + 1}", "30 detents at most")):
        with pytest.raises(ValueError, match=why):
            parse(line)
    with pytest.raises(ValueError, match="actions: press NAME"):
        parse("tap AP", {"press": "press NAME"})


def test_wrong_actions_fail_in_the_callers_thread():
    live = Live()
    for action in (("fly",), ("tap", "AP1"), ("turn", "FREQ inner", 1), ("tilt", "up"), ("wait", -1)):
        with pytest.raises(ValueError):
            live.act(*action)
    with pytest.raises(TypeError):
        live.act("tap")
    assert live.actions.empty()


def test_code_py_starts_again_after_an_error_on_the_same_board():
    # code.py's handler (firmware/test_code.py) releases everything, waits 2 s and reloads. AP, held through the
    # reload, stays silent: the new keypad hears only its release. A new tap goes through.
    def bug(board):                            # this run's panel fails on the next detent
        def turn(*_):
            raise ValueError("bug")
        board.code["panel"].turn = turn
        board.turn("ALTHDG_OUTER", 1)
    live = Live(speed=50)
    live.act("press", "AP")
    live.act("wait", 200)
    live.do(bug)
    live.act("wait", 2200)
    live.act("release", "AP")
    live.act("wait", 100)
    live.act("tap", "AP")
    out = run(live)
    finish(live)
    assert [type(e) for e in live.printed] == [ValueError] and len(live.reloads) == 1
    assert out[2] == (1, ["AP"]) and out[-4:] == [(1, []), (2, []), (1, ["AP"]), (1, [])]


@pytest.mark.parametrize("where", ["output", "action"])
def test_an_error_outside_code_py_ends_the_run(where):
    # not code.py's error, so no reload: the thread ends, and everything that waits for it raises
    def fail(*_):
        raise OSError("gone")
    live = Live(speed=SPEED)
    if where == "action":
        live.do(fail)
    live.start(fail if where == "output" else lambda *_: None)
    live.thread.join(TIMEOUT_S)
    for call in (live.idle, lambda: live.act("tap", "AP"), lambda: live.do(print)):
        with pytest.raises(RuntimeError, match="gone"):
            call()
    with pytest.raises(OSError, match="gone"):
        live.stop()
    assert not live.printed and not live.reloads


def test_start_twice_and_a_stop_that_times_out_raise():
    live = Live(speed=SPEED)
    entered, stuck = threading.Event(), threading.Event()

    def output(*_):                            # hangs in the first report
        entered.set()
        stuck.wait(TIMEOUT_S)
    live.start(output)
    with pytest.raises(RuntimeError):
        live.start(print)
    assert entered.wait(TIMEOUT_S)
    with pytest.raises(TimeoutError):
        live.stop(timeout=0.05)
    stuck.set()
    live.stop()
