"""The report descriptor boot.py builds, through the parser of hid-tools (what hid-recorder uses), without a kernel:
two joysticks on report IDs 4 and 5, and the reports code.py sends read with it name the buttons buttonmap.py
gives; in keyboard mode one keyboard, whose reports read with it are the shortcuts of keys.py. The firmware shell
(nix/shells.nix) has hid-tools on Linux and sets REQUIRE_HID_TOOLS=1 there, which makes a missing parser fail these
tests; elsewhere they skip. tests/test_uhid.py does the same through the kernel where it can."""
from conftest import hid_parser
from sim import BM, FUNCTIONS, Sim
from sim.hardware import Board, keys

hid = hid_parser()
REPORT_ID = {1: 4, 2: 5}
BUTTON_PAGE = 0x09 << 16
KEY_PAGE = 0x07 << 16


def descriptor(keyboard=False):
    devices = Board(keyboard=keyboard).boot().devices
    return hid.ReportDescriptor.from_bytes(list(b"".join(d.report_descriptor for d in devices)))


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


def test_keyboard_mode_is_one_boot_keyboard():
    # no report ID; the boot keyboard's 8 bytes: Ctrl, Shift, Alt and the GUI keys of both sides as bits, a
    # constant byte, six keys from 0 to 101; and the LEDs' output report, which the panel ignores
    rdesc = descriptor(keyboard=True)
    [report] = rdesc.input_reports.values()
    [leds] = rdesc.output_reports.values()
    assert not report.numbered and report.application_name == "Keyboard" and report.size == keys.REPORT
    *mods, reserved, array = report
    assert [f.usage for f in mods] == [KEY_PAGE | u for u in range(0xE0, 0xE8)] and reserved.is_const
    assert (array.size, array.count, array.logical_min, array.logical_max) == (8, 6, 0, 101)
    assert array.usages == [KEY_PAGE | u for u in range(102)]
    assert leds.size == 1 and not rdesc.feature_reports


def test_keyboard_reports_read_with_the_descriptor_are_the_shortcuts():
    # every key down in the reports of a scenario, read as the descriptor says, is a function's shortcut
    sim = Sim(keyboard=True)
    for key in ("AP", "SHIFT", "FD", "SHIFT", "HOME", "COM_SWAP"):
        sim.tap(key)
    sim.turn("FREQ_INNER", -1)
    [report] = descriptor(keyboard=True).input_reports.values()
    *mods, _, array = report
    seen = []
    for _, data in sim.reports(1):
        bits = sum(f.get_values(list(data))[0] << i for i, f in enumerate(mods))
        [key, *rest] = array.get_values(list(data))
        assert bits == data[0] and not any(rest)
        if key:
            seen.append(FUNCTIONS[bits, key])
    assert seen == [(1, "AP"), (1, "YD"), (2, "COM_SWAP"), (2, "COM_KHZ_DN")]
