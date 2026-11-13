# boot.py - Avionics Panel rev 1. Runs once at power-up, before USB starts; changes need a replug.
# Two USB joysticks: device 1 (128 buttons) = everything plus unit 1, device 2 (64 buttons) = the
# unit 2 copies. See buttonmap.py / BUTTONS.md.
# In normal use the panel is only the two joysticks: no CIRCUITPY drive (the PC can't write to it, and it
# can't ask to be ejected) and no serial console. To keep both for an update, hold SHIFT while plugging in
# and until CIRCUITPY appears (about 2 s): CircuitPython waits up to 1 s (its safe-mode window) after
# power-up before it runs this file, and SHIFT is read only then.
# Holding the HOME key (amber legend UNIT) alone the same way switches between the joysticks and the keyboard
# mode (keys.py), which the panel keeps from then on; in keyboard mode the lights take turns at each start.
import time

import digitalio
import keys
import microcontroller
import storage
import supervisor
import usb_cdc
import usb_hid
import usb_midi

# SHIFT is matrix row 3, column 3 (buttonmap.MATRIX; pcb/board.py ROW_GP, COL_GP): row GP2, column GP6.
# The diode anode is on the column, so with the row driven low and the column pulled up, a held SHIFT
# reads low. The other rows are left as CircuitPython resets them (input, no pull), so no other key can
# pull the column down. UNIT (HOME) sits above it in the same column: row 2, GP5.
SHIFT_ROW, SHIFT_COL = microcontroller.pin.GPIO2, microcontroller.pin.GPIO6
UNIT_ROW = microcontroller.pin.GPIO5

# GP25, the FREQ outer ring's B line, is also the Pico build's status LED: at brightness 0 its blinks from here
# on drive the pin low, not high (docs/architecture/firmware.md, Pins)
supervisor.runtime.rgb_status_brightness = 0


def held(row_pin):
    """Whether the key of this row in SHIFT's column is held"""
    row = digitalio.DigitalInOut(row_pin)
    col = digitalio.DigitalInOut(SHIFT_COL)
    try:
        col.switch_to_input(pull=digitalio.Pull.UP)
        row.switch_to_output(value=False)
        time.sleep(0.005)                        # the pull-up charges the column
        return not col.value
    finally:                                     # free the pins for code.py's keypad
        row.deinit()
        col.deinit()


update = held(SHIFT_ROW)
if not update:
    storage.disable_usb_drive()
    usb_cdc.disable()

supervisor.set_usb_identification("DIY", "Avionics Panel")
usb_midi.disable()


def joystick(report_id, buttons):
    descriptor = bytes((
        0x05, 0x01,              # Usage Page (Generic Desktop)
        0x09, 0x04,              # Usage (Joystick)
        0xA1, 0x01,              # Collection (Application)
        0x85, report_id,         #   Report ID
        0x05, 0x09,              #   Usage Page (Button)
        0x19, 0x01,              #   Usage Minimum (1)
        0x29, buttons,           #   Usage Maximum
        0x15, 0x00,              #   Logical Minimum (0)
        0x25, 0x01,              #   Logical Maximum (1)
        0x75, 0x01,              #   Report Size (1)
        0x95, buttons,           #   Report Count
        0x81, 0x02,              #   Input (Data, Var, Abs)
        0xC0,                    # End Collection
    ))
    return usb_hid.Device(report_descriptor=descriptor, usage_page=0x01, usage=0x04,
                          report_ids=(report_id,), in_report_lengths=(buttons // 8,), out_report_lengths=(0,))


# Windows names a joystick on a composite USB device (SHIFT mode: drive, console and HID) after its HID
# interface, which CircuitPython calls "CircuitPython HID" unless told otherwise, and keeps the first name
# it saw (docs/using/mapping.md, Device name)
usb_hid.set_interface_name("Avionics Panel")
if keys.keyboard_mode(microcontroller.nvm, held(UNIT_ROW)):
    # One boot keyboard instead (keys.py), as the PS5 is reported to need. CircuitPython declares the boot
    # protocol only on USB interface 0 (else safe mode): not with the console and drive of an update, which come
    # first.
    keyboard = usb_hid.Device(report_descriptor=keys.DESCRIPTOR, usage_page=0x01, usage=0x06, report_ids=(0,),
                              in_report_lengths=(keys.REPORT,), out_report_lengths=(1,))
    usb_hid.enable((keyboard,), boot_device=0 if update else 1)
else:
    usb_hid.enable((joystick(4, 128), joystick(5, 64)))
