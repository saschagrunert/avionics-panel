"""Host tests for boot.py: runs it on the stand-in hardware of sim/hardware.py. SHIFT held is its switch closed
between its row and column pin: the column then reads low while the row pin drives low. UNIT (HOME) the same.
"""
import buttonmap as BM
import keys

from sim.hardware import SETTLE_S, Board

SHIFT_PINS = ("GP2", "GP6")        # row, column of SHIFT; tests/test_pins.py checks them against the board
UNIT_PINS = ("GP5", "GP6")         # row, column of HOME (UNIT), as well


def boot(shift=False, pins=SHIFT_PINS, unit=False, keyboard=False):
    """boot.py on a board with SHIFT held (its switch between pins closed) or not, UNIT held or not, and the
    keyboard mode stored or not"""
    board = Board(keyboard=keyboard)
    if shift:
        board.closed.add(pins)
    if unit:
        board.closed.add(UNIT_PINS)
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
    # number, so Windows may see new controllers in update mode; docs/using/mapping.md)
    for shift in (False, True):
        board = boot(shift=shift)
        assert board.calls.count(("set_usb_identification", "DIY", "Avionics Panel")) == 1
        assert board.calls.count(("usb_midi.disable",)) == 1


def test_hid_interface_carries_the_name():
    # on a composite device (update mode) Windows names the joysticks after the HID interface, not the product:
    # without this they would show as "CircuitPython HID". CircuitPython reads it when USB starts, after boot.py
    for shift in (False, True):
        board = boot(shift=shift)
        assert [c for c in board.calls if c[0] == "usb_hid.set_interface_name"] == [
            ("usb_hid.set_interface_name", "Avionics Panel")]


def test_shift_is_read_after_the_column_settles():
    # without the settle the column would still read low and every plain plug-in would keep the drive
    board = boot(shift=False)
    assert hidden(board) and max(board.boot_sleeps) >= SETTLE_S


def test_shift_and_unit_pins_are_released_for_code_py():
    for shift in (False, True):
        board = boot(shift=shift)
        assert set(board.ios) == set(SHIFT_PINS + UNIT_PINS) and all(io.released for io in board.ios.values())


def test_status_led_is_dark_after_boot():
    # GP25, the Pico build's status LED, is the FREQ outer encoder's B line: at brightness 0 the supervisor's
    # blinks after boot.py drive it low, in every mode (the stand-in starts at full brightness, as the board)
    assert Board().rgb_status_brightness == 0xFF
    for shift in (False, True):
        for keyboard in (False, True):
            assert boot(shift=shift, keyboard=keyboard).rgb_status_brightness == 0


def test_shift_is_matrix_row_3_column_3_and_unit_above_it():
    assert BM.MATRIX[3][3] == "SHIFT" and BM.MATRIX[2][3] == "HOME"


# ---------------- keyboard mode ----------------
def keyboard(board):
    """The keyboard boot.py enabled, after checking it is the only HID device"""
    [device] = board.devices
    assert (device.usage_page, device.usage, device.report_descriptor) == (0x01, 0x06, keys.DESCRIPTOR)
    assert (device.report_ids, device.in_report_lengths, device.out_report_lengths) == ((0,), (keys.REPORT,), (1,))
    return device


def test_the_joysticks_are_the_default_and_unit_alone_leaves_the_mode_stored():
    # a blank flash (0xFF), or any byte but KEYBOARD: the two joysticks, and nothing is written without UNIT
    for byte in (0xFF, 0x00, keys.KEYBOARD ^ 1):
        board = Board()
        board.nvm[keys.MODE_BYTE] = byte
        board.boot()
        assert [d.usage for d in board.devices] == [0x04, 0x04] and board.nvm[keys.MODE_BYTE] == byte
    board = boot(keyboard=True)
    assert keyboard(board) and board.nvm[keys.MODE_BYTE] == keys.KEYBOARD


def test_unit_held_at_plug_in_switches_the_mode_and_keeps_it():
    board = boot(unit=True)                                       # to keyboard mode
    assert keyboard(board) and board.boot_device == 1 and board.nvm[keys.MODE_BYTE] == keys.KEYBOARD
    again = Board()
    again.nvm[:] = board.nvm                                      # unplugged and plugged in again, without UNIT
    assert keyboard(again.boot())
    back = Board()
    back.nvm[:] = board.nvm
    back.closed.add(UNIT_PINS)
    back.boot()                                                   # UNIT held again: back to the joysticks
    assert [d.usage for d in back.devices] == [0x04, 0x04] and back.nvm[keys.MODE_BYTE] == keys.JOYSTICK
    assert all(b == 0xFF for b in back.nvm[1:])                   # nothing else written


def test_keyboard_mode_keeps_the_usb_name_and_the_drive_rules():
    # the same names as with the joysticks; the drive and console only with SHIFT held, and the boot protocol
    # only without them: CircuitPython allows it on USB interface 0 only (safe mode otherwise)
    for shift in (False, True):
        board = boot(shift=shift, keyboard=True)
        assert keyboard(board) and board.boot_device == (0 if shift else 1)
        assert bool(hidden(board)) is not shift
        assert board.calls.count(("set_usb_identification", "DIY", "Avionics Panel")) == 1
        assert board.calls.count(("usb_hid.set_interface_name", "Avionics Panel")) == 1
    board = boot(shift=True, unit=True)                           # both held: the update, in keyboard mode
    assert keyboard(board) and board.boot_device == 0 and not hidden(board)


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
    assert board.devices == board.created and len(board.created) == 2 and board.boot_device == 0
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
