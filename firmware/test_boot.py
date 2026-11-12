"""Host tests for boot.py: runs it on the stand-in hardware of sim/hardware.py. SHIFT held is its switch closed
between its row and column pin: the column then reads low while the row pin drives low.
"""
import buttonmap as BM

from sim.hardware import SETTLE_S, Board

SHIFT_PINS = ("GP2", "GP6")        # row, column of SHIFT; tests/test_pins.py checks them against the board


def boot(shift=False, pins=SHIFT_PINS):
    """boot.py on a board with SHIFT held (its switch between pins closed) or not"""
    board = Board()
    if shift:
        board.closed.add(pins)
    return board.boot()


def hidden(board):
    return {"disable_usb_drive", "usb_cdc.disable"} & {c[0] for c in board.calls}


def test_without_shift_the_drive_and_console_are_hidden():
    board = boot(shift=False)
    assert hidden(board) == {"disable_usb_drive", "usb_cdc.disable"}
    assert len(board.devices) == 2


def test_shift_held_keeps_the_drive_and_console():
    board = boot(shift=True)
    assert not hidden(board) and len(board.devices) == 2


def test_usb_name_and_interfaces():
    # in both modes the joysticks carry the name "Avionics Panel" (what joy.cpl and MobiFlight show) and MIDI
    # is off: only the drive and the console differ between the modes (they shift the joysticks' interface
    # number, so Windows may see new controllers in SHIFT mode; docs/using/mapping.md)
    for shift in (False, True):
        board = boot(shift=shift)
        assert board.calls.count(("set_usb_identification", "DIY", "Avionics Panel")) == 1
        assert board.calls.count(("usb_midi.disable",)) == 1


def test_hid_interface_carries_the_name():
    # on a composite device (SHIFT mode) Windows names the joysticks after the HID interface, not the product:
    # without this they would show as "CircuitPython HID". CircuitPython reads it when USB starts, after boot.py
    for shift in (False, True):
        board = boot(shift=shift)
        assert [c for c in board.calls if c[0] == "usb_hid.set_interface_name"] == [
            ("usb_hid.set_interface_name", "Avionics Panel")]


def test_shift_is_read_after_the_column_settles():
    # without the settle the column would still read low and every plain plug-in would keep the drive
    board = boot(shift=False)
    assert hidden(board) and max(board.boot_sleeps) >= SETTLE_S


def test_shift_pins_are_released_for_code_py():
    for shift in (False, True):
        board = boot(shift=shift)
        assert set(board.ios) == set(SHIFT_PINS) and all(io.released for io in board.ios.values())


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
    board = boot()
    assert board.devices == board.created and len(board.created) == 2
    ids = []
    for n, dev in zip((1, 2), board.created):
        d = parse(dev.report_descriptor)
        assert d["app"] == (0x01, 0x04, 0x01)              # Generic Desktop, Joystick, Application
        assert (dev.usage_page, dev.usage) == (0x01, 0x04)
        assert dev.report_ids == (d["id"],) and d["id"] != 0
        assert d["inputs"] == [(0x09, 1, BM.SIZE[n], 0, 1, 1, BM.SIZE[n], 0x02)]   # Button 1..N, Data Var Abs
        assert dev.in_report_lengths == (BM.SIZE[n] // 8,) and BM.SIZE[n] % 8 == 0
        assert dev.out_report_lengths == (0,)
        ids.append(d["id"])
    assert len(set(ids)) == 2
