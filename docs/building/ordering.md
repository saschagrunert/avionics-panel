# Ordering

This page orders everything from the JLC group: the board from JLCPCB, the front plate from JLCCNC, the
printed parts from JLC3DP, the screws from JLCMC and a few loose parts from LCSC. Only the feet, some
consumables and tools come from a local shop. The JLC group is a suggestion, not a requirement: the schematic,
the Gerbers and the STEP files allow other vendors too, but that route is not documented. The files are in
[production/](../../production/); every name there starts with `avionics-panel-rev1-`, which this page leaves
out (`body.step` is `avionics-panel-rev1-body.step`). What follows the order is in [Bring-up](bring-up.md).

## Assembly variants

By default JLCPCB fits and solders both sides of the board, so nothing needs soldering at home. Hand-soldering
the through-hole parts (keys, encoders, RANGE control) is the cheaper option for those who like to solder.
Both use the same Gerbers and the same bottom side.

| | Full assembly (default) | Hand-soldering (option) |
| --- | --- | --- |
| JLCPCB assembly | Standard, both sides | Economic, bottom side only (all SMD) |
| Files for JLCPCB | `gerbers.zip`, `BOM-full.csv`, `CPL-full.csv`: one BOM (parts list) and one CPL (placement file) for both sides, the only ones to upload | `gerbers.zip`, `BOM.csv`, `CPL.csv` |
| Through-hole parts | From JLCPCB's parts library, on both boards ([Parts and stock](#parts-and-stock)) | From LCSC (`THT-LCSC.csv`), soldered by hand with the J1 shell tabs ([Hand-soldering](assembly.md#hand-soldering)) |
| Edge rails | One, removed by JLCPCB before delivery ([Edge rails](#edge-rails)) | None |
| Bring-up | Every part is on from the start: a board that turns out dead takes its encoders and RANGE control with it, and the second board is the spare | The encoders and the RANGE control go on last, after the board has been tested |
| Cost | Higher ([cost](#shipping-tax-and-cost)) | The LCSC parts on top of a cheaper board order; 28 keys, three encoders and the RANGE control to solder per board |

## Order step by step

1. Full assembly: buy the six encoders into your Parts Manager stock now
   ([Parts and stock](#parts-and-stock)).
2. [JLCCNC](#jlccnc): the plate. It is paid after its review.
3. [JLCPCB](#jlcpcb): the boards. Go through the [placement preview](#placement-preview), then pay.
4. [JLC3DP](#jlc3dp): body, key caps, knobs, light pipes, as an order and a parcel of its own (hand-soldering:
   it may share the JLCPCB cart, see [shipping](#shipping-tax-and-cost)).
5. [LCSC](#lcsc): the spare keys (or, hand-soldering, the through-hole parts), shipped on its own.
6. JLCMC: the screws from the [shopping list](#shopping-list), an order and a parcel of its own. JLCMC does
   not combine with JLCPCB, JLC3DP or JLCCNC.
7. Locally: the rest of the [shopping list](#shopping-list).
8. Optional, to run the firmware before the boards arrive: the [Pico bench](bring-up.md#pico-bench) parts.

Before paying each order, read the [review questions](#review-questions) and the
[tax lines](#shipping-tax-and-cost). Place the orders one after the other; none depends on another's review,
and none of the answers there changes another order's files.

## Shopping list

Everything one panel needs, with its spare board. An item that only one assembly variant needs names that
variant. Hardware:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Board, assembled | 2 (of 5 bare) | JLCPCB | [Settings below](#jlcpcb) | The panel; the second is the spare for the first |
| ☐ | Front plate | 1 | JLCCNC | 6061 from 12 mm stock, black anodised, laser marking, orange UV print | [Putting it together](assembly.md#putting-it-together) |
| ☐ | Body | 1 | JLC3DP | [Files and processes](#jlc3dp) | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Key caps | 4 sets of 28 (A to D) | JLC3DP | [Files and processes](#jlc3dp); one set fits, the others are spares | [Choosing the cap set](bring-up.md#choosing-the-cap-set) |
| ☐ | Knobs | 15: 7 for the panel, 8 with a tighter or looser bore | JLC3DP | [Files and processes](#jlc3dp) | [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Light pipes | 2 bars of two pipes (1 bar spare) | JLC3DP | [Files and processes](#jlc3dp) | Step 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Screws | 7 (5 + 2 spare), or JLCMC's pack minimum | JLCMC, EDDH-C16E1-M3-L8 (10B21 blackened, 8.8) or EDDH-S1W-M3-L8 (A2-70) | M3 x 8 flanged button head, hex socket, ISO 7380-2 | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Spare keys (full assembly) | 5 (LCSC's minimum; 2 needed) | LCSC, C589907 | TE 1-1825910-4 | Trying the cap sets without pulling at a soldered key |
| ☐ | Through-hole parts (hand-soldering) | 1 set (one board; a second for the spare board if wanted) | LCSC, `THT-LCSC.csv` ([LCSC](#lcsc)) | 30 keys, 3 encoders, 1 RANGE control | [Hand-soldering](assembly.md#hand-soldering) |
| ☐ | Feet | 4 | Local | Self-adhesive, up to 10 mm across | Step 6 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | USB-C cable | 1 | Local | Data-capable (a charge-only cable shows no RPI-RP2 drive) | [Bring-up](bring-up.md) |

Consumables:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Fine sandpaper | 1 sheet | Local (or LCSC C5124393, 1000 grit) | 400 to 1000 grit | The light pipe stubs, step 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Flat file, or coarse sandpaper on a block | 1 | Local | 240 grit | Only for a square corner or a burr at the rail edge, [On arrival](bring-up.md#on-arrival) |
| ☐ | Adhesive tape | A strip | Local | | Only for a loose knob or a drill's depth mark, [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Solder and flux (hand-soldering; full assembly: rework only) | | Local | | [Hand-soldering](assembly.md#hand-soldering), rework |
| ☐ | Solder wick (hand-soldering; full assembly: rework only) | 1 | Local (or LCSC C92547, 2 mm, or C88005, 3 mm) | | Rework |

Tools:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Hex key | 1 | Local | 2 mm | The screws, the plate threads, the BOOT pads |
| ☐ | Two blocks and a cloth | 2 | At home (books, wood) | At least 25 mm high | Face-down work in [Putting it together](assembly.md#putting-it-together) |
| ☐ | Steel rule | 1 | Local | | Squaring the caps, step 1 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Multimeter | 1 | Local | Continuity beeper and diode mode | Steps 1 and 2 of [Flash and test](bring-up.md#flash-and-test) |
| ☐ | Soldering iron (hand-soldering; full assembly: rework only) | 1 | Local | Temperature controlled | [Hand-soldering](assembly.md#hand-soldering), rework |
| ☐ | Magnifier or loupe | 1 | Local (or LCSC C106807, 7.5x, or C90740, 3.5x) | | [When bring-up fails](bring-up.md#when-bring-up-fails), checking joints |
| ☐ | Drills and a needle file | 6.0, 3.5 and 2.5 mm | Local | | Only if a knob bore is too tight, [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Flat-nose pliers | 1 | Local | | Only if a board arrives with its rail, [On arrival](bring-up.md#on-arrival) |

The LCSC numbers for home items are an alternative only: every line of an EU import pays a €2 handling fee
([shipping](#shipping-tax-and-cost)), so a cheap item costs more in fees than in goods. Many of LCSC's USB-C
cables are charge-only, and their listings rarely say so: buy the cable where its data lines are stated.

## JLCPCB

4 layers, 1.6 mm, ENIG, black solder mask with white silkscreen, via covering Tented
([why](../architecture/electronics.md#solder-mask)); everything else at JLCPCB's defaults (0.3 mm via, 1 oz
outer copper, stackup, PCB quantity 5). Assembly quantity 2 (JLCPCB's minimum); the panel needs one, the
second is the spare. Confirm Parts Placement and Confirm Production File: yes.

- Full assembly: Standard assembly, both sides; `BOM-full.csv` and `CPL-full.csv` (the BOM step must find all
  27 lines with stock for 2 boards); Edge Rails/Fiducials: Added by JLCPCB, with JLCPCB's paid option to
  remove the edge rail before delivery; remark:

  > J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail there. One edge rail of at least
  > 10 mm on the y = 0 edge only, removed before delivery; keep the R3 corners milled. Solder the mounting
  > lugs of ENC_ALTHDG, ENC_FREQ and ENC_FMS in their slots. Solder the four J1 shell tabs from the top,
  > filling the slots. Solder mask: keep the 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask
  > before removing any. The two 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount LEDs:
  > please mill them with R0.5 inside corners (1.0 mm router).

- Hand-soldering: Economic assembly, bottom side; `BOM.csv` and `CPL.csv`; Edge Rails/Fiducials: None;
  remark:

  > J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design. No edge rails, please. Solder mask: keep
  > the 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask before removing any. The two
  > 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount LEDs: please mill them with R0.5
  > inside corners (1.0 mm router).

The reasons: [edge rails](#edge-rails), [J1 shell tabs](assembly.md#hand-soldering),
[solder mask](../architecture/electronics.md#solder-mask),
[LED cutouts](../architecture/electronics.md#lights).

JLCPCB lists black among its standard colours at standard pricing, but its build-time table is for green:
check the price and build time the quote shows for black.

### Edge rails

- J1 overhangs its long edge (y = 60 mm in the Gerbers) by 0.5 mm, so the plug reaches it through the body
  wall: no rail can go there. Every other bottom-side part keeps 3.7 mm from the edges.
- Full assembly: Standard assembly needs 70 x 70 mm and the board is 60 mm wide, so one rail of at least 10 mm
  goes on the opposite long edge (y = 0). JLCPCB removes it before delivery (a paid option), and the V-cut
  edge it leaves (±0.4 mm) fits the body.
- Hand-soldering: JLCPCB lists rails as not needed for Economic assembly, and the milled outline fits the body
  as delivered. Should their engineer add rails anyway, accept if the J1 edge stays free.
- The R3 corners stay milled: a V-cut square corner does not fit the body.

A board that arrives with a rail anyway: [On arrival](bring-up.md#on-arrival).

### Parts and stock

`BOM-full.csv` lists the through-hole parts for one board; JLCPCB multiplies by the 2 assembled boards. They
are extended parts in JLCPCB's own library, whose stock is not LCSC's. The parts whose stock is worth a look
before ordering:

| Part | JLC part | Library | Per board |
| --- | --- | --- | --- |
| TE 1-1825910-4 key switch | C589907 | Extended | 28 (full assembly only) |
| Bourns PEC11D-4120F-S0015 dual encoder | C19270361 | Extended | 3 (full assembly only) |
| Alps RKJXT1F42001 RANGE control | C160841 | Extended | 1 (full assembly only) |
| U4: hongjiacheng SRV05-4 ESD array, SOT-23-6 | C7420376 | Preferred extended | 1 |
| F1: Bourns MF-NSMF050-2 PTC fuse, 0.5 A hold, 1206 | C75464 | Extended | 1 |
| LiteOn LTST-C230KSKT yellow LED (the amber SHIFT light) | C125108 | Extended | 1 |
| LiteOn LTW-C230DS white LED | C575513 | Extended | 1 |

The encoders are the tight part: JLCPCB stocks few of them. Buy the six into your Parts Manager stock as soon
as you order: the assembly takes them from there, so no other order can take them first. If the stock is
short:

- Buy them in through Global Sourcing (a fee and days to weeks).
- Send six as consigned parts.
- Unselect the three encoder lines in the BOM step and solder the encoders by hand (buy them at LCSC or a
  Bourns distributor; [Hand-soldering](assembly.md#hand-soldering)).

JLCPCB charges a fee per part type: in Economic assembly for each extended part (the RP2040, the flash, the
crystal, J1, F1 and the two LEDs), in Standard assembly for every part type, basic parts included. JLCPCB
moves parts between the classes, so go by the quote.

### Placement preview

Check every assembled part in JLCPCB's placement preview of the bottom side. The preview draws JLC's own
footprint over our pads; the marks below are on our bottom silkscreen, so they hold whichever way round the
preview shows the board. If a part shows turned, correct its rotation there or ask JLCPCB's engineer in the
review; do not order as is. JLCPCB's reading of bottom rotations can change (the CPL's convention:
[Electronics](../architecture/electronics.md#assembly-data)).

- LED_SHIFT and LED_UNIT (reverse-mount LEDs over the two cutouts in the board): JLC's cathode, pin 1, at our
  cathode bar, which is on the side of each LED away from the other one (LED_SHIFT's bar away from LED_UNIT,
  LED_UNIT's away from LED_SHIFT; that holds whether or not the preview shows the bottom mirrored), the part
  centred over its cutout. JLC's footprints draw other cutouts than ours (a round hole for the white one,
  with its pads reaching into it, a smaller square for the amber one): go by the pads and our cutout.
- U1 (RP2040): JLC's pin 1 mark in the corner with our silkscreen corner mark (an L next to the corner pad).
- U2 (flash): JLC's pin 1 mark at our pin 1 dot, next to a corner pad of the row facing away from the RP2040.
- U3 (regulator): JLC's pin 1 mark at our pin 1 dot; the single pin (3, VIN) faces the USB-C socket.
- Y1 (crystal): all four of JLC's pads exactly on ours, long side along the board, JLC's footprint pin 1 at
  our dot (diagonally opposite is fine too: pins 1 and 3 swap). Go by the pads and the footprint's pin 1,
  not by a chamfered corner: Abracon allows the ABM8's chamfer on pin 1, 3 or 4. A part turned by 90°
  shows up as pads off ours.
- J1 (USB-C): the opening at the board edge (y = 60 mm), the two pegs in the unplated holes and the four shell
  tabs in the slots.
- The 35 diodes (D...): every cathode band of JLC's footprint on the pad with our silkscreen bar, the pad
  towards the electronics strip (for the five RANGE diodes that is away from the RANGE control). Correct any
  reversed diode in the preview: the firmware cannot work round one
  ([why](../architecture/electronics.md#gpio-map)).
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

The UV print may blur slightly at the edges; laser marking alone would make every legend grey. The SHIFT cap
legend is printed in an amber that approximates JLCCNC's orange.

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

Items at or under a shop's published guideline: expect a question in the review. Should a review end in a
change, change [mech/stack.py](../../mech/stack.py), run `./build.sh`
([Generators](../architecture/generators.md#build)), see which files in `production/` changed and upload each
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
| JLC3DP | Body: the counterbore of the middle column is wider than its 4.0 mm bar, so it is open on two sides; JLC3DP has not reviewed this shape | Print as is. The bar ends keep 1.9 mm of wall beyond the counterbore, over the 1.5 mm for fastener features |
| JLC3DP | Body: 1.6 mm of PA12 between the counterbore seats and the board | Print as is: over the 1.5 mm for fastener features |
| JLC3DP | Outer knobs: the key is 1.4 mm wide, under the 1.5 mm for positioning features | Print as is: a wider key does not clear a narrow shaft slot |
| JLC3DP | Key caps: the tactile bars are 0.5 mm proud (0.8 mm for embossed detail), the set dimples leave 0.91 mm of wall on a worst print | Print as is |

## Shipping, tax and cost

The JLC shops share one account but each has its own checkout, payment by PayPal, card or Google Pay.

- JLC3DP items can join the JLCPCB cart and be paid together. JLCCNC is paid separately after its review.
- LCSC combines its parcel with a JLC order only if that order is shipped to LCSC's Hong Kong warehouse
  (chosen as the address at the JLC checkout, and not changeable after). Ship LCSC on its own: added to a JLC
  parcel it also pushes it over the €150 line below.
- EU (Germany as the example), for parcels to consumers:
  - Every parcel pays the EU handling fee of €2 per customs declaration line, whatever its value.
  - Under €150 of goods per shipment, JLC collects the VAT at checkout (IOSS, the EU import scheme). A flat
    customs duty of €3 per tariff line (an interim rule, until 2028-07-01) and a carrier's disbursement fee
    can come on top, so check the tax lines before paying.
  - A shipment over €150 is cleared on delivery instead, with the carrier's fee.
  - Full assembly: the JLCPCB order alone is over €150, so ship JLC3DP on its own. Hand-soldering: JLC3DP may
    share the JLCPCB cart if both together stay under €150 of goods.

Rough cost of the panel with its spare board, without the rail removal fee: about €370 to 420 with shipping
for full assembly, €250 to 300 with hand-soldering, plus the screws with their own shipping and the local
items. The quotes give the current figures.
