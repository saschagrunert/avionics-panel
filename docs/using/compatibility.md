# Compatibility

What each control maps to on each avionics family, by aircraft. The firmware sends a separate joystick button
for every key, knob step and push, plain and shifted (two joysticks, see [Mapping](mapping.md)); only
SHIFT itself, UNIT (SHIFT, HOME) and the outer ring of the squawk entry send none. MobiFlight maps them per
aircraft, so one panel drives every avionics family below. Keys without a counterpart in an aircraft stay
unused.

Covered families: G1000 and G1000 NXi, TDS GTN 750Xi and 650Xi, GNS 530/430, Bendix/King (KAP 140, KFC 150 +
KAS 297B, KFC 225, KX 155/165, KR 87, KT 76, KMA 28), GTX 327, newer Garmin (GFC 500, G3X Touch). For MSFS 2024,
[generated profiles](mapping.md#generated-profiles) cover the G1000 NXi, the GFC 500 with the G3X Touch, the
GNS 530/430 and TDS GTN 750Xi and 650Xi with the KAP 140, and Black Square's KFC 150 with the KAS 297B; the
others are mapped by hand.

Compared with the documentation of these reference aircraft, with the profile that fits each:

- Cessna 172 Skyhawk G1000 (G1000 NXi): G1000 profile
- CubCrafters XCub (one G3X Touch) and Draco X (PFD and MFD): G3X profile
- Cessna 172 Skyhawk Classic (KAP 140, GNS 530/430): GNS profile; with TDS's GTN 750Xi and 650Xi: GTN profile
- COWS DA40 (Working Title G1000 with its own autopilot): G1000 profile; its autopilot keys may need the
  aircraft's own events
- Black Square Bonanza (KFC 150 + KAS 297B, KX 155B, KR 87, GTX 327, GNS 530/430 or GTN 750/650): KFC 150
  profile
- Black Square TBM 850 (KFC 325, KAS 297B), Caravan, Duke and King Air: by hand
- A2A Comanche 250 (S-TEC 30, Narco radios, NSD-360A HSI): by hand
- A2A Aerostar 600 (Century IV, Collins Microline radios: VHF-251, VIR-351, ADF-650, TDR-950, AMR-350): by hand

Autopilots:

| Panel | GFC 700 (G1000) | GFC 500 | KAP 140 | KFC 150 + KAS 297B | KFC 225 |
| --- | --- | --- | --- | --- | --- |
| AP, HDG, NAV, APR, ALT | Yes | Yes | Yes | Yes (AP = AP ENG) | Yes |
| TEST (SHIFT, AP) | None (self-test at power-up) | None | None (self-test at power-up) | TEST, preflight check | Depends on the aircraft |
| BC (SHIFT, APR) | BC | None (back course is automatic) | REV | BC | REV |
| VNV | Yes | Yes | None | None | None |
| VS | Yes | Yes | None (VS via UP / DN) | VS on the KAS 297B | Yes |
| FLC | Yes | IAS | None | None | None |
| LVL | Some NXi installs | Yes | None | None | None |
| GPSS (SHIFT, NAV) | None (NAV flies GPS steering) | None (NAV flies GPS steering) | None (NAV follows the CDI) | None | None |
| ½ BANK (SHIFT, LVL) | None in MSFS's G1000 aircraft | None | None | None | None |
| FD, YD (SHIFT, FD) | Yes | Yes | None | FD, YD switch | YD if installed |
| ARM (SHIFT, ALT) | None (Tmr/Ref softkey in the profile) | None | ARM | ARM on the KAS 297B | ARM |
| UP / DN | NOSE UP / DN | Wheel | UP / DN | Vertical trim rocker | UP / DN |
| ALT knob | ALT knob | ALT SEL knob | Altitude select knob | KAS 297B knob | Altitude select knob |
| HDG knob, push SYNC | HDG, push sync | HDG, push sync | HDG bug (KI 525), no sync | HSI heading bug, no sync | HDG bug, no sync |
| SHIFT: BARO, CRS, push STD; CRS CTR (SHIFT, HDG) | CRS/BARO knob: outer BARO, inner CRS; its push centres the course | On the G5 / G3X knob | CRS (KI 525), BARO key + knob | HSI course, altimeter | CRS, BARO |

More autopilots in Black Square and A2A aircraft:

| Panel | KFC 325 + KMC 321 (Black Square TBM 850) | King Air (Black Square) | S-TEC 30 + ST-901 (A2A Comanche) | Century IV (A2A Aerostar) |
| --- | --- | --- | --- | --- |
| AP, HDG, NAV, APR, ALT | Yes | Yes | HDG, NAV, ALT (no APR key) | Yes |
| BC (SHIFT, APR) | BC | BC | None | REV |
| VS, UP / DN | VS, UP / DN | VS, UP / DN | UP / DN command VS | Pitch trim wheel |
| FLC | IAS | IAS | None | None |
| YD (SHIFT, FD) | Yes | Yes | None | Option |
| ½ BANK (SHIFT, LVL) | Half bank | Half bank | None | None |
| GPSS (SHIFT, NAV) | Via the navigator | Via the navigator | ST-901 GPSS | None |
| ALT knob, ARM | KAS 297B | Altitude preselect | None | None |

½ BANK limits the bank angle to about half for a smoother ride. Collins, the KFC 325 and Garmin's
G3000 and GFC 600 (labelled BANK there) have it.

Navigators:

| Panel | G1000 / NXi | G3X Touch | GTN 750Xi (TDS) | GNS 530/430 |
| --- | --- | --- | --- | --- |
| D→, MENU, CLR, ENT, FPL, PROC | Bezel keys | D→, MENU and BACK (CLR) are keys; FPL and ENT are on the touchscreen; no procedures | D→ is a key; the rest are on the touchscreen | Bezel keys |
| HOME | None (ENGINE softkey and back in the profile) | None | HOME key | None |
| MSG, NRST, VNAV, TERR, MAP (with SHIFT) | Softkeys; in the profile MSG and NRST press the PFD's Alerts and Nearest, MAP, TERR and VNAV the MFD's Charts, Checklist and Detail | NRST key; the rest are on the touchscreen | Touchscreen | MSG key; NRST page; VNAV key (530); hold CLR |
| CDI, OBS | Softkeys | Touchscreen, worked by the sim's events (see below) | Touchscreen | Bezel keys |
| FMS knob, push CRSR | FMS knob | Right knob and its push | The GTN's dual knob (no cursor, see below) | Right knob, push CRSR |
| RANGE, pan, push PTR | MFD RANGE knob + joystick; with SHIFT the PFD's | Touchscreen; the inner knob zooms on the map page | Touchscreen; the inner knob zooms on the map page; with SHIFT the volume knob | RNG keys; with SHIFT the second unit's |
| UNIT (SHIFT, HOME) | MFD with radio 1 / PFD with radio 2 | PFD / MFD, where there are two displays | GTN / second unit | 530 / 430 |

On units without a HOME key (G1000, G3X Touch, GNS) map HOME to whatever is used most there; the G1000
profile makes it the MFD's ENGINE softkey and back.

The TDS GTN 750Xi and 650Xi take only their bezel controls from outside: HOME, D→, the dual knob and its push,
and the volume knob and its push. Their touchscreen functions have no event or variable, so these controls do
nothing with a GTN: FPL, PROC, MENU, CLR, ENT, MSG, NRST, TERR, VNAV, MAP, CDI, OBS, RANGE without SHIFT, PTR
without SHIFT, the map's pan. Press HOME and touch the function on the screen; the map also zooms with the
inner FMS knob on the map page. The GTN and KFC 150 profiles put the GTN 750's volume knob on SHIFT with the
RANGE knob. The pms50 GTN 750 takes other events: the [generated profile](mapping.md#generated-profiles) for
TDS's GTNs does not work with it, the [KFC 150 profile](mapping.md#kfc-150-black-square) in Black Square's
Bonanza does.

The G3X Touch has its CDI, OBS, radios, transponder and audio panel on the touchscreen too, but those are the
sim's own, which the sim's events work from outside. Its own functions stay on its screen, so these controls
do nothing with a G3X Touch: FPL, ENT, MSG, VNAV, TERR, MAP, RANGE, the map's pan and PTR.

Radios, transponder, audio:

| Panel | G1000 | G3X Touch | GTN / GNS | Bendix/King |
| --- | --- | --- | --- | --- |
| FREQ knob, push COM/NAV/ADF | COM and NAV knobs, ADF window | COM and NAV radios, shown on the data bar | COM and NAV radios, shown on the GNS (GTN: see [Mapping](mapping.md#tds-gtn-750xi-and-650xi)) | KX 155/165 knobs, KR 87 |
| COM ⇆, NAV ⇆, ADF ⇆ | Flip-flops | Flip-flops on the data bar | Flip-flops (GTN: no key, see below) | Flip-flops, KR 87 FRQ |
| 121.5 (SHIFT, COM ⇆) | Hold COM ⇆ | Sets COM to 121.5 | GNS: hold COM ⇆ (not in the Working Title GNS); GTN: hold the volume knob pushed for about 2 s | Sets COM to 121.5 |
| UNIT for radio 2 | COM 2 / NAV 2 tuning box | COM 2 / NAV 2 | Second unit | Second radio |
| Squawk, XPDR mode, IDENT, VFR | GTX 345 | Transponder on the data bar | GTX 327 / GTN XPDR | KT 76 |
| MIC / COM / NAV / ADF / DME audio | GMA 1347 | Audio panel on the data bar | GMA 340 / GMA 35 | KMA 28 |

The GTN has one dual knob for the FREQ and FMS rows. Its push toggles tuning between COM and NAV (there is no
cursor), pushing and holding it flips the active and standby frequency, and it returns from NAV to COM by
itself after 30 s without input. It has no COM ⇆ key: map COM ⇆ to the flip-flop event, where the aircraft
exposes one.

Partly covered: the KLN 90B (Black Square Bonanza). D→, CLR, ENT, MSG and the FMS knob can map to it
if the aircraft exposes events for them; its cursor keys and second knob have no place on the panel.

Cockpit lighting (SHIFT, FMS knob) maps to the aircraft's panel and flood light dimmers and the cabin or
dome light, where the sim or the aircraft exposes them as events or variables; aircraft with one dimmer
for everything use the outer ring only.

Deliberately not on the panel: volume and squelch (except the GTN 750's, on SHIFT with the RANGE knob in the
GTN and KFC 150 profiles), the G1000 softkeys (except the ones the G1000 profile presses), the KR 87 timer,
the KN 62 DME mode switch and the Collins IND-450 DME, marker audio (MKR), COM 3, KNS 81 RNAV waypoint entry,
weather radar controls (RDR 1150XL), soft ride, autothrottle and the G3000 touch controllers.
