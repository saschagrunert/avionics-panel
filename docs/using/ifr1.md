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
| Black Square Bonanza | [avionics-panel-ifr1-black-square-bonanza.mfproj][p-bonanza] | [open][c-bonanza] | [open][s-bonanza] |
| Carenado C182T | [avionics-panel-ifr1-carenado-c182t.mfproj][p-c182t] | [open][c-c182t] | [open][s-c182t] |
| COWS DA40 | [avionics-panel-ifr1-cows-da40.mfproj][p-da40] | [open][c-da40] | [open][s-da40] |
| G1000 NXi | [avionics-panel-ifr1-g1000.mfproj][p-g1000] | [open][c-g1000] | [open][s-g1000] |
| GFC 500 and G3X Touch | [avionics-panel-ifr1-g3x.mfproj][p-g3x] | [open][c-g3x] | [open][s-g3x] |
| GNS 530/430 | [avionics-panel-ifr1-gns.mfproj][p-gns] | [open][c-gns] | [open][s-gns] |
| TDS GTN 750Xi/650Xi | [avionics-panel-ifr1-gtn.mfproj][p-gtn] | [open][c-gtn] | [open][s-gtn] |

Every profile's cards and cheat sheets, the panel's and the IFR-1's, are also listed on [one page][index] beside
the 3D view, and are in [avionics-panel-cards.zip][cards] with the commit of the download in their titles. Open
one in a browser and print it on A4 in landscape.

## Setting up

1. Install MobiFlight 11.3 or newer: the IFR-1's ⇆ and keys need its long press and hold, which came with 11.3.
   Every command goes through MobiFlight's WASM module in the sim's Community folder: when MobiFlight offers
   it, choose Install Now with the sim closed.
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

With MobiFlight older than 11.3 the frequency steps, but the holds do nothing.

The AP keys' lights are meant to show the autopilot's modes in every mode of the IFR-1, from the sim's
autopilot flags ([To check on the device](#to-check-on-the-device)). The flash of the mode key in shift is
MobiFlight's own and needs the IFR-1's firmware 1.2 or newer, which Octavi offers as early access only.

MobiFlight runs one project at a time, and a project holds several profiles, each on a tab of its own: to fly
the panel and the IFR-1 together, add the IFR-1's profile to the panel's project as a tab, with the + beside
the tabs, From existing project ([Generated profiles](mapping.md#generated-profiles)).

For another VFR code than 7000, as 1200 in the US, write the profile with that code: on Windows,
`profile.bat --ifr1 cows-da40 --vfr 1200` from the [simulator's zip](simulator.md) writes
`avionics-panel-ifr1-cows-da40.mfproj`, as `python3 -m mobiflight --ifr1 cows-da40 --vfr 1200` does from the
repository ([Generators](../architecture/generators.md)). Or change `0x7000` in the project's `XPDR^_TOG`
item, where the code stands once, as for the panel ([Generated profiles](mapping.md#generated-profiles)).

## What each control does

| Mode | Outer / inner ring | ⇆ | Knob push, keys |
| --- | --- | --- | --- |
| COM1, COM2 | MHz / kHz of COM 1 / COM 2 | tap: flip-flop; let go after 0.7 s: COM 1 / COM 2 audio (listen); held 2 s: talk on COM 1 / COM 2 | shift |
| HDG (COM1 shifted) | heading bug 10° / 1° | heading bug to the heading (in the Bonanza the HSI's course too) | shift back |
| BARO (COM2 shifted) | altimeter setting on both rings; in the Bonanza, of both altimeters | tap: STD; again: the setting before, where the panel does so (in the Bonanza both altimeters); hold: pitot heat | shift back |
| NAV1, NAV2 | MHz / kHz of NAV 1 / NAV 2 | tap: flip-flop; hold: NAV 1 / NAV 2 audio (ident) | shift |
| CRS1 (NAV1 shifted) | course 10° / 1°: in the G1000 NXi, DA40, C182T and G3X profiles the CDI's course, else NAV 1's | tap: the course to the VOR or LOC; hold: marker audio | shift back |
| CRS2 (NAV2 shifted) | NAV 2 course 10° / 1° | tap: NAV 2's course to the VOR or LOC; hold: DME audio | shift back |
| FMS1, FMS2 | the unit's FMS knob; ⇆ held: its map range, where the profile has one (the G3X has none), the outer ring on a GTN its volume | tap: the unit's HOME, where it has one | CRSR; D→, MENU, CLR, ENT and CDI, OBS, MSG, FPL, VNAV, PROC; held CLR, MENU, PROC: MAP, NRST, TERR; each where the profile has it |
| AP | selected altitude 1000 ft / 100 ft; ⇆ held: the inner ring is the panel's UP and DN (the held altitude, VS, IAS or pitch, by autopilot) | tap: by autopilot, below | held: VNV |
| XPDR | first two / last two squawk digits; ⇆ held: panel dimmer / flood dimmer (the C182T's cabin lights), where the profile knows the aircraft's | tap: IDENT | shift |
| MODE (XPDR shifted) | either ring: clockwise ALT (from standby or off), counter-clockwise standby | tap: VFR and back; hold: cabin light | shift back |
| Every mode but FMS1 and FMS2 | | | AP, HDG, NAV, APR (held: BC), ALT (held: ARM), VS, each where the profile has it |

- ⇆ in FMS1, FMS2, AP and XPDR: held while turning a ring, the ring does what follows "⇆ held" and ⇆ sends
  nothing when let go. Otherwise ⇆ sends its tap when let go, and nothing after 0.7 s, a press meant for a turn
  that did not come. Press ⇆ first, then turn: a detent that comes with the press, in the same report of the
  IFR-1, reaches the profile before it (MobiFlight 11.3.1), so that detent does what it does without ⇆, and ⇆
  let go at once then sends its tap, unless the ring turned again. For that reason ⇆ has no hold in these
  modes: a hold there, as LVL, would come with a turn meant for the ring.
- A key with a hold sends its hold at once when held 0.7 s, while still down, and its own function on a tap,
  when let go; let go after the hold, it sends nothing more. The amber functions of the panel's keys are such
  holds: APR (BC), ALT (ARM), CLR (MAP), MENU (NRST) and PROC (TERR), each where the profile maps that
  function; the cheat sheet says what it is in the aircraft. ⇆ in NAV1, NAV2 and CRS2, held, is the panel's
  NAV 1, NAV 2 or DME audio; in CRS1 and BARO the simulator's event for the marker audio or pitot heat, which
  an aircraft may ignore; in MODE the cabin light. The AP knob's push is VNV, held only, as a push comes
  easily with a turn of the altitude rings. AP, HDG, NAV and VS send at once: disengaging the autopilot cannot
  wait for the release.
- ⇆ in COM1 and COM2 has two holds in place of 121.5: let go after 0.7 s, it is the panel's COM 1 or COM 2
  audio, which turns listening to that radio on or off; held for 2 s, it is the panel's MIC 1 or MIC 2 at that
  moment, which picks the radio you talk on, and its release then sends nothing. So COM 2 can play the ATIS
  while you talk on COM 1. A hold is twice the panel's 0.35 s, so a flip-flop pressed a little slow does not
  turn a radio's audio off unseen.
- FMS1 and FMS2 are the panel's units 1 and 2, but in the G1000 NXi, DA40 and C182T profiles FMS1 is the PFD
  and FMS2 the MFD, as the G1000 numbers them (the panel's unit 1 is the MFD): there ⇆ held with a ring zooms
  the PFD's inset map in FMS1, which shows only when the inset is on, and the MFD's map in FMS2. In the Black
  Square Bonanza, FMS1 is the primary selection of its tablet and FMS2 the secondary, every selection at once,
  as on the panel. With ⇆ held, the outer ring is the GNS's map range and the GTN's volume (TDS's and
  PMS50's), and in FMS1 also the KLN 90B's left outer knob; the inner ring is the map range, and in FMS1 also
  the KLN 90B's left inner knob. On a GTN (TDS's or PMS50's) that range is its inner knob, which sets the
  range on a map page and works the knob on any other page.
- On TDS's GTN, in the GTN and Bonanza profiles, MENU, CLR and ENT of FMS1 and FMS2 set its volume up and down
  and push its volume knob (squelch with COM selected, ident with NAV), as TDS's GTN takes those keys only on
  its touchscreen; in the Bonanza FMS2's MENU does so held.
- The Black Square Bonanza has more on the IFR-1 than on the panel's keys alone, as one profile for every
  selection of its tablet. PMS50's GTN takes MENU, CLR, ENT and MSG as the keys its screen shows and PROC as
  its Procedures page (these with PMS50's Premium version), as on the panel. ⇆ in HDG sets the HSI's course
  (the yellow arrow) to the heading with the heading bug. BARO's rings and ⇆ set both altimeters, the
  right-hand one to the left-hand one's setting. The cockpit's functions go on keys: CDI held in FMS1 switches
  the HSI between NAV 1 and RNAV (GPSS, which CRS1 needs on RNAV); in FMS2, VNAV steps the DME selector, and
  MENU and PROC are the EDM 800's STEP and LEAN FIND on a tap, as they are pressed often, the GNS 430's MENU and
  PROC (and PMS50's) moving to the hold. Held in FMS2, ENT runs the KFC 150's self-test with the autopilot off,
  MSG opens or shuts the oxygen valve, FPL switches the tip tank transfer pumps (both off if either runs, else
  both on), OBS prop heat, CDI steps the fuel boost pump one position from where it is (off, low, high, off)
  and VNAV switches the air conditioner with its blower, as the guide's "Hardware Inputs & Outputs" and the
  project the Bonanza is flown with set them. The fuel selector stays in the cockpit.
- The COWS DA40 and the Carenado C182T have their electric fuel pump on CDI held in FMS2, and the DA40 NG
  its fuel transfer pump on FPL held in FMS2 (the XLS ignores it). The C182T's inner ring in XPDR with ⇆ held
  dims its two cabin lights, as on the panel.
- ⇆ tapped in AP: FLC on the GFC 700 and GFC 500 (its IAS mode), FD on the KFC 150, nothing on the KAP 140.
  The KAP 140's VS key leaves ALT hold for VS, which the panel leaves to its ALT key.
- The squawk rings step two digits at a time as one octal number, from 77 round to 00 and back. The MODE
  rings take the transponder one way each however far they turn: from standby or off to ALT, from ALT or on
  to standby.
- The rings send one step per detent, without the panel's quick turn. MobiFlight passes on every detent of a
  fast spin; whether the sim keeps up is to check.
- MobiFlight sends a key's release to the mode the IFR-1 is in when the key comes up, and a hold to the button
  the key went down on. A change of mode, or leaving shift with the knob push, lets go of ⇆ and of every key
  with a hold, so one still held then sends nothing, neither held on nor let go; entering shift lets go of ⇆,
  so a hold of COM1 or COM2 sends nothing in HDG or BARO. A key of TDS's GTN held in FMS1 or FMS2 while
  changing mode stays down in the GTN until pressed again; its key-up never reaches the other GTN.

What the IFR-1 has no control for, of the panel's functions: in every profile 121.5 and the ADF, including its
ident audio, and the maps' pan and pointer; the COM volume in the GNS and Bonanza profiles; in the Bonanza,
PMS50's volume push, the MD41's lamp test, the KLN 90B's left CRSR, the KR 87's keys, the EDM 800's long
presses, the weather radar and the KFC 150's YD; the GFC 700's and GFC 500's FD, YD and LVL. The cheat sheets
mark every control that does nothing in a profile, with the reason.

## To check on the device

- In COM1, a fast spin of 20 detents steps exactly 20 channels; so do the squawk rings, HDG, CRS1 and CRS2's
  outer rings, the dimmers and the Bonanza's BARO rings, which read the sim's value and write a new one each
  detent. With firmware 1.2, the mode key flashes only while shifted.
- The holds: 0.7 s feels right, neither a tap taken for a hold nor a hold that keeps one waiting; the hold goes
  out while the key is still down, and nothing when it comes up.
- The AP lights: the G1000 NXi lights HDG, NAV and APR in those modes (if it sets the sim's flags for them);
  the KAP 140's NAV and APR armed or captured; the KFC 150's modes on the sim's flags, or Black Square's own.
- The lights go out when the sim closes or MobiFlight stops.
- A bounce of the knob push (shift on and off at once, reported with MobiFlight) lets go of a ⇆ or key with a
  hold held meanwhile in COM1, COM2, NAV1, NAV2 or XPDR or their shifted modes: MobiFlight sends the same
  button for leaving shift as for a change of mode.
- ⇆ held in CRS1: the aircraft takes the simulator's marker audio event (Black Square's guide has it for the
  Bonanza); in BARO, the pitot heat event in the G1000 NXi, G3X, GNS and GTN profiles (the Bonanza, DA40 and
  C182T projects already send it).
- ⇆ pressed with a ring turned at once, in FMS1, FMS2, AP and XPDR: how often the IFR-1 reports the press and
  a detent together, which sends the detent without ⇆ and, with no further turn, ⇆'s tap when let go. In AP,
  where ⇆ held sets the rate or speed, that tap is FLC on the GFC 700 and GFC 500, which switches FLC off when
  it is the active mode: if it happens on the device, AP's ⇆ loses its tap too.
- COM1 and COM2: ⇆ let go after 0.7 s and before 2 s turns only that radio's audio on or off, and held for 2 s
  picks only the radio to talk on, while still held, with nothing more on its release.
- MODE: each ring takes the transponder to ALT clockwise and to standby counter-clockwise in every profile.
- KAP 140 (C182T, GNS, GTN): the VS key sends AP_PANEL_VS_ON past the KAP 140's own keys; its display shows VS
  and not ALT after it.
- Bonanza: ⇆ tapped in AP takes the KFC 150's FD (the simulator's TOGGLE_FLIGHT_DIRECTOR, which Black Square's
  guide does not list).
- Bonanza: the GTX 327 shows the code the squawk rings and VFR set with XPNDR_SET.
- Bonanza: with the two altimeters set apart, the right-hand one is the simulator's altimeter 2 and takes
  KOHLSMAN_SET's two parameters in the order the profile gives them (index, then the setting); either BARO
  ring sets both to the same setting; ⇆ tapped twice sets both to STD and back to the setting before. The
  panel's BARO sets only the left-hand one, so its STD after the IFR-1's brings back only that one. The rings
  step 0.01 inHg; with the sim in hPa, the setting moves 1 hPa about every third detent.
- Bonanza: CRS2 turns NAV 2's indicator; CRS1 with the HSI on RNAV (CDI held in FMS1); ⇆ in HDG turns the
  HSI's course to the heading.
- Bonanza: MENU, CLR and ENT in FMS1 and FMS2 (FMS2's MENU held) set the volume of TDS's GTN and push it; the
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
