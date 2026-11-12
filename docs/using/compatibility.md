# Compatibility

What each control maps to on each avionics family, by aircraft. The firmware sends a separate joystick button
for every key, knob step and push, plain and shifted (two joysticks, see [Mapping](mapping.md)); only
SHIFT itself, UNIT (SHIFT, HOME) and the outer ring of the squawk entry send none. MobiFlight maps them per
aircraft, so one panel drives every avionics family below. Keys without a counterpart in an aircraft stay
unused.

Covered families: G1000 and G1000 NXi, TDS GTN 750Xi, GNS 530/430, Bendix/King (KAP 140, KFC 150 + KAS 297B,
KFC 225, KX 155/165, KR 87, KT 76, KMA 28), GTX 327, newer Garmin (GFC 500, G3X, G500 TXi).

Checked against these reference aircraft:

- COWS DA40 (Working Title G1000 with its own autopilot, G1000 profile)
- Black Square Bonanza (KFC 150 + KAS 297B, KX 155B, KR 87, GTX 327, GNS 530/430 or GTN 750/650)
- Black Square TBM 850 (KFC 325, KAS 297B), Caravan, Duke and King Air
- A2A Comanche 250 (S-TEC 30, Narco radios, NSD-360A HSI)
- A2A Aerostar 600 (Century IV, Collins Microline radios: VHF-251, VIR-351, ADF-650, TDR-950, AMR-350)

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
| FD, YD (SHIFT, FD) | Yes | Yes | None | FD, YD switch | YD if installed |
| ARM (SHIFT, ALT) | None | None | ARM | ARM on the KAS 297B | ARM |
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

| Panel | G1000 / NXi | GTN 750Xi (TDS) | GNS 530/430 |
| --- | --- | --- | --- |
| D→, MENU, CLR, ENT, FPL, PROC | Bezel keys | D→ is a key; the rest are on the touchscreen | Bezel keys |
| HOME | None | HOME key | None |
| MSG, NRST, VNAV, TERR, MAP (with SHIFT) | Softkeys / pages; hold CLR | Touchscreen | MSG key; NRST page; VNAV key (530); hold CLR |
| CDI, OBS | Softkeys | Touchscreen | Bezel keys |
| FMS knob, push CRSR | FMS knob | The GTN's dual knob (no cursor, see below) | Right knob, push CRSR |
| RANGE, pan, push PTR | RANGE knob + joystick | Map zoom | RNG keys |
| UNIT (SHIFT, HOME) | Radio 2 only; the FMS keys stay on the MFD | GTN / second unit | 530 / 430 |

On units without a HOME key (G1000, GNS) map HOME to whatever is used most there.

The TDS GTN 750Xi and 650Xi take only their bezel controls from outside: HOME, D→, the dual knob and its
push, and the volume knob and its push. Their touchscreen functions (FPL, PROC, MENU, CLR, ENT, MSG, NRST,
TERR, VNAV, MAP, CDI, OBS) have no event or variable, so these keys do nothing with a GTN: press HOME and
touch the function on the screen.

Radios, transponder, audio:

| Panel | G1000 | GTN / GNS | Bendix/King |
| --- | --- | --- | --- |
| FREQ knob, push COM/NAV/ADF | COM and NAV knobs, ADF window | Dual knob, C/V push | KX 155/165 knobs, KR 87 |
| COM ⇆, NAV ⇆, ADF ⇆ | Flip-flops | Flip-flops (GTN: no key, see below) | Flip-flops, KR 87 FRQ |
| 121.5 (SHIFT, COM ⇆) | Hold COM ⇆ | GNS: hold COM ⇆; GTN: hold the volume knob pushed for about 2 s | Sets COM standby to 121.5 |
| UNIT for radio 2 | COM 2 / NAV 2 tuning box | Second unit | Second radio |
| Squawk, XPDR mode, IDENT, VFR | GTX 345 | GTX 327 / GTN XPDR | KT 76 |
| MIC / COM / NAV / ADF / DME audio | GMA 1347 | GMA 340 / GMA 35 | KMA 28 |

The GTN has one dual knob for the FREQ and FMS rows. Its push toggles tuning between COM and NAV (there is no
cursor), pushing and holding it flips the active and standby frequency, and it returns from NAV to COM by
itself after 30 s without input. It has no COM ⇆ key: map COM ⇆ to the flip-flop event, where the aircraft
exposes one.

Partly covered: the KLN 90B (Black Square Bonanza). D→, CLR, ENT, MSG and the FMS knob can map to it
if the aircraft exposes events for them; its cursor keys and second knob have no place on the panel.

Cockpit lighting (SHIFT, FMS knob) maps to the aircraft's panel and flood light dimmers and the cabin or
dome light, where the sim or the aircraft exposes them as events or variables; aircraft with one dimmer
for everything use the outer ring only.

Deliberately not on the panel: volume and squelch, the G1000 softkeys, the KR 87 timer, the KN 62 DME
mode switch and the Collins IND-450 DME, marker audio (MKR), COM 3, KNS 81 RNAV waypoint entry,
weather radar controls (RDR 1150XL), soft ride, autothrottle and the G3000 touch controllers.
