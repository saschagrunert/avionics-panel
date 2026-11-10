"""Host smoke tests for code.py: runs its main loop against stub CircuitPython modules.

code.py itself needs the hardware (keypad, rotaryio, pwmio, usb_hid), so these stubs stand in for it:
the tests script key presses and encoder steps per millisecond and record the HID reports it sends.
"""
import os
import sys
import types

import buttonmap as BM
import pytest

NAMES = [n for row in BM.MATRIX for n in row]
HERE = os.path.dirname(os.path.abspath(__file__))


class Stop(BaseException):
    """ends code.py's endless loop (not an Exception: code.py's error handler must not catch it)"""


class Event:
    def __init__(self, key_number, pressed):
        self.key_number, self.pressed = key_number, pressed


class Queue:
    def __init__(self):
        self.items, self.overflowed = [], False

    def get(self):
        return self.items.pop(0) if self.items else None

    def clear(self):
        self.items, self.overflowed = [], False


class Keys:
    """a keypad: the keys physically held, and its event queue. reset() assumes every key released, so the
    next scan reports the keys still held as fresh presses, as CircuitPython's keypad does."""

    def __init__(self, hw, interval=0.020):
        self.hw, self.events, self.held, self.resets, self.rescan = hw, Queue(), set(), 0, None
        self.scan_ms = round(interval * 1000)

    def reset(self):
        self.resets += 1
        self.rescan = self.hw.t + self.scan_ms

    def scan(self):
        if self.rescan == self.hw.t:
            self.events.items += [Event(k, True) for k in sorted(self.held)]
            self.rescan = None


class Encoder:
    def __init__(self, a, b, divisor=4):
        self.pins, self.divisor, self.position = (a, b), divisor, 0


class PWM:
    def __init__(self, pin, frequency=0):
        self.pin, self.frequency, self._duty, self.writes = pin, frequency, 0, 0

    @property
    def duty_cycle(self):
        return self._duty

    @duty_cycle.setter
    def duty_cycle(self, value):
        self._duty, self.writes = value, self.writes + 1


class Joystick:
    """one of the two devices. Both share one USB HID interface, as on the board: send_report waits for that
    interface, so the host's polling (hw.busy, hw.block) is the same for both"""
    usage_page, usage = 0x01, 0x04

    def __init__(self, hw):
        self.hw, self.reports, self.tries = hw, [], []

    def send_report(self, report):
        hw = self.hw
        self.tries.append(hw.t)
        if hw.busy:
            hw.busy -= 1
            hw.t += hw.block
            raise OSError("USB busy")
        self.reports.append(bytes(report))


class Hardware:
    """the stub modules, plus the clock that drives the script"""

    def __init__(self, ms, script=None, busy=0, usb_from=0, usb_gap=(0, 0), pico_test=False, edits=()):
        self.t, self.ms, self.script, self.usb_from, self.usb_gap = 0, ms, script or {}, usb_from, usb_gap
        self.pico_test, self.edits = pico_test, edits      # edits: (old, new) source lines, as on a first board
        self.busy = busy                      # sends that fail next, whichever device sends
        self.block = 0                        # ms a failing send blocks (2000 on the board); skips scripts
        self.joysticks = [Joystick(self), Joystick(self)]
        self.matrix = self.direct = None
        self.encoders, self.leds, self.duty = [], [], {}
        self.sleeps, self.reloads, self.printed = [], [], []
        hw = self

        class Matrix(Keys):
            def __init__(self, rows, cols, **kwargs):
                super().__init__(hw, kwargs.get("interval", 0.020)); hw.matrix = self
                self.rows, self.cols, self.kwargs = rows, cols, kwargs

        class Direct(Keys):
            def __init__(self, pins, **kwargs):
                super().__init__(hw, kwargs.get("interval", 0.020)); hw.direct = self
                self.pins, self.kwargs = pins, kwargs

        class Enc(Encoder):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs); hw.encoders.append(self)

        class Pwm(PWM):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs); hw.leds.append(self)

        pins = types.SimpleNamespace(**{f"GPIO{i}": f"GP{i}" for i in range(30)})
        self.modules = {
            "keypad": types.SimpleNamespace(KeyMatrix=Matrix, Keys=Direct),
            "microcontroller": types.SimpleNamespace(pin=pins),
            "pwmio": types.SimpleNamespace(PWMOut=Pwm),
            "rotaryio": types.SimpleNamespace(IncrementalEncoder=Enc),
            "usb_hid": types.SimpleNamespace(devices=self.joysticks),
            "supervisor": types.SimpleNamespace(runtime=self, reload=self.reload),   # runtime.usb_connected, below
            "time": types.SimpleNamespace(monotonic_ns=lambda: hw.t * 1_000_000, sleep=self.sleep),
            "traceback": types.SimpleNamespace(print_exception=self.printed.append),
        }

    @property
    def usb_connected(self):
        return self.t >= self.usb_from and not self.usb_gap[0] <= self.t < self.usb_gap[1]

    def reload(self):
        self.reloads.append(self.t)
        raise Stop                            # the VM restarts code.py: this run ends

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        if self.leds:                         # the LED as code.py left it in the pass for time self.t
            self.duty[self.t] = self.leds[0].duty_cycle
        self.t += 1
        if self.t >= self.ms:
            raise Stop
        for action in self.script.get(self.t, ()):
            action(self)
        for keys in (self.matrix, self.direct):
            keys.scan()

    def run(self):
        saved = {n: sys.modules.get(n) for n in self.modules}
        sys.modules.update(self.modules)
        path = os.path.join(HERE, "code.py")
        with open(path) as f:
            source = f.read()
        if self.pico_test:
            assert source.count("\nPICO_TEST = False\n") == 1
            source = source.replace("\nPICO_TEST = False\n", "\nPICO_TEST = True\n")
        for old, new in self.edits:
            assert source.count(old) == 1, old
            source = source.replace(old, new)
        try:
            self.code = {"__name__": "__main__", "__file__": path}   # code.py's globals, for the scripts
            exec(compile(source, path, "exec"), self.code)
        except Stop:
            pass
        finally:
            for n, m in saved.items():
                if m is None:
                    sys.modules.pop(n, None)
                else:
                    sys.modules[n] = m
        return self


def press(name, pressed, lost=False):
    """a matrix key goes down or up; lost: the keypad queue overflows and drops the event"""
    def act(hw):
        keys, number = (hw.direct, 0) if name == "FREQ_PUSH" else (hw.matrix, NAMES.index(name))
        (keys.held.add if pressed else keys.held.discard)(number)
        if lost:
            keys.events.overflowed = True
        else:
            keys.events.items.append(Event(number, pressed))
    return act


def step(ring_index, by):
    def act(hw):
        hw.encoders[ring_index].position += by
    return act


def pressed(report, device, name):
    b = BM.BUTTON[device][name]
    return bool(report[b >> 3] & (1 << (b & 7)))


def test_key_press_is_reported():
    hw = Hardware(400, {10: [press("AP", True)], 200: [press("AP", False)]}).run()
    reports = hw.joysticks[0].reports
    assert any(pressed(r, 1, "AP") for r in reports)
    assert not pressed(reports[-1], 1, "AP")


def test_usb_busy_does_not_stop_the_loop():
    # the first reports fail as if the PC were not reading yet; the loop runs on and the key press still
    # gets through on a later try
    hw = Hardware(4000, {10: [press("HDG", True)], 3500: [press("HDG", False)]}, busy=2).run()
    assert any(pressed(r, 1, "HDG") for r in hw.joysticks[0].reports)


def never_polled(ms):
    """a host that enumerates the panel but never reads it: every try blocks for 2 s and fails"""
    hw = Hardware(ms)
    hw.busy, hw.block = 10**6, 2000
    return hw.run()


def test_failed_sends_back_off():
    # code.py waits 1 s from the end of a failed try before the next one, doubling up to 8 s, instead of
    # trying in every loop pass. One back-off for both devices (they share the USB interface): the other
    # device waits too, so the loop stalls for 2 s of every 10 in the end, not 4
    hw = never_polled(40000)
    tries = sorted(t for j in hw.joysticks for t in j.tries)
    gaps = [b - a for a, b in zip(tries, tries[1:])]
    assert gaps == [2000 + wait for wait in (1000, 2000, 4000, 8000, 8000)]
    stalled = hw.ms - len(hw.sleeps)                  # ms not spent in 1 ms loop passes
    assert len(tries) == 6 and stalled == 6 * 2000      # 12 s of 40 (22 s with a back-off per device)


def test_backoff_ends_with_a_good_send():
    # after the host starts reading, a send goes through and the next change is sent at once again; a later
    # failure starts the back-off from 1 s again
    def fail_once(hw):
        hw.busy = 1
    hw = Hardware(9600, {8000: [press("AP", True)], 8500: [fail_once, press("AP", False)]}, busy=3).run()
    tries = hw.joysticks[0].tries
    assert tries[:4] == [0, 1000, 3000, 7000]                # 3 failed, the fourth went through
    first = next(t for t in tries if t >= 8000)
    assert first <= 8001 and pressed(hw.joysticks[0].reports[1], 1, "AP")
    assert [t for t in tries if t >= 8500] == [8500, 9500]   # failed, then 1 s later, not 8 s


def test_backoff_ends_when_usb_drops():
    # a host that comes back (a new boot) gets the current state at once, not after the old back-off
    hw = Hardware(4000, busy=3, usb_gap=(3500, 3600)).run()
    tries = hw.joysticks[0].tries
    assert tries[:3] == [0, 1000, 3000]                      # failed; the next try would be at 7000
    assert tries[3] == 3600 and len(hw.joysticks[0].reports) == 1


def test_a_failed_send_skips_the_other_device():
    # both devices have a report to send, and the first send fails: the other device waits for the same
    # back-off, so a pass never takes more than 2 s (a longer one would outlast SHIFT_MS, drop detents and
    # freeze the light)
    hw = never_polled(20000)
    passes = sorted(hw.duty)
    assert max(b - a for a, b in zip(passes, passes[1:])) == 2000 + 1
    one, two = hw.joysticks
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
    hw = Hardware(400, crash(error)).run()
    assert hw.printed == [error] and len(hw.reloads) == 1
    one, two = hw.joysticks
    assert any(pressed(r, 1, "AP") for r in one.reports)
    assert one.reports[-1] == bytes(BM.SIZE[1] // 8) and two.reports[-1] == bytes(BM.SIZE[2] // 8)
    assert hw.sleeps[-1] == 2


def test_error_while_usb_is_down_sends_nothing():
    # with USB down a send would only block for 2 s: the release is skipped (the host resets on its return)
    hw = Hardware(400, crash(ValueError("bug")), usb_gap=(50, 10**6)).run()
    assert len(hw.reloads) == 1
    assert all(t < 50 for j in hw.joysticks for t in j.tries)


def test_error_with_usb_busy_still_reloads():
    # releasing fails too (OSError from send_report): code.py still restarts
    def busy(hw):
        hw.busy = 10
    script = crash(ValueError("bug"))
    script[99] = [busy]
    hw = Hardware(400, script).run()
    assert len(hw.reloads) == 1


def test_error_releases_and_reloads_when_printing_fails():
    # formatting the traceback fails again (MemoryError on the board): the buttons are released before it,
    # and code.py still restarts
    def no_memory(e):
        hw.printed.append(e)
        raise MemoryError
    hw = Hardware(400, crash(MemoryError()))
    hw.modules["traceback"] = types.SimpleNamespace(print_exception=no_memory)
    hw.run()
    assert len(hw.printed) == 1 and len(hw.reloads) == 1
    one, two = hw.joysticks
    assert any(pressed(r, 1, "AP") for r in one.reports)
    assert one.reports[-1] == bytes(BM.SIZE[1] // 8) and two.reports[-1] == bytes(BM.SIZE[2] // 8)


def test_error_reloads_when_releasing_fails():
    # a release that raises something other than OSError (no memory for it): code.py still restarts
    def fail(hw):
        def no_memory(report):
            raise MemoryError
        for j in hw.joysticks:
            j.send_report = no_memory
    script = crash(ValueError("bug"))
    script[99] = [fail]
    hw = Hardware(400, script).run()
    assert len(hw.printed) == 1 and len(hw.reloads) == 1


def test_ctrl_c_releases_every_button():
    # Ctrl-C on the console ends code.py for the REPL: nothing stays held, and no reload
    hw = Hardware(400, crash(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        hw.run()
    assert hw.reloads == [] and hw.joysticks[0].reports[-1] == bytes(BM.SIZE[1] // 8)


def test_unit_light_is_written_only_on_a_change():
    hw = Hardware(600, {10: [press("SHIFT", True)], 60: [press("SHIFT", False)],
                        110: [press("HOME", True)], 160: [press("HOME", False)]}).run()
    unit = hw.leds[1]
    assert unit.duty_cycle > 0 and unit.writes == 2         # off at the start, on after SHIFT, HOME


def test_shift_light_is_written_only_on_a_change():
    # code.py asks for the level every pass (1 ms) but writes the PWM duty only when it changes
    hw = Hardware(3200, {10: [press("SHIFT", True)], 60: [press("SHIFT", False)]}).run()
    duty = [hw.duty[t] for t in sorted(hw.duty)]
    changes = sum(a != b for a, b in zip(duty, duty[1:]))
    assert changes >= 3 and hw.leds[0].writes == 1 + changes    # off at the start, on, pulses, off


@pytest.mark.parametrize("count", [0, 1])
def test_missing_joysticks_stop_code_py(count):
    # without boot.py's two joysticks (a fresh install) code.py stops with a hint instead of running half
    hw = Hardware(100)
    hw.modules["usb_hid"] = types.SimpleNamespace(devices=hw.joysticks[:count])
    with pytest.raises(RuntimeError, match="joysticks missing"):
        hw.run()
    assert hw.reloads == []


def test_pico_test_keeps_all_seven_encoders():
    # the bench must allocate the same 7 PIO encoders as the board, RANGE included
    board, pico = Hardware(5).run(), Hardware(5, pico_test=True).run()
    assert len(board.encoders) == len(pico.encoders) == 7


def test_encoder_step_is_reported():
    hw = Hardware(400, {10: [step(0, 1)]}).run()       # ALT/HDG outer ring, one slow detent
    assert any(pressed(r, 1, "ALT_100_UP") for r in hw.joysticks[0].reports)


def test_reversed_ring_counts_the_other_way():
    # the reverse flag in RINGS (for a ring that turns the wrong way on the first board): a clockwise count
    # of the ALT/HDG outer ring sends the counter-clockwise button, the other rings stay as they are
    reverse = ('("ALTHDG_OUTER", P.GPIO18, P.GPIO19, False)', '("ALTHDG_OUTER", P.GPIO18, P.GPIO19, True)')
    hw = Hardware(400, {10: [step(0, 1), step(1, 1)]}, edits=[reverse]).run()
    assert sent_names(hw, 1, ("ALT_100_UP", "ALT_100_DN", "HDG_1_UP", "HDG_1_DN")) == {"ALT_100_DN", "HDG_1_UP"}


def sent_names(hw, device, names):
    return {n for r in hw.joysticks[device - 1].reports for n in names if pressed(r, device, n)}


def test_two_detents_in_one_read_are_fast_unless_the_loop_stalled():
    alt = ("ALT_100_UP", "ALT_1000_UP")
    hw = Hardware(400, {10: [step(0, 2)]}).run()       # read in a normal pass: a fast turn
    assert sent_names(hw, 1, alt) == {"ALT_1000_UP"}
    pressed_then = []

    def look(hw):                                       # the back-off holds the report: ask the panel
        pressed_then.extend(BM.DEVICE[1][b] for b in hw.code["panel"].buttons(1))
    hw = Hardware(2100, {2001: [step(0, 2)], 2002: [look]}, busy=1)   # read in the pass after a failed 2 s send
    hw.block = 2000
    hw.run()
    assert hw.joysticks[0].tries == [0] and pressed_then == ["ALT_100_UP"]


def test_shift_light_pulses_on_the_led():
    # one run of code.py, the LED duty of every pass by its time: steady full, then dim and full phases in
    # the last second, never 0 before the drop, 0 after it
    hw = Hardware(3200, {10: [press("SHIFT", True)], 60: [press("SHIFT", False)]}).run()
    duty = hw.duty
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
    assert Hardware(100, tap).run().leds[0].duty_cycle > 0          # armed: amber on
    tap.update({150: [press("SHIFT", True)], 200: [press("SHIFT", False)]})
    assert Hardware(250, tap).run().leds[0].duty_cycle == 0         # tapped again: cancelled


def test_no_reports_before_usb_connects():
    # PC still booting: nothing is sent (send_report would block for 2 s), the loop and the light keep running
    sent = {}

    def count(hw):
        sent[hw.t] = len(hw.joysticks[0].reports)
    hw = Hardware(400, {10: [press("SHIFT", True)], 60: [press("SHIFT", False)], 150: [count], 300: [count]},
                  usb_from=200).run()
    assert hw.duty[100] > 0                              # the light came on while USB was down
    assert sent[150] == 0 and sent[300] >= 1             # nothing sent before USB, then the current state


def overflow(hw):
    hw.matrix.events.overflowed = True


def test_keypad_overflow_keeps_held_keys_pressed():
    # events were lost while AP is held: the keypad is reset and re-reports AP, and the PC sees AP held
    # throughout, not released and pressed again (which would toggle the autopilot off)
    hw = Hardware(400, {10: [press("AP", True)], 100: [overflow]}).run()
    reports = hw.joysticks[0].reports
    first = next(i for i, r in enumerate(reports) if pressed(r, 1, "AP"))
    assert hw.matrix.resets == 1 and all(pressed(r, 1, "AP") for r in reports[first:])


def test_keypad_overflow_releases_a_lost_release():
    # AP's release was among the lost events: once the keypad has rescanned, AP is released
    hw = Hardware(400, {10: [press("AP", True)], 100: [press("AP", False, lost=True)]}).run()
    reports = hw.joysticks[0].reports
    assert any(pressed(r, 1, "AP") for r in reports) and not pressed(reports[-1], 1, "AP")


def test_keypad_overflow_leaves_the_other_keypad_alone():
    # the matrix overflows while the FREQ knob (its own keypad) is pushed: the push stays held
    hw = Hardware(400, {10: [press("FREQ_PUSH", True)], 100: [overflow]}).run()
    reports = hw.joysticks[0].reports
    first = next(i for i, r in enumerate(reports) if pressed(r, 1, "FREQ_PUSH"))
    assert all(pressed(r, 1, "FREQ_PUSH") for r in reports[first:]) and hw.direct.resets == 0


def test_held_key_is_resent_after_usb_comes_back():
    # the PC reboots while AP is held: the new host assumes everything released, so the panel sends AP again
    sent = {}

    def count(hw):
        sent[hw.t] = len(hw.joysticks[0].reports)
    hw = Hardware(400, {10: [press("AP", True)], 190: [count]}, usb_gap=(100, 200)).run()
    reports = hw.joysticks[0].reports
    assert len(reports) > sent[190] and pressed(reports[-1], 1, "AP")
