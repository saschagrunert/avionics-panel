# Ordering

The board, the front plate and the printed parts come from the JLC group: the board from JLCPCB, the front
plate from JLCCNC, the printed parts from JLC3DP. The screws, the feet, a USB-C cable, sandpaper and a few
tools come from a local shop. The JLC group is the only supported route; other shops can work from the same
files, unsupported. The files are in [production/](../../production/): to get them, download the repository
(on GitHub: Code, then Download ZIP). Every name there starts with `avionics-panel-rev1-`, which this page
leaves out (`body.step` is `avionics-panel-rev1-body.step`). What follows the order is in
[Bring-up](bring-up.md).

JLCPCB fits and solders both sides of the board, so nothing needs soldering at home. Soldering the keys, the
encoders and the RANGE control yourself is a cheaper option: [Hand-soldering](hand-soldering.md) has what
differs, the order included. A few fallbacks on these pages change a dimension and build the files again with
`./build.sh`, which needs Nix on Linux (on Windows: WSL 2, [Generators](../architecture/generators.md#build)).

## Order step by step

1. Before spending anything, two quotes:
   - The key caps: their price moves the panel's by several hundred dollars. Upload `caps-A.zip` to JLC3DP's
     quote page with WJP Full Color Resin; that needs no order. JLC3DP prices WJP from $5 a part and asks for
     one model per file, and each zip holds a set of 28 separate caps. If the quote takes the zip as one part,
     the four sets start at about $20; if it counts 28 parts, at $560. Then ask their support: "Will you print
     this file, a set of 28 separate key caps, as it is, and price it as one part?" A no means the higher
     price, or that JLC3DP does not print the file at all; if they want one model per file, the caps go in
     from the `caps-single-*.zip` files ([JLC3DP](#jlc3dp)). Keep their answer for step 5.
   - The plate: upload it to [JLCCNC](#jlccnc) with the settings and the remark there, and submit it with
     review before payment, not automatic payment. JLCCNC answers in hours; nothing is paid until step 3.

   Go on once you have both answers.
2. If JLCPCB has Y1 in stock, skip this step ([Parts and stock](#parts-and-stock)). Otherwise buy the crystals
   for Y1 into your Parts Manager stock through Global Sourcing (ten, or Parts Manager's minimum quantity if
   that is more), and the six encoders from JLCPCB's stock (Parts Manager, Order Parts, JLCPCB Parts; search
   for C19270361; those show at once). Global Sourcing takes 2 to 5 weeks, and step 4 can use the crystals
   only once Parts Manager shows them in stock. Steps 3, 6 and 7 need not wait.
3. [JLCCNC](#jlccnc): pay the plate once its review has passed.
4. [JLCPCB](#jlcpcb): the boards. Go through the [placement preview](#placement-preview).
5. [JLC3DP](#jlc3dp): body, key caps, knobs, light pipes, added to the JLCPCB cart, so they come in one
   parcel with the boards ([why](#shipping-tax-and-cost)). Then pay the cart.
6. Locally: the screws and the rest of the [shopping list](#shopping-list).
7. Optional, to run the firmware before the boards arrive: the [Pico bench](bring-up.md#pico-bench) parts.

Before paying each order, read the [review questions](#review-questions) and the
[tax lines](#shipping-tax-and-cost). Once step 1 has both answers, only the JLCPCB order waits, for Y1
(step 2).

## Shopping list

Everything one panel needs, with its spare board:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Crystals for Y1 | 10, or Parts Manager's minimum | JLCPCB Global Sourcing, ABM8-272-T3 | 12 MHz, Abracon | Y1 on both boards; not needed while JLCPCB stocks it ([Parts and stock](#parts-and-stock)) |
| ☐ | Encoders | 6 | JLCPCB Parts Manager, C19270361 | Bourns PEC11D-4120F-S0015 | Both boards: bought in step 2, or taken from JLCPCB's stock in the BOM step ([Parts and stock](#parts-and-stock)) |
| ☐ | Board, assembled | 2 (PCB quantity 5; three come bare) | JLCPCB | [Settings below](#jlcpcb) | The panel; the second is the spare for the first |
| ☐ | Front plate | 1 | JLCCNC | [Settings below](#jlccnc) | [Putting it together](assembly.md#putting-it-together) |
| ☐ | Body | 1 | JLC3DP | [Files and processes](#jlc3dp) | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Key caps | 4 sets of 28 (A to D) | JLC3DP | [Files and processes](#jlc3dp); one set fits, the others are spares | [Choosing the cap set](bring-up.md#choosing-the-cap-set) |
| ☐ | Knobs | 35: the panel's 7, each in five bores | JLC3DP | [Files and processes](#jlc3dp) | [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Light pipes | 2 bars of two pipes (1 bar spare) | JLC3DP | [Files and processes](#jlc3dp) | Step 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Screws | 7 (5 + 2 spare) | Local; or JLCMC, EDDH-C16E1-M3-L8 (10B21 blackened, 8.8) or EDDH-S1W-M3-L8 (A2-70), its pack minimum, as an order and a parcel of their own | M3 x 8 flanged button head, ISO 7380-2, 2 mm hex socket; steel (black, 8.8 or 10.9) or stainless A2 | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Feet | 4 | Local | Self-adhesive silicone (high friction), up to 10 mm across | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | USB-C cable | 1 | Local | USB-C at the panel, the other end to suit the PC (USB-A or USB-C). Data-capable (a charge-only cable shows no RPI-RP2 drive), straight plug, its overmould at most 12.85 x 7.0 mm ([why](../architecture/mechanics.md#plate-and-body)) | Step 2 of [Flash and test](bring-up.md#flash-and-test), step 5 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Fine sandpaper | 1 sheet | Local | 400 to 1000 grit | The light pipe stubs, step 2 of [Putting it together](assembly.md#putting-it-together); a knob that rubs, [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Hex key | 1 | Local | 2 mm | The screws, the plate threads, the BOOT pads |
| ☐ | Two blocks and a cloth | 2 | At home (books, wood) | At least 25 mm high | Face-down work in [Putting it together](assembly.md#putting-it-together) |
| ☐ | Steel rule | 1 | Local | | Squaring the caps, step 1 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Multimeter | 1 | Local | Continuity beeper and diode mode | Steps 1 and 2 of [Flash and test](bring-up.md#flash-and-test) |

Only if something does not fit or fails:

| ☐ | Item | Shop, part | For |
| --- | --- | --- | --- |
| ☐ | Flat file, or 240 grit sandpaper on a block | Local | A square corner, a burr or a V-cut edge that does not fit the body, [On arrival](bring-up.md#on-arrival); a body wall that touches the plate, step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Flat-nose pliers | Local | A board that arrives with its rail, [On arrival](bring-up.md#on-arrival) |
| ☐ | Drill, 4.2 mm, and a pin vice to turn it by hand | Local | A screw that does not pass a body hole, step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Magnifier or loupe | Local | [When bring-up fails](bring-up.md#when-bring-up-fails); the joints after [soldering](hand-soldering.md#soldering) |
| ☐ | Soldering iron (temperature controlled), solder, flux, solder wick | Local | Rework ([Soldering](hand-soldering.md#soldering)) |

## JLCPCB

4 layers, 1.6 mm, ENIG (gold-plated pads), black solder mask with white silkscreen, via covering Tented
([why](../architecture/electronics.md#solder-mask)); everything else at JLCPCB's defaults (0.3 mm via, 1 oz
outer copper, stackup, PCB quantity 5). Standard assembly of both sides, assembly quantity 2 (JLCPCB's
minimum); the panel needs one, the second is the spare. Edge Rails/Fiducials: Added by JLCPCB, with the option
to remove the edge rail before delivery (it costs extra). Confirm Parts Placement and Confirm Production File:
yes. PCB Remark:

> J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail there. One edge rail of at least
> 10 mm on the y = 0 edge only, removed before delivery; keep the R3 corners milled. Solder mask: keep the
> 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask before removing any. The two
> 2.2 x 2.6 mm internal cutouts in the outline are for reverse-mount LEDs: please mill them with R0.5
> inside corners (1.0 mm router).

Upload `gerbers.zip`, then `BOM-full.csv` (the parts list) and `CPL-full.csv` (the placement file): one of
each, for both sides. The BOM step must find all 28 lines with stock for 2 boards, the encoders and Y1 from
your own parts if step 2 bought them ([Parts and stock](#parts-and-stock)). Under Advanced Options set PCBA
Remark to Yes and enter:

> Solder the mounting lugs of ENC_ALTHDG, ENC_FREQ and ENC_FMS in their slots. Solder the four J1 shell
> tabs from the top, filling the slots. All through-hole joints by hand soldering: no wave or selective
> soldering over the bottom side.

The reasons: [edge rails](#edge-rails), [solder mask](../architecture/electronics.md#solder-mask),
[LED cutouts](../architecture/electronics.md#lights), [encoder lugs](hand-soldering.md#soldering),
[J1's shell tabs and the through-hole joints](../architecture/electronics.md#through-hole-parts).

### Edge rails

- No rail on the J1 edge (y = 60 mm in the Gerbers): J1 overhangs it by 0.5 mm, so that the plug reaches it
  through the body wall. If JLCPCB insists on one there, accept only one joined by mouse bites behind a
  routed gap, never a V-cut: its blade would run under J1.
- One rail of at least 10 mm on the opposite long edge (y = 0): Standard assembly needs rails and 70 x 70 mm
  with them, and the board is 60 mm wide. JLCPCB removes it before delivery; the V-cut edge it leaves (scored
  and snapped, ±0.4 mm), or a mouse-bite edge filed flat, fits the body. A rail on a short edge as well leaves
  a V-cut edge there that may need sanding.
- In the confirmed production file: the rail on y = 0, the J1 edge free and the corners milled round (R3; a
  V-cut square corner does not fit the body). JLCPCB's default is a 5 mm rail on two opposite edges, the J1
  edge included.

A board that arrives with a rail anyway: [On arrival](bring-up.md#on-arrival).

### Parts and stock

`BOM-full.csv` lists the parts for one board; JLCPCB multiplies by the 2 assembled boards. The BOM step shows
any line that is short. Two parts are worth a look before ordering.

Y1 (Abracon ABM8-272-T3, a 12 MHz crystal, C20625731) is rarely in stock at JLCPCB, and a board without it
has no USB. JLCPCB places at least five of this part and adds attrition on top (the part's order guide on
JLCPCB's parts page gives both). While the parts page shows that many in stock, order the boards at once.
Otherwise:

- Buy the crystals through Global Sourcing first (Parts Manager, Order Parts, Global Sourcing Parts; search
  for ABM8-272-T3): ten, or the minimum quantity Parts Manager shows for the part if that is more. Own stock
  that falls short of what the BOM step needs is not used at all. The review takes 1 to 3 business days and
  the buying 9 to 20, and a kind of part may carry a $20 inspection fee. In the BOM step, Y1 must then come
  from your own parts, like the encoders; if the step does not find the crystals, match them by the part
  number ABM8-272-T3.
- A stocked 12 MHz 3225 crystal, picked in the BOM step in place of C20625731, saves the wait, but
  Raspberry Pi's guide asks for extensive testing of any change to its crystal circuit. The part to take
  first is C21900467 (13 pF): its datasheet gives at most 40 ohm of ESR (series resistance; the less, the
  more surely the crystal starts), under the 50 ohm of Raspberry Pi's design. C5310728 (10 pF), C362368
  (9 pF) and C50430 (10 pF) are listed with 60 to 80 ohm. Check in the placement preview that the part's four
  pads land on ours, and on the first board that RPI-RP2 appears at every plug-in (step 2 of
  [Flash and test](bring-up.md#flash-and-test)).

The encoders (Bourns PEC11D-4120F-S0015, C19270361) are the other tight part: JLCPCB stocks few of them,
which is why step 2 buys them ahead while the crystals take their weeks. If the stock is short, buy them in
through Global Sourcing (2 to 5 weeks, with the same inspection fee).

Any other line short: wait for stock or buy it in through Global Sourcing. Do not substitute another part
number: the footprints and checks are made for these parts.

### Placement preview

In JLCPCB's placement preview every part must sit on its own pads, and the parts below the right way round.
The preview draws JLC's own footprint over our pads; the marks are on our bottom silkscreen, so they hold
whichever way round the preview shows the board. If a part shows turned, correct its rotation there or ask
JLCPCB's engineer in the review; do not order as is.

- LED_SHIFT and LED_UNIT (reverse-mount LEDs over the two cutouts in the board): JLC's cathode (pin 1) at our
  cathode bar, on the side of each LED away from the other, the part centred over its cutout. JLC draws other
  cutouts than ours: go by the pads.
- The 35 diodes (D...): JLC's cathode band on the pad with our silkscreen bar. All 35 bars are at the same end
  of their diodes, towards the short edge nearer J1 and the RP2040 (U1), both named on the bottom silkscreen;
  a band at the other end is a reversed diode, which the firmware cannot work round
  ([why](../architecture/electronics.md#gpio-map)).
- U1 (RP2040): JLC's pin 1 mark in the corner with our silkscreen corner mark (an L next to the corner pad).
- U2 (flash), U3 (regulator) and U4 (ESD array, the SOT-23-6 below J1): JLC's pin 1 mark at our pin 1 dot.
  U3's single pin faces J1. U4 turned by 180° damages the board at the first plug-in
  ([why](../architecture/electronics.md#usb-protection)); step 1 of
  [Flash and test](bring-up.md#flash-and-test) tests for it.
- Q_UNIT (the UNIT light's transistor, the SOT-23 12 mm from that light towards the J1 edge): JLC's single pin
  towards the light.
- Y1 (crystal): all four of JLC's pads exactly on ours, long side along the board, JLC's pin 1 at our dot or
  diagonally opposite. Go by the pads and JLC's pin 1, not by a chamfered corner.
- J1 (USB-C): the opening at the board edge (y = 60 mm), the two pegs in the unplated holes and the four shell
  tabs in the slots.
- The top side (no polarity marks there): each footprint on all its holes. ENC_ALTHDG, ENC_FREQ and ENC_FMS
  have their two-pin row (the push switch) on the side of the three-pin row towards the J1 edge; the RANGE
  control's pattern fits one way only; a key is the same switch either way round.

## JLCCNC

JLCCNC's order form overrides the drawing, so set these on it (the labels may differ a little):

- Material: aluminium 6061.
- Surface finish: black anodising, the option with bead blasting (anodising alone comes without it).
- Threads: yes (five M3).
- Tightest tolerance: ±0.05 mm, for the boss height. At the default, ISO 2768-m, the bosses come ±0.2 mm.
- Marking: laser marking and UV printing. The UV colour is the amber the drawing gives (sRGB 217 / 164 / 65,
  CMYK 0 / 24 / 70 / 15); where the form only lists colour names, pick orange.
- Appearance: Strict, which keeps rack marks and scratches off the marked front face. Standard allows four
  rack marks and five scratches wherever they do not affect assembly.

Files: `plate.step`, `plate.pdf` (the drawing, with every tolerance, the threads, the finish, the edge
breaks and a front view of the marking with the amber's colour values) and `plate.dxf` (the marking).
JLCCNC pairs a model with the drawings of the same name and takes the threads, the marking and the
tolerances from them. The plate's line must then show both `plate.pdf` and `plate.dxf`; if it shows one,
upload `plate.step`, `plate.pdf` and `plate.dxf` together as one zip. Remark:

> Machined to the drawing avionics-panel-rev1-plate.pdf; all its notes and tolerances apply, also where they
> are tighter than your general tolerance. Threads M3-6H, plugged through blasting and anodising (your
> standard under M5); they must gauge afterwards. Anodising rack contacts on the back face, on the boss end
> faces or inside the pockets; never on the front face, the outline or the key holes. Marking per
> avionics-panel-rev1-plate.dxf: layer LASER is laser marking, layer UV_AMBER is UV print in the amber the
> drawing gives.

## JLC3DP

| File | Quantity | Process | Part |
| --- | --- | --- | --- |
| `body.step` | 1 | MJF PA12-HP, dyed black | Body |
| `caps-A.zip`, `caps-B.zip`, `caps-C.zip`, `caps-D.zip` | 1 each | WJP Full Color Resin | Four sets of 28 key caps |
| `knob-outer-1.step` to `knob-outer-5.step` | 2 each | SLA Black Resin | Outer rings of ALT/HDG and FREQ |
| `knob-outer-fms-1.step` to `knob-outer-fms-5.step` | 1 each | SLA Black Resin | Outer ring of FMS (coarser grip) |
| `knob-inner-1.step` to `knob-inner-5.step` | 3 each | SLA Black Resin | Inner knobs |
| `knob-range-1.step` to `knob-range-5.step` | 1 each | SLA Black Resin | RANGE knob |
| `lightpipes.step` | 2 | SLA 8001 Resin, translucent | Two light pipes on one bar; the second bar is the spare |

That is 26 files, and the quote page takes 10 per upload: upload them in three uploads into the same cart.
Each knob comes in five bores, 1 the tightest and 5 the loosest, every one in the panel's quantity: 35 knobs
([why](../architecture/mechanics.md#knobs)). Black Resin is the material of that name, not JLC Black Resin or
Imagine Black Resin, and WJP Full Color Resin is not Full-Color Tough Resin. Remark:

> Please print every part as designed. Knobs: supports on the bottom faces only, none inside the bores and
> recesses; support marks sanded flush, no more than 0.05 mm proud. The 0.9 mm dimples in the knobs'
> undersides number the bores: keep them open, do not fill them. Light pipes
> (avionics-panel-rev1-lightpipes.step): rods up, supports on the bar only; no sanding and no oil spray; the
> 2.0 mm rods are 4.45 mm long on purpose. Body: the counterbore of the screw column in the middle is open on
> two sides on purpose.

- Key caps: upload the zips, they carry the texture (the OBJ alone prints without legends). All four sets are
  ordered at once: which one fits depends on the print ([why](../architecture/mechanics.md#key-caps)). Step 1
  of [Order step by step](#order-step-by-step) settles their price first.
- Key caps, one model per file, if JLC3DP asks for it in step 1: in place of `caps-A.zip` to `caps-D.zip`,
  unzip `caps-single-A.zip` to `caps-single-D.zip`. Each holds a set's 28 caps as one zip per cap
  (`cap-A-01-AP.zip` and so on); upload those zips, quantity 1 each, 10 per upload. With the other 22 files
  that is 134 orders, more than the 50 JLC3DP takes in one batch: in step 1, ask their support how to place
  them so they ship together with the boards.
- Light pipes: JLC3DP sands and oil-sprays transparent 8001 by default, which can break the thin rods;
  translucent gets no sanding, and the remark asks for none.

## Review questions

Some items are at or under a shop's published guideline, so expect questions in the reviews. These have an
answer of their own:

| Shop | They may question | Answer |
| --- | --- | --- |
| JLCPCB | Black solder mask: 64 dams on the bottom (U1's pads, J1's contacts, C_X2 to R_X) are exactly 0.13 mm, JLCPCB's minimum for black | Check that the confirmed production file still has a dam between every pair of those pads. If any is gone, change the order to green (0.10 mm minimum): the same Gerbers then keep 0.03 mm to spare |
| JLCCNC | The UV legends: capitals 1.55 and 1.7 mm high (6.1 and 6.7 pt), at the 6 pt minimum, and 0.7 mm from the key holes | Accept a sample or a little blur. Keep them where drawn: they leave 0.5 mm beyond the hole's edge break for the print's register. If JLCCNC will not print that close to a hole: laser marking for those legends, in the laser's one tone |
| JLCCNC | The laser marking: the line between the AUDIO and RADIO keys passes 0.575 mm from the key holes beside it, where JLCCNC usually keeps 3 mm from an edge | Mark it as drawn. Where the line meets a hole's edge break it is only cosmetic: accept it fading or ending short there |
| JLCCNC | The pocket floors: 0.95 mm over the RANGE pocket (at least 0.85 mm, the drawing's note), 1.5 mm over the encoder pockets; JLCCNC recommends 0.8 mm, and over 1.5 mm where the part is bead blasted | As drawn. Hold the pocket depths +0/-0.1 mm (a thicker floor takes the room over the parts) and the flatness after blasting. If they will not blast it as drawn: anodising without blasting (tool marks may then show); never a thicker floor, and no blasting of the front face alone, which can bow the plate |
| JLCCNC | The boss height, 6.55 ±0.05 mm | ±0.1 mm is acceptable |
| JLCCNC | Flatness 0.1 mm: milling most of a 12 mm plate off one side can bow it, and JLCCNC publishes no flatness figure | Up to 0.2 mm is acceptable; with the boss height at ±0.1 mm, up to 0.15 mm ([why](../architecture/mechanics.md#light-pipes)). Stress-relieved plate (T651) helps, if they offer it |
| JLC3DP | Light pipes: the 2.0 mm rods are 4.45 mm long, over the pillar guideline (Ø2.0 up to 4 mm) | Print as is. If they refuse: set `top_len` in `PIPE` in `mech/stack.py` to 4.0, run `./build.sh` and upload `lightpipes.step` again |

The answer to every other question is "as drawn" (JLC3DP: "print as is"). Accept a change only if it keeps
the drawing's notes (JLCCNC) and the remarks. If a review does end in a change, change
[mech/stack.py](../../mech/stack.py), run [`./build.sh`](../architecture/generators.md#build), see which files
in `production/` changed and upload each to its shop again.

## Shipping, tax and cost

Each JLC shop has its own checkout. JLC3DP parts can join the JLCPCB cart, so put them there: they then ship
with the boards, once Y1 has arrived and the boards are built. The plate comes as a parcel of its own, with
its own shipping and import fees. If step 2 was skipped, you can leave it unpaid until step 5 and pay it in
the same cart; whether it then ships with the boards shows at checkout. Screws from JLCMC come as an order
and a parcel of their own, which costs more to ship than the screws do.

In the EU, up to €150 of goods the shop collects the VAT at checkout (IOSS); a flat customs duty of €3 per
kind of goods is added at checkout or paid on delivery, with any carrier's fee. Over €150 the standard duty
replaces the flat one, and VAT, duty and the carrier's fee are paid on delivery. Where the checkout offers DDP
shipping (delivered duty paid), pick it: it collects all of these at checkout.

JLCPCB's share with the spare board: its fees for assembling both sides come to about $130 and its parts to
about $80, about $50 of that the six encoders, before the boards, shipping, VAT and the carrier's fee. The
plate, the printed parts and the local items, the screws among them, come on top; the quotes give the totals,
and the key caps move them most (step 1). Allow 2 to 5 weeks for Y1 through Global Sourcing before the JLCPCB
order can be placed, then at least 4 days of Standard assembly; at least 72 hours of build time for the key
caps (WJP).
