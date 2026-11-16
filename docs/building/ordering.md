# Ordering

The board, the front plate and the printed parts come from the JLC group: the board from JLCPCB, the front
plate from JLCCNC, the printed parts from JLC3DP. The screws, the feet, a USB-C cable, sandpaper and a few
tools come from a local shop (the screws also from JLCMC); with the hand-soldering option, the keys, the
encoders and the RANGE control come from LCSC. The JLC group is the only supported route; other shops can work
from the same files, unsupported. The files are in [production/](../../production/): to get them, download the
repository (on GitHub: Code, then Download ZIP). Every name there starts with `avionics-panel-rev1-`, which
this page leaves out (`body.step` is `avionics-panel-rev1-body.step`). What follows the order is in
[Bring-up](bring-up.md).

JLCPCB fits and solders both sides of the board, so nothing needs soldering at home. Soldering the keys, the
encoders and the RANGE control yourself is a cheaper option: [Hand-soldering](hand-soldering.md) has what
differs, the order included. A few fallbacks on these pages change a dimension and build the files again with
`./build.sh`, which needs Nix on Linux (on Windows: WSL 2, [Generators](../architecture/generators.md#build)).

## Order step by step

First freeze what you order: every file from one download, so from one commit. Take a release with a version
tag if there is one (on GitHub: Releases, its Source code zip; not the rolling Latest build), otherwise Code,
Download ZIP. Write down the commit: `firmware/version.py` in the download names it, its date and short hash.
Keep with it what each shop confirms (JLCPCB's production file and placement preview, the reviewed files of
JLCCNC and JLC3DP) and every review answer you accept.

1. Before spending anything, three quotes:
   - The key caps: their price moves the panel's by over a hundred dollars. Upload `caps-B.zip` to JLC3DP's
     quote page with Full Color Resin (WJP), Color Multicolor; that needs no order. JLC3DP prices WJP at about
     €4.77 a part (Surface Finish No) and asks for one model per file, and the zip holds a set of 28 separate
     caps. If the quote takes the zip as one part, the set and the three gauge caps come to about €20; if it
     counts each cap as a part (31), about €150. Then ask their support: "Will you print this file, a set of
     28 separate key caps, as it is, and price it as one part?" A no means the higher price, or that JLC3DP
     does not print the file at all; if they want one model per file, the caps go in from `caps-single-B.zip`
     ([JLC3DP](#jlc3dp)). Joining the caps on runners is no way round it: JLC3DP's connected-parts printing
     excludes WJP. Keep their answer for step 5.
   - The plate: upload it to [JLCCNC](#jlccnc) with the settings and the remark there, and submit it with
     review before payment, not automatic payment. JLCCNC answers in hours; nothing is paid until step 3.
     Ask them how long the reviewed quote holds, since the plate may wait for Y1 (step 2).
   - The knobs, sanded or not: upload the 24 knob files to JLC3DP's quote page twice, once with Surface
     Finish No and once with Yes: Sanding, General Sanding, and compare the two totals; that needs no order
     either. Unsanded saves the sanding fee and costs about an hour of sanding at home; sanded comes with the
     support marks gone. Choose by the difference, and order them as [JLC3DP](#jlc3dp) says for that choice.

   Go on once you have all three answers.
2. If JLCPCB has Y1 in stock, skip this step ([Parts and stock](#parts-and-stock)). Otherwise buy the crystals
   for Y1 into your Parts Manager stock through Global Sourcing (ten, or Parts Manager's minimum quantity if
   that is more), and the encoders from JLCPCB's stock (Parts Manager, Order Parts, JLCPCB Parts; search for
   C19270361; those show at once): as many as the part's order guide on JLCPCB's parts page asks for two
   boards (six, plus any attrition): own stock short of what the BOM step needs is not used at all. Global
   Sourcing takes 2 to 5 weeks, and step 4 can use the crystals only once Parts Manager shows them in stock.
   Steps 3, 6 and 7 need not wait.
3. [JLCCNC](#jlccnc): once the plate's review has passed, leave it unpaid until step 5 and pay it in the
   JLCPCB cart, so it ships with the boards; whether it does shows at checkout
   ([Shipping, tax and cost](#shipping-tax-and-cost)). JLCCNC's help (How to combine orders) has the way:
   from JLCCNC, open JLCPCB's order page through JLCCNC's navigation bar for steps 4 and 5, and the cart
   lists the plate with the boards and the printed parts; tick "All" there to pay them together. If step 2
   has to wait longer than the reviewed quote holds, or the plate should not wait, pay it here instead: it
   then comes as a parcel of its own.
4. [JLCPCB](#jlcpcb): the boards. Go through the [placement preview](#placement-preview).
5. [JLC3DP](#jlc3dp): body, key caps, knobs, light pipes, added to the JLCPCB cart, so they come in one
   parcel with the boards ([why](#shipping-tax-and-cost)). Then pay the cart, "All" ticked (step 3).
6. Locally: the screws and the rest of the [shopping list](#shopping-list).
7. Optional, to run the firmware before the boards arrive: the [Pico bench](bring-up.md#pico-bench) parts.

Before paying each order, read the [review questions](#review-questions) and the
[tax lines](#shipping-tax-and-cost). Once step 1 has both answers, only the JLCPCB cart (boards, plate and
printed parts) waits, for Y1 (step 2). To pay less:

- One parcel: the plate and the printed parts paid in the JLCPCB cart (steps 3 and 5) ship with the boards.
- Duty paid: pick DDP (delivered duty paid) shipping at checkout, the cheapest DDP line, so no duty, VAT or
  carrier's fee comes on delivery.
- Coupons: before paying, look at JLCPCB's coupons (there is usually a monthly one for SMT assembly) and at
  JLCCNC's and JLC3DP's (Account, Coupons).

## Shopping list

Everything one panel needs, with its spare board:

| ☐ | Item | Qty | Shop, part | Spec | For |
| --- | --- | --- | --- | --- | --- |
| ☐ | Crystals for Y1 | 10, or Parts Manager's minimum | JLCPCB Global Sourcing, ABM8-272-T3 | 12 MHz, Abracon | Y1 on both boards; not needed while JLCPCB stocks it ([Parts and stock](#parts-and-stock)) |
| ☐ | Encoders | 6, plus what the order guide adds for attrition | JLCPCB Parts Manager, C19270361 | Bourns PEC11D-4120F-S0015 | Both boards: bought in step 2, or taken from JLCPCB's stock in the BOM step ([Parts and stock](#parts-and-stock)) |
| ☐ | Board, assembled | 2 (PCB quantity 5; three come bare) | JLCPCB | [Settings below](#jlcpcb) | The panel; the second is the spare for the first |
| ☐ | Front plate | 1 | JLCCNC | [Settings below](#jlccnc) | [Putting it together](assembly.md#putting-it-together) |
| ☐ | Body | 1 | JLC3DP | [Files and processes](#jlc3dp) | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Key caps | 28 + 3: set B in full, and the AP cap of sets A, C and D as gauges | JLC3DP | [Files and processes](#jlc3dp) | [Choosing the cap set](bring-up.md#choosing-the-cap-set) |
| ☐ | Knobs | 42: the panel's 7, each in six bores | JLC3DP | [Files and processes](#jlc3dp) | [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Light pipes | 6 (3 + 3 spare) | JLC3DP | [Files and processes](#jlc3dp) | Step 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Screws | 7 (5 + 2 spare) | Local; or JLCMC, EDDH-C16E1-M3-L8 (10B21 blackened, 8.8) or EDDH-S1W-M3-L8 (A2-70), its pack minimum, as an order and a parcel of their own | M3 x 8 flanged button head, ISO 7380-2, 2 mm hex socket; steel (black, 8.8 or 10.9) or stainless A2 | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Feet | 4 | Local | Self-adhesive silicone (high friction), up to 10 mm across | Step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | USB-C cable | 1 | Local | USB-C at the panel, the other end to suit the PC (USB-A or USB-C). Data-capable (a charge-only cable shows no RPI-RP2 drive). Any straight USB-C plug within the USB-C spec fits (its limit is 12.85 x 7.0 mm, [why](../architecture/mechanics.md#plate-and-body)); avoid angled plugs and chunky or braided boots | Step 2 of [Flash and test](bring-up.md#flash-and-test), step 5 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Fine sandpaper | 1 sheet | Local | 400 to 1000 grit | The light pipes' support nubs, step 2 of [Putting it together](assembly.md#putting-it-together); the knobs' support marks and a knob that rubs, [Fitting the knobs](assembly.md#fitting-the-knobs) |
| ☐ | Hex key | 1 | Local | 2 mm | The screws, the plate threads, the BOOT pads |
| ☐ | Two blocks and a cloth | 2 | At home (books, wood) | At least 25 mm high | Face-down work in [Putting it together](assembly.md#putting-it-together) |
| ☐ | Steel rule | 1 | Local | | Squaring the caps and checking the board's bow, steps 1 and 2 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Multimeter | 1 | Local | Continuity beeper and diode mode | Steps 1 and 2 of [Flash and test](bring-up.md#flash-and-test) |

Only if something does not fit or fails:

| ☐ | Item | Shop, part | For |
| --- | --- | --- | --- |
| ☐ | Flat file or 240 grit sandpaper on a block | Local | A square corner, a burr or a V-cut edge that does not fit the body, [On arrival](bring-up.md#on-arrival); a body wall that touches the plate, step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Flat-nose pliers | Local | A board that arrives with its rail, [On arrival](bring-up.md#on-arrival) |
| ☐ | Drill, 4.2 mm, and a pin vice to turn it by hand | Local | A screw that does not pass a body hole, step 4 of [Putting it together](assembly.md#putting-it-together) |
| ☐ | Magnifier or loupe | Local | [When bring-up fails](bring-up.md#when-bring-up-fails); the joints after [soldering](hand-soldering.md#soldering) |
| ☐ | Soldering iron (temperature controlled), solder, flux, solder wick | Local | Rework ([Soldering](hand-soldering.md#soldering)) |

## JLCPCB

Layers 4, PCB Thickness 1.6 mm, Surface Finish ENIG, PCB Color Black (white silkscreen), Via Covering
Tented ([why](../architecture/electronics.md#solder-mask)); everything else at JLCPCB's defaults (0.3 mm via,
1 oz outer copper, stackup, PCB quantity 5). Standard assembly of both sides, assembly quantity 2 (JLCPCB's
minimum); the panel needs one, the second is the spare. Edge Rails/Fiducials: Added by JLCPCB. The form has no
option to remove the rail: the PCB remark asks for it, and JLCPCB adds the fee for it in the review. Confirm
Parts Placement and Confirm Production File: yes. PCB Remark:

> J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail there. One edge rail of at least
> 10 mm on the y = 0 edge only, removed before delivery; keep the R3 corners milled. Solder mask: keep the
> 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask before removing any. The three
> 2.2 x 2.6 mm internal cutouts in the outline are for reverse-mount LEDs: please mill them with R0.5
> inside corners (1.0 mm router).

Upload `gerbers.zip`, then `BOM-full.csv` (the parts list) and `CPL-full.csv` (the placement file): one of
each, for both sides. The BOM step must find all 29 lines with stock for 2 boards, the encoders and Y1 from
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

- LED_SHIFT, LED_UNIT and LED_FREQ (reverse-mount LEDs over the three cutouts in the board): JLC's cathode
  (pin 1) at our cathode bar, west of LED_SHIFT and east of the other two (seen from the top), the part centred
  over its cutout. JLC draws other cutouts than ours: go by the pads.
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
- Surface finish: "Bead blasting + Anodizing", black. Anodising alone is still blasted, at 120 mesh, unless
  the remark says no bead blasting.
- Threads: yes (five M3).
- Tightest tolerance: ±0.05 mm, for the boss height. At the default, ISO 2768-m, the bosses come ±0.2 mm.
- Marking: "+ Add finish", then "Laser marking"; no UV printing. The laser leaves one light grey on the black
  anodising, so there is no colour to choose.
- Appearance: Standard, which costs least. It allows up to four rack marks, where JLCCNC picks so that they do
  not affect assembly, and up to five scratches under 10 mm anywhere, the front face included. The remark
  asks for the rack marks off the front face and the boss end faces, which Standard does not promise. Strict,
  the level above, keeps rack marks and scratches off the cosmetic surfaces, the laser-marked face among
  them, for a price.

Files: `plate.step`, `plate.pdf` (the drawing, with every tolerance, the threads, the finish, the edge
breaks and a front view of the marking) and `plate.dxf` (the marking).
JLCCNC pairs a model with the drawings of the same name and takes the threads, the marking and the
tolerances from them. The plate's line must then show both `plate.pdf` and `plate.dxf`; if it shows one,
upload `plate.step`, `plate.pdf` and `plate.dxf` together as one zip. Remark:

> Machined to the drawing avionics-panel-rev1-plate.pdf; all its notes and tolerances apply, also where they
> are tighter than your general tolerance. Threads M3-6H, plugged through blasting and anodising (your
> standard under M5); they must gauge afterwards. Anodising rack contacts on the back face, inside the
> pockets or in the bores of the three encoder holes and the RANGE hole; never on the boss end faces, the
> front face, the outline or the key holes. The front face is the cosmetic surface. Marking per
> avionics-panel-rev1-plate.dxf: layer LASER is laser marking, no UV print; layer CUT (the outline and the
> through holes) is for reference only.

## JLC3DP

| File | Quantity | Process | Part |
| --- | --- | --- | --- |
| `body.step` | 1 | MJF PA12-HP, dyed black | Body |
| `caps-B.zip` | 1 | Full Color Resin (WJP), Color Multicolor, Surface Finish No | The 28 key caps, set B |
| `cap-A-01-AP.zip`, `cap-C-01-AP.zip`, `cap-D-01-AP.zip`, from `caps-single-A.zip`, `caps-single-C.zip` and `caps-single-D.zip` | 1 each | Full Color Resin (WJP), Color Multicolor, Surface Finish No | Gauge caps: the AP cap of sets A, C and D |
| `knob-outer-1.step` to `knob-outer-6.step` | 2 each | SLA Black Resin, Surface Finish No | Outer rings of ALT/HDG and FREQ |
| `knob-outer-fms-1.step` to `knob-outer-fms-6.step` | 1 each | SLA Black Resin, Surface Finish No | Outer ring of FMS (coarser grip) |
| `knob-inner-1.step` to `knob-inner-6.step` | 3 each | SLA Black Resin, Surface Finish No | Inner knobs |
| `knob-range-1.step` to `knob-range-6.step` | 1 each | SLA Black Resin, Surface Finish No | RANGE knob |
| `lightpipes.step` | 6 | SLA 8001 Resin, translucent, Surface Finish No | One light pipe: the panel's three and three spare |

That is 30 files: the body, the set's zip and the three gauge caps (28 + 3 key caps), the 24 knob files and
the light pipe, ordered 6 times. The quote page takes 10 per upload: upload them in three uploads into the
same cart. The cart submits up to 30 together (JLC3DP's FAQ; its order guide says 50), so the 30 go in one
submission. Each knob comes in six bores, 1 the tightest and 6 the loosest, every one in the panel's quantity:
42 knobs ([why](../architecture/mechanics.md#knobs)). Black Resin is the material of that name, not JLC Black
Resin or Imagine Black Resin, and Full Color Resin (WJP) is not Full-Color Tough Resin. Remark:

> Please print every part as designed. Knobs: supports on the bottom faces only, none inside the bores and
> recesses; leave the support marks on, they are sanded at home. No sanding, blasting, oil or coating: the
> bores hold the knobs by friction and stay as printed. The 1.0 mm dimples in the knobs' undersides number the
> bores: keep them open, do not fill them. The 1.2 mm wide, 0.25 mm deep groove along the RANGE knobs' bores
> (avionics-panel-rev1-knob-range-*.step) is on purpose: keep it open, no supports in it. Light pipes
> (avionics-panel-rev1-lightpipes.step): upright, rod up, supports on the base's bottom face only; no sanding
> and no oil spray; the 2.0 mm rod is 4.45 mm long on purpose. Body: the counterbore of the screw column in
> the middle is open on two sides on purpose. Key caps: no oil spray or coating; the sockets hold the caps by
> friction and stay as printed.

- Key caps: upload the zips, they carry the texture (the OBJ alone prints without legends). Which of the four
  sets fits depends on the print ([why](../architecture/mechanics.md#key-caps)): set B fits a print without
  error best, and the three gauge caps, the AP cap of each other set, show on the bench whether a neighbour
  fits better ([Choosing the cap set](bring-up.md#choosing-the-cap-set)). Unzip the gauge caps' zips from
  `caps-single-A.zip`, `caps-single-C.zip` and `caps-single-D.zip`. Step 1 of
  [Order step by step](#order-step-by-step) settles their price first.
- Key caps, one model per file, if JLC3DP asks for it in step 1: in place of `caps-B.zip`, unzip
  `caps-single-B.zip`. It holds the set's 28 caps as one zip per cap (`cap-B-01-AP.zip` and so on); upload
  those zips, quantity 1 each, 10 per upload. With the three gauge caps and the other 26 files that is 57
  orders, more than the cart submits together (30, or 50 by the order guide): two submissions. In step 1,
  ask their support how to place them so they ship together with the boards.
- Knobs: Surface Finish No, unless the quote in step 1 made sanding worth its price. With No the support
  marks stay on the bottom faces, and the builder sands them flush
  ([Fitting the knobs](assembly.md#fitting-the-knobs)). The bores stay as printed, whose grip the six sizes
  are made for ([why](../architecture/mechanics.md#knobs)).
- Knobs sanded instead: Surface Finish Yes: Sanding, General Sanding (the form's default for Black Resin),
  which sands, bead blasts and oils them, in the four knob rows of the table. In the remark, replace "leave
  the support marks on, they are sanded at home. No sanding, blasting, oil or coating: the bores hold the
  knobs by friction and stay as printed." with "support marks sanded flush, no more than 0.05 mm proud. The
  bores hold the knobs by friction: leave them as printed, with no sanding, blasting, oil or coating inside;
  General Sanding is for the outside only." If their review says they cannot keep it out of the bores: No.
- Light pipes: set Surface Finish to No. The form's default is Oil Spraying for transparent 8001 and Fine
  Sanding for translucent, and either can break the thin rods; the remark asks for neither.

## Review questions

Some items are at or under a shop's published guideline, so expect questions in the reviews. These have an
answer of their own:

| Shop | They may question | Answer |
| --- | --- | --- |
| JLCPCB | Black solder mask: 64 dams on the bottom (U1's pads, J1's contacts, C_X2 to R_X) are 0.13 mm wide, between pads 0.2 mm apart; JLCPCB's rule for a dam in black mask is a pad spacing of at least 0.13 mm (green 0.10 mm) | Check that the confirmed production file still has a dam between every pair of those pads. If any is gone, change the order to green, whose rule is 0.10 mm |
| JLCPCB | Encoder lug slots 1.5 x 3.0 mm, 0.4 mm longer than JLC's own footprint of C19270361 (and Bourns' recommended 2.6) | As drawn, on purpose: 3.0 mm meets JLC's 2:1 rule for slots, and the lugs are soldered in, so the extra length only takes solder |
| JLCPCB | The reverse-mount LEDs over their board cutouts: JLCPCB may question them, as reverse-mount parts over a cutout are rare | As designed (PCB remark): the cutouts are 2.2 x 2.6 mm with R0.5 corners, and each LED sits on its pads over its cutout ([why](../architecture/electronics.md#lights)); check it in the [placement preview](#placement-preview) |
| JLCPCB | J1 overhangs the y = 60 mm edge by 0.5 mm | By design, as the PCB remark says: the plug reaches it through the body wall. No rail on that edge ([Edge rails](#edge-rails)) |
| JLCPCB | A single edge rail, on y = 0 | As in the PCB remark. If the line needs a second one, it goes on a short edge (x = 0 or x = 160 mm), with no bottom-side part within 12.8 mm of either (the nearest are D_ALTHDG and D_FMS); never on the J1 edge, which J1 overhangs and C_OUT0 and U3 sit 3.7 and 6.75 mm from |
| JLCCNC | The laser marking's small legends: capitals 1.55 and 1.7 mm high (6.1 and 6.7 pt), strokes 0.19 mm at the thinnest. JLCCNC's marking guide gives no minimum for the laser (only lines thick enough to keep their detail); for its print it asks for 6 pt and 0.176 mm lines | Mark as drawn, which meets the print's figures too; accept a sample or a little blur |
| JLCCNC | The laser marking near the holes: the shift legends start 0.7 mm from the key holes, and the line between the AUDIO and RADIO keys passes 0.575 mm from the key holes beside it, where JLCCNC usually keeps a 3 mm margin from an edge | Mark it as drawn. The shift legends keep 0.5 mm beyond the holes' edge breaks for the marking's register. Where the line meets a hole's edge break it is only cosmetic: accept it fading or ending short there |
| JLCCNC | The floor over the RANGE pocket: 0.95 mm (at least 0.85 mm, the drawing's note); JLCCNC recommends 0.8 mm, and over 1.5 mm where the part is bead blasted (the floors over the encoder pockets are 1.65 mm) | As drawn. Hold the pocket depths +0/-0.1 mm (a thicker floor takes the room over the parts) and the flatness after blasting. If they will not blast it as drawn: anodising without blasting (tool marks may then show); never a thicker floor, and no blasting of the front face alone, which can bow the plate |
| JLCCNC | The boss height, 6.55 ±0.05 mm | ±0.1 mm is acceptable, with the flatness then held to 0.15 mm (see the next row) |
| JLCCNC | Flatness 0.1 mm: milling most of a 12 mm plate off one side can bow it, and JLCCNC publishes no flatness figure | Up to 0.2 mm is acceptable with the boss height held at ±0.05 mm, or up to 0.15 mm with the bosses at ±0.1 mm; not 0.2 mm and ±0.1 mm together ([why](../architecture/mechanics.md#light-pipes)). Stress-relieved plate (T651) helps, if they offer it |
| JLC3DP | Light pipes: the 2.0 mm rods are 4.45 mm long, over the pillar guideline (Ø2.0 up to 4 mm) | Print as is. If they refuse: in `mech/stack.py` set `top_len` in `PIPE` to 4.0 and `PIPE_ON_BAR` to `True`, run `./build.sh` and upload `lightpipes.step` again, quantity 2 (also in the file table and the shopping list). The pipe is then 9.65 mm long, under the least part of 10 mm, so the three come on one bar on Ø1.0 mm necks that snap off by hand ([Putting it together](assembly.md#putting-it-together)); the remark then reads "supports on the bar only" |

The answer to every other question is "as drawn" (JLC3DP: "print as is"). Accept a change only if it keeps
the drawing's notes (JLCCNC) and the remarks. If a review does end in a change, change
[mech/stack.py](../../mech/stack.py), run [`./build.sh`](../architecture/generators.md#build), see which files
in `production/` changed and upload each to its shop again.

## Shipping, tax and cost

Each JLC shop has its own checkout. JLC3DP parts can join the JLCPCB cart, so put them there: they then ship
with the boards, once Y1 has arrived and the boards are built. The plate comes as a parcel of its own, with
its own shipping and import fees, unless it was paid in the JLCPCB cart and the checkout ships it with the
boards (step 3). Screws from JLCMC come as an order and a parcel of their own, which costs more to ship than
the screws do.

In the EU, up to €150 of goods the shop collects the VAT at checkout (IOSS); a flat customs duty of €3 per
item line declared is added at checkout or paid on delivery, with any carrier's fee. Over €150 the standard
duty replaces the flat one, and VAT, duty and the carrier's fee are paid on delivery. Where the checkout
offers DDP shipping (delivered duty paid), pick it: it collects all of these at checkout.

JLCPCB's share with the spare board: its fees for assembling both sides come to about $130 and its parts to
about $80, about $50 of that the encoders, before the boards, shipping, VAT and the carrier's fee. The
plate, the printed parts and the local items, the screws among them, come on top; the quotes give the totals,
and the key caps move them most (step 1). Allow 2 to 5 weeks for Y1 through Global Sourcing before the JLCPCB
order can be placed, then at least 4 days of Standard assembly; at least 72 hours of build time for the key
caps (WJP).
