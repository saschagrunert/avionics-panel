# Octavi IFR-1

The [ready profiles](mapping.md#generated-profiles) also come for the Octavi IFR-1, a desktop knob and key
box with eight modes, in place of the panel. Each IFR-1 profile sends what the panel's profile of the same
name sends, so a fix to a panel profile reaches its IFR-1 profile too. They are for MSFS 2024 with MobiFlight
11.3 or newer on Windows. They are not yet tried on the device: the Black Square Bonanza, COWS DA40 and
Carenado C182T come first ([To check on the device](#to-check-on-the-device)).

## Downloads

From the release [Latest build][rolling], one project per profile, each with a card (the events every
control sends) and a cheat sheet (what every control does, in words) on the web:

| Profile | Project | Card | Cheat sheet |
| --- | --- | --- | --- |
| Black Square Bonanza | [avionics-panel-ifr1-black-square-bonanza.mfproj][p-bonanza] | [card][c-bonanza] | [cheat sheet][s-bonanza] |
| COWS DA40 | [avionics-panel-ifr1-cows-da40.mfproj][p-da40] | [card][c-da40] | [cheat sheet][s-da40] |
| Carenado C182T | [avionics-panel-ifr1-carenado-c182t.mfproj][p-c182t] | [card][c-c182t] | [cheat sheet][s-c182t] |
| G1000 NXi | [avionics-panel-ifr1-g1000.mfproj][p-g1000] | [card][c-g1000] | [cheat sheet][s-g1000] |
| GFC 500 and G3X Touch | [avionics-panel-ifr1-g3x.mfproj][p-g3x] | [card][c-g3x] | [cheat sheet][s-g3x] |
| GNS 530/430 | [avionics-panel-ifr1-gns.mfproj][p-gns] | [card][c-gns] | [cheat sheet][s-gns] |
| TDS GTN 750Xi/650Xi | [avionics-panel-ifr1-gtn.mfproj][p-gtn] | [card][c-gtn] | [cheat sheet][s-gtn] |

The cards and cheat sheets are also in [avionics-panel-cards.zip][cards], with the commit of the download in
their titles. Open one in a browser and print it on A4 in landscape.

## Setting up

1. Install MobiFlight 11.3 or newer: the IFR-1's ⇆ and keys need its long press, which came with 11.3. Every
   command goes through MobiFlight's WASM module in the sim's Community folder: when MobiFlight offers it,
   choose Install Now with the sim closed.
2. Quit Octavi's own plugin and keep it from starting with the sim. Only one program can open the IFR-1 at a
   time: with the plugin or Octavi's configuration tool running, MobiFlight sees no input.
3. Plug in the IFR-1 and open the downloaded profile in MobiFlight (File, Open). MobiFlight binds it to the
   connected IFR-1 by itself, by the name the IFR-1 gives itself. Octavi's registry fix for the IFR-1's GUID
   is not needed; the profile carries the GUID that fix sets, so with it applied the two should match without
   binding. Two IFR-1s on one PC are not supported.
4. Start a flight with the avionics on and choose Run. In COM1, turn the inner ring one detent: COM 1's
   standby frequency must step by one channel.
5. Save the project (File, Save).

The AP keys' lights are meant to show the autopilot's modes in every mode of the IFR-1, from the sim's
autopilot flags ([To check on the device](#to-check-on-the-device)). The flash of the mode key in shift is
MobiFlight's own and needs the IFR-1's firmware 1.2 or newer, which Octavi offers as early access only. For
another VFR code than 7000, as 1200 in the US: `python3 -m mobiflight --ifr1 cows-da40 --vfr 1200` writes
`avionics-panel-ifr1-cows-da40.mfproj` ([Generators](../architecture/generators.md)).

## What each control does

| Mode | Outer / inner ring | ⇆ | Knob push, keys |
| --- | --- | --- | --- |
| COM1, COM2 | MHz / kHz of COM 1 / COM 2 | tap: flip-flop; hold: 121.5 | shift |
| HDG (COM1 shifted) | heading bug 10° / 1° | heading bug to the heading | shift back |
| BARO (COM2 shifted) | altimeter setting on both | STD; again: the setting before, where the panel does so | shift back |
| NAV1, NAV2 | MHz / kHz of NAV 1 / NAV 2 | flip-flop | shift |
| CRS1 (NAV1 shifted) | course 10° / 1°: on the G1000 NXi and G3X the CDI's course, else NAV 1's | the course to the VOR or LOC | shift back |
| CRS2 (NAV2 shifted) | NAV 2 course 10° / 1° | NAV 2's course to the VOR or LOC | shift back |
| FMS1, FMS2 | the unit's FMS knob; ⇆ held: its map range, where the profile has one (the G3X has none) | tap: the unit's HOME, where it has one | CRSR; D→, MENU, CLR, ENT and CDI, OBS, MSG, FPL, VNAV, PROC; held CLR, MENU, PROC: MAP, NRST, TERR; each where the profile has it |
| AP | selected altitude 100 ft, ⇆ held 1000 ft / the panel's UP and DN | tap and hold: by autopilot, below | VNV |
| XPDR | first two / last two squawk digits | tap: IDENT; hold: VFR and back; held and a ring turned: standby or ALT | shift |
| lights (XPDR shifted) | panel dimmer / flood dimmer, where the profile knows the aircraft's | cabin light | shift back |
| Every mode but FMS1 and FMS2 | | | AP, HDG, NAV, APR (held: BC), ALT (held: ARM), VS, each where the profile has it |

- ⇆ in FMS1, FMS2, AP and XPDR: held while turning a ring, the ring does what follows "⇆ held" and ⇆ sends
  nothing when let go. Otherwise ⇆ sends its tap, or after more than 0.35 s its hold, as it is let go.
- A key with an amber function on the panel sends that function when held and its own on a tap, both as it is
  let go: APR (BC), ALT (ARM), CLR (MAP), MENU (NRST), PROC (TERR) and ⇆ in COM1 and COM2 (121.5), each where
  the profile maps that function; the cheat sheet says what it is in the aircraft. AP, HDG, NAV and VS send at
  once: disengaging the autopilot cannot wait for the release.
- FMS1 and FMS2 are the panel's units 1 and 2, but on the G1000 NXi FMS1 is the PFD and FMS2 the MFD, as the
  G1000 numbers them (the panel's unit 1 is the MFD). In the Black Square Bonanza, FMS1 is the primary
  selection of its tablet and FMS2 the secondary, every selection at once, as on the panel; with ⇆ held the
  outer ring of FMS1 is the KLN 90B's left outer knob, which does nothing on a GNS or GTN.
- ⇆ in AP: GFC 700 and GFC 500 tap FLC, hold LVL; KFC 150 tap FD, hold YD; KAP 140 nothing. The KAP 140's VS
  key leaves ALT hold for VS, which the panel leaves to its ALT key.
- The squawk rings step two digits at a time as one octal number, from 77 round to 00 and back.
- The rings send one step per detent, without the panel's quick turn. MobiFlight passes on every detent of a
  fast spin; whether the sim keeps up is to check.
- MobiFlight sends a key's release to the mode the IFR-1 is in when the key comes up. A change of mode, or
  leaving shift with the knob push, lets go of ⇆ and of every key with a hold, so one still held then sends
  nothing when let go in the new mode. A key of TDS's GTN held in FMS1 or FMS2 while changing mode stays down
  in the GTN until pressed again; its key-up never reaches the other GTN.

What the IFR-1 has no control for, of the panel's functions: in every profile the audio panel and the ADF; the
maps' pan and pointer, or the COM and GTN volume and squelch the GNS, GTN and Bonanza profiles put there; the
GFC 700's and GFC 500's FD and YD (the Bonanza has its own on ⇆ in AP); in the Bonanza its TEST, GPSS (the
HSI's NAV 1 or RNAV switch), the KLN 90B's left CRSR, the KR 87's keys, the EDM 800, the DME selector and the
weather radar. The cheat sheets mark every control that does nothing in a profile, with the reason.

## To check on the device

- In COM1, a fast spin of 20 detents steps exactly 20 channels; so do the squawk rings, HDG, CRS1 and CRS2's
  outer rings and the dimmers, which read the sim's value and write a new one each detent. With firmware 1.2,
  the mode key flashes only while shifted.
- The AP lights: the G1000 NXi lights HDG, NAV and APR in those modes (if it sets the sim's flags for them);
  the KAP 140's NAV and APR armed or captured; the KFC 150's modes on the sim's flags, or Black Square's own.
- The lights go out when the sim closes or MobiFlight stops.
- A bounce of the knob push (shift on and off at once, reported with MobiFlight) lets go of a ⇆ or key with a
  hold held meanwhile in COM1, COM2 or XPDR: MobiFlight sends the same button for leaving shift as for a change
  of mode.
- Bonanza: CRS2 turns NAV 2's indicator; CRS1 with the HSI on RNAV (switched on the panel or in the cockpit:
  the IFR-1 has no GPSS).
- TDS's GTN takes the tap of ⇆ in FMS1 and FMS2, sent down and up at once, as HOME.
- Flying the panel and the IFR-1 together, both profiles in one MobiFlight project.

[rolling]: https://github.com/saschagrunert/avionics-panel/releases/tag/rolling
[cards]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-cards.zip
[p-bonanza]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-black-square-bonanza.mfproj
[p-da40]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-cows-da40.mfproj
[p-c182t]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-carenado-c182t.mfproj
[p-g1000]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-g1000.mfproj
[p-g3x]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-g3x.mfproj
[p-gns]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-gns.mfproj
[p-gtn]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-ifr1-gtn.mfproj
[c-bonanza]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-black-square-bonanza-card.html
[c-da40]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-cows-da40-card.html
[c-c182t]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-carenado-c182t-card.html
[c-g1000]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g1000-card.html
[c-g3x]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g3x-card.html
[c-gns]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gns-card.html
[c-gtn]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gtn-card.html
[s-bonanza]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-black-square-bonanza-sheet.html
[s-da40]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-cows-da40-sheet.html
[s-c182t]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-carenado-c182t-sheet.html
[s-g1000]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g1000-sheet.html
[s-g3x]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-g3x-sheet.html
[s-gns]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gns-sheet.html
[s-gtn]: https://saschagrunert.de/avionics-panel/cards/avionics-panel-ifr1-gtn-sheet.html
