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

1. First buy at least ten crystals for Y1 into your Parts Manager stock through Global Sourcing, and with
   full assembly the six encoders from JLCPCB's stock (those show at once). Global Sourcing takes 2 to 5
   weeks, and step 4 can use the crystals only once Parts Manager shows them in stock
   ([Parts and stock](#parts-and-stock)). Steps 2, 3, 7 and 8 need not wait.
2. [JLCCNC](#jlccnc): the plate. It is paid after its review.
3. JLCMC: the screws from the [shopping list](#shopping-list), as an order and a parcel of their own. JLCMC
   does not combine with the other JLC shops.
4. [JLCPCB](#jlcpcb): the boards. Go through the [placement preview](#placement-preview).
5. [JLC3DP](#jlc3dp): body, key caps, knobs, light pipes, added to the JLCPCB cart, so they come in one
   parcel with the boards ([why](#shipping-tax-and-cost)). Quote one cap zip first ([why](#jlc3dp)). Then
   pay the cart.
6. [LCSC](#lcsc): the spare keys (or, hand-soldering, the through-hole parts), joined to the JLCPCB order at
   LCSC's checkout.
7. Locally: the rest of the [shopping list](#shopping-list).
8. Optional, to run the firmware before the boards arrive: the [Pico bench](bring-up.md#pico-bench) parts.

Before paying each order, read the [review questions](#review-questions) and the
[tax lines](#shipping-tax-and-cost). No order waits for another's review; only the JLCPCB order waits for Y1
(step 1).

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
| ☐ | Feet | 4 | Local | Self-adhesive silicone (high friction), up to 10 mm across | Step 6 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | USB-C cable | 1 | Local | Data-capable (a charge-only cable shows no RPI-RP2 drive), straight plug, its overmould at most 12.85 x 7.0 mm ([why](../architecture/mechanics.md#plate-and-body)) | Step 2 of [Flash and test](bring-up.md#flash-and-test), step 4 of [Putting it together](assembly.md#putting-it-together) |

Consumables:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Fine sandpaper | 1 sheet | Local | 400 to 1000 grit | The light pipe stubs, step 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Flat file, or coarse sandpaper on a block | 1 | Local | 240 grit | Only for a square corner or a burr at the rail edge, [On arrival](bring-up.md#on-arrival) |
| ☐ | Adhesive tape | A strip | Local | | Only for a drill's depth mark, [Fitting the knobs](assembly.md#fitting-the-knobs) |
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
| ☐ | Drills, a hand chuck or T-handle tap wrench that holds a 6 mm drill, a needle file | 4 drills, 1 holder, 1 file | Local | Drills of 6.0, 4.2, 3.5 and 2.5 mm | Only if a knob bore is too tight ([Fitting the knobs](assembly.md#fitting-the-knobs)) or a screw does not pass a body hole (step 4 of [Putting it together](assembly.md#putting-it-together)) |
| ☐ | Flat-nose pliers | 1 | Local | | Only if a board arrives with its rail, [On arrival](bring-up.md#on-arrival) |

## JLCPCB

4 layers, 1.6 mm, ENIG (gold-plated pads), black solder mask with white silkscreen, via covering Tented
([why](../architecture/electronics.md#solder-mask)); everything else at JLCPCB's defaults (0.3 mm via, 1 oz
outer copper, stackup, PCB quantity 5). Standard assembly, assembly quantity 2 (JLCPCB's minimum); the panel
needs one, the second is the spare. Edge Rails/Fiducials: Added by JLCPCB, with the paid option to remove the
edge rail before delivery. Confirm Parts Placement and Confirm Production File: yes. Check the price and build
time the quote shows for black, and in the Gerber viewer the inner layers' order: Inner Layer 1 (layer 2) must
be `avionics-In1_Cu.g2` (GND) and Inner Layer 2 `avionics-In2_Cu.g3` (3V3). PCB Remark, in both variants:

> J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail there. One edge rail of at least
> 10 mm on the y = 0 edge only, removed before delivery; keep the R3 corners milled. Solder mask: keep the
> 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask before removing any. The two
> 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount LEDs: please mill them with R0.5
> inside corners (1.0 mm router).

- Full assembly: both sides; `BOM-full.csv` and `CPL-full.csv` (the BOM step must find all 28 lines with
  stock for 2 boards). Under Advanced Options set PCBA Remark to Yes and enter:

  > Solder the mounting lugs of ENC_ALTHDG, ENC_FREQ and ENC_FMS in their slots. Solder the four J1 shell
  > tabs from the top, filling the slots. All through-hole joints by hand soldering: no wave or selective
  > soldering over the bottom side.

  JLCPCB's capabilities page says through-hole parts are wave soldered, but 113 of the through-hole pads are
  1.1 to 1.5 mm from a bottom-side SMD pad (each key pin from its diode), where selective soldering asks for
  5 mm. Hand soldering costs $0.0164 a joint, 152 joints a board, plus $3.58 an order.
- Hand-soldering: bottom side; `BOM.csv` and `CPL.csv` (the BOM step must find all 25 lines with stock for
  2 boards); no PCBA remark.

The reasons: [edge rails](#edge-rails), [solder mask](../architecture/electronics.md#solder-mask),
[LED cutouts](../architecture/electronics.md#lights), [J1 shell tabs](assembly.md#hand-soldering).

### Edge rails

- J1 overhangs its long edge (y = 60 mm in the Gerbers) by 0.5 mm, so the plug reaches it through the body
  wall: no rail can go there.
- Standard assembly needs edge rails and at least 70 x 70 mm with them. The board is 60 mm wide and the J1
  edge takes no rail, so one rail of at least 10 mm goes on the opposite long edge (y = 0). JLCPCB removes it
  before delivery (a paid option), and the V-cut edge it leaves (scored and snapped, ±0.4 mm), or a
  mouse-bite edge with small nubs to file flat, fits the body.
- JLCPCB's default is a 5 mm rail on two opposite edges, here the J1 edge too, and its assembly terms want
  part bodies at least 2.5 mm from the board edge. Check the panel in the confirmed production file: one rail
  on y = 0 only, the J1 edge free, the R3 corners milled.
- If its engineer wants more than the one rail, accept any that leaves the J1 edge free; a rail on a short
  edge leaves a V-cut edge that may need sanding ([On arrival](bring-up.md#on-arrival)). If JLCPCB insists on
  a rail on the J1 edge, accept only one joined by mouse bites behind a routed gap, never a V-cut: its blade
  would run under J1.
- The R3 corners stay milled: a V-cut square corner does not fit the body.

A board that arrives with a rail anyway: [On arrival](bring-up.md#on-arrival).

### Parts and stock

`BOM-full.csv` lists the through-hole parts for one board; JLCPCB multiplies by the 2 assembled boards. They
come from JLCPCB's own parts library, whose stock is not LCSC's. The parts whose stock is worth a look before
ordering:

| Part | JLC part | Per board |
| --- | --- | --- |
| Y1: Abracon ABM8-272-T3 12 MHz crystal | C20625731 | 1 |
| TE 1-1825910-4 key switch | C589907 | 28 (full assembly only) |
| Bourns PEC11D-4120F-S0015 dual encoder | C19270361 | 3 (full assembly only) |
| Alps RKJXT1F42001 RANGE control | C160841 | 1 (full assembly only) |
| U4: SRV05-4 ESD (electrostatic discharge) protection array, SOT-23-6 (hongjiacheng at JLCPCB, R+O at LCSC) | C7420376 | 1 |
| F1: Bourns MF-NSMF050-2 PTC (resettable) fuse, 0.5 A hold, 1206 | C75464 | 1 |
| LiteOn LTST-C230KSKT yellow LED (the amber SHIFT light) | C125108 | 1 |
| LiteOn LTW-C230DS white LED | C575513 | 1 |

Y1 is rarely in stock at JLCPCB or LCSC, and a board without it has no USB. Before ordering, buy at least ten
ABM8-272-T3 through Global Sourcing (Parts Manager, Order Parts, Global Sourcing Parts; search for
ABM8-272-T3). JLCPCB places at least five of this part and adds attrition on top (the part's order guide on
JLCPCB's parts page gives both), and own stock that falls short of what the BOM step needs is not used at
all: ten leaves room for both. The review takes 1 to 3 business days and the buying 9 to 20. In the BOM step,
Y1 must then come from your own parts; if the step does not find them, match them by the part number
ABM8-272-T3. Consigning crystals bought elsewhere also works, but it needs a declared-value form,
a courier to JLCPCB's Hong Kong warehouse and a handling fee of at least $10. Take a stocked 12 MHz 3225
crystal instead only if you test it on the first board: C5310728 (10 pF, 60 ohm), C362368 (9 pF, 60 ohm) and
C50430 (YXC, 10 pF, 80 ohm) have more ESR than the 50 ohm of Raspberry Pi's design, whose guide asks for
extensive testing of any change to its crystal circuit. Pick one in the BOM step in place of C20625731, check
in the placement preview that its four pads land on ours, and on the first board that RPI-RP2 appears at every
plug-in (step 2 of [Flash and test](bring-up.md#flash-and-test)).

The encoders are the other tight part: JLCPCB stocks few of them. If the stock is short:

- Buy them in through Global Sourcing (2 to 5 weeks; switch-type parts may carry a $20 inspection fee).
- Unselect the encoder line (ENC_ALTHDG, ENC_FREQ, ENC_FMS) in the BOM step, which then finds 27 lines, and
  drop the sentence on the encoder lugs from the PCBA remark. Buy three encoders per board at LCSC or a
  Bourns distributor and solder them by hand in step 7 of [Flash and test](bring-up.md#flash-and-test)
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
- Q_UNIT (the UNIT light's transistor, the SOT-23 12 mm from that light towards the J1 edge): JLC's single pin
  (3, the drain) towards the light, its pin 1 (the gate) on the pad next to the resistor beside it
  (R_UNIT_PD).
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
every tolerance, the threads, the finish, the edge breaks, the machining order and where the anodising racks
may touch) and `plate.dxf` (the marking). Remark:

> 6061 from 12 mm plate, machined to plate-drawing.pdf; all its notes apply, also where they are tighter
> than your general tolerance: boss height 6.55 ±0.05 mm, positions ±0.1 mm, flatness 0.1 mm after anodising,
> pocket depths +0/-0.1 mm, key holes +0.1/-0 mm after anodising, light holes +0.1/-0 mm. Machining order:
> face the front first, then machine the back. The five M3-6H threads must take a screw after anodising:
> mask them or cut them again afterwards. Anodising rack contacts in one of the M3 threads (cut it again
> afterwards), on the back face, on the boss end faces or inside the pockets; never on the front face, the
> outline or the key holes.
> Marking per plate.dxf: layer LASER is laser marking, layer UV_AMBER is UV print in your standard orange.

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
| `lightpipes.step` | 2 | SLA 8001 Resin, translucent | Two light pipes on one bar; the second bar is the spare |

That is 18 files, and the quote page takes 10 per upload: upload them in two batches into the same cart.
Black Resin is the material of that name, not JLC Black Resin or Imagine Black Resin. Remark:

> Please print every part as designed. Light pipes (lightpipes.step): no sanding and no oil spray; the 2.0 mm
> rods are 4.45 mm long on purpose. Body: the counterbore of the screw column in the middle is open on two
> sides on purpose.

- Key caps: upload the zips, they carry the texture (the OBJ alone prints without legends). JLC3DP asks for
  one part per file, offers no connected parts for full colour and prices WJP from $5 a part, so quote one zip
  before ordering. If the quote counts its 28 caps as 28 parts (the four sets then come to at least $560), ask
  their support to take all 28 caps of a set as one part. All four sets are ordered at once: which one fits
  depends on the print ([why](../architecture/mechanics.md#key-caps)).
- Light pipes: JLC3DP sands and oil-sprays transparent 8001 by default, which can break the thin rods;
  translucent gets no sanding, and the remark asks for none.

## LCSC

- Full assembly: five keys (C589907; LCSC's minimum, two are needed).
- Hand-soldering: `THT-LCSC.csv` in LCSC's BOM tool, one board's set: 30 keys (28 and two spares, C589907),
  3 encoders (C19270361) and 1 RANGE control (C160841); the `Needed` column gives the count per board. A
  second set for the spare board if wanted. Order the encoders early: LCSC stocks few of them.

## Review questions

Items at or under a shop's published guideline: expect a question in the review. A question not in the table:
accept a change only if it keeps the drawing's notes (JLCCNC) and the remarks; otherwise ask for the part as
drawn. If a review ends in a change, change [mech/stack.py](../../mech/stack.py), run
[`./build.sh`](../architecture/generators.md#build), see which files in `production/` changed and upload each
to its shop again.

| Shop | They may question | Answer |
| --- | --- | --- |
| JLCPCB | Black solder mask: 64 dams on the bottom (U1's pads, J1's contacts, C_X2 to R_X) are exactly 0.13 mm, JLCPCB's minimum for black | Check that the confirmed production file still has a dam between every pair of those pads. If any is gone, change the order to green (0.10 mm minimum): the same Gerbers then keep 0.03 mm to spare |
| JLCPCB | The two 2.2 x 2.4 mm cutouts in the outline Gerber | Internal cutouts for reverse-mount LEDs, milled with R0.5 corners (1.0 mm router), not slots |
| JLCPCB | The six plated encoder lug slots, 1.5 x 2.6 mm as on Bourns' drawing, against a slot rule of length at least twice the width | As drawn |
| JLCPCB | J1 overhangs its edge by 0.5 mm, against the assembly terms' 2.5 mm from a part body to the board edge | As designed: no rail on that edge ([Edge rails](#edge-rails)) |
| JLCCNC | The UV legends: capitals 1.55 and 1.7 mm high (6.1 and 6.7 pt), at the 6 pt minimum, and 0.7 mm from the key holes, where the margin is usually 3 mm | Accept a sample or a little blur. Keep them where drawn: they leave 0.5 mm beyond the hole's edge break for the print's register |
| JLCCNC | The web, 4.0 ±0.1 mm | Ask for 3.9 to 4.1 mm if they offer a wider tolerance |
| JLCCNC | The pocket floors: 0.95 mm over the RANGE pocket (at least 0.85 mm, the drawing's note), 1.5 mm over the encoder pockets; JLCCNC recommends 0.8 mm, and over 1.5 mm where the part is bead blasted | As drawn. Hold the pocket depths +0/-0.1 mm (a thicker floor takes the room over the parts) and the flatness after blasting. If they will not blast it as drawn: low-pressure blasting of the front face only, or (your call) anodising without blasting; never a thicker floor |
| JLCCNC | Threads they cannot mask | Cut them after anodising |
| JLCCNC | The boss height, 6.55 ±0.05 mm | ±0.1 mm is acceptable |
| JLCCNC | Flatness 0.1 mm: milling most of a 12 mm plate off one side can bow it, and JLCCNC publishes no flatness figure | Up to 0.2 mm is acceptable; with the boss height at ±0.1 mm, up to 0.15 mm ([why](../architecture/mechanics.md#light-pipes)). Stress-relieved plate (T651) helps, if they offer it |
| JLC3DP | Light pipes: the 2.0 mm rods are 4.45 mm long, over the pillar guideline (Ø2.0 up to 4 mm) | Print as is. If they refuse: set `top_len` in `PIPE` in `mech/stack.py` to 4.0, run `./build.sh` and upload `lightpipes.step` again |
| JLC3DP | Light pipes: the Ø2.8 bases are under the next guideline entry (Ø3.0 up to 6 mm), the necks are Ø1.0 | Print as is; the order has a spare pair |
| JLC3DP | Body: the counterbore of the middle column is wider than its 4.0 mm bar, so it is open on two sides | Print as is: it is open on purpose, as the remark says. The bar ends keep 1.9 mm of wall beyond the counterbore, over the 1.5 mm for fastener features |
| JLC3DP | Body: 1.6 mm of PA12 between the counterbore seats and the board | Print as is: over the 1.5 mm for fastener features |
| JLC3DP | Outer knobs: the key is 1.4 mm wide, under the 1.5 mm for positioning features | Print as is: a wider key does not clear a narrow shaft slot |
| JLC3DP | Key caps: the tactile bars are 0.5 mm proud (0.8 mm for embossed detail), the set dimples leave 0.91 mm of wall on a worst print | Print as is |

## Shipping, tax and cost

Each JLC shop has its own checkout. JLC3DP parts can join the JLCPCB cart, and LCSC orders can join a JLCPCB
order at LCSC's checkout; JLCMC combines with neither, so the screws come as a parcel of their own. JLCPCB
recommends one shipment over €150, so put the JLC3DP parts in the JLCPCB cart and join the LCSC order to it;
the plate and the screws come on their own. The JLC3DP parts then ship with the boards, once Y1 has arrived
and the boards are built.

EU (Germany as the example), for parcels to consumers: under €150 of goods, IOSS collects only the VAT; the
€3 customs duty per item category and the €2 handling fee per declaration line are paid on delivery with the
carrier's disbursement fee (DHL: 2 %, at least €15), unless the checkout offers DDP shipping, which collects
them all. Pick DDP where offered. Over €150, the parcel is cleared on delivery at the standard tariff, with VAT
and the carrier's fee.

JLCPCB's share with full assembly and the spare board: its published fees alone come to about $133 and its
parts to about $82 ($49.60 of them the six encoders), before the boards, shipping, VAT and the carrier's fee.
With hand-soldering JLCPCB assembles one side, so its setup fee is about $25.56 and its stencil $8.21 instead
of $51.12 and $16.42. The plate, the printed parts, the screws and the local items come on top. The quotes
give the totals. Allow 2 to 5 weeks for Y1 through Global Sourcing before the JLCPCB order can be placed, then
at least 4 days of Standard assembly; at least 72 hours of build time for the key caps (WJP).
