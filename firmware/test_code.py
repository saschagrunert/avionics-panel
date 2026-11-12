"""Host smoke tests for code.py: runs its main loop on the stand-in hardware of sim/hardware.py.

The tests script key events and encoder steps per millisecond and look at the HID reports code.py sends.
"""
from types import SimpleNamespace

import buttonmap as BM
import keys
import panel as P
import pytest

import sim.hardware
from sim import typed
from sim.hardware import BOOT_MS, FRAME_MS, MATRIX_NAMES, PAD_RESET, RESUME_MS, TICKS_WRAP_MS, Board, Device, Event

PICO =[("\nPICO_TEST = False\n", "\nPICO_TEST = True\n")]   # code.py edited for the Pico bench


def hardware(script=None, busy=0, usb_from=0, usb_gap=(0, 0), wrap=TICKS_WRAP_MS - BOOT_MS, memorymap=True,
             keyboard=False):
    """the stand-in board after boot.py, with a script {ms: [action(hw)]}: hw.run(ms) runs code.py. A loop pass
    takes only its 1 ms sleep (no run time of its own)."""
    hw = Board(script, wrap=wrap, keyboard=keyboard).boot()
    hw.busy, hw.usb_from, hw.usb_gap = busy, usb_from, usb_gap
    if not memorymap:                         # a CircuitPython build without memorymap: the import fails
        hw.modules["memorymap"] = None
    return hw


def received(hw, device):
    """the reports that went through to device 1 or 2"""
    return [data for _, d, data in hw.received if d is hw.devices[device - 1]]


def duties(hw):
    """the SHIFT light's duty as code.py left it in each pass, by the ms of the pass's sleep"""
    out, writes, k, d = {}, hw.leds[0].history, 0, 0
    for t, _ in hw.sleeps:
        while k < len(writes) and writes[k][0] <= t:
            d = writes[k][1]
            k += 1
        out[t] = d
    return out


def press(name, pressed, lost=False, late=0):
    """a key or push goes down or up and its keypad reports it at once, not at its next scan; lost: the keypad
    queue overflows and drops the event; late: the keypad scanned it this many ms before code.py gets it (a pass
    that waited for the host). A release with no press before it is that of a key held when the keypad started,
    which reports no press for it"""
    def act(hw):
        keys, number = (hw.direct, 0) if name == "FREQ_PUSH" else (hw.matrix, MATRIX_NAMES.index(name))
        hw.hold(name, pressed)
        keys.state = keys.read()              # as scanned: the keypad's own scans find no change
        if lost:
            keys.events.overflowed = True
        else:
            keys.events.items.append(Event(number, pressed, hw.ticks_ms(hw.t - late)))
    return act


def step(ring_index, by):
    def act(hw):
        hw.turn(hw.code["RINGS"][ring_index][0], by)
    return act


def pressed(report, device, name):
    b = BM.BUTTON[device][name]
    return bool(report[b >> 3] & (1 << (b & 7)))


def test_key_press_is_reported():
    hw = hardware({10: [press("AP", True)], 200: [press("AP", False)]}).run(400)
    reports = received(hw, 1)
    assert any(pressed(r, 1, "AP") for r in reports)
    assert not pressed(reports[-1], 1, "AP")


def test_usb_busy_does_not_stop_the_loop():
    # the first reports fail as if the PC were not reading yet; the loop runs on and the key press still
    # gets through on a later try
    hw = hardware({10: [press("HDG", True)], 3500: [press("HDG", False)]}, busy=2).run(4000)
    assert any(pressed(r, 1, "HDG") for r in received(hw, 1))


def never_polled(ms):
    """a host that enumerates the panel but never reads it: every try blocks for 2 s and fails"""
    hw = hardware()
    hw.busy, hw.block = 10**6, 2000
    return hw.run(ms)


def test_failed_sends_back_off():
    # code.py waits 1 s from the end of a failed try before the next one, doubling up to 8 s, instead of
    # trying in every loop pass. One back-off for both devices (they share the USB interface): the other
    # device waits too, so the loop stalls for 2 s of every 10 in the end, not 4
    hw = never_polled(40000)
    tries = sorted(t for j in hw.devices for t in j.tries)
    gaps = [b - a for a, b in zip(tries, tries[1:])]
    assert gaps == [2000 + wait for wait in (1000, 2000, 4000, 8000, 8000)]
    stalled = hw.until - len(hw.sleeps)                  # ms not spent in 1 ms loop passes
    assert len(tries) == 6 and stalled == 6 * 2000      # 12 s of 40 (22 s with a back-off per device)


def test_backoff_ends_with_a_good_send():
    # after the host starts reading, a send goes through and the next change is sent at once again; a later
    # failure starts the back-off from 1 s again (AP's release reaches the panel's report BOUNCE_MS later)
    def fail_once(hw):
        hw.busy = 1
    script = {8000: [press("AP", True)], 8500 - P.BOUNCE_MS: [fail_once, press("AP", False)]}
    hw = hardware(script, busy=3).run(9600)
    tries = hw.devices[0].tries
    assert tries[:4] == [0, 1000, 3000, 7000]                # 3 failed, the fourth went through
    first = next(t for t in tries if t >= 8000)
    assert first <= 8001 and pressed(received(hw, 1)[1], 1, "AP")
    assert [t for t in tries if t >= 8500] == [8500, 9500]   # failed, then 1 s later, not 8 s


def test_backoff_ends_when_usb_drops():
    # a host that comes back (a new boot) gets the current state at once, not after the old back-off
    hw = hardware(busy=3, usb_gap=(3500, 3600)).run(4000)
    tries = hw.devices[0].tries
    assert tries[:3] == [0, 1000, 3000]                      # failed; the next try would be at 7000
    assert tries[3] == 3600 and len(received(hw, 1)) == 1


def test_a_failed_send_skips_the_other_device():
    # both devices have a report to send, and the first send fails: the other device waits for the same
    # back-off, so a pass never takes more than 2 s (a longer one would outlast SHIFT_MS, drop detents and
    # freeze the light)
    hw = never_polled(20000)
    passes = sorted(duties(hw))
    assert max(b - a for a, b in zip(passes, passes[1:])) == 2000 + 1
    one, two = hw.devices
    assert one.tries[0] == 0 and two.tries == []


def crash(error, at=100):
    """a script that holds AP, then makes code.py's panel raise `error` on the next encoder detent"""
    def boom(*_):
        raise error

    def arm(hw):
        hw.code["panel"].turn = boom
    return {10: [press("AP", True)], at: [arm, step(0, 1)]}


def test_error_releases_every_button_and_reloads():
    # the loop raises while AP is held: the traceback is printed, both devices get an all-zero report (the
    # PC would keep AP held otherwise), and after a 2 s pause (time for Ctrl-C) code.py restarts
    error = ValueError("bug")
    hw = hardware(crash(error)).run(400)
    assert hw.printed == [error] and len(hw.reloads) == 1
    one, two = received(hw, 1), received(hw, 2)
    assert any(pressed(r, 1, "AP") for r in one)
    assert one[-1] == bytes(BM.SIZE[1] // 8) and two[-1] == bytes(BM.SIZE[2] // 8)
    assert hw.sleeps[-1][1] == 2


def test_error_while_usb_is_down_sends_nothing():
    # with USB down a send would only block for 2 s: the release is skipped (the host resets on its return). The
    # detent that raises asks the host to resume first (wake), which finds no host
    hw = hardware(crash(ValueError("bug")), usb_gap=(50, 10**6)).run(5000)
    assert len(hw.reloads) == 1
    assert [t for j in hw.devices for t in j.tries if t >= 50] == [100]


def test_error_with_usb_busy_still_reloads():
    # releasing fails too (OSError from send_report): code.py still restarts
    def busy(hw):
        hw.busy = 10
    script = crash(ValueError("bug"))
    script[99] = [busy]
    hw = hardware(script).run(400)
    assert len(hw.reloads) == 1


def test_error_releases_and_reloads_when_printing_fails():
    # formatting the traceback fails again (MemoryError on the board): the buttons are released before it,
    # and code.py still restarts
    def no_memory(e):
        hw.printed.append(e)
        raise MemoryError
    hw = hardware(crash(MemoryError()))
    hw.modules["traceback"] = SimpleNamespace(print_exception=no_memory)
    hw.run(400)
    assert len(hw.printed) == 1 and len(hw.reloads) == 1
    one, two = received(hw, 1), received(hw, 2)
    assert any(pressed(r, 1, "AP") for r in one)
    assert one[-1] == bytes(BM.SIZE[1] // 8) and two[-1] == bytes(BM.SIZE[2] // 8)


def test_error_reloads_when_releasing_fails():
    # a release that raises something other than OSError (no memory for it): code.py still restarts
    def fail(hw):
        def no_memory(report):
            raise MemoryError
        for j in hw.devices:
            j.send_report = no_memory
    script = crash(ValueError("bug"))
    script[99] = [fail]
    hw = hardware(script).run(400)
    assert len(hw.printed) == 1 and len(hw.reloads) == 1


def test_ctrl_c_releases_every_button():
    # Ctrl-C on the console ends code.py for the REPL: nothing stays held, and no reload
    hw = hardware(crash(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        hw.run(400)
    assert hw.reloads == [] and received(hw, 1)[-1] == bytes(BM.SIZE[1] // 8)


def test_unit_light_is_written_only_on_a_change():
    hw = hardware({10: [press("SHIFT", True)], 60: [press("SHIFT", False)],
                  110: [press("HOME", True)], 160: [press("HOME", False)]}).run(600)
    unit = hw.leds[1]
    assert unit.duty_cycle > 0 and len(unit.history) == 2         # off at the start, on after SHIFT, HOME


def test_both_light_pads_drive_12_ma():
    # the LEDs' series resistors assume the 12 mA pad drive: DRIVE (bits 5:4) set on GP12 and GP15 only, the rest
    # of each register as it was; the Pico bench leaves its onboard LED's pad alone
    regs = hardware().run(50).regs
    pads = {0x4001C004 + 4 * gp: PAD_RESET | 0x30 for gp in (12, 15)}
    assert regs == pads and all(v & 0x30 == 0x30 and v & ~0x30 == PAD_RESET & ~0x30 for v in regs.values())
    assert hardware().run(50, PICO).regs == {}


def test_lights_work_without_memorymap():
    # a build without memorymap: code.py runs on and the lights still follow SHIFT, at the pads' default drive
    tap = {50: [press("SHIFT", True)], 60: [press("SHIFT", False)]}
    hw = hardware(tap, memorymap=False).run(100)
    assert hw.regs == {} and hw.leds[0].duty_cycle > 0 and not hw.printed


def test_lights_work_when_the_pad_registers_cannot_be_written(capsys):
    # a build whose memorymap refuses the pad registers: code.py says so on the console for each pad and runs on,
    # and the lights still follow SHIFT and UNIT, at the pads' default drive
    def refuse(start, length):
        raise ValueError("Address range not allowed")
    script = {50: [press("SHIFT", True)], 60: [press("SHIFT", False)],
              150: [press("HOME", True)], 160: [press("HOME", False)]}
    hw = hardware(script)
    hw.modules["memorymap"].AddressRange = refuse
    hw.run(300)
    out = capsys.readouterr().out
    assert all(f"LED drive strength not set on GP {gp} " in out for gp in (12, 15))
    assert duties(hw)[100] > 0 and hw.leds[1].duty_cycle > 0 and not hw.printed


def test_shift_light_is_written_only_on_a_change():
    # code.py asks for the level every pass (1 ms) but writes the PWM duty only when it changes
    hw = hardware({10: [press("SHIFT", True)], 60: [press("SHIFT", False)]}).run(3200)
    d = duties(hw)
    duty = [d[t] for t in sorted(d)]
    changes = sum(a != b for a, b in zip(duty, duty[1:]))
    assert changes >= 3 and len(hw.leds[0].history) == 1 + changes    # off at the start, on, pulses, off


@pytest.mark.parametrize("count", [0, 1])
def test_missing_joysticks_show_a_hint_and_restart(count):
    # without boot.py's two joysticks (a fresh install) code.py prints a hint instead of running half, and
    # restarts 2 s later, like after any error: the hint shows again until the panel is replugged
    hw = hardware()
    hw.modules["usb_hid"] = SimpleNamespace(devices=hw.devices[:count])
    hw.run(3000)
    assert [str(e) for e in hw.printed] == ["joysticks missing: copy boot.py and replug the panel"]
    assert hw.sleeps == [(0, 2)] and hw.reloads == [2000] and not any(j.tries for j in hw.devices)


def test_error_before_the_loop_restarts():
    # a file code.py imports is missing, or a pin is taken: code.py prints the error, releases every button it
    # can (both joysticks once it has found them) and restarts after 2 s, instead of leaving the panel dead
    hw = hardware()
    hw.modules["panel"] = None
    hw.run(3000)
    assert isinstance(hw.printed[0], ImportError) and hw.reloads == [2000] and not hw.received

    def taken(*_, **__):
        raise ValueError("GP11 in use")
    hw = hardware()
    hw.modules["keypad"] = SimpleNamespace(KeyMatrix=taken)
    hw.run(3000)
    assert [str(e) for e in hw.printed] == ["GP11 in use"] and len(hw.reloads) == 1
    assert received(hw, 1) == [bytes(BM.SIZE[1] // 8)] and received(hw, 2) == [bytes(BM.SIZE[2] // 8)]


def test_pico_test_keeps_all_seven_encoders():
    # the bench must allocate the same 7 PIO encoders as the board, RANGE included
    board, pico = hardware().run(5), hardware().run(5, PICO)
    assert len(board.encoders) == len(pico.encoders) == 7


def test_encoder_step_is_reported():
    hw = hardware({10: [step(0, 1)]}).run(400)       # ALT/HDG outer ring, one slow detent
    assert any(pressed(r, 1, "ALT_100_UP") for r in received(hw, 1))


def test_reversed_ring_counts_the_other_way():
    # the reverse flag in RINGS (for a ring that turns the wrong way on the first board): a clockwise count
    # of the ALT/HDG outer ring sends the counter-clockwise button, the other rings stay as they are
    reverse = ('("ALTHDG_OUTER", P.GPIO18, P.GPIO19, False)', '("ALTHDG_OUTER", P.GPIO18, P.GPIO19, True)')
    hw = hardware({10: [step(0, 1), step(1, 1)]}).run(400, [reverse])
    assert sent_names(hw, 1, ("ALT_100_UP", "ALT_100_DN", "HDG_1_UP", "HDG_1_DN")) == {"ALT_100_DN", "HDG_1_UP"}


def sent_names(hw, device, names):
    return {n for r in received(hw, device) for n in names if pressed(r, device, n)}


def test_two_detents_in_one_read_are_fast_unless_the_loop_stalled():
    alt = ("ALT_100_UP", "ALT_1000_UP")
    hw = hardware({10: [step(0, 2)]}).run(400)       # read in a normal pass: a fast turn
    assert sent_names(hw, 1, alt) == {"ALT_1000_UP"}
    pressed_then = []

    def look(hw):                                       # the back-off holds the report: ask the panel
        pressed_then.extend(BM.DEVICE[1][b] for b in hw.code["panel"].buttons(1))
    hw = hardware({2001: [step(0, 2)], 2002: [look]}, busy=1)   # read in the pass after a failed 2 s send
    hw.block = 2000
    hw.run(2100)
    assert hw.devices[0].tries == [0] and pressed_then == ["ALT_100_UP"]


def test_shift_light_pulses_on_the_led():
    # one run of code.py, the LED duty of every pass by its time: steady full, then dim and full phases in
    # the last second, never 0 before the drop, 0 after it
    hw = hardware({10: [press("SHIFT", True)], 60: [press("SHIFT", False)]}).run(3200)
    duty = duties(hw)
    lit = [t for t in sorted(duty) if duty[t]]
    on, end = lit[0], lit[-1] + 1                        # SHIFT armed ... dropped
    assert on == 10 and end == on + 3000                 # armed in the pass of the press, 3 s exactly
    full = duty[on]
    warning = [duty[t] for t in range(end - 1000, end)]
    assert all(duty[t] == full for t in range(on, end - 1000))
    dim = warning[0]                                     # whatever SHIFT_DUTY says: between off and full
    assert 0 < dim < full and set(warning) == {dim, full} and warning[-1] == full
    assert all(duty[t] == 0 for t in range(end, 3200))


def test_shift_light_follows_shift():
    tap = {10: [press("SHIFT", True)], 60: [press("SHIFT", False)]}
    assert hardware(tap).run(100).leds[0].duty_cycle > 0          # armed: amber on
    tap.update({150: [press("SHIFT", True)], 200: [press("SHIFT", False)]})
    assert hardware(tap).run(250).leds[0].duty_cycle == 0         # tapped again: cancelled


def test_no_reports_before_usb_connects():
    # PC still booting: nothing is sent (send_report would block for 2 s), then the current state
    sent = {}

    def count(hw):
        sent[hw.t] = len(received(hw, 1))
    hw = hardware({150: [count], 300: [count]}, usb_from=200).run(400)
    assert sent[150] == 0 and sent[300] >= 1
    assert all(t >= 200 for j in hw.devices for t in j.tries)


def test_lights_are_dark_while_usb_is_down():
    # the host suspends the bus (the PC sleeps) with SHIFT armed and unit 2 selected: both lights go off, the
    # panel runs on, and once the host resumes they show its state again; no input, so no wake request
    script = {10: [press("SHIFT", True)], 60: [press("SHIFT", False)], 110: [press("HOME", True)],
              160: [press("HOME", False)], 300: [press("SHIFT", True)], 350: [press("SHIFT", False)]}
    hw = hardware(script)
    hw.suspend = (1000, 2000)
    hw.run(2200)                                         # before SHIFT's last second, where it pulses
    shift, unit = (dict(led.history) for led in hw.leds)
    assert shift[300] > 0 and shift[1000] == 0 and shift[2000] > 0 and max(shift) == 2000
    assert unit[110] > 0 and unit[1000] == 0 and unit[2000] > 0 and max(unit) == 2000
    assert not [t for j in hw.devices for t in j.tries if 1000 <= t < 2000]


@pytest.mark.parametrize("resume", [RESUME_MS, 300])
def test_a_tap_while_suspended_wakes_the_host(monkeypatch, resume):
    # the host has suspended the bus (an idle device, or the PC asleep with the panel allowed to wake it): AP's
    # tap asks it to resume, which takes the 2 s send_report waits, and reaches the PC once the host is back, held
    # for PRESS_MS from then although the finger let go long before; also from a host that takes 300 ms to resume
    monkeypatch.setattr(sim.hardware, "RESUME_MS", resume)
    hw = hardware({500: [press("AP", True)], 600: [press("AP", False)]})
    hw.suspend = (100, 10**6)
    hw.run(3500)
    back = 500 + 2000 + resume
    assert hw.devices[0].tries[1] == 500 and hw.suspend[1] == back
    taken = [(t, pressed(r, 1, "AP")) for t, d, r in hw.received if d is hw.devices[0]]   # by the host's polls
    on = [t for t, p in taken if p]
    off = [t for t, p in taken if not p and t > on[0]]
    assert back < on[0] <= back + 2 * FRAME_MS and off[0] - on[0] >= P.PRESS_MS


def test_wake_requests_back_off_when_the_host_stays_away():
    # a sleeping PC that does not let the panel wake it, or no host at all: a key tapped every 300 ms asks it to
    # resume at most once per back-off (1 s after the last request's 2.5 s, doubling up to 8 s)
    script = {t: [press("AP", (t // 300) % 2 == 1)] for t in range(300, 40000, 300)}
    for away in ({"suspend": (100, 10**6), "wakeup": False}, {"usb_gap": (100, 10**6)}):
        hw = hardware(script)
        for k, v in away.items():
            setattr(hw, k, v)
        hw.run(40000)
        tries = [t for t in hw.devices[0].tries if t >= 100]
        gaps = [b - a for a, b in zip(tries, tries[1:])]
        assert len(received(hw, 1)) == 1 and len(gaps) >= 5
        for g, wait in zip(gaps, (1000, 2000, 4000, 8000, 8000)):
            assert 2000 + 500 + wait <= g <= 2000 + 500 + wait + 300


def test_a_host_back_by_itself_ends_the_wake_back_off():
    # a request the host refuses backs off for 1 s; the host resumes on its own before that is up and soon
    # suspends again, now letting the panel wake it: the next tap asks at once and reaches the PC
    def sleep_again(hw):
        hw.suspend, hw.wakeup = (3600, 10**6), True
    script = {500: [press("AP", True)], 600: [press("AP", False)], 3600: [sleep_again],
              3700: [press("AP", True)], 3800: [press("AP", False)]}
    hw = hardware(script)
    hw.suspend, hw.wakeup = (100, 3500), False
    hw.run(6500)
    assert [t for t in hw.devices[0].tries if 100 <= t < 3500] == [500] and 3700 in hw.devices[0].tries
    back = 3700 + 2000 + RESUME_MS
    assert hw.suspend[1] == back
    assert any(t > back and pressed(r, 1, "AP") for t, d, r in hw.received if d is hw.devices[0])


def test_a_turn_before_a_tap_while_suspended_comes_first():
    # ALT/HDG outer turned one detent while the host has the bus suspended, then SHIFT tapped during the wake
    # request's wait: the detent is ALT 100 as the dark light said, not BARO under the SHIFT that came later
    hw = hardware({500: [step(0, 1)], 700: [press("SHIFT", True)], 750: [press("SHIFT", False)]})
    hw.suspend = (100, 10**6)
    hw.run(3500)
    assert sent_names(hw, 1, ("ALT_100_UP", "BARO_UP")) == {"ALT_100_UP"}


def overflow(hw):
    hw.matrix.events.overflowed = True


def test_keypad_overflow_keeps_held_keys_pressed():
    # events were lost while AP is held: the keypad is reset and re-reports AP, and the PC sees AP held
    # throughout, not released and pressed again (which would toggle the autopilot off)
    hw = hardware({10: [press("AP", True)], 100: [overflow]}).run(400)
    reports = received(hw, 1)
    first = next(i for i, r in enumerate(reports) if pressed(r, 1, "AP"))
    assert hw.matrix.resets == 1 and all(pressed(r, 1, "AP") for r in reports[first:])


def test_keypad_overflow_releases_a_lost_release():
    # AP's release was among the lost events: once the keypad has rescanned, AP is released
    hw = hardware({10: [press("AP", True)], 100: [press("AP", False, lost=True)]}).run(400)
    reports = received(hw, 1)
    assert any(pressed(r, 1, "AP") for r in reports) and not pressed(reports[-1], 1, "AP")


def test_keypad_overflow_leaves_the_other_keypad_alone():
    # the matrix overflows while the FREQ knob (its own keypad) is pushed: the push stays held
    hw = hardware({10: [press("FREQ_PUSH", True)], 100: [overflow]}).run(400)
    reports = received(hw, 1)
    first = next(i for i, r in enumerate(reports) if pressed(r, 1, "FREQ_PUSH"))
    assert all(pressed(r, 1, "FREQ_PUSH") for r in reports[first:]) and hw.direct.resets == 0


def times_pressed(hw, device, name):
    """(ms, pressed?) of every report sent to device (no failed sends: tries are the send times)"""
    tries, sent = hw.devices[device - 1].tries, received(hw, device)
    assert len(tries) == len(sent)
    return [(t, pressed(r, device, name)) for t, r in zip(tries, sent)]


def presses_sent(hw, device, name):
    on = [p for _, p in times_pressed(hw, device, name)]
    return sum(b and not a for a, b in zip([False] + on, on))


def test_keypad_overflow_releases_a_lost_release_after_three_scans():
    # the reset keypad reports the keys still held at once: a key not reported again in three scans
    # (RESYNC_MS) is released then, not before
    hw = hardware({10: [press("AP", True)], 100: [press("AP", False, lost=True)]}).run(400)
    sent = times_pressed(hw, 1, "AP")
    assert [t for t, p in sent if not p][-1] == 100 + 3 * P.KEY_SCAN_MS
    assert all(p for t, p in sent if 10 <= t < 100 + 3 * P.KEY_SCAN_MS)


def test_press_right_after_a_resync_release_is_a_new_press():
    # AP's release was lost, and AP is pressed again 10 ms after the resync released it: that is a new press
    # for the PC (the resync release is no switch bounce), released again later
    end = 100 + 3 * P.KEY_SCAN_MS
    hw = hardware({10: [press("AP", True)], 100: [press("AP", False, lost=True)],
                  end + 10: [press("AP", True)], 400: [press("AP", False)]}).run(600)
    assert presses_sent(hw, 1, "AP") == 2 and not times_pressed(hw, 1, "AP")[-1][1]


def test_bounce_is_judged_by_the_scan_times():
    # the keypad scans AP's release and, a scan later, its new press (a bounce), but the pass in between waits
    # 37 ms for the host, so code.py reads the press 38 ms after the release; supervisor.ticks_ms wraps in
    # between. By the scan times it is still a bounce: one press for the PC, held until its release
    def wait(hw):
        hw.waits[100] = 37
    scan = 100 + P.KEY_SCAN_MS
    hw = hardware({10: [press("AP", True)], 100: [press("AP", False), step(0, 1), wait],
                  138: [press("AP", True, late=138 - scan)], 400: [press("AP", False)]}, wrap=130).run(600)
    assert 100 in hw.devices[0].tries and not [t for t in duties(hw) if 100 < t < 137]   # no pass in the wait
    assert presses_sent(hw, 1, "AP") == 1 and not times_pressed(hw, 1, "AP")[-1][1]


def test_release_read_late_keeps_its_scan_time():
    # AP's release is scanned during a pass that waits for the host and read 28 ms late; AP is pressed again 35 ms
    # after the release, more than BOUNCE_MS by the scans: a new press, and a second AP for the PC
    def wait(hw):
        hw.waits[100] = 37
    hw = hardware({10: [press("AP", True)], 100: [step(0, 1), wait], 138: [press("AP", False, late=28)],
                        145: [press("AP", True)], 400: [press("AP", False)]}).run(700)
    assert presses_sent(hw, 1, "AP") == 2 and not times_pressed(hw, 1, "AP")[-1][1]


def test_release_without_a_press_is_ignored():
    # a key held while the keypad starts (power-up, reload) is only reported when it is let go. For the RANGE
    # centre that lone release would send PTR; for a key, a press within BOUNCE_MS of it would count as a
    # bounce and be lost
    hw = hardware({100: [press("RANGE_COM", False)]}).run(400)
    assert not sent_names(hw, 1, BM.DEVICE[1]) and hw.code["panel"].pending == {}
    hw = hardware({100: [press("AP", False)], 110: [press("AP", True)], 300: [press("AP", False)]}).run(400)
    assert presses_sent(hw, 1, "AP") == 1 and not times_pressed(hw, 1, "AP")[-1][1]


def test_held_key_is_resent_after_usb_comes_back():
    # the PC reboots while AP is held: the new host assumes everything released, so the panel sends AP again
    sent = {}

    def count(hw):
        sent[hw.t] = len(received(hw, 1))
    hw = hardware({10: [press("AP", True)], 190: [count]}, usb_gap=(100, 200)).run(400)
    reports = received(hw, 1)
    assert len(reports) > sent[190] and pressed(reports[-1], 1, "AP")


# Neither the key switches (TE FSM) nor the encoder pushes give a bounce time in their datasheets; 10 ms is a
# common upper figure for small tactile switches.
SWITCH_BOUNCE_MS = 10


def test_key_scan_outlasts_switch_bounce():
    # debounce_threshold 1: a key's state changes on the first scan that reads it differently. A scan interval
    # longer than the bounce means the next scan reads it settled, so one press is one event
    hw = hardware().run(5)
    for pad in (hw.matrix, hw.direct):
        assert pad.interval * 1000 == P.KEY_SCAN_MS and pad.debounce_threshold == 1
        assert pad.interval * 1000 >= SWITCH_BOUNCE_MS


# ---------------- keyboard mode ----------------
START_MS = len(keys.START) * round(keys.BLINK_S * 1000)     # the start pattern, before the loop's first pass


def keyboard_hardware(script, **kwargs):
    """hardware() in keyboard mode, with the script's times counted from the end of the start pattern"""
    return hardware({START_MS + t: actions for t, actions in script.items()}, keyboard=True, **kwargs)


def typed_by(hw):
    """(ms, report) of every report the keyboard sent"""
    return [(t, r) for t, d, r in hw.received if d is hw.devices[0]]


def test_keyboard_mode_starts_with_the_lights_taking_turns():
    # SHIFT, UNIT, SHIFT ... for BLINK_S each, then the loop's first pass sets both as the panel has them (dark),
    # and SHIFT lights up as ever
    hw = keyboard_hardware({10: [press("SHIFT", True)], 60: [press("SHIFT", False)]}).run(START_MS + 100)
    steps = len(keys.START)
    shift, unit = hw.leds[0].history, hw.leds[1].history
    assert [t for t, _ in shift[:steps]] == [t for t, _ in unit[:steps]] == list(range(0, START_MS, START_MS // steps))
    assert [(s > 0, u > 0) for (_, s), (_, u) in zip(shift[:steps], unit[:steps])] == [
        (light == 0, light == 1) for light in keys.START]
    assert shift[steps:] == [(START_MS, 0), (START_MS + 10, hw.code["LED_DUTY"][0])] and unit[steps:] == [(START_MS, 0)]


@pytest.mark.parametrize("name", ["AP", "VFR"])
def test_a_shortcut_goes_down_after_its_modifiers_and_up_before_them(name):
    # one report per step: the modifiers, the key, the key up, the modifiers up
    mods, key = keys.shortcut(1, BM.BUTTON[1][name])
    hw = keyboard_hardware({10: [press(name, True)], 200: [press(name, False)]}).run(START_MS + 400)
    sent = typed_by(hw)
    assert [r for _, r in sent] == [bytes(8), bytes((mods, 0, 0)) + bytes(5), bytes((mods, 0, key)) + bytes(5),
                                    bytes((mods, 0, 0)) + bytes(5), bytes(8)]
    assert [(d, n) for _, d, n in typed(sent)] == [(1, name)]
    down = next(t for t, r in sent if r[2])
    up = next(t for t, r in sent if t > down and not r[2])
    assert down <= START_MS + 10 + 2 * 8 and up - down >= P.PRESS_MS      # down within two frames, and held


def test_a_held_key_holds_the_next_shortcut_back():
    # AP held while ALT turns: the detent's shortcut goes down once AP's is up, never both at once (typed() checks)
    hw = keyboard_hardware({10: [press("AP", True)], 50: [step(0, 1)], 400: [press("AP", False)]})
    hw.run(START_MS + 800)
    (ap, _, first), (alt, _, second) = typed(typed_by(hw))
    assert (first, second) == ("AP", "ALT_100_UP")
    released = next(t for t, r in typed_by(hw) if t > ap and not r[2])
    assert released >= START_MS + 400 + P.BOUNCE_MS and alt > released


def test_a_held_shortcut_is_resent_after_usb_comes_back():
    # the PC reboots while AP is held: the new host assumes every key up, so the panel sends AP's report again
    hw = keyboard_hardware({10: [press("AP", True)]}, usb_gap=(START_MS + 100, START_MS + 200)).run(START_MS + 400)
    mods, key = keys.shortcut(1, BM.BUTTON[1]["AP"])
    before, after = [t for t, r in typed_by(hw) if r == bytes((mods, 0, key)) + bytes(5)]
    assert before < START_MS + 100 and START_MS + 200 <= after < START_MS + 200 + 2 * 8


def test_keyboard_mode_lets_go_of_every_key_on_an_error():
    hw = keyboard_hardware(crash(ValueError("bug"))).run(START_MS + 400)
    assert hw.printed and len(hw.reloads) == 1
    sent = typed_by(hw)
    assert [n for _, _, n in typed(sent)] == ["AP"] and sent[-1][1] == bytes(keys.REPORT)


@pytest.mark.parametrize("byte", [keys.KEYBOARD, keys.JOYSTICK, 0x00, keys.KEYBOARD ^ 1])
def test_code_py_reads_the_mode_where_keys_py_keeps_it(byte):
    # code.py reads the byte itself, so that keys.py is imported in keyboard mode only: it must agree with keys.py
    hw = Board()
    hw.nvm[keys.MODE_BYTE] = byte
    hw.boot().run(10)
    assert hw.code["KEYBOARD"] is keys.keyboard_mode(hw.nvm) is (byte == keys.KEYBOARD)
    assert ("keys" in hw.code) is hw.code["KEYBOARD"]


def test_a_missing_keyboard_shows_a_hint_and_restarts():
    # the keyboard mode stored, but boot.py made the joysticks (an older boot.py): code.py prints what to do and
    # restarts 2 s later, like after any error, and sends nothing
    hw = Board(keyboard=True).boot()
    hw.devices[:] = hardware().devices
    hw.modules["usb_hid"] = SimpleNamespace(devices=hw.devices[:])
    hw.run(3000)
    assert [str(e) for e in hw.printed] == ["keyboard missing: copy boot.py and replug the panel"]
    assert hw.reloads == [2000] and not hw.received


def test_keyboard_mode_error_at_start_lets_go_and_restarts():
    # a pin taken while code.py starts in keyboard mode: the keyboard gets an all-zero report, and code.py
    # restarts after 2 s
    def taken(*_, **__):
        raise ValueError("GP11 in use")
    hw = hardware(keyboard=True)
    hw.modules["keypad"] = SimpleNamespace(KeyMatrix=taken)
    hw.run(3000)
    assert [str(e) for e in hw.printed] == ["GP11 in use"] and hw.reloads == [2000]
    assert [r for _, r in typed_by(hw)] == [bytes(keys.REPORT)]


def test_keyboard_mode_lights_are_dark_while_usb_is_down():
    # the start pattern shows also while USB is down (at plug-in the host may not have the panel mounted yet), then
    # the lights stay dark until the host is there; later, the host suspends the bus with SHIFT armed and unit 2
    # selected: both go off, and come back once the host resumes
    script = {10: [press("SHIFT", True)], 60: [press("SHIFT", False)], 110: [press("HOME", True)],
              160: [press("HOME", False)], 300: [press("SHIFT", True)], 350: [press("SHIFT", False)]}
    hw = keyboard_hardware(script, usb_from=START_MS + 5)
    hw.suspend = (START_MS + 1000, START_MS + 2000)
    hw.run(START_MS + 2200)
    steps = len(keys.START)
    assert [(s > 0, u > 0) for (_, s), (_, u) in zip(hw.leds[0].history[:steps], hw.leds[1].history[:steps])] == [
        (light == 0, light == 1) for light in keys.START]
    shift, unit = (dict(led.history[steps:]) for led in hw.leds)
    assert shift[START_MS] == unit[START_MS] == 0 and min(shift) == min(unit) == START_MS
    t0 = START_MS
    assert shift[t0 + 300] > 0 and shift[t0 + 1000] == 0 and shift[t0 + 2000] > 0 and max(shift) == t0 + 2000
    assert unit[t0 + 110] > 0 and unit[t0 + 1000] == 0 and unit[t0 + 2000] > 0 and max(unit) == t0 + 2000


def test_keyboard_mode_tap_while_suspended_wakes_the_host():
    # as with the joysticks: AP's tap while the host has the bus suspended sends the keyboard's report as the
    # request to resume, and AP's shortcut reaches the PC once the host is back, its key held about PRESS_MS (its
    # modifiers go out a report before it)
    hw = keyboard_hardware({500: [press("AP", True)], 600: [press("AP", False)]})
    hw.suspend = (START_MS + 100, 10**6)
    hw.run(START_MS + 3500)
    back = START_MS + 500 + 2000 + RESUME_MS
    assert START_MS + 500 in hw.devices[0].tries and hw.suspend[1] == back
    sent = typed_by(hw)
    assert [n for _, _, n in typed(sent)] == ["AP"]
    down = next(t for t, r in sent if r[2])
    up = next(t for t, r in sent if t > down and not r[2])
    assert back < down <= back + 3 * FRAME_MS and up - down >= P.PRESS_MS - FRAME_MS   # as any short press here


def test_a_host_in_the_boot_protocol_gets_the_same_reports():
    # a host that asks for the boot protocol gets CircuitPython's boot keyboard in usb_hid.devices: no report ID
    # and 8 bytes, as the panel's own keyboard, so code.py sends the same reports
    def run(boot_protocol):
        hw = keyboard_hardware({10: [press("VS", True)], 100: [press("VS", False)], 300: [step(5, 1)]})
        if boot_protocol:
            hw.devices[:] = [Device(hw, report_descriptor=b"", usage_page=0x01, usage=0x06, report_ids=(0,),
                                    in_report_lengths=(keys.REPORT,), out_report_lengths=(1,))]
        return [r for _, r in typed_by(hw.run(START_MS + 600))]
    assert run(True) == run(False) and len(run(True)) > 4

