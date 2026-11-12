"""The live panel (sim/live.py) in keyboard mode as keystrokes on Windows, through SendInput: each keyboard report
code.py sends becomes the key presses and releases it differs by from the one before, by their scan codes, as a
keyboard's would. Windows gives them to the window that has the focus: keep the sim in front and play the panel
page from another device, such as a tablet:

    python -m sim.page --keyboard --sendinput --host 0.0.0.0

docs/using/simulator.md has the steps.
"""
import ctypes
import sys
import threading

from sim.hardware import keys
from sim.vjoy import CONSOLE_HANDLER, CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT

# winuser.h: an INPUT of type INPUT_KEYBOARD holds a KEYBDINPUT in a union as large as its largest member,
# MOUSEINPUT. ULONG_PTR is as wide as a pointer (size_t): 40 bytes in all for 64-bit Windows.
INPUT_KEYBOARD, KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 1, 0x0001, 0x0002, 0x0008


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_uint16), ("wScan", ctypes.c_uint16), ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_int32), ("dy", ctypes.c_int32), ("mouseData", ctypes.c_uint32),
                ("dwFlags", ctypes.c_uint32), ("time", ctypes.c_uint32), ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    class Union(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_uint32), ("u", Union)]


# The keys keys.py sends, by their HID usage, as scan codes (set 1; 0xE0xx: an extended key), from Microsoft's
# table of HID usages and scan codes (learn.microsoft.com/windows/win32/inputdev/about-keyboard-input, Scan codes):
# F1 to F12, then Insert, Home, Page Up, Delete, End, Page Down and the arrows right, left, down, up
SCAN = {**{0x3A + i: 0x3B + i for i in range(10)}, 0x44: 0x57, 0x45: 0x58,
        **dict(zip(range(0x49, 0x53), (0xE052, 0xE047, 0xE049, 0xE053, 0xE04F, 0xE051, 0xE04D, 0xE04B, 0xE050,
                                       0xE048), strict=True))}
# the modifier bits of the report: left Ctrl, Shift, Alt, right Ctrl, Shift
MODIFIERS = ((0x01, 0x1D), (0x02, 0x2A), (0x04, 0x38), (0x10, 0xE01D), (0x20, 0x36))


def keystroke(scan, up):
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0) | (KEYEVENTF_EXTENDEDKEY if scan > 0xFF else 0)
    return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wScan=scan & 0xFF, dwFlags=flags))


class SendInput:
    """The keyboard of a Board in keyboard mode as keystrokes: send(device, report) is Live's output. close() lets
    go of every key, also on Ctrl-Break and when the console window closes (Python runs no finally then; a kill
    from Task Manager can leave a modifier down until it is pressed and let go on the PC's keyboard). user32,
    kernel32: Windows' (on win32 by default)."""

    name = "keystrokes to the window in front"

    def __init__(self, board, user32=None, kernel32=None):
        if not board.keyboard:
            raise OSError("SendInput takes the keyboard mode's keys: add --keyboard (joysticks: --vjoy)")
        if user32 is None:
            if sys.platform != "win32":
                raise OSError("SendInput runs on Windows only (on Linux: --uhid)")
            user32, kernel32 = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
        user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int)
        user32.SendInput.restype = ctypes.c_uint
        self.user32, self.lock, self.closed = user32, threading.Lock(), False
        self.last = self.failed = bytes(keys.REPORT)   # the last report Windows took in full, one it did not
        self.handler = None
        if kernel32 is not None:                   # kept: Windows calls it after Python would have freed it
            self.handler = CONSOLE_HANDLER(self.console)
            kernel32.SetConsoleCtrlHandler(self.handler, True)

    def console(self, event):
        """Windows' console handler: lets go on Ctrl-Break and when the window closes; Ctrl-C goes on to Python"""
        if event in (CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT):
            self.close()
        return int(event == CTRL_CLOSE_EVENT)

    def send(self, device, report):
        """A report's changes as one SendInput: keys up, modifiers up, modifiers down, keys down; nothing once
        closed"""
        with self.lock:
            if not self.closed:
                self.press(bytes(report))

    def press(self, new):
        """What tells new from the last report Windows took in full. Windows can take a part or nothing (nothing
        while a UAC prompt, Ctrl+Alt+Del or the lock screen is up): then new counts as failed, for close()."""
        old = self.last
        events = [(SCAN[k], True) for k in old[2:] if k and k not in new[2:]]
        events += [(scan, True) for bit, scan in MODIFIERS if old[0] & bit and not new[0] & bit]
        events += [(scan, False) for bit, scan in MODIFIERS if new[0] & bit and not old[0] & bit]
        events += [(SCAN[k], False) for k in new[2:] if k and k not in old[2:]]
        taken = self.keystrokes(events)
        if taken != len(events):
            self.failed = new
            raise OSError(f"Windows took {taken} of {len(events)} keystrokes: a prompt or another program blocks "
                          "them")
        self.last = new

    def keystrokes(self, events):
        """The keystrokes [(scan code, up)] as one SendInput: how many of them Windows took"""
        if not events:
            return 0
        inputs = (INPUT * len(events))(*(keystroke(scan, up) for scan, up in events))
        return self.user32.SendInput(len(events), inputs, ctypes.sizeof(INPUT))

    def close(self):
        """Lets go of the keys of the last report and of a failed one, then of all five modifiers, whatever Windows
        took before; sends nothing after that"""
        with self.lock:
            if not self.closed:
                self.closed = True
                down = sorted({k for report in (self.last, self.failed) for k in report[2:] if k})
                self.keystrokes([(SCAN[k], True) for k in down] + [(scan, True) for _, scan in MODIFIERS])
