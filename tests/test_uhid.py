"""The simulated panel as a Linux HID device (sim/uhid.py), through the kernel. These run only where /dev/uhid is
writable and the hidraw node the device gets is readable (root, or udev rules), and skip elsewhere
(tests/test_descriptor.py checks the descriptor and the reports there without a kernel), but for the first, which
stands in for the kernel. REQUIRE_UHID=1 turns the skips into failures: the build workflow loads the kernel
module, opens both up and sets it. The keyboard mode's test types one shortcut (Ctrl, Shift and Alt with an
F-key) into the desktop too."""
import contextlib
import fcntl
import glob
import os
import select
import struct
import time
import uuid

import pytest

import sim.uhid
from sim import BM, typed
from sim.hardware import keys
from sim.live import Live
from sim.uhid import UHID_GET_REPORT, UHID_GET_REPORT_REPLY, UHID_INPUT_REPORT, UHID_START, Uhid

TIMEOUT_S = 5


def need(ok, why):
    if not ok:
        if os.environ.get("REQUIRE_UHID"):
            pytest.fail(why)
        pytest.skip(why)


def until(check):
    end = time.monotonic() + TIMEOUT_S
    while not check() and time.monotonic() < end:
        time.sleep(0.01)
    return check()


@pytest.fixture
def panel():
    with plugged() as panel:
        yield panel


@contextlib.contextmanager
def plugged(keyboard=False):
    """(the live panel, plugged in but not started, its uhid device, its sysfs directory, its hidraw nodes, one of
    them open)"""
    need(os.access("/dev/uhid", os.W_OK), "/dev/uhid not writable (root, or a udev rule)")
    live = Live(speed=10, keyboard=keyboard)
    phys = f"avionics-panel-test/{uuid.uuid4().hex}"
    uhid = Uhid(live, phys=phys)
    try:
        hid = next(d for d in glob.glob("/sys/bus/hid/devices/*") if f"HID_PHYS={phys}" in uevent(d))
        assert until(lambda: glob.glob(f"{hid}/hidraw/hidraw*"))
        nodes = sorted(os.path.basename(n) for n in glob.glob(f"{hid}/hidraw/hidraw*"))
        node = f"/dev/{nodes[0]}"
        need(until(lambda: os.access(node, os.R_OK)), f"{node} not readable (root, or a udev rule)")
        fd = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
        try:
            yield live, uhid, hid, nodes, fd
        finally:
            os.close(fd)
    finally:
        live.stop()
        uhid.close()


def read(directory, name, mode="r"):
    with open(os.path.join(directory, name), mode) as f:
        return f.read()


def uevent(directory):
    return read(directory, "uevent").splitlines()


class Kernel:
    """os and select for sim.uhid without /dev/uhid: the kernel's events in events, what sim.uhid writes in
    written"""
    O_RDWR = O_CLOEXEC = 0

    def __init__(self):
        self.events, self.written = [], []

    def open(self, path, flags):
        return -1

    def close(self, fd):
        pass

    def write(self, fd, event):
        self.written.append(event)

    def read(self, fd, size):
        return self.events.pop(0)

    def select(self, read, write, error, timeout):
        if not self.events:
            time.sleep(min(timeout, 0.01))
        return [fd for fd in read if self.events], [], []


def test_get_report_answers_with_the_last_report_of_its_id(monkeypatch):
    # the joysticks' reports start with their report ID; the keyboard's have none, their first byte is the
    # modifiers, and GET_REPORT asks for report 0
    kernel = Kernel()
    monkeypatch.setattr(sim.uhid, "os", kernel)
    monkeypatch.setattr(sim.uhid, "select", kernel)
    for keyboard, reports in ((False, (ap(), bytes([5]) + bytes(8))), (True, (bytes((keys.RC, 0, 0x3A)) + bytes(5),))):
        kernel.events.append(struct.pack("<I", UHID_START))
        uhid = Uhid(Live(keyboard=keyboard))
        try:
            for report in reports:
                uhid.send(1, report)
            assert sorted(uhid.last) == ([0] if keyboard else [4, 5])
            kernel.events.append(struct.pack("<IIBB", UHID_GET_REPORT, 7, 0 if keyboard else 4, UHID_INPUT_REPORT))
            assert until(lambda: kernel.written[-1][:4] == struct.pack("<I", UHID_GET_REPORT_REPLY))
            reply = kernel.written[-1][4:]
            assert reply[:8 + len(reports[0])] == struct.pack("<IHH", 7, 0, len(reports[0])) + reports[0]
        finally:
            uhid.close()


def test_the_kernel_takes_the_descriptor_name_and_ids(panel):
    live, uhid, hid, nodes, _ = panel
    assert read(hid, "report_descriptor", "rb") == b"".join(d.report_descriptor for d in live.devices)
    assert {"HID_ID=0003:0000239A:000080F4", "HID_NAME=DIY Avionics Panel"} <= set(uevent(hid))
    assert len(nodes) == 1                     # both joysticks, report IDs 4 and 5, on one node


def ap():
    """Device 1's report with AP pressed"""
    report = bytearray([4]) + bytes(16)
    report[1 + BM.BUTTON[1]["AP"] // 8] |= 1 << BM.BUTTON[1]["AP"] % 8
    return bytes(report)


def hidioc(nr, size):
    """HIDIOCGFEATURE (7) and HIDIOCGINPUT (10) of <linux/hidraw.h> for a buffer of size bytes"""
    return 3 << 30 | size << 16 | ord("H") << 8 | nr


def test_a_tap_arrives_as_its_button_bit(panel):
    live, uhid, _, _, fd = panel
    live.act("tap", "AP")
    live.start(uhid.send)
    assert live.idle(TIMEOUT_S)
    reports, end = [], time.monotonic() + TIMEOUT_S
    while len(reports) < 4 and select.select([fd], [], [], max(end - time.monotonic(), 0))[0]:
        reports.append(os.read(fd, 64))
    assert reports == [bytes([4]) + bytes(16), bytes([5]) + bytes(8), ap(), bytes([4]) + bytes(16)]


def test_get_report_is_answered_at_once(panel):
    # an input report: the last one sent; a feature report (there are none): EIO, not the kernel's 5 s timeout
    live, uhid, _, _, fd = panel
    live.act("press", "AP")
    live.start(uhid.send)
    assert live.idle(TIMEOUT_S)
    start, report = time.monotonic(), bytearray([4]) + bytes(16)
    fcntl.ioctl(fd, hidioc(10, len(report)), report)
    assert report == ap()
    with pytest.raises(OSError):
        fcntl.ioctl(fd, hidioc(7, len(report)), bytearray([4]) + bytes(16))
    assert time.monotonic() - start < 1


def test_the_keyboard_mode_is_one_keyboard_that_types_a_shortcut():
    # its own descriptor on one node, reports without a report ID, and a key's shortcut with its modifiers
    # around it (the key with the most modifiers, which desktops are the likeliest to leave alone)
    name = max(BM.PLAIN_KEYS + BM.UNIT_KEYS, key=lambda n: bin(keys.shortcut(1, BM.BUTTON[1][n])[0]).count("1"))
    with plugged(keyboard=True) as (live, uhid, hid, nodes, fd):
        assert read(hid, "report_descriptor", "rb") == keys.DESCRIPTOR and len(nodes) == 1
        live.act("wait", 1000)                 # the start pattern
        live.act("tap", name)
        live.start(uhid.send)
        assert live.idle(TIMEOUT_S)
        reports, end = [], time.monotonic() + TIMEOUT_S
        while len(reports) < 5 and select.select([fd], [], [], max(end - time.monotonic(), 0))[0]:
            reports.append(os.read(fd, 64))
    assert [(d, n) for _, d, n in typed(enumerate(reports))] == [(1, name)] and reports[-1] == bytes(keys.REPORT)
