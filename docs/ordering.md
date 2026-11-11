# Ordering

The board, the plate and the printed parts come from the JLC group (JLCPCB, JLCCNC, JLC3DP); standoffs,
screws, washers, feet, consumables and the optional steel plate come from LCSC or a local shop. The board
comes in one of two [assembly variants](#assembly-variants): economic (JLCPCB fits the SMD bottom side,
the through-hole parts come from LCSC and are soldered by hand) or full (JLCPCB fits both sides, the
boards arrive fully soldered). The files are in [production/](../production/); every file name there
starts with `avionics-panel-rev1-`, which the tables below leave out (`body.step` is
`avionics-panel-rev1-body.step`).

## Assembly variants

| | Economic | Full |
| --- | --- | --- |
| JLCPCB assembly | Economic, bottom side only (all SMD) | Standard, both sides: the SMD bottom and the through-hole parts on the top |
| Files for JLCPCB | `gerbers.zip`, `BOM.csv`, `CPL.csv` (bottom side only) | `gerbers.zip`, `BOM-full.csv`, `CPL-full.csv`: one BOM and one CPL for both sides, the side in the CPL's Layer column ("Top" for the through-hole parts, "Bottom" for the SMD parts), upload them as the only BOM and CPL |
| Through-hole parts | from LCSC (`THT-LCSC.csv`): keys, encoders, RANGE control and LEDs for one board plus spares, soldered by hand ([Mechanics](mechanics.md#hand-soldering)) | from JLCPCB's parts library (below), fitted on both boards: two sets |
| J1 shell tabs | soldered by hand from the top | soldered by JLCPCB, asked for in the order remark (below) |
| Order remark | edge rails (below) | edge rails and the [through-hole remark](#full-variant-through-hole-parts-at-jlcpcb) |
| Extended parts (2026-11-11) | RP2040, flash, crystal, J1, and the 27 R (a preferred extended part: no fee in Economic assembly) | the same plus the five through-hole parts |
| Quote 2026-11-09 (re-quote) | about €72 for 2 boards, plus about €37 at LCSC for one set of through-hole parts | about €227.43 for 2 fully populated boards |
| On arrival | [mechanics](mechanics.md#on-arrival), then the hand-soldering in the bring-up | [mechanics](mechanics.md#on-arrival) with the full-variant checks; no soldering |
| Bring-up | the encoders and the RANGE control go on last, after the board has been tested | every part is on from the start: a board that turns out dead takes its encoders and RANGE control with it; the second board is the spare |

Both variants use the same Gerbers and the same bottom side. The full variant costs about €118 more than
the economic one with one LCSC set (about €81 more against two sets, which the economic variant needs for a
second working board), and saves 28 keys, three encoders, the RANGE control and two LEDs of hand soldering
per board, plus the risk of a bridge or a tilted part. In exchange it gives up the bring-up order that
fits the expensive parts last.

### Full variant: through-hole parts at JLCPCB

`BOM-full.csv` lists the through-hole parts by their JLC part numbers (the LCSC numbers, which JLCPCB's
parts library uses too) for one board; JLCPCB multiplies by the 2 assembled boards and adds its own few
spares of the keys and LEDs. All five are in JLCPCB's library as extended parts. Stock on 2026-11-11
(JLCPCB's stock is LCSC's, so the two variants draw on the same parts):

| Part | JLC part | Library | JLC stock | Per board | For 2 boards |
| --- | --- | --- | --- | --- | --- |
| TE 1-1825910-4 key switch | C589907 | extended | 30920 | 28 | 56 |
| Bourns PEC11D-4120F-S0015 dual encoder | C19270361 | extended | 68 | 3 | 6 |
| Alps RKJXT1F42001 RANGE control | C160841 | extended | 6859 | 1 | 2 |
| XINGLIGHT XL-302UYC amber LED (SHIFT) | C2895466 | extended | 2769 | 1 | 2 |
| XINGLIGHT XL-302UWC white LED (UNIT) | C2895458 | extended | 45483 | 1 | 2 |

The encoders are the tight part: 6 of 68. If JLCPCB's stock drops under 6 before the order, the BOM step
shows them as short, and there are three ways on:

- Buy them into your JLCPCB parts library first (Parts Manager): from JLC's own stock once it is back, or
  through Global Sourcing from another distributor (a sourcing fee, and days to weeks before assembly can
  start). The assembly then takes them from your library.
- Consigned parts: buy the six encoders anywhere and send them to JLCPCB for this order.
- Leave the three encoder lines out of the assembly (unselect them in the BOM step, so the CPL rows for
  ENC_ALTHDG, ENC_FREQ and ENC_FMS are not placed) and solder the encoders by hand as in the economic
  variant ([Mechanics](mechanics.md#hand-soldering)), bought at LCSC or a Bourns distributor. Everything
  else stays fully assembled, and the encoders go on last again.

The CPL places every through-hole part by JLC's footprint in JLCPCB's convention for the top side: seen
from the top, the library footprint turned counter-clockwise by the rotation, its origin on the CPL
position. The keys, the encoders, the RANGE control and the amber LED are at 0, the white LED at 180: JLC's
two LED footprints number their pins the other way round (pin 1 is the cathode of the amber one, the anode
of the white one). The encoders' CPL position is 1 mm north of the shaft (towards the J1 edge), where JLC's
footprint has its origin, midway between its pin rows. [pcb/check.py](../pcb/check.py) fits each JLC
footprint at its CPL position and rotation onto our holes pin by pin (the cathode on the square pad, each
encoder pin on its own hole), so a wrong rotation or position fails the build.

The through-hole parts sit under the front plate with little room, so the order remark must say how to
seat them; JLCPCB solders them from the bottom, among the SMD parts (by hand or by selective soldering;
the SMD parts there rule out a plain wave), and `check.py` keeps 1.0 mm round every through-hole pad free
of other exposed copper for that ([Electronics](electronics.md)). Remark for the full variant, after the
edge-rail remark below: "Through-hole parts on the top side: please seat every one fully down and flat on
the board before soldering, not tilted and not lifted on its leads. The two LEDs LED_SHIFT and LED_UNIT
flush on the board, at most 0.2 mm proud (a light pipe sits right above them); cathode (flat side, short
lead) on the square pad. The encoders ENC_ALTHDG, ENC_FREQ, ENC_FMS and the RANGE control flat on the
board (the front plate pockets leave only 0.3 mm over the encoders, 0.1 mm over and 0.17 mm round the
RANGE control); solder the encoder mounting lugs too. The 28 keys K00 to K36 flat and square. Please also
solder the four J1 (USB-C) shell tabs from the top side, filling the slots: the pin-in-paste stencil
openings only leave a fillet on the bottom, and the tabs carry the plug."

## Suppliers

| Part | Service | Process | Files in `production/` |
| --- | --- | --- | --- |
| Board, assembled | JLCPCB | 4 layers, 1.6 mm thick, ENIG, green solder mask, via covering "Tented" (below), 0.3 mm min. via; 2 boards. Economic variant: Economic assembly, bottom side (all SMD). Full variant: Standard assembly, both sides, through-hole parts included. Confirm Parts Placement: yes, and Review Before Payment if offered; Edge Rails/Fiducials: Added by JLCPCB, on the two short edges only (below; break them off on arrival) | economic: `gerbers.zip`, `BOM.csv`, `CPL.csv`; full: `gerbers.zip`, `BOM-full.csv`, `CPL-full.csv` |
| Through-hole parts (economic variant only) | LCSC, hand-soldered | keys, encoders, RANGE control, LEDs for one board plus spares (30 keys, 5 + 5 LEDs). The spare board needs its own set if the first one fails after its keys are on (desoldering 28 keys rarely leaves them reusable): optionally add 28 keys, 1 RANGE control and, if wanted, 3 encoders (the 4 + 4 spare LEDs already cover its LEDs) | `THT-LCSC.csv` (LCSC BOM tool) |
| Front plate | JLCCNC | 4 mm aluminium 6061, CNC from the back, bead blasting + black anodising (matte), laser marking, no threads; the form allows two finishes, so the amber UV print goes into the remark (below) | `plate.step`, `plate-drawing.pdf` (back face, pockets), `plate.dxf` (marking) |
| Body | JLC3DP | MJF PA12-HP, dyed black | `body.step` (`body.stl` if the STEP is refused) |
| Key caps | JLC3DP | WJP Full Color Resin, four full sets of 28 caps (A, B, C, D: rib circles 3.15, 3.25, 3.35, 3.05 mm, marked with 1, 2, 3, 4 dimples on the underside), quantity 1 each; upload the zips, they carry the texture (the OBJ alone prints without legends). One set fits, see [Mechanics](mechanics.md#caps-light-pipes-knobs). If JLC3DP wants one part per file, see below | `caps-A.zip` to `caps-D.zip` (`caps-single-A.zip` etc.: one zip per cap) |
| Knobs | JLC3DP | SLA Black Resin: `knob-outer` x2 (ALT/HDG, FREQ), `knob-outer-fms` x1 (same fits, coarser grip), `knob-inner` x3, `knob-range` x1, plus one each of `knob-outer-tight`, `-loose`, `knob-outer-fms-tight`, `-loose`, `knob-inner-tight`, `-loose`, `knob-range-tight`, `-loose` (bore 0.2 mm under / over nominal; the knobs are held by friction, keep whichever grips) | `knob-*.step` |
| Light pipes | JLC3DP | SLA 8001 Resin, transparent, quantity 2 (one spare); both pipes on one snap-off bar (JLC3DP prints resin from 10 x 2 x 2 mm only); break off, sand, polish the top, glue in with clear epoxy or UV glue. The rods (Ø1.5 and Ø1.3, 3.6 mm long) are longer than JLC3DP's resin pillar guideline, so the review may flag them or they may break: the fallback is below | `lightpipes.step` |
| Light pipe fallback | local or online | PMMA end-glow optical fibre (plastic fibre for lamps and models), Ø1.5 mm for SHIFT and Ø1.0 to 1.25 mm for UNIT, a few cm of each; cut to 3.6 mm with a fresh blade, sand both ends flat and polish them | |
| Standoffs | LCSC or local | 6 (2 spare) hex standoffs M2.5 x 8, female-female, 5 mm across flats, threaded through, 8.0 ±0.1 long, brass (nickel-plated) or aluminium; for example Würth 970080154 (check that the listing says female-female and 5 mm across flats) | |
| Screws, washers, feet | LCSC or local | 6 x M2.5 x 8 pan head (ISO 7045 or ISO 14583; 2 spare), 6 x DIN 125-A (ISO 7089) M3 washers (3.2 x 7 x 0.5), one under every head; 4 self-adhesive feet up to 10 mm across | |
| Consumables | local | thixotropic (non-sag, paste) two-part epoxy with at least 30 minutes of working time for the standoffs, for example Araldite 2014-1 (not a runny clear epoxy); clear epoxy or UV glue for the light pipes (not CA glue); soft wax or plasticine to plug the standoff threads while gluing, a toothpick to press it in; isopropyl alcohol, fine sandpaper (up to about 1000 grit, plus plastic polish for the light-pipe tops), a stiff card and a release film (a piece of PE bag or baking paper; or low-tack tape) to hold the light pipes flush, double-sided tape for the steel plate, a data-capable USB-C cable (a charge-only cable shows no RPI-RP2 drive). Tools: two blocks at least 25 mm high (books, wood) and a cloth for face-down assembly, two more to rest the body on, a feeler gauge set (0.1 mm for the board-bow check on arrival, 0.2 mm for the LED seating in the full variant, about 0.8 mm for the body gap; a 0.8 mm drill shank also works for the gap), a steel rule as a straightedge (board-bow check in the full variant), a 5 mm nut driver, a PH1 (ISO 7045) or T8 (ISO 14583) screwdriver for the M2.5 pan heads, a flat file or 240 grit sandpaper on a flat block for the edge-rail stubs and the board corners, calipers for the board length, soldering iron, solder and flux (in the full variant only for the J1 tabs, should they come back unfilled), side cutters for the LED legs (economic variant); if a knob bore is tight, 6.0, 3.5 and 2.5 mm drills and a needle file | |
| Steel plate (optional) | local or laser cut | 2 mm steel, 143 x 36 mm (±0.1) with two 15 x 15 mm notches at the back corners for the feet (about 74 g), desk weight in the 144 x 37 mm recess under the body, double-sided tape | `steel.dxf` (outline) |
| Bench (before the boards) | local or online | Raspberry Pi Pico with headers and a data-capable micro-USB cable, a breadboard and jumper wires, a few push buttons, one cheap EC11-type encoder with push and 30 detents / 15 pulses per turn, like the PEC11D (not one of the three PEC11D; a 20 / 20 part, common among cheap EC11 and KY-040 encoders, needs `divisor=4` in `code.py`, see [Firmware](firmware.md#pico-bench)), a 1N4148 diode for SHIFT from GP6 to GP2 (see [Firmware](firmware.md#pico-bench)) | |

Every part number in the BOM is set. The RP2040, the flash, the crystal and the USB-C socket are extended
parts at JLCPCB (an extended-part fee each, about $3). The 27 R USB series resistors (C25190) are extended
too, but flagged as a preferred extended part on 2026-11-11, which carries no fee in Economic assembly; JLC
moves parts between these classes, so the quote may show a fee for them. They stay 27 R, the value in
Raspberry Pi's design ([Electronics](electronics.md)); 22 R (C23345, basic, already on the board for the
white LED) would save that fee. The column pull-ups (10 k, C25804) are a basic part.

JLCCNC remark: "No threads. 4 x round flat-bottom pockets dia 7.0 +0.1/-0 from the back, 2.0 +0/-0.1 mm
deep (see plate-drawing.pdf). Plate 4.0 ±0.1; all pocket depths +0/-0.1: at least 0.7 mm must stay to the
front face. RANGE pocket dia 19.6: sharp floor corner, inside radius 0.3 mm max. Key holes 10.2 x 7.0
+0.1/-0 after anodising. Light holes dia 1.8 and 1.6 +0.1/-0. Pocket and hole positions ±0.1 mm to each
other. Flatness 0.1 mm over the whole plate after bead blasting and anodising (it is held only at its
four corners; the LEDs sit 0.05 mm under its back near the middle). Front marking per plate.dxf, same
origin and orientation as the STEP (bottom-left corner seen from the front); DXF units: mm; fill closed
contours even-odd (the holes in letters such as A, D and O are separate contours). Layer LASER = laser
marking; layer UV_AMBER = UV print in amber #D9A441 (RGB 217, 164, 65; Pantone 7563 C, roughly RAL 1004);
layer CUT = outline and through holes, for alignment only, not to be marked."

Keep the solder mask green: the mask dams between the RP2040's pads, between the USB-C contacts and
between C_X2 and R_X are 0.1 mm, JLCPCB's minimum for green ([pcb/check.py](../pcb/check.py) measures
them). Other colours need wider dams, so those pads would lose the mask between them.

Edge rails: JLCPCB's assembly terms want component bodies 2.5 mm from the board edge, and the line holds
the board by rails. Choose Edge Rails/Fiducials "Added by JLCPCB" and ask for them on the two short edges
(x = 0 and x = 160 mm, the 60 mm sides) only; if the form offers no choice of sides, say so in the order
remark. Every bottom-side part but one keeps at least 3.7 mm from the edges (pads; the bodies are no
larger). The USB-C socket J1 overhangs its long edge (y = 60 mm in the Gerbers, the edge its opening
faces) by 0.5 mm by design: JLC's footprint of C165948 runs from -2.26 to +5.09 mm about its origin,
and the plug has to reach it through the case wall. JLC may still want a rail on a long edge (boards under
70 mm in one dimension can need them): then only on the long edge away from J1, or accept their
engineer's proposal if it keeps J1's edge clear. The board corners are R3 (the body's cavity corners
R3.5), and a V-cut only makes straight lines: a square corner would stand about 0.74 mm into the body.
Remark for their review: "J1 (USB-C) overhangs the board edge at the USB opening (y = 60 mm in the
Gerbers) by 0.5 mm by design. Please add the edge rails on the two short edges (60 mm) only, none on the
long edges. If a rail on a long edge is required, put it only on the long edge away from J1 (y = 0).
Keep the R3 corners (milled); V-cut on the straight short edges only, or tabs."

The boards arrive with the rails still on (JLCPCB's default): with a 5 mm rail on each short edge the
board is about 170 mm long and doesn't go into the body. Break them off and sand the board to 160.2 mm or
shorter before anything else ([Mechanics](mechanics.md#on-arrival)). JLCPCB can also remove the rails for
a fee; ask in the order remark if you prefer, and still measure the length.

Via covering "Tented" matches the Gerbers: the solder mask covers every via on both sides except two
deliberate openings, which JLCPCB keeps because the mask Gerber decides for a Gerber order (its via
covering guide): the three 1V1 vias under the RP2040 are probe points on the top (open there, tented
underneath), and the four GND vias in the RP2040's exposed pad sit in that pad's mask opening, clear of its
paste windows. Should JLC tent those as well, assembly is unaffected; only the 1V1 probe points are lost.

All four shops share one JLC account but have their own checkout. JLC3DP items can join the JLCPCB
cart and be paid together; LCSC can combine its shipment with a JLCPCB order (choose it at the LCSC
checkout); JLCCNC is paid separately after its review. Payment by PayPal, card or Google Pay. Under
€150 of goods per shipment JLC collects German VAT at checkout (IOSS); since July 2026 a customs duty and
a disbursement fee can come on top, so check the tax lines before paying. A shipment over €150 is cleared
on delivery instead, with the carrier's fee. The quotes below are too old to tell which side of the line
the order falls on (they cover one cap set, no knob variants and no FMS ring), so re-quote and read the
JLC cart total of goods: if JLCPCB and JLC3DP together come to more than €150, pay and ship the JLC3DP
order on its own (or expect the customs fee on delivery). The full variant's JLCPCB order alone is over
€150, so it is cleared on delivery either way; ship JLC3DP on its own then too. Ship the LCSC order on its
own as well: added to a JLC parcel it takes that over the line.
JLCPCB assembles at least 2 boards (bare boards come in 5). Order 2 assembled boards but only one set of
plate, body, caps and knobs; the second board is the spare for the first, untested chip-down design. In
the full variant both boards come fully populated, with two sets of through-hole parts.

## Before paying

- Upload the current files to the four quotes (JLCPCB, JLC3DP, JLCCNC, LCSC; see the
  [checklist](#checklist)). The quotes below are older than most of the files.
- JLCCNC reviews the plate before payment. The plate has no threads now (four glued standoffs in 2 mm
  flat-bottom pockets); the JLCCNC remark above also carries the laser marking and the amber UV print. Watch
  for a flag on the 0.85 mm webs between the light holes (+0.1/-0) and the SHIFT and UNIT key holes
  (+0.1/-0 after anodising; 0.75 mm with both at +0.1, JLCCNC recommends 0.8 and allows 0.5); if they flag
  those, shrink `LIGHT_HOLES` in [mech/stack.py](../mech/stack.py) to 1.6 mm (SHIFT) and 1.4 mm (UNIT): the
  pipes follow, 0.3 mm under their holes. JLCCNC publishes no flatness capability, so the remark's flatness
  0.1 mm after bead blasting and anodising may come back as a review question or a surcharge.
- JLC3DP: check that the four cap files with 28 separate caps each are accepted (see
  [key caps](#parts-and-quotes) below).
- Go through the placement preview of every assembled side (below) and the review watch items.

### Placement preview

Check every assembled part in the JLCPCB placement preview of the bottom side. The preview draws JLC's
own footprint over our pads; the marks below are on our bottom silkscreen, so they hold whichever way
round the preview shows the board:

- U1 (RP2040): JLC's pin 1 mark in the corner with our silk corner mark (an L next to the corner pad).
- U2 (flash): JLC's pin 1 mark at our pin 1 dot, next to a corner pad of the row facing away from the RP2040.
- U3 (regulator): JLC's pin 1 mark at our pin 1 dot; the single pin (3, VIN) faces the USB-C socket.
- Y1 (crystal): all four of JLC's pads exactly on ours, long side along the board, JLC's footprint pin 1
  at our dot (diagonally opposite is fine too: the crystal has no polarity, pins 1 and 3 just swap). Go by
  the pads and the footprint's pin 1, not by a chamfered corner on the part drawn in the preview or on the
  real crystal: Abracon's drawing allows the ABM8's chamfer on pin 1, 3 or 4. A part turned by 90 degrees
  shows up as pads off ours.
- J1 (USB-C): the opening at the board edge (y = 60 mm in the Gerbers; it overhangs it by 0.5 mm, see
  the edge rails above), the two pegs in the unplated holes and the four shell tabs in the slots. The
  paste Gerber has openings over the four shell pads (pin-in-paste), but the stencil puts only about
  0.12 mm3 of solder there against about 0.8 mm3 of free slot, so the reflow leaves a fillet on the bottom
  at most: the tabs that carry the load of the plug are soldered from the top, by hand in the economic
  variant ([Mechanics](mechanics.md#hand-soldering)), by JLCPCB in the full one (its remark above).
- The 35 diodes (D...): every cathode band of JLC's footprint on the pad with our silk bar, the pad
  towards the electronics strip (for the five RANGE diodes that is away from the RANGE control). Check
  every one of them and correct any reversed diode in the preview. The firmware can't fix a mixed
  reversal. A uniform one (all 35 the same way) could be scanned with the roles swapped
  (`KeyMatrix(row_pins=COL_PINS, column_pins=ROW_PINS, columns_to_anodes=True)`, and `boot.py` driving
  GP6 and reading GP2 for SHIFT), but then the read lines only have the RP2040's weak internal pull-ups
  and the phantom presses the 10 k column pull-ups prevent come back. `columns_to_anodes=False` keeps the
  roles but reads the columns against internal pull-downs, which R_PU0 to R_PU6 overpower (every key
  would read pressed) until they come off the board. Neither is a plan: check the diodes in the preview.
- The resistors and capacitors have no polarity: only check they sit on their pads.

The CPL gives every bottom rotation in JLCPCB's convention for the bottom side (seen from the bottom, the
part is JLC's library footprint turned counter-clockwise by the rotation, as KiBot's JLCPCB filter and the
kicad-jlcpcb-tools plugin write it), and [pcb/check.py](../pcb/check.py) fits each of JLC's footprints onto
our pads with that convention. JLC has changed how it reads bottom rotations before, so if the preview shows
a part turned, correct its rotation there in the preview (or ask JLC's engineer in the review) rather than
ordering as is. A footprint that is not mirrored cannot be fixed by a rotation; check.py asserts the pin
order of every bottom-side part.

Full variant, top side as well (the top silkscreen has no polarity marks, so go by the pads and holes):

- LED_SHIFT and LED_UNIT: the cathode pin of JLC's footprint (away from its "+" mark) on our square pad.
- ENC_ALTHDG, ENC_FREQ, ENC_FMS: JLC's footprint on all eight pin holes and the two lug slots, with its
  two-pin row (the push switch) on the side of the three-pin row towards the J1 edge.
- RANGE: all ten pin holes and JLC's unplated hole on our locating hole; the pattern fits one way only.
- K00 to K36: each footprint on the four holes of its key (either way round is the same switch).

### Review watch items

Items below JLC's published minimums, where the design leaves no room; expect a question in their review:

- SLA light pipes: the Ø1.5 and Ø1.3 mm rods, 3.6 mm long, exceed the resin pillar guideline (Ø1.0 up to
  1 mm, Ø2.0 up to 4 mm). If flagged or broken, use the PMMA fibre fallback in the table above.
- SLA outer knob key: 1.4 mm wide, under the 1.5 mm asked for positioning features; at 1.5 a key printed
  0.2 mm wide would no longer clear the narrowest shaft slot (1.7 mm).
- WJP caps: the set dimples leave 1.11 mm to the socket and the outline, 0.86 mm on a print with the
  outline 0.2 mm small and both holes 0.3 mm large (no spot between the 3.8 mm socket and a 6.4 mm wide
  cap keeps 1.0 there); the socket wall is 1.05 mm on such a print. The tactile bars are 1.0 mm wide but
  only 0.5 mm proud (embossed detail 0.8 mm), so the front bars don't hide the SHIFT and DN legends.
- MJF body: the screw bosses are fastener features at 1.6 mm (seat under the PCB, wall round the
  counterbore; over JLC3DP's 1.5 mm for fasteners, under the 2.0 mm general wall for parts over 100 mm).
  Every other wall, rib and the floor is 2.0 mm or more, bar the front edge of the floor: the 6° bottom
  plane leaves 1.6 mm there, about 1.8 mm just inside the front wall and 2.0 mm from about 3.8 mm in.
- JLCPCB: the paste layer has openings on the four J1 shell pads (pin-in-paste). If their engineer drops
  them from the stencil, nothing changes: the tabs are soldered from the top anyway, by hand in the
  economic variant (bring-up step 1, [Mechanics](mechanics.md#hand-soldering)), by JLCPCB in the full one.
- JLCPCB, full variant: the through-hole remark above. If their engineer says a part cannot be seated as
  asked (the LEDs flush, the encoders and the RANGE control flat), leave that part out of the assembly
  and solder it by hand ([Mechanics](mechanics.md#hand-soldering)) rather than accept it standing proud.

## Parts and quotes

UV print on JLCCNC parts may blur slightly at the edges; the shift legends are 1.7 mm tall, so ask for a
sample or accept the risk. Laser marking alone would make every legend grey.

Key caps, one file per set: JLC3DP's guidelines ask for one part per file (up to 10 files per quote), and
their connected-parts option (small parts joined in one file) is not offered for WJP full colour. Upload
`caps-A.zip` to `caps-D.zip` and see whether the quote or the review accepts 28 separate caps per file; if
they ask for single parts, ask their support first, or upload the files in `caps-single-A.zip` to `-D`
(one zip per cap, each with its own texture tile, the set letter in its name) in batches of 10. All four
sets are needed: only one of them will fit, and which one depends on the print. The light pipes are one
part on their bar, the knobs one part each.

The dual encoders are Bourns PEC11D-4120F-S0015 (C19270361, $8.26 at LCSC, 68 in stock on 2026-11-09 and
2026-11-11): in production, 30 detents / 15 pulses with push like the Alps EC11EBB24C03 drawn first (not
recommended for new designs), with 5 mm shorter shafts. Same footprint apart from the pin holes (1.2 mm),
so the board kept its routing. Order the encoders early; stock is small (three for the economic variant,
six for the full one).

Quotes on 2026-11-09 (Germany; JLCCNC in USD and subject to their review). They predate the switch to
Bourns encoders (new holes), the bottom-only BOM, the thicker body bosses, the knob fit variants, the
knob files (`knob-outer-22` and `knob-outer-24` are gone: now `knob-outer` x2, `knob-outer-fms` x1 and
the variants, all Ø17) and the mechanical rework (glued standoffs instead of threads, deeper pockets,
hollow body, four cap sets with rigid ribs, light pipes, the FMS ring and its fit variants), so re-upload
the board, plate and all JLC3DP files before paying. The JLC3DP price below is too low: it covers one set
of caps, the order now has four:

| Order | Price | Shipping |
| --- | --- | --- |
| JLCPCB, economic variant: 5 boards, 2 assembled (Economic, SMD side) | €71.95 | about €21 (DHL) |
| JLCPCB, full variant: 5 boards, 2 assembled (Standard, both sides incl. through-hole) | €227.43 | |
| JLCCNC: front plate | $30.09 | $26.60 (UPS) |
| JLC3DP: body, knobs, caps, light pipes (quoted with four printed spacers, now dropped) | €42.10 | €7.13 |
| LCSC (economic variant only): through-hole parts for one panel | about €37 (three dual encoders about €22) | separate |

Hand-soldering the through-hole parts saves about €118 over Standard assembly (€155 less the about €37 of
LCSC parts for one board). Rough total for the first panel with the spare board: about €250 to 300
including shipping in the economic variant, about €370 to 420 in the full one, plus the standoffs, screws
and consumables.

## Checklist

1. Run `./build.sh`; it must finish with every check passing.
2. Pick the [assembly variant](#assembly-variants). JLCPCB: upload `gerbers.zip`; board options as in the
   table (4 layers, 1.6 mm, ENIG, green, tented, 0.3 mm via); 2 boards. Confirm Parts Placement: yes, and
   Review Before Payment if offered; Edge Rails/Fiducials: Added by JLCPCB, short edges only, with the J1
   remark above.
   - Economic: Economic assembly, bottom side; upload `BOM.csv` and `CPL.csv`.
   - Full: Standard assembly, both sides; upload `BOM-full.csv` and `CPL-full.csv`, check that the BOM step
     finds all 23 lines with stock for 2 boards (six encoders; if not, see
     [above](#full-variant-through-hole-parts-at-jlcpcb)), and add the through-hole remark to the edge-rail
     remark.

   Go through the [placement preview](#placement-preview), top side too in the full variant. The boards
   come with the rails on: break them off, sand the edges flush and the board to 160.2 mm or shorter on
   arrival ([Mechanics](mechanics.md#on-arrival)).
3. JLC3DP: body (MJF), `caps-A.zip` to `caps-D.zip` (full colour, all four sets), knobs with the counts
   in the table, including the eight fit variants, light pipes (8001, quantity 2). Add them to the JLCPCB
   cart if offered.
4. JLCCNC: `plate.step`, `plate-drawing.pdf` and `plate.dxf`; finishes as in the table, and the remark
   above for the pockets, the laser marking and the amber UV print; pay after their review.
5. LCSC: economic variant only, upload `THT-LCSC.csv` to the BOM tool and order the encoders early (small
   stock); optionally add the second through-hole set for the spare board (see the table). Either variant:
   add the standoffs, screws, washers and feet from the table if you have none. Ship it on its own (see
   the €150 note above).
6. Locally: the consumables and tools from the table and, if wanted, the notched 2 mm steel plate
   (`steel.dxf`).
7. Bench: the Pico, buttons, encoder and diode from the table, to run the firmware before the boards
   arrive ([Firmware](firmware.md#pico-bench)).
8. [Before paying](#before-paying): the review watch items, and the JLC cart total of goods: over €150,
   pay and ship JLC3DP as its own order (or expect a customs fee on delivery). Check the tax lines of every
   order.
