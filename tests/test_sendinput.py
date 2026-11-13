"""The Windows keystroke output of the keyboard mode (sim/sendinput.py) without Windows: its structs against
winuser.h's layout on 64-bit Windows, the keystrokes it makes of the keyboard's reports, and its calls into a
stand-in for user32.dll. Windows itself, and the sim taking the keys, are tested on a Windows PC."""
import ctypes
import sys
import threading
import time

import pytest

import sim.sendinput
from sim import BM, FUNCTIONS, Sim
from sim.hardware import Board, keys
from sim.live import Live
from sim.sendinput import INPUT, KEYBDINPUT, SCAN, SendInput

pytestmark = pytest.mark.skipif(ctypes.sizeof(ctypes.c_void_p) != 8, reason="the layout of 64-bit Windows")
# winuser.h's values, which the stand-in below reads the keystrokes by: not sim.sendinput's own
INPUT_KEYBOARD, KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 1, 0x0001, 0x0002, 0x0008


class User32:
    """user32.dll's SendInput as sim.sendinput calls it: calls has the keystrokes of each call, as (scan code,
    up), took what each returned (take, or all of them), and overlapped says whether two calls ran at once (each
    takes delay s)"""

    def __init__(self, take=None):
        self.calls, self.took, self.take, self.delay, self.inside, self.overlapped = [], [], take, 0, 0, False
        user32 = self

        def send(n, inputs, size):
            assert size == ctypes.sizeof(INPUT) and all(inputs[i].type == INPUT_KEYBOARD for i in range(n))
            assert all(inputs[i].ki.dwFlags & KEYEVENTF_SCANCODE and not inputs[i].ki.wVk for i in range(n))
            ki = [inputs[i].ki for i in range(n)]
            user32.overlapped |= user32.inside > 0
            user32.inside += 1
            time.sleep(user32.delay)
            user32.inside -= 1
            user32.calls.append([(k.wScan | (0xE000 if k.dwFlags & KEYEVENTF_EXTENDEDKEY else 0),
                                  bool(k.dwFlags & KEYEVENTF_KEYUP)) for k in ki])
            user32.took.append(n if user32.take is None else user32.take)
            return user32.took[-1]
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


BLOCKED = ("sim.sendinput: Windows took {} of {} keystrokes (a prompt or another program blocks them): they go on "
           "once it takes them again\n")


def test_keystrokes_windows_does_not_take_are_let_go_until_it_takes_them_again(capsys):
    # Windows takes none while a UAC prompt or the lock screen is up. One line says so; every key of the report
    # before and of the one not taken and every modifier is let go, again before each report as long as Windows
    # takes nothing; the first report it takes goes out in full
    user32 = User32()
    out = output(user32)
    out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))
    user32.take = 0
    out.send(1, bytes((keys.RC, 0, UP)) + bytes(5))                  # not taken, nor the key-ups after it
    out.send(1, bytes((keys.RC, 0, 0)) + bytes(5))                   # only the key-ups again
    user32.take = None
    out.send(1, bytes((keys.RC, 0, UP)) + bytes(5))                  # the key-ups, taken, then all of the report
    out.send(1, bytes(keys.REPORT))
    let_go = [(0x3B, True), (0xE048, True), *ALL_UP]
    assert user32.calls[1:] == [[(0x3B, True), (RSHIFT, True), (RCTRL, False), (0xE048, False)], let_go, let_go,
                                let_go, [(RCTRL, False), (0xE048, False)], [(0xE048, True), (RCTRL, True)]]
    assert capsys.readouterr().err == BLOCKED.format(0, 4)


RETRY_S = 0.02       # sim.sendinput's in the tests of its retries
LET_GO = [(0x3B, True), (0xE048, True)]     # the key-ups of blocked()'s keys; ALL_UP follows them


def until(check):
    end = time.monotonic() + 5
    while not check() and time.monotonic() < end:
        time.sleep(0.005)
    return check()


@pytest.fixture
def retries(monkeypatch):
    """The threads sim.sendinput starts for its retries, here every RETRY_S; they have ended after the test"""
    started = []

    class Thread(threading.Thread):
        def start(self):
            started.append(self)
            super().start()
    monkeypatch.setattr(sim.sendinput, "RETRY_S", RETRY_S)
    monkeypatch.setattr(sim.sendinput.threading, "Thread", Thread)
    yield started
    assert until(lambda: not any(thread.is_alive() for thread in started))


def blocked():
    """(user32, an output) after a report Windows took and one it did not: the output retries"""
    user32 = User32()
    out = output(user32)
    out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))
    user32.take = 0
    out.send(1, bytes((keys.RC, 0, UP)) + bytes(5))
    return user32, out


def test_keys_windows_holds_through_a_block_are_let_go_when_it_ends(retries):
    # the prompt can go while the panel sends nothing: the key-ups are tried again every RETRY_S, until taken
    user32, out = blocked()
    start = time.monotonic()
    assert until(lambda: len(user32.calls) > 5)                      # three more times, not taken
    assert time.monotonic() - start > 2.5 * RETRY_S                  # ... and no sooner
    user32.take = None
    assert until(lambda: user32.took[-1])
    calls = len(user32.calls)
    time.sleep(10 * RETRY_S)                                         # no more follow
    assert len(user32.calls) == calls and user32.calls[-1] == [*LET_GO, *ALL_UP]
    out.send(1, bytes((keys.RC, 0, UP)) + bytes(5))                  # the next report, in full, at once
    assert user32.calls[calls:] == [[(RCTRL, False), (0xE048, False)]]


def test_close_ends_the_retries(retries):
    user32, out = blocked()
    assert until(lambda: len(user32.calls) > 5)
    out.close()
    calls = len(user32.calls)
    time.sleep(10 * RETRY_S)
    assert len(user32.calls) == calls and user32.calls[-1] == [*LET_GO, *ALL_UP]     # close's own, the last


def test_a_report_windows_takes_ends_the_retries_until_it_blocks_again(retries):
    # while the thread sleeps: the report lets go itself, and the thread finds nothing left to do. The next
    # block gets a thread again.
    user32, out = blocked()
    user32.take = None
    out.send(1, bytes((keys.RC, 0, UP)) + bytes(5))
    calls = len(user32.calls)
    time.sleep(10 * RETRY_S)
    assert len(user32.calls) == calls and user32.calls[-2:] == [[*LET_GO, *ALL_UP], [(RCTRL, False), (0xE048, False)]]
    assert not retries[0].is_alive()
    user32.take = 0
    out.send(1, bytes(keys.REPORT))
    assert until(lambda: len(user32.calls) > calls + 5) and len(retries) == 2
    out.close()


def test_one_thread_retries_however_often_windows_blocks(retries, capsys):
    # blocked, taken and blocked again before the thread wakes, six times: still one thread, whose calls never
    # run beside a report's
    user32 = User32()
    out = output(user32)
    for _ in range(6):
        user32.take = None
        out.send(1, bytes(keys.REPORT))
        user32.take = 0
        out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))
    assert until(lambda: sum(thread.is_alive() for thread in retries) == 1)
    user32.delay = 2 * RETRY_S                                       # a call takes its time
    for _ in range(5):
        out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))
    assert not user32.overlapped
    out.close()
    assert capsys.readouterr().err == 6 * BLOCKED.format(0, 2)


def test_close_lets_go_of_the_keys_windows_did_not_take_too(capsys):
    # of a report it took none of, and of one it took a part of
    user32 = User32()
    out = output(user32)
    out.send(1, bytes((keys.RS, 0, F1)) + bytes(5))
    user32.take = 0
    out.send(1, bytes((keys.RC, 0, UP)) + bytes(5))
    out.close()
    assert user32.calls[-1] == [(0x3B, True), (0xE048, True), *ALL_UP]
    user32 = User32(take=1)
    out = output(user32)
    out.send(1, bytes((keys.RS | keys.RC, 0, 0)) + bytes(5))
    out.close()
    assert user32.calls == [[(RCTRL, False), (RSHIFT, False)], ALL_UP, ALL_UP]
    assert capsys.readouterr().err == BLOCKED.format(0, 4) + BLOCKED.format(1, 2)


def test_a_blocked_keystroke_does_not_end_the_panel(capsys):
    # the panel runs on through a prompt, and its next key reaches Windows
    user32 = User32(take=0)
    live = Live(speed=25, keyboard=True)
    out = SendInput(live, user32)
    live.act("wait", 1000)                                           # the start pattern
    live.act("tap", "AP")
    live.do(lambda board: setattr(user32, "take", None))
    live.act("tap", "FD")
    live.start(out.send)
    assert live.idle(5)
    live.stop()                                                      # raises what ended the run
    out.close()
    down = [scan for call in user32.calls for scan, up in call if not up and scan in SCAN.values()]
    assert down == [SCAN[keys.shortcut(1, BM.BUTTON[1]["FD"])[1]]]   # (AP's went nowhere)
    assert capsys.readouterr().err.count("Windows took 0 of") == 1


def test_closing_the_window_lets_go():
    # through the console handler of sim.vjoy, which tests/test_vjoy.py checks event by event
    user32, kernel32 = User32(), Kernel32()
    out = output(user32, kernel32)
    [(handler, add)] = kernel32.handlers
    assert add and handler is out.handler
    out.send(1, bytes((0, 0, UP)) + bytes(5))
    assert handler(2) == 1 and user32.calls[-1] == [(0xE048, True), *ALL_UP]


def test_the_joystick_mode_and_other_systems_are_refused(monkeypatch):
    with pytest.raises(OSError, match="SendInput takes the keyboard mode's keys: add --keyboard"):
        SendInput(Board().boot(), User32())
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(OSError, match="SendInput runs on Windows only"):
        SendInput(Board(keyboard=True).boot())
