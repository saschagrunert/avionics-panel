# Compatibility

The firmware sends a separate joystick button for every key, knob step and push, plain and shifted
(two joystick devices, see [Firmware](firmware.md)). MobiFlight maps them per aircraft, so one panel
drives every avionics family below. Keys without a counterpart in an aircraft simply stay unused.
Covered families: G1000 and G1000 NXi, TDS GTN 750Xi, GNS 530/430, Bendix/King (KAP 140, KFC 150 with
KAS 297B, KFC 225, KX 155/165, KR 87, KT 76, KMA 28), GTX 327, newer Garmin (GFC 500, G3X, G500 TXi).
Checked against these reference aircraft: the COWS DA40 (Working Title G1000 with its own autopilot,
G1000 profile), the Black Square Bonanza (KFC 150 + KAS 297B, KX 155B, KR 87, GTX 327, GNS 530/430 or
GTN 750/650), the Black Square TBM 850 (KFC 325, KAS 297B), Caravan, Duke and King Air, and the A2A
Comanche 250 (S-TEC 30, Narco radios, NSD-360A HSI) and Aerostar 600 (Century IV, Collins Microline
radios: VHF-251, VIR-351, ADF-650, TDR-950, AMR-350).

Autopilots:

| Panel | GFC 700 (G1000) | GFC 500 | KAP 140 | KFC 150 + KAS 297B | KFC 225 |
| --- | --- | --- | --- | --- | --- |
| AP, HDG, NAV, APR, ALT | yes | yes | yes | yes (AP = AP ENG) | yes |
| TEST (SHIFT, AP) | none (self-test at power-up) | none | none (self-test at power-up) | TEST, preflight check | verify |
| BC (SHIFT, APR) | BC | verify | REV | BC | REV |
| VS | yes | yes | none (VS via UP/DN) | VS on the KAS 297B | yes |
| FLC | yes | IAS | none | none | none |
| VNV | yes | yes | none | none | none |
| LVL | some NXi installs | yes | none | none | none |
| FD, YD (SHIFT, FD) | yes | yes | none | FD, YD switch | YD if installed |
| ARM (SHIFT, ALT) | none | none | ARM | ARM on the KAS 297B | ARM |
| UP / DN | NOSE UP / DN | wheel | UP / DN | vertical trim rocker | UP / DN |
| ALT knob | ALT knob | ALT SEL knob | altitude select knob | KAS 297B knob | altitude select knob |
| HDG knob, push SYNC | HDG, push sync | HDG, push sync | HDG bug (KI 525), no sync | HSI heading bug, no sync | HDG bug, no sync |
| SHIFT: CRS, BARO, STD, CRS CTR | CRS/BARO knob | on the G5 / G3X knob | CRS (KI 525), BARO key + knob | HSI course, altimeter | CRS, BARO |

More autopilots in Black Square and A2A aircraft:

| Panel | KFC 325 + KMC 321 (Black Square TBM 850) | King Air (Black Square, verify model) | S-TEC 30 + ST-901 (A2A Comanche) | Century IV (A2A Aerostar) |
| --- | --- | --- | --- | --- |
| AP, HDG, NAV, APR, ALT | yes | yes | HDG, NAV, ALT (no APR key) | yes |
| BC (SHIFT, APR) | BC | BC | none | REV |
| VS, UP / DN | VS, UP / DN | VS, UP / DN | UP / DN command VS | pitch trim wheel |
| FLC | IAS | IAS | none | none |
| YD (SHIFT, FD) | yes | yes | none | option |
| ½ BANK (SHIFT, LVL) | half bank | half bank | none | none |
| GPSS (SHIFT, NAV) | via the navigator | via the navigator | ST-901 GPSS | none |
| ALT knob, ARM | KAS 297B | altitude preselect | none | none |

½ BANK limits the bank angle to about half for a smoother ride. Collins, the KFC 325 and Garmin's
G3000 and GFC 600 (labelled BANK there) have it.

Navigators:

| Panel | G1000 / NXi | GTN 750Xi (TDS) | GNS 530/430 |
| --- | --- | --- | --- |
| D→, MENU, CLR, ENT, FPL, PROC | bezel keys | D→ is a key; the rest are on the touchscreen | bezel keys |
| HOME | none | HOME key | none |
| MSG, NRST, VNAV, TERR, MAP (with SHIFT) | softkeys / pages; hold CLR | touchscreen | MSG key; NRST page; VNAV key (530); hold CLR |
| CDI, OBS | softkeys | touchscreen | bezel keys |
| FMS knob, push CRSR | FMS knob | the GTN knob | right knob, push CRSR |
| RANGE, pan, push PTR | RANGE knob + joystick | map zoom | RNG keys |
| UNIT (SHIFT, HOME) | radio 2 only; the FMS keys stay on the MFD | GTN / second unit | 530 / 430 |

Radios, transponder, audio:

| Panel | G1000 | GTN / GNS | Bendix/King |
| --- | --- | --- | --- |
| Frequency knob, push COM/NAV/ADF | COM and NAV knobs, ADF window | dual knob, C/V push | KX 155/165 knobs, KR 87 |
| COM ⇆, NAV ⇆, ADF ⇆ | flip-flops | flip-flops | flip-flops, KR 87 FRQ |
| 121.5 (SHIFT, COM ⇆) | hold COM ⇆ | hold COM ⇆ | sets COM standby to 121.5 |
| UNIT for radio 2 | COM 2 / NAV 2 tuning box | second unit | second radio |
| Squawk, XPDR mode, IDENT, VFR | GTX 345 | GTX 327 / GTN XPDR | KT 76 |
| MIC / COM / NAV / ADF / DME audio | GMA 1347 | GMA 340 / GMA 35 | KMA 28 |

Partly covered: the KLN 90B (Black Square Bonanza). D→, CLR, ENT, MSG and the FMS knob can map to it
if the aircraft exposes events for them; its cursor keys and second knob have no place on the panel.

Cockpit lighting (SHIFT, FMS knob) maps to the aircraft's panel and flood light dimmers and the cabin or
dome light, where the sim or the aircraft exposes them as events or variables; aircraft with one dimmer
for everything use the outer ring only.

Deliberately not on the panel: volume and squelch, the G1000 softkeys, the KR 87 timer, the KN 62 DME
mode switch and the Collins IND-450 DME, marker audio (MKR), COM 3, KNS 81 RNAV waypoint entry,
weather radar controls (RDR 1150XL), soft ride, autothrottle and the G3000 touch controllers.
