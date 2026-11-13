"""The simulator itself (sim/): what it refuses, and that it raises the firmware's errors."""
import sys
from itertools import pairwise

import pytest

from sim import Sim, typed
from sim.hardware import (
    BOOT_MS,
    RESUME_MS,
    RING_PINS,
    RINGS,
    TICKS_WRAP_MS,
    Board,
    DigitalInOut,
    Event,
    EventQueue,
    IncrementalEncoder,
    Keys,
    Pull,
    keys,
)


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


# ---------------- the stand-ins against what CircuitPython 9.2.9's source says ----------------
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


def test_send_report_has_one_wait_for_the_host_and_the_endpoint():
    # the host takes a report at its next poll, and the next send waits for that. One 2 s wait covers the host
    # and the endpoint: a host that turns up after 1.5 s and then does not poll fails the send at 2 s. A host
    # back within the wait gets the report
    board = Board().boot()
    one, two = board.devices
    one.send_report(bytes(16))
    two.send_report(bytes(8))
    assert [(t, d is one) for t, d, _ in board.received] == [(8, True), (16, False)] and board.t == 8
    board = Board().boot()
    board.usb_gap, board.busy = (0, 1500), 1
    with pytest.raises(OSError):
        board.devices[0].send_report(bytes(16))
    assert board.t == 2000 and board.busy == 0 and not board.received
    board = Board().boot()
    board.suspend = (0, 1500)
    board.devices[0].send_report(bytes(16))
    assert board.t == 1500 and [t for t, _, _ in board.received] == [1504]


def test_a_send_that_meets_a_suspend_sends_nothing_and_asks_the_host_to_resume():
    # the endpoint still holds the last report when the host suspends the bus: the send waits out its 2 s, asks
    # the host to resume and returns, with no error and nothing sent
    board = Board().boot()
    one, two = board.devices
    one.send_report(bytes(16))
    board.suspend = (3, 10**6)
    two.send_report(bytes(8))
    assert board.t == 2000 and len(board.received) == 1 and board.suspend[1] == 2000 + RESUME_MS


def test_a_host_that_does_not_poll_for_a_while_takes_the_report_at_its_first_poll_after():
    # a host that has resumed and needs 60 ms before it polls: the endpoint has the report at once, the host
    # takes it at 64, and the next send waits until then
    board = Board().boot()
    board.quiet = (0, 60)
    one, two = board.devices
    one.send_report(bytes(16))
    assert board.t == 0 and board.taken == 64
    two.send_report(bytes(8))
    assert board.t == 64 and [t for t, _, _ in board.received] == [64, 72]


def test_a_host_that_goes_away_before_its_poll_never_takes_the_report():
    # the endpoint has the report at 0 and the poll is due at 8: a host that re-enumerates in between, however
    # briefly, does not get it
    board = Board().boot()
    board.usb_gap = (3, 4)
    board.devices[0].send_report(bytes(16))
    assert board.t == 0 and board.taken == 8 and not board.received


def test_a_wake_request_never_keeps_the_host_away_longer():
    # a host that is about to resume by itself is back then, not RESUME_MS after the request
    board = Board().boot()
    board.suspend = (0, 2010)
    board.devices[0].send_report(bytes(16))
    assert board.t == 2000 and board.suspend[1] == 2010


def test_before_boot_py_the_devices_are_circuitpythons_own():
    # a keyboard, a mouse and consumer control; boot.py's replace them
    board = Board()
    assert [(d.usage_page, d.usage) for d in board.devices] == [(0x01, 0x06), (0x01, 0x02), (0x0C, 0x01)]
    assert not board.keyboard and not board.created
    board.boot()
    assert [d.usage for d in board.devices] == [0x04, 0x04] and board.devices == board.created
    assert Board(keyboard=True).boot().keyboard


def encoder(board, ring="FMS_INNER", divisor=2, swap=False):
    a, b = RING_PINS[ring]
    return IncrementalEncoder(board, *((b, a) if swap else (a, b)), divisor=divisor)


def counts(board, enc, ring, turns):
    """the change of an encoder's position at each of a ring's turns (detents)"""
    out = []
    for detents in turns:
        before = enc.position
        board.turn(ring, detents)
        out.append(enc.position - before)
    return out


TURNS = (1, 1, -1, -1, 1, -1, 1, 1, -1, 1, -1, -1)


@pytest.mark.parametrize("ring", RINGS)
def test_an_encoder_counts_every_detent_of_a_ring_that_starts_on_one(ring):
    # two edges a detent (divisor 2), clockwise up with A leading; from a detent with both contacts open or
    # both closed
    for start in (0, 2):
        board = Board()
        board.edge(ring, start)
        assert counts(board, encoder(board, ring), ring, TURNS) == list(TURNS)


def test_an_encoder_started_between_two_detents_loses_the_first_detent_after_a_reversal():
    # rotaryio counts two edges from the state it starts in, so it counts halfway between the detents: after a
    # reversal the first detent brings it back there and counts nothing. With A on the lower GPIO the RP2040
    # port reads that first state with its bits swapped, which costs the first edge too
    for start in (1, 3):
        board = Board()
        board.edge("FMS_INNER", start)
        enc = encoder(board)
        board.edge("FMS_INNER", 1)                         # on to the next detent
        got = counts(board, enc, "FMS_INNER", TURNS)
        assert sum(TURNS[i] != got[i] for i in range(len(TURNS))) >= 5 and set(got) <= {-1, 0, 1}


def test_an_encoder_reads_its_first_state_as_the_port_does():
    # one edge past a detent, then four edges on: with A on the lower GPIO, as on the board, the port takes the
    # state it starts in with its two bits the wrong way round, so the first edge counts backwards and one
    # detent comes of the two. With A on the higher GPIO it reads that state right
    for swap, position in ((False, 1), (True, -2)):
        board = Board()
        board.edge("FMS_INNER", 1)
        enc = encoder(board, swap=swap)
        board.edge("FMS_INNER", 4)
        assert enc.position == position


def test_an_encoder_follows_its_pins_and_its_divisor():
    # A and B the other way round count backwards; pins that are no neighbours are refused; divisor 4 counts
    # every second detent of the panel's rings (it is for encoders with a detent per pulse)
    board = Board()
    assert counts(board, encoder(board, swap=True), "FMS_INNER", TURNS) == [-n for n in TURNS]
    with pytest.raises(RuntimeError):
        IncrementalEncoder(board, "GP16", "GP18")
    board = Board()
    assert counts(board, encoder(board, divisor=4), "FMS_INNER", (1, 1, 1, 1, -1, -1)) == [0, 1, 0, 1, 0, -1]


def test_an_input_reads_a_rings_contact_once_its_pull_up_has_charged_it():
    # digitalio on a ring's pins, as code.py looks at them before rotaryio has them: both open on a detent,
    # A closed after one edge clockwise, both closed on the next detent. A pin a DigitalInOut holds is in use
    board = Board()
    a, b = (DigitalInOut(board, pin) for pin in RING_PINS["RANGE"])
    for io in (a, b):
        io.switch_to_input(pull=Pull.UP)
    assert (a.value, b.value) == (False, False)            # not charged yet
    board.settle(0.001)
    seen = [(a.value, b.value)]
    for _ in range(4):
        board.edge("RANGE", 1)
        seen.append((a.value, b.value))
    assert seen == [(True, True), (False, True), (False, False), (True, False), (True, True)]
    with pytest.raises(ValueError, match="GP28 in use"):
        IncrementalEncoder(board, *RING_PINS["RANGE"])
    a.deinit()
    b.deinit()
    assert IncrementalEncoder(board, *RING_PINS["RANGE"]).position == 0


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


def test_get_into_moves_the_next_event_into_the_one_given():
    # keypad.Event() made on the board is stamped with supervisor.ticks_ms; get_into fills it from the queue and
    # leaves it as it is when the queue is empty; it takes nothing but an Event
    board = Board()
    event = board.modules["keypad"].Event()
    assert (event.key_number, event.pressed, event.timestamp) == (0, True, board.ticks_ms())
    queue = EventQueue()
    queue.record(Event(5, False, 123))
    assert queue.get_into(event) and (event.key_number, event.pressed, event.timestamp) == (5, False, 123)
    assert not queue.get_into(event) and (event.key_number, event.pressed, event.timestamp) == (5, False, 123)
    with pytest.raises(TypeError):
        queue.get_into(None)
    with pytest.raises(ValueError):
        Event(-1, True, 0)
    with pytest.raises(TypeError):
        board.modules["keypad"].Event(0, True, "now")


def test_the_clock_counts_from_power_up_and_wraps():
    # supervisor.ticks_ms starts 2**16 ms before its wrap at power-up, BOOT_MS before code.py starts, and wraps
    # to 0 at 2**29. The stand-in's time module has no monotonic_ns: on the board it returns a long integer,
    # which code.py's loop must not make in every pass
    board = Board()
    assert board.ticks_ms() == (1 << 29) - (1 << 16) + BOOT_MS
    assert board.ticks_ms(TICKS_WRAP_MS - BOOT_MS - 1) == (1 << 29) - 1 and board.ticks_ms(TICKS_WRAP_MS - BOOT_MS) == 0
    assert not hasattr(board.modules["time"], "monotonic_ns")
