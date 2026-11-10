"""Host smoke tests for code.py: runs its main loop against stub CircuitPython modules.

code.py itself needs the hardware (keypad, rotaryio, pwmio, usb_hid), so these stubs stand in for it:
the tests script key presses and encoder steps per millisecond and record the HID reports it sends.
"""
import os
import runpy
import sys
import types

import buttonmap as BM

NAMES = [n for row in BM.MATRIX for n in row]
HERE = os.path.dirname(os.path.abspath(__file__))


class Stop(Exception):
    """ends code.py's endless loop"""


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
        self.pins, self.position = (a, b), 0


class PWM:
    def __init__(self, pin, frequency=0):
        self.pin, self.duty_cycle = pin, 0


class Joystick:
    usage_page, usage = 0x01, 0x04

    def __init__(self, busy=0):
        self.busy, self.reports = busy, []

    def send_report(self, report):
        if self.busy:
            self.busy -= 1
            raise OSError("USB busy")
        self.reports.append(bytes(report))


class Hardware:
    """the stub modules, plus the clock that drives the script"""

    def __init__(self, ms, script=None, busy=0, usb_from=0, usb_gap=(0, 0)):
        self.t, self.ms, self.script, self.usb_from, self.usb_gap = 0, ms, script or {}, usb_from, usb_gap
        self.joysticks = [Joystick(busy), Joystick(busy)]
        self.matrix = self.direct = None
        self.encoders, self.leds, self.duty = [], [], {}
        hw = self

        class Matrix(Keys):
            def __init__(self, *args, **kwargs):
                super().__init__(hw, kwargs.get("interval", 0.020)); hw.matrix = self

        class Direct(Keys):
            def __init__(self, *args, **kwargs):
                super().__init__(hw, kwargs.get("interval", 0.020)); hw.direct = self

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
            "supervisor": types.SimpleNamespace(runtime=self),   # runtime.usb_connected, see below
            "time": types.SimpleNamespace(monotonic_ns=lambda: hw.t * 1_000_000, sleep=self.sleep),
        }

    @property
    def usb_connected(self):
        return self.t >= self.usb_from and not self.usb_gap[0] <= self.t < self.usb_gap[1]

    def sleep(self, _seconds):
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
        try:
            runpy.run_path(os.path.join(HERE, "code.py"), run_name="__main__")
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
    # the first 50 reports fail as if the PC were still booting; the key press still gets through
    hw = Hardware(400, {10: [press("HDG", True)], 200: [press("HDG", False)]}, busy=50).run()
    assert any(pressed(r, 1, "HDG") for r in hw.joysticks[0].reports)


def test_encoder_step_is_reported():
    hw = Hardware(400, {10: [step(0, 1)]}).run()       # ALT/HDG outer ring, one slow detent
    assert any(pressed(r, 1, "ALT_100_UP") for r in hw.joysticks[0].reports)


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


def test_boot_report_sizes_match_buttonmap():
    # boot.py declares the two joysticks' button counts; buttonmap.SIZE must agree, or reports get cut off
    import re
    with open(os.path.join(HERE, "boot.py")) as f:
        sizes = [int(n) for n in re.findall(r"joystick\(\d+, (\d+)\)", f.read())]
    assert sizes == [BM.SIZE[1], BM.SIZE[2]]


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
