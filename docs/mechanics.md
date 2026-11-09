# Mechanics

Body, front plate, knobs, light pipes and key caps. Every height and fit is in
[mech/stack.py](../mech/stack.py); [mech/check_fit.py](../mech/check_fit.py) checks the clearances.

## Stack and assembly

Stack (z = 0 is the PCB top):

| z (mm) | Part |
| --- | --- |
| -7.2 to -5.6 | body floor at the front edge, deeper towards the back (6° wedge) |
| -5.6 to -1.6 | 4 bosses (Ø7.2) carry the PCB corners, 2 posts the middle (between the key blocks) |
| -4.1 | screw heads, recessed in the bosses (0.8 mm wall) |
| -1.6 to 0 | PCB |
| 0 to 7 | 4 printed spacer tubes (5 mm OD) between PCB and plate: they alone set the plate height; the body walls end at 6.7. Encoder bodies 8 mm, RANGE body 8.6 mm |
| 7 to 10 | aluminium plate, pockets 1.3 mm (encoders) and 2 mm (RANGE) deep from below; M2.5 threads 1.2 mm full thread, drilled 2.2 mm deep including the point, 0.8 mm left to the front |
| 10 to 12.5 | key caps, 2.5 mm proud |
| 10.8 to 18 | outer knob ring |
| 18.8 to 29.2 | inner knob, sitting on the 28 mm tip of the inner shaft |

- Four M2.5 x 12 screws from below hold everything: body boss, PCB, spacer, blind thread in the plate.
  Nothing shows on the front. The screw tip stops 0.3 mm short of the last full thread, room for screw
  length and print tolerances, so the screws clamp instead of bottoming out. About two threads carry the
  load: plenty for a light panel, but tighten gently.
- Held only at the corners (153 mm apart), the PCB would sag 0.3 to 0.5 mm under a key press in the
  middle, about the switch travel. Two posts at board positions (72.3, 30.8) and (98.6, 30.8), free of
  bottom parts and pins, just touch its underside.
- Assembly: put the spacers on the PCB mounting holes, lay the plate on, turn it over, set the body on,
  screw. Push the light pipes into the plate from below before the plate goes on (flat on the collar
  towards the key). Then the knobs: outer knob key into the shaft slot, inner knob onto the D flat.
- Key caps grip the switch's 3.10 mm plunger with a 3.05 mm socket. Test-print one cap first; full-colour
  prints vary. Light pipes are 0.08 mm under their holes (anodising shrinks the holes a little).
- Knob fits are drawn for the datasheet shafts with 0.05 mm allowance (`stack.FIT`). The knobs are held
  by friction only and resin prints vary, so one outer and one inner knob also come with a bore 0.1 mm
  tighter and 0.1 mm looser (`stack.FIT_VARIANTS`). Try those first, then keep the fit that grips and
  reprint the rest with that `FIT` if needed.
- The knobs stand 19.2 mm above the plate (29.2 above the PCB), set by the uncut PEC11D shafts: the outer
  knob grips 4.6 mm of the 6 mm shaft above the bushing, the inner knob the 7 mm D flat.
- `mech/check_fit.py` draws sections through the ALT/HDG knob, the RANGE knob and the SHIFT light pipe
  and checks every clearance, including the RANGE skirt at full 9° tilt (about 0.5 mm left).
- BOOT: two bridge pads on the underside of the PCB under a 5 mm hole in the case floor. Bridge them
  with a small screwdriver while plugging in USB. Recovery only: normal updates enter the bootloader
  from software.
- Four silicone feet. The aluminium plate adds about 65 g; the panel may still slide when knobs are
  turned one-handed, so an optional steel plate (about 2 mm) in the floor adds weight.

## Dimensions

| Item | Value |
| --- | --- |
| PCB | 160 × 60 mm, 4 layers, every SMD part on the bottom (see `pcb/board.py`) |
| Case | about 165 × 65 mm, 17 mm high at the front, 24 mm at the back (6° wedge). Chosen for a flat desk in front of the pilot; a steeper angle (12°) only pays off when the panel sits further away or lower |
| Key pitch | 11.85 mm horizontal (17.1 mm between AUTOPILOT and AUDIO), 11 mm vertical; 14.5 mm between rows 2 and 3 for the FMS line. Rows stay aligned across the panel on purpose, so the autopilot block shares that gap |
| Caps | 9.6 × 6.4 mm, 2.5 mm proud, one legend size (about 2.0 mm cap height, Barlow Semi Condensed), condensed face; the flip-flop icon is narrow so COM ⇆ does not shrink every legend |
| Dual knob centres | x 15 and 145, y 15 and 45 (30 mm apart; gap 8 mm left, 7 mm right) |
| Knobs | avionics style: matte black resin, fine vertical flutes, slight taper, chamfered flat top, no index line. Outer ring 7.2 mm tall, inner knob Ø13 × 10.4 mm above it: 19.2 mm above the plate. RANGE Ø13.6 with a Ø15.6 skirt |
| SHIFT light | Ø1.8 mm light pipe below the SHIFT cap, amber LED on the PCB |
| UNIT 2 light | Ø1.6 mm light pipe right of the UNIT engraving, white LED on the PCB |
