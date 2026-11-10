# Ordering

The board, the plate and the printed parts come from the JLC group (JLCPCB, JLCCNC, JLC3DP), the
through-hole parts from LCSC; standoffs, screws, washers, feet, consumables and the optional steel plate
come from LCSC or a local shop. The files are in [production/](../production/); every file name there
starts with `avionics-panel-rev1-`, which the tables below leave out (`body.step` is
`avionics-panel-rev1-body.step`).

| Part | Service | Process | Files in `production/` |
| --- | --- | --- | --- |
| Board, assembled | JLCPCB | 4 layers, 1.6 mm thick, ENIG, green solder mask, via covering "Tented" (below), 0.3 mm min. via; Economic assembly, bottom side (all SMD), 2 boards, confirm parts placement; BOM and CPL list the bottom side only | `gerbers.zip`, `BOM.csv`, `CPL.csv` |
| Through-hole parts | LCSC, hand-soldered | keys, encoders, RANGE control, LEDs for one panel plus spares | `THT-LCSC.csv` (LCSC BOM tool) |
| Front plate | JLCCNC | 4 mm aluminium 6061, CNC from the back in one setup, bead blasting + black anodising (matte), laser marking, no threads; the form allows two finishes, so the amber UV print goes into the remark (below) | `plate.step`, `plate-drawing.pdf` (back face, pockets), `plate.dxf` (marking) |
| Body | JLC3DP | MJF PA12-HP, dyed black | `body.step` (`body.stl` if the STEP is refused) |
| Key caps | JLC3DP | WJP Full Color Resin, four full sets of 28 caps (A, B, C, D: rib circles 3.15, 3.25, 3.35, 3.05 mm, marked with 1, 2, 3, 4 dimples on the underside), quantity 1 each; upload the zips, they carry the texture (the OBJ alone prints without legends). One set fits, see [Mechanics](mechanics.md#caps-light-pipes-knobs). If JLC3DP wants one part per file, see below | `caps-A.zip` to `caps-D.zip` (`caps-single-A.zip` etc.: one zip per cap) |
| Knobs | JLC3DP | SLA Black Resin: `knob-outer` x2 (ALT/HDG, FREQ), `knob-outer-fms` x1 (same fits, coarser grip), `knob-inner` x3, `knob-range` x1, plus one each of `knob-outer-tight`, `-loose`, `knob-outer-fms-tight`, `-loose`, `knob-inner-tight`, `-loose`, `knob-range-tight`, `-loose` (bore 0.2 mm under / over nominal; the knobs are held by friction, keep whichever grips) | `knob-*.step` |
| Light pipes | JLC3DP | SLA 8001 Resin, transparent, quantity 2 (one spare); both pipes on one snap-off bar (JLC3DP prints resin from 10 x 2 x 2 mm only); break off, sand, polish the top, glue in with clear epoxy or UV glue. The rods (Ø1.5 and Ø1.3, 3.9 mm long) are longer than JLC3DP's resin pillar guideline, so the review may flag them or they may break: the fallback is below | `lightpipes.step` |
| Light pipe fallback | local or online | PMMA end-glow optical fibre (plastic fibre for lamps and models), Ø1.5 mm for SHIFT and Ø1.0 to 1.25 mm for UNIT, a few cm of each; cut to 3.9 mm with a fresh blade, sand both ends flat and polish them | |
| Standoffs | LCSC or local | 6 (2 spare) hex standoffs M2.5 x 8, female-female, 5 mm across flats, threaded through, 8.0 ±0.1 long, brass (nickel-plated) or aluminium; for example Würth 970080154 (check that the listing says female-female and 5 mm across flats) | |
| Screws, washers, feet | LCSC or local | 6 x M2.5 x 8 pan head (ISO 7045 or ISO 14583; 2 spare), 6 x DIN 125-A (ISO 7089) M3 washers (3.2 x 7 x 0.5), one under every head; 4 self-adhesive feet up to 10 mm across | |
| Consumables | local | thixotropic (non-sag, paste) two-part epoxy with at least 30 minutes of working time for the standoffs, for example Araldite 2014-1 (not a runny clear epoxy); clear epoxy or UV glue for the light pipes (not CA glue); soft wax or plasticine to plug the standoff threads while gluing; isopropyl alcohol, fine sandpaper, masking tape, double-sided tape for the steel plate, a data-capable USB-C cable (a charge-only cable shows no RPI-RP2 drive) | |
| Steel plate (optional) | local or laser cut | 2 mm steel, 144 x 37 mm with two 15 x 15 mm notches at the back corners for the feet (about 77 g), desk weight in the recess under the body, double-sided tape | `steel.dxf` (outline) |

Every part number in the BOM is set.

JLCCNC remark: "No threads. 4 x round flat-bottom pockets dia 7.0 +0.1/-0 from the back, 2.0 +0/-0.1 mm
deep (see plate-drawing.pdf). Plate 4.0 ±0.1; all pocket depths +0/-0.1: at least 0.7 mm must stay to the
front face. Light holes dia 1.8 and 1.6 +0.1/-0. Pocket and hole positions ±0.1 mm to each other. Front
marking per plate.dxf, same origin and orientation as the STEP (bottom-left corner seen from the front);
DXF units: mm; fill closed contours even-odd (the holes in letters such as A, D and O are separate
contours). Layer LASER = laser marking; layer UV_AMBER = UV print in amber #D9A441 (RGB 217, 164, 65;
Pantone 7563 C, roughly RAL 1004); layer CUT = outline and through holes, for alignment only, not to be
marked."

Keep the solder mask green: the mask dams between the RP2040's pads, between the USB-C contacts and
between C_X2 and R_X are 0.1 mm, JLCPCB's minimum for green ([pcb/check.py](../pcb/check.py) measures
them). Other colours need wider dams, so those pads would lose the mask between them.

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
- J1 (USB-C): the opening at the board edge, the two pegs in the unplated holes and the four shell tabs
  in the slots. The paste Gerber has openings over the four shell pads (pin-in-paste), so the reflow
  solders the tabs that carry the load of the plug; if a tab comes back unsoldered, solder it from the top
  (see [Mechanics](mechanics.md#hand-soldering)).
- The 35 diodes (D...): every cathode band of JLC's footprint on the pad with our silk bar, the pad
  towards the electronics strip (for the five RANGE diodes that is away from the RANGE control). A
  reversal is not fatal if all of them are reversed the same way (the firmware then needs
  `columns_to_anodes=False`); the ICs cannot be rescued like that.
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
   1.6 mm, ENIG, green, tented, 0.3 mm via); Economic assembly, bottom side, 2 boards. Tick "review
   before payment" and go through the placement preview above.
3. JLC3DP: body (MJF), `caps-A.zip` to `caps-D.zip` (full colour, all four sets), knobs with the counts
   in the table, including the eight fit variants, light pipes (8001, quantity 2). Add them to the JLCPCB
   cart if offered.
4. JLCCNC: `plate.step`, `plate-drawing.pdf` and `plate.dxf`; finishes as in the table, and the remark
   above for the pockets, the laser marking and the amber UV print; pay after their review.
5. LCSC: upload `THT-LCSC.csv` to the BOM tool and order the encoders early (small stock). Add the
   standoffs, screws, washers and feet from the table if you have none. Ship it on its own (see the
   €150 note above).
6. Locally: the consumables from the table and, if wanted, the notched 2 mm steel plate (`steel.dxf`).
7. Before paying, read the JLC cart total of goods: over €150, pay and ship JLC3DP as its own order (or
   expect a customs fee on delivery). Check the tax lines of every order.
