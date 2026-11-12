# Mapping

The panel is two USB joysticks, mapped in MobiFlight, which reads every button; a sim's own control settings
may stop short of a joystick's 128 buttons. Every state (SHIFT, UNIT, the FREQ knob's mode) lives in the
firmware and comes out as fixed joystick buttons, so a mapping never needs variables or preconditions and
cannot get out of sync with the panel, with [one exception](#per-avionics). What each control is meant to do
is in [Controls](controls.md), and what it maps to per aircraft in [Compatibility](compatibility.md). For the
G1000 NXi, [generate the profile](#generated-profiles) instead of mapping by hand.

## Two joysticks

| Device | Buttons | Carries |
| --- | --- | --- |
| 1 | 117 of 128 | Everything, with unit 1 |
| 2 | 39 of 64 | The unit 2 copies of the FMS keys, FMS knob, CDI and OBS, flip-flops and FREQ knob, sent while unit 2 is selected (SHIFT, HOME) |

[BUTTONS.md](../../firmware/BUTTONS.md) lists every button with what sends it, numbered as Windows and
MobiFlight show them.

- Both devices are named "Avionics Panel", and MobiFlight keys them by their GUID (the ID Windows gives a game
  controller). Tell them apart by their button count (128 on device 1, 64 on device 2) or with MobiFlight's
  input scan: a plain AP press comes from device 1, ENT in unit 2 from device 2.
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
  (GNS, GTN), map all three modes to the unit's knob and the push to its C/V (the COM/VLOC cursor toggle), so
  the unit keeps the state. For avionics without one (G1000, KX 155/165, KR 87), map each mode to its radio.
- A GNS or GTN together with an ADF: no mapping stays in sync. The unit's C/V has two states and the knob
  three modes, so with the ADF mode mapped to the ADF receiver, every round through the three modes leaves the
  unit's cursor on the other radio. Go by the cursor on the unit.
- G1000: UNIT selects radio 2 only, so map the FMS keys and knob of both devices to the MFD
  ([why](controls.md#keys-label-shift-legend-in-parentheses)).
- GNS 430 as unit 2 has its own CDI and OBS, so they are on device 2 too.
- In unit 2, CDI, OBS, HOME, ADF ⇆ and the ADF mode's turns come from device 2. Where the aircraft has only
  one of them (the G1000's CDI and OBS softkeys, a single ADF), map device 2's buttons the same as device 1's,
  or they do nothing in unit 2.

## Generated profiles

[mobiflight/](../../mobiflight/) writes a ready MobiFlight 11 project for both joysticks, one avionics family
at a time. The first is the Working Title G1000 NXi in MSFS 2024 (`--family g1000`). It takes the sim events
from [HubHop](https://hubhop.mobiflight.com/)'s presets, the database MobiFlight's own preset lists come from,
and prints the buttons it leaves unmapped; [g1000.py](../../mobiflight/families/g1000.py) gives the reason for
each. Differences from the real G1000:

- The FMS keys and knob, RANGE, pan and PTR work the MFD, in both units.
- The radios are tuned directly, COM 1 / NAV 1 in unit 1 and COM 2 / NAV 2 in unit 2, whichever radio the
  G1000's tuning box is on. 121.5 (SHIFT, COM ⇆) is the exception: it is the G1000's long COM ⇆ press, so it
  tunes the COM radio in the tuning box, and it does nothing in unit 2.
- The fast HDG step is 5°, and CRS has no fast step.

MobiFlight knows a joystick by its GUID, so the project needs the GUIDs of your two joysticks. Let MobiFlight
find them:

1. In MobiFlight, start a new project and add two input configs. Bind the first to ENT in unit 1 (device 1,
   Button 83) and the second to ENT in unit 2 (SHIFT, HOME, then ENT: device 2, Button 10) with the input
   scan. They need no action. Then SHIFT, HOME again for unit 1.
2. Save the project, for example as `guids.mfproj`, and note where.

Then make the profile, with Python 3 and nothing else:

1. Download this repository (on GitHub: Code, Download ZIP) and unpack it. On Windows, install Python 3 from
   [python.org](https://www.python.org/downloads/).
2. Open the folder that holds `mobiflight` (Extract All puts it one level down, in `avionics-panel-main`),
   right-click an empty spot and choose Open in Terminal. There, download HubHop's presets (into
   `hubhop-presets.json`; they are HubHop's data, not part of this repository), then generate the project
   (into `g1000.mfproj`). On Windows:

   ```bat
   py -m mobiflight.hubhop
   py -m mobiflight --family g1000 --from "C:\path\to\guids.mfproj"
   ```

   On Linux and macOS, `python3` instead of `py`.

Using it:

- Open `g1000.mfproj` in MobiFlight as a project of its own; do not merge it into another one that maps the
  same buttons.
- The joysticks match by name and GUID, so no binding dialog comes up. If it does (another PC, a new board,
  the [Pico bench](#update-mode-and-guids)), make a new `guids.mfproj` there and generate the project again:
  the dialog shows both joysticks only as "Avionics Panel" with a GUID.
- `--serials JS-<guid> JS-<guid>` instead of `--from` takes the GUIDs of device 1 and device 2 as MobiFlight
  writes them. The project is a text file: replacing its two GUIDs also moves it to other joysticks.
- Every command goes through MobiFlight's WASM module, which MobiFlight installs into the sim's Community
  folder.

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

`boot.py` names both the USB product and the joysticks' HID (human interface device) interface "Avionics
Panel" (in update mode Windows names a joystick after its interface). Windows keeps the first name it saw for
a USB ID, and every Pico running CircuitPython shares one (VID 239A, PID 80F4: the USB vendor and product ID),
the Pico bench included. If `joy.cpl` or MobiFlight shows "CircuitPython HID" or another old name, unplug the
panel, delete this registry key (`regedit`) and plug it in again:

```text
HKEY_CURRENT_USER\System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_239A&PID_80F4
```

## Linux

Linux makes one input device of both joysticks and maps only the first 80 buttons of device 1 to it, so
`evtest` and `jstest` show nothing of device 2 and never device 1's buttons 81 to 117: check the buttons with
`hid-recorder` ([Flash and test](../building/bring-up.md#flash-and-test)) or on Windows. While testing on
Linux, keep `evtest` or `jstest` open on that input device (it makes the host poll the panel): a host that
enumerates the panel but never reads it makes the firmware [back off](../architecture/firmware.md#usb), and
the lights and timers stutter.
