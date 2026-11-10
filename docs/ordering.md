# Ordering

Everything comes from the JLC group. The files are in [production/](../production/).

| Part | Service | Process | Files in `production/` |
| --- | --- | --- | --- |
| Board, assembled | JLCPCB | 4 layers, ENIG, 0.3 mm min. via; Economic assembly, bottom side (all SMD), 2 boards, confirm parts placement; BOM and CPL list the bottom side only | `gerbers.zip`, `BOM.csv`, `CPL.csv` |
| Through-hole parts | LCSC, hand-soldered | keys, encoders, RANGE control, LEDs for one panel plus spares | `THT-LCSC.csv` (LCSC BOM tool) |
| Front plate | JLCCNC | 4 mm aluminium 6061, CNC from the back in one setup, bead blasting + black anodising (matte), laser marking, threads: yes; the form allows two finishes, so the orange UV print and the threads go into the remark (below) | `plate.step`, `plate-drawing.pdf` (threads), `plate.dxf` (marking) |
| Body | JLC3DP | MJF PA12-HP, dyed black; 4 printed spacers (`spacer.step`) only as a fallback for the metal ones | `body.step` |
| Key caps | JLC3DP | WJP Full Color Resin; upload the zip, it carries the texture (the OBJ alone prints without legends) | `caps.zip` |
| Knobs | JLC3DP | SLA Black Resin: `knob-outer-22` x2, `knob-outer-24` x1, `knob-inner` x3, `knob-range` x1, plus one each of `knob-outer-22-tight`, `-loose`, `knob-inner-tight`, `-loose`, `knob-range-tight`, `-loose` (bore 0.1 mm under / over nominal; the knobs are held by friction, keep whichever grips) | `knob-*.step` |
| Light pipes | JLC3DP | SLA 8001 Resin, transparent; both on one snap-off bar (JLC3DP prints resin from 2 x 2 x 10 mm only); break off, sand, polish the top, glue in with clear epoxy or UV glue | `lightpipes.step` |
| Screws, washers, feet | LCSC or local | 4 x M2.5 x 12 pan head (ISO 7045 or ISO 14583, no socket heads), 20 x DIN 125-A (ISO 7089) M3 washers (3.2 x 7 x 0.5): one under every head, up to three more to shim the screws to fit, 4 self-adhesive feet up to 10 mm across | |
| Spacers | local | 4 round metal spacers, unthreaded, 6.0 mm (±0.05) long, 5 mm OD, about 2.7 mm ID (2.8 max, M2.5), aluminium or brass; no LCSC part found, so buy them locally | |
| Steel plate (optional) | local or laser cut | 2 mm steel, 144 x 48 mm with two 15 x 15 mm notches at the back corners for the feet (about 100 g), desk weight in the recess under the body, double-sided tape | |

Every part number in the BOM is set.

JLCCNC remark for the threads: "4 x M2.5 blind threads from the back, thread milled in flat-bottom holes
3.2 +0/-0.1 mm deep, full thread from 0.1 to at least 2.6 mm, no countersink (see plate-drawing.pdf).
Plate 4.0 ±0.1; hole and pocket depths +0/-0.1: at least 0.7 mm must stay to the front face. Thread and hole positions
±0.1 mm to each other. Please mask the threads before anodising, or chase them after anodising."

All four shops share one JLC account but have their own checkout. JLC3DP items can join the JLCPCB
cart and be paid together; LCSC can combine its shipment with a JLCPCB order (choose it at the LCSC
checkout); JLCCNC is paid separately after its review. Payment by PayPal, card or Google Pay. Under
€150 per shipment JLC collects German VAT at checkout (IOSS); since July 2026 a customs duty and a
disbursement fee can come on top, so check the tax lines before paying. A combined shipment over €150
is cleared on delivery instead, with the carrier's fee.
JLCPCB assembles at least 2 boards (bare boards come in 5). Order 2 assembled boards but only one set of
plate, body, caps and knobs; the second board is the spare for the first, untested chip-down design.

Before paying, check in the JLCPCB placement preview (bottom side seen from the top, so mirrored):

- Pin 1 of U1 (RP2040) at the bottom of its west side, next to the silk corner mark; pins run clockwise.
- Pin 1 of U2 (flash) bottom-right, U3 (regulator) on the north-east pad, Y1 (crystal) top-right.
- J1 (USB-C): contact A1/B12 on the left (-x) end of the pad row, shell pegs in the NPTH holes.
- The two LEDs with the flat (cathode) on the square pad; encoders and the RANGE control inside their outlines.
- The 35 diodes: every cathode band on the east (+x) side, towards the electronics strip (for the five
  RANGE diodes that is away from the RANGE control). A reversal is not fatal if all of them are
  reversed the same way (the firmware then needs `columns_to_anodes=False`); the ICs cannot be rescued
  like that.

JLC can fix a rotation in the preview, but not a footprint that is not mirrored;
[pcb/check.py](../pcb/check.py) asserts the pin order of every bottom-side part.

UV print on JLCCNC parts may blur slightly at the edges; the shift legends are 1.7 mm tall, so ask for a
sample or accept the risk. Laser marking alone would make every legend grey.

The dual encoders are Bourns PEC11D-4120F-S0015 (C19270361, $8.26 at LCSC, 68 in stock on 2026-11-09):
in production, 30 detents / 15 pulses with push like the Alps EC11EBB24C03 drawn first (not recommended
for new designs), with 5 mm shorter shafts. Same footprint apart from the pin holes (1.2 mm), so the
board kept its routing. Order the three encoders early; stock is small.

Quotes on 2026-11-09 (Germany; JLCCNC in USD and subject to their review). They
predate the switch to Bourns encoders (new holes), the bottom-only BOM, the thicker body bosses and the
knob fit variants, and the mechanical rework (milled threads, deeper pockets, larger
PCB mounting holes, hollow body, cap sockets, light pipes), so re-upload those files before paying:

| Order | Price | Shipping |
| --- | --- | --- |
| JLCPCB: 5 boards, 2 assembled (Economic, SMD side) | €71.95 | about €21 (DHL) |
| JLCPCB, for comparison: Standard assembly of both sides incl. through-hole | €227.43 | |
| JLCCNC: front plate | $30.09 | $26.60 (UPS) |
| JLC3DP: body, spacers, knobs, caps, light pipes | €42.10 | €7.13 |
| LCSC: through-hole parts for one panel | about €37 (three dual encoders about €22) | separate |

Hand-soldering the through-hole parts saves about €118 over Standard assembly (€155 less the about €37 of
LCSC parts). Rough total for the first
panel with the spare board: about €250 to 300 including shipping.

## Checklist

1. Run `./build.sh`; it must finish with every check passing.
2. JLCPCB: upload `gerbers.zip`, then `BOM.csv` and `CPL.csv`; Economic assembly, bottom side, 2
   boards. Tick "review before payment" and go through the placement preview above.
3. JLC3DP: body (MJF; add the printed spacers only without metal ones), `caps.zip` (full colour), knobs
   with the counts in the table, including the six fit variants, light pipes (8001). Add them to the
   JLCPCB cart if offered.
4. JLCCNC: `plate.step` and `plate-drawing.pdf`, finishes and remark as in the table; pay after their
   review.
5. LCSC: upload `THT-LCSC.csv` to the BOM tool, order the encoders early (small stock), and combine the
   shipment with the JLCPCB order. Add 4 M2.5 x 12 pan-head screws, 20 DIN 125 M3 washers and 4 feet
   if you have none.
6. Locally: 4 metal spacers (5 x 6.0 mm, M2.5) and, if wanted, the notched 2 mm steel plate (144 x 48 mm).
7. Check the tax lines before paying.
