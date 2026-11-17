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

Ready projects for MSFS 2024 and MobiFlight 11.2 or newer map both joysticks, for one avionics family or one
aircraft each. The steps below follow MobiFlight 11.3. The profiles to download:

- [G1000 NXi](#g1000-nxi): [avionics-panel-g1000.mfproj][g1000]
- [GFC 500 and G3X Touch](#gfc-500-and-g3x-touch): [avionics-panel-g3x.mfproj][g3x]
- [GNS 530/430](#gns-530430) with the KAP 140, also for KX 155/165 radios without a GNS:
  [avionics-panel-gns.mfproj][gns]
- [TDS GTN 750Xi and 650Xi](#tds-gtn-750xi-and-650xi) with the KAP 140: [avionics-panel-gtn.mfproj][gtn]
- [Black Square Bonanza](#black-square-bonanza), its KFC 150 and KAS 297B with every avionics selection of its
  tablet: [avionics-panel-black-square-bonanza.mfproj][bonanza] (formerly the KFC 150 profile,
  `avionics-panel-kfc150.mfproj` and `--family kfc150`)
- [COWS DA40](#cows-da40), the G1000 NXi with its autopilot: [avionics-panel-cows-da40.mfproj][da40]
- [Carenado C182T](#carenado-c182t), the G1000 with the KAP 140: [avionics-panel-carenado-c182t.mfproj][c182t]

For other avionics, join [avionics parts](#avionics-parts) instead. Each profile has a
[quick-reference card](#quick-reference-cards) to print, and MobiFlight can show the buttons by their names
([Button names in MobiFlight](#button-names-in-mobiflight)). The downloads are on the release [Latest
build][rolling]. To use one:

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
   amber light by SHIFT off (wait for it to go out; tap SHIFT if it blinks), turn the inner knob of the
   ALT/HDG knob one detent: the heading bug must move by 1 degree. If it does not, the joysticks are the wrong
   way round: open the downloaded profile again (File, Open, and do not save the changes), bind them the other
   way and repeat this step. If the bug moves neither way, check that MobiFlight is connected to the sim and
   its WASM module is installed, that you chose Run, and that the panel was plugged in without SHIFT held and
   shows up as two joysticks (in keyboard mode it is a keyboard: [Keyboard mode](keyboard.md)).
5. Save the project (File, Save). From then on it opens without asking.

Each project names the commit it was built from at the end of its name, its first `"Name"` in the file (a text
file), as "Avionics Panel: G1000 NXi (2026-11-14, 5d1c305)": the date and the short hash. A download with a
later date is newer; on the same day, the hash tells them apart, and the release's tag names the latest.

Or generate a profile bound to your own joysticks, so MobiFlight opens it without asking. On Windows the
[simulator's zip][sim-zip] does it with the Python it carries, so nothing needs installing; on Linux and macOS
it takes Python 3.10 or newer and nothing else. MobiFlight knows a joystick by its GUID, so let it find them:

1. In MobiFlight, start a new project and add two input configs. Bind the first to ENT in unit 1 (device 1,
   Button 83) and the second to ENT in unit 2 (SHIFT, HOME, then ENT: device 2, Button 10) with the input
   scan. They need no action. Then SHIFT, HOME again for unit 1.
2. Save the project, for example as `guids.mfproj`, and note where.
3. On Windows, download [avionics-panel-sim-windows.zip][sim-zip], unblock and extract it as in step 2 of
   [Simulator](simulator.md#windows), and open its `avionics-panel-sim` folder. On Linux and macOS, download
   this repository (on GitHub: Code, Download ZIP), unpack it and open the folder that holds `mobiflight`
   (`avionics-panel-main`).
4. Right-click an empty spot in that folder and choose Open in Terminal. There, generate the project of your
   profile (`--family g1000`, `g3x`, `gns`, `gtn`, `black-square-bonanza`, `cows-da40` or `carenado-c182t`),
   here the G1000 (into `avionics-panel-g1000.mfproj`, the download's name), or of your [avionics
   parts](#avionics-parts). On Windows, with the zip's `profile.bat` (double-clicked, it shows these steps and
   lists the profiles and the parts):

   ```bat
   .\profile.bat --family g1000 --from "C:\path\to\guids.mfproj"
   ```

   On Linux and macOS:

   ```sh
   python3 -m mobiflight --family g1000 --from /path/to/guids.mfproj
   ```

   Without `--from` it makes the profile of the download. `--vfr 1200` makes the VFR key squawk 1200 (US), or
   any other code of four digits from 0 to 7. `--list` lists the profiles and the parts. With Python
   installed on Windows, `py -m mobiflight` in the repository's folder does the same as `profile.bat`.
5. Open the new project in MobiFlight (File, Open).

The project's name ends in the commit of the zip or the download, as for the profiles to download. One made
in a git checkout has none (git log names the commit there), unless `--stamp TEXT` gives one.

Using it:

- MobiFlight runs one project at a time, and all the profiles in it (its tabs) run together. To use the panel
  beside other MobiFlight hardware, open that hardware's project, choose the + beside the tabs, From existing
  project, pick the panel's project you saved, bound to your joysticks, and save the result under a name of
  its own for that family (File, Save As). The added tab is a copy: to change the family or take a newer
  profile, first remove the old tab, "Avionics Panel" in every family (the dots on the tab, Remove), then add
  the new one. Never put two of this panel's profiles into one project: they map the same buttons.
- To have MobiFlight switch with the aircraft, save a project for each family you fly. Start a flight in an
  aircraft and open its project, then click the aircraft's name at the bottom of MobiFlight's window ("No
  aircraft detected" before a flight) and choose Link current config; in the same menu, turn on Auto-load
  linked config once. The link is to the name the sim reports, which can differ between liveries and
  variants of one aircraft: link each one you fly. When the sim loads a linked aircraft, MobiFlight opens its
  project (asking first to save unsaved changes) and stops running: choose Run again, or turn on Auto beside
  Run to have it start by itself. The Aircraft list in a project's settings does not do this: it only limits
  the presets MobiFlight offers.
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
squawks 7000, the VFR code of EASA, and selects ALT; pressed again on 7000 it squawks the code from before,
once, as a GTX 327's VFR key does (the profile keeps it in `L:AvionicsPanel_Squawk`), and with none kept it
only selects ALT. A code entered with the squawk digits forgets the one kept; one set in the cockpit with the
mouse does not. For another VFR code,
1200 in the US, change the `0x7000` at the start of the code of the row "VFR: XPNDR_SET, ..." in MobiFlight,
or generate the profile with `--vfr 1200` (above). The XPDR mode push (SHIFT, FREQ push) switches the
simulator's transponder between standby and ALT. MobiFlight shows the commands as custom code.

Does nothing in every profile: the FREQ push (it only switches the FREQ knob between COM, NAV and ADF; it
sends nothing to the sim). Each family below lists what else does nothing, mostly the keys its avionics lack
([Compatibility](compatibility.md)), and the dimmers where the profile does not know the aircraft's (they
differ by aircraft).

### G1000 NXi

The Working Title G1000 NXi, as in the Cessna 172 Skyhawk G1000. The autopilot, knob and FMS rows follow
Working Title's source of the NXi. The NXi itself turns ALT's 100 ft steps into 1000 ft steps from the 11th
step of a quick turn (steps less than 0.3 s apart, one way). Differences from the real G1000:

- Unit 1 is the MFD with COM 1 / NAV 1, unit 2 the PFD with COM 2 / NAV 2: the FMS keys and knob work the MFD
  in unit 1 and the PFD in unit 2 (SHIFT, HOME), and while you edit on the PFD the FREQ knob tunes radio 2.
- RANGE, pan and PTR work the MFD's map. With SHIFT they work the PFD's inset map, while the PFD shows it.
- HOME opens the MFD's engine menu (its ENGINE softkey) and, pressed again, goes back (BACK). After the menu
  is left another way, or a new flight starts after an odd number of HOME presses, the next HOME press presses
  the MFD's 11th softkey instead (Charts on the map page), and the one after opens the engine menu again.
- On the MFD's map page, MAP (SHIFT, CLR) toggles Charts, the second softkey from the right, TERR (SHIFT,
  PROC) presses Checklist, the rightmost, and VNAV (SHIFT, FPL) Detail, the third from the right, which steps
  through the map's four declutter levels and back to the first. The NXi takes no long CLR press from outside,
  so MAP cannot return to the default map page.
- At the top level of the PFD's softkeys, MSG (SHIFT, D→) toggles the Alerts window (the rightmost softkey),
  NRST (SHIFT, MENU) the Nearest window (the second from the right; in PFD Opt it is Back) and ARM (SHIFT,
  ALT) the Tmr/Ref window, where the minimums are set (the third from the right).
- The BARO push (STD) sets standard pressure. With the altimeter within half a hPa of 29.92 inHg (1013 hPa),
  as in STD, it presses PFD Opt, then STD Baro on the PFD instead, which toggle STD and, leaving it, return to
  the setting before; STD Baro then returns the softkeys to their top level. That works from the top level of
  the PFD's softkeys only; from another of their menus, press STD Baro there.
- CDI steps through GPS, NAV 1 and NAV 2 as the CDI softkey does, and OBS switches the GPS's OBS mode, from
  both units. In SUSP, OBS switches to OBS mode instead of resuming the sequence as the softkey does.
- UP and DN step the VS, IAS or pitch reference, as NOSE UP and NOSE DN do, but not the altitude in ALT hold.
- LVL engages the autopilot in its wings-level and pitch-level modes, also in aircraft without a LVL key.

Does nothing in this profile: TEST, GPSS and ½ BANK (MSFS's GFC 700 has no such keys; it flies GPS steering
in NAV), the dimmers.

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
- The BARO push only sets STD; leave it with the BARO ring. Working Title's G3X is taken to keep STD as a mode
  of its own, as its G1000 NXi does, which a setting sent from outside would not leave.
- Where the G3X manages the transponder's ground mode by itself, it turns the ALT of the XPDR mode push into
  that mode on the ground.

Does nothing in this profile: TEST, ARM, GPSS, BC and ½ BANK (the GFC 500 has no such keys), HOME (the G3X
has none), FPL, ENT, MSG, VNAV, TERR, MAP, RANGE, the map's pan and PTR (on the touchscreen; the map zooms
with the inner FMS knob on the map page), PROC (the G3X loads no procedures), the dimmers.

### GNS 530/430

The Working Title GNS 530 as unit 1 and GNS 430 as unit 2 in the KAP 140 cockpit: the KAP 140 with a KR 87
ADF, a KT 76 transponder and a KMA 28 audio panel, as in the Cessna 172 Skyhawk Classic. The same profile
drives KX 155/165 radios without a GNS; the FMS keys, CDI, OBS and the RANGE turn then do nothing, and the
RANGE knob tilted up and down still sets the COM volume. With another autopilot the autopilot keys do nothing:
map them in the project by hand. Two GNS of the same type, two GNS 430 for example, are not covered: the
profile's events cannot tell the two apart. Differences from the real units:

- The ALT/HDG knob sets the KAP 140's altitude and the heading bug, and its push syncs the bug to the heading,
  as on the G1000. With SHIFT it sets the course of NAV 1 and the altimeter, not the KAP 140's own BARO.
- The BARO push (STD) sets standard pressure and, pressed again on STD (29.92 inHg or 1013.25 hPa), the
  setting from before, once (the profile keeps it in `L:AvionicsPanel_Baro`). A turn of the BARO ring forgets
  it, so at a QNH of 1013 hPa the push sets STD.
- CRS CTR (SHIFT, HDG) sets the course of NAV 1 to its VOR or localizer; the KAP 140 cockpit's CDI has no
  such push.
- RANGE is the GNS 530's RNG key, and SHIFT, RANGE the GNS 430's, in both units. Tilted up and down, the RANGE
  knob sets the volume of COM 1 (the GNS 530's volume knob), and with SHIFT that of COM 2.
- The XPDR mode push turns the KT 76's mode knob: to ALT from OFF or SBY, to SBY from any other position.
- VNV, with or without SHIFT, works out and sets the vertical speed that reaches the selected altitude at the
  active waypoint ([VNV without VNAV](#vnv-without-vnav)).

Does nothing in this profile: TEST, FD, YD, VS, FLC, LVL, GPSS and ½ BANK (the KAP 140 has none of these
keys; it engages in VS, and UP and DN set the rate), ARM (the sim's KAP 140 does nothing on it), HOME (the GNS
has none), NRST and TERR (the GNS has pages for them, not keys), the RANGE knob tilted left or right and PTR
(the GNS has no joystick), VNAV in unit 2 (the GNS 430 has none), the dimmers.

### TDS GTN 750Xi and 650Xi

The KAP 140 cockpit of the [GNS profile](#gns-530430) with TDS's GTN 750Xi as unit 1 and GTN 650Xi as unit 2,
which TDS numbers as its GTN 750Xi unit 1 and GTN 650Xi unit 2. For an aircraft that loads them otherwise, as
a GTN 650Xi unit 1 beside the GTN 750Xi, join [avionics parts](#avionics-parts) with the GTN of TDS's unit it
has; the [Black Square Bonanza profile](#black-square-bonanza) covers the Bonanza's. TDS takes only the bezel
from outside, so the profile sends HOME, D→, the FMS knob and its push; held, the push flips the frequencies.
The RANGE knob works the GTN 750Xi, and with SHIFT the GTN 650Xi. Turned, it turns the GTN's inner knob the
other way round, as Garmin's touchscreen units zoom in clockwise (assumed for the GTN): so clockwise zooms the
map out on the map page, as on the GNS and the G1000; on other pages it works as the FMS knob's inner ring
does there, the other way round. Tilted up and down, it turns the GTN's volume knob; pushed, it is the volume
knob's push, squelch. The panel sends the RANGE push as a tap, so holding it does not tune 121.5: SHIFT, COM ⇆
(121.5) does.

COM ⇆ and NAV ⇆ are the sim's flip-flops, as the GTN has no such keys. TDS says the GTNs control the sim's COM
and NAV radios; if a frequency set with the FREQ knob does not show on the GTN, tune it there with the FMS
knob, whose push toggles between COM and NAV. The XPDR mode push works the cockpit's KT 76 through the
simulator's variable; a transponder that the GTN runs itself may not follow it. VNV and SHIFT, VNV are the
descent calculator, as in the GNS profile, with TDS's distance to the next waypoint.

Does nothing in this profile: TEST, FD, YD, VS, FLC, LVL, GPSS, ½ BANK and ARM (as in the GNS profile),
FPL, PROC, MENU, CLR, ENT, MSG, NRST, TERR, VNAV, MAP, CDI, OBS, the RANGE knob tilted left or right (on the
touchscreen), the dimmers.

### Black Square Bonanza

Black Square's Bonanza with the Bendix/King KFC 150 and the KAS 297B altitude selector, by the inputs Black
Square's guide lists for home cockpits, for every avionics selection on the options page of its tablet. Unit 1
is the primary selection (KX 155B, KLN 90B, GNS 530 or GTN 750) with COM 1 / NAV 1, unit 2 the secondary (KX
155B, GNS 430 or GTN 650) with COM 2 / NAV 2, and either GTN is PMS50's or TDS's. A control sends the inputs
of every navigator its unit may hold at once (the GNS's as in the GNS profile, TDS's GTN by TDS's own key
events as in the GTN profile, the GTN 650 as either of TDS's units); each takes only its own, so the profile
works with whatever the tablet selected, without a change. With a GTN, of the FMS keys only HOME, D→, the FMS
knob and its push work, the rest is on its touchscreen; with a GNS, HOME does nothing. Differences from the
real units:

- The ALT/HDG knob sets the KAS 297B's altitude (or its rate while its knob is pulled in the cockpit) and the
  heading bug, and its push syncs the bug to the heading. With SHIFT it sets the course of NAV 1 and the
  altimeter, and its push toggles STD as in the [GNS profile](#gns-530430).
- VFR presses the GTX 327's ALT key as it squawks the VFR code.
- VS and ALT ARM (SHIFT, ALT) are the KAS 297B's VS ENG and ALT ARM keys. TEST starts the KFC 150's self-test
  and holds the MD41's lamp test as long as it is held.
- VNV works out and sets the vertical speed that reaches the selected altitude at the active waypoint, then
  presses VS ENG when the autopilot is engaged, VS is off and no glideslope is captured ([VNV without
  VNAV](#vnv-without-vnav)). SHIFT, VNV is the KR 87's BFO key (below).
- UP and DN step the altitude held in ALT, the rate in VS and the pitch in pitch mode, as the KFC 150's rocker
  does. Black Square lists no event for the rocker or for FD, so they send the simulator's, which the aircraft
  may ignore.
- SHIFT, UP and SHIFT, DN are the EDM 800 engine monitor's left (STEP) and right (LEAN FIND) buttons: a tap is
  a short press, a key held longer than 0.35 s a long one. Black Square's guide does not say which button is
  which; STEP on the left is the real unit's. Both buttons pressed together and the mode switch stay in the
  cockpit.
- CDI switches the GNS 530 or the HSI between GPS and VLOC, as the MD41's VLOC/GPS key does beside the KLN
  90B; in unit 2 it is the GNS 430's CDI key. GPSS (SHIFT, NAV) is the HSI's source switch below it, NAV 1 or
  RNAV.
- The RANGE knob works the primary navigator, and with SHIFT the secondary. Turned, it sets the map's range:
  the GNS's RNG key, and the GTN's inner knob, which zooms its map on the map page; clockwise zooms out, the
  GTN's knob turned the other way as in the [GTN profile](#tds-gtn-750xi-and-650xi). On a GTN's other pages
  the turn works its inner knob there, as the FMS knob's inner ring does, the other way round. Tilted up and
  down, it sets the COM volume, of the radio (the GNS's and the KX 155B's volume knob) and of the GTN's volume
  knob; that a GTN's volume does not step twice for it is assumed. Pushed, it is the volume push of TDS's
  GTN, squelch; PMS50's GTN takes none from outside. With the KLN 90B as primary, RANGE works the KLN's left
  side: turned, its left inner knob; tilted left and right, its left outer knob; pushed, its left CRSR.
- The KLN 90B takes D→, CLR, ENT and MSG, MENU as its ALT key, the FMS knob as its right knob and the FMS push
  as its right CRSR; its power, brightness and scan stay in the cockpit. On the MD41 beside it, NRST (SHIFT,
  MENU) presses APR ARM and TERR (SHIFT, PROC) OBS, the simulator's OBS toggle, which with a GNS as primary
  toggles its OBS mode too.
- LVL turns the KDI 572R DME's selector one position on, and from the last to the first.
- ADF ⇆ is the KR 87's FRQ key. SHIFT, FLC presses its ADF (antenna) key and SHIFT, VNV its BFO key; its timer
  stays in the cockpit.
- The RDR 1150XL weather radar: SHIFT with the RANGE knob tilted left and right steps its range down and up,
  and FLC and ½ BANK (SHIFT, LVL) tilt its antenna down and up in steps of 5 % of its travel (a higher value
  up, assumed). Its mode, gain, brightness and other keys stay in the cockpit.
- YD sends the simulator's yaw damper event, for the aircraft that have one.
- MIC 1 and MIC 2 also set the pilot's transmit selector.
- The XPDR mode push presses the GTX 327's ALT key from OFF or SBY, its STBY key from any other mode.
- The lighting is as a project the Bonanza is flown with sets it. The outer ring steps the instrument lights'
  dimmer, and the engine instruments' and the subpanel's alike, in steps of 5 %, with the master panel
  lighting switch on above 0 and off at 0. The inner ring steps the glareshield flood lights, with their
  switch and the pilot's yoke map light. The lights need both their switch and their dimmer. The cabin light
  push turns the six reading lights and the copilot's yoke map light on or off, as the pilot's reading light
  goes.

Does nothing in this profile: NRST in unit 2 and TERR in unit 2 (neither the GNS nor the GTN has such keys),
VNAV in unit 2 (the GNS 430 and the GTN have none).

### COWS DA40

The COWS DA40 (XLS and NG) with Working Title's G1000 NXi and its autopilot: the [G1000 NXi
profile](#g1000-nxi) under the DA40's name, so a project of its own can be linked to the aircraft, with the
same differences from the real units, and the DA40's lighting as a project it is flown with sets it: the
dimmers are the panel lights (outer ring) and the glareshield lights (inner ring), in steps of 5 %, and the
cabin light push turns the three cabin lights on or off.

Does nothing in this profile: TEST, GPSS and ½ BANK (as in the G1000 NXi profile).

### Carenado C182T

Carenado's CT182T Skylane with the G1000 and the KAP 140. Both are taken to be the sim's own: its product
pages name the "default MSFS G1000" and the "default KAP140" autopilot, and in MSFS 2024 that G1000 is Working
Title's NXi, as users report; that its KAP 140 takes the sim's KAP 140 events is assumed. The profile has the
KAP 140's keys and altitude knob as in the [GNS profile](#gns-530430), the G1000's cockpit and navigator as in
the [G1000 NXi profile](#g1000-nxi), with the same differences from the real units. The ALT/HDG knob with
SHIFT sets the PFD's CRS and BARO knobs, and the heading bug is the sim's. The C182T dims all its panel lights
with one knob: the outer ring steps its four dimmers alike (two potentiometers, the panel and the pedestal),
in steps of 5 %, and the cabin light push turns its two cabin lights fully on or off, as a project the C182T
is flown with sets them. VNV and SHIFT, VNV are the descent calculator, as in the GNS profile; VNV takes the
NXi's required vertical speed first ([VNV without VNAV](#vnv-without-vnav)).

Does nothing in this profile: TEST, FD, YD, VS, FLC, LVL, GPSS, ½ BANK and ARM (as in the GNS profile), the
flood dimmer (the C182T has one dimmer for all its panel lights).

### VNV without VNAV

The KAP 140 and the KFC 150 with the KAS 297B have no VNAV, and a GNS or GTN drives none through them. In the
GNS, GTN, Black Square Bonanza and Carenado C182T profiles and the `kap140` and `kfc150` autopilot parts, VNV
is a descent calculator instead: one press works out a vertical speed down and sets it. It is a calculator,
not path tracking: the rate stays as it was set until you press VNV again, change it with UP and DN, or the
autopilot captures the altitude. It sets no climb: neither autopilot minds the airspeed in VS, so a climb is
for you to set, with an eye on the airspeed and the power.

1. Set the altitude to reach with the ALT/HDG knob, as usual, and make the fix where you want to reach it the
   navigator's active waypoint: D→ to it, or fly the flight plan's leg to it.
2. Press VNV. It works out the rate that reaches the selected altitude at that waypoint: the altitude to lose
   over the time to the waypoint at the present ground speed. It rounds the rate to 100 ft/min and keeps it
   between 300 and 1500 ft/min down. In the KAP 140 it leaves ALT hold for VS as the ALT key does and then
   sets the rate; in the KAS 297B it sets the rate and then presses VS ENG, when the autopilot is engaged, not
   in VS and not on a glideslope. With the autopilot off, VNV only sets the rate; an autopilot may take the
   present vertical speed when it engages, so press VNV again after engaging it.
3. Press VNV again now and then, after a turn or a change of speed or wind: it works the rate out anew from
   where you are.

VNV does nothing without a distance or at 30 knots or less (in the C182T, unless the NXi gives a required
vertical speed, below), or unless the selected altitude is more than 100 ft below. VNV has no amber legend, so
SHIFT, VNV does the same and a stray SHIFT changes nothing; in the Bonanza, SHIFT, VNV stays the KR 87's BFO
key.

The distance is the first one above 0 of the navigators' own, unit 1's first: a TDS GTN's is TDS's GTNXi's
distance to the next waypoint (`L:TDSGTNXI_NextWaypointDistanceNM`, from TDS's manual); a GNS's, PMS50's GTN's
and the G1000 NXi's is the sim's GPS distance to the active waypoint (`GPS WP DISTANCE`), which Working
Title's GNS and NXi write from their own flight plans; then the GPS distance, if neither unit gave it. So the
GNS and C182T profiles read the GPS distance alone, and a TDS variable that another aircraft of the session
left behind does not count there. The Bonanza, whose tablet chooses the navigators, reads first the KNS 81's
RNAV distance, while the HSI's source switch is on RNAV, then TDS's, then the GPS distance; the `kap140` and
`kfc150` parts alone, which cannot know the navigator, read TDS's, then the GPS distance. The ground speed is
the aircraft's (`GROUND VELOCITY`), the altitude the altimeter's. With the G1000 NXi (the C182T, or the
`kap140` part joined with the `g1000` navigator), VNV first takes the NXi's required vertical speed (`VSR` on
its PFD, `L:WTAP_VNAV_Required_VS`), when it is a descent of 300 ft/min or more; without one, or with a
smaller one, as for a constraint far ahead, VNV works the rate out itself. The NXi works the VSR out to the
next altitude constraint of its flight plan, which may lie above the selected altitude: VNV holds that rate
past the constraint's fix too, so press VNV again there.

None of this has been flown in the sim yet. To check there:

- That the selected altitude is the sim's first autopilot altitude (`AUTOPILOT ALTITUDE LOCK VAR:1`) in the
  KAP 140 and the KAS 297B, also in ALT hold, where the sim's KAP 140 holds its altitude in the second. If VNV
  does nothing in ALT hold after you set a lower altitude, it is not.
- In the Bonanza, which altitude the KFC 150's rocker steps in ALT hold, which settles the check above for the
  KAS 297B. UP and DN send `AP_ALT_VAR_INC` and `_DEC` without a slot, taken to step the first one, the one
  VNV reads as the KAS 297B's selected altitude: both cannot be right unless the KAS 297B's selection is the
  altitude held. In ALT hold, set an altitude 1000 ft below on the KAS 297B and press UP once. If the aircraft
  climbs 100 ft and the KAS 297B still shows the altitude you set, the first slot is the altitude held: UP and
  DN are right, and VNV must read the selection from elsewhere. If the KAS 297B's altitude steps up 100 ft and
  the aircraft stays level, the first slot is the selection: VNV is right, and UP and DN must step the slot of
  the altitude held. If neither moves, the KFC 150 takes the rocker from no key event.
- That the KAP 140 enters VS on `AP_PANEL_VS_ON`, as its ALT key makes it do, and holds the rate set right
  after it (`AP_VS_VAR_SET_ENGLISH`). Its display shows VS and the rate for 3 s as it enters VS; a rate set
  while it already flies VS is not shown.
- That the KAP 140 captures the selected altitude after VS (ARM on its display). Its ARM key does nothing in
  the sim, so if it does not, press ALT at the altitude; else the aircraft goes on through it.
- That the KAS 297B takes the rate (Black Square's guide says the native VS events keep working) and shows it
  for 2 s, and that it arms the altitude capture. If ARM is not lit, press ALT ARM (SHIFT, ALT); else the
  aircraft goes on through the selected altitude.
- That the KAS 297B keeps its VS mode in the sim's `AUTOPILOT VERTICAL HOLD`: VNV presses VS ENG only while
  that is off, so if the KAS 297B keeps VS to itself, a second press of VNV in a VS descent turns VS off.
- That the first press in ALT hold keeps its rate. If the autopilot still takes the present rate as it enters
  VS, press VNV again.
- Which of two GTNs TDS's distance is for. With a TDS GTN that has no active waypoint, a flight plan in the
  sim's own GPS may give the GPS distance. TDS's variable may also keep its last value after a flight with a
  TDS GTN: in the Bonanza with its tablet set to a GNS, the KLN 90B or PMS50's GTN, and with the parts alone,
  it would then come ahead of the GPS distance. The profile cannot see the tablet's choice, and reads TDS's
  first, as a TDS GTN may fly a leg that the sim's own flight plan, which gives the GPS distance, does not.
- That the KLN 90B writes the GPS distance: Black Square's guide names no distance variable for it. The same
  for PMS50's GTN, whose own flight plan may leave the sim's GPS behind.
- In the Bonanza, that the KNS 81's RNAV distance (`L:var_RNAV_DME`) drops to 0 when it loses the station, as
  VNV takes it while the HSI is on RNAV.
- In the C182T, that the NXi writes its VSR with the KAP 140 fitted, and below 0 for a descent, as Working
  Title's source works it out (VNV takes it only then, else it works the rate out itself). That source runs
  the NXi's VNAV with its own autopilot, which it keeps running beside the KAP 140.

## Avionics parts

For avionics the profiles above do not join, the panel's buttons come in parts. Each part covers buttons of its
own, so one of each kind makes a whole profile:

- An autopilot (the autopilot keys, UP and DN, the ALT/HDG knob's altitude and heading): `gfc700` (the G1000
  NXi's), `gfc500` (the G3X Touch's), `kap140`, or `kfc150` (Black Square's KFC 150 and KAS 297B). In
  `kap140` and `kfc150`, VNV is the descent calculator, with or without SHIFT ([VNV without
  VNAV](#vnv-without-vnav)).
- A cockpit (the ALT/HDG knob with SHIFT, the audio panel, transponder and lighting, the radios and ADF of both
  units): `g1000` (the PFD's CRS and BARO knobs), `g3x`, or `bendix-king` (the course of NAV 1 and the
  altimeter).
- Navigators: `g1000` or `g3x` for both units, or one for each unit: `gns530`, `gns430`, TDS's GTN as TDS
  numbers it in the aircraft (`gtn750-tds1`, `gtn750-tds2`, `gtn650-tds1`, `gtn650-tds2`), pms50's GTN
  (`gtn750-pms50`, `gtn650-pms50`, by the events Black Square's guide lists for it), or `none` for radios
  alone. A navigator of one unit takes that unit's keys and FMS knob and its map on the RANGE knob, without
  SHIFT in unit 1 and with SHIFT in unit 2: turned, the map's range; tilted up and down, the COM volume;
  pushed, a TDS GTN's squelch, as in the [GTN profile](#tds-gtn-750xi-and-650xi).

Two ways to join them:

- Generate one project as in the steps above (with `--from` bound to your joysticks, without it bound as a
  download is, in steps 2 to 5 of the first list), with the parts instead of `--family`. It writes
  `avionics-panel.mfproj`:

  ```bat
  .\profile.bat --autopilot kap140 --cockpit g1000 --navigator g1000 --from "C:\path\to\guids.mfproj"
  .\profile.bat --autopilot kap140 --cockpit bendix-king --unit1 gtn750-tds1 --unit2 gns430
  ```

  On Linux and macOS, `python3 -m mobiflight` instead of `.\profile.bat`.

- Or download [avionics-panel-parts.zip][parts] and unpack it: it holds a project of every part, to add to one
  MobiFlight project as its tabs. Start a new project and, for each part, choose the + beside the tabs, From
  existing project, and its file: `avionics-panel-autopilot-kap140.mfproj` and the like, one
  `avionics-panel-cockpit-*.mfproj`, and `avionics-panel-navigator-g1000.mfproj` (or `-g3x`) or one
  `avionics-panel-navigator-*-unit1.mfproj` and one `*-unit2.mfproj`. Each tab is named after its part, as
  "Avionics Panel: KAP 140 autopilot" or "Avionics Panel: GNS 430 in unit 2"; for a unit without a navigator,
  add no navigator tab. Save the project (File, Save As) before you bind the joysticks, then bind them once
  for all of the tabs and check them (steps 3 and 4 above): if they are the wrong way round, open the saved
  project again without saving and bind them the other way. Never add two parts of one kind, except one
  navigator for unit 1 and one for unit 2: they map the same buttons.

## Quick-reference cards

[avionics-panel-cards.zip][cards] holds a card for each profile above, `avionics-panel-g1000-card.html` and
the like: one page with what every key, ring, push and tilt sets in that profile, plain, with SHIFT (amber)
and in unit 2. A control that does nothing in the profile says "nothing" with a number, and the foot of the
card gives the reason. What a control sets is named as MobiFlight lists it, by the events and variables of its
code, so the card also tells which row of the project to open. Unpack the zip, open a card in a browser and
print it on A4 in landscape; on Letter, scale it to fit the page. The cards are of the profiles to download,
not of [avionics parts](#avionics-parts) or a profile changed in MobiFlight.

The cards of main are also on the web, to open and print without the zip: [G1000 NXi][card-g1000], [GFC 500
and G3X Touch][card-g3x], [GNS 530/430][card-gns], [GTN 750Xi/650Xi][card-gtn], [Black Square
Bonanza][card-black-square-bonanza], [COWS DA40][card-cows-da40] and [Carenado C182T][card-carenado-c182t].

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
- Every knob detent is a short press, and so is every step of a held UP or DN (without SHIFT), every pan step
  of a RANGE tilt and the RANGE push (PTR): map them "on press".
- Shifted functions are buttons of their own. The keys without an amber legend (VS, UP, FLC, DN, VNV, ENT) and
  the RANGE knob (turn, tilt, push) still send a shifted button of their own: these are free for your own
  mappings. Map the keys you do not use to the same function as the plain control, so a stray SHIFT before DN
  or ENT does no harm; held, SHIFT, DN then steps once, as it does not repeat. The generated profiles use
  SHIFT with the RANGE knob for the second unit's map, where the profile has one; the Bonanza profile uses
  SHIFT, UP and SHIFT, DN for its engine monitor, SHIFT, FLC and SHIFT, VNV for its ADF's keys and SHIFT with
  the RANGE knob tilted left and right for its weather radar's range.
- The cockpit lighting (SHIFT, FMS knob) stays on device 1 whatever unit is selected.
- The button numbers stay fixed: new buttons only go at the end of a device, and retired ones keep their slot,
  so mappings survive firmware updates.

### Button names in MobiFlight

MobiFlight shows the panel's buttons as "Button 1" to "Button 128" on device 1 and "Button 1" to "Button 64"
on device 2. [avionics-panel.joystick.json][joystick], a joystick definition for MobiFlight 11.2 or newer,
names the 117 that device 1 sends as [BUTTONS.md](../../firmware/BUTTONS.md) does, after their number (118 to
128 stay "Button 118" and so on). MobiFlight finds a definition by the joystick's name, and both devices are
"Avionics Panel", so one definition names the buttons of both: buttons 1 to 39 carry device 1's name and then
device 2's, as "Button 10: DN | unit 2: ENT"; the others say "device 1 only", as "Button 50: BARO_STD | device
1 only", since device 2 lists its buttons 40 to 64 but never sends them. The definition could also match by
the USB vendor and product ID, but the two devices share them, and so does every Pico running CircuitPython,
so it does not. It changes only the names MobiFlight shows: projects, their rows and the bindings stay as they
are. It follows MobiFlight's source and has not yet been tried in MobiFlight. To install it:

1. Close MobiFlight.
2. Open MobiFlight's `Joysticks` folder: for MobiFlight installed by its setup, enter
   `%LOCALAPPDATA%\MobiFlight\MobiFlight Connector\Joysticks` in the address bar of File Explorer. Make a folder
   `avionics-panel` in it and put the file there. A definition in `Joysticks` itself works too, but MobiFlight
   moves it into a folder `_MIGRATED_` when it starts.
3. Start MobiFlight. The names show where the panel's joysticks are named "Avionics Panel"
   ([Device name](#device-name)).

To remove it, delete the folder and restart MobiFlight.

## Per avionics

- FREQ knob: its push cycles COM, NAV and ADF, and each mode sends turn buttons of its own. The mode stays
  until the next push, or a push held 1 s, which returns it to COM; the green light shows the mode and counts
  it after each push ([Controls](controls.md#knobs)). Map each
  mode to its radio (COM and NAV 1 or 2 by unit, and the one ADF), as the
  [generated profiles](#generated-profiles) do; a GNS shows the frequencies whichever field its cursor is on;
  for a GTN see [TDS GTN 750Xi and 650Xi](#tds-gtn-750xi-and-650xi).
- G1000: map the FMS keys and knob of device 1 to the MFD and of device 2 to the PFD, as the generated profile
  does ([why](controls.md#keys-label-shift-legend-in-parentheses)).
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
   (ALT/HDG is on device 1): the bug must move by 4°. No more than 4 each: the firmware drops a detent
   that finds 8 presses waiting, all rings and keys together.

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
a few idle seconds: the lights go dark, SHIFT ends, and the next input reaches the PC about 2 s late (a SHIFT
tap as that input is lost; [why](../architecture/firmware.md#usb)). Set its `power/control` to `on`.

[g1000]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-g1000.mfproj
[g3x]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-g3x.mfproj
[gns]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-gns.mfproj
[gtn]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-gtn.mfproj
[bonanza]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-black-square-bonanza.mfproj
[da40]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-cows-da40.mfproj
[c182t]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-carenado-c182t.mfproj
[parts]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-parts.zip
[cards]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-cards.zip
[joystick]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel.joystick.json
[rolling]: https://github.com/saschagrunert/avionics-panel/releases/tag/rolling
[sim-zip]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-sim-windows.zip
[card-g1000]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-g1000-card.html
[card-g3x]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-g3x-card.html
[card-gns]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-gns-card.html
[card-gtn]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-gtn-card.html
[card-black-square-bonanza]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-black-square-bonanza-card.html
[card-cows-da40]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-cows-da40-card.html
[card-carenado-c182t]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-carenado-c182t-card.html
