# Mapping

The panel is two USB joysticks, mapped in MobiFlight or directly in the sim's controls. Every state (SHIFT,
UNIT, the frequency knob's mode) lives in the firmware and comes out as fixed joystick buttons, so a mapping
never needs variables or preconditions and can't get out of sync with the panel. What each control is meant to
do is in [Controls](controls.md), and what it maps to per aircraft in [Compatibility](compatibility.md).

## Two joysticks

| Device | Buttons | Carries |
| --- | --- | --- |
| 1 | 117 of 128 | everything, with unit 1 |
| 2 | 39 of 64 | the unit 2 copies of the FMS keys, FMS knob, CDI and OBS, flip-flops and frequency knob, sent while UNIT 2 is selected (SHIFT, HOME) |

[BUTTONS.md](../../firmware/BUTTONS.md) lists every button with what sends it, numbered as Windows and
MobiFlight show them.

- Both devices are named "Avionics Panel", and MobiFlight keys them by their GUID. Tell them apart by their
  button count (128 on device 1, 64 on device 2) or with MobiFlight's input scan: a plain AP press comes from
  device 1, ENT in UNIT 2 from device 2.
- Every knob detent is a short press: map it "on press".
- Shifted functions are buttons of their own. Keys and knobs without an amber legend still send their own
  shifted button: map it to the same function as the plain control, so a stray SHIFT before DN or ENT does no
  harm, or use the slot for a personal mapping.
- The cockpit lighting (SHIFT, FMS knob) stays on device 1 whatever unit is selected.
- The button numbers stay fixed: new buttons only go at the end of a device, and retired ones keep their slot,
  so mappings survive firmware updates.

## Per avionics

- Frequency knob: its push cycles COM, NAV and ADF, and each mode sends turn buttons of its own. For avionics
  that show their own tuning cursor (GNS, GTN), map all three modes to the unit's knob and the push to its
  C/V, so the unit keeps the state. For avionics without one (G1000, KX 155/165, KR 87), map each mode to its
  radio: the mode returns to COM 10 s after the last turn or push, so you always start from COM.
- G1000: UNIT selects radio 2 only, so map the FMS keys and knob of both devices to the MFD
  ([why](controls.md#keys-label-shift-legend-in-parentheses)).
- GNS 430 as unit 2 has its own CDI and OBS, so they are on device 2 too.

## Update mode and GUIDs

Holding SHIFT while plugging in keeps the CIRCUITPY drive and the serial console for an update
([Bring-up](../building/bring-up.md#normal-and-update-mode)). In that mode the joysticks sit on another USB
interface number, so Windows may list them as two more game controllers with DirectInput GUIDs of their own.

- Test the joysticks and create mappings only after a plain replug (without SHIFT), and ignore any extra
  "Avionics Panel" controllers that show up while SHIFT kept the drive.
- Don't add them to MobiFlight's excluded joysticks: that setting matches by name, so it would exclude both
  real devices too.
- Mappings made on the [Pico bench](../building/bring-up.md#pico-bench) don't carry over to the board: the
  board reports another USB serial number, so Windows gives its joysticks new GUIDs. Map the board's joysticks
  again.

## Device name

`boot.py` gives the joysticks' HID interface the name "Avionics Panel" as well as the USB product. In update
mode the panel is a composite device (drive, console and joysticks), and there Windows names a joystick after
its interface, which CircuitPython otherwise calls "CircuitPython HID". Windows also keeps the first name it
saw for a USB ID, and every Pico running CircuitPython shares one (VID 239A, PID 80F4), the Pico bench
included. If joy.cpl or MobiFlight shows "CircuitPython HID" or another old name, unplug the panel, delete
this registry key (regedit) and plug it in again:

```text
HKEY_CURRENT_USER\System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_239A&PID_80F4
```

## Linux

Linux maps at most 80 buttons per joystick, so `evtest` and `jstest` never show device 1's buttons 81 to 117:
check those on Windows, in MobiFlight or a DirectInput tester. While testing on Linux, keep `evtest` or
`jstest` open on either joystick (opening one makes the host poll both): a host that enumerates the panel but
never reads it makes the firmware [back off](../architecture/firmware.md#usb), and the lights and timers
stutter.
