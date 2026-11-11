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
| Edge rails | none: the milled outline fits the body as delivered ([edge rails](#edge-rails)) | one rail of at least 10 mm on the long edge away from J1, removed on arrival ([edge rails](#edge-rails)) |
| Order remark | the J1 overhang ([edge rails](#edge-rails)) | the edge-rail remark and the [through-hole remark](#full-variant-through-hole-parts-at-jlcpcb) |
| Extended parts (2026-11-11) | RP2040, flash, crystal, J1, and the 27 R (a preferred extended part: no fee in Economic assembly) | the same plus the five through-hole parts |
| Quote 2026-11-09 (both predate the latest changes: re-quote) | about €72 for 2 boards, plus about €37 at LCSC for one set of through-hole parts | €227.43 for 2 fully populated boards (see [quotes](#parts-and-quotes)) |
| On arrival | [mechanics](mechanics.md#on-arrival), then the hand-soldering in the bring-up | [mechanics](mechanics.md#on-arrival): remove the rail, then the full-variant checks; the iron only for the J1 tabs and any rework |
| Bring-up | the encoders and the RANGE control go on last, after the board has been tested | every part is on from the start: a board that turns out dead takes its encoders and RANGE control with it; the second board is the spare |

Both variants use the same Gerbers and the same bottom side. The full variant costs about €118 more than
the economic one with one LCSC set (about €81 more against two sets, which the economic variant needs for a
second working board), and saves 28 keys, three encoders, the RANGE control and two LEDs of hand soldering
per board, plus the risk of a bridge or a tilted part. In exchange it gives up the bring-up order that
fits the expensive parts last.

### Full variant: through-hole parts at JLCPCB

`BOM-full.csv` lists the through-hole parts by their JLC part numbers (the LCSC numbers, which JLCPCB's
parts library uses too) for one board; JLCPCB multiplies by the 2 assembled boards and adds its own few
spares of the keys and LEDs. All five are in JLCPCB's library as extended parts. JLCPCB's assembly stock is
its own: it often matches LCSC's but not always (the numbers below differ from LCSC's for four of the five),
so check JLCPCB's for the full variant and LCSC's for the economic one. JLCPCB stock on 2026-11-11:

| Part | JLC part | Library | JLC stock | Per board | For 2 boards |
| --- | --- | --- | --- | --- | --- |
| TE 1-1825910-4 key switch | C589907 | extended | 30920 | 28 | 56 |
| Bourns PEC11D-4120F-S0015 dual encoder | C19270361 | extended | 68 | 3 | 6 |
| Alps RKJXT1F42001 RANGE control | C160841 | extended | 6859 | 1 | 2 |
| XINGLIGHT XL-302UYC amber LED (SHIFT) | C2895466 | extended | 2769 | 1 | 2 |
| XINGLIGHT XL-302UWC white LED (UNIT) | C2895458 | extended | 45483 | 1 | 2 |

The encoders are the tight part: 6 of 68. As soon as you pick the full variant, buy the six encoders into
your JLCPCB parts library (Parts Manager, from JLC's own stock): parts there are yours and the assembly
takes them from it, so nobody else's order can take them first. If JLCPCB's stock drops under 6 before
that, the BOM step shows them as short, and there are three ways on:

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

The through-hole parts sit under the front plate with little room, so the order remark must say how to seat
them; JLCPCB solders them from the bottom, among the SMD parts (by hand or by selective soldering; the SMD
parts there rule out a plain wave), and `check.py` keeps 1.0 mm round every through-hole pad free of other
exposed copper for that ([Electronics](electronics.md)). The board sits 4.0 mm over the body floor (3.7 mm
with the print tolerance), and the LEDs come with legs of about 18 mm, so the remark asks for the leads to
be trimmed (JLCPCB's fee list charges extra for trimming some through-hole parts, so it is not a given;
leads that come back long are cut on arrival). Remark for the full variant, after the
[edge-rail remark](#edge-rails): "Through-hole parts on the top side: please seat every one fully down and
flat on the board before soldering, not tilted and not lifted on its leads. The two LEDs LED_SHIFT and
LED_UNIT flush on the board, at most 0.2 mm proud (a light pipe sits right above them); cathode (flat side,
short lead) on the square pad. The encoders ENC_ALTHDG, ENC_FREQ, ENC_FMS and the RANGE control flat on the
board, at most 0.05 mm proud (the front plate pockets leave only 0.25 mm over the encoders and 0.11 mm beside
their lugs, 0.10 mm over the RANGE control; please hold the RANGE control pressed down while its pins are
soldered, so the gap under its base frame is the same on all four sides); solder the encoder mounting lugs
too. The 28 keys K00 to K06, K10 to K16, K20 to K26 and K30 to K36 flat and square. Please trim every
through-hole lead of these parts to 2 mm or less below the bottom side: the board sits only 4 mm over the case
floor. Please also solder the four J1 (USB-C) shell tabs from the top side, filling the slots: the
pin-in-paste stencil openings only leave a fillet on the bottom, and the tabs carry the plug."

## Suppliers

| Part | Service | Process | Files in `production/` |
| --- | --- | --- | --- |
| Board, assembled | JLCPCB | 4 layers, 1.6 mm thick, ENIG, black solder mask with white silkscreen (below), via covering "Tented" (below), 0.3 mm min. via, outer copper 1 oz and inner 0.5 oz (the defaults), the default stackup, Mark on PCB as you like (the board is hidden in the body); PCB quantity 5, assembly quantity 2. Economic variant: Economic assembly, bottom side (all SMD), Edge Rails/Fiducials: none. Full variant: Standard assembly, both sides, through-hole parts included, Edge Rails/Fiducials: Added by JLCPCB, one rail of at least 10 mm on the long edge away from J1 ([below](#edge-rails); removed on arrival). Confirm Parts Placement: yes, Confirm Production File: yes ([below](#review-watch-items)), and Review Before Payment if offered | economic: `gerbers.zip`, `BOM.csv`, `CPL.csv`; full: `gerbers.zip`, `BOM-full.csv`, `CPL-full.csv` |
| Through-hole parts (economic variant) | LCSC, hand-soldered | keys, encoders, RANGE control, LEDs for one board plus spares (30 keys; 20 of each LED, LCSC's minimum order, of which one each is needed; the `Needed` column gives the count per board). The spare board needs its own set if the first one fails after its keys are on (desoldering 28 keys rarely leaves them reusable): optionally add 28 keys, 1 RANGE control and, if wanted, 3 encoders (the spare LEDs already cover its LEDs). The two spare keys also serve to try the cap sets on ([Mechanics](mechanics.md#on-arrival)) | `THT-LCSC.csv` (LCSC BOM tool) |
| Spare keys and RANGE control (full variant) | LCSC | 2 x TE 1-1825910-4 (C589907), loose, to try the cap sets on without pulling at a soldered switch; 1 x Alps RKJXT1F42001 (C160841), loose, the reference for the seating check of the soldered ones ([Mechanics](mechanics.md#on-arrival)) | |
| Front plate | JLCCNC | 4 mm aluminium 6061, CNC from the back, bead blasting + black anodising (matte), laser marking, no threads; the form allows two finishes, so the amber UV print goes into the remark (below). If the form has a UV colour field, pick orange there: it is only the fallback, and the remark says that it takes precedence | `plate.step`, `plate-drawing.pdf` (back face, pockets), `plate.dxf` (marking) |
| Body and USB-C filler | JLC3DP | MJF PA12-HP, dyed black, both parts: the body quantity 1, the filler quantity 2 (one spare; it closes the USB-C notch from the back, [Mechanics](mechanics.md#fastening)) | `body.step`, `usb-filler.step` (`body.stl`, `usb-filler.stl` if a STEP is refused) |
| Key caps | JLC3DP | WJP Full Color Resin, four full sets of 28 caps (A, B, C, D: rib circles 3.15, 3.25, 3.35, 3.05 mm, marked with 1, 2, 3, 4 dimples on the underside), quantity 1 each; upload the zips, they carry the texture (the OBJ alone prints without legends). One set fits, see [Mechanics](mechanics.md#caps-light-pipes-knobs). If JLC3DP wants one part per file, see below | `caps-A.zip` to `caps-D.zip` (`caps-single-A.zip` etc.: one zip per cap) |
| Knobs | JLC3DP | SLA Black Resin: `knob-outer` x2 (ALT/HDG, FREQ), `knob-outer-fms` x1 (same fits, coarser grip), `knob-inner` x3, `knob-range` x1, plus one each of `knob-outer-tight`, `-loose`, `knob-outer-fms-tight`, `-loose`, `knob-inner-tight`, `-loose`, `knob-range-tight`, `-loose` (bore 0.2 mm under / over nominal; the knobs are held by friction, keep whichever grips) | `knob-*.step` |
| Light pipes | JLC3DP | SLA 8001 Resin, transparent, quantity 2 (one spare), no post-processing (JLC3DP sands and oil-sprays 8001 by default, which can break the thin rods: pick none, or ask in the remark: "Light pipes: no sanding and no oil spray, please"); both pipes on one snap-off bar (JLC3DP prints resin from 10 x 2 x 2 mm only); break off, sand, polish the top, glue in with clear epoxy or UV glue. The rods (Ø1.5 and Ø1.3, 3.6 mm long) are longer than JLC3DP's resin pillar guideline, so the review may flag them or they may break: the fallback is below | `lightpipes.step` |
| Light pipe fallback | local or online | PMMA end-glow optical fibre (plastic fibre for lamps and models), Ø1.5 mm for SHIFT and Ø1.0 to 1.25 mm for UNIT, a few cm of each; cut to 3.6 mm with a fresh blade, sand both ends flat and polish them | |
| Standoffs | LCSC or local | 6 (2 spare) hex standoffs M2.5 x 8, female-female, 5 mm across flats, threaded through, 8.0 ±0.1 long, brass (nickel-plated) or aluminium; for example Würth 970080154 (check that the listing says female-female and 5 mm across flats) | |
| Screws, washers, feet | LCSC or local | 6 x M2.5 x 8 pan head (ISO 7045 or ISO 14583; 2 spare), 6 x DIN 125-A (ISO 7089) M3 washers (3.2 x 7 x 0.5), one under every head; 4 self-adhesive feet up to 10 mm across | |
| Consumables | local | thixotropic (non-sag, paste) two-part epoxy with at least 30 minutes of working time for the standoffs, for example Araldite 2014-1 (not a runny clear epoxy; it usually comes in a 2:1 double cartridge that needs its dispenser gun and mixing nozzles, or squeeze both parts out by weight and mix them by hand on a card); clear epoxy for the light pipes, or UV glue with a small UV lamp (not CA glue); soft wax or plasticine to plug the standoff threads while gluing, a toothpick to press it in; removable adhesive putty (Blu Tack) for the USB-C filler; isopropyl alcohol, fine sandpaper (up to about 1000 grit, plus plastic polish for the light-pipe tops), a release film (a piece of PE bag or baking paper) for the light-pipe gluing and the plate corners while the standoffs cure, double-sided tape for the steel plate, solder wick, a data-capable USB-C cable (a charge-only cable shows no RPI-RP2 drive). Tools: a flat glass plate at least 170 x 70 mm (board-bow and plate-flatness checks, light-pipe gluing), two blocks at least 25 mm high (books, wood) and a cloth for face-down assembly, two more to rest the body on, a feeler gauge set from 0.03 mm up to 1.0 mm, whose blades stack for the readings in between (0.05 mm for the encoder seating, about 0.4 mm and that plus 0.03 mm for the RKJXT's frame gap, 0.1 mm for the board-bow and plate-flatness checks, 0.2 mm for the LED seating in the full variant, about 0.8 mm for the body gap, where a 0.8 mm drill shank also works; the 1.0 mm blade pushes the USB-C filler flush), a steel rule as a straightedge (board-bow check, squaring the caps), a multimeter with a continuity beeper (bring-up steps 1 and 2, bridge checks), a magnifier or loupe, calipers (board width, lead length), a 5 mm nut driver, a PH1 (ISO 7045) or T8 (ISO 14583) screwdriver for the M2.5 pan heads, a flat file or 240 grit sandpaper on a flat block for the rail edge (full variant), soldering iron, solder and flux (in the full variant for the J1 tabs, should they come back unfilled, and any rework, such as reseating a part that stands proud), side cutters for the leads (and in the full variant for any lead that comes back longer than 2 mm); if a knob bore is tight, 6.0, 3.5 and 2.5 mm drills and a needle file | |
| Steel plate (optional) | local or laser cut | 2 mm steel, 143 x 36 mm (±0.1) with two 15 x 15 mm notches at the back corners for the feet (about 74 g), desk weight in the 144 x 37 mm recess under the body, double-sided tape | `steel.dxf` (outline) |
| Bench (before the boards) | local or online | Raspberry Pi Pico or Pico H (RP2040) with headers, not a Pico W (its radio takes GP23, GP24, GP25 and GP29) and not a Pico 2 (RP2350, which needs another CircuitPython build), and a data-capable micro-USB cable, a breadboard and jumper wires, a few push buttons, one cheap EC11-type encoder with push and 30 detents / 15 pulses per turn, like the PEC11D (not one of the three PEC11D; a 20 / 20 part, common among cheap EC11 and KY-040 encoders, needs `divisor=4` in `code.py`, see [Firmware](firmware.md#pico-bench)), a 1N4148 diode for SHIFT from GP6 to GP2 (see [Firmware](firmware.md#pico-bench)) | |

Every part number in the BOM is set. The RP2040, the flash, the crystal and the USB-C socket are extended
parts at JLCPCB (an extended-part fee each, about $3). The 27 R USB series resistors (C25190) are extended
too, but flagged as a preferred extended part on 2026-11-11, which carries no fee in Economic assembly; JLC
moves parts between these classes, so the quote may show a fee for them. They stay 27 R, the value in
Raspberry Pi's design ([Electronics](electronics.md)); 22 R (C23345, basic, already on the board for the
white LED) would save that fee. The column pull-ups (10 k, C25804) are a basic part.

JLCCNC remark: "No threads. 4 x round flat-bottom pockets dia 7.0 +0.1/-0 from the back, 2.0 +0/-0.1 mm deep
(see plate-drawing.pdf). Plate 4.0 ±0.1 before anodising; all pocket depths +0/-0.1: at least 0.65 mm must
stay to the front face. Encoder pockets 15.6 x 20 and RANGE pocket dia 19.6: floor corner (inside radius
between wall and floor) 0.3 mm max. Key holes 10.2 x 7.0 +0.1/-0 after anodising. Light holes dia 1.8 and
1.6 +0.1/-0. Pocket and hole positions ±0.1 mm to each other. Flatness 0.1 mm over the whole plate after bead
blasting and anodising (it is held only at its four corners; the LEDs sit 0.025 mm under its back near the
middle). The pockets may be anodised or bare, but all alike. Key holes: edge break 0.1 to 0.2 mm on their back
edges (a lead-in for the key caps). Front marking per plate.dxf, same origin and orientation as the STEP
(bottom-left corner seen from the front); DXF units: mm; fill closed contours even-odd (the holes in letters
such as A, D and O are separate contours). Layer LASER = laser marking; layer UV_AMBER = UV print in amber:
please match #D9A441 (RGB 217, 164, 65; Pantone 7563 C, roughly RAL 1004) if you can, otherwise use your
standard orange. This remark takes precedence over the UV colour picked in the order form: orange is picked
there only as that fallback. Layer CUT = outline and through holes, for alignment only, not to be marked."

JLCCNC's help centre lists eight UV print colours (black, white, red, orange, yellow, green, cyan, purple)
and says nothing about matching a custom one, so the remark asks for the amber and falls back to their
orange. The SHIFT cap legend and the 3D view follow whatever the plate gets: if JLCCNC's review says it
prints its standard orange, ask for that orange's colour value, set it as `AMBER` in
[mech/stack.py](../mech/stack.py) and run `./build.sh` before ordering the caps (the
[checklist](#checklist) has JLCCNC's review come first).

The solder mask is black, with the white legend JLCPCB prints on it: green showed as a thin line in the
gap round each key cap and through the USB-C opening. Black needs wider mask dams than green (0.13 mm
against 0.10 mm with 1 oz outer copper, JLCPCB's capabilities page), so every opening is its pad plus
0.035 mm per side, not the usual 0.05: the RP2040's pads, the USB-C contacts and C_X2 to R_X are 0.2 mm
apart and keep a 0.13 mm dam between them ([pcb/check.py](../pcb/check.py) measures every dam and checks
that each opening clears its pad by at least 0.025 mm). JLCPCB exposes the mask by LDI, allows openings as
small as the pad (1:1) since June 2025, and a JLCPCB blog gives the alignment on multilayer boards as
±0.02 mm (the capabilities page gives no figure; at that the mask stays off the pads). JLCPCB removes a
dam it cannot hold rather than asking, so the order asks for the production file to be confirmed and the
dams are checked there ([below](#review-watch-items)); the fallback is green, which needs only 0.10 mm.
JLCPCB lists black among its standard colours, at standard pricing and lead time for most orders; its build
time table is quoted for green, so check the price and build time the quote shows for black before paying.

Via covering "Tented" matches the Gerbers: the solder mask covers every via on both sides except two
deliberate openings, which JLCPCB keeps because the mask Gerber decides for a Gerber order (its via
covering guide): the three 1V1 vias under the RP2040 are probe points on the top (open there, tented
underneath), and the four GND vias in the RP2040's exposed pad sit in that pad's mask opening, clear of its
paste windows. Should JLC tent those as well, assembly is unaffected; only the 1V1 probe points are lost.

All four shops share one JLC account but have their own checkout. JLC3DP items can join the JLCPCB
cart and be paid together (JLC3DP waits for JLCCNC's review, so the JLCPCB payment then waits too, see the
[checklist](#checklist)); LCSC can combine its shipment with a JLCPCB order (choose it at the LCSC
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

### Edge rails

The USB-C socket J1 overhangs its long edge (y = 60 mm in the Gerbers, the edge its opening faces) by
0.5 mm by design: JLC's footprint of C165948 runs from -2.26 to +5.09 mm about its origin, and the plug has
to reach it through the case wall. So no rail can go on that edge. Every other bottom-side part keeps at
least 3.7 mm from the edges (pads; the bodies are no larger), past the 2.5 mm JLCPCB's assembly terms ask
for. The board corners are R3 (the body's cavity corners R3.5), and a V-cut only makes straight lines: a
square corner would stand about 0.74 mm into the body, so the corners stay milled.

- Economic variant: no rails. JLCPCB lists edge rails as not necessary for Economic assembly, so choose
  Edge Rails/Fiducials "None". The outline is then milled all round (±0.2 mm) and fits the body as
  delivered: nothing to break off or sand. Remark for their review: "J1 (USB-C) overhangs the board edge at
  the USB opening (y = 60 mm in the Gerbers) by 0.5 mm by design. No edge rails, please." If their engineer
  insists on rails anyway, accept the proposal as long as it keeps the J1 edge (y = 60) free; the rails
  then come off on arrival as in [Mechanics](mechanics.md#on-arrival): one on the long edge y = 0 as in
  the full-variant step (break it off, sand the edge flush, 60.4 mm wide or less), ones on the short
  edges as in the fallback there (160.2 mm long or less).
- Full variant: Standard assembly needs a board of at least 70 x 70 mm, and this one is 60 mm wide. Choose
  "Added by JLCPCB" and ask for one rail of at least 10 mm on the long edge away from J1 (y = 0), none on
  the other edges. Remark for their review: "J1 (USB-C) overhangs the board edge at the USB opening (y = 60
  mm in the Gerbers) by 0.5 mm by design, so no rail there. Edge rail: one rail of at least 10 mm on the
  long edge y = 0 only (Standard assembly needs 70 mm), none on the other three edges. Keep the R3 corners
  (milled); V-cut only on the straight part of the y = 0 edge, or tabs." The board arrives with that rail
  on: break it off and sand the edge flush before anything else ([Mechanics](mechanics.md#on-arrival)).
  The V-cut edge is held to ±0.4 mm, which the cavity still takes (`check_fit.py` has the row). JLCPCB can
  also remove the rail for a fee; ask in the order remark if you prefer, and still check the edge.

## Before paying

- Upload the current files to the four quotes (JLCPCB, JLC3DP, JLCCNC, LCSC; see the
  [checklist](#checklist)). The quotes below are older than most of the files.
- JLCCNC reviews the plate before payment. The plate has no threads now (four glued standoffs in 2 mm
  flat-bottom pockets); the JLCCNC remark above also carries the laser marking and the amber UV print. Watch
  for a flag on the 0.85 mm webs between the light holes (+0.1/-0) and the SHIFT and UNIT key holes
  (+0.1/-0 after anodising; 0.75 mm with both at +0.1, JLCCNC recommends 0.8 and allows 0.5); if they flag
  those, shrink `LIGHT_HOLES` in [mech/stack.py](../mech/stack.py) to 1.6 mm (SHIFT) and 1.4 mm (UNIT) and run
  `./build.sh`: the pipes follow, 0.3 mm under their holes (Ø1.3 and Ø1.1 mm), and so do their snap-off necks
  (1.0 mm, the resin minimum). The fibre fallback then takes Ø1.25 mm for SHIFT and Ø1.0 mm for UNIT. JLCCNC
  publishes no flatness capability, so the remark's flatness 0.1 mm after bead blasting and anodising may come
  back as a review question or a surcharge.
- Submit JLCCNC first and pay JLC3DP only after its review: a change to the light holes changes the light
  pipes, and its answer on the amber decides the colour of the SHIFT cap legend (above). Pipes already
  printed for the old holes would have to be sanded down or replaced by the fibre fallback.
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

Full variant, top side as well (the top silkscreen marks only the LED cathodes with a "K"; otherwise go by
the pads and holes):

- LED_SHIFT and LED_UNIT: the cathode pin of JLC's footprint (away from its "+" mark) on our square pad.
- ENC_ALTHDG, ENC_FREQ, ENC_FMS: JLC's footprint on all eight pin holes and the two lug slots, with its
  two-pin row (the push switch) on the side of the three-pin row towards the J1 edge.
- RANGE: all ten pin holes and JLC's unplated hole on our locating hole; the pattern fits one way only.
- K00 to K06, K10 to K16, K20 to K26 and K30 to K36: each footprint on the four holes of its key (either
  way round is the same switch).

### Review watch items

Items below or at JLC's published minimums, where the design leaves no room; expect a question in their
review:

- JLCPCB black solder mask: 64 dams on the bottom (between the RP2040's pads, the USB-C contacts and C_X2
  to R_X) are exactly 0.13 mm, JLCPCB's minimum for black. JLCPCB removes a dam under its minimum without
  asking (the pads then share one opening), and its CAM may resize openings. So order with Confirm
  Production File: yes and add to the order remark: "Solder mask: please keep the 0.13 mm dams between
  the pads of U1, J1 and C_X2/R_X; if black cannot hold them, please ask before removing any." When the
  processed files come back, check the bottom mask still has a dam between every pair of U1's and J1's
  pads and between C_X2 and R_X. If any is gone, ask JLCPCB to change the order to green (the file is
  confirmed after payment, so this means their change or a cancelled and new order, and a new file to
  check): the same Gerbers then leave 0.03 mm over its 0.10 mm minimum.
- JLCCNC UV print colour: the remark asks for amber #D9A441 with their standard orange as the fallback
  (above); go by their answer for the caps.
- JLCCNC text size: their UV design guide asks for text of at least 6 pt (2.117 mm font size) and lines of
  at least 0.176 mm. The shift legends under the keys are a 6.7 pt font (1.7 mm in `make_plate_art.py`),
  the knob legends 6.1 pt (1.55 mm) and the titles 6.9 pt; the frame lines are 0.3 mm. Strokes in the
  letters are mostly 0.2 mm or wider. Everything is at 6 pt or more; the legends sit between the keys and
  round the knobs, with little room to grow, so a flag here means asking for a sample or accepting a little
  blur.
- JLCCNC plate thickness: the drawing and the remark ask for 4.0 ±0.1 before anodising, and the stack has no
  room past that either way. On a 4.1 mm plate the outer knobs keep only 0.02 mm over the face at worst
  (encoder tolerances, anodised pocket floors, the plate bowed away from the board near the knobs); on a
  4.15 mm plate they would rub on it. On a 3.9 mm plate 0.65 mm of metal stays over the RANGE pocket
  (JLCCNC's minimum is 0.5 mm), and the cap socket ceilings stay 0.01 mm under the face where the plate bows
  towards the board (cosmetic: the socket stays inside the cap). A plate cut from sheet at ±0.15 to 0.2 has
  no room for that. If their review offers only sheet tolerance, ask for a plate between 3.9 and 4.1 mm
  thick before anodising.
- JLCCNC RANGE pocket: it is 3.25 mm deep in the 4 mm plate, so 0.65 mm of metal stays over it, above
  JLCCNC's 0.5 mm minimum but under the 0.8 mm it recommends; the RKJXT needs that depth. If they flag it,
  ask them to hold the depth +0/-0.1 rather than make the floor thicker.
- SLA light pipes: the Ø1.5 and Ø1.3 mm rods, 3.6 mm long, exceed the resin pillar guideline (Ø1.0 up to
  1 mm, Ø2.0 up to 4 mm). If flagged or broken, use the PMMA fibre fallback in the table above.
- SLA outer knob key: 1.4 mm wide, under the 1.5 mm asked for positioning features; at 1.5 a key printed
  0.2 mm wide would no longer clear the narrowest shaft slot (1.7 mm).
- WJP caps: the set dimples leave 1.11 mm to the socket and the outline, 0.86 mm on a print with the
  outline 0.2 mm small and both holes 0.3 mm large (no spot between the 3.8 mm socket and a 6.4 mm wide
  cap keeps 1.0 there); the socket wall is 1.05 mm on such a print. The tactile bars are 1.0 mm wide but
  only 0.5 mm proud (embossed detail 0.8 mm), so the front bars don't hide the SHIFT and DN legends.
- MJF body: the screw bosses are fastener features at 1.6 mm (the seat under the PCB, 1.9 mm round the
  counterbore; over JLC3DP's 1.5 mm for fasteners, under the 2.0 mm general wall for parts over 100 mm).
  Every other wall, rib and the floor is 2.0 mm or more, bar the front edge of the floor: the 6° bottom
  plane leaves 1.6 mm there, about 1.8 mm just inside the front wall and 2.0 mm from about 3.8 mm in.
- JLCPCB: the paste layer has openings on the four J1 shell pads (pin-in-paste). If their engineer drops
  them from the stencil, nothing changes: the tabs are soldered from the top anyway, by hand in the
  economic variant (bring-up step 1, [Mechanics](mechanics.md#hand-soldering)), by JLCPCB in the full one.
- JLCPCB, full variant: the through-hole remark above. If their engineer says a part cannot be seated as
  asked (the LEDs flush, the encoders and the RANGE control flat), leave that part out of the assembly
  and solder it by hand ([Mechanics](mechanics.md#hand-soldering)) rather than accept it standing proud.
  If they won't trim the leads to 2 mm, accept it and cut them on arrival
  ([Mechanics](mechanics.md#on-arrival)).
- JLCPCB, full variant: the single rail on the long edge away from J1 ([edge rails](#edge-rails)). Accept
  their engineer's proposal if it keeps the J1 edge free.
- JLC3DP light pipes: no post-processing (the table above), so the thin rods aren't sanded off.
- MJF USB-C filler: a small part at the limit, not under it (19.7 x 2.0 x 3.85 mm, 0.15 cm³): its 2.0 mm
  thickness is exactly the 2 mm of JLC3DP's 10 x 2 x 2 mm minimum. If JLC3DP flags it anyway, point them
  at that minimum in their design guideline and ask them to print it as it is (SLA is no way out: the
  guideline gives the same minimum for SLA and MJF). Without it the panel works as before, only with the
  notch above the plug open.

## Parts and quotes

UV print on JLCCNC parts may blur slightly at the edges, and the legends are close to the 6 pt JLCCNC
asks for (review watch items), so ask for a sample or accept the risk. Laser marking alone would make every
legend grey.

Key caps, one file per set: JLC3DP's guidelines ask for one part per file (up to 10 files per quote), and
their connected-parts option (small parts joined in one file) is not offered for WJP full colour. Upload
`caps-A.zip` to `caps-D.zip` and see whether the quote or the review accepts 28 separate caps per file. If
they ask for single parts, ask their support first: 112 single caps at JLC3DP's full-colour minimum (from
about $5 a part) come to about $450 to 500, against one part per set now. If single parts it must be, the
cheaper way is two rounds: one test cap of each set from `caps-single-A.zip` to `-D` (one zip per cap, each
with its own texture tile, the set letter in its name; take the same key from each), then the 28 of the set
that fits, in batches of 10. All four sets are needed: only one of them will fit, and which one depends on
the print. The light pipes are one part on their bar, the knobs one part each.

The JLC3DP order has 19 files (the body, the USB-C filler, the four cap zips, 12 knob files and the light
pipes), and its quote page takes 10 per upload: upload them in two batches into the same cart.

The dual encoders are Bourns PEC11D-4120F-S0015 (C19270361, $8.26 at LCSC, 68 in stock on 2026-11-09 and
2026-11-11): in production, 30 detents / 15 pulses with push like the Alps EC11EBB24C03 drawn first (not
recommended for new designs), with 5 mm shorter shafts. Same footprint apart from the pin holes (1.2 mm),
so the board kept its routing. Order the encoders early; stock is small (three for the economic variant
at LCSC; six for the full one, bought into the JLCPCB parts library, see
[above](#full-variant-through-hole-parts-at-jlcpcb)).

Quotes on 2026-11-09 (Germany; JLCCNC in USD and subject to their review). They predate the switch to
Bourns encoders (new holes), the bottom-only BOM, the thicker body bosses, the knob fit variants, the
knob files (`knob-outer-22` and `knob-outer-24` are gone: now `knob-outer` x2, `knob-outer-fms` x1 and
the variants, all Ø17) and the mechanical rework (glued standoffs instead of threads, deeper pockets,
hollow body, four cap sets with rigid ribs, light pipes, the FMS ring and its fit variants, the USB-C
filler), so re-upload the board, plate and all JLC3DP files before paying. The JLC3DP price below is too
low: it covers one set of caps (the order now has four) and no USB-C filler:

| Order | Price | Shipping |
| --- | --- | --- |
| JLCPCB, economic variant: 5 boards, 2 assembled (Economic, SMD side) | €71.95 | about €21 (DHL) |
| JLCPCB, full variant: 5 boards, 2 assembled (Standard, both sides incl. through-hole) | €227.43 | not quoted (the parcel is over €150: import VAT and the carrier's fee come on delivery) |
| JLCCNC: front plate | $30.09 | $26.60 (UPS) |
| JLC3DP: body, knobs, caps, light pipes (quoted with four printed spacers, now dropped, and without the USB-C filler) | €42.10 | €7.13 |
| LCSC (economic variant only): through-hole parts for one panel | about €37 (three dual encoders about €22) | separate |

Hand-soldering the through-hole parts saves about €118 over Standard assembly (€155 less the about €37 of
LCSC parts for one board). Rough total for the first panel with the spare board: about €250 to 300
including shipping in the economic variant, about €370 to 420 in the full one, plus the standoffs, screws
and consumables.

## Checklist

1. Run `./build.sh`; it must finish with every check passing.
2. Pick the [assembly variant](#assembly-variants). Full variant: buy the six encoders into the JLCPCB
   parts library now ([above](#full-variant-through-hole-parts-at-jlcpcb)).
3. JLCCNC first: `plate.step`, `plate-drawing.pdf` and `plate.dxf`; finishes as in the table (orange if the
   form asks for a UV colour, only as the fallback: the remark takes precedence), and the remark above for the
   pockets, the laser marking and the amber UV print. Wait for their review before paying JLC3DP: it can
   change the light holes (and so the pipes) and the amber ([before paying](#before-paying)); if it does,
   change `stack.py`, run `./build.sh` again and upload the new files. Pay JLCCNC after their review.
4. JLCPCB: upload `gerbers.zip`; board options as in the table (4 layers, 1.6 mm, ENIG, black solder
   mask, white silkscreen, tented, 0.3 mm via, PCB quantity 5, assembly quantity 2). Confirm Parts
   Placement: yes, Confirm Production File: yes with the solder mask remark ([review watch
   items](#review-watch-items)), and Review Before Payment if offered.
   - Economic: Economic assembly, bottom side; upload `BOM.csv` and `CPL.csv`; Edge Rails/Fiducials: none,
     with the J1 remark ([edge rails](#edge-rails)).
   - Full: Standard assembly, both sides; upload `BOM-full.csv` and `CPL-full.csv`, check that the BOM step
     finds all 23 lines with stock for 2 boards (six encoders; if not, see
     [above](#full-variant-through-hole-parts-at-jlcpcb)); Edge Rails/Fiducials: Added by JLCPCB, one rail
     of at least 10 mm on the long edge away from J1, with the edge-rail remark and the through-hole remark
     after it.

   Go through the [placement preview](#placement-preview), top side too in the full variant. If JLC3DP is
   to join this cart (step 5), hold the JLCPCB payment until JLCCNC's review is back, since JLC3DP waits for
   it; otherwise pay JLCPCB now.
5. JLC3DP, after JLCCNC's review: body and USB-C filler (MJF, both dyed black, the filler quantity 2),
   `caps-A.zip` to `caps-D.zip` (full colour, all four sets), knobs with the counts in the table, including
   the eight fit variants, light pipes (8001, quantity 2, no post-processing); 19 files, so two uploads.
   Economic variant: add them to the JLCPCB cart only if JLCPCB and JLC3DP together stay under €150 of
   goods, and then pay both together (the JLCPCB payment held since step 4); otherwise, and always in the
   full variant, pay and ship JLC3DP as its own order (the €150 note above).
6. LCSC: economic variant, upload `THT-LCSC.csv` to the BOM tool and order the encoders early (small
   stock); optionally add the second through-hole set for the spare board (see the table). Full variant:
   two spare keys (C589907) to try the cap sets on and one RKJXT1F42001 (C160841) as the reference for the
   RANGE control's seating check. Either variant: add the standoffs, screws, washers and feet from the
   table if you have none. Ship it on its own (see the €150 note above).
7. Locally: the consumables and tools from the table and, if wanted, the notched 2 mm steel plate
   (`steel.dxf`).
8. Bench: the Pico, buttons, encoder and diode from the table, to run the firmware before the boards
   arrive ([Firmware](firmware.md#pico-bench)).
9. [Before paying](#before-paying) each order: the review watch items, and the tax lines of every order.
