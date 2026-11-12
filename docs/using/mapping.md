# Mapping

The panel is two USB joysticks, mapped in MobiFlight, which reads every button; a sim's own control settings
may stop short of a joystick's 128 buttons. Every state (SHIFT, UNIT, the FREQ knob's mode) lives in the
firmware and comes out as fixed joystick buttons, so a mapping never needs variables or preconditions and
cannot get out of sync with the panel. What each control is meant to do is in [Controls](controls.md), and
what it maps to per aircraft in [Compatibility](compatibility.md). For the families under
[Generated profiles](#generated-profiles), generate the profile instead of mapping by hand.

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

- FREQ knob: its push cycles COM, NAV and ADF, and each mode sends turn buttons of its own. The mode stays
  until the next push, and the panel has no light for it. Map each mode to its radio (COM and NAV 1 or 2 by
  unit, and the one ADF), as the [generated profiles](#generated-profiles) do; a GNS or GTN shows the
  frequencies whichever field its cursor is on.
- G1000: UNIT selects radio 2 only, so map the FMS keys and knob of both devices to the MFD
  ([why](controls.md#keys-label-shift-legend-in-parentheses)).
- GNS 430 as unit 2 has its own CDI and OBS, so they are on device 2 too.
- In unit 2, CDI, OBS, HOME, ADF ⇆ and the ADF mode's turns come from device 2. Where the aircraft has only
  one of them (the G1000's CDI and OBS softkeys, a single ADF), map device 2's buttons the same as device 1's,
  or they do nothing in unit 2.

## Generated profiles

[mobiflight/](../../mobiflight/) writes a ready MobiFlight 11 project for both joysticks, one avionics family
at a time, for MSFS 2024. It takes the sim events from [HubHop](https://hubhop.mobiflight.com/)'s presets, the
database MobiFlight's own preset lists come from, and prints the buttons it leaves unmapped, with the reason
for each. Every family tunes the radios directly, COM 1 / NAV 1 in unit 1 and COM 2 / NAV 2 in unit 2,
whatever the avionics' own tuning box or cursor is on: the FREQ push only changes the panel's mode. The ADF
mode's turns tune the active ADF frequency, and ADF ⇆ swaps it with the standby. The families:

- [G1000 NXi](#g1000-nxi): `--family g1000`
- [GNS 530/430](#gns-530430) with the KAP 140, also for KX 155/165 radios without a GNS: `--family gns`
- [TDS GTN 750Xi and 650Xi](#tds-gtn-750xi-and-650xi) with the KAP 140: `--family gtn`

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
   `hubhop-presets.json`; they are HubHop's data, not part of this repository), then generate the project of
   your family, here the G1000 (into `g1000.mfproj`). On Windows:

   ```bat
   py -m mobiflight.hubhop
   py -m mobiflight --family g1000 --from "C:\path\to\guids.mfproj"
   ```

   On Linux and macOS, `python3` instead of `py`.

Using it:

- Open the project in MobiFlight as a project of its own, the one of the family you fly; do not merge it into
  another one that maps the same buttons.
- The joysticks match by name and GUID, so no binding dialog comes up. If it does (another PC, a new board,
  the [Pico bench](#update-mode-and-guids)), make a new `guids.mfproj` there and generate the project again:
  the dialog shows both joysticks only as "Avionics Panel" with a GUID.
- `--serials JS-<guid> JS-<guid>` instead of `--from` takes the GUIDs of device 1 and device 2 as MobiFlight
  writes them. The project is a text file: replacing its two GUIDs also moves it to other joysticks.
- Every command goes through MobiFlight's WASM module, which MobiFlight installs into the sim's Community
  folder.

### G1000 NXi

The Working Title G1000 NXi. Differences from the real G1000:

- The FMS keys and knob, RANGE, pan and PTR work the MFD, in both units.
- 121.5 (SHIFT, COM ⇆) is the G1000's long COM ⇆ press, so it tunes the COM radio in the tuning box, and it
  does nothing in unit 2.
- The fast HDG step is 5°, and CRS has no fast step.

### GNS 530/430

The Working Title GNS 530 as unit 1 and GNS 430 as unit 2 in the KAP 140 cockpit: the KAP 140 with a KR 87
ADF, a KT 76 transponder and a KMA 28 audio panel, as in the Cessna 172 Skyhawk Classic. The same profile
drives KX 155/165 radios without a GNS; the FMS keys, CDI, OBS and RANGE then do nothing. With another
autopilot the autopilot keys do nothing: map them in the project by hand. Differences from the real units:

- The ALT/HDG knob sets the KAP 140's altitude and the heading bug, whose fast step is 5°, and its push syncs
  the bug to the heading, as on the G1000. With SHIFT it sets the course of NAV 1 and the altimeter, not the
  KAP 140's own BARO.
- RANGE is the GNS 530's RNG key, in both units.
- 121.5 (SHIFT, COM ⇆) does nothing: the Working Title GNS's COM flip-flop has no long press.

### TDS GTN 750Xi and 650Xi

The KAP 140 cockpit of the [GNS profile](#gns-530430) with TDS's GTN 750Xi as unit 1 and GTN 650Xi as unit 2,
as TDS's MSFS 2024 aircraft mods number them; aircraft that load the 650Xi as unit 1, as Black Square's do,
are not covered. If HOME in unit 2 does nothing on the 650Xi, the aircraft loads it as unit 1. TDS takes only
the bezel from outside, so the profile sends HOME, D→, the FMS knob and its push (held, it flips the
frequencies) and 121.5, which holds the volume knob pushed: tap SHIFT, then hold COM ⇆ for about 2 s (a short
press toggles the squelch). The other FMS keys, CDI, OBS and the map's pan are on the touchscreen, and the map
zooms there or with the inner FMS knob on the map page. COM ⇆ and NAV ⇆ are the sim's flip-flops, as the GTN
has no such keys.

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
- Mappings made on the [simulator](simulator.md)'s vJoy devices do not attach to the panel either: bind them to
  the panel's devices once it is plugged in ([how](simulator.md#from-the-simulator-to-the-panel)).

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
