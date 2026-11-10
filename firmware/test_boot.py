"""Host tests for boot.py: runs it against stub CircuitPython modules.

The stub matrix has one switch, SHIFT, from its column pin to its row pin (through the diode, anode on the
column, as on the board): the column only reads low while SHIFT is held and the row pin drives low.
"""
import os
import sys
import types

import buttonmap as BM

HERE = os.path.dirname(os.path.abspath(__file__))
SHIFT_PINS = ("GP2", "GP6")        # row, column of SHIFT; tests/test_pins.py checks them against the board


class Boot:
    def __init__(self, shift=False, pins=SHIFT_PINS):
        self.shift, (self.row, self.col) = shift, pins
        self.calls, self.ios, self.devices, self.enabled = [], {}, [], None
        boot = self

        class Pull:
            UP, DOWN = "up", "down"

        class DigitalInOut:
            def __init__(self, pin):
                assert pin not in boot.ios or boot.ios[pin].released, f"{pin} claimed twice"
                self.pin, self.mode, self.pull, self.out, self.released = pin, "in", None, None, False
                boot.ios[pin] = self

            def switch_to_input(self, pull=None):
                self.mode, self.pull = "in", pull

            def switch_to_output(self, value=False, drive_mode=None):
                self.mode, self.out = "out", value

            @property
            def value(self):
                assert not self.released and self.mode == "in"
                other = boot.ios.get(boot.row if self.pin == boot.col else None)
                if boot.shift and other and not other.released and other.mode == "out" and not other.out:
                    return False                   # current through the diode and the closed switch
                assert self.pull == Pull.UP, f"{self.pin} floats"
                return True

            def deinit(self):
                self.released = True

        def device(**kw):
            boot.devices.append(kw)
            return kw

        def call(name):
            return lambda *args: boot.calls.append((name,) + args)

        pins = types.SimpleNamespace(**{f"GPIO{i}": f"GP{i}" for i in range(30)})
        self.modules = {
            "digitalio": types.SimpleNamespace(DigitalInOut=DigitalInOut, Pull=Pull),
            "microcontroller": types.SimpleNamespace(pin=pins),
            "storage": types.SimpleNamespace(disable_usb_drive=call("disable_usb_drive")),
            "supervisor": types.SimpleNamespace(set_usb_identification=call("set_usb_identification")),
            "time": types.SimpleNamespace(sleep=lambda s: None),
            "usb_cdc": types.SimpleNamespace(disable=call("usb_cdc.disable")),
            "usb_hid": types.SimpleNamespace(Device=device, enable=self.enable),
            "usb_midi": types.SimpleNamespace(disable=call("usb_midi.disable")),
        }

    def enable(self, devices):
        self.enabled = devices

    def run(self):
        saved = {n: sys.modules.get(n) for n in self.modules}
        sys.modules.update(self.modules)
        try:
            path = os.path.join(HERE, "boot.py")
            with open(path) as f:
                exec(compile(f.read(), path, "exec"), {"__name__": "__main__", "__file__": path})
        finally:
            for n, m in saved.items():
                if m is None:
                    sys.modules.pop(n, None)
                else:
                    sys.modules[n] = m
        return self

    @property
    def hidden(self):
        return {"disable_usb_drive", "usb_cdc.disable"} & {c[0] for c in self.calls}


def test_without_shift_the_drive_and_console_are_hidden():
    boot = Boot(shift=False).run()
    assert boot.hidden == {"disable_usb_drive", "usb_cdc.disable"}
    assert len(boot.enabled) == 2


def test_shift_held_keeps_the_drive_and_console():
    boot = Boot(shift=True).run()
    assert not boot.hidden and len(boot.enabled) == 2


def test_shift_pins_are_released_for_code_py():
    for shift in (False, True):
        boot = Boot(shift=shift).run()
        assert set(boot.ios) == set(SHIFT_PINS) and all(io.released for io in boot.ios.values())


def test_shift_is_matrix_row_3_column_3():
    assert BM.MATRIX[3][3] == "SHIFT"


# ---------------- HID descriptors ----------------
def hid_items(descriptor):
    """HID short items: (type, tag, value); type 0 main, 1 global, 2 local"""
    i, out = 0, []
    while i < len(descriptor):
        prefix = descriptor[i]
        size = (0, 1, 2, 4)[prefix & 3]
        value = int.from_bytes(bytes(descriptor[i + 1:i + 1 + size]), "little")
        out.append(((prefix >> 2) & 3, prefix >> 4, value))
        i += 1 + size
    assert i == len(descriptor), "descriptor ends inside an item"
    return out


def parse(descriptor):
    """what one joystick descriptor declares: usage page / usage of the collection, report id, and its
    inputs as (usage page, first usage, last usage, logical min, max, size, count)"""
    state, local, depth, out = {}, {}, 0, {"inputs": []}
    for kind, tag, value in hid_items(descriptor):
        if kind == 1:
            state[{0: "page", 1: "lmin", 2: "lmax", 7: "size", 8: "id", 9: "count"}[tag]] = value
        elif kind == 2:
            local[{0: "usage", 1: "umin", 2: "umax"}[tag]] = value
        elif tag == 0xA:                                   # Collection
            out.setdefault("app", (state["page"], local["usage"], value))
            depth += 1
        elif tag == 0xC:                                   # End Collection
            depth -= 1
        elif tag == 0x8:                                   # Input
            out["id"] = state["id"]
            out["inputs"].append((state["page"], local["umin"], local["umax"], state["lmin"], state["lmax"],
                                  state["size"], state["count"], value))
        if kind == 0:
            local = {}
    assert depth == 0, "unbalanced collections"
    return out


def test_hid_descriptors_match_buttonmap():
    # two joysticks, each one application collection with one array of 1-bit buttons: as many buttons as
    # buttonmap.SIZE says, a report as long as the device says, report IDs as the device says
    boot = Boot().run()
    assert list(boot.enabled) == boot.devices and len(boot.devices) == 2
    ids = []
    for n, dev in zip((1, 2), boot.devices):
        d = parse(dev["report_descriptor"])
        assert d["app"] == (0x01, 0x04, 0x01)              # Generic Desktop, Joystick, Application
        assert (dev["usage_page"], dev["usage"]) == (0x01, 0x04)
        assert dev["report_ids"] == (d["id"],) and d["id"] != 0
        assert d["inputs"] == [(0x09, 1, BM.SIZE[n], 0, 1, 1, BM.SIZE[n], 0x02)]   # Button 1..N, Data Var Abs
        assert dev["in_report_lengths"] == (BM.SIZE[n] // 8,) and BM.SIZE[n] % 8 == 0
        assert dev["out_report_lengths"] == (0,)
        ids.append(d["id"])
    assert len(set(ids)) == 2
