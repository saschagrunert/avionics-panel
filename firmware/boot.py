# boot.py - Avionics Panel rev 1. Runs once at power-up, before USB starts; changes need a replug.
# Two USB joysticks: device 1 (128 buttons) = everything plus unit 1, device 2 (64 buttons) = the
# unit 2 copies. See buttonmap.py / BUTTONS.md.
import supervisor
import usb_hid
import usb_midi

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


usb_hid.enable((joystick(4, 128), joystick(5, 64)))
