"""The simulator itself (sim/): what it refuses, and that it raises the firmware's errors."""
import sys

import pytest

from sim import Sim


def test_unknown_names_fail_when_the_action_is_scheduled():
    sim = Sim()
    for action in (lambda: sim.tap("AP1"), lambda: sim.turn("FREQ inner", 1), lambda: sim.tilt("up")):
        with pytest.raises(ValueError):
            action()
    with pytest.raises(AssertionError):
        sim.wait(-1)
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
