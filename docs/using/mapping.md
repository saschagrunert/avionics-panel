# Mapping

The panel is two USB joysticks, mapped in MobiFlight, which reads every button; a sim's own control settings
may stop short of a joystick's 128 buttons. Every state (SHIFT, UNIT, the FREQ knob's mode) lives in the
firmware and comes out as fixed joystick buttons, so a mapping never needs variables or preconditions and
cannot get out of sync with the panel, with [one exception](#per-avionics). What each control is meant to do
is in [Controls](controls.md), and what it maps to per aircraft in [Compatibility](compatibility.md).

## Two joysticks

| Device | Buttons | Carries |
| --- | --- | --- |
| 1 | 117 of 128 | Everything, with unit 1 |
| 2 | 39 of 64 | The unit 2 copies of the FMS keys, FMS knob, CDI and OBS, flip-flops and FREQ knob, sent while unit 2 is selected (SHIFT, HOME) |

[BUTTONS.md](../../firmware/BUTTONS.md) lists every button with what sends it, numbered as Windows and
MobiFlight show them.

- Both devices are named "Avionics Panel", and MobiFlight keys them by their GUID. Tell them apart by their
  button count (128 on device 1, 64 on device 2) or with MobiFlight's input scan: a plain AP press comes from
  device 1, ENT in unit 2 from device 2.
- Every knob detent is a short press, and so is every step of a held UP or DN, every pan step of a RANGE
  tilt and the RANGE push (PTR): map them "on press".
- Shifted functions are buttons of their own. The keys without an amber legend (VS, UP, FLC, DN, VNV, ENT)
  and the RANGE knob (turn, tilt, push) still send a shifted button of their own: these are free for your own
  mappings. Map the ones you do not use to the same function as the plain control, so a stray SHIFT before DN
  or ENT does no harm.
- The cockpit lighting (SHIFT, FMS knob) stays on device 1 whatever unit is selected.
- The button numbers stay fixed: new buttons only go at the end of a device, and retired ones keep their slot,
  so mappings survive firmware updates.

## Per avionics

- FREQ knob: its push cycles COM, NAV and ADF, and each mode sends turn buttons of its own. The mode
  stays until the next push, and the panel has no light for it. For avionics that show their own tuning cursor
  (GNS, GTN), map all three modes to the unit's knob and the push to its C/V, so the unit keeps the state. For
  avionics without one (G1000, KX 155/165, KR 87), map each mode to its radio.
- A GNS or GTN together with an ADF: no mapping stays in sync. The unit's C/V has two states and the knob
  three modes, so with the ADF mode mapped to the ADF receiver, every round through the three modes leaves the
  unit's cursor on the other radio. Go by the cursor on the unit.
- G1000: UNIT selects radio 2 only, so map the FMS keys and knob of both devices to the MFD
  ([why](controls.md#keys-label-shift-legend-in-parentheses)).
- GNS 430 as unit 2 has its own CDI and OBS, so they are on device 2 too.

## Update mode and GUIDs

Holding SHIFT while plugging in keeps the CIRCUITPY drive and the serial console for an update
([Bring-up](../building/bring-up.md#normal-and-update-mode)). In that mode the joysticks sit on another USB
interface number, so Windows may list them as two more game controllers with DirectInput GUIDs of their own.

- Test the joysticks and create mappings only after a plain replug (without SHIFT), and ignore any extra
  "Avionics Panel" controllers that show up while SHIFT kept the drive.
- Do not add them to MobiFlight's excluded joysticks: that setting matches by name, so it would exclude both
  real devices too.
- Mappings made on the [Pico bench](../building/bring-up.md#pico-bench) do not carry over to the board: the
  board reports another USB serial number, so Windows gives its joysticks new GUIDs. Map the board's joysticks
  again.

## Device name

`boot.py` names both the USB product and the joysticks' HID interface "Avionics Panel" (in update mode
Windows names a joystick after its interface). Windows keeps the first name it saw for a USB ID, and every
Pico running CircuitPython shares one (VID 239A, PID 80F4), the Pico bench included. If `joy.cpl` or
MobiFlight shows "CircuitPython HID" or another old name, unplug the panel, delete this registry key
(`regedit`) and plug it in again:

```text
HKEY_CURRENT_USER\System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_239A&PID_80F4
```

## Linux

Linux maps at most 80 buttons per joystick, so `evtest` and `jstest` never show device 1's buttons 81 to 117:
check those on Windows, in MobiFlight or a DirectInput tester. While testing on Linux, keep `evtest` or
`jstest` open on either joystick (opening one makes the host poll both): a host that enumerates the panel but
never reads it makes the firmware [back off](../architecture/firmware.md#usb), and the lights and timers
stutter.
