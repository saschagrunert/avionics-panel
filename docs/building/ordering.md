# Ordering

This page orders everything from the JLC group: the board from JLCPCB, the front plate from JLCCNC, the
printed parts from JLC3DP, the screws from JLCMC and a few loose parts from LCSC. Only the feet, a USB-C
cable, some consumables and tools come from a local shop. The JLC group is a suggestion, not a requirement:
the schematic, the Gerbers and the STEP files allow other vendors too, but that route is not documented. The
files are in [production/](../../production/); every name there starts with `avionics-panel-rev1-`, which this
page leaves out (`body.step` is `avionics-panel-rev1-body.step`). What follows the order is in
[Bring-up](bring-up.md).

## Assembly variants

By default JLCPCB fits and solders both sides of the board, so nothing needs soldering at home. Hand-soldering
the through-hole parts (keys, encoders, RANGE control) is the cheaper option for those who like to solder.
Both are Standard assembly orders with the same Gerbers (`gerbers.zip`), the same bottom side and the same
edge rail.

| | Full assembly (default) | Hand-soldering (option) |
| --- | --- | --- |
| JLCPCB assembles | Both sides | The bottom side only: every surface-mount (SMD) part |
| BOM and CPL for JLCPCB | `BOM-full.csv`, `CPL-full.csv`: one BOM (parts list) and one CPL (placement file) for both sides, the only ones to upload | `BOM.csv`, `CPL.csv` |
| Through-hole parts | From JLCPCB's parts library, on both boards ([Parts and stock](#parts-and-stock)) | From LCSC (`THT-LCSC.csv`), soldered by hand with the shell tabs of J1, the USB-C socket ([Hand-soldering](assembly.md#hand-soldering)) |
| Bring-up | Every part is on from the start: a board that turns out dead takes its encoders and RANGE control with it, and the second board is the spare | The encoders and the RANGE control go on last, after the board has been tested |
| Cost | Higher ([cost](#shipping-tax-and-cost)) | The LCSC parts on top of a cheaper board order; 28 keys, three encoders and the RANGE control to solder per board |

## Order step by step

1. Full assembly: first buy the six encoders into your Parts Manager stock, so no other order can take them
   ([Parts and stock](#parts-and-stock)).
2. [JLCCNC](#jlccnc): the plate. It is paid after its review.
3. [JLCPCB](#jlcpcb): the boards. Go through the [placement preview](#placement-preview), then pay.
4. [JLC3DP](#jlc3dp): body, key caps, knobs, light pipes, as an order and a parcel of its own
   ([why](#shipping-tax-and-cost)).
5. [LCSC](#lcsc): the spare keys (or, hand-soldering, the through-hole parts), shipped on its own.
6. JLCMC: the screws from the [shopping list](#shopping-list), an order and a parcel of its own. JLCMC does
   not combine with JLCPCB, JLC3DP or JLCCNC.
7. Locally: the rest of the [shopping list](#shopping-list).
8. Optional, to run the firmware before the boards arrive: the [Pico bench](bring-up.md#pico-bench) parts.

Before paying each order, read the [review questions](#review-questions) and the
[tax lines](#shipping-tax-and-cost). No order waits for another's review.

## Shopping list

Everything one panel needs, with its spare board. An item that only one assembly variant needs names that
variant. Hardware:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Board, assembled | 2 (PCB quantity 5; three come bare) | JLCPCB | [Settings below](#jlcpcb) | The panel; the second is the spare for the first |
| ☐ | Front plate | 1 | JLCCNC | 6061 from 12 mm stock, black anodised, laser marking, orange UV print (UV-cured ink) | [Putting it together](assembly.md#putting-it-together) |
| ☐ | Body | 1 | JLC3DP | [Files and processes](#jlc3dp) | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Key caps | 4 sets of 28 (A to D) | JLC3DP | [Files and processes](#jlc3dp); one set fits, the others are spares | [Choosing the cap set](bring-up.md#choosing-the-cap-set) |
| ☐ | Knobs | 15: 7 for the panel, 8 with a tighter or looser bore | JLC3DP | [Files and processes](#jlc3dp) | [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Light pipes | 2 bars of two pipes (1 bar spare) | JLC3DP | [Files and processes](#jlc3dp) | Step 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Screws | 7 (5 + 2 spare), or JLCMC's pack minimum | JLCMC, either EDDH-C16E1-M3-L8 (10B21 blackened, 8.8) or EDDH-S1W-M3-L8 (A2-70) | M3 x 8 flanged button head, hex socket, ISO 7380-2 | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Spare keys (full assembly) | 5 (LCSC's minimum; 2 needed) | LCSC, C589907 | TE 1-1825910-4 | Trying the cap sets without pulling at a soldered key |
| ☐ | Through-hole parts (hand-soldering) | 1 set (one board; a second for the spare board if wanted) | LCSC, `THT-LCSC.csv` ([LCSC](#lcsc)) | 30 keys, 3 encoders, 1 RANGE control | [Hand-soldering](assembly.md#hand-soldering) |
| ☐ | Feet | 4 | Local | Self-adhesive, up to 10 mm across | Step 6 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | USB-C cable | 1 | Local | Data-capable (a charge-only cable shows no RPI-RP2 drive) | Step 2 of [Flash and test](bring-up.md#flash-and-test) |

Consumables:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Fine sandpaper | 1 sheet | Local | 400 to 1000 grit | The light pipe stubs, step 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Flat file, or coarse sandpaper on a block | 1 | Local | 240 grit | Only for a square corner or a burr at the rail edge, [On arrival](bring-up.md#on-arrival) |
| ☐ | Adhesive tape | A strip | Local | | Only for a loose knob or a drill's depth mark, [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Solder and flux (hand-soldering; full assembly: rework only) | | Local | | [Hand-soldering](assembly.md#hand-soldering), rework |
| ☐ | Solder wick (hand-soldering; full assembly: rework only) | 1 | Local | | Rework |

Tools:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Hex key | 1 | Local | 2 mm | The screws, the plate threads, the BOOT pads |
| ☐ | Two blocks and a cloth | 2 | At home (books, wood) | At least 25 mm high | Face-down work in [Putting it together](assembly.md#putting-it-together) |
| ☐ | Steel rule | 1 | Local | | Squaring the caps, step 1 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Multimeter | 1 | Local | Continuity beeper and diode mode | Steps 1 and 2 of [Flash and test](bring-up.md#flash-and-test), [Hand-soldering](assembly.md#hand-soldering) |
| ☐ | Soldering iron (hand-soldering; full assembly: rework only) | 1 | Local | Temperature controlled | [Hand-soldering](assembly.md#hand-soldering), rework |
| ☐ | Magnifier or loupe | 1 | Local | | [When bring-up fails](bring-up.md#when-bring-up-fails), checking joints |
| ☐ | Drills and a needle file | 3 drills, 1 file | Local | Drills of 6.0, 3.5 and 2.5 mm | Only if a knob bore is too tight, [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Flat-nose pliers | 1 | Local | | Only if a board arrives with its rail, [On arrival](bring-up.md#on-arrival) |

## JLCPCB

4 layers, 1.6 mm, ENIG (gold-plated pads), black solder mask with white silkscreen, via covering Tented
([why](../architecture/electronics.md#solder-mask)); everything else at JLCPCB's defaults (0.3 mm via, 1 oz
outer copper, stackup, PCB quantity 5). Standard assembly, assembly quantity 2 (JLCPCB's minimum); the panel
needs one, the second is the spare. Edge Rails/Fiducials: Added by JLCPCB, with the paid option to remove the
edge rail before delivery. Confirm Parts Placement and Confirm Production File: yes. Check the price and build
time the quote shows for black.

- Full assembly: both sides; `BOM-full.csv` and `CPL-full.csv` (the BOM step must find all 27 lines with
  stock for 2 boards); remark:

  > J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail there. One edge rail of at least
  > 10 mm on the y = 0 edge only, removed before delivery; keep the R3 corners milled. Solder mask: keep the
  > 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask before removing any. The two
  > 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount LEDs: please mill them with R0.5
  > inside corners (1.0 mm router). Solder the mounting lugs of ENC_ALTHDG, ENC_FREQ and ENC_FMS in their
  > slots. Solder the four J1 shell tabs from the top, filling the slots.

- Hand-soldering: bottom side; `BOM.csv` and `CPL.csv` (the BOM step must find all 24 lines with stock for
  2 boards); remark:

  > J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail there. One edge rail of at least
  > 10 mm on the y = 0 edge only, removed before delivery; keep the R3 corners milled. Solder mask: keep the
  > 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask before removing any. The two
  > 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount LEDs: please mill them with R0.5
  > inside corners (1.0 mm router).

The reasons: [edge rails](#edge-rails), [solder mask](../architecture/electronics.md#solder-mask),
[LED cutouts](../architecture/electronics.md#lights), [J1 shell tabs](assembly.md#hand-soldering).

### Edge rails

- J1 overhangs its long edge (y = 60 mm in the Gerbers) by 0.5 mm, so the plug reaches it through the body
  wall: no rail can go there.
- Standard assembly needs edge rails and at least 70 x 70 mm with them. The board is 60 mm wide and the J1
  edge takes no rail, so one rail of at least 10 mm goes on the opposite long edge (y = 0). JLCPCB removes it
  before delivery (a paid option), and the V-cut edge it leaves (scored and snapped, ±0.4 mm) fits the body.
- JLCPCB's default is a 5 mm rail on two opposite edges. If its engineer wants more than the one rail, accept
  any that leaves the J1 edge free; a rail on a short edge leaves a V-cut edge that may need sanding
  ([On arrival](bring-up.md#on-arrival)).
- The R3 corners stay milled: a V-cut square corner does not fit the body.

A board that arrives with a rail anyway: [On arrival](bring-up.md#on-arrival).

### Parts and stock

`BOM-full.csv` lists the through-hole parts for one board; JLCPCB multiplies by the 2 assembled boards. They
come from JLCPCB's own parts library, whose stock is not LCSC's. The parts whose stock is worth a look before
ordering:

| Part | JLC part | Per board |
| --- | --- | --- |
| TE 1-1825910-4 key switch | C589907 | 28 (full assembly only) |
| Bourns PEC11D-4120F-S0015 dual encoder | C19270361 | 3 (full assembly only) |
| Alps RKJXT1F42001 RANGE control | C160841 | 1 (full assembly only) |
| U4: hongjiacheng SRV05-4 ESD (electrostatic discharge) protection array, SOT-23-6 | C7420376 | 1 |
| F1: Bourns MF-NSMF050-2 PTC (resettable) fuse, 0.5 A hold, 1206 | C75464 | 1 |
| LiteOn LTST-C230KSKT yellow LED (the amber SHIFT light) | C125108 | 1 |
| LiteOn LTW-C230DS white LED | C575513 | 1 |

The encoders are the tight part: JLCPCB stocks few of them ([step 1](#order-step-by-step)). If the stock is
short:

- Buy them in through Global Sourcing (a fee and days to weeks).
- Send six as consigned parts.
- Unselect the encoder line (ENC_ALTHDG, ENC_FREQ, ENC_FMS) in the BOM step, which then finds 26 lines, and
  drop the sentence on the encoder lugs from the remark. Buy three encoders per board at LCSC or a Bourns
  distributor and solder them by hand in step 7 of [Flash and test](bring-up.md#flash-and-test)
  ([Hand-soldering](assembly.md#hand-soldering)); skip the encoder checks of steps 3 and 4 of
  [On arrival](bring-up.md#on-arrival).

Any other line short: wait for stock or buy it in through Global Sourcing. Do not substitute another part
number: the footprints and checks are made for these parts.

### Placement preview

Check every assembled part in JLCPCB's placement preview of the bottom side. The preview draws JLC's own
footprint over our pads; the marks below are on our bottom silkscreen, so they hold whichever way round the
preview shows the board. If a part shows turned, correct its rotation there or ask JLCPCB's engineer in the
review; do not order as is.

- LED_SHIFT and LED_UNIT (reverse-mount LEDs over the two cutouts in the board): JLC's cathode (pin 1) at our
  cathode bar, on the side of each LED away from the other, the part centred over its cutout. JLC draws other
  cutouts than ours: go by the pads.
- U1 (RP2040): JLC's pin 1 mark in the corner with our silkscreen corner mark (an L next to the corner pad).
- U2 (flash): JLC's pin 1 mark at our pin 1 dot, next to a corner pad of the row facing away from the RP2040.
- U3 (regulator): JLC's pin 1 mark at our pin 1 dot; the single pin (3, VIN) faces the USB-C socket.
- Y1 (crystal): all four of JLC's pads exactly on ours, long side along the board, JLC's pin 1 at our dot or
  diagonally opposite. Go by the pads and JLC's pin 1, not by a chamfered corner.
- J1 (USB-C): the opening at the board edge (y = 60 mm), the two pegs in the unplated holes and the four shell
  tabs in the slots.
- The 35 diodes (D...): JLC's cathode band on the pad with our silkscreen bar. All 35 bars are at the same end
  of their diodes, towards the short edge nearer J1 and the RP2040 (U1), both named on the bottom silkscreen;
  a band at the other end is a reversed diode. Correct it in the preview (the firmware cannot work round one,
  [why](../architecture/electronics.md#gpio-map)).
- U4 (ESD array, the SOT-23-6 below J1): JLC's pin 1 mark at our pin 1 dot, just beyond the corner pin away
  from J1 on the fuse's side. Turned by 180° it damages the board at the first plug-in
  ([why](../architecture/electronics.md#usb-protection)); step 1 of
  [Flash and test](bring-up.md#flash-and-test) tests for it.
- F1 (the 1206 between U4 and the regulator), the resistors and the capacitors have no polarity: only check
  they sit on their pads.

Full assembly, the top side as well (no polarity marks there; go by the pads and holes):

- ENC_ALTHDG, ENC_FREQ, ENC_FMS: JLC's footprint on all eight pin holes and the two lug slots, its two-pin row
  (the push switch) on the side of the three-pin row towards the J1 edge.
- RANGE: all ten pin holes and JLC's unplated hole on our locating hole; the pattern fits one way only.
- K00 to K36: each footprint on the four holes of its key (either way round is the same switch).

## JLCCNC

Aluminium 6061 from 12 mm stock, CNC, bead blasting and black anodising (matte), laser marking and UV print.
If the form has a UV colour field, pick orange. Files: `plate.step`, `plate-drawing.pdf` (an A3 drawing with
every tolerance, the threads, the finish and the edge breaks) and `plate.dxf` (the marking). Remark:

> 6061 from 12 mm plate, machined to plate-drawing.pdf; all its notes apply, also where they are tighter
> than your general tolerance: boss height 6.55 ±0.05 mm, positions ±0.1 mm, flatness 0.1 mm after anodising,
> pocket depths +0/-0.1 mm, key holes +0.1/-0 mm after anodising, light holes +0.1/-0 mm. The five M3-6H
> threads must take a screw after anodising: mask them or cut them again afterwards. Marking per plate.dxf:
> layer LASER is laser marking, layer UV_AMBER is UV print in your standard orange.

## JLC3DP

| File | Quantity | Process | Part |
| --- | --- | --- | --- |
| `body.step` (`body.stl` if the STEP is refused) | 1 | MJF PA12-HP, dyed black | Body |
| `caps-A.zip`, `caps-B.zip`, `caps-C.zip`, `caps-D.zip` | 1 each | WJP Full Color Resin | Four sets of 28 key caps |
| `knob-outer.step` | 2 | SLA Black Resin | Outer rings of ALT/HDG and FREQ |
| `knob-outer-fms.step` | 1 | SLA Black Resin | Outer ring of FMS (coarser grip) |
| `knob-inner.step` | 3 | SLA Black Resin | Inner knobs |
| `knob-range.step` | 1 | SLA Black Resin | RANGE knob |
| The eight `knob-*-tight.step` and `knob-*-loose.step` | 1 each | SLA Black Resin | Each knob type with a bore 0.2 mm tighter and 0.2 mm looser |
| `lightpipes.step` | 2 | SLA 8001 Resin, transparent, no post-processing | Two light pipes on one bar; the second bar is the spare |

That is 18 files, and the quote page takes 10 per upload: upload them in two batches into the same cart.
Remark:

> Please print every part as designed. Light pipes (lightpipes.step): no sanding and no oil spray; the 2.0 mm
> rods are 4.35 mm long on purpose. Body: the counterbore of the screw column in the middle is open on two
> sides on purpose.

- Key caps: upload the zips, they carry the texture (the OBJ alone prints without legends). JLC3DP asks for
  one part per file, and its connected-parts option is not offered for full colour, so see whether the quote
  or the review accepts 28 separate caps per file. If they insist on single parts, ask their support to accept
  all 28 caps of a set as one file. All four sets are ordered at once: which one fits depends on the print
  ([why](../architecture/mechanics.md#key-caps)).
- Light pipes: JLC3DP sands and oil-sprays 8001 by default, which can break the thin rods, so pick no
  post-processing where the form offers it.

## LCSC

- Full assembly: five keys (C589907; LCSC's minimum, two are needed).
- Hand-soldering: `THT-LCSC.csv` in LCSC's BOM tool, one board's set: 30 keys (28 and two spares, C589907),
  3 encoders (C19270361) and 1 RANGE control (C160841); the `Needed` column gives the count per board. A
  second set for the spare board if wanted. Order the encoders early: LCSC stocks few of them.

## Review questions

Items at or under a shop's published guideline: expect a question in the review. A question not in the table:
accept a change only if it keeps the drawing's notes (JLCCNC) and the remark; otherwise ask for the part as
drawn. If a review ends in a change, change [mech/stack.py](../../mech/stack.py), run
[`./build.sh`](../architecture/generators.md#build), see which files in `production/` changed and upload each
to its shop again.

| Shop | They may question | Answer |
| --- | --- | --- |
| JLCPCB | Black solder mask: 64 dams on the bottom (U1's pads, J1's contacts, C_X2 to R_X) are exactly 0.13 mm, JLCPCB's minimum for black | Check that the confirmed production file still has a dam between every pair of those pads. If any is gone, change the order to green (0.10 mm minimum): the same Gerbers then keep 0.03 mm to spare |
| JLCPCB | The two 2.2 x 2.4 mm cutouts in the outline Gerber | Internal cutouts for reverse-mount LEDs, milled with R0.5 corners (1.0 mm router), not slots |
| JLCPCB | The six plated encoder lug slots, 1.5 x 2.6 mm as on Bourns' drawing, against a slot rule of length at least twice the width | As drawn |
| JLCCNC | The UV legends are 6.1 and 6.7 pt, at the 6 pt minimum | Accept a sample or a little blur |
| JLCCNC | The web, 4.0 ±0.1 mm | Ask for 3.9 to 4.1 mm if they offer a wider tolerance |
| JLCCNC | The pocket floors: 0.95 mm over the RANGE pocket (at least 0.85 mm, the drawing's note), 1.5 mm over the encoder pockets; JLCCNC recommends 0.8 mm | As drawn. Hold the pocket depths +0/-0.1 mm; a thicker floor takes the room over the parts |
| JLCCNC | Threads they cannot mask | Cut them after anodising |
| JLCCNC | The boss height, 6.55 ±0.05 mm | ±0.1 mm is acceptable |
| JLCCNC | Flatness 0.1 mm: milling most of a 12 mm plate off one side can bow it, and JLCCNC publishes no flatness figure | Up to 0.2 mm is acceptable; with the boss height at ±0.1 mm, up to 0.15 mm ([why](../architecture/mechanics.md#light-pipes)). Stress-relieved plate (T651) helps, if they offer it |
| JLC3DP | Light pipes: the 2.0 mm rods are 4.35 mm long, over the pillar guideline (Ø2.0 up to 4 mm) | Print as is. If they refuse: set `top_len` in `PIPE` in `mech/stack.py` to 4.0, run `./build.sh` and upload `lightpipes.step` again |
| JLC3DP | Light pipes: the Ø2.8 bases are under the next guideline entry (Ø3.0 up to 6 mm), the necks are Ø1.0 | Print as is; the order has a spare pair |
| JLC3DP | Body: the counterbore of the middle column is wider than its 4.0 mm bar, so it is open on two sides | Print as is: it is open on purpose, as the remark says. The bar ends keep 1.9 mm of wall beyond the counterbore, over the 1.5 mm for fastener features |
| JLC3DP | Body: 1.6 mm of PA12 between the counterbore seats and the board | Print as is: over the 1.5 mm for fastener features |
| JLC3DP | Outer knobs: the key is 1.4 mm wide, under the 1.5 mm for positioning features | Print as is: a wider key does not clear a narrow shaft slot |
| JLC3DP | Key caps: the tactile bars are 0.5 mm proud (0.8 mm for embossed detail), the set dimples leave 0.91 mm of wall on a worst print | Print as is |

## Shipping, tax and cost

Each JLC shop has its own checkout, but JLC3DP parts can join the JLCPCB cart: keep them out of it. Ship
JLC3DP, JLCMC and LCSC as orders and parcels of their own: added to the JLCPCB parcel, they push it over the
€150 line below.

EU (Germany as the example), for parcels to consumers:

- Every parcel pays the EU handling fee of €2 per customs declaration line, whatever its value.
- Under €150 of goods per shipment, JLC collects the VAT at checkout (IOSS, the EU import scheme). A flat
  customs duty of €3 per tariff line and a carrier's disbursement fee can come on top, so check the tax lines
  before paying.
- A shipment over €150, such as a full assembly JLCPCB order, is cleared on delivery instead, with the
  carrier's fee.

Rough cost of the panel with its spare board, without the rail removal fee: about €370 to 420 with shipping
for full assembly, €290 to 340 with hand-soldering. The screws with their own shipping and the local items
come on top. The quotes give the current figures.
