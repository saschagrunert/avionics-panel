# Status

Rev 1 is designed and checked; nothing is ordered yet.

## Before ordering

- Upload the current files to the four quotes (JLCPCB, JLC3DP, JLCCNC, LCSC; see the
  [checklist](ordering.md#checklist)).
- JLCCNC reviews the plate before payment. The plate has no threads now (four glued standoffs in 2 mm
  flat-bottom pockets); the remark in [Ordering](ordering.md) also carries the laser marking and the amber
  UV print. Watch for a flag on the 0.85 mm webs between the light holes (+0.1/-0) and the SHIFT and UNIT
  key holes (+0.1/-0 after anodising; 0.75 mm with both at +0.1, JLCCNC recommends 0.8 and allows 0.5); if
  they flag those, shrink `LIGHT_HOLES` in [mech/stack.py](../mech/stack.py) to 1.6 mm (SHIFT) and 1.4 mm
  (UNIT): the pipes follow, 0.3 mm under their holes. JLCCNC publishes no flatness capability, so the
  remark's flatness 0.1 mm after bead blasting and anodising may come back as a review question or a
  surcharge.
- JLC3DP: check that the four cap files with 28 separate caps each are accepted (see
  [Ordering](ordering.md)).
- Watch items for JLC's reviews, below their published minimums where the design leaves no room:
  - SLA light pipes: the Ø1.5 and Ø1.3 mm rods, 3.6 mm long, exceed the resin pillar guideline (Ø1.0 up to
    1 mm, Ø2.0 up to 4 mm). If flagged or broken, use the PMMA fibre fallback in [Ordering](ordering.md).
  - SLA outer knob key: 1.4 mm wide, under the 1.5 mm asked for positioning features; at 1.5 a key
    printed 0.2 mm wide would no longer clear the narrowest shaft slot (1.7 mm).
  - WJP caps: the set dimples leave 1.11 mm to the socket and the outline, 0.86 mm on a print with the
    outline 0.2 mm small and both holes 0.3 mm large (no spot between the 3.8 mm socket and a 6.4 mm wide
    cap keeps 1.0 there); the socket wall is 1.05 mm on such a print. The tactile bars are 1.0 mm wide but
    only 0.5 mm proud (embossed detail 0.8 mm), so the front bars don't hide the SHIFT and DN legends.
  - MJF body: the screw bosses are fastener features at 1.6 mm (seat under the PCB, wall round the
    counterbore; over JLC3DP's 1.5 mm for fasteners, under the 2.0 mm general wall for parts over
    100 mm). Every other wall, rib and the floor is 2.0 mm or more, bar the front edge of the floor: the
    6° bottom plane leaves 1.6 mm there, about 1.8 mm just inside the front wall and 2.0 mm from about
    3.8 mm in.
  - JLCPCB: the paste layer has openings on the four J1 shell pads (pin-in-paste). If their engineer
    drops them from the stencil, nothing changes: the tabs are soldered by hand from the top anyway
    (bring-up step 1, [Mechanics](mechanics.md#hand-soldering)).
- On arrival, first: break the V-scored edge rails off both boards and file or sand the short edges
  flush ([Ordering](ordering.md#ordering)); with the rails on the board is about 170 mm long, too long
  for the body, and the bow check below needs a bare edge. Then measure each board's length with calipers
  and sand the short edges until it is 160.2 mm or shorter: a V-cut edge is only held to ±0.4 mm, and the
  cavity is 160.36 mm long with the body printed 0.4 % small. If a corner comes back square, file it to
  R3.
- On arrival: try one cap of each set (A to D) and fit the set that seats on the plunger top and holds;
  see [Mechanics](mechanics.md#caps-light-pipes-knobs).
- On arrival, before soldering: lay each board top side down on a flat surface (glass; the top side is
  still bare) and press the middle of its front edge down. A 0.1 mm feeler gauge must not slide under any
  corner: the stack takes 0.1 mm of bow towards the plate at the SHIFT and UNIT LEDs, near the middle of
  the board (`stack.PCB_BOW`; JLCPCB allows 0.75 %). A board bowed more gets both LEDs soldered fully
  flat, which gives back 0.2 mm. Lay the plate face down on glass too: a 0.1 mm feeler gauge must not
  slide under it anywhere (flatness 0.1 after bead blasting and anodising, as on the drawing).

## Bench and first board

- Run the firmware on a Pico first (`PICO_TEST = True` in [code.py](../firmware/code.py): a plain Pico
  lacks GP23, GP24, GP25 and GP29 on its header, so the FREQ knob moves to GP12-15 and its push to GP22;
  the RANGE encoder still runs on GP28/GP29 but can't be turned there). Check: two joysticks in
  MobiFlight (same name: 128 and 64 buttons), the [knob pulse timing](firmware.md) (112 ms per step, also
  with both joysticks sending at once: hold UP, which always sends on device 1 and repeats every 125 ms,
  while spinning the bench encoder on the FMS inner ring's pins GP16 / GP17 in UNIT 2; wiring in
  [Firmware](firmware.md#install-and-bring-up)), encoder directions, ring order (outer / inner) and
  the RANGE tilt directions (`PAN_DIRS` in [panel.py](../firmware/panel.py)). Check whether the GUIDs
  differ: do MobiFlight and joy.cpl list the joysticks as new controllers after a plug-in with SHIFT held
  (drive and console on)? See [Firmware](firmware.md#install-and-bring-up).
- On the first board, check GP25: the Pico CircuitPython build drives it as its status LED during boot
  and in safe mode, and here it is the FREQ outer encoder's B line (harmless, limited current). A custom
  board definition would avoid it. Moving that line to the spare GP14 was tried: its fan-out is boxed in,
  and none of 13 router seeds could route it.
- On the first board, repeat the knob timing check with two knobs: spin the FMS inner ring and the
  ALT/HDG knob at the same time in UNIT 2 ([Firmware](firmware.md)).
- On the first board, check for phantom presses: a held key must not press the one right below it in its
  matrix column (UP to DN, DN to RANGE_A, ENT to FMS push, HOME to SHIFT: the amber light; bring-up steps
  6 and 7 in [Firmware](firmware.md#install-and-bring-up)).
- Check the white UNIT light; if it is too dim, fit 0 R for R_UNIT ([Electronics](electronics.md#lights)).
  The Pico bench can't tell: `PICO_TEST` prints the UNIT state instead of lighting an LED.

## In the sim

- Verify which GTN 750Xi functions TDS exposes as events. HOME, D→ and the knob are bezel controls;
  FPL, PROC, MENU, CLR, ENT, MSG, NRST, TERR, VNAV, MAP, CDI and OBS are touchscreen functions on the real
  GTN and only work from the panel if TDS offers events for them.
- One MobiFlight profile per avionics family (G1000, GTN 750Xi, GNS 530/430, Bendix/King, GFC 500/G3X),
  following the [compatibility tables](compatibility.md) and [BUTTONS.md](../firmware/BUTTONS.md).
- Planned firmware feature (Reddit feedback): a keyboard mode, picked by holding a key at power-up, in
  which the panel is a USB keyboard and every key and knob detent sends a unique shortcut (for example
  Ctrl+Shift+F-keys, avoiding keys that move between keyboard layouts). The shortcuts are bound once in
  MSFS's own controls menu, so it works without MobiFlight, and on consoles, which accept USB keyboards but
  usually ignore generic joysticks. Firmware only, no hardware change. Many MSFS functions (FMS knobs,
  softkeys, BARO) have no default key, so a binding table replaces presetting the defaults. To verify
  first: whether MSFS on PS5 and Xbox accepts USB keyboard bindings for these functions; on the PC the
  keys only reach MSFS while it has the focus.

## Rev 2

- No ESD protection or fuse on USB, common for DIY boards.
- Three 100 nF caps (C_D0, C_D1, C_D3) and the 1 uF C_D2 serve the RP2040's six IOVDD pins plus USB_VDD,
  ADC_AVDD and VREG_VIN, where Raspberry Pi's minimal design has one 100 nF per IOVDD pin (the 3V3 and GND
  inner planes make it very likely fine).

## Done

- RANGE footprint checked against JLC's own (C160841), encoder footprint against JLC's own
  (C19270361); LED and resistor part numbers; plate attachment; knob and light-pipe models; rev 1
  firmware; live JLC quotes (2026-11-09).
- Reddit feedback: FD plain with YD shifted, DME audio instead of MKR, CRS and BARO kept behind SHIFT,
  cockpit lighting dimmers behind SHIFT on the FMS knob.
- First external review: the regulator, crystal and USB-C footprints are mirrored for the bottom side
  (the USB-C pad row follows JLC's footprint of C165948), the second VBUS pad is tied, SWD debug pads
  and PCB support posts added, key switch changed to TE 1-1825910-4 (the C&K PTS645SL95 is out of
  stock at JLC).
- Encoders changed from the Alps EC11EBB24C03 (not recommended for new designs) to the Bourns
  PEC11D-4120F-S0015.
- Second review: code.py retries a HID report instead of stopping when USB is not ready at power-up,
  the JLCPCB BOM and CPL hold only the bottom side, the body bosses are thicker around the screw heads
  (now 1.0 mm round the counterbore, 1.6 mm above it), and the knobs come with tighter and looser bore variants.
- Third review: tactile bars on the SHIFT, UP and DN caps are now part of the printed mesh, the flash
  footprint follows JLC's of C2456211 (rows 5.37 mm apart), the fan-out breakout points stay under the solder
  mask, the viewer serves its fonts and three.js itself (no Google Fonts, no CDN), Apache-2.0 license.
- Reddit and review follow-ups (2026-11-10): the SHIFT light pulses before SHIFT drops out, cockpit
  lighting on SHIFT and the FMS knob, VFR as the plain key with IDENT behind SHIFT, consistent knob
  legends, one renumbering of the joystick buttons (frozen from the first build on), and the firmware
  checked to compile with MicroPython.
- Pre-order mechanics review (2026-11-10): glued M2.5 standoffs instead of threads milled into the plate
  (no shimming), flexing cap ribs for a 3.10 to 3.3 mm plunger plus three test caps, outer knob seated on
  its slot floor, 1.0 mm between the knobs when pushed, wider knob fit variants, 1.0 mm light-pipe necks,
  thicker RANGE skirt rim, one amber for caps, plate and 3D view.
- Pre-order firmware review (2026-11-10): the drive and serial console only appear with SHIFT held at
  power-up, a crash releases all buttons and reloads `code.py`, 50 / 40 ms knob pulses for MobiFlight's
  polling (superseded by 56 / 56 ms, see below), reversing a knob drops its queued steps, failed USB sends
  back off (one loop pass waits for at most one of them), held shifted pushes and tilts keep SHIFT and its
  light, also through a stalled pass, and the RANGE centre push is shifted as at its press.
- Pre-order review round 1, mechanics and PCB (PR #8): rigid-rib cap sockets on the plunger's cone (from
  TE's STEP model) in three fit sets instead of flexing ribs and test caps, standoffs glued with the
  assembled board as the jig and a non-sag epoxy, 1.4 mm outer knob key, light pipes 0.3 mm under their
  holes, check_fit rows with the slot, print and plug tolerances, the mounting-hole copper keep-out checked
  on the Gerbers, cleanups in check.py and the footprint fetcher.
- Pre-order review round 2, mechanics and order docs (PR #8): a fourth cap set (D, 3.05 mm) so the sets
  cover rib circles printed 0.21 mm small to 0.22 mm large; cap legends in Barlow Semi Condensed Bold
  with every stroke at least 0.4 mm, tactile bars 1.0 mm wide (0.5 proud, so they hide no legend) and
  dimples 0.9 mm deep (JLC3DP detail minimums); FMS ring fit variants; pin-in-paste on the USB-C shell
  tabs; 2.0 mm body walls and ribs, 1.6 mm round the counterbores, a shorter steel plate that keeps the
  floor whole; Ø9.2 encoder holes and a Ø19.2 RANGE pocket for the worst board offset; support posts 0.25
  mm short; light holes +0.1/-0; sturdier light-pipe necks with a fibre fallback; DXF units in the
  header; updated ordering and gluing steps.
- Garmin knob proportions (2026-11-10): all three outer rings Ø17 (were 22, 22 and 24), inner knobs Ø12
  (were 13), with a thinner neck and recess between them and the knob legends turned to stay in view.
- Knob review (2026-11-10): no neck on the outer ring, so every resin wall keeps 1.0 mm and the inner knob
  clears the outer shaft at the worst print and fit; a coarser FMS ring to tell it from FREQ by feel;
  flutes and the outer diameter in one place each, also for the 3D view; a 3.8 mm cap socket so the cap
  wall keeps 1.0 mm at the worst print; flute grooves at least 0.8 mm wide; the outer knob key 0.7 mm into
  the slot and clear of the inner shaft.
- Final pre-order mechanics review (2026-11-10): the USB-C opening widened to 15.8 x 8.4 mm (R0.5) and
  carried up through the back wall so the socket clears it, the steel plate 0.5 mm smaller than its
  recess, key holes +0.1/-0 after anodising and counted in the board offset, 3.6 mm light pipes with a
  PCB bow budget, a Ø16.6 RANGE skirt, the RKJXT float of 0.26 mm (from Alps' STEP model) with a Ø19.6
  RANGE pocket and a Ø11.2 hole, the pan arrows clear of the skirt, and the bench parts, gluing tools and
  a second through-hole set in the order list. Board changes in the same round: 10 k column pull-ups,
  C_D2 at 1 uF next to VREG_VIN (the old C_VIN, renamed C_BULK, stays as 3V3 bulk), the LED resistors
  moved beside the LEDs, 1.1 mm RKJXT pin holes, and new `check.py` checks (1.0 mm round every
  hand-soldered pad, at least 1 uF at pins 44 and 45, the through-hole footprints against JLC's own).
  Firmware and docs in the same round: 56 / 56 ms knob pulses (press and gap outlast MobiFlight's poll
  even with an edge three 8 ms USB frames late), the board files also compiled with CircuitPython 9.2's
  own mpy-cross (pinned, patched for Nix's glibc), and phantom-press and joystick-naming checks in the
  bring-up.
