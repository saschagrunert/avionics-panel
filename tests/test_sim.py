"""The simulator itself (sim/): what it refuses, and that it raises the firmware's errors."""
import sys
from itertools import pairwise

import pytest

from sim import Sim, typed
from sim.hardware import BOOT_MS, RESUME_MS, TICKS_WRAP_MS, Board, Event, EventQueue, Keys, keys


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


# ---------------- the stand-ins against CircuitPython 9.2.9 ----------------
def test_send_report_checks_the_length_and_waits_for_the_host():
    # a wrong length raises at once; with the host away send_report waits 2 s for it, then raises if it is not
    # mounted, and returns if it has the bus suspended, after asking it to resume (if the host allows that)
    board = Board().boot()
    one = board.devices[0]
    with pytest.raises(ValueError):
        one.send_report(bytes(8))
    board.usb_gap = (0, 10**6)
    with pytest.raises(OSError):
        one.send_report(bytes(16))
    assert board.t == 2000
    board.usb_gap, board.suspend, board.wakeup = (0, 0), (0, 10**6), False
    one.send_report(bytes(16))
    assert board.t == 4000 and board.suspended and not board.received
    board.wakeup = True
    one.send_report(bytes(16))
    assert board.t == 6000 and board.suspend[1] == 6000 + RESUME_MS and not board.received
    board.advance(RESUME_MS)
    assert board.usb_connected


def test_keypads_scan_every_20_ticks():
    # interval 0.02 s is 20 ticks of 1/1024 s (19.53 ms): 512 scans in 10 s
    board = Board()
    pad = Keys(board, ["GP13"], value_when_pressed=False, interval=0.02)
    scans, scan = [], pad.scan
    pad.scan = lambda tick: (scans.append(board.t), scan(tick))
    board.advance(10000)
    assert len(scans) == 512 and {b - a for a, b in pairwise(scans)} == {19, 20}


def test_event_queue_drops_the_newest_when_full():
    queue = EventQueue()
    for k in range(65):
        queue.record(Event(k, True, 0))
    assert len(queue) == 64 and queue.overflowed and queue.items[-1].key_number == 63


def test_clocks_count_from_power_up():
    # supervisor.ticks_ms starts 2**16 ms before its wrap at power-up, BOOT_MS before code.py starts
    board = Board()
    assert board.ticks_ms() == (1 << 29) - (1 << 16) + BOOT_MS
    assert board.ticks_ms(TICKS_WRAP_MS - BOOT_MS) == 0
    assert board.modules["time"].monotonic_ns() == BOOT_MS * 1_000_000
