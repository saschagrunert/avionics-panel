"""The vJoy output (sim/vjoy.py) without Windows: its struct against vJoy 2.2.2.0's header, the report of every
button of both joysticks against the firmware's descriptor and buttonmap.py, and its calls into a stand-in for
vJoyInterface.dll. The DLL itself, vJoy's driver and what MobiFlight sees are tested on a Windows PC."""
import ctypes
import io
import os
import re
import sys

import pytest

import sim.vjoy
from conftest import hid_parser
from sim import BM, Sim
from sim.hardware import FIRMWARE, Board
from sim.vjoy import (
    VJD_STAT_BUSY,
    VJD_STAT_FREE,
    VJD_STAT_MISS,
    VJD_STAT_OWN,
    VJD_STAT_UNKN,
    Position,
    VJoy,
    VJoyError,
    load,
    position,
)

REPORT_ID = {1: 4, 2: 5}
BUTTONS = os.path.join(FIRMWARE, "BUTTONS.md")
# JOYSTICK_POSITION_V3, public.h L316-361 at vJoy's tag v2.2.2.0, field by field: (name, offset, size)
HEADER = [("bDevice", 0, 1)] + [(name, 4 * i, 4) for i, name in enumerate((
    "wThrottle", "wRudder", "wAileron", "wAxisX", "wAxisY", "wAxisZ", "wAxisXRot", "wAxisYRot", "wAxisZRot",
    "wSlider", "wDial", "wWheel", "wAccelerator", "wBrake", "wClutch", "wSteering", "wAxisVX", "wAxisVY",
    "lButtons", "bHats", "bHatsEx1", "bHatsEx2", "bHatsEx3", "lButtonsEx1", "lButtonsEx2", "lButtonsEx3",
    "wAxisVZ", "wAxisVBRX", "wAxisVBRY", "wAxisVBRZ"), 1)]


def test_the_struct_is_the_headers():
    assert [(name, getattr(Position, name).offset, getattr(Position, name).size) for name, _ in Position._fields_] \
        == HEADER
    assert ctypes.sizeof(Position) == 124
    signed = {name for name, kind in Position._fields_ if kind is ctypes.c_int32}   # LONG; BYTE, DWORD unsigned
    assert signed == {name for name, _, _ in HEADER if name[0] in "wl"}


def pressed(p):
    """vJoy's buttons a Position presses, numbered from 1"""
    bits = int.from_bytes(b"".join(getattr(p, w).to_bytes(4, "little", signed=True) for w in sim.vjoy.WORDS),
                          "little")
    return [n + 1 for n in range(128) if bits >> n & 1]


def documented():
    """{device: {name: button number}} of BUTTONS.md's table"""
    out = {1: {}, 2: {}}
    with open(BUTTONS, encoding="utf-8") as f:
        for line in f:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("|") and cells[2:] != ["Device 1", "Device 2"] and cells[0] != "---":
                for device, cell in zip((1, 2), cells[2:], strict=True):
                    if cell:
                        out[device][cells[0]] = int(cell)
    return out


def test_every_button_of_both_joysticks_is_its_vjoy_button():
    # each bit of each report, read with boot.py's descriptor (hid-tools' parser), is vJoy's button of the same
    # number on the device of the same number, alone; for the buttons buttonmap.py names, BUTTONS.md's number
    hid = hid_parser()
    rdesc = hid.ReportDescriptor.from_bytes(list(b"".join(d.report_descriptor for d in Board().boot().devices)))
    numbers = documented()
    for device, report_id in REPORT_ID.items():
        size, named = BM.SIZE[device], BM.DEVICE[device]
        assert set(numbers[device]) == set(named)
        for bit in range(size):
            report = bytearray([report_id]) + bytes(size // 8)
            report[1 + bit // 8] |= 1 << bit % 8
            usages = [f.usage & 0xFFFF for f in rdesc.input_reports[report_id] if f.get_values(list(report)) == [1]]
            p = position(device, report)
            assert pressed(p) == usages == [bit + 1] and p.bDevice == device
            if bit < len(named):
                assert numbers[device][named[bit]] == bit + 1
    assert position(1, b"\4" + b"\xff" * 16).lButtonsEx3 == -1      # LONG: button 128 is the sign bit


class Dll:
    """vJoyInterface.dll's functions as sim.vjoy calls them; calls has every call"""

    def __init__(self, enabled=True, status=None, buttons=None, acquire=(1, 2), update=True):
        self.enabled, self.update, self.acquire = enabled, update, acquire
        self.status = {1: VJD_STAT_FREE, 2: VJD_STAT_FREE} if status is None else status
        self.buttons = buttons or {1: 128, 2: 64}
        self.calls, self.positions = [], []

    def vJoyEnabled(self):
        self.calls.append(("vJoyEnabled",))
        return self.enabled

    def GetVJDStatus(self, n):
        self.calls.append(("GetVJDStatus", n))
        return self.status.get(n, VJD_STAT_MISS)

    def GetVJDButtonNumber(self, n):
        self.calls.append(("GetVJDButtonNumber", n))
        return self.buttons[n]

    def GetOwnerPid(self, n):
        return 4711

    def AcquireVJD(self, n):
        self.calls.append(("AcquireVJD", n))
        return n in self.acquire

    def RelinquishVJD(self, n):
        self.calls.append(("RelinquishVJD", n))

    def UpdateVJD(self, n, p):
        self.calls.append(("UpdateVJD", n, tuple(pressed(p))))
        self.positions.append((n, bytes(p)))
        return self.update


CHECKS = [("vJoyEnabled",), ("GetVJDStatus", 1), ("GetVJDButtonNumber", 1), ("GetVJDStatus", 2),
          ("GetVJDButtonNumber", 2), ("AcquireVJD", 1), ("AcquireVJD", 2)]


def test_reports_go_one_update_each_and_close_lets_go():
    dll = Dll()
    vjoy = VJoy(Board().boot(), dll)
    assert dll.calls == CHECKS
    vjoy.send(1, b"\4\1" + bytes(15))
    vjoy.send(2, b"\5\0\0\0\0\0\0\0\x80")
    vjoy.close()
    vjoy.close()                               # once is enough
    assert dll.calls[len(CHECKS):] == [("UpdateVJD", 1, (1,)), ("UpdateVJD", 2, (64,)), ("UpdateVJD", 2, ()),
                                        ("RelinquishVJD", 2), ("UpdateVJD", 1, ()), ("RelinquishVJD", 1)]
    n, raw = dll.positions[0]
    assert len(raw) == 124 and raw[0] == 1 and raw[76:80] == b"\1\0\0\0" and raw[80:96] == b"\xff" * 16


def test_a_device_this_program_owns_already_is_taken_again():
    VJoy(Board().boot(), Dll(status={1: VJD_STAT_OWN, 2: VJD_STAT_FREE}))


@pytest.mark.parametrize("dll, message", [
    (Dll(enabled=False), "the vJoy driver is not enabled"),
    (Dll(status={1: VJD_STAT_FREE}), "vJoy device 2 is not configured: run vjoy-setup.bat as administrator"),
    (Dll(status={1: VJD_STAT_BUSY, 2: VJD_STAT_FREE}),
     r"vJoy device 1 is in use by another program \(process 4711\): close it \(another simulator window\?\); in "
     "MobiFlight, remove the profile's vJoy outputs"),
    (Dll(status={1: VJD_STAT_FREE, 2: VJD_STAT_UNKN}), r"vJoy device 2 is in an unknown state \(4\)"),
    (Dll(buttons={1: 128, 2: 32}), "vJoy device 2 has 32 buttons, not 64: run vjoy-setup.bat as administrator"),
])
def test_a_missing_or_wrong_device_is_named_before_anything_is_acquired(dll, message):
    with pytest.raises(VJoyError, match=message):
        VJoy(Board().boot(), dll)
    assert not [c for c in dll.calls if c[0] in ("AcquireVJD", "UpdateVJD")]


def test_the_keyboard_mode_is_refused_before_anything_is_loaded():
    dll = Dll()
    with pytest.raises(VJoyError, match="vJoy takes the joysticks: the keyboard mode goes .* through --sendinput"):
        VJoy(Board(keyboard=True).boot(), dll)
    assert dll.calls == []


def test_a_device_that_cannot_be_acquired_lets_go_of_the_other():
    dll = Dll(acquire=(1,))
    with pytest.raises(VJoyError, match="vJoy device 2 cannot be acquired"):
        VJoy(Board().boot(), dll)
    assert dll.calls[-4:] == [("AcquireVJD", 1), ("AcquireVJD", 2), ("UpdateVJD", 1, ()), ("RelinquishVJD", 1)]


def test_a_report_vjoy_refuses_raises():
    with pytest.raises(VJoyError, match="vJoy device 1 took no report"):
        VJoy(Board().boot(), Dll(update=False)).send(1, b"\4" + bytes(16))


def test_a_report_after_close_goes_nowhere():
    # the console handler can close while code.py's thread still sends
    dll = Dll()
    vjoy = VJoy(Board().boot(), dll)
    vjoy.close()
    vjoy.send(1, b"\4\1" + bytes(15))
    assert dll.calls[-1] == ("RelinquishVJD", 1)


class Kernel32:
    def __init__(self):
        self.handlers = []

    def SetConsoleCtrlHandler(self, handler, add):
        self.handlers.append((handler, add))
        return 1


def test_ctrl_break_and_closing_the_window_let_go_and_ctrl_c_goes_on_to_python():
    released = [("UpdateVJD", 2, ()), ("RelinquishVJD", 2), ("UpdateVJD", 1, ()), ("RelinquishVJD", 1)]
    dll, kernel32 = Dll(), Kernel32()
    vjoy = VJoy(Board().boot(), dll, kernel32)
    [(handler, add)] = kernel32.handlers
    assert add and handler is vjoy.handler
    vjoy.send(1, b"\4\1" + bytes(15))
    calls = len(dll.calls)
    assert handler(0) == 0 and len(dll.calls) == calls             # Ctrl-C: KeyboardInterrupt in Python
    assert handler(1) == 0 and dll.calls[calls:] == released       # Ctrl-Break: Windows then ends the process
    assert handler(2) == 1 and dll.calls[calls:] == released       # the window closes: Windows waits for it
    dll = Dll()
    vjoy = VJoy(Board().boot(), dll, Kernel32())
    assert vjoy.handler(2) == 1 and dll.calls[-4:] == released     # without a Ctrl-Break before it too


def test_the_console_handler_is_windows_only(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert VJoy(Board().boot(), Dll()).handler is None


def test_the_dll_gets_every_signature(monkeypatch, tmp_path):
    # a misspelt name would only fail on Windows: every function of SIGNATURES is looked up and typed
    class Function:
        restype = argtypes = None

    class Library:
        def __init__(self, path):
            self.path, self.functions = path, {}

        def __getattr__(self, name):
            return self.functions.setdefault(name, Function())

    path = tmp_path / "vJoyInterface.dll"
    path.write_bytes(b"MZ")
    monkeypatch.setattr(ctypes, "CDLL", Library)
    dll = load(str(path))
    assert dll.path == str(path)
    assert {name: (f.restype, f.argtypes) for name, f in dll.functions.items()} == {
        "vJoyEnabled": (ctypes.c_int, []),
        "GetVJDStatus": (ctypes.c_int, [ctypes.c_uint]),
        "GetVJDButtonNumber": (ctypes.c_int, [ctypes.c_uint]),
        "GetOwnerPid": (ctypes.c_int, [ctypes.c_uint]),
        "AcquireVJD": (ctypes.c_int, [ctypes.c_uint]),
        "RelinquishVJD": (None, [ctypes.c_uint]),
        "UpdateVJD": (ctypes.c_int, [ctypes.c_uint, ctypes.POINTER(Position)]),
    }
    monkeypatch.setenv("VJOY_DLL", str(path))
    monkeypatch.setattr(sys, "platform", "win32")
    assert load().path == str(path)


def test_the_dll_is_looked_for_on_windows_only(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(VJoyError, match="vJoy runs on Windows only"):
        load()
    dll = tmp_path / "vJoyInterface.dll"
    # (start.bat always asks for vJoy: the message names the way to the page without it)
    with pytest.raises(VJoyError, match=r"vJoy is not installed: there is no .*vJoyInterface.dll\. .*without vJoy, "
                                        r".* run python\\python\.exe -m sim\.page --open$"):
        load(str(dll))
    dll.write_bytes(b"MZ")
    with pytest.raises(VJoyError, match="vJoyInterface.dll does not load: "):
        load(str(dll))


def test_vjoy_setup_makes_the_devices_vjoy_asks_for():
    # windows/vjoy-setup.bat's button counts are the ones VJoy checks (a smaller one stops the simulator at the
    # start), and sim/vjoy.py's docstring gives the same commands
    with open(os.path.join(os.path.dirname(FIRMWARE), "windows", "vjoy-setup.bat"), encoding="utf-8") as f:
        setup = [(int(n), int(b)) for n, b in re.findall(r'^"%VJOYCONFIG%" (\d) -f -a -b (\d+)$', f.read(), re.M)]
    docstring = [(int(n), int(b)) for n, b in re.findall(r"^ +vJoyConfig (\d) -f -a -b (\d+)$", sim.vjoy.__doc__, re.M)]
    assert setup == docstring == sorted(VJoy(Board().boot(), Dll()).devices.values()) == [(1, 128), (2, 64)]


def test_the_buttons_vjoy_gets_are_the_ones_the_firmware_sends():
    # a scenario's reports through VJoy name, by vJoy's button numbers, the buttons the scenario pressed
    sim = Sim()
    for key in ("AP", "SHIFT", "FD", "SHIFT", "HOME", "ENT", "SHIFT", "FMS_PUSH"):
        sim.tap(key)
    sim.turn("FREQ_INNER", 2)
    dll = Dll()
    vjoy = VJoy(Board().boot(), dll)
    for device in REPORT_ID:
        for _, report in sim.reports(device):
            vjoy.send(device, report)
    for device in REPORT_ID:
        updates = [[BM.DEVICE[device][b - 1] for b in c[2]] for c in dll.calls[len(CHECKS):] if c[1] == device]
        assert updates == [names for _, names in sim.buttons(device)]
    assert {n for c in dll.calls[len(CHECKS):] for n in c[2]} >= {BM.BUTTON[1]["AP"] + 1, BM.BUTTON[2]["ENT"] + 1}


def test_lines_from_stdin_go_to_vjoy(monkeypatch, capsys):
    dll = Dll()
    monkeypatch.setattr(sim.vjoy, "load", lambda: dll)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"press AP\nfly\nlights\n")))
    sim.vjoy.main([])
    out, err = capsys.readouterr()
    assert out.endswith("\nSHIFT 0x0000 UNIT 0x0000\n") and "fly: actions:" in err
    assert ("UpdateVJD", 1, (BM.BUTTON[1]["AP"] + 1,)) in dll.calls
    assert dll.calls[-2:] == [("UpdateVJD", 1, ()), ("RelinquishVJD", 1)]


def test_main_says_what_is_wrong(monkeypatch):
    monkeypatch.setattr(sim.vjoy, "load", lambda: Dll(status={}))
    with pytest.raises(SystemExit, match="sim.vjoy: vJoy device 1 is not configured"):
        sim.vjoy.main([])


def test_main_ends_with_the_reason_when_vjoy_refuses_a_report(monkeypatch):
    dll = Dll(update=False)
    monkeypatch.setattr(sim.vjoy, "load", lambda: dll)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"press AP\n")))
    with pytest.raises(SystemExit, match="sim.vjoy: vJoy device 1 took no report"):
        sim.vjoy.main([])
    assert dll.calls[-1] == ("RelinquishVJD", 1)


def test_ctrl_c_lets_go_and_ends_quietly(monkeypatch):
    class Interrupted(io.TextIOWrapper):
        def __iter__(self):
            raise KeyboardInterrupt

    dll = Dll()
    monkeypatch.setattr(sim.vjoy, "load", lambda: dll)
    monkeypatch.setattr(sys, "stdin", Interrupted(io.BytesIO()))
    sim.vjoy.main([])
    assert dll.calls[-1] == ("RelinquishVJD", 1)
