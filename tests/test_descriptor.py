"""The report descriptor boot.py builds, through the parser of hid-tools (what hid-recorder uses), without a kernel:
two joysticks on report IDs 4 and 5, and the reports code.py sends read with it name the buttons buttonmap.py
gives. build.sh provides hid-tools; tests/test_uhid.py does the same through the kernel where it can."""
import pytest

from sim import BM, Sim
from sim.hardware import Board

hid = pytest.importorskip("hidtools.hid", reason="hid-tools missing (build.sh provides it)")
REPORT_ID = {1: 4, 2: 5}
BUTTON_PAGE = 0x09 << 16


def descriptor():
    return hid.ReportDescriptor.from_bytes(list(b"".join(d.report_descriptor for d in Board().boot().devices)))


def test_two_joysticks_with_128_and_64_buttons():
    rdesc = descriptor()
    assert sorted(rdesc.input_reports) == [4, 5] and not rdesc.feature_reports and not rdesc.output_reports
    for device, report_id in REPORT_ID.items():
        report = rdesc.input_reports[report_id]
        assert report.application_name == "Joystick" and report.numbered
        assert report.size == 1 + BM.SIZE[device] // 8
        assert [f.usage for f in report] == [BUTTON_PAGE | n for n in range(1, BM.SIZE[device] + 1)]
        assert all((f.size, f.count, f.logical_min, f.logical_max) == (1, 1, 0, 1) for f in report)


def test_reports_read_with_the_descriptor_name_the_buttons_of_buttonmap():
    # every pressed bit of every report, read as its descriptor says, is the button buttonmap.py names
    sim = Sim()
    for key in ("AP", "SHIFT", "FD", "SHIFT", "FMS_PUSH", "SHIFT", "HOME", "COM_SWAP"):   # CABIN_LT: the last
        sim.tap(key)                                                                      # button of device 1
    sim.turn("ALTHDG_OUTER", 1)
    sim.turn("FREQ_INNER", -1)                 # unit 2's
    rdesc, seen = descriptor(), {1: set(), 2: set()}
    for device, report_id in REPORT_ID.items():
        reports = sim.reports(device)
        for (_, data), (_, names) in zip(reports, sim.buttons(device), strict=True):
            report = rdesc.get(data[0], len(data))
            assert report is rdesc.input_reports[report_id]
            read = [BM.DEVICE[device][(f.usage & 0xFFFF) - 1] for f in report if f.get_values(list(data)) == [1]]
            assert read == names
            seen[device].update(read)
    assert seen == {1: {"AP", "YD", "CABIN_LT", "ALT_100_UP"}, 2: {"COM_SWAP", "COM_KHZ_DN"}}
