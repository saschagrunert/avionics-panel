"""The simulated panel as a Linux HID device (sim/uhid.py), through the kernel. These run only where /dev/uhid is
writable and the hidraw node the device gets is readable (root, or udev rules), and skip elsewhere, CI included
(tests/test_descriptor.py checks the descriptor and the reports there without a kernel). REQUIRE_UHID=1 turns the
skips into failures."""
import fcntl
import glob
import os
import select
import time
import uuid

import pytest

from sim import BM
from sim.live import Live
from sim.uhid import Uhid

TIMEOUT_S = 2


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
    """(the live panel, plugged in but not started, its uhid device, its sysfs directory, its hidraw nodes, one of
    them open)"""
    need(os.access("/dev/uhid", os.W_OK), "/dev/uhid not writable (root, or a udev rule)")
    live = Live(speed=10)
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
