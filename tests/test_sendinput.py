"""The Windows keystroke output of the keyboard mode (sim/sendinput.py) without Windows: its structs against
winuser.h's layout on 64-bit Windows, the keystrokes it makes of the keyboard's reports, and its calls into a
stand-in for user32.dll. Windows itself, and the sim taking the keys, are tested on Windows."""
import ctypes
import sys

import pytest

from sim import BM, FUNCTIONS, Sim
from sim.hardware import Board, keys
from sim.sendinput import INPUT, KEYBDINPUT, KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE, SCAN, SendInput

pytestmark = pytest.mark.skipif(ctypes.sizeof(ctypes.c_void_p) != 8, reason="the layout of 64-bit Windows")


class User32:
    """user32.dll's SendInput as sim.sendinput calls it: calls has the keystrokes of each call, as (scan code,
    up)"""

    def __init__(self, take=None):
        self.calls, self.take = [], take
        user32 = self

        def send(n, inputs, size):
            assert size == ctypes.sizeof(INPUT) and all(inputs[i].type == 1 for i in range(n))
            assert all(inputs[i].ki.dwFlags & KEYEVENTF_SCANCODE and not inputs[i].ki.wVk for i in range(n))
            ki = [inputs[i].ki for i in range(n)]
            user32.calls.append([(k.wScan | (0xE000 if k.dwFlags & KEYEVENTF_EXTENDEDKEY else 0),
                                  bool(k.dwFlags & KEYEVENTF_KEYUP)) for k in ki])
            return n if user32.take is None else user32.take
        self.SendInput = send


class Kernel32:
    def __init__(self):
        self.handlers = []

    def SetConsoleCtrlHandler(self, handler, add):
        self.handlers.append((handler, add))
        return 1


def output(user32=None, kernel32=None):
    return SendInput(Board(keyboard=True).boot(), user32 or User32(), kernel32)


def test_the_structs_are_winusers():
    # INPUT: DWORD type, then the union at 8, as large as MOUSEINPUT (32 bytes); KEYBDINPUT: WORD wVk, WORD wScan,
    # DWORD dwFlags, DWORD time, ULONG_PTR dwExtraInfo
    assert ctypes.sizeof(INPUT) == 40 and INPUT.u.offset == 8 and ctypes.sizeof(KEYBDINPUT) == 24
    assert [(n, getattr(KEYBDINPUT, n).offset) for n, _ in KEYBDINPUT._fields_] == [
        ("wVk", 0), ("wScan", 2), ("dwFlags", 4), ("time", 8), ("dwExtraInfo", 16)]


F1, INSERT, UP = 0x3A, 0x49, 0x52
LCTRL, LSHIFT, LALT, RCTRL, RSHIFT = 0x1D, 0x2A, 0x38, 0xE01D, 0x36   # their scan codes
ALL_UP = [(LCTRL, True), (LSHIFT, True), (LALT, True), (RCTRL, True), (RSHIFT, True)]


def test_every_shortcut_has_its_scan_codes():
    # Microsoft's table: F1 to F10 0x3B to 0x44, F11 0x57, F12 0x58; Insert, Home, Page Up, Delete, End, Page Down
    # and the arrows right, left, down, up as extended keys (E0 and a code)
    assert {k for _, k in FUNCTIONS} <= set(SCAN)
    assert [SCAN[F1 + i] for i in range(12)] == [*range(0x3B, 0x45), 0x57, 0x58]
    assert [SCAN[k] for k in range(INSERT, UP + 1)] == [0xE052, 0xE047, 0xE049, 0xE053, 0xE04F, 0xE051, 0xE04D,
                                                        0xE04B, 0xE050, 0xE048]


def test_a_report_sequence_becomes_keystrokes_in_order():
    # modifiers down before the key and up after it, right Ctrl and the navigation keys as extended keys; a report
    # that changes both lets the key up first
    user32 = User32()
    out = output(user32)
    for report in ((keys.RC | keys.LA, 0, 0), (keys.RC | keys.LA, 0, INSERT), (keys.RC | keys.LA, 0, 0),
                   (keys.LC | keys.RS, 0, 0), (keys.LC | keys.RS, 0, F1 + 11), (0, 0, 0)):
        out.send(1, bytes(report) + bytes(5))
    out.send(1, bytes(keys.REPORT))                                  # no change: no call
    assert user32.calls == [[(LALT, False), (RCTRL, False)], [(0xE052, False)], [(0xE052, True)],
                            [(LALT, True), (RCTRL, True), (LCTRL, False), (RSHIFT, False)], [(0x58, False)],
                            [(0x58, True), (LCTRL, True), (RSHIFT, True)]]


def test_the_keys_the_panel_types_reach_windows():
    # a scenario's reports through SendInput: each function's key goes down once, in order, and nothing stays down
    sim = Sim(keyboard=True)
    for key in ("AP", "SHIFT", "FD", "SHIFT", "HOME", "COM_SWAP"):
        sim.tap(key)
    user32 = User32()
    out = output(user32)
    for _, report in sim.reports(1):
        out.send(1, report)
    down = [scan for call in user32.calls for scan, up in call if not up and scan in SCAN.values()]
    assert down == [SCAN[keys.shortcut(d, BM.BUTTON[d][n])[1]] for d, n in ((1, "AP"), (1, "YD"), (2, "COM_SWAP"))]
    held = {}
    for call in user32.calls:
        for scan, up in call:
            held[scan] = not up
    assert not any(held.values())


def test_close_lets_go_and_nothing_follows():
    user32 = User32()
    out = output(user32)
    out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))
    out.close()
    out.close()                                                      # once is enough
    out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))                  # code.py's thread, after the window closed
    assert user32.calls == [[(RSHIFT, False), (0x3B, False)], [(0x3B, True), *ALL_UP]]


def test_keystrokes_windows_does_not_take_raise_and_close_lets_go_of_them():
    # Windows takes a part, or none while a UAC prompt or the lock screen is up: the next report is told from the
    # last one it took in full, and close() lets go of the keys of both and of every modifier
    with pytest.raises(OSError, match="Windows took 1 of 2 keystrokes: a prompt or another program blocks them"):
        output(User32(take=1)).send(1, bytes((keys.RS | keys.RC, 0, 0)) + bytes(5))
    user32 = User32()
    out = output(user32)
    out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))
    user32.take = 0
    with pytest.raises(OSError, match="Windows took 0 of 4 keystrokes"):
        out.send(1, bytes((keys.RC, 0, UP)) + bytes(5))
    user32.take = None
    out.send(1, bytes((keys.RC, 0, 0)) + bytes(5))
    out.close()
    assert user32.calls[2:] == [[(0x3B, True), (RSHIFT, True), (RCTRL, False)], [(0xE048, True), *ALL_UP]]


def test_ctrl_break_and_closing_the_window_let_go_and_ctrl_c_goes_on_to_python():
    user32, kernel32 = User32(), Kernel32()
    out = output(user32, kernel32)
    [(handler, add)] = kernel32.handlers
    assert add and handler is out.handler
    out.send(1, bytes((0, 0, UP)) + bytes(5))
    assert handler(0) == 0 and len(user32.calls) == 1               # Ctrl-C: KeyboardInterrupt in Python
    assert handler(1) == 0 and user32.calls[-1] == [(0xE048, True), *ALL_UP]   # Ctrl-Break: Windows ends it
    assert handler(2) == 1 and len(user32.calls) == 2               # the window closes: let go already


def test_the_joystick_mode_and_other_systems_are_refused(monkeypatch):
    with pytest.raises(OSError, match="SendInput takes the keyboard mode's keys: add --keyboard"):
        SendInput(Board().boot(), User32())
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(OSError, match="SendInput runs on Windows only"):
        SendInput(Board(keyboard=True).boot())
