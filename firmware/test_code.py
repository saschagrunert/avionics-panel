"""Host smoke tests for code.py: runs its main loop on the stand-in hardware of sim/hardware.py.

The tests script key events and encoder steps per millisecond and look at the HID reports code.py sends.
"""
import os
import random
import re
from types import SimpleNamespace

import buttonmap as BM
import keys
import panel as P
import pytest

import sim.hardware
from sim import typed
from sim.hardware import CONTACTS, FRAME_MS, PAD_RESET, RESUME_MS, RINGS, SEND_MS, Board, Device, Event

FIRMWARE_MD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs/architecture/firmware.md")
PICO = [("\nPICO_TEST = False\n", "\nPICO_TEST = True\n")]   # code.py edited for the Pico bench
READY_MS = 1         # code.py's first loop pass comes this long after its start: the rings' pull-ups charge first
ZERO = {1: bytes(BM.SIZE[1] // 8), 2: bytes(BM.SIZE[2] // 8)}


def hardware(script=None, busy=0, usb_from=0, usb_gap=(0, 0), wrap=None, memorymap=True, keyboard=False):
    """the stand-in board after boot.py, with a script {ms: [action(hw)]}: hw.run(ms) runs code.py. A loop pass
    takes only its 1 ms sleep (no run time of its own). wrap: the ms at which supervisor.ticks_ms wraps."""
    hw = Board(script, keyboard=keyboard, **({} if wrap is None else {"wrap": wrap})).boot()
    hw.busy, hw.usb_from, hw.usb_gap = busy, usb_from, usb_gap
    if not memorymap:                         # a CircuitPython build without memorymap: the import fails
        hw.modules["memorymap"] = None
    return hw


def taken(hw, device=1):
    """(ms the host took it, report) of every report that went through to device 1 or 2"""
    return [(t, data) for t, d, data in hw.received if d is hw.devices[device - 1]]


def received(hw, device):
    """the reports that went through to device 1 or 2"""
    return [data for _, data in taken(hw, device)]


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
        keys, number = hw.key(name)
        hw.hold(name, pressed)
        keys.state = keys.read()              # as scanned: the keypad's own scans find no change
        if lost:
            keys.events.overflowed = True
        else:
            keys.events.items.append(Event(number, pressed, hw.ticks_ms(hw.t - late)))
    return act


def tap(name, at, hold=50):
    """a script that taps a key at ms `at`"""
    return {at: [press(name, True)], at + hold: [press(name, False)]}


def step(ring_index, by):
    def act(hw):
        hw.turn(hw.code["RINGS"][ring_index][0], by)
    return act


def pressed(report, device, name):
    b = BM.BUTTON[device][name]
    return bool(report[b >> 3] & (1 << (b & 7)))


def downs(hw, device=1):
    """the names of the buttons that went down on device 1 or 2, in the order the host took them"""
    out, before = [], ZERO[device]
    for r in received(hw, device):
        out += [n for n in BM.DEVICE[device] if pressed(r, device, n) and not pressed(before, device, n)]
        before = r
    return out


def sent_names(hw, device, names):
    return {n for r in received(hw, device) for n in names if pressed(r, device, n)}


def test_key_press_is_reported():
    hw = hardware({10: [press("AP", True)], 200: [press("AP", False)]}).run(400)
    reports = received(hw, 1)
    assert any(pressed(r, 1, "AP") for r in reports)
    assert not pressed(reports[-1], 1, "AP")


# ---------------- a host that does not take the reports ----------------
def test_usb_busy_does_not_stop_the_loop():
    # the first two sends fail as if the PC were not reading yet, 2 s each; the loop runs on between the tries
    # (the light follows SHIFT), and the key still held gets through on a later try
    script = {10: [press("HDG", True)], 2500: [press("SHIFT", True)], 2550: [press("SHIFT", False)],
              7500: [press("HDG", False)]}
    hw = hardware(script, busy=2).run(8000)
    assert hw.devices[0].tries[:3] == [READY_MS, READY_MS + 3000, READY_MS + 7000]
    assert duties(hw)[2500] > 0 and downs(hw) == ["HDG"]


def never_polled(ms, **kwargs):
    """a host that enumerates the panel but never reads it: every try blocks for 2 s and fails"""
    hw = hardware(**kwargs)
    hw.busy = 10**6
    return hw.run(ms)


@pytest.mark.parametrize("wrap", [None, 3500, 12000])
def test_failed_sends_back_off(wrap):
    # code.py waits 1 s from the end of a failed try before the next one, doubling up to 8 s, instead of
    # trying in every loop pass. One back-off for both devices (they share the USB interface): the other
    # device waits too, so the loop stalls for 2 s of every 10 in the end, not 4. The same while
    # supervisor.ticks_ms wraps, in a send or in a back-off
    hw = never_polled(40000, wrap=wrap)
    tries = sorted(t for j in hw.devices for t in j.tries)
    gaps = [b - a for a, b in zip(tries, tries[1:])]
    assert gaps == [SEND_MS + wait for wait in (1000, 2000, 4000, 8000, 8000)]
    stalled = hw.until - len(hw.sleeps)                  # ms not spent in 1 ms loop passes
    assert len(tries) == 6 and stalled == 6 * SEND_MS   # 12 s of 40 (22 s with a back-off per device)


def test_backoff_ends_with_a_good_send():
    # after the host starts reading, a send goes through and the next change is sent at once again; a later
    # failure starts the back-off from 1 s again (AP's release reaches the panel's report BOUNCE_MS later)
    def fail_once(hw):
        hw.busy = 1
    script = {8000: [press("AP", True)], 8500 - P.BOUNCE_MS: [fail_once, press("AP", False)]}
    hw = hardware(script, busy=2).run(11600)
    tries = hw.devices[0].tries
    assert tries[:3] == [READY_MS, READY_MS + 3000, READY_MS + 7000]   # 2 failed, the third went through
    first = next(t for t in tries if t >= 8000)
    assert first <= 8001 and pressed(received(hw, 1)[1], 1, "AP")
    assert [t for t in tries if t >= 8500] == [8500, 8500 + SEND_MS + 1000]   # failed, then 1 s later, not 4 s


def test_backoff_ends_when_usb_drops():
    # a host that comes back (a new boot) gets the current state at once, not after the old back-off
    hw = hardware(busy=2, usb_gap=(5500, 5600)).run(6000)
    tries = hw.devices[0].tries
    assert tries[:2] == [READY_MS, READY_MS + 3000]          # failed; the next try would be 4 s later
    assert tries[2] == 5600 and len(received(hw, 1)) == 1


def test_a_failed_send_skips_the_other_device():
    # both devices have a report to send, and the first send fails: the other device waits for the same
    # back-off, so the sends of a pass never take more than 2 s (4 s would outlast SHIFT_MS and freeze the
    # light for it)
    hw = never_polled(20000)
    passes = sorted(duties(hw))
    assert max(b - a for a, b in zip(passes, passes[1:])) == SEND_MS + 1
    one, two = hw.devices
    assert one.tries[0] == READY_MS and two.tries == []


# ---------------- errors, Ctrl-C and reloads ----------------
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
    assert downs(hw) == ["AP"] and received(hw, 1)[-1] == ZERO[1] and received(hw, 2)[-1] == ZERO[2]
    assert hw.sleeps[-1][1] == 2


def test_error_while_usb_is_down_sends_nothing():
    # with USB down a send would only block for 2 s: the release is skipped (the host resets on its return).
    # The detent raises as it goes to the panel, before a request to resume
    hw = hardware(crash(ValueError("bug")), usb_gap=(50, 10**6)).run(5000)
    assert len(hw.reloads) == 1
    assert [t for j in hw.devices for t in j.tries if t >= 50] == []


def test_error_with_usb_busy_still_reloads():
    # releasing fails too (OSError from send_report, after 2 s for each device): code.py still restarts
    def busy(hw):
        hw.busy = 10
    script = crash(ValueError("bug"))
    script[99] = [busy]
    hw = hardware(script).run(7000)
    assert hw.reloads == [100 + 2 * SEND_MS + 2000]


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
    assert downs(hw) == ["AP"] and received(hw, 1)[-1] == ZERO[1] and received(hw, 2)[-1] == ZERO[2]


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
    assert hw.reloads == [] and received(hw, 1)[-1] == ZERO[1]


def test_a_reload_releases_every_button():
    # a file saved to CIRCUITPY (update mode) while AP is held: CircuitPython ends code.py with its
    # ReloadException, which is no Exception. Both devices still get an all-zero report first, and nothing is
    # printed. With USB down nothing is sent, and the reload does not wait for a host
    hw = hardware({10: [press("AP", True)], 100: [Board.reload]}).run(400)
    assert hw.reloads == [100] and not hw.printed
    assert downs(hw) == ["AP"] and received(hw, 1)[-1] == ZERO[1] and received(hw, 2)[-1] == ZERO[2]
    hw = hardware({10: [press("AP", True)], 100: [Board.reload]}, usb_gap=(50, 10**6)).run(400)
    assert hw.reloads == [100] and not [t for j in hw.devices for t in j.tries if t >= 50]


# ---------------- the lights ----------------
def test_unit_light_is_written_only_on_a_change():
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110)}).run(600)
    unit = hw.leds[1]
    assert unit.duty_cycle > 0 and len(unit.history) == 2         # off at the start, on after SHIFT, HOME


def test_the_shift_light_pad_drives_12_ma():
    # the amber LED's series resistor assumes the 12 mA pad drive: DRIVE (bits 5:4) set on GP12, the rest of the
    # register as it was. GP15 only switches the UNIT light's transistor and keeps its drive, and the Pico bench
    # leaves its onboard LED's pad alone
    assert hardware().run(50).regs == {0x4001C004 + 4 * 12: PAD_RESET | 0x30}
    assert hardware().run(50, PICO).regs == {}


def test_lights_work_without_memorymap():
    # a build without memorymap: code.py runs on and the lights still follow SHIFT, at the pads' default drive
    hw = hardware(tap("SHIFT", 50, 10), memorymap=False).run(100)
    assert hw.regs == {} and hw.leds[0].duty_cycle > 0 and not hw.printed


def test_lights_work_when_the_pad_register_cannot_be_written(capsys):
    # a build whose memorymap refuses the pad registers: code.py says so on the console, once, and runs on, and
    # the lights still follow SHIFT and UNIT, at the pads' default drive
    def refuse(start, length):
        raise ValueError("Address range not allowed")
    hw = hardware({**tap("SHIFT", 50, 10), **tap("HOME", 150, 10)})
    hw.modules["memorymap"].AddressRange = refuse
    hw.run(300)
    out = capsys.readouterr().out
    assert out.count("LED drive strength not set") == 1 and "LED drive strength not set on GP 12 " in out
    assert duties(hw)[100] > 0 and hw.leds[1].duty_cycle > 0 and not hw.printed


def test_shift_light_is_written_only_on_a_change():
    # code.py asks for the level every pass (1 ms) but writes the PWM duty only when it changes
    hw = hardware(tap("SHIFT", 10)).run(3200)
    d = duties(hw)
    duty = [d[t] for t in sorted(d)]
    changes = sum(a != b for a, b in zip(duty, duty[1:]))
    assert changes >= 3 and len(hw.leds[0].history) == 1 + changes    # off at the start, on, pulses, off


def test_the_lights_do_not_flicker():
    # the PWM runs fast enough that the eye sees a steady light, also while it moves
    for edits in ((), PICO):
        assert all(led.frequency >= 200 for led in hardware().run(50, edits).leds)


def test_firmware_md_gives_the_lights_as_code_py_drives_them():
    # the duties and the PWM frequency that docs/architecture/firmware.md gives by hand
    hw = hardware().run(5)
    shift, unit = hw.code["LED_DUTY"]
    with open(FIRMWARE_MD, encoding="utf-8") as f:
        text = " ".join(f.read().split())
    assert f"PWM at {hw.leds[0].frequency // 1000} kHz, at `LED_DUTY` = {shift:#06x} and {unit:#06x} " \
           f"(about {100 * shift // 0xFFFF} and {100 * unit // 0xFFFF} % of full)" in text


def test_the_lights_go_dark_before_a_wake_request():
    # unit 2 and SHIFT armed; in one and the same pass the host turns out to have suspended the bus and AP goes
    # down, which asks it to resume: both lights are off before that wait of 2 s and more, not after it, and
    # the white one comes back with the host
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), **tap("SHIFT", 1500), 2000: [press("AP", True)]})
    hw.suspend = (2000, 10**6)
    hw.run(5000)
    shift, unit = (led.history for led in hw.leds)
    assert [t for t, d in shift if not d] == [READY_MS, 110, 2000] and [t for t, d in unit if not d] == [READY_MS, 2000]
    assert unit[-1][1] > 0 and hw.suspend[1] <= unit[-1][0] <= hw.suspend[1] + FRAME_MS and downs(hw) == ["AP"]


@pytest.mark.parametrize("wrap", [None, 1500, 2700])
def test_shift_light_pulses_on_the_led(wrap):
    # one run of code.py, the LED duty of every pass by its time: steady full, then dim and full phases in
    # the last second, never 0 before the drop, 0 after it. The same while supervisor.ticks_ms wraps
    hw = hardware(tap("SHIFT", 10), wrap=wrap).run(3200)
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
    script = tap("SHIFT", 10)
    assert hardware(script).run(100).leds[0].duty_cycle > 0          # armed: amber on
    script.update(tap("SHIFT", 150))
    assert hardware(script).run(250).leds[0].duty_cycle == 0         # tapped again: cancelled


# ---------------- the start ----------------
@pytest.mark.parametrize("devices", [(), (0,), (2, 3), (0, 1, 2), (0, 2)])
def test_missing_joysticks_show_a_hint_and_restart(devices):
    # with one joystick or none, with two other devices, or with a device beside the joysticks (0 and 1 are
    # boot.py's joysticks, 2 and 3 CircuitPython's keyboard and mouse), code.py prints a hint instead of running
    # half, and restarts 2 s later, like after any error: the hint shows again until the panel is replugged
    hw = hardware()
    found = [(hw.devices + Board().devices)[i] for i in devices]
    hw.modules["usb_hid"] = SimpleNamespace(devices=found)
    hw.run(3000)
    assert [str(e) for e in hw.printed] == ["joysticks missing: copy boot.py and replug the panel"]
    assert hw.sleeps == [(0, 2)] and hw.reloads == [2000] and not any(d.tries for d in found + hw.devices)


def test_without_boot_py_the_default_keyboard_is_not_the_keyboard_mode():
    # before boot.py has run (a fresh install, until the first replug) CircuitPython has its own keyboard, mouse
    # and consumer control: code.py asks for boot.py, in either stored mode, and sends nothing
    for keyboard in (False, True):
        hw = Board(keyboard=keyboard).run(3000)
        assert [(d.usage_page, d.usage) for d in hw.devices] == [(0x01, 0x06), (0x01, 0x02), (0x0C, 0x01)]
        assert [str(e) for e in hw.printed] == ["joysticks missing: copy boot.py and replug the panel"]
        assert hw.reloads == [2000] and not any(d.tries for d in hw.devices)


def test_the_mode_follows_the_devices_boot_py_made():
    # the keyboard mode stored, but an older boot.py made the joysticks: code.py runs them, without keys.py
    hw = hardware({10: [press("AP", True)]})
    hw.nvm[keys.MODE_BYTE] = keys.KEYBOARD
    hw.run(100)
    assert not hw.printed and downs(hw) == ["AP"] and "keys" not in hw.code
    assert "keys" in hardware(keyboard=True).run(10).code


def test_error_before_the_loop_restarts():
    # a file code.py imports is missing, or a pin is taken: code.py prints the error, releases every button it
    # can (both joysticks once it has found them) and restarts after 2 s, instead of leaving the panel dead
    hw = hardware()
    hw.modules["panel"] = None
    hw.run(3000)
    assert isinstance(hw.printed[0], ImportError) and hw.reloads == [2000] and not hw.received

    def taken_pin(*_, **__):
        raise ValueError("GP11 in use")
    hw = hardware()
    hw.modules["keypad"] = SimpleNamespace(KeyMatrix=taken_pin)
    hw.run(3000)
    assert [str(e) for e in hw.printed] == ["GP11 in use"] and len(hw.reloads) == 1
    assert received(hw, 1) == [ZERO[1]] and received(hw, 2) == [ZERO[2]]


def test_the_pass_time_lines_of_firmware_md_run(capsys):
    # docs/architecture/firmware.md, Loop pass time: the lines it gives, added to code.py where it says, print
    # the passes of each second and the longest of them. Here a pass takes 1 ms, the first one 8 ms (it sends
    # both devices' reports), and one at 2300 waits 100 ms for the host
    def stall(hw):
        hw.waits[hw.t] = 100
    with open(FIRMWARE_MD, encoding="utf-8") as f:
        section = f.read().split("\n## Loop pass time\n")[1].split("\n## ")[0]
    first = re.search(r"the line `([^`]+)`", " ".join(section.split())).group(1)
    lines = section.split("```python\n")[1].split("```")[0]
    ready, loop = '    print("Avionics Panel rev 1 ready")\n', "    while True:\n        t = now()\n"
    hw = hardware({2300: [step(0, 1), stall]})
    hw.run(3100, [(ready, "    " + first + "\n" + ready), (loop, loop + lines)])
    printed = [line for line in capsys.readouterr().out.splitlines() if "passes" in line]
    assert not hw.printed and printed == ["993 passes, longest 8 ms", "1000 passes, longest 1 ms",
                                          "893 passes, longest 101 ms"]


def test_pico_test_keeps_all_seven_encoders():
    # the bench must allocate the same 7 PIO encoders as the board, RANGE included
    board, pico = hardware().run(5), hardware().run(5, PICO)
    assert len(board.encoders) == len(pico.encoders) == 7


# ---------------- the rings ----------------
def test_encoder_step_is_reported():
    hw = hardware({10: [step(0, 1)]}).run(400)       # ALT/HDG outer ring, one slow detent
    assert downs(hw) == ["ALT_100_UP"]


def test_every_ring_counts_a_detent_each_way():
    # clockwise is the first button of each ring, with the A contact closing first; one press per detent
    names = (("ALT_100_UP", "ALT_100_DN"), ("HDG_1_UP", "HDG_1_DN"), ("COM_MHZ_UP", "COM_MHZ_DN"),
             ("COM_KHZ_UP", "COM_KHZ_DN"), ("FMS_OUTER_CW", "FMS_OUTER_CCW"), ("FMS_INNER_CW", "FMS_INNER_CCW"),
             ("RANGE_CW", "RANGE_CCW"))
    script = {}
    for i in range(len(RINGS)):
        script.update({100 + 600 * i: [step(i, 1)], 400 + 600 * i: [step(i, -1)]})
    hw = hardware(script).run(100 + 600 * len(RINGS))
    assert [r[0] for r in hw.code["RINGS"]] == list(RINGS)
    assert downs(hw) == [n for pair in names for n in pair]


def test_reversed_ring_counts_the_other_way():
    # the reverse flag in RINGS (for a ring that turns the wrong way on the first board): a clockwise count
    # of the ALT/HDG outer ring sends the counter-clockwise button, the other rings stay as they are
    reverse = ('("ALTHDG_OUTER", P.GPIO18, P.GPIO19, False)', '("ALTHDG_OUTER", P.GPIO18, P.GPIO19, True)')
    hw = hardware({10: [step(0, 1), step(1, 1)]}).run(400, [reverse])
    assert sent_names(hw, 1, ("ALT_100_UP", "ALT_100_DN", "HDG_1_UP", "HDG_1_DN")) == {"ALT_100_DN", "HDG_1_UP"}


def test_two_detents_in_one_read_are_fast_unless_the_loop_stalled():
    hw = hardware({10: [step(0, 2)]}).run(400)       # read in a normal pass: a fast turn
    assert downs(hw) == ["ALT_1000_UP"] * 2

    def stall(hw):                                      # the pass's send waits 100 ms for the host
        hw.waits[hw.t] = 100
    hw = hardware({300: [step(1, 1), stall], 350: [step(0, 2)]}).run(800)
    assert not [t for t in duties(hw) if 300 < t < 400]   # one pass: the detents are read in the next one
    assert downs(hw) == ["HDG_1_UP"] + ["ALT_100_UP"] * 2


TURNS = (1, 1, -1, -1, 1, -1, 1, 1)


def turned(hw):
    return downs(hw) == ["FMS_INNER_CW" if way > 0 else "FMS_INNER_CCW" for way in TURNS]


def off_detent(script, edges=1):
    """the board, booted, with the FMS inner ring resting between two detents, and TURNS (detents) from 800 ms"""
    for i, way in enumerate(TURNS):
        script[800 + 200 * i] = [step(5, way)]
    hw = Board(script).boot()
    hw.edge("FMS_INNER", edges)
    return hw


@pytest.mark.parametrize("edges", [1, -1, 3])
def test_a_ring_off_its_detent_at_the_start_counts_every_detent(edges, capsys):
    # the FMS inner ring rests between two detents while code.py starts and settles on one 20 ms later: code.py
    # waits for that, and from then on every detent counts, also the first one after each reversal
    def settle(hw):
        hw.edge("FMS_INNER", 1)
    hw = off_detent({20: [settle]}, edges).run(800 + 200 * len(TURNS))
    assert turned(hw) and hw.devices[0].tries[0] == 20 and "detents" not in capsys.readouterr().out


def test_a_ring_that_stays_off_its_detent_does_not_stop_the_start(capsys):
    # held between two detents for longer than code.py waits (0.5 s for all rings together): the panel starts,
    # says so on the console, and that ring loses the first detent after each reversal until the next start
    def settle(hw):
        hw.edge("FMS_INNER", 1)
        hw.edge("RANGE", 1)
    hw = off_detent({700: [settle]})
    hw.edge("RANGE", 1)                                    # a second ring: the 0.5 s are for both together
    hw.run(800 + 200 * len(TURNS))
    assert hw.devices[0].tries[0] == READY_MS + 500
    out = capsys.readouterr().out
    assert "FMS_INNER is between two detents" in out and "RANGE is between two detents" in out
    assert not hw.printed and len(downs(hw)) < len(TURNS)


# ---------------- USB down ----------------
def test_no_reports_before_usb_connects():
    # PC still booting: nothing is sent (send_report would block for 2 s), then the current state
    sent = {}

    def count(hw):
        sent[hw.t] = len(received(hw, 1))
    hw = hardware({150: [count], 300: [count]}, usb_from=200).run(400)
    assert sent[150] == 0 and sent[300] >= 1
    assert all(t >= 200 for j in hw.devices for t in j.tries)


def test_lights_are_dark_while_usb_is_down():
    # the host suspends the bus (the PC sleeps) with SHIFT armed and unit 2 selected: both lights go off and
    # the panel runs on. SHIFT ends with its light (dark means plain); unit 2 stays, and the white light shows it
    # again once the host resumes. No input, so no wake request
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), **tap("SHIFT", 300), **tap("AP", 2100)})
    hw.suspend = (1000, 2000)
    hw.run(2400)
    shift, unit = (dict(led.history) for led in hw.leds)
    assert shift[300] > 0 and shift[1000] == 0 and max(shift) == 1000
    assert unit[110] > 0 and unit[1000] == 0 and unit[2000] > 0 and max(unit) == 2000
    assert not [t for j in hw.devices for t in j.tries if 1000 <= t < 2000] and downs(hw) == ["AP"]


@pytest.mark.parametrize("at, then, sent", [(2600, step(0, 1), "ALT_100_UP"), (1700, press("VFR", True), "VFR")])
def test_shift_ends_when_usb_goes_down(at, then, sent):
    # SHIFT armed, then the host suspends the bus: the amber light goes dark, and dark means plain. An input
    # after that, inside SHIFT's 3 s, asks the host to resume and goes out plain, whether the host is back
    # before or after those 3 s: ALT, not BARO; VFR, not IDENT. SHIFT stays off once the host is back
    hw = hardware({**tap("SHIFT", 1500), at: [then]})
    hw.suspend = (at - 100, 10**6)
    hw.run(at + 3000)
    assert downs(hw) == [sent]
    lit = [t for t, d in duties(hw).items() if d]
    assert lit[0] == 1500 and lit[-1] == at - 101


def test_shift_does_nothing_while_usb_is_down():
    # SHIFT tapped while the host has the bus suspended, which asks it to resume, and VFR pressed during the wait:
    # the light was dark throughout, so VFR goes out plain, and the light stays dark once the host is back
    hw = hardware({**tap("SHIFT", 500), **tap("VFR", 1200, 100)})
    hw.suspend = (100, 10**6)
    hw.run(4000)
    assert downs(hw) == ["VFR"] and not any(duties(hw).values())


@pytest.mark.parametrize("resume", [RESUME_MS, 300])
def test_a_tap_while_suspended_wakes_the_host(monkeypatch, resume):
    # the host has suspended the bus (an idle device, or the PC asleep with the panel allowed to wake it): AP's
    # tap asks it to resume, which takes the 2 s send_report waits, and reaches the PC once the host is back, held
    # for PRESS_MS from then although the finger let go long before; also from a host that takes 300 ms to resume
    monkeypatch.setattr(sim.hardware, "RESUME_MS", resume)
    hw = hardware(tap("AP", 500, 100))
    hw.suspend = (100, 10**6)
    hw.run(3500)
    back = 500 + SEND_MS + resume
    assert hw.devices[0].tries[1] == 500 and hw.suspend[1] == back
    ap = [(t, pressed(r, 1, "AP")) for t, r in taken(hw)]   # by the host's polls
    on = [t for t, p in ap if p]
    off = [t for t, p in ap if not p and t > on[0]]
    assert back < on[0] <= back + 2 * FRAME_MS and off[0] - on[0] >= P.PRESS_MS


@pytest.mark.parametrize("away, stall", [({"suspend": (100, 10**6), "wakeup": False}, SEND_MS + 500),
                                         ({"usb_gap": (100, 10**6)}, SEND_MS)])
def test_wake_requests_back_off_when_the_host_stays_away(away, stall):
    # a sleeping PC that does not let the panel wake it, or no host at all: a key tapped every 300 ms asks it to
    # resume at most once per back-off, 1 s after the last request, doubling up to 8 s. A request to a suspended
    # host takes send_report's 2 s and 0.5 s of waiting for it; with no host send_report raises after its 2 s,
    # nothing was asked, and the loop goes on at once
    script = {t: [press("AP", (t // 300) % 2 == 1)] for t in range(300, 40000, 300)}
    hw = hardware(script)
    for k, v in away.items():
        setattr(hw, k, v)
    hw.run(40000)
    tries = [t for t in hw.devices[0].tries if t >= 100]
    gaps = [b - a for a, b in zip(tries, tries[1:])]
    assert len(received(hw, 1)) == 1 and len(gaps) >= 5
    for g, wait in zip(gaps, (1000, 2000, 4000, 8000, 8000)):
        assert stall + wait <= g <= stall + wait + 300


def test_a_host_back_by_itself_ends_the_wake_back_off():
    # a request the host refuses backs off for 1 s; the host resumes on its own before that is up and soon
    # suspends again, now letting the panel wake it: the next tap asks at once and reaches the PC
    def sleep_again(hw):
        hw.suspend, hw.wakeup = (3600, 10**6), True
    hw = hardware({**tap("AP", 500, 100), 3600: [sleep_again], **tap("AP", 3700, 100)})
    hw.suspend, hw.wakeup = (100, 3500), False
    hw.run(6500)
    assert [t for t in hw.devices[0].tries if 100 <= t < 3500] == [500] and 3700 in hw.devices[0].tries
    back = 3700 + SEND_MS + RESUME_MS
    assert hw.suspend[1] == back
    assert any(t > back and pressed(r, 1, "AP") for t, r in taken(hw))


def test_a_turn_before_a_tap_while_suspended_comes_first():
    # FMS inner turned one detent while the host has the bus suspended, then ENT tapped during the wake
    # request's wait: the detent goes to the PC first, as it was made
    hw = hardware({500: [step(5, 1)], **tap("ENT", 700)})
    hw.suspend = (100, 10**6)
    hw.run(3500)
    assert downs(hw) == ["FMS_INNER_CW", "ENT"]


@pytest.mark.parametrize("back, suspend", [(600, (100, 10**6)), (1500, (100, 10**6)), (2400, (100, 10**6)),
                                           (700, (100, 800)), (900, (100, 800))])
def test_a_turn_back_during_a_wake_request_keeps_the_step_before_it(back, suspend):
    # ALT/HDG outer one detent up while the host has the bus suspended, which asks it to resume, and one detent
    # back during the wait: the PC gets both steps, up then down, as an awake host does. Whenever the turn back
    # comes, and also when the host is back by itself within the request (at 800)
    hw = hardware({500: [step(0, 1)], back: [step(0, -1)]})
    hw.suspend = suspend
    hw.run(3500)
    assert downs(hw) == ["ALT_100_UP", "ALT_100_DN"]


def test_a_turn_back_during_a_send_that_meets_a_suspend_keeps_the_steps_before_it():
    # FMS inner four detents at once, and the send of the first step meets a suspend: that send is the request.
    # A detent back during the wait does not take back the three steps still queued: the PC gets all four and
    # the step back, as after a request of wake()
    hw = hardware({3000: [step(5, 4), suspend_in_the_next_send], 3500: [step(5, -1)]}).run(8000)
    assert downs(hw) == ["FMS_INNER_CW"] * 4 + ["FMS_INNER_CCW"]


def test_turns_during_a_wake_request_add_up():
    # FMS inner: one detent asks the host to resume, then four more and two back during the wait. The PC gets
    # the one from before the request and the two the knob stands further on, not a step back
    script = {500: [step(5, 1)], 2000: [step(5, -1)], 2100: [step(5, -1)]}
    script.update({600 + 100 * i: [step(5, 1)] for i in range(4)})
    hw = hardware(script)
    hw.suspend = (100, 10**6)
    hw.run(4000)
    assert downs(hw) == ["FMS_INNER_CW"] * 3


def test_input_right_after_the_wake_check_still_wakes_the_host():
    # a detent whose last edge comes right after a pass looked for input, with the bus suspended: it is not read
    # in that pass, where it would go nowhere. The next pass finds it and asks the host to resume
    def late(hw):
        check = hw.code["input_waiting"]

        def waiting():
            found = check()
            if not found and not turned:
                turned.append(hw.t)
                hw.turn("ALTHDG_OUTER", 1)
            return found
        hw.code["input_waiting"] = waiting
    turned = []
    hw = hardware({500: [late]})
    hw.suspend = (100, 10**6)
    hw.run(3500)
    assert turned == [500] and [t for t in hw.devices[0].tries if 100 <= t < hw.suspend[1]] == [501]
    assert downs(hw) == ["ALT_100_UP"]


def test_input_during_a_wake_back_off_is_read_as_it_comes():
    # no host at all: the first tap's request fails and backs off. A key pressed during the back-off and still
    # held when a host turns up reaches it at once, without another request
    hw = hardware({**tap("AP", 500, 100), 2700: [press("HDG", True)]}, usb_gap=(100, 3000))
    hw.run(3200)
    assert [t for t in hw.devices[0].tries if 100 <= t < 3000] == [500]
    assert downs(hw) == ["HDG"] and taken(hw)[-1][0] <= 3000 + 2 * FRAME_MS


def suspend_in_the_next_send(hw):
    """the host suspends the bus while joystick 1's next send waits 5 ms for the endpoint"""
    one = hw.devices[0]
    send = one.send_report

    def meet(report):
        del one.send_report
        hw.waits[hw.t], hw.suspend = 5, (hw.t + 1, 10**6)
        send(report)
    one.send_report = meet


def test_a_host_that_came_anew_during_a_request_gets_the_other_joystick_too():
    # unit 2 with CDI held. AP's send meets a suspend and asks the host to resume; the host resumes and
    # re-enumerates right after, while the panel waits for it: no pass sees USB down. The new host assumes
    # everything released, so it gets CDI on joystick 2 again
    script = {**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("CDI", True)],
              1000: [press("AP", True), suspend_in_the_next_send]}
    hw = hardware(script, usb_gap=(1000 + SEND_MS + RESUME_MS, 1100 + SEND_MS + RESUME_MS)).run(4000)
    assert [t for t, r in taken(hw, 2) if t >= 1100 + SEND_MS + RESUME_MS and pressed(r, 2, "CDI")]


def test_a_send_that_meets_a_suspend_is_the_request_to_resume():
    # unit 2, AP and CDI let go together: both joysticks change in one pass. The host suspends the bus while
    # joystick 1's send waits for the endpoint: that send asks the host to resume and returns with nothing sent.
    # That is the request: the pass waits for the host there, and joystick 2's send does not go on to wait. No
    # other pass and no second request come before the host is back, and both releases reach it then
    script = {**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("AP", True), press("CDI", True)],
              1000: [press("AP", False), press("CDI", False), suspend_in_the_next_send]}
    hw = hardware(script).run(4000)
    asleep = range(hw.suspend[0] - 1, hw.suspend[1])       # from that send to the host's return
    assert len(asleep) == SEND_MS + RESUME_MS and len([t for j in hw.devices for t in j.tries if t in asleep]) == 1
    assert [t for t, _ in hw.sleeps if t in asleep] == list(range(asleep[0] + SEND_MS, hw.suspend[1]))
    assert received(hw, 1)[-1] == ZERO[1] and received(hw, 2)[-1] == ZERO[2]


@pytest.mark.parametrize("name, at", [("FMS_INNER_CW", 3000), ("AP", 3000), ("AP", 3020)])
def test_a_press_whose_send_meets_a_suspend_reaches_the_pc_whole(name, at):
    # an FMS detent, or AP tapped for 40 ms, and the send of its press meets a suspend: the host is asked to
    # resume and the panel waits for it, so the press reaches the PC once the host is back, held for PRESS_MS,
    # also when it is AP's release that meets the suspend
    script = {3000: [step(5, 1)]} if name != "AP" else {3000: [press("AP", True)], 3040: [press("AP", False)]}
    script.setdefault(at, []).append(suspend_in_the_next_send)
    hw = hardware(script).run(6000)
    on = [pressed(r, 1, name) for _, r in taken(hw)]
    edges = [t for (t, _), a, b in zip(taken(hw), [False] + on, on) if a != b]
    assert len(edges) == 2 and edges[1] - edges[0] >= P.PRESS_MS
    assert (edges[0] > hw.suspend[1]) == (at == 3000)


@pytest.mark.parametrize("keyboard", [False, True])
@pytest.mark.parametrize("wait", [0, 30, SEND_MS - 1])
def test_a_report_sent_right_before_a_suspend_counts_as_unsent(keyboard, wait):
    # AP's press, in keyboard mode its modifiers, handed to the endpoint at once, after 30 ms or 1 ms before
    # send_report would give up, and the host suspends the bus before send_report returns: USB is down, so the
    # panel cannot tell whether the host took it, and the next pass asks the host to resume. It asked nothing
    # yet, so it does not wait for the host first. The host gets AP once it is back, in keyboard mode its key
    # after its modifiers
    def suspend_after_the_next_send(hw):
        one = hw.devices[0]
        send = one.send_report

        def then_suspend(report):
            del one.send_report
            hw.waits[hw.t] = wait
            send(report)
            hw.suspend = (hw.t, 10**6)
        one.send_report = then_suspend
    t0 = START_MS if keyboard else 0
    hw = hardware({t0 + 1000: [press("AP", True), suspend_after_the_next_send]}, keyboard=keyboard).run(t0 + 6000)
    tries = [t - t0 for t in hw.devices[0].tries if t >= t0 + 1000]
    assert tries[:3] == [1000, 1001 + wait, hw.suspend[1] - t0]
    if keyboard:
        assert [n for _, _, n in typed(taken(hw))] == ["AP"] and taken(hw)[-1][1][2]
    else:
        assert pressed(taken(hw)[-1][1], 1, "AP")


def test_a_send_is_the_request_to_resume_by_its_own_wait_only():
    # unit 2, AP and CDI let go together: joystick 1's send takes 24 ms, and joystick 2's goes out 1980 ms later,
    # 2004 ms after the pass began, and the host suspends the bus as it returns. That send waited less than
    # send_report's 2 s, so it asked nothing: the next pass asks the host to resume at once
    def slow_then_suspend(hw):
        two = hw.devices[1]
        send = two.send_report

        def then_suspend(report):
            del two.send_report
            hw.waits[hw.t] = 1980
            send(report)
            hw.suspend = (hw.t, 10**6)
        two.send_report = then_suspend
        hw.waits[hw.t] = P.LATE_MS
    script = {**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("AP", True), press("CDI", True)],
              1000: [press("AP", False), press("CDI", False)], 1000 + P.BOUNCE_MS: [slow_then_suspend]}
    hw = hardware(script).run(6000)
    sent = 1000 + P.BOUNCE_MS
    assert [t for t in hw.devices[1].tries if 1000 <= t < hw.suspend[1]] == [sent + P.LATE_MS]
    assert [t for t in hw.devices[0].tries if t >= 1000][:3] == [sent, sent + P.LATE_MS + 1981, hw.suspend[1]]
    assert received(hw, 1)[-1] == ZERO[1] and received(hw, 2)[-1] == ZERO[2]


@pytest.mark.parametrize("suspend", [3010, 3030, 3050])
@pytest.mark.parametrize("detents, unit", [(1, 1), (3, 1), (1, 2)])
def test_steps_the_host_misses_while_it_suspends_ask_it_to_resume(suspend, detents, unit):
    # one FMS detent, or three at once, on joystick 1, or in unit 2 on joystick 2: the host takes the first press
    # at 3008 and suspends the bus soon after. What the panel goes on to show (the release, the steps still
    # queued) differs from what the host has, so the panel asks it to resume and the host gets each step. A
    # detent at 6000 is a press of its own, not merged
    script = {**tap("SHIFT", 10), **tap("HOME", 110)} if unit == 2 else {}
    hw = hardware({**script, 3000: [step(5, detents)], 6000: [step(5, 1)]})
    hw.suspend = (suspend, 10**6)
    hw.run(8000)
    assert downs(hw, unit) == ["FMS_INNER_CW"] * (detents + 1) and received(hw, unit)[-1] == ZERO[unit]
    assert len([t for t in hw.devices[0].tries if suspend <= t < hw.suspend[1]]) == 1


@pytest.mark.parametrize("keyboard, unit", [(False, 1), (False, 2), (True, 1)])
def test_a_refused_request_is_not_repeated_without_input(keyboard, unit):
    # three FMS detents at once, the first of which the host has (in unit 2 on joystick 2), and the host then
    # suspends the bus without letting the panel wake it: the first release asks once. The request brings no
    # host back, and until the host has been back only input asks again: the steps that play out after the
    # request do not, also after the back-off. When the host resumes by itself it gets the last report
    t0 = START_MS if keyboard else 0
    script = {**tap("SHIFT", 10), **tap("HOME", 110)} if unit == 2 else {}
    hw = hardware({**script, t0 + 1000: [step(5, 3)]}, keyboard=keyboard)
    hw.suspend, hw.wakeup = (t0 + 1030, t0 + 30000), False
    hw.run(t0 + 31000)
    assert [t - t0 for t in hw.devices[0].tries if t0 + 1030 <= t < t0 + 30000] == [1000 + P.PRESS_MS + 1]
    assert taken(hw)[-1][1] == (bytes(keys.REPORT) if keyboard else ZERO[1])
    assert keyboard or received(hw, 2)[-1] == ZERO[2]


@pytest.mark.parametrize("keyboard", [False, True])
def test_a_held_key_does_not_wake_a_host_that_suspended_the_bus(keyboard):
    # UP held, and the host suspends the bus between two of its repeats, letting the panel wake it: the panel
    # leaves it asleep, as dark means plain also for the repeats. Once the host resumes by itself the repeats go
    # on, the one missed while it was away first
    t0 = START_MS if keyboard else 0
    hw = hardware({t0 + 500: [press("UP", True)], t0 + 7000: [press("UP", False)]}, keyboard=keyboard)
    hw.suspend = (t0 + 3000, t0 + 6000)
    hw.run(t0 + 7500)
    assert not [t for t in hw.devices[0].tries if t0 + 3000 <= t < t0 + 6000]
    if keyboard:
        ups = [t - t0 for t, _, n in typed(taken(hw)) if n == "UP"]
    else:
        on = [pressed(r, 1, "UP") for _, r in taken(hw)]
        ups = [t for (t, _), a, b in zip(taken(hw), [False] + on, on) if b and not a]
    after = [t for t in ups if t >= 6000]
    assert after[0] <= 6000 + 2 * FRAME_MS and P.REPEAT_MS - FRAME_MS <= after[1] - after[0] <= P.REPEAT_MS + FRAME_MS


def test_a_held_key_repeats_on_time_after_a_send_that_waited():
    # UP held, and the send of its press waits 300 ms for the endpoint: the PC gets the first repeat
    # REPEAT_DELAY_MS after the press it got, not sooner
    def taken_endpoint(hw):
        hw.waits[hw.t] = 300
    hw = hardware({1000: [press("UP", True), taken_endpoint], 2000: [press("UP", False)]}).run(2500)
    on = [t for t, r in taken(hw) if pressed(r, 1, "UP")]
    starts = [b for a, b in zip([0] + on, on) if b - a > FRAME_MS]
    assert starts[0] > 1300 and P.REPEAT_DELAY_MS <= starts[1] - starts[0] <= P.REPEAT_DELAY_MS + 2 * FRAME_MS


def test_a_key_pressed_while_a_wait_keeps_the_shift_light_lit_is_shifted():
    # SHIFT armed at 200, until 3200. A send at 2930 waits 400 ms for the endpoint, so the light stays lit until
    # 3330; VFR pressed at 3250 is read after the wait: it goes out shifted, IDENT, as the light showed
    def taken_endpoint(hw):
        hw.waits[hw.t] = 400
    hw = hardware({100: [press("AP", True)], **tap("SHIFT", 200), 2900: [press("AP", False)],
                   2900 + P.BOUNCE_MS: [taken_endpoint], **tap("VFR", 3250, 100)}).run(4000)
    assert 2900 + P.BOUNCE_MS in hw.devices[0].tries and not [t for t in duties(hw) if 2930 < t < 3330]
    assert downs(hw) == ["AP", "IDENT"]


@pytest.mark.parametrize("wrap", [None, 1022])
@pytest.mark.parametrize("first, second, sent", [("FREQ_PUSH", "SHIFT", "FREQ_PUSH"), ("SHIFT", "FREQ_PUSH",
                                                 "XPDR_MODE"), (None, "SHIFT FREQ_PUSH", "XPDR_MODE")])
def test_the_two_keypads_events_reach_the_panel_in_the_order_they_were_scanned(first, second, sent, wrap):
    # the FREQ push (a keypad of its own) and SHIFT (the matrix) pressed 25 ms apart, in two scans, while a send
    # waits 100 ms, and read together after it: they reach the panel in the order of their scans, so a push
    # before SHIFT is plain and a push after it shifted, also when supervisor.ticks_ms wraps between the two.
    # In one scan the matrix's SHIFT comes first
    def taken_endpoint(hw):
        hw.waits[hw.t] = 100

    def hold(names):
        return [lambda hw, name=name: hw.hold(name, True) for name in names.split()]
    script = {990: [step(0, 1), taken_endpoint], 1025: hold(second)}
    if first:
        script[1000] = hold(first)
    hw = hardware(script, wrap=wrap).run(1500)
    assert not [t for t in duties(hw) if 990 < t < 1090]
    assert downs(hw) == ["ALT_100_UP", sent]


def test_the_loop_reads_the_keypads_without_making_an_event_per_read(monkeypatch):
    # EventQueue.get() makes a new Event in every call, also with the queue empty: code.py uses get_into()
    def allocates(self):
        raise AssertionError("get() allocates")
    monkeypatch.setattr(sim.hardware.EventQueue, "get", allocates)
    assert downs(hardware(tap("AP", 100)).run(400)) == ["AP"]


@pytest.mark.parametrize("released", [2960, 2985, 2999])
def test_a_release_just_before_a_suspend_still_reaches_the_host(released):
    # AP held and let go 40, 15 or 1 ms before the host suspends the bus. The release waits out its 30 ms: in
    # the first case it goes out before the suspend; in the others it is applied after it, and the report that
    # lets AP go, which the host does not have, asks the host to resume in the next pass, so the PC does not keep
    # AP down
    hw = hardware({1000: [press("AP", True)], released: [press("AP", False)]})
    hw.suspend = (3000, 10**6)
    hw.run(6000)
    assert downs(hw) == ["AP"] and received(hw, 1)[-1] == ZERO[1]
    asked = [] if released == 2960 else [released + P.BOUNCE_MS + 1]
    assert [t for t in hw.devices[0].tries if 3000 <= t < hw.suspend[1]] == asked


@pytest.mark.parametrize("held, last", [(("RANGE_COM",), "PTR"), (("SHIFT",), None),
                                        (("RANGE_COM", "RANGE_A"), "PAN_UP")])
def test_only_a_release_the_pc_would_see_asks_a_suspended_host(held, last):
    # a control let go 15 ms before the host suspends the bus. The RANGE centre's release sends PTR once it has
    # waited out its 30 ms, so the report with PTR asks the host to resume, and PTR reaches it. The release of
    # SHIFT, or of the centre after a tilt that ended half a second before, changes nothing for the PC: the host
    # is left alone
    script = {1000: [press(k, True) for k in held], 2500: [press(k, False) for k in held[1:]],
              2985: [press(held[0], False)]}
    hw = hardware(script)
    hw.suspend = (3000, 10**6)
    hw.run(6000)
    assert (downs(hw) or [None])[-1] == last
    asked = [2985 + P.BOUNCE_MS + 1] if last == "PTR" else []
    assert [t for t in hw.devices[0].tries if 3000 <= t < hw.suspend[1]] == asked


def slow_send(held, *keys, wait=900, **kwargs):
    """unit 2 with one key held from 300, and keys tapped together at 1000 for 300 ms; the send of the first
    one's press finds the endpoint taken for wait ms"""
    def taken_endpoint(hw):
        hw.waits[hw.t] = wait
    script = {**tap("SHIFT", 10), **tap("HOME", 110), 300: [press(held, True)],
              1000: [press(k, True) for k in keys] + [taken_endpoint], 1300: [press(k, False) for k in keys]}
    return hardware(script, **kwargs).run(2500)


@pytest.mark.parametrize("held, key", [("CDI", "AP"), ("AP", "CDI")])
def test_a_host_that_came_anew_during_a_send_gets_the_other_joystick_too(held, key):
    # the host re-enumerates while one joystick's send waits for the endpoint, and is back before the send
    # ends: no pass sees USB down. The new host assumes everything released, so it gets the key held on the
    # other joystick again: CDI on joystick 2 after joystick 1's AP, and AP after joystick 2's CDI
    hw = slow_send(held, key, usb_gap=(1100, 1500))
    other, sender = (2, hw.devices[0]) if held == "CDI" else (1, hw.devices[1])
    assert 1000 in sender.tries and not [t for t in duties(hw) if 1000 < t < 1900]
    assert [t for t, r in taken(hw, other) if t >= 1500 and pressed(r, other, held)]


def test_a_host_that_came_anew_during_a_second_late_send_gets_the_other_joystick_too():
    # unit 2 with CDI held on joystick 2. AP's press goes out 300 ms late, and joystick 2's report follows it.
    # A second AP press waits 900 ms, during which the host re-enumerates: that report is late and holds a
    # change, so joystick 2's follows it as well, and the new host gets CDI
    def taken_endpoint(wait):
        def late(hw):
            hw.waits[hw.t] = wait
        return late
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("CDI", True)],
                   500: [press("AP", True), taken_endpoint(300)], 900: [press("AP", False)],
                   1500: [press("AP", True), taken_endpoint(900)]}, usb_gap=(1600, 2000))
    hw.run(3000)
    assert 801 in hw.devices[1].tries and 1500 in hw.devices[0].tries
    assert not [t for t in duties(hw) if 1500 < t < 2400]
    assert [t for t, r in taken(hw, 2) if t >= 2000 and pressed(r, 2, "CDI")]


@pytest.mark.parametrize("wait, again", [(20, False), (30, True)])
def test_only_a_report_later_than_three_frames_counts_as_late(wait, again):
    # AP's press goes out 20 ms late, within the 24 ms a press allows for: nothing else happens. 30 ms late,
    # it counts as late, and joystick 2's report goes out again, in the next pass
    hw = slow_send("CDI", "AP", wait=wait)
    assert [t for t in hw.devices[1].tries if t >= 1000] == ([1000 + wait + 1] if again else [])


def test_a_press_lasts_for_the_pc_after_a_send_that_waited():
    # AP's press goes out 900 ms late, long after its 56 ms: the PC still gets it for PRESS_MS, and COM1,
    # pressed with it and waiting its turn behind it, follows PRESS_MS later, not at once
    hw = slow_send("CDI", "AP", "COM1")
    ap = [t for t, r in taken(hw) if pressed(r, 1, "AP")]
    com = [t for t, r in taken(hw) if pressed(r, 1, "COM1")]
    up = next(t for t, r in taken(hw) if t > ap[0] and not pressed(r, 1, "AP"))
    assert 1900 < ap[0] <= 1900 + FRAME_MS and up - ap[0] >= P.PRESS_MS and com[0] - ap[0] >= P.PRESS_MS


def test_a_gap_lasts_for_the_pc_after_a_send_that_waited():
    # two FMS detents, and the report that ends the first one's press goes out 900 ms late, long after its gap:
    # the second press still comes GAP_MS after the PC got that release, so MobiFlight counts two
    def taken_endpoint(hw):
        hw.waits[hw.t] = 900
    hw = hardware({1000: [step(5, 2)], 1000 + P.PRESS_MS: [taken_endpoint]}).run(2500)
    on = [pressed(r, 1, "FMS_INNER_CW") for _, r in taken(hw)]
    edges = [t for (t, _), a, b in zip(taken(hw), [False] + on, on) if a != b]
    assert len(edges) == 4 and edges[1] > 1900 and edges[2] - edges[1] >= P.GAP_MS


def test_two_short_waits_in_one_pass_count_together():
    # unit 2: AP's release and DIRECT's press fall into one pass. Joystick 1's send waits 12 ms and joystick
    # 2's 20 ms, each less than the 24 ms a press allows for, but DIRECT's press reaches the PC 32 ms late. It
    # starts anew, so the PC still gets it for PRESS_MS, not for 24 ms
    def waits(hw):
        hw.waits[hw.t], hw.waits[hw.t + 12] = 12, 20
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("AP", True)],
                   1000 - P.BOUNCE_MS: [press("AP", False)], 1000: [press("DIRECT", True), waits],
                   1010: [press("DIRECT", False)]}).run(1500)
    on = [t for t, r in taken(hw, 2) if pressed(r, 2, "DIRECT")]
    off = next(t for t, r in taken(hw, 2) if t > on[0] and not pressed(r, 2, "DIRECT"))
    assert hw.devices[0].tries[-2] == 1000 and 1012 in hw.devices[1].tries and off - on[0] >= P.PRESS_MS


def test_a_host_that_polls_slowly_gets_no_endless_resends(monkeypatch):
    # a host that takes a report only every 32 ms, later than the 24 ms a press allows for. An idle panel sends
    # its first two reports and then nothing; AP tapped for 100 ms and four FMS detents reach the host as one
    # press and four, each over within a few polls, and the loop keeps running
    monkeypatch.setattr(sim.hardware, "FRAME_MS", 32)
    script = tap("AP", 1000, 100)
    script.update({2000 + 20 * i: [step(5, 1)] for i in range(4)})
    hw = hardware(script).run(4000)
    tries = sorted(t for d in hw.devices for t in d.tries)
    assert len(hw.sleeps) > 3000 and not [t for t in tries if 100 < t < 1000 or 1500 < t < 2000 or t > 3200]
    for name, count in (("AP", 1), ("FMS_INNER_CW", 4)):
        on = [pressed(r, 1, name) for _, r in taken(hw)]
        edges = [t for (t, _), a, b in zip(taken(hw), [False] + on, on) if a != b]
        assert len(edges) == 2 * count and all(32 <= b - a <= 250 for a, b in zip(edges, edges[1:]))


@pytest.mark.parametrize("key, n", [("AP", 1), ("CDI", 2)])
def test_a_late_report_is_followed_by_the_other_joysticks_once(key, n):
    # unit 2: the press of AP, on joystick 1, or of CDI, on joystick 2, goes out 300 ms late, and the other
    # joystick's report follows it, 300 ms late as well: nothing follows that one
    def waits(hw):
        hw.waits[hw.t], hw.waits[hw.t + 301] = 300, 300
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), 1000: [press(key, True), waits]}).run(2500)
    assert [t for t in hw.devices[n - 1].tries if t >= 1000] == [1000]
    assert [t for t in hw.devices[2 - n].tries if t >= 1000] == [1301]


def test_the_sends_of_a_pass_wait_once():
    # unit 2, AP and CDI let go together: joystick 1's send waits 1.99 s and goes out, and the host then does
    # not poll. Joystick 2's send, which fails after its own 2 s, comes in the next pass, not on top
    def slow(hw):
        hw.waits[hw.t] = SEND_MS - 10

    def not_polling(hw):
        hw.busy = 1
    at = 1000 + P.BOUNCE_MS
    then = at + SEND_MS - 9                                # the pass after joystick 1's send
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("AP", True), press("CDI", True)],
                   1000: [press("AP", False), press("CDI", False)], at: [slow], then: [not_polling]})
    hw.run(6500)
    passes = sorted(duties(hw))
    assert hw.devices[0].tries[-1] == at and hw.devices[1].tries[-2:] == [then, then + SEND_MS + 1000]
    assert max(b - a for a, b in zip(passes, passes[1:])) == SEND_MS + 1


def test_two_resends_that_wait_come_in_two_passes():
    # the host suspends the bus and resumes by itself, and is then slow: joystick 1's report, which goes out
    # again unchanged, waits 1.99 s, and joystick 2's would wait 2 s more and fail. Each has a pass of its own
    def slow(hw):
        hw.waits[hw.t] = SEND_MS - 10

    def not_polling(hw):
        hw.busy = 1
    hw = hardware({2000: [slow], 2000 + SEND_MS - 9: [not_polling]})
    hw.suspend = (1000, 2000)
    hw.run(6500)
    passes = sorted(duties(hw))
    assert hw.devices[0].tries[-1] == 2000 and hw.devices[1].tries[-1] == 2000 + SEND_MS - 9
    assert max(b - a for a, b in zip(passes, passes[1:])) == SEND_MS + 1


def test_a_tap_keeps_its_press_through_a_resend_that_waits():
    # unit 2: CDI's release on joystick 2 goes out 300 ms late, so joystick 1's report goes out again. FPL is
    # tapped meanwhile, and the pass that reads it and presses it first sends joystick 1's unchanged report,
    # which waits 1.5 s: FPL's press, on joystick 2, waits for the next pass. It starts anew, so it is still
    # down then and reaches the PC, for longer than a poll
    def waits(hw):
        hw.waits[hw.t], hw.waits[hw.t + 301] = 300, 1500
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("CDI", True)],
                   1000 - P.BOUNCE_MS: [press("CDI", False)], 1000: [waits], **tap("FPL", 1100)})
    hw.run(3500)
    assert 1000 in hw.devices[1].tries and hw.devices[0].tries[-1] == 1301
    on = [t for t, r in taken(hw, 2) if pressed(r, 2, "FPL")]
    assert downs(hw, 2) == ["CDI", "FPL"]
    assert next(t for t, r in taken(hw, 2) if t > on[0] and not pressed(r, 2, "FPL")) - on[0] > P.POLL_MS


def test_the_first_press_after_a_wake_request_lasts_on_a_host_slow_to_poll():
    # AP tapped while the host has the bus suspended; the host resumes on the request and polls for the first
    # time 60 ms later. AP's press is in the endpoint at once, and joystick 2's report, unchanged, waits for
    # that poll: the press starts anew, so the PC gets it for PRESS_MS, not for the 16 ms left of it
    hw = hardware(tap("AP", 500, 100))
    hw.suspend = (100, 10**6)
    back = 500 + SEND_MS + RESUME_MS
    hw.quiet = (back, back + 60)
    hw.run(3500)
    on = [t for t, r in taken(hw) if pressed(r, 1, "AP")]
    off = next(t for t, r in taken(hw) if t > on[0] and not pressed(r, 1, "AP"))
    assert back + 60 <= on[0] <= back + 60 + FRAME_MS and off - on[0] >= P.PRESS_MS


@pytest.mark.parametrize("wait", [0, 300])
def test_a_host_that_came_anew_during_an_unchanged_resend_gets_the_other_joystick_too(wait):
    # AP held on joystick 1. The host suspends the bus, resumes by itself and gets both reports again, then
    # resets while joystick 2's, unchanged, still waits for the endpoint, and re-enumerates before that send
    # ends: no pass sees USB down. The new host assumes everything released, so it gets AP again. Also when
    # AP's press went out late, so that joystick 2's report followed it once before
    def taken_endpoint(hw):
        hw.waits[hw.t] = wait
    hw = hardware({300: [press("AP", True), taken_endpoint]}, usb_gap=(2004, 2400))
    hw.suspend = (1000, 2000)
    hw.run(3000)
    assert [t for t in hw.devices[1].tries if 300 < t < 1000] == ([301 + wait] if wait else [])
    assert hw.devices[1].tries[-1] == 2000 and not [t for t in duties(hw) if 2000 < t < 2400]
    assert [t for t, r in taken(hw) if t >= 2400 and pressed(r, 1, "AP")]


def every_scan(hw, name="AP"):
    """a switch that opens or closes before every scan of the matrix from now on (a broken one); returns the
    list that gets the queue's length before each of those scans"""
    lengths, scan = [], hw.matrix.scan

    def flip(tick):
        lengths.append(len(hw.matrix.events))
        hw.hold(name, CONTACTS[name] not in hw.closed)
        scan(tick)
    hw.matrix.scan = flip
    return lengths


def test_a_wake_request_and_a_send_that_fails_make_a_pass_of_4_s():
    # FMS inner turns one detent while the host has the bus suspended; the host resumes on the request and then
    # does not poll: the request (2 s and the 30 ms of the resume) and the send that fails (2 s) are one pass
    # of about 4 s. The keys are read between the two
    def not_polling(hw):
        hw.busy = 1
    back = 3000 + SEND_MS + RESUME_MS
    hw = hardware({3000: [step(5, 1), every_scan], back: [not_polling]})
    hw.suspend = (1000, 10**6)
    hw.run(7500)
    assert [t for t in hw.devices[0].tries if t >= 3000] == [3000, back]
    # no sleep of the loop from 3000 until the second send has failed, only wake()'s own while the host resumes
    assert [t for t, _ in hw.sleeps if 3000 <= t < back + SEND_MS] == list(range(3000 + SEND_MS, back))
    assert hw.matrix.resets == 0 and not hw.matrix.events.overflowed


def test_two_requests_to_resume_make_the_longest_pass(monkeypatch):
    # FMS inner turns one detent while the host has the bus suspended; the host takes 499 ms to resume on the
    # request, and suspends the bus again while the detent's send waits for the endpoint: that send is a request
    # of its own, and the host again takes 499 ms. One pass of 5 s, the longest there is
    monkeypatch.setattr(sim.hardware, "RESUME_MS", 499)
    back = 3000 + SEND_MS + 499
    hw = hardware({3000: [step(5, 1)], back: [suspend_in_the_next_send]})
    hw.suspend = (1000, 10**6)
    hw.run(9000)
    assert [t for t in hw.devices[0].tries if t >= 3000][:2] == [3000, back]
    end = back + SEND_MS + 499
    # no sleep of the loop from 3000 until the host is back the second time, only those of the two waits for it
    assert [t for t, _ in hw.sleeps if 3000 <= t < end] == [*range(3000 + SEND_MS, back), *range(back + SEND_MS, end)]
    assert end - 3000 == 4998 and downs(hw) == ["FMS_INNER_CW"]


def test_the_queue_holds_what_a_broken_switch_makes_while_it_goes_unread():
    # the longest time a keypad's queue goes unread, in passes of 3 ms: unit 2, AP and CDI let go together, and
    # joystick 1's send waits 24 ms, not late. Joystick 2's send meets a suspend and waits out its 2 s, the panel
    # waits 0.5 s more for the host, which comes back at the end of them and suspends the bus again at once,
    # and the next pass's request is refused: 2.5 s more. A switch that changes with every scan makes 258 events
    # in those 5 s and a little more, which the queue holds with room to spare, and the pass that reads the keys
    # takes them all
    def suspend_in_the_second_send(hw):
        one = hw.devices[0]
        send = one.send_report

        def slow(report):
            del one.send_report
            lengths.append(every_scan(hw))
            hw.waits[hw.t], hw.suspend, hw.wakeup = P.LATE_MS, (hw.t + P.LATE_MS + 1, 10**6), False
            hw.script[hw.t + P.LATE_MS + SEND_MS + 496] = [back_for_a_ms]   # its last look for the host
            send(report)
        one.send_report = slow
    lengths = []
    script = {**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("AP", True), press("CDI", True)],
              1000: [press("AP", False), press("CDI", False), suspend_in_the_second_send]}
    hw = Board(script, work_ms=3).boot().run(9000)
    sent = hw.devices[1].tries[-1] - P.LATE_MS
    assert hw.devices[0].tries[-3:-1] == [sent, sent + P.LATE_MS + SEND_MS + 500]
    assert max(lengths[0]) + 1 == 258 and hw.code["MAX_EVENTS"] - 258 >= 60
    assert lengths[0][lengths[0].index(257) + 1] <= 1
    assert hw.matrix.resets == 0 and not hw.matrix.events.overflowed


def back_for_a_ms(hw):
    """the host resumes the bus for this ms only, and suspends it again"""
    hw.suspend = (hw.t + 1, 10**6)


def test_keys_come_before_turns_after_a_wake_request():
    # ALT/HDG outer one detent asks the host to resume; during the wait FMS inner turns a detent and then ENT is
    # tapped. The detent from before the request goes first; of what came during the wait, the key goes before
    # the turn, since an encoder's count carries no time
    hw = hardware({500: [step(0, 1)], 900: [step(5, 1)], **tap("ENT", 1500)})
    hw.suspend = (100, 10**6)
    hw.run(4000)
    assert downs(hw) == ["ALT_100_UP", "ENT", "FMS_INNER_CW"]


def test_a_wake_request_goes_out_as_joystick_1s_last_report():
    # AP held; the host suspends the bus and resumes by itself 300 ms later, within the request a detent made:
    # what it gets from the request is the report it had, with AP down, so AP is never let go for the PC
    hw = hardware({300: [press("AP", True)], 1000: [step(5, 1)]})
    hw.suspend = (1000, 1300)
    hw.run(2000)
    reports = [r for t, r in taken(hw) if t >= 300 + FRAME_MS]
    assert 1000 in hw.devices[0].tries and len(reports) >= 3 and all(pressed(r, 1, "AP") for r in reports)
    assert downs(hw) == ["AP", "FMS_INNER_CW"]


def test_a_host_back_within_a_wake_request_gets_the_input_at_once():
    # two sends failed, so the next try waits for its back-off, 4 s. The host re-enumerates from 5500 to 5600,
    # and AP is tapped at 5500, which asks it to resume: the host is back within that request, and AP goes
    # out at once, not after the old back-off
    hw = hardware(tap("AP", 5500, 60), busy=2, usb_gap=(5500, 5600))
    hw.run(6500)
    assert hw.devices[0].tries[:3] == [READY_MS, READY_MS + 3000, 5500]
    assert downs(hw) == ["AP"] and received(hw, 1)[-1] == ZERO[1]
    assert [t for t, r in taken(hw) if pressed(r, 1, "AP")][0] <= 5600 + 2 * FRAME_MS


def test_a_host_back_within_a_wake_request_gets_the_held_buttons_again():
    # unit 2 with CDI held; the host re-enumerates and SHIFT is tapped as it goes, which asks it to resume: the
    # new host assumes everything released, so CDI is sent again
    hw = hardware({**tap("SHIFT", 10), **tap("HOME", 110), 300: [press("CDI", True)], **tap("SHIFT", 1000, 60)},
                  usb_gap=(1000, 1100))
    hw.run(1500)
    assert [t for t, r in taken(hw, 2) if t >= 1100 and pressed(r, 2, "CDI")]


def test_held_key_is_resent_after_usb_comes_back():
    # the PC reboots while AP is held: the new host assumes everything released, so the panel sends AP again
    sent = {}

    def count(hw):
        sent[hw.t] = len(received(hw, 1))
    hw = hardware({10: [press("AP", True)], 190: [count]}, usb_gap=(100, 200)).run(400)
    reports = received(hw, 1)
    assert len(reports) > sent[190] and pressed(reports[-1], 1, "AP")


# ---------------- the keypads ----------------
def overflow(hw):
    hw.matrix.events.overflowed = True


def times_pressed(hw, device, name):
    """(ms, pressed?) of every report sent to device (no failed sends: tries are the send times)"""
    tries, sent = hw.devices[device - 1].tries, received(hw, device)
    assert len(tries) == len(sent)
    return [(t, pressed(r, device, name)) for t, r in zip(tries, sent)]


def presses_sent(hw, device, name):
    on = [p for _, p in times_pressed(hw, device, name)]
    return sum(b and not a for a, b in zip([False] + on, on))


def test_keypad_overflow_lets_go_of_every_key_and_takes_the_held_ones_again():
    # events were lost while AP is held: AP goes up at once, and the keypad, reset, reports it again, a new
    # press for the PC, held from then on
    hw = hardware({10: [press("AP", True)], 100: [overflow]}).run(400)
    sent = times_pressed(hw, 1, "AP")
    assert hw.matrix.resets == 1 and presses_sent(hw, 1, "AP") == 2 and sent[-1][1]
    assert [t for t, p in sent if not p][-1] == 100


def test_keypad_overflow_releases_a_lost_release():
    # AP's release was among the lost events: AP is released at once, and stays so
    hw = hardware({10: [press("AP", True)], 100: [press("AP", False, lost=True)]}).run(400)
    sent = times_pressed(hw, 1, "AP")
    assert presses_sent(hw, 1, "AP") == 1 and [t for t, p in sent if not p][-1] == 100


def test_keypad_overflow_leaves_the_other_keypad_alone():
    # the matrix overflows while the FREQ knob (its own keypad) is pushed: the push stays held
    hw = hardware({10: [press("FREQ_PUSH", True)], 100: [overflow]}).run(400)
    reports = received(hw, 1)
    first = next(i for i, r in enumerate(reports) if pressed(r, 1, "FREQ_PUSH"))
    assert all(pressed(r, 1, "FREQ_PUSH") for r in reports[first:]) and hw.direct.resets == 0


def test_press_right_after_an_overflow_release_is_a_new_press():
    # AP's release was lost, and AP is pressed again 10 ms after the overflow released it: that is a new press
    # for the PC (that release is no switch bounce), released again later
    hw = hardware({10: [press("AP", True)], 100: [press("AP", False, lost=True)],
                  110: [press("AP", True)], 400: [press("AP", False)]}).run(600)
    assert presses_sent(hw, 1, "AP") == 2 and not times_pressed(hw, 1, "AP")[-1][1]


def test_a_queue_that_overflows_is_dropped_and_the_held_keys_come_again():
    # eight keys open and close every 40 ms while a send waits 1.98 s for the host: 400 events, more than the
    # matrix's queue holds. After the wait code.py drops what the queue kept and resets the keypad, and the PC
    # gets one press of each key that is held in the end, none of the others
    names = ("AP", "ALT", "HDG", "FD", "VS", "NAV", "FLC", "APR")

    def toggle(hw):
        for i, name in enumerate(names):
            hw.hold(name, (hw.t // 40 + i) % 2 == 0)

    def stall(hw):
        hw.waits[hw.t] = 1980
    script = {t: [toggle] for t in range(1000, 2980, 40)}
    script[1000] = [step(5, 1), stall, toggle]
    hw = hardware(script).run(3700)
    held = [name for name in names if hw.key(name)[1] in hw.matrix.state]
    assert len(held) == 4 and hw.matrix.resets == 1 and not hw.matrix.events.overflowed
    assert sorted(downs(hw)) == sorted(["FMS_INNER_CW"] + held)


def test_a_scan_between_the_clear_and_the_reset_of_an_overflow_is_one_press():
    # the keypad scans from an interrupt, also between code.py's clear() and reset() after an overflow: that
    # scan reports AP, which has just gone down, and the reset reports it again. The PC gets one press
    def scan_after_clear(hw):
        events = hw.matrix.events
        clear = events.clear

        def cleared():
            del events.clear
            clear()
            hw.hold("AP", True)
            hw.matrix.scan(hw.raw_ticks())
        events.clear, events.overflowed = cleared, True

    def let_go(hw):
        hw.hold("AP", False)
    hw = hardware({100: [scan_after_clear], 400: [let_go]}).run(700)
    assert hw.matrix.resets == 1 and downs(hw) == ["AP"] and received(hw, 1)[-1] == ZERO[1]


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
    assert downs(hw) == []
    hw = hardware({100: [press("AP", False)], 110: [press("AP", True)], 300: [press("AP", False)]}).run(400)
    assert presses_sent(hw, 1, "AP") == 1 and not times_pressed(hw, 1, "AP")[-1][1]


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
START_MS = READY_MS + 6 * 150        # the start pattern, before the loop's first pass


def keyboard_hardware(script, **kwargs):
    """hardware() in keyboard mode, with the script's times counted from the end of the start pattern"""
    return hardware({START_MS + t: actions for t, actions in script.items()}, keyboard=True, **kwargs)


def turns_of_the_lights(hw):
    """(ms, SHIFT lit, UNIT lit) of the six steps of the start pattern, and the lights' histories after it"""
    shift, unit = hw.leds[0].history, hw.leds[1].history
    return [(t, s > 0, u > 0) for (t, s), (_, u) in zip(shift[:6], unit[:6])], shift[6:], unit[6:]


def test_keyboard_mode_starts_with_the_lights_taking_turns():
    # SHIFT, UNIT, three times, 150 ms each (docs/architecture/firmware.md, Keyboard mode), then the first pass
    # of the loop sets both as the panel has them (dark), and SHIFT lights up as ever
    hw = keyboard_hardware(tap("SHIFT", 10)).run(START_MS + 100)
    pattern, shift, unit = turns_of_the_lights(hw)
    assert pattern == [(READY_MS + 150 * i, i % 2 == 0, i % 2 == 1) for i in range(6)]
    assert shift == [(START_MS, 0), (START_MS + 10, hw.code["LED_DUTY"][0])] and unit == [(START_MS, 0)]


def test_keyboard_mode_on_the_pico_bench_blinks_its_one_light():
    # the bench has no UNIT light: the SHIFT light alone shows the pattern
    hw = hardware(keyboard=True).run(START_MS + 10, PICO)
    assert len(hw.leds) == 1 and [d > 0 for _, d in hw.leds[0].history] == [True, False] * 3 + [False]


@pytest.mark.parametrize("name", ["AP", "VFR"])
def test_a_shortcut_goes_down_after_its_modifiers_and_up_before_them(name):
    # one report per step: the modifiers, the key, the key up, the modifiers up
    mods, key = keys.shortcut(1, BM.BUTTON[1][name])
    hw = keyboard_hardware({10: [press(name, True)], 200: [press(name, False)]}).run(START_MS + 400)
    sent = taken(hw)
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
    (ap, _, first), (alt, _, second) = typed(taken(hw))
    assert (first, second) == ("AP", "ALT_100_UP")
    released = next(t for t, r in taken(hw) if t > ap and not r[2])
    assert released >= START_MS + 400 + P.BOUNCE_MS and alt > released


def test_a_held_shortcut_goes_down_again_after_usb_comes_back():
    # the PC re-enumerates the panel while AP is held: the new host has every key up, so AP's modifiers go down
    # a report before its key again
    gap = (START_MS + 100, START_MS + 400)
    hw = keyboard_hardware({10: [press("AP", True)]}, usb_gap=gap).run(START_MS + 600)
    after = [(t, r) for t, r in taken(hw) if t >= gap[1]]
    assert [n for _, _, n in typed(after)] == ["AP"] and after[-1][0] < gap[1] + 3 * FRAME_MS and after[-1][1][2]


def test_keyboard_mode_asks_a_host_to_resume_with_every_key_up():
    # AP held; the host re-enumerates, and a detent as it goes asks it to resume. The host is back within that
    # request and gets its report: every key up, not the report the old host had, with AP's key in it. Then AP's
    # modifiers and key, a report apart
    gap = (START_MS + 200, START_MS + 240)
    hw = keyboard_hardware({10: [press("AP", True)], 200: [step(0, 1)]}, usb_gap=gap).run(START_MS + 600)
    after = [(t, r) for t, r in taken(hw) if t >= gap[1]]
    assert START_MS + 200 in hw.devices[0].tries and after[0][1] == bytes(keys.REPORT)
    assert [n for _, _, n in typed(after)] == ["AP"]


def test_keyboard_mode_keeps_its_steps_apart_when_a_send_fails():
    # AP let go and LVL (other modifiers) pressed, and the report that lets AP's key go fails: the host still
    # has that key down, so the modifiers must not change until it has gone up
    def fail_once(hw):
        hw.busy = 1
    hw = keyboard_hardware({10: [press("AP", True)], 300: [press("AP", False), press("LVL", True)],
                            300 + P.BOUNCE_MS - 1: [fail_once], 4000: [press("LVL", False)]}).run(START_MS + 4500)
    assert [n for _, _, n in typed(taken(hw))] == ["AP", "LVL"] and taken(hw)[-1][1] == bytes(keys.REPORT)


def test_keyboard_mode_lets_go_of_every_key_on_an_error():
    hw = keyboard_hardware(crash(ValueError("bug"))).run(START_MS + 400)
    assert hw.printed and len(hw.reloads) == 1
    sent = taken(hw)
    assert [n for _, _, n in typed(sent)] == ["AP"] and sent[-1][1] == bytes(keys.REPORT)


def test_keyboard_mode_error_at_start_lets_go_and_restarts():
    # a pin taken while code.py starts in keyboard mode: the keyboard gets an all-zero report, and code.py
    # restarts after 2 s
    def taken_pin(*_, **__):
        raise ValueError("GP11 in use")
    hw = hardware(keyboard=True)
    hw.modules["keypad"] = SimpleNamespace(KeyMatrix=taken_pin)
    hw.run(3000)
    assert [str(e) for e in hw.printed] == ["GP11 in use"] and hw.reloads == [2000]
    assert [r for _, r in taken(hw)] == [bytes(keys.REPORT)]


def test_keyboard_mode_lights_are_dark_until_the_host_is_there():
    # the start pattern shows also while USB is down (at plug-in the host may not have the panel mounted yet).
    # Then both lights stay dark until the host is there, also when SHIFT is tapped, and follow the panel after
    hw = keyboard_hardware({**tap("SHIFT", 500), **tap("SHIFT", 3500), **tap("HOME", 3600)},
                           usb_from=START_MS + 3000)
    hw.run(START_MS + 4000)
    pattern, shift, unit = turns_of_the_lights(hw)
    assert [lit for _, *lit in pattern] == [[True, False], [False, True]] * 3
    assert [t - START_MS for t, d in shift if d] == [3500] and [t - START_MS for t, d in unit if d] == [3600]


def test_keyboard_mode_lights_are_dark_while_usb_is_down():
    # the host suspends the bus with SHIFT armed and unit 2 selected: both lights go off. SHIFT ends with its
    # light, and the white light shows unit 2 again once the host resumes
    t0 = START_MS
    hw = keyboard_hardware({**tap("SHIFT", 10), **tap("HOME", 110), **tap("SHIFT", 300)})
    hw.suspend = (t0 + 1000, t0 + 2000)
    hw.run(t0 + 2200)
    _, shift, unit = turns_of_the_lights(hw)
    shift, unit = dict(shift), dict(unit)
    assert shift[t0 + 300] > 0 and shift[t0 + 1000] == 0 and max(shift) == t0 + 1000
    assert unit[t0 + 110] > 0 and unit[t0 + 1000] == 0 and unit[t0 + 2000] > 0 and max(unit) == t0 + 2000


def test_keyboard_mode_tap_while_suspended_wakes_the_host():
    # as with the joysticks: AP's tap while the host has the bus suspended sends the keyboard's report as the
    # request to resume, and AP's shortcut reaches the PC once the host is back, its key held about PRESS_MS (its
    # modifiers go out a report before it)
    hw = keyboard_hardware(tap("AP", 500, 100))
    hw.suspend = (START_MS + 100, 10**6)
    hw.run(START_MS + 3500)
    back = START_MS + 500 + SEND_MS + RESUME_MS
    assert START_MS + 500 in hw.devices[0].tries and hw.suspend[1] == back
    sent = taken(hw)
    assert [n for _, _, n in typed(sent)] == ["AP"]
    down = next(t for t, r in sent if r[2])
    up = next(t for t, r in sent if t > down and not r[2])
    assert back < down <= back + 3 * FRAME_MS and up - down >= P.PRESS_MS - FRAME_MS   # as any short press here


def test_keyboard_mode_does_not_type_again_a_shortcut_the_host_kept_through_a_suspend():
    # AP tapped; the host suspends the bus once AP's key is down, and the release asks it to resume. The panel
    # waits for the host and the press goes on for it from there: AP's key, which a suspended host keeps, does
    # not go down a second time, or the autopilot would switch on and off
    hw = keyboard_hardware({1000: [press("AP", True)], 1040: [press("AP", False)]})
    hw.suspend = (START_MS + 1012, 10**6)
    hw.run(START_MS + 4000)
    assert [t - START_MS for t in hw.devices[0].tries if hw.suspend[0] <= t < hw.suspend[1]] == [1040]
    assert [n for _, _, n in typed(taken(hw))] == ["AP"] and taken(hw)[-1][1] == bytes(keys.REPORT)


def test_keyboard_mode_takes_a_host_that_failed_a_request_for_a_new_one():
    # AP held; the host re-enumerates, and a detent then asks it to resume. The new host has the panel mounted
    # but does not poll it yet, so the request fails: AP's shortcut goes down again, its modifiers first, then the
    # detent's
    def not_polling(hw):
        hw.busy = 1
    hw = keyboard_hardware({10: [press("AP", True)], 300: [step(0, 1)], 400: [not_polling],
                            3000: [press("AP", False)]}, usb_gap=(START_MS + 200, START_MS + 400))
    hw.run(START_MS + 4000)
    after = [(t, r) for t, r in taken(hw) if t >= START_MS + 400]
    assert START_MS + 300 in hw.devices[0].tries
    assert [n for _, _, n in typed(after)] == ["AP", "ALT_100_UP"] and after[-1][1] == bytes(keys.REPORT)


@pytest.mark.parametrize("suspend, asked", [(1030, [1000 + P.PRESS_MS + 1]), (1200, [])])
def test_keyboard_mode_asks_a_suspended_host_that_holds_a_key_the_panel_let_go(suspend, asked):
    # an FMS detent's shortcut is down at the host when it suspends the bus: the panel lets it go, which asks the
    # host to resume, and the host gets the key and then its modifiers up. Suspended once the shortcut is all up,
    # the host has what the panel shows and is left alone
    hw = keyboard_hardware({1000: [step(5, 1)]})
    hw.suspend = (START_MS + suspend, 10**6)
    hw.run(START_MS + 4000)
    assert [t - START_MS for t in hw.devices[0].tries if hw.suspend[0] <= t < hw.suspend[1]] == asked
    assert [n for _, _, n in typed(taken(hw))] == ["FMS_INNER_CW"] and taken(hw)[-1][1] == bytes(keys.REPORT)


def test_a_host_in_the_boot_protocol_gets_the_same_reports():
    # a host that asks for the boot protocol gets CircuitPython's boot keyboard in usb_hid.devices: no report ID
    # and 8 bytes, as the panel's own keyboard, so code.py sends the same reports
    def run(boot_protocol):
        hw = keyboard_hardware({10: [press("VS", True)], 100: [press("VS", False)], 300: [step(5, 1)]})
        if boot_protocol:
            hw.devices[:] = [Device(hw, report_descriptor=b"", usage_page=0x01, usage=0x06, report_ids=(0,),
                                    in_report_lengths=(keys.REPORT,), out_report_lengths=(1,))]
        return [r for _, r in taken(hw.run(START_MS + 600))]
    assert run(True) == run(False) and len(run(True)) > 4


# ---------------- random input, with the host coming and going ----------------
KEYS = ("AP", "VFR", "ENT", "CDI", "COM_SWAP", "SHIFT", "HOME", "UP", "FREQ_PUSH", "FMS_PUSH", "RANGE_COM", "RANGE_A")


def random_run(seed, keyboard):
    """A board that ran 6 s of random keys and turns while the host suspends the bus, goes away or stops
    polling at a random time, then 8 s with nothing held and, at the latest from 7 s, a host that is there
    (two sends that fail, with their back-offs, take 7 s)"""
    rng = random.Random(seed)
    script, t = {}, (START_MS if keyboard else 0) + 50
    while t < 6000:
        if rng.random() < 0.5:
            name, hold = rng.choice(KEYS), rng.choice((5, 40, 120, 600))
            script.setdefault(t, []).append(press(name, True))
            script.setdefault(t + hold, []).append(press(name, False))
        else:
            script.setdefault(t, []).append(step(rng.randrange(len(RINGS)), rng.choice((-2, -1, 1, 1, 2))))
        t += rng.choice((3, 20, 60, 200, 700))
    hw = hardware(script, keyboard=keyboard)
    kind, a = rng.choice(("suspend", "suspend", "usb_gap", "busy", "none")), rng.randrange(100, 4500)
    b = a + rng.choice((1, 40, 300, 1900, 2100, 2500))
    if kind == "suspend":                          # until b, or until the panel asks, by 7 s at the latest
        hw.suspend, hw.wakeup = (a, b if rng.random() < 0.5 else 7000), rng.random() < 0.7
    elif kind == "usb_gap":
        hw.usb_gap = (a, b)
    elif kind == "busy":
        hw.script.setdefault(a, []).append(lambda hw: setattr(hw, "busy", rng.randrange(1, 3)))
    return hw.run(14000)


@pytest.mark.parametrize("seed", range(12))
def test_random_input_leaves_nothing_held_and_no_light_in_the_dark(seed):
    # whatever is pressed and turned while the host comes and goes: no error, no pass that begins with USB down
    # leaves the amber light on (one that began with USB up can stall in a send, and its light with it), and in
    # the end the host has every button released
    hw = random_run(seed, keyboard=False)
    assert not hw.printed and not hw.reloads
    duty, begin, lit = duties(hw), 0, []
    for t, seconds in hw.sleeps:                   # (the suspension as the run left it, a wake request included)
        if duty[t] and not (hw.mounted(begin) and not hw.suspend[0] <= begin < hw.suspend[1]):
            lit.append(t)
        begin = t + round(1000 * seconds)
    assert not lit, lit[:5]
    for device in (1, 2):
        assert received(hw, device)[-1] == ZERO[device]


@pytest.mark.parametrize("seed", range(12))
def test_random_input_in_keyboard_mode_types_whole_shortcuts(seed):
    # the same in keyboard mode: each host that comes sees whole shortcuts only, modifiers before the key and
    # after it (typed() raises otherwise), and every key up in the end. A host that went away comes back with
    # every key up
    hw = random_run(seed, keyboard=True)
    assert not hw.printed and not hw.reloads
    back = hw.usb_gap[1]
    old, new = [r for r in taken(hw) if r[0] < back], [r for r in taken(hw) if r[0] >= back]
    # A send that began with the old host and still waited when the new one came goes out as it was worked out
    # for the old one, on the board as here: send_report does not tell. If that report holds a key, it is left
    # out here
    tries = [t for t in hw.devices[0].tries if t < back]
    if tries and not [t for t, _ in hw.sleeps if tries[-1] < t < back] and new and new[0][1][2]:
        new = new[1:]
    typed(old)
    typed(new)
    assert taken(hw)[-1][1] == bytes(keys.REPORT)
