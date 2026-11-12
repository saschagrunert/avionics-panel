# Ordering

This page orders everything from the JLC group: the board from JLCPCB, the front plate from JLCCNC, the printed
parts from JLC3DP, the screws from JLCMC and a few loose parts from LCSC. Only the feet, some consumables and
tools (and the optional steel plate) come from a local shop. The JLC group is a suggestion, not a requirement:
the schematic, the Gerbers and the STEP files allow other vendors too, but that route is not documented. The
files are in [production/](../../production/); every
name there starts with `avionics-panel-rev1-`, which this page leaves out (`body.step` is
`avionics-panel-rev1-body.step`). What follows the order is in [Bring-up](bring-up.md).

## Assembly variants

By default JLCPCB fits and solders both sides of the board, so nothing needs soldering at home. Hand-soldering
the through-hole parts (keys, encoders, RANGE control) is the cheaper option for those who like to solder.
Both use the same Gerbers and the same bottom side.

| | Full assembly (default) | Hand-soldering (option) |
| --- | --- | --- |
| JLCPCB assembly | Standard, both sides | Economic, bottom side only (all SMD) |
| Files for JLCPCB | `gerbers.zip`, `BOM-full.csv`, `CPL-full.csv`: one BOM (parts list) and one CPL (placement file) for both sides, the only ones to upload | `gerbers.zip`, `BOM.csv`, `CPL.csv` |
| Through-hole parts | from JLCPCB's parts library, on both boards ([below](#through-hole-parts)) | from LCSC (`THT-LCSC.csv`), soldered by hand with the J1 shell tabs ([Hand-soldering](assembly.md#hand-soldering)) |
| Edge rails | one of at least 10 mm on the long edge away from J1, removed by JLCPCB before delivery ([edge rails](#edge-rails)) | none |
| Bring-up | every part is on from the start: a board that turns out dead takes its encoders and RANGE control with it, and the second board is the spare | the encoders and the RANGE control go on last, after the board has been tested |
| Cost | higher ([cost](#shipping-tax-and-cost)) | the LCSC parts on top of a cheaper board order; 28 keys, three encoders and the RANGE control to solder per board |

## Order step by step

1. Full assembly: buy the six encoders into your Parts Manager stock now ([below](#through-hole-parts)).
2. [JLCCNC](#jlccnc), first: the plate. Pay after their review, and wait for that review before paying JLC3DP:
   it can change the light holes (and so the light pipes) and the amber. If it does, change
   [mech/stack.py](../../mech/stack.py), run `./build.sh` ([Generators](../architecture/generators.md#build))
   and upload the new files.
3. [JLCPCB](#jlcpcb): the boards. Go through the [placement preview](#placement-preview), then pay. (With
   hand-soldering, JLC3DP may join this cart if both stay under €150 of goods; then pay only once JLCCNC's
   review is back: [shipping](#shipping-tax-and-cost).)
4. [JLC3DP](#jlc3dp), after JLCCNC's review: body, USB-C filler, key caps, knobs, light pipes. With full
   assembly, as an order and a parcel of its own: the board order alone is over €150.
5. [LCSC](#lcsc): the spare keys and the reference RANGE control (or, hand-soldering, the through-hole parts),
   shipped on its own.
6. [JLCMC](#jlcmc): the screws, an order and a parcel of its own.
7. Locally: the rest of the [shopping list](#shopping-list).
8. Optional, to run the firmware before the boards arrive: the [Pico bench](bring-up.md#pico-bench) parts.

Before paying each order, read the [review questions](#review-questions) and the
[tax lines](#shipping-tax-and-cost).

## Shopping list

Everything one panel needs, with its spare board. Hardware:

| ☐ | Item | Qty | Shop, part | Spec | For | Variant |
| --- | --- | --- | --- | --- | --- | --- |
| ☐ | Board, assembled | 2 (of 5 bare) | JLCPCB | [settings below](#jlcpcb) | the panel; the second is the spare for the first | both |
| ☐ | Front plate | 1 | JLCCNC | 6061 from 12 mm stock, black anodised, laser marking, amber UV print | [assembly](assembly.md#putting-it-together) | both |
| ☐ | Body | 1 | JLC3DP | MJF PA12-HP, dyed black | [assembly](assembly.md#putting-it-together) step 4 | both |
| ☐ | USB-C filler | 2 (1 spare) | JLC3DP | MJF PA12-HP, dyed black | [assembly](assembly.md#putting-it-together) step 5 | both |
| ☐ | Key caps | 4 sets of 28 (A to D): `caps-A.zip` to `caps-D.zip`, quantity 1 each | JLC3DP | WJP Full Color Resin; one set fits, the others are spares | [cap set](bring-up.md#choosing-the-cap-set) | both |
| ☐ | Outer knob | 2 + 1 tight + 1 loose | JLC3DP | SLA Black Resin, `knob-outer` (ALT/HDG, FREQ) | [knobs](assembly.md#fitting-the-knobs) | both |
| ☐ | Outer FMS knob | 1 + 1 tight + 1 loose | JLC3DP | SLA Black Resin, `knob-outer-fms` (coarser grip) | [knobs](assembly.md#fitting-the-knobs) | both |
| ☐ | Inner knob | 3 + 1 tight + 1 loose | JLC3DP | SLA Black Resin, `knob-inner` | [knobs](assembly.md#fitting-the-knobs) | both |
| ☐ | RANGE knob | 1 + 1 tight + 1 loose | JLC3DP | SLA Black Resin, `knob-range` | [knobs](assembly.md#fitting-the-knobs) | both |
| ☐ | Light pipes | 2 bars (1 spare) | JLC3DP | SLA 8001 Resin, transparent, no post-processing; two pipes per bar | [assembly](assembly.md#putting-it-together) step 2 | both |
| ☐ | Screws | 6 (4 + 2 spare), or JLCMC's pack minimum | JLCMC, EDDH-C16E1-M3-L8 (10B21 blackened, 8.8) or EDDH-S1W-M3-L8 (A2-70) | M3 x 8 flanged button head, hex socket, ISO 7380-2 | [assembly](assembly.md#putting-it-together) step 4 | both |
| ☐ | Spare keys | 5 (LCSC's minimum; 2 needed) | LCSC, C589907 | TE 1-1825910-4 | trying the cap sets without pulling at a soldered key | full |
| ☐ | RANGE control, loose | 1 | LCSC, C160841 | Alps RKJXT1F42001 | reference for the [seating check](bring-up.md#on-arrival) | full |
| ☐ | Through-hole parts | 1 set (one board; a second for the spare board if wanted), as `THT-LCSC.csv` orders it: 30 keys (28 + 2 spare), 3 encoders, 1 RANGE control | LCSC, `THT-LCSC.csv`: C589907, C19270361, C160841 | TE 1-1825910-4, Bourns PEC11D-4120F-S0015, Alps RKJXT1F42001 | [Hand-soldering](assembly.md#hand-soldering) | hand-soldering |
| ☐ | Feet | 4 | local | self-adhesive, up to 10 mm across | [assembly](assembly.md#putting-it-together) step 7 | both |
| ☐ | USB-C cable | 1 | local | data-capable (a charge-only cable shows no RPI-RP2 drive) | [bring-up](bring-up.md) | both |
| ☐ | Steel plate | 1 | local laser cutting, `steel.dxf` | 2 mm steel, 143 x 36 mm (±0.1) with two 15 x 15 mm notches at the back corners, about 74 g | desk weight, [assembly](assembly.md#putting-it-together) step 7 | optional |

Consumables:

| ☐ | Item | Qty | Shop, part | Spec | For | Variant |
| --- | --- | --- | --- | --- | --- | --- |
| ☐ | Removable adhesive putty | a pea-sized piece | local | Blu Tack, black or white | holding the USB-C filler, [assembly](assembly.md#putting-it-together) step 5 | both |
| ☐ | Fine sandpaper | 1 sheet | local (or LCSC C5124393, 1000 grit) | 400 to 1000 grit | the light-pipe stubs, [assembly](assembly.md#putting-it-together) step 2 | both |
| ☐ | Flat file, or coarse sandpaper on a block | 1 | local | 240 grit | a square corner or a burr at the rail edge, [on arrival](bring-up.md#on-arrival) | if needed |
| ☐ | Double-sided tape | a strip | local | | the steel plate | optional |
| ☐ | Adhesive tape | a strip | local | | a loose knob, [knobs](assembly.md#fitting-the-knobs) | if needed |
| ☐ | Solder and flux | | local | | [Hand-soldering](assembly.md#hand-soldering), rework | hand-soldering; full: rework only |
| ☐ | Solder wick | 1 | local (or LCSC C92547, 2 mm, or C88005, 3 mm) | | rework | hand-soldering; full: rework only |

Tools:

| ☐ | Item | Qty | Shop, part | Spec | For | Variant |
| --- | --- | --- | --- | --- | --- | --- |
| ☐ | Hex key | 1 | local | 2 mm | the screws, the plate threads, the BOOT pads | both |
| ☐ | Two blocks and a cloth | 2 | at home (books, wood) | at least 25 mm high | face-down [assembly](assembly.md#putting-it-together) | both |
| ☐ | Feeler gauge set | 1 | local | 0.03 to 1.0 mm, blades that stack | the [seating check](bring-up.md#on-arrival), the USB-C filler | both |
| ☐ | Steel rule | 1 | local | | squaring the caps, [assembly](assembly.md#putting-it-together) step 1 | both |
| ☐ | Multimeter | 1 | local | continuity beeper and diode mode | [bring-up](bring-up.md#flash-and-test) steps 1 and 2 | both |
| ☐ | Soldering iron | 1 | local | temperature controlled | [Hand-soldering](assembly.md#hand-soldering), rework | hand-soldering; full: rework only |
| ☐ | Magnifier or loupe | 1 | local (or LCSC C106807, 7.5x, or C90740, 3.5x) | | [troubleshooting](bring-up.md#when-bring-up-fails), checking joints | both |
| ☐ | Drills and a needle file | 6.0, 3.5 and 2.5 mm | local | | only if a knob bore is too tight, [knobs](assembly.md#fitting-the-knobs) | if needed |

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
  remove the edge rail before delivery ([edge rails](#edge-rails)); remark:

  > J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail there. One edge rail of at least
  > 10 mm on the y = 0 edge only, removed before delivery; keep the R3 corners milled. Through-hole parts: seat
  > each one fully down and flat before soldering; ENC_ALTHDG, ENC_FREQ, ENC_FMS and RANGE at most 0.05 mm
  > proud (hold RANGE pressed down while soldering), and solder the encoder lugs. Solder the four J1 shell
  > tabs from the top, filling the slots. Solder mask: keep the 0.13 mm dams between the pads of U1, J1 and
  > C_X2/R_X; please ask before removing any. The two 2.2 x 2.4 mm internal cutouts in the outline are for
  > reverse-mount LEDs: please mill them with R0.5 inside corners (1.0 mm router).

- Hand-soldering: Economic assembly, bottom side; `BOM.csv` and `CPL.csv`; Edge Rails/Fiducials: None;
  remark:

  > J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design. No edge rails, please. Solder mask: keep
  > the 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask before removing any. The two
  > 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount LEDs: please mill them with R0.5
  > inside corners (1.0 mm router).

The reasons: [seating](../architecture/mechanics.md#seating),
[J1 shell tabs](assembly.md#hand-soldering), [solder mask](../architecture/electronics.md#solder-mask).

JLCPCB lists black among its standard colours at standard pricing, but its build-time table is for green:
check the price and build time the quote shows for black.

### Edge rails

J1 overhangs its long edge (y = 60 mm in the Gerbers) by 0.5 mm, so the plug reaches it through the body wall:
no rail can go there. Every other bottom-side part keeps 3.7 mm from the edges. The R3 corners stay milled: a
V-cut square corner does not fit the body ([On arrival](bring-up.md#on-arrival)).

- Full assembly: Standard assembly needs 70 x 70 mm and the board is 60 mm wide, so one rail goes on y = 0.
  With JLCPCB's paid option to remove the edge rail before delivery, the board arrives ready for the body; the
  V-cut edge that is left (±0.4 mm) fits the cavity (`check_fit.py`).
- Hand-soldering: JLCPCB lists rails as not needed for Economic assembly, and the milled outline fits the body
  as delivered. Should their engineer add rails anyway, accept if the J1 edge stays free.

A board that arrives with a rail anyway: [On arrival](bring-up.md#on-arrival).

### Through-hole parts

`BOM-full.csv` lists the through-hole parts for one board; JLCPCB multiplies by the 2 assembled boards. They
are extended parts in JLCPCB's own library, whose stock is not LCSC's. The parts whose stock is worth a look
before ordering:

| Part | JLC part | Library | Per board |
| --- | --- | --- | --- |
| TE 1-1825910-4 key switch | C589907 | extended | 28 (full only) |
| Bourns PEC11D-4120F-S0015 dual encoder | C19270361 | extended | 3 (full only) |
| Alps RKJXT1F42001 RANGE control | C160841 | extended | 1 (full only) |
| U4: hongjiacheng SRV05-4 ESD array, SOT-23-6 | C7420376 | preferred extended | 1 |
| F1: Bourns MF-NSMF050-2 PTC fuse, 0.5 A hold, 1206 | C75464 | extended | 1 |
| LiteOn LTST-C230KSKT yellow LED (the amber SHIFT light) | C125108 | extended | 1 |
| LiteOn LTW-C230DS white LED | C575513 | extended | 1 |

The encoders are the tight part: JLCPCB stocks few of them. Buy the six into your Parts Manager stock as soon
as you order: the assembly takes them from there, so no other order can take them first. If the stock is
short:

- Buy them in through Global Sourcing (a fee and days to weeks).
- Send six as consigned parts.
- Unselect the three encoder lines in the BOM step and solder the encoders by hand (buy them at LCSC or a
  Bourns distributor; [Hand-soldering](assembly.md#hand-soldering)).

JLCPCB charges a fee per part type: in Economic assembly for each extended part (the RP2040, the flash, the
crystal, J1, F1 and the two LEDs), in Standard assembly for every part type, basic parts included. JLC moves
parts between the classes, so go by the quote.

### Placement preview

Check every assembled part in JLCPCB's placement preview of the bottom side. The preview draws JLC's own
footprint over our pads; the marks below are on our bottom silkscreen, so they hold whichever way round the
preview shows the board. If a part shows turned, correct its rotation there or ask JLCPCB's engineer in the
review; do not order as is. JLCPCB's reading of bottom rotations can change (the CPL's convention:
[Electronics](../architecture/electronics.md#assembly-data)).

- LED_SHIFT and LED_UNIT (reverse-mount LEDs over the two cutouts in the board): JLC's cathode, pin 1, at our
  cathode bar (west), the part centred over its cutout. JLC's footprints draw other cutouts than ours (a
  round hole for the white one, with its pads reaching into it, a smaller square for the amber one): go by the
  pads and our cutout.
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

Aluminium 6061 from 12 mm stock, CNC, bead blasting and black anodising (matte), laser marking. If the form
has a UV colour field, pick orange. Files: `plate.step`, `plate-drawing.pdf` (sizes, tolerances, threads,
finish, edge breaks) and `plate.dxf` (marking). Remark:

> 6061 from 12 mm plate, machined to plate-drawing.pdf; all its notes apply. Boss height 6.05 ±0.05 mm, not
> the general tolerance. The M3-6H threads must take a screw after anodising: mask them or cut them again
> afterwards. Flatness 0.1 mm after anodising. Marking per plate.dxf as the drawing says; layer UV_AMBER:
> please match #D9A441 (RGB 217, 164, 65; Pantone 7563 C) if you can, otherwise use your standard orange. This
> remark takes precedence over the UV colour picked in the form.

JLCCNC lists a fixed set of UV print colours and says nothing about matching one. The SHIFT cap legend and
the 3D view follow whatever the plate gets: if the review says it prints its standard orange, ask for that
orange's colour value, set it as `AMBER` in [mech/stack.py](../../mech/stack.py) and run `./build.sh` before
ordering the caps. UV print may blur slightly at the edges; laser marking alone would make every legend grey.

## JLC3DP

Processes as in the [shopping list](#shopping-list). Quantity per file: `body.step` 1, `usb-filler.step` 2,
each caps zip 1, `knob-outer` 2, `knob-outer-fms` 1, `knob-inner` 3, `knob-range` 1, each `-tight` and
`-loose` knob 1, `lightpipes.step` 2. Files: `body.step` and `usb-filler.step` (`body.stl`, `usb-filler.stl`
if a STEP is refused), `caps-A.zip` to `caps-D.zip`, the twelve `knob-*.step` and `lightpipes.step`. That is
19 files, and the quote page takes 10 per upload: upload them in two batches into the same cart.

- Key caps: upload the zips, they carry the texture (the OBJ alone prints without legends). JLC3DP asks for
  one part per file, and its connected-parts option is not offered for full colour, so see whether the quote
  or the review accepts 28 separate caps per file. If they insist on single parts, ask their support to accept
  all 28 caps of a set as one file. All four sets are ordered at once: which one fits depends on the print
  ([Mechanics](../architecture/mechanics.md#caps-light-pipes-knobs)).
- Light pipes: pick no post-processing. JLC3DP sands and oil-sprays 8001 by default, which can break the thin
  rods; otherwise ask in the remark: "Light pipes: no sanding and no oil spray, please". Both pipes print on
  one snap-off bar (JLC3DP prints resin from 10 x 2 x 2 mm only).

## LCSC

Full assembly: five keys (LCSC's minimum; two are needed) and the loose RANGE control from the shopping list.
Hand-soldering: `THT-LCSC.csv` in LCSC's BOM tool, one board's set; it already orders the two spare keys (30
keys; the `Needed` column gives the count per board). A second set for the spare board if wanted. Order the
encoders early: LCSC stocks few of them. Add any home items from the shopping list only if you want them from
LCSC anyway (the fee note there).

## JLCMC

The screws from the shopping list. JLCMC ships on its own: it does not combine with JLCPCB, JLC3DP or JLCCNC.

## Review questions

Items at or under JLC's published minimums: expect a question in their review, and the answer.

- JLCPCB, black solder mask: 64 dams on the bottom (U1's pads, J1's contacts, C_X2 to R_X) are exactly
  0.13 mm, JLCPCB's minimum for black. Check that the confirmed production file still has a dam between every
  pair of those pads. If any is gone, change the order to green (0.10 mm minimum): the same Gerbers then keep
  0.03 mm to spare.
- JLCPCB, reverse-mount LEDs: the two 2.2 x 2.4 mm cutouts in the outline Gerber are internal cutouts to be
  milled with R0.5 corners (a 1.0 mm router; the remark asks for them), not slots.
- JLCPCB, encoder lug slots: the six plated slots are 1.5 x 2.6 mm, as Bourns' drawing gives them. JLCPCB's
  slot rule asks for a length of at least twice the width: ask for them as drawn.
- JLCPCB, full assembly: should a part not be seatable flat as asked, leave it out of the assembly and solder
  it by hand ([Hand-soldering](assembly.md#hand-soldering)) rather than accept it standing proud.
- JLCCNC, legends: the amber is matched or falls back to their orange (the SHIFT cap legend follows,
  [above](#jlccnc)). The UV legends are 6.1 to 6.9 pt, at their 6 pt minimum: a flag means a sample or a
  little blur.
- JLCCNC, web, pocket and threads: the web is 4.0 ±0.1 mm (ask for 3.9 to 4.1 if they offer less). The RANGE
  pocket leaves 0.65 mm of metal (their minimum 0.5): hold its depth +0/-0.1 rather than thicken the floor.
  Threads they say they cannot mask: ask for them to be cut after anodising.
- JLCCNC, flatness: milling most of a 12 mm plate off one side can leave it bowed, and JLCCNC publishes
  no flatness capability; stress-relieved plate (T651) helps, if they offer it. If they ask, up to 0.17 mm is
  acceptable (the light pipes' room over their bases goes first, then the body walls at 0.19). Ask for the
  boss height ±0.05 mm, but if they can only hold ±0.1, accept (cosmetic only). Not both at once: with the
  bosses at ±0.1, flatness up to about 0.12 mm ([Mechanics](../architecture/mechanics.md#fastening)).
- JLC3DP: the light pipes (Ø2.0 rods, Ø2.8 bases on Ø1.0 necks), the outer knob key (1.4 mm wide, under 1.5
  for positioning features, or it would not clear a narrow shaft slot), the cap set dimples (0.86 mm of wall
  on a worst print) and tactile bars (0.5 mm proud), the MJF body's screw bosses (1.6 mm, over the 1.5 mm for
  fasteners) and the USB-C filler (2.0 mm thick, exactly the 10 x 2 x 2 mm minimum): ask them to print as is.
  The light pipes' rods meet the resin pillar guideline (Ø2.0 up to 4 mm), but the bases are under the next
  entry (Ø3.0 up to 6 mm); the order has a spare pair.

## Shipping, tax and cost

The JLC shops share one account but each has its own checkout, payment by PayPal, card or Google Pay.

- JLC3DP items can join the JLCPCB cart and be paid together; the JLCPCB payment then waits for JLCCNC's
  review too. JLCCNC is paid separately after its review.
- LCSC combines its parcel with a JLC order only if that order is shipped to LCSC's Hong Kong warehouse
  (chosen as the address at the JLC checkout, and not changeable after). Ship LCSC on its own: added to a JLC
  parcel it also pushes it over the €150 line below.
- EU (Germany as the example), for parcels to consumers:
  - Every parcel pays the EU handling fee of €2 per customs declaration line, whatever its value.
  - Under €150 of goods per shipment, JLC collects the VAT at checkout (IOSS, the EU import scheme). A flat
    customs duty of €3 per tariff line (an interim rule, until 2028-07-01) and a carrier's disbursement fee
    can come on top, so check the tax lines before paying.
  - A shipment over €150 is cleared on delivery instead, with the carrier's fee.
  - Full assembly: the JLCPCB order alone is over €150, so ship JLC3DP on its own. Hand-soldering: ship JLC3DP
    on its own too if JLCPCB and JLC3DP together come to more than €150 of goods.

Rough cost of the panel with its spare board, without the rail removal fee: about €370 to 420 with shipping
for full assembly, €250 to 300 with hand-soldering, plus the screws with their own shipping and the local
items. The quotes give the current figures.
