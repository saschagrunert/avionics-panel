# Octavi IFR-1

The [ready profiles](mapping.md#generated-profiles) also come for the Octavi IFR-1, a desktop knob and key
box with eight modes, in place of the panel. Each IFR-1 profile sends what the panel's profile of the same
name sends, so a fix to a panel profile reaches its IFR-1 profile too. They are for MSFS 2024 with MobiFlight
11.3 or newer on Windows. They are not yet tried on the device; the Black Square Bonanza, COWS DA40 and
Carenado C182T will be tried first ([To check on the device](#to-check-on-the-device)).

## Downloads

From the release [Latest build][rolling], one project per profile, each with a card (the events every control
sends) and a cheat sheet on the web. The cheat sheet draws the IFR-1 with a box of plain words for each
control round it and a line from each box to its control: a mode key's box says what the rings, the knob push
and ⇆ do in that mode and in its shifted mode, and the boxes of the keys on the right and below say what each
does in FMS1, FMS2 and the other modes.

| Profile | Project | Card | Cheat sheet |
| --- | --- | --- | --- |
| Black Square Bonanza | [avionics-panel-ifr1-black-square-bonanza.mfproj][p-bonanza] | [Bonanza][c-bonanza] | [Bonanza][s-bonanza] |
| Carenado C182T | [avionics-panel-ifr1-carenado-c182t.mfproj][p-c182t] | [C182T][c-c182t] | [C182T][s-c182t] |
| COWS DA40 | [avionics-panel-ifr1-cows-da40.mfproj][p-da40] | [DA40][c-da40] | [DA40][s-da40] |
| G1000 NXi | [avionics-panel-ifr1-g1000.mfproj][p-g1000] | [G1000 NXi][c-g1000] | [G1000 NXi][s-g1000] |
| GFC 500 and G3X Touch | [avionics-panel-ifr1-g3x.mfproj][p-g3x] | [G3X][c-g3x] | [G3X][s-g3x] |
| GNS 530/430 | [avionics-panel-ifr1-gns.mfproj][p-gns] | [GNS][c-gns] | [GNS][s-gns] |
| TDS GTN 750Xi/650Xi | [avionics-panel-ifr1-gtn.mfproj][p-gtn] | [GTN][c-gtn] | [GTN][s-gtn] |

Every profile's cards and cheat sheets, the panel's and the IFR-1's, are also listed on [one page][index] beside
the 3D view, and are in [avionics-panel-cards.zip][cards] with the commit of the download in their titles. Open
one in a browser and print it on A4 in landscape (on Letter, scaled to fit the page).

## Setting up

1. Install MobiFlight 11.3 or newer (the profiles are made for 11.3.1). Every command goes through
   MobiFlight's WASM module in the sim's Community folder: when MobiFlight offers it, choose Install Now with
   the sim closed.
2. Quit Octavi's own plugin and keep it from starting with the sim. Only one program can open the IFR-1 at a
   time: with the plugin or Octavi's configuration tool running, MobiFlight sees no input.
3. Plug in the IFR-1 and open the downloaded profile in MobiFlight (File, Open). MobiFlight binds it to the
   connected IFR-1 by itself, by the name the IFR-1 gives itself. Octavi's registry fix for the IFR-1's GUID
   is not needed; the profile carries the GUID that fix sets, so with it applied the two should match without
   binding. Two IFR-1s on one PC are not supported.
4. Start a flight with the avionics on and choose Run. In COM1, turn the inner ring one detent: COM 1's
   standby frequency must step by one channel.
5. Save the project (File, Save).

If the frequency does not step:

- Octavi's plugin or configuration tool still runs (step 2): MobiFlight then shows no input from the IFR-1.
- MobiFlight's WASM module is missing from the Community folder: install it from MobiFlight with the sim
  closed (step 1).
- The IFR-1 was not plugged in when the project opened: plug it in and open the project again.
- MobiFlight shows the IFR-1 as missing: bind it in Extras, Controller Bindings. MobiFlight takes an IFR-1 that
  names itself "Octavi" as well as "IFR1", but binds a project by the name and GUID it carries.

The AP keys' lights are meant to show the autopilot's modes in every mode of the IFR-1, from the sim's
autopilot flags ([To check on the device](#to-check-on-the-device)). The flash of the mode key in shift is
MobiFlight's own and needs the IFR-1's firmware 1.2 or newer, which Octavi offers as early access only.

MobiFlight runs one project at a time, and a project holds several profiles, each on a tab of its own: to fly
the panel and the IFR-1 together, add the IFR-1's profile to the panel's project as a tab, with the + beside
the tabs, From existing project ([Generated profiles](mapping.md#generated-profiles)).

For another VFR code than 7000, as 1200 in the US, write the profile with that code: on Windows,
`.\profile.bat --ifr1 cows-da40 --vfr 1200` in a terminal (cmd or PowerShell) in the folder of the
[simulator's zip](simulator.md) writes `avionics-panel-ifr1-cows-da40.mfproj`, as `python3 -m mobiflight
--ifr1 cows-da40 --vfr 1200` does from the repository ([Generators](../architecture/generators.md)). Or change
`7000` in the project's `XPDR^_TOG` item, where the code stands once (without leading zeros: 0400 is `400`),
as for the panel ([Generated profiles](mapping.md#generated-profiles)).

## What each control does

| Mode | Outer / inner ring | ⇆ | Knob push, keys |
| --- | --- | --- | --- |
| COM1, COM2 | MHz / kHz of COM 1 / COM 2 | tap: flip-flop; let go after 0.7 s: COM 1 / COM 2 audio (listen; stays on while you talk on it); held 2 s: talk on COM 1 / COM 2, and listen | shift |
| HDG (COM1 shifted) | heading bug 10° / 1° | heading bug to the heading (in the Bonanza the HSI's course too) | shift back |
| BARO (COM2 shifted) | altimeter setting on both rings; in the Bonanza, of both altimeters | tap: STD; again: the setting before, where the panel does so (in the Bonanza both altimeters); hold: pitot heat | shift back |
| NAV1, NAV2 | MHz / kHz of NAV 1 / NAV 2 | tap: flip-flop; hold: NAV 1 / NAV 2 audio (ident) | shift |
| CRS1 (NAV1 shifted) | course 10° / 1°: in the G1000 NXi, DA40, C182T and G3X profiles the CDI's course, else NAV 1's | tap: the course to the VOR or LOC; hold: marker audio | shift back |
| CRS2 (NAV2 shifted) | NAV 2 course 10° / 1° | tap: NAV 2's course to the VOR or LOC; hold: DME audio | shift back |
| FMS1, FMS2 | the unit's FMS knob; ⇆ held: its map range, where the profile has one (the G3X has none), the outer ring on a GTN its volume | tap: the unit's HOME, where it has one | CRSR; D→, MENU, CLR, ENT and CDI, OBS, MSG, FPL, VNAV (in the G1000 NXi and DA40 profiles the GFC 700's VNV, in the Bonanza's FMS1 the descent calculator), PROC; held CLR, MENU, PROC: MAP, NRST, TERR; each where the profile has it (in the Bonanza's FMS1, CLR and ENT are the EDM 800's, held its long press) |
| AP | selected altitude 1000 ft / 100 ft; ⇆ held: the inner ring is the panel's UP and DN (the held altitude, VS, IAS or pitch, by autopilot), the outer ring five of them at once (500 ft/min in VS, 5 kt in FLC, five pitch steps in pitch hold, in ALT hold five altitude steps on the KAP 140 and KFC 150, in the Bonanza 500 ft of the altitude its UP and DN step, [to check](mapping.md#vnv-without-vnav)). With the autopilot or the flight director in VS (on the KAP 140, which has none, the autopilot), the other way round: the rings set the rate without ⇆ (inner 100 ft/min, outer 500 ft/min) and the altitude to level off at with ⇆ held, in a climb too | none: it only modifies the rings | held: VNV |
| XPDR | the squawk, a digit at a time, as on the panel: the outer ring selects the digit (1 to 4, stopping at both ends; every entry starts at digit 1), the inner ring steps it 0 … 7; ⇆ held: panel dimmer / flood dimmer (the C182T's cabin lights), where the profile knows the aircraft's | tap: IDENT | shift: MODE |
| MODE (XPDR shifted) | either ring: clockwise ALT (from standby or off), counter-clockwise standby | tap: VFR and back; hold: cabin light | shift back |
| Every mode but FMS1 and FMS2 | | | AP, HDG, NAV (in the Bonanza held: GPSS), APR (held: BC), ALT (held: ARM), VS (held: FLC on the GFC 700 and GFC 500, FD on the KFC 150), each where the profile has it |

- ⇆ in FMS1, FMS2, AP and XPDR: held while turning a ring, the ring does what follows "⇆ held" and ⇆ sends
  nothing when let go. Otherwise ⇆ sends its tap when let go, however long it was held. Press ⇆ first, then
  turn: a detent that comes with the press, in the same report of the IFR-1, reaches the profile before it
  (MobiFlight 11.3.1), so that detent does what it does without ⇆, and ⇆ let go at once then sends its tap,
  unless the ring turned again. For that reason ⇆ has no hold in these modes, and in AP no tap either: a hold
  or tap there, as LVL or FLC, would come with a turn meant for the ring.
- A key with a hold sends its hold at once when held 0.7 s, while still down, and its own function on a tap,
  when let go; let go after the hold, it sends nothing more, but for the KAP 140's VNV (the AP knob's push held
  in the C182T, GNS and GTN profiles), which sets its rate again then, as the panel's VNV does (not if
  the mode changed with it still down: press VNV again then, as MobiFlight's message on a change of mode has
  no room for it). The amber functions of the panel's keys are such holds: APR (BC), ALT (ARM), CLR (MAP),
  MENU (NRST) and PROC (TERR), each where the profile maps that function; the cheat sheet says what it is in
  the aircraft. ⇆ in NAV1, NAV2 and CRS2, held, is the panel's NAV 1, NAV 2 or DME audio; in CRS1 and BARO the
  simulator's event for the marker audio or pitot heat, which an aircraft may ignore; in MODE the cabin light.
  The AP knob's push is VNV, held only, as a push comes easily with a turn of the altitude rings. VS held is
  FLC on the GFC 700 and GFC 500 (the GFC 500's IAS mode) and FD on the KFC 150 (with the autopilot off only,
  as on the panel). AP sends at once, as disengaging the autopilot cannot wait for the release, and HDG, NAV
  and VS too where they have no hold.
- ⇆ in COM1 and COM2 has two holds in place of 121.5: let go after 0.7 s, it is the panel's COM 1 or COM 2
  audio, which turns listening to that radio on or off; held for 2 s, it is the panel's MIC 1 or MIC 2 at that
  moment, which picks the radio you talk on, and its release then sends nothing. So COM 2 can play the ATIS
  while you talk on COM 1. As on an audio panel, the radio you talk on stays heard, and picking it to talk on
  turns its audio on. A hold is twice the panel's 0.35 s, so a flip-flop pressed a little slow does not turn a
  radio's audio off unseen.
- FMS1 and FMS2 are the panel's units 1 and 2, but in the G1000 NXi, DA40 and C182T profiles FMS1 is the PFD
  and FMS2 the MFD, as the G1000 numbers them (the panel's unit 1 is the MFD): there ⇆ held with a ring zooms
  the PFD's inset map in FMS1, which shows only when the inset is on, and the MFD's map in FMS2. In the Black
  Square Bonanza, FMS1 is the primary selection of its tablet and FMS2 the secondary, every selection at once,
  as on the panel. With ⇆ held, the outer ring is the GNS's map range and the GTN's volume (TDS's and
  PMS50's), and in FMS1 also the KLN 90B's left outer knob; the inner ring is the map range, and in FMS1 also
  the KLN 90B's left inner knob. On a GTN (TDS's or PMS50's) that range is its inner knob, which sets the
  range on a map page and works the knob on any other page. In the G1000 NXi and DA40 profiles VNAV is the GFC
  700's VNV, as the IFR-1's legend reads, not the MFD's Detail softkey the panel's amber VNAV is there; the
  C182T's KAP 140 has no VNAV, and its VNAV stays the softkey. In the Bonanza FMS1's VNAV is the descent
  calculator ([VNV in the Bonanza](#vnv-in-the-bonanza)).
- On TDS's GTN, in the GTN profile, MENU, CLR and ENT of FMS1 and FMS2 set its volume up and down and push its
  volume knob (squelch with COM selected, ident with NAV), as TDS's GTN takes those keys only on its
  touchscreen; in the Bonanza none do, as the volume keys are seldom used: there the outer ring with ⇆ held
  sets each GTN's volume.
- The Black Square Bonanza has more on the IFR-1 than on the panel's keys alone. Its keys are laid out for
  TDS's GTN 750Xi and 650Xi, which take only their bezel (HOME, D→, the knobs) from outside; the other
  selections of its tablet (GNS 530/430, PMS50's GTN, KLN 90B) keep the keys that cost the GTNs nothing.
  PMS50's GTN takes MENU, CLR, ENT and MSG as the keys its screen shows and PROC as its Procedures page (these
  with PMS50's Premium version), as on the panel, but for FMS1's CLR and ENT. ⇆ in HDG sets the HSI's course
  (the yellow arrow) to the heading with the heading bug. BARO's rings and ⇆ set both altimeters, the
  right-hand one to the left-hand one's setting, as the panel's BARO does. NAV held switches the HSI between
  NAV 1 and RNAV (GPSS, which CRS1 needs on RNAV), as the panel's amber NAV. The cockpit's functions go on
  keys: in FMS1, CLR and ENT are the EDM 800's STEP and LEAN FIND, side by side as its left and right buttons:
  a tap is a short press, sent as the key is let go, held 0.7 s a long press (the GNS 530's and PMS50's CLR
  and ENT give way, and CLR's amber MAP), and VNAV is the descent calculator; in FMS2, VNAV steps the DME
  selector, and CLR and ENT are the GNS 430's (and PMS50's). Held in FMS2, MENU runs the KFC 150's self-test
  with the autopilot off, MSG opens or shuts the oxygen valve, FPL switches the tip tank transfer pumps (both
  off if either runs, else both on), OBS prop heat, CDI steps the fuel boost pump one position from where it
  is (off, low, high, off) and VNAV switches the air conditioner with its blower, as the guide's "Hardware
  Inputs & Outputs" and the project the Bonanza is flown with set them. The fuel selector stays in the
  cockpit.
- The COWS DA40 and the Carenado C182T have their electric fuel pump on CDI held in FMS2, and the DA40 NG
  its fuel transfer pump on FPL held in FMS2 (the XLS ignores it). The C182T's inner ring in XPDR with ⇆ held
  dims its two cabin lights, as on the panel.
- The KAP 140's VS key leaves ALT hold for VS, as the panel's does; it has no hold.
- The squawk goes a digit at a time, as on the panel: the outer ring selects the digit, clockwise to the next,
  stopping at 4, counter-clockwise back, stopping at 1, so a turn far counter-clockwise always finds digit 1;
  the inner ring steps that digit (the simulator's XPNDR_1000_INC and the like, as the panel's), the others
  kept. Every change of mode starts the entry at digit 1 again. To squawk 4512 from 7000: inner ring to 4,
  outer one detent, inner to 5, outer, inner to 1, outer, inner to 2. The knob push in XPDR shifts to MODE,
  whose rings take the transponder one way each however far they turn: clockwise from standby or off to ALT,
  counter-clockwise from ALT or on to standby; ⇆ there squawks the VFR code, and pressed again the code
  before. Push the knob again to come back to XPDR.
- The rings send one step per detent, without the panel's quick turn. MobiFlight passes on every detent of a
  fast spin; whether the sim keeps up is to check.
- MobiFlight sends a key's release to the mode the IFR-1 is in when the key comes up, and a hold to the button
  the key went down on. A change of mode, or leaving shift with the knob push, lets go of ⇆ and of every key
  with a hold, so one still held then sends nothing, neither held on nor let go; entering shift lets go of ⇆,
  so a hold of COM1 or COM2 sends nothing in HDG or BARO. A key of TDS's GTN held in FMS1 or FMS2 while
  changing mode stays down in the GTN until pressed again; its key-up never reaches the other GTN.

What the IFR-1 has no control for, of the panel's functions: in every profile 121.5 and the ADF, including its
ident audio, and the maps' pan and pointer; the COM volume in the GNS and Bonanza profiles; in the Bonanza,
the GTNs' volume push, the GNS 530's CLR, ENT, MAP (CLR held long) and VNAV and PMS50's GTN 750's CLR and ENT
(FMS1's CLR and ENT are the EDM 800's, its VNAV the descent calculator), the MD41's lamp test, the KLN
90B's left CRSR, the KR 87's keys, the weather radar and the KFC 150's YD; the GFC
700's and GFC 500's FD, YD and LVL; in the G1000 NXi and DA40 profiles the MFD's Detail softkey. The cheat
sheets mark every control that does nothing in a profile, with the reason.

## VNV in the Bonanza

The KFC 150 has no VNAV and the GTNs drive none through it, so VNV is a descent calculator ([VNV without
VNAV](mapping.md#vnv-without-vnav)): one press works out the vertical speed that reaches the KAS 297B's
selected altitude at the GTN's active waypoint, sets it and engages VS. It does not track a path: press it
again now and then on the way down.

1. Fly with the autopilot engaged, in ALT hold or any other mode (not on a glideslope).
2. In AP, turn the rings to the altitude to reach (outer 1000 ft, inner 100 ft), on the KAS 297B; already in
   VS, hold ⇆ while turning, as the rings set the rate there.
3. On the GTN 750 make the fix where you want to be at that altitude the active waypoint: D→ to it, or fly
   the flight plan's leg to it.
4. Press VNAV in FMS1 (the key under ALT), or hold the AP knob's push for 0.7 s in AP. The KAS 297B shows the
   rate for 2 s and the KFC 150 enters VS; the KAS 297B captures the altitude at the end.
5. In VS the AP rings now set the rate (inner 100 ft/min, outer 500 ft/min) and, with ⇆ held, the altitude.
   After a turn, a change of speed or wind, press VNAV again: it works the rate out anew.

VNV sets nothing when the selected altitude is not more than 100 ft below, without a distance from the GTN
(no active waypoint), at 30 kt or less over the ground, or for a climb. The rate is rounded to 100 ft/min and
kept between 300 and 1500 ft/min. If nothing happens, it is one of these, or VNV reads the selected
altitude from where the KAS 297B does not keep it ([To check on the device](#to-check-on-the-device)).

## To check on the device

- In COM1, a fast spin of 20 detents steps exactly 20 channels; so do HDG, CRS1 and CRS2's outer rings, the
  dimmers and the Bonanza's BARO rings, which read the sim's value and write a new one each detent. With
  firmware 1.2, the mode key flashes only while shifted.
- The squawk's inner ring steps only the digit selected: XPNDR_1_INC on 7007 gives 7000, not 7010, and the
  other digit events alike (the panel's digits send the same events). If a digit carries into the next, the
  IFR-1's and the panel's squawk digits both need XPNDR_SET of the whole code instead.
- The holds: 0.7 s feels right, neither a tap taken for a hold nor a hold that keeps one waiting; the hold goes
  out while the key is still down, and nothing when it comes up.
- The AP lights: the G1000 NXi lights HDG, NAV and APR in those modes (if it sets the sim's flags for them);
  the KAP 140's NAV and APR armed or captured; the KFC 150's modes on the sim's flags, or Black Square's own.
- The lights go out when the sim closes or MobiFlight stops.
- The AP outer ring with ⇆ held: five steps of UP or DN sent at once take five steps, on the Garmin autopilots
  and the KFC 150 (the sim's increment events) and on the KAP 140, whose KAP140.js handles each push: if it
  sets the rate from the sim's value plus 100, five pushes in one go read the same value and take one step.
- A bounce of the knob push (shift on and off at once, reported with MobiFlight) lets go of a ⇆ or key with a
  hold held meanwhile in COM1, COM2, NAV1, NAV2 or XPDR or their shifted modes: MobiFlight sends the same
  button for leaving shift as for a change of mode.
- ⇆ held in CRS1: the aircraft takes the simulator's marker audio event (Black Square's guide has it for the
  Bonanza); in BARO, the pitot heat event in the G1000 NXi, G3X, GNS and GTN profiles (the Bonanza, DA40 and
  C182T projects already send it).
- ⇆ pressed with a ring turned at once, in FMS1, FMS2, AP and XPDR: how often the IFR-1 reports the press and
  a detent together, which sends the detent without ⇆ and, with no further turn, ⇆'s tap when let go. In XPDR
  that detent changes the squawk unseen and ⇆ then IDENTs: if it happens, the dimmers leave XPDR's ⇆ layer.
- Fast spins: MobiFlight sends each detent of a report as its own command at once, so several may read the same
  value of the sim in one frame and step it once (the squawk, HDG and CRS's 10° steps, BARO, the dimmers); if
  the fast spin above loses detents, those rings step from a value of their own instead.
- COM1 and COM2: ⇆ let go after 0.7 s and before 2 s turns only that radio's audio on or off, and held for 2 s
  picks only the radio to talk on, while still held, with nothing more on its release.
- MODE: each ring takes the transponder to ALT clockwise and to standby counter-clockwise in every profile.
- KAP 140 (C182T, GNS, GTN): VNV held from ALT hold keeps the rate it set once let go, after the autopilot
  code entered VS a frame late (as the panel's, [VNV without
  VNAV](mapping.md#vnv-without-vnav)).
- KAP 140 (C182T, GNS, GTN): the VS key sends AP_PANEL_VS_ON past the KAP 140's own keys; its display shows VS
  and not ALT after it.
- Bonanza: VS held takes the KFC 150's FD (the simulator's TOGGLE_FLIGHT_DIRECTOR, which Black Square's guide
  does not list).
- Bonanza: the GTX 327 shows the code VFR sets with XPNDR_SET, in the sim's Bco16 (the
  code read as its digits, `(A:TRANSPONDER CODE:1, number)` 1200 for 1200; MobiFlight's wiki).
- Bonanza: VNV (FMS1's VNAV, or the AP knob's push held) from ALT hold with the altitude set 3000 ft lower on
  the KAS 297B and a GTN waypoint 10 nm ahead enters VS at a rate down. If nothing happens, the selected
  altitude is not in `AUTOPILOT ALTITUDE LOCK VAR:1` in ALT hold: in the sim's developer mode (Tools,
  Behaviors, LocalVariables) look for the KAS 297B's selected altitude among the L: variables (`kas297b`,
  `Preselect`).
- The AP rings in VS set the rate, on the sim's AUTOPILOT VERTICAL HOLD flag with the autopilot or the flight
  director on (the KFC 150, the GFC 700 and the GFC 500; the KAP 140, which has no flight director, with the
  autopilot on), also with VS entered straight from the VS key. If they still set the altitude, look at the AP
  VS light, which reads the same flag: dark in VS, the aircraft keeps VS to itself (in the Bonanza, the KAS
  297B's `L:var_VsAdjustMode` may tell it).
- Bonanza: with the two altimeters set apart, the right-hand one is the simulator's altimeter 2 and takes
  KOHLSMAN_SET's two parameters in the order the profile gives them (index, then the setting); either BARO
  ring sets both to the same setting; ⇆ tapped twice sets both to STD and back to the setting before, as the
  panel's BARO does. The rings step 0.01 inHg; with the sim in hPa, the setting moves 1 hPa about every third
  detent.
- Bonanza: CRS2 turns NAV 2's indicator; CRS1 with the HSI on RNAV (NAV held); ⇆ in HDG turns the HSI's course
  to the heading.
- Bonanza: CLR and ENT in FMS1 tapped press the EDM 800's STEP and LEAN FIND, held 0.7 s their long press; the
  outer ring with ⇆ held sets TDS's and PMS50's volume.
- Bonanza with PMS50's GTN 650: which prefix it takes, `GTN650_` (Black Square's guide) or `GTN650_2_`
  (PMS50's list for a GTN on COM 2); the profile sends both. MENU, CLR, ENT, MSG and PROC on PMS50's GTN.
- Bonanza: the oxygen valve from FMS2's MSG held.
- TDS's GTN takes the tap of ⇆ in FMS1 and FMS2, sent down and up at once, as HOME.
- Flying the panel and the IFR-1 together, both profiles in one MobiFlight project.

[rolling]: https://github.com/saschagrunert/avionics-panel/releases/tag/rolling
[cards]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-cards.zip
[index]: https://saschagrunert.de/avionics-panel/cards/
[p-bonanza]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-black-square-bonanza.mfproj
[p-da40]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-cows-da40.mfproj
[p-c182t]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-carenado-c182t.mfproj
[p-g1000]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-g1000.mfproj
[p-g3x]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-g3x.mfproj
[p-gns]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-gns.mfproj
[p-gtn]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-gtn.mfproj
[c-bonanza]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-black-square-bonanza-card.html "Black Square Bonanza IFR-1 card"
[c-da40]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-cows-da40-card.html "COWS DA40 IFR-1 card"
[c-c182t]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-carenado-c182t-card.html "Carenado C182T IFR-1 card"
[c-g1000]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g1000-card.html "G1000 NXi IFR-1 card"
[c-g3x]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g3x-card.html "GFC 500 and G3X Touch IFR-1 card"
[c-gns]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gns-card.html "GNS 530/430 IFR-1 card"
[c-gtn]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gtn-card.html "TDS GTN 750Xi/650Xi IFR-1 card"
[s-bonanza]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-black-square-bonanza-sheet.html "Black Square Bonanza IFR-1 cheat sheet"
[s-da40]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-cows-da40-sheet.html "COWS DA40 IFR-1 cheat sheet"
[s-c182t]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-carenado-c182t-sheet.html "Carenado C182T IFR-1 cheat sheet"
[s-g1000]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g1000-sheet.html "G1000 NXi IFR-1 cheat sheet"
[s-g3x]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g3x-sheet.html "GFC 500 and G3X Touch IFR-1 cheat sheet"
[s-gns]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gns-sheet.html "GNS 530/430 IFR-1 cheat sheet"
[s-gtn]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gtn-sheet.html "TDS GTN 750Xi/650Xi IFR-1 cheat sheet"
