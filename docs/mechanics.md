# Mechanics

Body, front plate, knobs, light pipes and key caps. Every height and fit is in
[mech/stack.py](../mech/stack.py); [mech/check_fit.py](../mech/check_fit.py) checks the clearances.

## Stack and assembly

Stack (z = 0 is the PCB top):

| z (mm) | Part |
| --- | --- |
| -7.6 to -5.6 | body floor, 2 mm (1.6 at the front edge); below it the 6° wedge is hollow down to the desk plane (-7.2 at the front, about -14 at the back), with ribs, a solid band along the front, four foot pads and a recess for an optional steel plate |
| -5.6 to -1.6 | 4 bosses (Ø8 on the PCB, joined to the corner walls) carry the PCB corners, 2 posts the middle (between the key blocks) |
| -2.5 | counterbore seats (Ø8.4, 1 mm wall): one to four washers and the pan head below them stay recessed |
| -1.6 to 0 | PCB |
| 0 to 6 | 4 metal round spacers (5 mm OD, about 2.7 mm ID, 6.0 mm long) between PCB and plate: they alone set the plate height; the body walls end at 5.1. Encoder bodies 8 mm (±0.3), RANGE body 8.6 mm |
| 6 to 10 | 4 mm (±0.1) aluminium plate, pockets 2.8 mm (encoders, at least 1.1 mm left) and 3.2 mm (RANGE, at least 0.7 mm left) deep from below, +0/-0.1; M2.5 threads milled in flat-bottom holes 3.2 +0/-0.1 mm deep, full thread from 0.1 to at least 2.6 mm, at least 0.7 mm left to the front |
| 10 to 12.5 | key caps, 2.5 mm proud |
| 10.8 to 18 | outer knob ring |
| 18.8 to 29.2 | inner knob, sitting on the 28 mm tip of the inner shaft |

- Four M2.5 x 12 pan-head screws (ISO 7045 or ISO 14583, head up to 5 mm across and 1.75 mm high) from
  below hold everything: body boss, PCB, spacer, blind thread in the plate. Nothing shows on the front.
  Socket heads (2.5 mm high) do not fit under four washers at the front corners. One washer type does
  everything: DIN 125-A M3 (3.2 x 7 x 0.5) on the M2.5 screw. One goes under every head. The 8.4 mm
  counterbore is only a little wider than the washer, so its wall, not the screw, keeps the washer over
  the body hole: it bears all round even with the screw against the hole wall. An M2.5 washer slides
  0.23 mm on the screw and can overhang the hole.
- The screws are shimmed to fit with those washers. The threads are milled in flat-bottom holes (no tap
  lead), and the last 2 pitches of a screw end are incomplete (ISO 4753). A screw may stop at the end of
  the full thread (2.6 mm at worst) or at the floor. Tighten each screw with its head washer; if it
  stops before the parts clamp, it has bottomed: add one more washer and try again. The shortest stack
  (screw length ±0.35, MJF counterbore ±0.3, PCB ±0.16, spacer ±0.05) clamps on the head washer alone,
  the longest needs up to three more. Either way at least 1.1 mm (2.4 turns) of full thread engage on
  both parts, and the counterbores hold four washers under a pan head, recessed even at the front
  corners where the bottom rises. Tighten gently.
- The screws do not locate the board: the key caps centre it in the 10.2 x 7.0 mm key holes (0.3 mm per
  side, against about 0.23 mm of per-key errors, RSS), and the board can still sit up to about 0.39 mm
  off (the caps shift 0.34 mm diagonally). The 4.2 mm PCB mounting holes keep the screws off their edges
  across that offset and the plate (±0.1), PCB drill (±0.075) and hole size (±0.2) tolerances; the 5 mm
  spacers stay inside the 3.6 mm copper keep-out with their play on the screw. The body holes (3.7 mm,
  counterbores 8.4 mm) clear the screws and washers with the MJF body up to 0.6 mm off over its length;
  at least 1.4 mm of wall stays outside each counterbore. The cavity leaves 0.5 mm per side round the
  PCB, so the board fits even with the body 0.4 % small.
- Held only at the corners (153 mm apart), the PCB would sag 0.3 to 0.5 mm under a key press in the
  middle, about the switch travel. Two posts at board positions (72.3, 30.8) and (98.6, 30.8), free of
  bottom parts and pins, just touch its underside.
- Assembly, face down. The encoder shafts stick out 18 mm past the plate face, so the plate rests on two
  blocks (books, wood) at least 25 mm high under its long front and back edges, at most 8 mm in from
  the edge (the nearest caps and shafts are about 10 mm in), with a cloth on top.
  1. Push all caps onto their plungers first, tactile bars as in the 3D view; a cap that falls off when
     the board is turned over is too loose anyway.
  2. Lay the plate face down on the blocks. Put tape over the two light holes on the front, push each
     light pipe in from the back until it touches the tape (top flush with the face) and fix it with a
     drop of clear epoxy or UV glue at the back; not CA glue, it fogs clear resin. Let it cure, then
     stand the four spacers on the threaded holes.
  3. Lower the PCB, caps and shafts down: the caps drop into their key holes and centre the board.
  4. Set the body on, then the four screws, each with a washer. If a screw stops before the parts
     clamp, it has bottomed: add a washer as above.
  5. Turn it over and fit the knobs: outer knob key into the shaft slot, inner knob onto the D flat.
- Key caps hold the switch's 3.10 mm (±0.30) plunger in a 3.6 mm bore with three ribs reaching in to
  3.05 mm. The ribs are 0.8 mm wide, the smallest detail the full-colour process prints (sizes ±0.2 mm,
  holes ±0.1 to 0.2 mm). Rigid resin does not crush, so this grips plungers of about 3.05 to 3.25 mm when
  the print comes out true; the full ±0.30 range is wider than any rigid socket covers. Measure a plunger
  and test-print one cap first; change `stack.CAP_SOCKET` if needed.
- Light pipes are plain rods 0.08 mm under their holes (anodising shrinks the holes a little), glued in
  flush with the face. Under the 4 mm plate only 0.7 mm is left above the LEDs, too little for a collar
  that keeps a loose pipe captive without ever touching the plate. Glued, the 3.95 mm pipe's bottom stays
  at least 0.1 mm over an LED soldered 0.3 mm proud (LED top 5.3 +0.4/-0.1 mm, pipe ±0.1, plate ±0.1,
  spacer ±0.05), so the board never pushes on it. Both pipes print on a bar over their tops: sand the
  stub off with the top and polish it before gluing.
- The key holes are 4 mm deep now; a pressed cap (0.35 mm travel) still ends at least 0.1 mm inside its hole.
- Knob bores are drawn at the datasheet shaft size (`stack.FIT` = 0): the shafts are toleranced +0/-0.05
  and +0/-0.1 mm, which leaves 0 to 0.1 mm real clearance. The knobs are held by friction only and resin
  prints vary, so one outer, one inner and the RANGE knob also come with a bore 0.1 mm tighter and 0.1 mm
  looser (`stack.FIT_VARIANTS`). Try those first, then keep the fit that grips and reprint the rest with
  that `FIT` if needed.
- The knobs stand 19.2 mm above the plate (29.2 above the PCB), set by the uncut PEC11D shafts: the outer
  knob grips 4.6 mm of the 6 mm shaft above the bushing, the inner knob the 7 mm D flat.
- `mech/check_fit.py` draws sections through the ALT/HDG knob, the RANGE knob and the SHIFT light pipe
  and checks every clearance, including the RANGE skirt at full 9° tilt (about 0.5 mm left).
- BOOT: two bridge pads on the underside of the PCB under a 5 mm hole in the case floor. Bridge them
  with a small screwdriver while plugging in USB. Recovery only: normal updates enter the bootloader
  from software.
- Four self-adhesive feet up to 10 mm across, on the four flat 12 mm pads under the corners (with or
  without the steel plate). The aluminium plate adds about 84 g; the printed body is hollow under its
  2 mm floor (about 37 cm3, ribs down to the desk plane, no slot under 0.8 mm). The panel may still slide
  when knobs are turned one-handed, so a recess in the bottom takes an optional 2 mm steel plate,
  144 x 48 mm with two 15 x 15 mm notches at the back corners for the feet (about 100 g), held with
  double-sided tape.

## Dimensions

| Item | Value |
| --- | --- |
| PCB | 160 × 60 mm, 4 layers, every SMD part on the bottom (see `pcb/board.py`) |
| Case | about 165 × 65 mm, 17 mm high at the front, 24 mm at the back (6° wedge). Chosen for a flat desk in front of the pilot; a steeper angle (12°) only pays off when the panel sits further away or lower |
| Key pitch | 11.85 mm horizontal (17.1 mm between AUTOPILOT and AUDIO), 11 mm vertical; 14.5 mm between rows 2 and 3 for the FMS line. Rows stay aligned across the panel on purpose, so the autopilot block shares that gap |
| Caps | 9.6 × 6.4 mm, 2.5 mm proud, one legend size (about 2.0 mm cap height, Barlow Semi Condensed), condensed face; the flip-flop icon is narrow so COM ⇆ does not shrink every legend |
| Dual knob centres | x 15 and 145, y 15 and 45 (30 mm apart; gap 11.2 mm left to the RANGE skirt, 7 mm right) |
| Knobs | avionics style: matte black resin, fine vertical flutes, slight taper, chamfered flat top, no index line. Outer ring 7.2 mm tall, inner knob Ø13 × 10.4 mm above it: 19.2 mm above the plate. RANGE Ø13.6 with a Ø15.6 skirt |
| SHIFT light | Ø1.8 mm light pipe below the SHIFT cap, amber LED on the PCB |
| UNIT 2 light | Ø1.6 mm light pipe right of the UNIT engraving, white LED on the PCB |
