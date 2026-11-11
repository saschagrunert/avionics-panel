# Ordering

The board, the plate and the printed parts come from the JLC group (JLCPCB, JLCCNC, JLC3DP), the screws from
JLCMC; only the feet, a few consumables and tools and the optional steel plate come from a local shop. By
default JLCPCB fits and solders both sides of the board, so nothing needs soldering at home; hand-soldering the
through-hole parts is an option ([assembly variants](#assembly-variants)). The files are in
[production/](../production/); every file name there starts with `avionics-panel-rev1-`, which the tables
below leave out (`body.step` is `avionics-panel-rev1-body.step`).

## Assembly variants

Full assembly is the default: JLCPCB fits the SMD bottom side and the through-hole parts on the top, and the
boards arrive soldered. The economic variant is an option for those who like to solder: JLCPCB fits only the
bottom side, and the keys, encoders and RANGE control come from LCSC and are soldered by hand.

| | Full (default) | Economic (option) |
| --- | --- | --- |
| JLCPCB assembly | Standard, both sides | Economic, bottom side only (all SMD) |
| Files for JLCPCB | `gerbers.zip`, `BOM-full.csv`, `CPL-full.csv`: one BOM and one CPL for both sides (the CPL's Layer column gives the side), uploaded as the only ones | `gerbers.zip`, `BOM.csv`, `CPL.csv` |
| Through-hole parts | from JLCPCB's parts library, on both boards ([below](#full-variant-through-hole-parts-at-jlcpcb)) | from LCSC (`THT-LCSC.csv`), one board's set plus spares, soldered by hand with the J1 shell tabs ([Mechanics](mechanics.md#hand-soldering)) |
| Edge rails | one of at least 10 mm on the long edge away from J1, broken off on arrival ([edge rails](#edge-rails)) | none |
| Order remark | [below](#full-variant-through-hole-parts-at-jlcpcb) | [edge rails](#edge-rails) |
| Extended parts (2026-11-11) | RP2040, flash, crystal, J1, F1, the two LEDs, the 27 R, U4 and the three through-hole parts (a fee each) | the same bar the through-hole parts; the 27 R and U4 are preferred extended parts, no fee here |
| Quote 2026-11-09 (older than the files: re-quote) | €227.43 for 2 fully populated boards ([quotes](#parts-and-quotes)) | about €72 for 2 boards, plus about €37 at LCSC for one through-hole set |
| Bring-up | every part is on from the start: a board that turns out dead takes its encoders and RANGE control with it, and the second board is the spare | the encoders and the RANGE control go on last, after the board has been tested |

Both variants use the same Gerbers and bottom side. The full one costs about €118 more than the economic one
with one LCSC set (about €81 against two) and saves soldering 28 keys, three encoders and the RANGE control per
board.

### Full variant: through-hole parts at JLCPCB

`BOM-full.csv` lists the through-hole parts by their JLC part numbers for one board; JLCPCB multiplies by the
2 assembled boards. All three are extended parts in JLCPCB's library, whose stock is its own (check it, not
LCSC's). JLCPCB stock on 2026-11-11:

| Part | JLC part | Library | JLC stock | Per board | For 2 boards |
| --- | --- | --- | --- | --- | --- |
| TE 1-1825910-4 key switch | C589907 | extended | 30920 | 28 | 56 |
| Bourns PEC11D-4120F-S0015 dual encoder | C19270361 | extended | 68 | 3 | 6 |
| Alps RKJXT1F42001 RANGE control | C160841 | extended | 6859 | 1 | 2 |

The encoders are the tight part: 6 of 68. Buy the six into your JLCPCB parts library (Parts Manager) as soon as
you order: the assembly takes them from there, so no other order can take them first. If the stock is short,
buy them in through Global Sourcing (a fee and days to weeks), send six as consigned parts, or unselect the
three encoder lines in the BOM step and solder the encoders by hand as in the economic variant (buy them at
LCSC or a Bourns distributor; [Mechanics](mechanics.md#hand-soldering)).

The CPL places every through-hole part by JLC's footprint at rotation 0 (the encoders' position is 1 mm
towards the J1 edge from the shaft, where JLC's footprint has its origin); [pcb/check.py](../pcb/check.py)
fits each JLC footprint onto our holes pin by pin, so a wrong rotation or position fails the build.

Order remark (the only one for JLCPCB): "J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design: no rail
there. One edge rail of at least 10 mm on the y = 0 edge only; keep the R3 corners milled. Through-hole parts:
seat each one fully down and flat before soldering; ENC_ALTHDG, ENC_FREQ, ENC_FMS and RANGE at most 0.05 mm
proud (hold RANGE pressed down while soldering), and solder the encoder lugs. Solder the four J1 shell tabs
from the top, filling the slots. Solder mask: keep the 0.13 mm dams between the pads of U1, J1 and C_X2/R_X;
please ask before removing any. The two 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount
LEDs: please mill them with R0.5 inside corners (1.0 mm router)." Why: Standard assembly needs a board of 70
mm and up; the plate pockets leave the encoders and the RKJXT about 0.1 mm
([Mechanics](mechanics.md#on-arrival)); the pin-in-paste openings leave only a fillet under the J1 tabs, which
carry the plug; black mask needs 0.13 mm dams ([review watch items](#review-watch-items)). The leads stay as
they are: untrimmed they stand at most 2.7 mm under the board, 1.0 mm clear of the body floor
(`check_fit.py`).

## Suppliers

| Part | Service | Process | Files in `production/` |
| --- | --- | --- | --- |
| Board, assembled | JLCPCB | 4 layers, 1.6 mm, ENIG, black solder mask with white silkscreen ([below](#review-watch-items)), via covering Tented (below; the form defaults a 4-layer board to Plugged), everything else at JLCPCB's defaults (0.3 mm via, 1 oz outer copper, stackup, PCB quantity 5); assembly quantity 2. Full (default): Standard assembly, both sides, Edge Rails/Fiducials: Added by JLCPCB, with the remark [above](#full-variant-through-hole-parts-at-jlcpcb). Economic: Economic assembly, bottom side, Edge Rails/Fiducials: None, with the remark under [edge rails](#edge-rails). Confirm Parts Placement and Confirm Production File: yes | full: `gerbers.zip`, `BOM-full.csv`, `CPL-full.csv`; economic: `gerbers.zip`, `BOM.csv`, `CPL.csv` |
| Spare keys and RANGE control | LCSC | full variant: 2 x TE 1-1825910-4 (C589907) to try the cap sets on without pulling at a soldered switch, 1 x Alps RKJXT1F42001 (C160841) as the reference for the RANGE control's seating check ([Mechanics](mechanics.md#on-arrival)) | |
| Through-hole parts (economic option) | LCSC, hand-soldered | keys, encoders, RANGE control for one board plus spares (30 keys, the two spares for the cap sets; the `Needed` column gives the count per board); a second set for the spare board if wanted | `THT-LCSC.csv` (LCSC BOM tool) |
| Front plate | JLCCNC | aluminium 6061 from 12 mm stock, CNC, bead blasting + black anodising (matte), laser marking; the amber UV print goes into the remark (below). If the form has a UV colour field, pick orange there, the remark's fallback | `plate.step`, `plate-drawing.pdf` (tolerances, threads, finish), `plate.dxf` (marking) |
| Body and USB-C filler | JLC3DP | MJF PA12-HP, dyed black, both parts: the body quantity 1, the filler quantity 2 (one spare; it closes the USB-C notch from the back, [Mechanics](mechanics.md#fastening)) | `body.step`, `usb-filler.step` (`body.stl`, `usb-filler.stl` if a STEP is refused) |
| Key caps | JLC3DP | WJP Full Color Resin, four full sets of 28 caps (A, B, C, D: rib circles 3.15, 3.25, 3.35, 3.05 mm, marked with 1, 2, 3, 4 dimples on the underside), quantity 1 each; upload the zips, they carry the texture (the OBJ alone prints without legends). One set fits, see [Mechanics](mechanics.md#caps-light-pipes-knobs). If JLC3DP wants one part per file, see below | `caps-A.zip` to `caps-D.zip` (`caps-single-A.zip` etc.: one zip per cap) |
| Knobs | JLC3DP | SLA Black Resin: `knob-outer` x2 (ALT/HDG, FREQ), `knob-outer-fms` x1 (same fits, coarser grip), `knob-inner` x3, `knob-range` x1, plus one each of `knob-outer-tight`, `-loose`, `knob-outer-fms-tight`, `-loose`, `knob-inner-tight`, `-loose`, `knob-range-tight`, `-loose` (bore 0.2 mm under / over nominal; the knobs are held by friction, keep whichever grips) | `knob-*.step` |
| Light pipes | JLC3DP | SLA 8001 Resin, transparent, quantity 2 (one spare), no post-processing (JLC3DP sands and oil-sprays 8001 by default, which can break the thin rods: pick none, or ask in the remark: "Light pipes: no sanding and no oil spray, please"); both stepped pipes on one snap-off bar under their bases (JLC3DP prints resin from 10 x 2 x 2 mm only); break off and sand the stubs flush, no further. The rods (Ø2.0, 3.65 mm long) meet JLC3DP's resin pillar guideline (Ø2.0 up to 4 mm); the base (Ø2.8, 5.35 mm long) is under its next entry (Ø3.0 up to 6 mm) and each 9 mm part stands on Ø1.0 necks, so the review may flag them: then ask them to print as is (the order has a spare pair) | `lightpipes.step` |
| Screws | JLCMC | 6 (or JLCMC's pack minimum) x M3 x 8 flanged button head, hex socket (ISO 7380-2; series EDDH: EDDH-C16E1-M3-L8, 10B21 blackened, 8.8, or EDDH-S1W-M3-L8, A2-70 stainless; 2 spare; both "ships within 1 day" on 2026-11-11, from $0.0073 each). No washers. JLCMC is a separate order and parcel: since 2026-11-02 it no longer ships with JLCPCB, JLC3DP or JLCCNC | |
| Feet | local | 4 self-adhesive feet up to 10 mm across (none in stock at LCSC or JLCMC) | |
| Consumables | local | removable adhesive putty (Blu Tack) for the USB-C filler, fine sandpaper (about 400 to 1000 grit) for the light-pipe stubs, double-sided tape for the steel plate, a data-capable USB-C cable (a charge-only cable shows no RPI-RP2 drive). Only the cable is stocked at LCSC | |
| Tools | local | a 2 mm hex key for the M3 flanged heads (not at LCSC or JLCMC), two blocks at least 25 mm high (books, wood) and a cloth for face-down assembly, a feeler gauge set from 0.03 to 1.0 mm whose blades stack (the encoder and RKJXT seating, the USB-C filler), a steel rule (squaring the caps), pliers and a flat file or 240 grit sandpaper on a block (the rail), a multimeter with a continuity beeper (bring-up steps 1 and 2), a magnifier or loupe (troubleshooting). Economic option, or rework: a soldering iron, solder, flux and solder wick. Only if a knob bore is tight or loose: 6.0, 3.5 and 2.5 mm drills, a needle file and adhesive tape | |
| Steel plate (optional) | local or laser cut | 2 mm steel, 143 x 36 mm (±0.1) with two 15 x 15 mm notches at the back corners for the feet (about 74 g), desk weight in the 144 x 37 mm recess under the body, double-sided tape | `steel.dxf` (outline) |
| Bench (before the boards) | local or online | Raspberry Pi Pico or Pico H (RP2040) with headers, not a Pico W (its radio takes GP23, GP24, GP25 and GP29) and not a Pico 2 (RP2350, which needs another CircuitPython build), and a data-capable micro-USB cable, a breadboard and jumper wires, a few push buttons, one cheap EC11-type encoder with push and 30 detents / 15 pulses per turn, like the PEC11D (not one of the three PEC11D; a 20 / 20 part, common among cheap EC11 and KY-040 encoders, needs `divisor=4` in `code.py`, see [Firmware](firmware.md#pico-bench)), a 1N4148 diode for SHIFT from GP6 to GP2 (see [Firmware](firmware.md#pico-bench)) | |

Every part number in the BOM is set. The RP2040, the flash, the crystal, the USB-C socket and the two LEDs
(LTST-C230KSKT C125108 and LTW-C230DS C575513) are extended parts at JLCPCB (an extended-part fee each, about
$3); JLCPCB had 8700 and 56682 of the LEDs in stock on 2026-11-11. The 27 R USB series resistors (C25190) are
extended too, but flagged as a preferred extended part on 2026-11-11, which carries no fee in Economic
assembly; JLC moves parts between these classes, so the quote may show a fee for them. They stay 27 R, the
value in Raspberry Pi's design ([Electronics](electronics.md)); 22 R (C23345, basic, already on the board for
the white LED) would save that fee. The column pull-ups (10 k, C25804) and the amber LED's 75 R (C4275) are
basic parts.

The USB protection adds two parts ([Electronics](electronics.md#usb-protection)), both in JLCPCB's library
(stock on 2026-11-11):

| Part | JLC part | Library | JLC stock | Fee, economic | Fee, full |
| --- | --- | --- | --- | --- | --- |
| U4: hongjiacheng SRV05-4 ESD array, SOT-23-6 | C7420376 | preferred extended | 308828 | none | about $3 |
| F1: Bourns MF-NSMF050-2 PTC fuse, 0.5 A hold, 13.2 V, 1206 | C75464 | extended | 65039 | about $3 | about $3 |

No ESD array for USB is a basic part (the basic TVS diodes are for 12 V and up or SMB-sized), and no
resettable fuse at all is basic or preferred extended, so F1 carries the fee in both variants and U4 only in
the full one: about $3 more in the economic variant, about $6 in the full one. The IOVDD capacitors (C_IO1,
C_IO10, C_IO22, C_IO49) and C_1V1 are the 0402 100 nF C1525, a basic part already on the board (Economic
assembly places 0402), and C_IN is now the 10 uF C19702 of C_OUT0, also basic; C_D0 is gone. R_IN, the 1 ohm
that damps the hot-plug ringing (C22936, 0603), and R_CC2, now an 0402 5.1k (C25905), are basic parts too.

JLCCNC remark: "6061 from 12 mm plate, machined to plate-drawing.pdf; all its notes apply. Boss height 6.05
±0.05 mm, not the general tolerance. The M3-6H threads must take a screw after anodising: mask them or cut
them again afterwards. Flatness 0.1 mm after anodising. Marking per plate.dxf as the drawing says; layer
UV_AMBER: please match #D9A441 (RGB 217, 164, 65; Pantone 7563 C) if you can, otherwise use your standard
orange. This remark takes precedence over the UV colour picked in the form." The drawing carries every size,
tolerance and edge break; the remark repeats only the three items their review is most likely to question, and
the colour, which the form cannot take.

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

The JLC shops share one JLC account but have their own checkout; JLCMC is a separate order with its own parcel
and shipping. JLC3DP items can join the JLCPCB cart and be paid together (JLC3DP waits for JLCCNC's review, so
the JLCPCB payment then waits too, see the [checklist](#checklist)); LCSC can combine its shipment with a
JLCPCB order (choose it at the LCSC checkout); JLCCNC is paid separately after its review. Payment by PayPal,
card or Google Pay. Under €150 of goods per shipment JLC collects German VAT at checkout (IOSS); since July
2026 a customs duty and a disbursement fee can come on top, so check the tax lines before paying. A shipment
over €150 is cleared on delivery instead, with the carrier's fee. The quotes below are too old to tell which
side of the line the order falls on (they cover one cap set, no knob variants and no FMS ring), so re-quote
and read the JLC cart total of goods: if JLCPCB and JLC3DP together come to more than €150, pay and ship the
JLC3DP order on its own (or expect the customs fee on delivery). The full variant's JLCPCB order alone is over
€150, so it is cleared on delivery either way; ship JLC3DP on its own then too. Ship the LCSC order on its own
as well: added to a JLC parcel it takes that over the line. The JLCMC order (the screws from the table) is
small and ships on its own anyway. JLCPCB assembles at least 2 boards (bare boards come in 5). Order 2
assembled boards but only one set of plate, body, caps and knobs; the second board is the spare for the first,
untested chip-down design. In the full variant both boards come fully populated, with two sets of through-hole
parts.

### Edge rails

J1 overhangs its long edge (y = 60 mm in the Gerbers) by 0.5 mm, so the plug reaches it through the case wall:
no rail can go there. Every other bottom-side part keeps 3.7 mm from the edges. The R3 corners stay milled (a
V-cut square corner would stand 0.74 mm into the body).

- Full (default): Standard assembly needs 70 x 70 mm and the board is 60 mm wide, so Edge Rails/Fiducials:
  Added by JLCPCB, one rail on y = 0 (the remark [above](#full-variant-through-hole-parts-at-jlcpcb)). It is
  broken off on arrival; the V-cut edge (±0.4 mm) still fits the cavity (`check_fit.py`), so nothing needs
  measuring. JLCPCB can also remove it for a fee.
- Economic: Edge Rails/Fiducials "None" (JLCPCB lists them as not needed for Economic assembly); the milled
  outline fits the body as delivered. Remark: "J1 (USB-C) overhangs the y = 60 mm edge by 0.5 mm by design. No
  edge rails, please. Solder mask: keep the 0.13 mm dams between the pads of U1, J1 and C_X2/R_X; please ask
  before removing any. The two 2.2 x 2.4 mm internal cutouts in the outline are for reverse-mount LEDs: please
  mill them with R0.5 inside corners (1.0 mm router)." Should their engineer add rails anyway, accept if the
  J1 edge stays free and break them off on arrival ([Mechanics](mechanics.md#on-arrival)).

## Before paying

- Upload the current files to the four quotes (JLCPCB, JLC3DP, JLCCNC, LCSC; see the
  [checklist](#checklist)). The quotes below are older than most of the files.
- JLCCNC reviews the plate before payment. The plate is now milled from 12 mm stock (about 97 cm³ come off,
  most of it from the back round the four bosses; the part is 10.05 mm high, up to 10.2), so expect a higher
  price than the $30.09 quoted for the 4 mm plate; the remark above also carries the threads, the laser
  marking and the amber UV print. JLCCNC publishes no flatness capability, and milling most of a 12 mm plate
  off one side can leave it bowed, so the remark's flatness 0.1 mm after bead blasting and anodising may come
  back as a review question or a surcharge; stress-relieved plate (T651) helps, if they offer it. If they ask,
  up to 0.17 mm is acceptable: every row in `check_fit.py` still passes there (the light pipes' room over
  their bases goes first, then the body walls at 0.19), bar the cosmetic cap socket ceiling, which may then
  stand up to 0.05 mm above the face. Ask for the boss height ±0.05, but if they can only hold ±0.1, accept
  (cosmetic only): at their default ±0.1 every row still passes bar that same row (up to 0.04 mm above the
  face on a plunger 0.3 mm high, TE's tolerance). Not both at once: with the bosses at ±0.1, flatness up to
  about 0.12 mm (with the same exception).
- Submit JLCCNC first and pay JLC3DP only after its review: a change to the light holes changes the light
  pipes, and its answer on the amber decides the colour of the SHIFT cap legend (above). Pipes already
  printed for the old holes would have to be printed again.
- JLC3DP: check that the four cap files with 28 separate caps each are accepted (see
  [key caps](#parts-and-quotes) below).
- Go through the placement preview (below) and the review watch items.

### Placement preview

Check every assembled part in the JLCPCB placement preview of the bottom side. The preview draws JLC's
own footprint over our pads; the marks below are on our bottom silkscreen, so they hold whichever way
round the preview shows the board:

- LED_SHIFT and LED_UNIT (reverse-mount 1206 LEDs over the two cutouts in the board): JLC's cathode, pin 1, at
  our cathode bar (west), the part centred over its cutout. JLC lists reverse-mount LEDs as placed at the
  customer's risk should the cutout be wrong; the cutouts are in the outline Gerber, 2.2 x 2.4 mm with R0.5
  corners round LiteOn's 1.5 x 1.6 mm lens (LiteOn's land pattern: 2.1 x 2.3 mm, sharp corners). JLC's
  footprint of the white LTW-C230DS draws a round 2.3 mm hole with its pads reaching into it, and the amber
  one's a 1.9 mm square: both differ from ours, which follows LiteOn's land pattern with the pads 0.2 mm off
  the cutout; go by the pads and the cutout.
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
- U4 (ESD array, the SOT-23-6 below J1): JLC's pin 1 mark at our pin 1 dot, just beyond the corner pin
  that is away from J1 on the fuse's side. Turned by 180 degrees its VCC pin would sit on GND and its clamp
  diode forward across the fused VBUS: plugged in, that burns the 1 ohm R_IN open (it gives way long before
  the fuse trips, [Electronics](electronics.md#usb-protection)) and the board stays dead until U4 and R_IN
  are replaced (a U4 that carried the fault current is likely damaged). Check it; bring-up step 1 also
  tests for it with the multimeter's diode mode.
- F1 (fuse, the 1206 between U4 and the regulator) and the resistors and capacitors have no polarity: only
  check they sit on their pads.

The CPL gives every bottom rotation in JLCPCB's convention for the bottom side (seen from the bottom, the
part is JLC's library footprint turned counter-clockwise by the rotation, as KiBot's JLCPCB filter and the
kicad-jlcpcb-tools plugin write it), and [pcb/check.py](../pcb/check.py) fits each of JLC's footprints onto
our pads with that convention. JLC has changed how it reads bottom rotations before, so if the preview shows
a part turned, correct its rotation there in the preview (or ask JLC's engineer in the review) rather than
ordering as is. A footprint that is not mirrored cannot be fixed by a rotation; check.py asserts the pin
order of every bottom-side part.

Full variant, top side as well (the top silkscreen has no polarity marks; go by the pads and holes):

- ENC_ALTHDG, ENC_FREQ, ENC_FMS: JLC's footprint on all eight pin holes and the two lug slots, with its
  two-pin row (the push switch) on the side of the three-pin row towards the J1 edge.
- RANGE: all ten pin holes and JLC's unplated hole on our locating hole; the pattern fits one way only.
- K00 to K06, K10 to K16, K20 to K26 and K30 to K36: each footprint on the four holes of its key (either
  way round is the same switch).

### Review watch items

Items at or under JLC's published minimums; expect a question in their review, and the answer:

- JLCPCB black solder mask: 64 dams on the bottom (U1's pads, J1's contacts, C_X2 to R_X) are exactly
  0.13 mm, JLCPCB's minimum for black, and JLCPCB removes a dam under its minimum without asking. The remark
  asks them to keep the dams; check the confirmed production file still has a dam between every pair of those
  pads. If any is gone, change the order to green (0.10 mm minimum): the same Gerbers then keep 0.03 mm to
  spare.
- JLCPCB reverse-mount LEDs: placed at the customer's risk should the cutout be wrong. The two 2.2 x 2.4 mm
  cutouts in the outline Gerber are internal cutouts to be milled with R0.5 corners (a 1.0 mm router; the
  remark asks for them, and the lens clears them by 0.01 mm at R0.5), not slots.
- JLCPCB, full variant: should a part not be seatable flat as asked, leave it out of the assembly and solder it
  by hand ([Mechanics](mechanics.md#hand-soldering)) rather than accept it standing proud.
- JLCCNC: the amber is matched or falls back to their orange (the SHIFT cap legend follows, above); the UV
  legends are 6.1 to 6.9 pt, at their 6 pt minimum, so a flag means a sample or a little blur; the web is 4.0
  ±0.1 (ask for 3.9 to 4.1 if they offer less); the RANGE pocket leaves 0.65 mm of metal (their minimum 0.5):
  hold its depth +0/-0.1 rather than thicken the floor; threads they say they cannot mask: ask for them to be
  cut after anodising.
- JLC3DP: the light pipes (Ø2.0 rods, Ø2.8 bases on Ø1.0 necks), the outer knob key (1.4 mm wide, under 1.5
  for positioning features, or it would not clear a narrow shaft slot), the cap set dimples (0.86 mm of wall
  on a worst print) and tactile bars (0.5 mm proud), the MJF body's screw bosses (1.6 mm, over the 1.5 mm for
  fasteners) and the USB-C filler (2.0 mm thick, exactly the 10 x 2 x 2 mm minimum): ask them to print as is.

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
the variants, all Ø17) and the mechanical rework (the plate milled from 12 mm stock with tapped bosses,
deeper pockets, hollow body, four cap sets with rigid ribs, stepped light pipes over reverse-mount LEDs, the
FMS ring and its fit variants, the USB-C filler), so re-upload the board, plate and all JLC3DP files before
paying. The JLC3DP price below is too
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
including shipping in the economic variant, about €370 to 420 in the full one, plus the screws (JLCMC, a few
dollars of screws and their own parcel's shipping) and the few consumables.

## Checklist

1. Run `./build.sh`; it must finish with every check passing.
2. Full variant (default): buy the six encoders into the JLCPCB parts library now
   ([above](#full-variant-through-hole-parts-at-jlcpcb)).
3. JLCCNC first: `plate.step`, `plate-drawing.pdf` and `plate.dxf`, finishes as in the table and the remark
   above. Wait for their review before paying JLC3DP: it can change the light holes (and so the pipes) and the
   amber ([before paying](#before-paying)); if it does, change `stack.py`, run `./build.sh` again and upload the
   new files. Pay JLCCNC after their review.
4. JLCPCB: `gerbers.zip`, the options in the table, and per variant:
   - Full (default): Standard assembly, both sides; `BOM-full.csv` and `CPL-full.csv` (the BOM step must find
     all 27 lines with stock for 2 boards); Edge Rails/Fiducials: Added by JLCPCB; the remark
     [above](#full-variant-through-hole-parts-at-jlcpcb).
   - Economic: Economic assembly, bottom side; `BOM.csv` and `CPL.csv`; Edge Rails/Fiducials: None; the remark
     under [edge rails](#edge-rails).

   Go through the [placement preview](#placement-preview). If JLC3DP is to join this cart (step 5), hold the
   payment until JLCCNC's review is back; otherwise pay now.
5. JLC3DP, after JLCCNC's review: body and USB-C filler (MJF, dyed black, the filler quantity 2), `caps-A.zip`
   to `caps-D.zip` (full colour), the knobs with the counts in the table, light pipes (8001, quantity 2, no
   post-processing); 19 files, so two uploads. Pay and ship it on its own unless JLCPCB and JLC3DP together stay
   under €150 of goods (economic variant only; the €150 note above).
6. LCSC, shipped on its own: full variant, the two spare keys (C589907) and the reference RKJXT1F42001
   (C160841); economic, `THT-LCSC.csv` in the BOM tool, encoders early (small stock).
7. JLCMC, its own order and parcel: the M3 x 8 flanged button-head screws from the table.
8. Locally: the feet, consumables and tools from the table and, if wanted, the notched 2 mm steel plate
   (`steel.dxf`).
9. Bench: the Pico, buttons, encoder and diode from the table, to run the firmware before the boards arrive
   ([Firmware](firmware.md#pico-bench)).
10. [Before paying](#before-paying) each order: the review watch items and the tax lines.
