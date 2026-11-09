"""Host smoke tests for code.py: runs its main loop against stub CircuitPython modules.

code.py itself needs the hardware (keypad, rotaryio, pwmio, usb_hid), so these stubs stand in for it:
the tests script key presses and encoder steps per millisecond and record the HID reports it sends.
"""
import os
import runpy
import sys
import types

import buttonmap as BM

HERE = os.path.dirname(os.path.abspath(__file__))


class Stop(Exception):
    """ends code.py's endless loop"""


class Event:
    def __init__(self, key_number, pressed):
        self.key_number, self.pressed = key_number, pressed


class Queue:
    def __init__(self):
        self.items = []

    def get(self):
        return self.items.pop(0) if self.items else None


class Keys:
    def __init__(self, *args, **kwargs):
        self.events = Queue()


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

    def __init__(self, ms, script=None, busy=0):
        self.t, self.ms, self.script = 0, ms, script or {}
        self.joysticks = [Joystick(busy), Joystick(busy)]
        self.matrix = self.direct = None
        self.encoders, self.leds = [], []
        hw = self

        class Matrix(Keys):
            def __init__(self, *args, **kwargs):
                super().__init__(); hw.matrix = self

        class Direct(Keys):
            def __init__(self, *args, **kwargs):
                super().__init__(); hw.direct = self

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
            "time": types.SimpleNamespace(monotonic_ns=lambda: hw.t * 1_000_000, sleep=self.sleep),
        }

    def sleep(self, _seconds):
        self.t += 1
        if self.t >= self.ms:
            raise Stop
        for action in self.script.get(self.t, ()):
            action(self)

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


def press(name, pressed):
    number = [n for row in BM.MATRIX for n in row].index(name)
    return lambda hw: hw.matrix.events.items.append(Event(number, pressed))


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
