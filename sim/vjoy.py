r"""The live panel (sim/live.py) as two vJoy devices on Windows, for MobiFlight: every report code.py sends becomes
one UpdateVJD of its vJoy device (report ID 4: device 1, report ID 5: device 2), so MobiFlight never reads half a
report. Windows sees two of vJoy's generic joysticks ("vJoy Device", with vJoy's descriptor and IDs), not the
panel's name and IDs.

    python -m sim.vjoy

reads actions from stdin like `python3 -m sim.uhid`, one per line, such as `tap AP` or `turn FREQ_INNER 3`, and
`lights`. `python -m sim.page --vjoy` feeds vJoy from the panel page.

It needs vJoy 2.2.2.0 (BrunnerInnovation's signed build for Windows 10 and 11) with vJoyInterface.dll in its
default folder, C:\Program Files\vJoy\x64 (the environment variable VJOY_DLL names another), and vJoy devices 1
and 2 with at least 128 and 64 buttons. windows/vjoy-setup.bat makes them, as administrator:

    vJoyConfig 1 -f -a -b 128
    vJoyConfig 2 -f -a -b 64

docs/using/simulator.md has the steps.
"""
import argparse
import ctypes
import os
import struct
import sys
import threading

from sim.live import Live, from_stdin

# vJoy 2.2.2.0's SDK: https://github.com/BrunnerInnovation/vJoy/blob/v2.2.2.0/SDK/inc/public.h L316-361, the
# JOYSTICK_POSITION_V3 that UpdateVJD takes (USE_JOYSTICK_API_VERSION 3, L80), with Windows' BYTE, LONG and
# DWORD of 1, 4 and 4 bytes, also on Linux for the tests; its natural alignment, as vjoyinterface.h says ("a
# 4-bytes aligned struct", L340). Its 4 button words carry buttons 1-32, 33-64, 65-96 and 97-128, bit 0 first.
AXES = ("wThrottle", "wRudder", "wAileron", "wAxisX", "wAxisY", "wAxisZ", "wAxisXRot", "wAxisYRot", "wAxisZRot",
        "wSlider", "wDial", "wWheel", "wAccelerator", "wBrake", "wClutch", "wSteering", "wAxisVX", "wAxisVY")
HATS = ("bHats", "bHatsEx1", "bHatsEx2", "bHatsEx3")
WORDS = ("lButtons", "lButtonsEx1", "lButtonsEx2", "lButtonsEx3")
AXES_V3 = ("wAxisVZ", "wAxisVBRX", "wAxisVBRY", "wAxisVBRZ")
SIZE = 124                 # sizeof(JOYSTICK_POSITION_V3)
CENTRED = 0xFFFFFFFF       # a hat in its middle (-1); the devices have none


class Position(ctypes.Structure):
    _fields_ = [("bDevice", ctypes.c_uint8), *((a, ctypes.c_int32) for a in AXES), (WORDS[0], ctypes.c_int32),
                *((h, ctypes.c_uint32) for h in HATS), *((w, ctypes.c_int32) for w in WORDS[1:]),
                *((a, ctypes.c_int32) for a in AXES_V3)]


assert ctypes.sizeof(Position) == SIZE

# vjoyinterface.h (the same tag) L25-32: enum VjdStat
VJD_STAT_OWN, VJD_STAT_FREE, VJD_STAT_BUSY, VJD_STAT_MISS, VJD_STAT_UNKN = range(5)
# the functions used here, all __cdecl (L311-341): name, return type, argument types (BOOL and the enum are int)
SIGNATURES = (
    ("vJoyEnabled", ctypes.c_int),
    ("GetVJDStatus", ctypes.c_int, ctypes.c_uint),
    ("GetVJDButtonNumber", ctypes.c_int, ctypes.c_uint),
    ("GetOwnerPid", ctypes.c_int, ctypes.c_uint),
    ("AcquireVJD", ctypes.c_int, ctypes.c_uint),
    ("RelinquishVJD", None, ctypes.c_uint),
    ("UpdateVJD", ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Position)),
)
SETUP = "run vjoy-setup.bat as administrator"
# wincon.h: Ctrl-Break and closing the window end the process without a finally (Python handles only Ctrl-C;
# logoff and shutdown reach services only), and the handler's type, BOOL WINAPI HandlerRoutine(DWORD); WINAPI is
# the one x64 convention, so CFUNCTYPE stands in for WINFUNCTYPE where ctypes lacks it (the tests on Linux)
CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT = 1, 2
CONSOLE_HANDLER = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(ctypes.c_int, ctypes.c_uint)


class VJoyError(OSError):
    pass


def load(path=None):
    """vJoyInterface.dll (path, else VJOY_DLL, else vJoy's default folder) with the signatures of SIGNATURES"""
    if path is None and sys.platform != "win32":
        raise VJoyError("vJoy runs on Windows only (on Linux: --uhid)")
    path = path or os.environ.get("VJOY_DLL") or os.path.join(
        os.environ.get("PROGRAMFILES", r"C:\Program Files"), "vJoy", "x64", "vJoyInterface.dll")
    if not os.path.isfile(path):
        raise VJoyError(f"vJoy is not installed: there is no {path}. Install vJoy 2.2.2.0, or set VJOY_DLL to "
                        "its vJoyInterface.dll")
    try:
        dll = ctypes.CDLL(path)
    except OSError as e:
        raise VJoyError(f"{path} does not load: {e}") from e
    for name, restype, *argtypes in SIGNATURES:
        function = getattr(dll, name)
        function.restype, function.argtypes = restype, argtypes
    return dll


def position(device, report):
    """The Position of vJoy device `device` for a report (its ID first): bit b of the report's buttons, which the
    descriptor makes button b + 1, is vJoy's button b + 1. No axes; the hats in their middle."""
    words = struct.unpack("<4i", bytes(report[1:]).ljust(4 * len(WORDS), b"\0"))
    return Position(device, **dict(zip(WORDS, words, strict=True)), **dict.fromkeys(HATS, CENTRED))


class VJoy:
    """vJoy devices 1 and 2 for a Board's two joysticks, acquired: send(device, report) is Live's output, and
    close() lets go of every button and of the devices, also on Ctrl-Break and when the console window closes
    (Python runs no finally then; a kill from Task Manager still leaves the last buttons down until the next
    start). dll: vJoyInterface.dll's functions (load()); kernel32: Windows' kernel32 (on win32 by
    default) for the console handler."""

    name = "vJoy devices 1 and 2"

    def __init__(self, board, dll=None, kernel32=None):
        self.dll, self.acquired, self.lock = load() if dll is None else dll, [], threading.Lock()
        # report ID -> (vJoy device, buttons): device n for the board's joystick n
        self.devices = {d.report_ids[0]: (n, 8 * d.in_report_lengths[0]) for n, d in enumerate(board.devices, 1)}
        if not self.dll.vJoyEnabled():
            raise VJoyError("the vJoy driver is not enabled: enable it in Configure vJoy")
        for n, buttons in self.devices.values():
            status = self.dll.GetVJDStatus(n)
            if status == VJD_STAT_MISS:
                raise VJoyError(f"vJoy device {n} is not configured: {SETUP}")
            if status == VJD_STAT_BUSY:
                raise VJoyError(f"vJoy device {n} is in use by another program (process {self.dll.GetOwnerPid(n)}): "
                                "close it; in MobiFlight, remove the profile's vJoy outputs")
            if status not in (VJD_STAT_OWN, VJD_STAT_FREE):
                raise VJoyError(f"vJoy device {n} is in an unknown state ({status})")
            if (have := self.dll.GetVJDButtonNumber(n)) < buttons:
                raise VJoyError(f"vJoy device {n} has {have} buttons, not {buttons}: {SETUP}")
        try:
            for n, _ in self.devices.values():
                if not self.dll.AcquireVJD(n):
                    raise VJoyError(f"vJoy device {n} cannot be acquired: another program may have taken it")
                self.acquired.append(n)
        except BaseException:
            self.close()
            raise
        if kernel32 is None and sys.platform == "win32":
            kernel32 = ctypes.WinDLL("kernel32")
        self.handler = None
        if kernel32 is not None:          # kept: Windows calls it after Python would have freed it
            self.handler = CONSOLE_HANDLER(self.console)
            kernel32.SetConsoleCtrlHandler(self.handler, True)

    def console(self, event):
        """Windows' console handler, in a thread of its own: lets go on Ctrl-Break and when the window closes
        (Windows waits up to about 5 s for it); Ctrl-C goes on to Python"""
        if event in (CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT):
            self.close()
        return int(event == CTRL_CLOSE_EVENT)   # Ctrl-Break: Windows' default handler then ends the process

    def send(self, device, report):
        """A report as one UpdateVJD; nothing once closed"""
        with self.lock:
            n, _ = self.devices[report[0]]
            if n in self.acquired and not self.dll.UpdateVJD(n, position(n, report)):
                raise VJoyError(f"vJoy device {n} took no report: another program may have taken it")

    def close(self):
        with self.lock:
            while self.acquired:
                n = self.acquired.pop()
                self.dll.UpdateVJD(n, position(n, b"\0"))
                self.dll.RelinquishVJD(n)


def main(argv=None):
    argparse.ArgumentParser(prog="python -m sim.vjoy", description=__doc__.split("\n\n")[0]).parse_args(argv)
    live = Live()
    try:
        vjoy = VJoy(live)
    except OSError as e:
        sys.exit(f"sim.vjoy: {e}")
    print(f"The panel on {vjoy.name}; actions, one per line:", file=sys.stderr)
    from_stdin(live, vjoy, "sim.vjoy")


if __name__ == "__main__":
    main()
