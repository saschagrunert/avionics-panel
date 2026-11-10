# Ordering

The board, the plate and the printed parts come from the JLC group (JLCPCB, JLCCNC, JLC3DP), the
through-hole parts from LCSC; standoffs, screws, washers, feet, consumables and the optional steel plate
come from LCSC or a local shop. The files are in [production/](../production/); every file name there
starts with `avionics-panel-rev1-`, which the tables below leave out (`body.step` is
`avionics-panel-rev1-body.step`).

| Part | Service | Process | Files in `production/` |
| --- | --- | --- | --- |
| Board, assembled | JLCPCB | 4 layers, 1.6 mm thick, ENIG, green solder mask, via covering "Tented" (below), 0.3 mm min. via; Economic assembly, bottom side (all SMD), 2 boards; Confirm Parts Placement: yes, and Review Before Payment if offered; Edge Rails/Fiducials: Added by JLCPCB, on the two short edges only (below; break them off on arrival); BOM and CPL list the bottom side only | `gerbers.zip`, `BOM.csv`, `CPL.csv` |
| Through-hole parts | LCSC, hand-soldered | keys, encoders, RANGE control, LEDs for one board plus spares (30 keys, 5 + 5 LEDs). The spare board needs its own set if the first one fails after its keys are on (desoldering 28 keys rarely leaves them reusable): optionally add 28 keys, 1 RANGE control and, if wanted, 3 encoders (the 4 + 4 spare LEDs already cover its LEDs) | `THT-LCSC.csv` (LCSC BOM tool) |
| Front plate | JLCCNC | 4 mm aluminium 6061, CNC from the back, bead blasting + black anodising (matte), laser marking, no threads; the form allows two finishes, so the amber UV print goes into the remark (below) | `plate.step`, `plate-drawing.pdf` (back face, pockets), `plate.dxf` (marking) |
| Body | JLC3DP | MJF PA12-HP, dyed black | `body.step` (`body.stl` if the STEP is refused) |
| Key caps | JLC3DP | WJP Full Color Resin, four full sets of 28 caps (A, B, C, D: rib circles 3.15, 3.25, 3.35, 3.05 mm, marked with 1, 2, 3, 4 dimples on the underside), quantity 1 each; upload the zips, they carry the texture (the OBJ alone prints without legends). One set fits, see [Mechanics](mechanics.md#caps-light-pipes-knobs). If JLC3DP wants one part per file, see below | `caps-A.zip` to `caps-D.zip` (`caps-single-A.zip` etc.: one zip per cap) |
| Knobs | JLC3DP | SLA Black Resin: `knob-outer` x2 (ALT/HDG, FREQ), `knob-outer-fms` x1 (same fits, coarser grip), `knob-inner` x3, `knob-range` x1, plus one each of `knob-outer-tight`, `-loose`, `knob-outer-fms-tight`, `-loose`, `knob-inner-tight`, `-loose`, `knob-range-tight`, `-loose` (bore 0.2 mm under / over nominal; the knobs are held by friction, keep whichever grips) | `knob-*.step` |
| Light pipes | JLC3DP | SLA 8001 Resin, transparent, quantity 2 (one spare); both pipes on one snap-off bar (JLC3DP prints resin from 10 x 2 x 2 mm only); break off, sand, polish the top, glue in with clear epoxy or UV glue. The rods (Ø1.5 and Ø1.3, 3.6 mm long) are longer than JLC3DP's resin pillar guideline, so the review may flag them or they may break: the fallback is below | `lightpipes.step` |
| Light pipe fallback | local or online | PMMA end-glow optical fibre (plastic fibre for lamps and models), Ø1.5 mm for SHIFT and Ø1.0 to 1.25 mm for UNIT, a few cm of each; cut to 3.6 mm with a fresh blade, sand both ends flat and polish them | |
| Standoffs | LCSC or local | 6 (2 spare) hex standoffs M2.5 x 8, female-female, 5 mm across flats, threaded through, 8.0 ±0.1 long, brass (nickel-plated) or aluminium; for example Würth 970080154 (check that the listing says female-female and 5 mm across flats) | |
| Screws, washers, feet | LCSC or local | 6 x M2.5 x 8 pan head (ISO 7045 or ISO 14583; 2 spare), 6 x DIN 125-A (ISO 7089) M3 washers (3.2 x 7 x 0.5), one under every head; 4 self-adhesive feet up to 10 mm across | |
| Consumables | local | thixotropic (non-sag, paste) two-part epoxy with at least 30 minutes of working time for the standoffs, for example Araldite 2014-1 (not a runny clear epoxy); clear epoxy or UV glue for the light pipes (not CA glue); soft wax or plasticine to plug the standoff threads while gluing, a toothpick to press it in; isopropyl alcohol, fine sandpaper (up to about 1000 grit, plus plastic polish for the light-pipe tops), a stiff card and a release film (a piece of PE bag or baking paper; or low-tack tape) to hold the light pipes flush, double-sided tape for the steel plate, a data-capable USB-C cable (a charge-only cable shows no RPI-RP2 drive). Tools: two blocks at least 25 mm high (books, wood) and a cloth for face-down assembly, two more to rest the body on, a feeler gauge set (0.1 mm for the board-bow check on arrival, about 0.8 mm for the body gap; a 0.8 mm drill shank also works for the gap), a 5 mm nut driver, a PH1 (ISO 7045) or T8 (ISO 14583) screwdriver for the M2.5 pan heads, a flat file or 240 grit sandpaper on a flat block for the edge-rail stubs and the board corners, calipers for the board length, soldering iron, solder and flux, side cutters for the LED legs; if a knob bore is tight, 6.0, 3.5 and 2.5 mm drills and a needle file | |
| Steel plate (optional) | local or laser cut | 2 mm steel, 143 x 36 mm (±0.1) with two 15 x 15 mm notches at the back corners for the feet (about 74 g), desk weight in the 144 x 37 mm recess under the body, double-sided tape | `steel.dxf` (outline) |
| Bench (before the boards) | local or online | Raspberry Pi Pico with headers and a data-capable micro-USB cable, a breadboard and jumper wires, a few push buttons, one cheap EC11-type encoder with push and 30 detents / 15 pulses per turn, like the PEC11D (not one of the three PEC11D; a 20 / 20 part, common among cheap EC11 and KY-040 encoders, needs `divisor=4` in `code.py`, see [Firmware](firmware.md#install-and-bring-up)), a 1N4148 diode for SHIFT from GP6 to GP2 (see [Firmware](firmware.md#install-and-bring-up)) | |

Every part number in the BOM is set. The 27 R USB series resistors (C25190) are an extended part at
JLCPCB now, so they add one extended-part fee (about $3) to the assembly quote. They stay 27 R, the value
in Raspberry Pi's design ([Electronics](electronics.md)); 22 R (C23345, basic, already on the board for
the white LED) would save the fee. The column pull-ups (10 k, C25804) are a basic part.

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

The boards arrive with the rails still on (JLCPCB's default). Before anything else, break off the
V-scored rails and file or sand both short edges flush (outdoors or wet: glass-fibre dust). With a 5 mm
rail on each short edge the board is about 170 mm long and doesn't go into the body, and the bow check on
arrival ([Status](status.md#before-ordering)) assumes a bare edge. Then measure the length with calipers
and sand both short edges about equally, only as much as needed, until the board is 160.2 mm or shorter.
A V-cut edge is only held to ±0.4 mm (a routed one to ±0.2): the cavity is 161.0 mm long, 160.36 mm
with the body printed 0.4 % small, so a board of 160.4 mm would not go in (`check_fit.py` has the row).
If a corner comes back square, file it to R3. JLCPCB can also remove the rails for a fee; ask in the
order remark if you prefer, and still measure the length.

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
order on its own (or expect the customs fee on delivery). Ship the LCSC order on its own too: added to a
JLC parcel it takes that over the line.
JLCPCB assembles at least 2 boards (bare boards come in 5). Order 2 assembled boards but only one set of
plate, body, caps and knobs; the second board is the spare for the first, untested chip-down design.

Before paying, check every assembled part in the JLCPCB placement preview of the bottom side. The
preview draws JLC's own footprint over our pads; the marks below are on our bottom silkscreen, so they
hold whichever way round the preview shows the board:

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
  at most: the tabs that carry the load of the plug are soldered from the top by hand (see
  [Mechanics](mechanics.md#hand-soldering)).
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

The CPL gives every rotation in JLCPCB's convention for the bottom side (seen from the bottom, the part is
JLC's library footprint turned counter-clockwise by the rotation, as KiBot's JLCPCB filter and the
kicad-jlcpcb-tools plugin write it), and [pcb/check.py](../pcb/check.py) fits each of JLC's footprints onto
our pads with that convention. JLC has changed how it reads bottom rotations before, so if the preview shows
a part turned, correct its rotation there in the preview (or ask JLC's engineer in the review) rather than
ordering as is. A footprint that is not mirrored cannot be fixed by a rotation; check.py asserts the pin
order of every bottom-side part.

UV print on JLCCNC parts may blur slightly at the edges; the shift legends are 1.7 mm tall, so ask for a
sample or accept the risk. Laser marking alone would make every legend grey.

Key caps, one file per set: JLC3DP's guidelines ask for one part per file (up to 10 files per quote), and
their connected-parts option (small parts joined in one file) is not offered for WJP full colour. Upload
`caps-A.zip` to `caps-D.zip` and see whether the quote or the review accepts 28 separate caps per file; if
they ask for single parts, ask their support first, or upload the files in `caps-single-A.zip` to `-D`
(one zip per cap, each with its own texture tile, the set letter in its name) in batches of 10. All four
sets are needed: only one of them will fit, and which one depends on the print. The light pipes are one
part on their bar, the knobs one part each.

The dual encoders are Bourns PEC11D-4120F-S0015 (C19270361, $8.26 at LCSC, 68 in stock on 2026-11-09):
in production, 30 detents / 15 pulses with push like the Alps EC11EBB24C03 drawn first (not recommended
for new designs), with 5 mm shorter shafts. Same footprint apart from the pin holes (1.2 mm), so the
board kept its routing. Order the three encoders early; stock is small.

Quotes on 2026-11-09 (Germany; JLCCNC in USD and subject to their review). They predate the switch to
Bourns encoders (new holes), the bottom-only BOM, the thicker body bosses, the knob fit variants, the
knob files (`knob-outer-22` and `knob-outer-24` are gone: now `knob-outer` x2, `knob-outer-fms` x1 and
the variants, all Ø17) and the mechanical rework (glued standoffs instead of threads, deeper pockets,
hollow body, four cap sets with rigid ribs, light pipes, the FMS ring and its fit variants), so re-upload
the board, plate and all JLC3DP files before paying. The JLC3DP price below is too low: it covers one set
of caps, the order now has four:

| Order | Price | Shipping |
| --- | --- | --- |
| JLCPCB: 5 boards, 2 assembled (Economic, SMD side) | €71.95 | about €21 (DHL) |
| JLCPCB, for comparison: Standard assembly of both sides incl. through-hole | €227.43 | |
| JLCCNC: front plate | $30.09 | $26.60 (UPS) |
| JLC3DP: body, knobs, caps, light pipes (quoted with four printed spacers, now dropped) | €42.10 | €7.13 |
| LCSC: through-hole parts for one panel | about €37 (three dual encoders about €22) | separate |

Hand-soldering the through-hole parts saves about €118 over Standard assembly (€155 less the about €37 of
LCSC parts). Rough total for the first panel with the spare board: about €250 to 300 including shipping,
plus the standoffs, screws and consumables.

## Checklist

1. Run `./build.sh`; it must finish with every check passing.
2. JLCPCB: upload `gerbers.zip`, then `BOM.csv` and `CPL.csv`; board options as in the table (4 layers,
   1.6 mm, ENIG, green, tented, 0.3 mm via); Economic assembly, bottom side, 2 boards. Confirm Parts
   Placement: yes, and Review Before Payment if offered; Edge Rails/Fiducials: Added by JLCPCB, short
   edges only, with the J1 remark above. Go through the placement preview above. The boards come with
   the rails on: break them off, sand the edges flush and the board to 160.2 mm or shorter on arrival (see
   the edge rails above).
3. JLC3DP: body (MJF), `caps-A.zip` to `caps-D.zip` (full colour, all four sets), knobs with the counts
   in the table, including the eight fit variants, light pipes (8001, quantity 2). Add them to the JLCPCB
   cart if offered.
4. JLCCNC: `plate.step`, `plate-drawing.pdf` and `plate.dxf`; finishes as in the table, and the remark
   above for the pockets, the laser marking and the amber UV print; pay after their review.
5. LCSC: upload `THT-LCSC.csv` to the BOM tool and order the encoders early (small stock). Optionally add
   the second through-hole set for the spare board (see the table). Add the standoffs, screws, washers and
   feet from the table if you have none. Ship it on its own (see the €150 note above).
6. Locally: the consumables and tools from the table and, if wanted, the notched 2 mm steel plate
   (`steel.dxf`).
7. Bench: the Pico, buttons, encoder and diode from the table, to run the firmware before the boards
   arrive.
8. Before paying, read the JLC cart total of goods: over €150, pay and ship JLC3DP as its own order (or
   expect a customs fee on delivery). Check the tax lines of every order.
