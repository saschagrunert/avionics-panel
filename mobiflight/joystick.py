"""MobiFlight's joystick definition of the panel: a label for each button, by its name in firmware/BUTTONS.md
(docs/using/mapping.md#button-names-in-mobiflight).

The format is MobiFlight's *.joystick.json, as its Joysticks/mfjoystick.schema.json describes it and
MobiFlight/Joysticks/JoystickManager.cs reads it (src/MobiFlightConnector/ in MobiFlight-Connector, the same from 11.2
to 11.3.1): it loads every *.joystick.json under its Joysticks folder at its start, and gives a DirectInput joystick
the definition whose InstanceName is the joystick's name, else the one of its USB vendor and product ID. A button is
"Button N", N its HID usage, from 1 (Joystick.RegisterButton), and an input of Type "Button" and Id N labels it
(JoystickInput.Name); the inputs come first in MobiFlight's list, in their order. The labels change only what
MobiFlight shows: a project still names the button "Button N".

Both joysticks are named "Avionics Panel" and share their vendor and product ID, so one definition labels both: each
button of device 1 by its name, and the first buttons, which device 2 has too, by device 2's name as well, which is
the unit 2 copy; the others say they are on device 1 only, as device 2 lists its buttons 40 to 64 but never sends
them. The definition gives no IDs: those of every Pico that runs CircuitPython, the panel's, would label any such
joystick that no definition names.
"""
import json

from mobiflight import profile

BM = profile.BM


def label(number):
    """Button N's label: its number and its names on device 1 and on device 2, or that device 2 has no button N"""
    one = BM.DEVICE[1][number - 1]
    two = BM.DEVICE[2][number - 1] if number <= len(BM.DEVICE[2]) else None
    return f"Button {number}: {one} | " + (f"unit 2: {two}" if two else "device 1 only")


def definition():
    """The definition as a dict: the panel's name and a label for every button device 1 sends"""
    return {
        "$schema": "../mfjoystick.schema.json",
        "InstanceName": profile.NAME,
        "Inputs": [{"Id": n, "Type": "Button", "Label": label(n)} for n in range(1, len(BM.DEVICE[1]) + 1)],
    }


def dumps(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"
