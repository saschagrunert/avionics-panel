"""The simulator itself (sim/): what it refuses, and that it raises the firmware's errors."""
import sys

import pytest

from sim import Sim, typed
from sim.hardware import keys


def test_unknown_names_fail_when_the_action_is_scheduled():
    sim = Sim()
    for action in (lambda: sim.tap("AP1"), lambda: sim.turn("FREQ inner", 1), lambda: sim.tilt("up"),
                   lambda: sim.wait(-1), lambda: sim.turn("FREQ_INNER", 1, every=-1)):
        with pytest.raises(ValueError):
            action()
    assert sim.script == {}


@pytest.mark.parametrize("before", [1, 5, 50])
def test_a_firmware_error_is_raised_also_in_the_last_passes(before):
    # code.py's handler waits 2 s before it reloads: an error this close to the end of a scenario is still raised
    def boom(board):
        def turn(*_):
            raise ValueError("bug")
        board.code["panel"].turn = turn
        board.turn("ALTHDG_OUTER", 1)
    sim = Sim()
    sim.tap("AP")
    sim._at(sim.now - before, boom)
    with pytest.raises(ValueError, match="bug"):
        sim.presses(1)


def test_the_stand_ins_stay_out_of_sys_modules():
    sim = Sim()
    sim.tap("AP")
    sim.presses(1)
    assert "keypad" not in sys.modules and hasattr(sys.modules["time"], "perf_counter")


def test_typed_refuses_what_a_host_could_take_for_another_shortcut():
    # AP is Right Ctrl+F1: its modifiers go down a report before the key; everything may go up at once
    rc, f1 = keys.RC, 0x3A

    def run(*reports):
        return typed(enumerate(bytes(r) + bytes(keys.REPORT - len(r)) for r in reports))

    assert run((rc,), (rc, 0, f1), (0,)) == [(1, 1, "AP")]
    for reports, error in ((((rc,), (rc, 0, f1), (rc | keys.RS, 0, f1)), "the modifiers change with a key down"),
                           (((rc, 0, f1),), "the modifiers change with a key down"),       # at once with the key
                           (((rc,), (rc, 0, f1), (rc, 0, f1 + 1)), "one key replaces another"),
                           (((keys.LC,), (keys.LC, 0, f1)), "a shortcut of no function"),
                           (((rc, 0, f1, f1 + 1),), "not one key and its modifiers"),
                           (((0x40,),), "not one key and its modifiers")):               # right Alt
        with pytest.raises(ValueError, match=error):
            run(*reports)
