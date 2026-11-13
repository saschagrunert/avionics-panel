# Mapping

The panel is two USB joysticks, mapped in MobiFlight, which reads every button; a sim's own control settings
may stop short of a joystick's 128 buttons. Every state (SHIFT, UNIT, the FREQ knob's mode) lives in the
firmware and comes out as fixed joystick buttons, so a mapping never needs variables or preconditions and
cannot get out of sync with the panel. What each control is meant to do is in [Controls](controls.md), and
what it maps to per aircraft in [Compatibility](compatibility.md). For MSFS without MobiFlight, and on Xbox
and PS5, there is the [keyboard mode](keyboard.md).

For the avionics families below, download the ready profile. For another aircraft, start from the profile of
the closest family and change the rows that differ: open a row in MobiFlight and choose the aircraft's event
from MobiFlight's presets. Or map the buttons by hand: [Two joysticks](#two-joysticks) and
[Per avionics](#per-avionics).

## Generated profiles

Ready projects for MSFS 2024 and MobiFlight 11.2 or newer map both joysticks, one avionics family each. The
steps below follow MobiFlight 11.3. The families, with the profile to download:

- [G1000 NXi](#g1000-nxi): [avionics-panel-g1000.mfproj][g1000]
- [GFC 500 and G3X Touch](#gfc-500-and-g3x-touch): [avionics-panel-g3x.mfproj][g3x]
- [GNS 530/430](#gns-530430) with the KAP 140, also for KX 155/165 radios without a GNS:
  [avionics-panel-gns.mfproj][gns]
- [TDS GTN 750Xi and 650Xi](#tds-gtn-750xi-and-650xi) with the KAP 140: [avionics-panel-gtn.mfproj][gtn]

The downloads are on the release [Latest build][rolling]. To use one:

1. Install MobiFlight 11.2 or newer. Every command of the profiles goes through MobiFlight's WASM module in
   the sim's Community folder: when MobiFlight offers it, choose Install Now with the sim closed (later:
   Extras, Microsoft Flight Simulator, Re-install WASM Module).
2. Plug in the panel, download the profile of your family and open it in MobiFlight (File, Open). MobiFlight
   says "Your input is needed!" for the "Avionics Panel" joysticks. Close that message; the next step binds
   the joysticks.
3. Choose Extras, Controller Bindings. It lists the profile's two joysticks as "Avionics Panel", one with
   `JS-device-1` below the name and one with `JS-device-2`. The dialog does not show which of your two
   "Avionics Panel" joysticks is device 1: bind `JS-device-1` to either and `JS-device-2` to the other, choose
   Apply changes, and check the choice in step 4.
4. Start a flight in an aircraft of your family with the avionics on and choose Run in MobiFlight. With the
   amber light by SHIFT off (wait for it to go out), turn the inner knob of the ALT/HDG knob one detent: the
   heading bug must move by 1 degree. If it does not, the joysticks are the wrong way round: open the
   downloaded profile again (File, Open, and do not save the changes), bind them the other way and repeat
   this step. If the bug moves neither way, check that MobiFlight is connected to the sim and its WASM
   module is installed, that you chose Run, and that the panel was plugged in without SHIFT held and shows up
   as two joysticks (in keyboard mode it is a keyboard: [Keyboard mode](keyboard.md)).
5. Save the project (File, Save). From then on it opens without asking.

Or generate a profile bound to your own joysticks, so MobiFlight opens it without asking, with Python 3 and
nothing else. MobiFlight knows a joystick by its GUID, so let it find them:

1. In MobiFlight, start a new project and add two input configs. Bind the first to ENT in unit 1 (device 1,
   Button 83) and the second to ENT in unit 2 (SHIFT, HOME, then ENT: device 2, Button 10) with the input
   scan. They need no action. Then SHIFT, HOME again for unit 1.
2. Save the project, for example as `guids.mfproj`, and note where.
3. Download this repository (on GitHub: Code, Download ZIP) and unpack it. On Windows, install Python 3 from
   [python.org](https://www.python.org/downloads/).
4. Open the folder that holds `mobiflight` (Extract All puts it one level down, in `avionics-panel-main`),
   right-click an empty spot and choose Open in Terminal. There, generate the project of your family
   (`--family g1000`, `g3x`, `gns` or `gtn`), here the G1000 (into `g1000.mfproj`). On Windows:

   ```bat
   py -m mobiflight --family g1000 --from "C:\path\to\guids.mfproj"
   ```

   On Linux and macOS, `python3` instead of `py`. Without `--from` it makes the profile of the download.
   `--vfr 7000` makes the VFR key squawk 7000, or any other code of four digits from 0 to 7.
5. Open the new project in MobiFlight (File, Open).

Using it:

- Open the project in MobiFlight as a project of its own, the one of the family you fly; do not merge it into
  another one that maps the same buttons.
- On another PC, with a new board or on the [Pico bench](#update-mode-and-guids) the joysticks have other
  GUIDs and MobiFlight asks again. Bind the project's two joysticks to the new ones in Extras, Controller
  Bindings, and check them with the heading bug before you save (step 4 of the steps above): if it does not
  move, open the project again without saving and bind them the other way. Or generate the profile again with
  a new `guids.mfproj`.
- `--serials JS-<guid> JS-<guid>` instead of `--from` takes the GUIDs of device 1 and device 2 as MobiFlight
  writes them, and names both joysticks "Avionics Panel"; for the [simulator](simulator.md)'s vJoy devices use
  `--from`, which keeps their names. The project is a text file: replacing its two serials also moves it to
  other joysticks.

Every family tunes the radios directly, COM 1 / NAV 1 in unit 1 and COM 2 / NAV 2 in unit 2, whatever the
avionics' own tuning box or cursor is on. The ADF mode's turns tune the active ADF frequency, and ADF ⇆ swaps
it with the standby. 121.5 (SHIFT, COM ⇆) sets the active frequency of the unit's COM radio to 121.5. VFR
squawks 1200; for another VFR code, 7000 in much of Europe, change the `0x1200` in the code of the row
"VFR: XPNDR_SET" in MobiFlight, or generate the profile with `--vfr 7000` (above). The XPDR mode push (SHIFT,
FREQ push) switches the simulator's transponder between standby and ALT. MobiFlight shows the commands as
custom code.

Does nothing in every profile: the FREQ push (it only switches the FREQ knob between COM, NAV and ADF; it
sends nothing to the sim) and the dimmers (they differ by aircraft). Each family below lists what else does
nothing, mostly the keys its avionics lack ([Compatibility](compatibility.md)).

### G1000 NXi

The Working Title G1000 NXi, as in the Cessna 172 Skyhawk G1000. The autopilot, knob and FMS rows follow
Working Title's source of the NXi. The NXi itself turns ALT's 100 ft steps into 1000 ft steps from the 11th
step of a quick turn (steps less than 0.3 s apart, one way). Differences from the real G1000:

- The FMS keys and knob, RANGE, pan and PTR work the MFD, in both units.
- CDI steps through GPS, NAV 1 and NAV 2 as the CDI softkey does, and OBS switches the GPS's OBS mode, from
  both units. In SUSP, OBS switches to OBS mode instead of resuming the sequence as the softkey does.
- UP and DN step the VS, IAS or pitch reference, as NOSE UP and NOSE DN do, but not the altitude in ALT hold.
- LVL engages the autopilot in its wings-level and pitch-level modes, also in aircraft without a LVL key.

Does nothing in this profile: TEST, ARM, GPSS and ½ BANK (MSFS's GFC 700 has no such keys; it flies GPS
steering in NAV), HOME, VNAV and TERR (the G1000 has no such keys; the autopilot's VNV key works), MSG and
NRST (softkeys, which change with the menu), MAP (SHIFT, CLR; the NXi takes no long CLR press from outside).

### GFC 500 and G3X Touch

The GFC 500 autopilot with Working Title's G3X Touch, as in the CubCrafters XCub (one display) and the Draco X
(PFD and MFD). Unit 1 works the PFD, or the only display, with COM 1 / NAV 1, and unit 2 the MFD with COM 2 /
NAV 2. If the FMS keys in unit 1 work the MFD, the aircraft numbers its displays the other way round. The FMS
keys and knob are the G3X's bezel: D→, MENU, CLR as BACK, NRST and the right knob. A GNS or GTN beside the
G3X gets nothing from this profile. Differences from the real units:

- With one display, the FMS keys and knob do nothing in unit 2.
- CDI and OBS work the one CDI from both units. CDI switches between GPS and NAV 1.
- CRS sets the course of what the CDI shows. CRS CTR (SHIFT, HDG) centres a VOR or localizer course and does
  nothing on GPS.
- UP and DN step the VS, IAS or pitch reference, as the GMC 507's wheel does, but not the altitude in ALT hold.
- Where the G3X manages the transponder's ground mode by itself, it turns the ALT of the XPDR mode push into
  that mode on the ground.

Does nothing in this profile: TEST, ARM, GPSS, BC and ½ BANK (the GFC 500 has no such keys), HOME (the G3X
has none), FPL, ENT, MSG, VNAV, TERR, MAP, RANGE, the map's pan and PTR (on the touchscreen; the map zooms
with the inner FMS knob on the map page), PROC (the G3X loads no procedures).

### GNS 530/430

The Working Title GNS 530 as unit 1 and GNS 430 as unit 2 in the KAP 140 cockpit: the KAP 140 with a KR 87
ADF, a KT 76 transponder and a KMA 28 audio panel, as in the Cessna 172 Skyhawk Classic. The same profile
drives KX 155/165 radios without a GNS; the FMS keys, CDI, OBS and RANGE then do nothing. With another
autopilot the autopilot keys do nothing: map them in the project by hand. Two GNS of the same type, two
GNS 430 for example, are not covered: the profile's events cannot tell the two apart. Differences from the
real units:

- The ALT/HDG knob sets the KAP 140's altitude and the heading bug, and its push syncs the bug to the heading,
  as on the G1000. With SHIFT it sets the course of NAV 1 and the altimeter, not the KAP 140's own BARO.
- CRS CTR (SHIFT, HDG) sets the course of NAV 1 to its VOR or localizer; the KAP 140 cockpit's CDI has no
  such push.
- RANGE is the GNS 530's RNG key, in both units.
- The XPDR mode push turns the KT 76's mode knob: to ALT from OFF or SBY, to SBY from any other position.

Does nothing in this profile: TEST, FD, YD, VS, FLC, VNV, LVL, GPSS and ½ BANK (the KAP 140 has none of these
keys; it engages in VS, and UP and DN set the rate), ARM (the sim's KAP 140 does nothing on it), HOME (the GNS
has none), NRST and TERR (the GNS has pages for them, not keys), the map's pan and PTR (the GNS has no
joystick), VNAV in unit 2 (the GNS 430 has none).

### TDS GTN 750Xi and 650Xi

The KAP 140 cockpit of the [GNS profile](#gns-530430) with TDS's GTN 750Xi as unit 1 and GTN 650Xi as unit 2.
Aircraft that load the 650Xi as unit 1, as Black Square's do, are not covered: there the 650Xi's bezel does
nothing in unit 2. TDS takes only the bezel from outside, so the profile sends HOME, D→, the FMS knob and its
push; held, the push flips the frequencies. The map zooms on the touchscreen or with the inner FMS knob on the
map page.

COM ⇆ and NAV ⇆ are the sim's flip-flops, as the GTN has no such keys. TDS says the GTNs control the sim's COM
and NAV radios; if a frequency set with the FREQ knob does not show on the GTN, tune it there with the FMS
knob, whose push toggles between COM and NAV. The XPDR mode push works the cockpit's KT 76 through the
simulator's variable; a transponder that the GTN runs itself may not follow it.

Does nothing in this profile: TEST, FD, YD, VS, FLC, VNV, LVL, GPSS, ½ BANK and ARM (as in the GNS profile),
FPL, PROC, MENU, CLR, ENT, MSG, NRST, TERR, VNAV, MAP, CDI, OBS, RANGE, the map's pan and PTR (on the
touchscreen).

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
  unit, and the one ADF), as the [generated profiles](#generated-profiles) do; a GNS shows the frequencies
  whichever field its cursor is on; for a GTN see [TDS GTN 750Xi and 650Xi](#tds-gtn-750xi-and-650xi).
- G1000: map the FMS keys and knob of both devices to the MFD
  ([why](controls.md#keys-label-shift-legend-in-parentheses)).
- GNS 430 as unit 2 has its own CDI and OBS, so they are on device 2 too.
- In unit 2, CDI, OBS, HOME, ADF ⇆ and the ADF mode's turns come from device 2. Where the aircraft has only
  one of them (the G1000's CDI and OBS softkeys, a single ADF), map device 2's buttons the same as device 1's,
  or they do nothing in unit 2.

## Knob timing

MobiFlight must count every detent of a quick turn ([why](../architecture/firmware.md#knob-steps)). To check
it once, with a sim running:

1. In a new MobiFlight project, map `FMS_INNER_CW` of both devices (Button 95 on device 1, Button 22 on
   device 2) to a counter you can read in the sim, for example heading bug +1.
2. Spin the FMS inner ring 8 detents quickly: the bug must move by 8°.
3. Repeat in unit 2 (SHIFT, HOME) while UP is held: the FMS knob is on device 2 there, and UP repeats on
   device 1.
4. In unit 2, turn the FMS inner ring and the ALT/HDG outer ring 4 quick detents each at the same time
   (ALT/HDG is on device 1): the bug must move by 4°. No more than 4 each: the firmware keeps at most 8
   detents waiting, all rings together, and drops the rest.

If steps go missing, tune `PRESS_MS`, `GAP_MS` and `MAX_QUEUE` in [panel.py](../../firmware/panel.py) (a
step longer than the 120 ms tilt repeat slows a held tilt down).

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

With USB autosuspend on for the panel (`power/control` at `auto`, which powertop sets), Linux suspends it after
a few idle seconds: both lights go dark, SHIFT ends, and the next input reaches the PC about 2 s late (a SHIFT
tap as that input is lost), as does a key let go just before the suspend
([why](../architecture/firmware.md#usb)). Set its `power/control` to `on`.

[g1000]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-g1000.mfproj
[g3x]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-g3x.mfproj
[gns]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-gns.mfproj
[gtn]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-gtn.mfproj
[rolling]: https://github.com/saschagrunert/avionics-panel/releases/tag/rolling
