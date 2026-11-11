# Mechanics

Body, front plate, knobs, light pipes and key caps. Every height and fit is in
[mech/stack.py](../mech/stack.py); [mech/check_fit.py](../mech/check_fit.py) checks the clearances.

## Stack and assembly

Stack (z = 0 is the PCB top):

| z (mm) | Part |
| --- | --- |
| -7.6 to -5.6 | body floor, 2 mm (1.6 at the front edge); below it the 6° wedge is hollow down to the desk plane (-7.2 at the front, about -14 at the back), with 2 mm ribs, a solid band along the front, four foot pads and a recess for an optional steel plate |
| -5.6 to -1.6 | 4 bosses (Ø8 on the PCB, joined to the corner walls) carry the PCB corners; 2 posts under the middle (between the key blocks) end 0.25 mm under the PCB |
| -3.2 | counterbore seats (Ø8.4, 1.9 mm wall), 1.6 mm of PA12 up to the PCB: the washer and the pan head below it stay recessed |
| -1.6 to 0 | PCB |
| 0 to 8 | 4 M2.5 x 8 female-female hex standoffs (5 mm across flats), the top 2 mm glued into the plate: they alone set the plate height, 6.0 +0.2/-0.1 mm over the PCB to the plate back (anodising: see [Fastening](#fastening)); the body walls end at 5.05. Encoder bodies 8 mm (±0.3), RANGE body 8.6 mm, key switch bodies 3.6 mm |
| 6 to 10 | 4 mm (±0.1 before anodising) aluminium plate, pockets 2.8 mm (encoders, at least 1.1 mm left) and 3.25 mm (RANGE, at least 0.65 mm left) deep from below, +0/-0.1; 4 round standoff pockets Ø7.0 +0.1/-0, 2.0 +0/-0.1 mm deep (at least 1.9 mm left); no threads |
| 6.8 to 12.5 | key caps, socket ceiling on the plunger top (9.5), 2.5 mm proud |
| 11.09 to 18 | outer knob ring |
| 19.5 to 29.9 | inner knob, sitting on the 28 mm tip of the inner shaft |

### Fastening

- Four M2.5 x 8 pan-head screws (ISO 7045 or ISO 14583, head up to 5 mm across and 1.75 mm high), each
  with one DIN 125-A M3 washer (3.2 x 7 x 0.5), come from below and hold everything: body boss, PCB,
  standoff. Nothing shows on the front. The 8.4 mm counterbore is only a little wider than the washer, so
  its wall, not the screw, keeps the washer over the 3.7 mm body hole: it bears all round even with the
  screw against the hole wall, which a pan head alone does not.
- The standoffs are glued with non-sag epoxy into flat-bottom pockets in the plate back. The screw pulls
  the standoff against the PCB and the PCB against the boss; the plate only hangs on the glue, which
  carries no screw preload (nothing presses on the plate in use: caps and knobs act on the switches and
  shafts).
- Screw length does not matter much any more: from the counterbore seat to the PCB top is 3.2 mm (±0.3
  MJF, ±0.16 PCB), so the tip of an M2.5 x 8 (±0.29) ends 3.5 to 5.1 mm into the standoff. Less the
  incomplete end of the screw (2 pitches) and the standoff's entry chamfer, at least 2.3 mm (5 turns) of
  full thread engage, and the tip stays at least 0.8 mm short of the wax plug in the plate end of the
  standoff (see gluing) and of the pocket. M2.5 x 10 would reach it. Socket heads (2.5 high) also fit but
  stand closer to the desk.
- Anodising grows every surface by up to about 0.025 mm. The drawing lets the pockets be anodised or bare, but
  all alike (all anodised or all bare: an anodised RANGE pocket over bare standoff pockets would come 0.025 mm
  closer to the RKJXT than the stack allows), so the standoff ends sit on anodised floors or on bare metal;
  either way the pocket floors keep their place against the back face (both grow, or neither does), so every
  pocket depth counts from the 6.0 +0.2/-0.1 mm gap as it is. Only the faces move: over bare floors the back
  face sits up to 0.025 mm lower; on anodised floors the whole plate stands 0.025 mm higher and its front face
  grows as much, so the highest front face is 6.2 + 4.1 + 0.05 = 10.35 mm over the PCB (4.0 ±0.1 mm before anodising).
  `check_fit.py` takes the worse case in every row: the LED and the body walls under the back, the knobs over
  the face.
- Positions: the key caps centre the board in the 10.2 x 7.0 mm key holes (+0.1/-0 after anodising, so at
  least 0.3 mm per side, against about 0.23 mm of per-key errors, RSS), and in holes at +0.1 it can still
  sit up to about 0.44 mm off. A cap can turn on its round plunger, and a turned cap has less room: at 1°
  about 0.24 mm, just over the per-key errors, and past about 5° it no longer goes into its hole at all. So
  each row of caps is squared against a steel rule before the plate goes on (assembly step 1);
  `check_fit.py` takes the room at 1°. The standoffs follow the board, not the plate: they are screwed onto the
  board before gluing, and each one enters its 7 mm pocket wherever the caps put the board (about 0.6 mm
  of play round the 5.77 mm corners, plus the screw's play in its PCB hole), so each one ends up on the
  axis of its screw. With the board up to 0.44 mm off, the 7.0 mm pocket leaves 0.12 mm of that play to
  spare; a 6.8 mm pocket would even out the glue gap a little but leave only about 0.02 mm, so the pocket
  stays at 7.0 mm and the non-sag epoxy fills the gap. The PCB holes must be close round the screw:
  3.0 mm (2.8 to 3.2 with JLCPCB's ±0.2) keeps each standoff within 0.44 mm of its hole, so its end
  (4.9 mm across flats at least) covers the hole all round with 0.41 mm to spare, its corners stay
  0.28 mm inside the 3.6 mm copper keep-out ([pcb/check.py](../pcb/check.py) checks the copper on the
  Gerbers), and the screw still passes the narrowest hole. A 4.2 mm hole would let a standoff end up
  1.04 mm off, past the keep-out and with the hole edge uncovered.
- The same board offset (plus the plate, PCB and pin tolerances, about 0.77 mm radially) moves the controls in
  their plate openings. Every opening here is at ISO 2768-m (±0.2) and loses about 0.05 mm to the anodising,
  which `check_fit.py` counts. It also takes the encoders and the RKJXT seated as far as their checks allow
  (see [on arrival](#on-arrival)): an encoder 0.05 mm proud (`stack.SEAT_GAP`), which lifts its lugs 0.05 mm,
  or tilted by that over the body, which moves its bushing up to 0.04 mm sideways at the plate face; the RKJXT
  with no gauge spot under its base frame 0.05 mm higher than on a seated part (`stack.RKJXT_SEAT`), which
  tilts it by up to 0.05 mm over 11.8 mm (see the RANGE control under [hand-soldering](#hand-soldering)) and
  lifts the corners of its octagon up to 0.064 mm. And it takes the plate bowed towards the board as far as
  the drawing allows, up to about half of the 0.1 mm near the knobs on a plate bowed across its width (see [on
  arrival](#on-arrival)). The Ø9.3 encoder holes still leave 0.06 mm round the bushings (7.0 +0.3; 0.11 mm
  with the encoder flat), and the 15.6 x 20 encoder pockets 0.07 mm beside the side lugs (13.1 ±0.5 across,
  the PEC11D drawing) and 0.20 mm over the bodies (0.11 and 0.25 mm flat). The RKJXT floats more on its pins
  (0.26 mm instead of 0.15, see [hand-soldering](#hand-soldering)), 0.88 mm in all: the Ø19.6 RANGE pocket
  still leaves 0.41 mm round its body (16.4 mm across corners above z 4 in Alps' STEP model, +0.3 assumed; it
  stands on a Ø13.5 foot, and the 17.2 mm base frame, 0.40 to 2.55 mm over the board, stays under the plate)
  and 0.04 mm over it (0.10 mm flat). So the floor corners of all four body pockets stay small (R0.3 at most,
  on the plate drawing; the encoder lugs and the RKJXT's corner then clear it by 0.07 and 0.04 mm), and the
  Ø11.1 RANGE hole clears its Ø7.2 hub (Alps' STEP model) at full tilt by 0.20 mm (the tilt fulcrum sits 4.65
  mm off the axis, which moves the hub 0.06 mm further out). The holes stay hidden under the knobs: seen from
  above, an outer ring covers its encoder hole by 1.2 mm even at its tapered top, printed small and off the
  hole by all of the above.
- The body holes (3.7 mm, counterbores 8.4 mm) clear the screws and washer with the MJF body up to 0.6 mm
  off over its length; at least 1.6 mm of wall stays outside each counterbore and 1.9 mm round it inside,
  1.6 mm with the counterbore and the boss both printed 0.3 mm off (JLC3DP asks for more than 1.5 mm on
  fastener features). The cavity leaves 0.5 mm per side round the PCB, so the board fits
  even with the body 0.4 % small: the milled outline (±0.2 mm) as delivered, 0.15 mm per side across the
  width with the full variant's V-cut rail edge (±0.4 mm), and V-cut short edges, should JLCPCB add rails
  there anyway, once they are sanded to 160.2 mm or less ([on arrival](#on-arrival)); the walls and the
  ribs under the floor are 2.0 mm (JLC3DP's MJF wall for parts over 100 mm).
- The USB-C opening in the back wall is 15.8 x 8.4 mm (R0.5) and runs on up through the top of the wall as a
  notch: JLC's socket (C165948) sticks out 0.52 mm past the board edge, level with the cavity wall, so a
  closed wall above the opening would catch it while the board goes in. Round a plug overmould of the USB-C
  maximum (12.35 x 6.5 mm, even with square corners) it leaves 0.06 mm with the board anywhere in the cavity
  (0.5 mm gap, and one short edge taken as V-cut, up to 0.4 mm short, although both variants mill it), the
  opening where MJF puts it over the 127.5 mm from the side wall (±0.51 mm, which also covers a body printed
  large), J1 placed 0.1 mm off, the opening's bottom ±0.3 mm against the bosses under the PCB and the
  opening printed 0.15 mm small. Under the opening the body is solid down to the desk, 0.8 mm wider than it
  on each side.
- Held only at the corners (153 mm apart), the PCB sags about 0.1 mm under a normal key press (about 1.6 N)
  in the middle, and 0.3 to 0.5 mm, as much as the switch travel, under about 5 N (a plate model of the bare
  board clamped between standoffs and bosses, see `stack.PRESS_FIRM`). Two posts at board positions
  (72.3, 30.8) and (98.6, 30.8), free of bottom parts and pins, end 0.25 mm under its underside: a firm press
  near them bends the board onto them, and a post printed 0.3 mm high (MJF) lifts the board by 0.05 mm at
  most, which the light-pipe row in check_fit.py counts.

### On arrival

Both [assembly variants](ordering.md#assembly-variants), in this order:

1. Edges. Economic variant: nothing to do. The board comes without rails, milled all round (±0.2 mm), and
   fits the body as delivered; should JLCPCB have added rails after all, one on the long edge y = 0 comes
   off as in the full variant, ones on the short edges as in the fallback below. Full variant: break the
   V-scored rail off the long edge away from J1 on both boards (pliers along the score, without bending the
   board), then file or sand that edge flush (outdoors or wet: glass-fibre dust). Measure the width with
   calipers: 60.4 mm or less (a V-cut is held to ±0.4 mm; `check_fit.py` has the row). If a corner at that
   edge comes back square, file it to R3: a square corner would stand about 0.74 mm into the body's R3.5
   cavity corner. Fallback, should JLCPCB have added rails on the short edges after all: break them off the
   same way, then sand both short edges about equally, only as much as needed, until the board is 160.2 mm
   long or shorter (the cavity is 161.0 mm long, 160.36 mm with the body printed 0.4 % small, so a V-cut
   board of 160.4 mm would not go in), and square corners to R3.
2. Board bow: the stack takes 0.1 mm of bow towards the plate at the SHIFT and UNIT LEDs, near the middle of
   the board (`stack.PCB_BOW`; JLCPCB allows 0.75 %). Economic variant, before soldering: lay each board top
   side down on glass (the top side is still bare) and press the middle of its front edge down; a 0.1 mm
   feeler gauge must not slide under any corner. J1's four shell tabs come through the board near the back
   edge (between about x 122 and 132, 1 to 7 mm in from that edge) and may stick out of the top side: if the
   board rocks on them, use the steel rule as in the full variant instead. Full variant (the top side is
   populated): stand a steel rule on edge along each long edge of the top side, over its full length, on the
   bare strip outside the parts; along the J1 edge, keep it on the outermost 1 mm, clear of J1's shell tabs.
   If the rule rocks on the middle (the board bows up, towards the plate), a 0.1 mm feeler gauge must not
   slide under either end. A board bowed more gets both LEDs seated fully flat, which gives back 0.2 mm (in
   the full variant, reheat and press down an LED that stands proud). A gap in the middle means the board bows
   away from the plate: that costs the LEDs nothing, but it lowers the keys in the middle in their key holes,
   as a firm key press does anyway (up to about 0.76 mm, on a flat board; a bowed board adds its bow): a cap
   pressed firmly there can dip under the plate back, and comes back into its hole (see [caps](#caps-light-pipes-knobs)).
3. Plate flatness (flatness 0.1 after bead blasting and anodising, as on the drawing): lay the plate face
   down on glass. If it lies on its ends, on its corners or on both long edges with a gap under the middle,
   its middle bows towards the board: a 0.1 mm feeler gauge must not slide under the middle. A plate bowed
   across its width lies on its long edges and shows that gap along its whole length, out to the knobs. That
   way the plate comes closer to the LEDs, brings the caps' sockets in the middle closer to the face and the
   pockets closer to the encoders and the RKJXT: by about a quarter of the reading there on a plate bowed
   along its length or domed, by about half on one bowed across its width (`check_fit.plate_bow`). If it
   rocks on its middle instead, it bows away from the board: rock it level, so both ends (or both long edges,
   if it rocks along its length) stand equally high, and the 0.1 mm feeler must not slide under either end
   or edge, corners included. That way the caps in the middle sit deeper in their key holes and the knobs
   have a little less room over the face. `check_fit.py` takes 0.1 mm either way, in each of these shapes.
   Past 0.1 mm the plate is outside the drawing: take it up with JLCCNC.
4. Full variant only, the work JLCPCB did on the top side (see the
   [order remark](ordering.md#full-variant-through-hole-parts-at-jlcpcb)):
   - LEDs flush on the board: a 0.2 mm feeler gauge must not slide under either LED's rim, and each
     cathode (flat side, short lead) sits on the square pad.
   - Encoders flat on the board: a 0.05 mm feeler gauge must not slide under the body of an encoder anywhere
     round it (`stack.SEAT_GAP`), and the encoder lugs are soldered. The RANGE control (RKJXT): press the
     loose one from the LCSC order fully down into the footprint of a bare board and read the gap under its
     base frame at its four gauge spots (see the RANGE control under [hand-soldering](#hand-soldering)): that
     is the reference. On each assembled board, at every spot the blade (or stack) that slid in on the
     reference must slide in and that blade plus 0.03 mm must not; in practice the same reading on all four
     sides, about 0.40 mm (Alps' STEP model). Then no spot stands 0.05 mm prouder than on a seated part
     (`stack.RKJXT_SEAT`: 0.03 mm plus up to 0.02 mm between two parts' flanges, assumed), and the pockets
     leave 0.04 mm over the RKJXT and at their floor corners. If both boards read outside the same way, read
     the loose part again in another bare board before reworking either: the reference is then more likely off
     than both soldered parts. The 28 keys sit flat and square: a tilted key tilts its cap in the key hole. A
     part that stands proud: reheat its pins while pressing it down, or use the second board for the panel.
   - Leads: no lead may stick out more than 2 mm under the board (calipers, or a ruler held across the
     bottom); the board sits only 4.0 mm over the body floor, and an uncut LED leg (about 18 mm) keeps it
     off the bosses. Cut longer ones with side cutters, then check the joint.
   - J1 shell tabs: all four slots filled from the top and wetting the tabs; if not, solder them as in
     [hand-soldering](#hand-soldering).
   - No solder bridges on the bottom, between a through-hole pin or J1 shell tab and the SMD pads next to
     it and above all between the RKJXT's COM and ECOM pins (see the RANGE control below): magnifier and
     continuity tester.
5. Cap set, both variants: try the four sets on one of the spare loose keys (two come with the economic
   LCSC set; add two to the LCSC order in the full variant), so pulling off a tight cap pulls at no
   soldered switch ([caps](#caps-light-pipes-knobs)). Without a spare, wait until the keys are on (in the
   economic variant after [bring-up](firmware.md#install-and-bring-up) step 4) and try them on a soldered
   key from loose to tight (C, B, A, D), stopping at the first that holds.

Then [bring-up](firmware.md#install-and-bring-up).

### Hand-soldering

Economic variant: the board comes with every SMD part on the bottom; the keys, encoders, RANGE control and
the two LEDs are soldered by hand from the bottom side. Flash and test the bare board first (steps 1 to 3
of [Install and bring-up](firmware.md#install-and-bring-up): the bottom side and USB need no through-hole
part), then solder the keys and LEDs and check them, and the encoders and RANGE control last: they are
the parts that are hard to remove again. In the full variant JLCPCB fits all of them and solders the J1
shell tabs; only the [arrival checks](#on-arrival) remain (flush LEDs, seating, leads, J1 tabs, no bridges), and
the notes below explain what they check.

- USB-C shell tabs: solder all four J1 shell tabs from the top before the first plug-in: flux, then feed
  solder into each slot until it is filled and wets the tab all round (they are GND). The paste Gerber
  puts paste on the shell pads (pin-in-paste), but that is about 0.12 mm³ of solder against about
  0.8 mm³ of slot, so the reflow leaves a fillet on the bottom at most. The tabs, not the 0.3 mm
  contacts, take the load of the plug.
- Every part sits flat on the board. The plate leaves little room: with the parts flat, the encoder pockets
  clear the encoder bodies by 0.25 mm and the RANGE pocket the RKJXT by 0.10 mm at worst (the plate bowed
  towards them as far as the drawing allows), less at the pocket floor corners, so an encoder may stand at
  most 0.05 mm proud (`stack.SEAT_GAP`) and the RKJXT 0.03 mm (checked against its own reading before
  soldering, see the RANGE control below): a 0.05 mm feeler gauge must not slide under an encoder body; the
  light pipes allow an LED at most 0.2 mm proud. Solder one pin, check from the side that the part sits flat
  and square (press it down while you reheat that pin if not), then solder the rest. Same for the 28 keys: a
  tilted key tilts its cap in the key hole.
- LEDs: amber XL-302UYC at SHIFT, white XL-302UWC at UNIT. The cathode (the flat side of the LED, the
  shorter leg) goes to the square pad, marked "K" in the front silkscreen. Push the LED
  flat onto the board before soldering, then cut the legs to 2 mm or less on the bottom: the board sits
  only 4.0 mm over the body floor (`check_fit.py` has the row). The same holds for every other
  through-hole lead.
- Encoders: the mounting lugs go through their slots and get soldered too; they carry the push of the
  knobs.
- RANGE control (RKJXT): no centring needed, just seat it flat. In Alps' STEP model it stands on a round Ø13.5
  mm foot, and its terminals come down inside the 17.2 mm base frame, so a feeler gauge slid in from a side
  stops at them, short of the foot. The frame stands on moulded flanges, 0.40 mm over the board in Alps'
  model, but Alps gives no tolerance on that, so the check compares the gap under the frame with the part
  pressed fully down. The flanges reach the frame edge only on a strip of each side, from about 0.5 to 3 mm
  left of its middle, seen from outside (the same on all four sides); at the middle of a side the flange is
  set back and a terminal 0.8 mm in stops the blade. These four strips are the gauge spots: slide the blade in
  square to the side, about 0.5 mm, on the strip only (with the corner of the blade or a narrow one). Before
  soldering, press the part fully down (a finger on the hub) and note at each spot the thickest blade or stack
  that slides in. After soldering, at every spot that blade must still slide in and that blade plus 0.03 mm
  must not: no spot then stands 0.03 mm prouder than on the seated part. If a spot reads outside, reheat the
  pins while pressing the part down, and read again. `check_fit.py` takes 0.05 mm (`stack.RKJXT_SEAT`), as in
  the full variant, whose reference is a loose part. The worst tilt that lets through rests the part on the
  far edge of its foot, 0.05 mm over 11.8 mm (the foot's radius plus the nearest point of the highest spot),
  and lifts the octagon's corners by up to 0.064 mm; `check_fit.py` counts both. Before soldering it can move
  up to 0.26 mm on its pins: its 0.7 x 0.2 mm terminals (Alps' STEP model) sit in holes drilled 1.1 mm, which
  JLCPCB's plating finishes at 1.02 to 1.23 mm, and its Ø1 mm locating peg (1 -0.1) in the 1.3 mm unplated
  hole of JLC's footprint (±0.2 at JLCPCB) would allow even 0.30 mm. Alps asks for 1.1 +0.1/-0 for the peg,
  but an unplated hole at ±0.2 can come out 0.9 mm, too small for the peg. So the plate gives the part the
  room instead: `check_fit.py` counts the 0.26 mm for the RANGE pocket, the hole and the skirt (see
  [Fastening](#fastening)). Its COM and ECOM pins are the closest hand-soldered pair on the board (0.38 mm of
  copper between the pads, RANGE_COM and GND): check them for a bridge with a magnifier and a continuity
  tester. A bridge makes the whole fifth column read pressed.

### Assembly and gluing

The first assembly glues the standoffs in, with the assembled board as the jig: the standoffs go onto the
board first, and the caps line the board up in the plate. Two glues:

- Standoffs: a thixotropic (non-sag, paste) two-part epoxy that fills gaps and does not run, with at
  least 30 minutes of working time, for example Araldite 2014-1 (grey paste, about 40 to 60 minutes pot
  life). Not a runny clear epoxy and not 5-minute epoxy: the gap between the hex and the 7 mm pocket is 0.6
  to 1.0 mm, which a thin coat does not bridge, and runny glue slumps onto the pocket floor, under the
  standoff end and into its thread.
- Light pipes: a clear epoxy, or UV glue with a small UV lamp (not CA glue, it fogs clear resin).

The encoder shafts stick out 18 mm past the plate face, so the plate rests face down on two blocks (books,
wood) at least 25 mm high under its long front and back edges, at most 8 mm in from the edge (the nearest
caps and shafts are about 10 mm in), with a cloth on top.

1. Push all caps of the chosen set onto their plungers (see [caps](#caps-light-pipes-knobs)), tactile
   bars as in the 3D view, down until each one sits on its plunger top. Then square them: hold a steel
   rule against the front edges of each row of caps and turn every cap until its edge lies flat on the
   rule. A cap turned by more than about 1° can rub its hole; one turned by more than about 5° lands on
   the plate back instead of in its hole.
2. Light pipes, while the plate face is still bare: lay a release film (a piece of PE bag or baking paper)
   on the glass and the plate face down on it, no blocks yet. Drop each light pipe into its hole from the
   back: it rests on the film, its top flush with the face, and its bottom end then sits 0.4 mm inside the
   hole, under the back face. Put a small drop of clear epoxy (or UV glue, then cure it with the UV lamp
   from the back) at the back mouth of the gap round the pipe, nothing proud of the back face, where it
   would sit over the LED. Don't let it wick through: the gap is only 0.15 mm, and glue that reaches the
   face spreads between the film and the bead-blasted face round the hole. Let it cure without moving the
   plate, peel the film off, and lay the plate face down on the blocks and the cloth.
3. Standoffs: roughen their hex sides with fine sandpaper and wipe them with alcohol. Press a little soft
   wax or plasticine (Blu Tack works) into the thread at the plate end of each one with a toothpick marked
   at 2 mm, no deeper than the mark, and scrape the end face clean (keep wax off the sides): it keeps the
   glue out of the thread. A grub screw is no good here: the shortest common M2.5 one (3 mm) can meet the
   screw tip.
4. Board: rest the body on two more blocks or books (the plate keeps the first two), under its long edges
   but clear of the four corners: the counterbores are in the bottom face, up to about 10 mm deep at the
   back. Set the PCB in and put the four screws with their washers in from below. Thread each standoff,
   plugged end up, onto its screw by hand until it seats on the PCB, then hold the standoff (fingers or a 5
   mm nut driver) while you turn the screw back a quarter turn, so the standoff stays put and can still
   slide a little with its screw in the PCB hole. On their screws the standoffs cannot tip over. Dry run:
   lay a strip of release film on the plate back at each corner, from the plate edge up to the standoff
   pocket but not over it, where the top of the body wall will land. Lower the unit face down into the
   plate as in step 6, without glue, and note at each corner which feeler gauge or drill shank (about
   0.8 mm) just slides into the gap between the top of the body wall and the film. Look at the face
   between the blocks: every cap must stand up through its hole; one that sits on the plate back was
   turned, so square it again. Lift the unit out again.
5. Wipe the pockets with alcohol and keep their floors dry. Mix the epoxy and butter the six sides of each
   standoff over the 2 mm that go into the pocket: about 35 mm³ per standoff, which is the gap round the
   hex, so a bead of about 4 mm, less rather than more. Keep the last 0.5 mm at the end and the end face
   bare. The pocket mouth comes to within about 0.5 mm of the body wall, whose top is only 0.95 mm under
   the plate back: excess that bulges out there could glue the body to the plate, which is why the film
   lies there.
6. Turn the unit over and lower it face down into the plate: the caps drop into their key holes and
   centre the board, the standoffs into their pockets. Let it settle: the weight of board and body seats
   each standoff end on its bare pocket floor and squares it between floor and PCB. Check that the unit
   moves a little in every direction (nothing jammed) and leave it in the middle. Then check each corner
   with the gauge from the dry run: it must slide into the gap as before. A corner where the gap is
   clearly wider has its standoff on glue instead of the pocket floor: press that corner down gently
   until the gap matches. Look for squeeze-out at each corner: epoxy that reaches the wall top or the
   film is scraped off with a toothpick now, before it cures. Look at the face again: every cap stands up
   through its hole.
7. Leave it face down and untouched until the epoxy has cured fully (usually 24 hours). Then pull the film
   strips out from between the wall tops and the plate.
8. Tighten the screws gently (small screwdriver, two fingers); the standoffs are fixed now. Turn the
   panel over and fit the knobs: outer knob key into the shaft slot, pushed down until the key sits on the
   slot floor, inner knob onto the D flat until its bore end sits on the shaft tip, and the RANGE knob
   onto the lever's D flat until its bore end sits on the lever tip.
9. Feet: stick the four self-adhesive feet onto the flat pads under the corners. With the steel plate,
   tape it into its recess first (notches at the back corners, round the back feet); the feet go on the
   same pads either way.

### Disassembly

1. Pull the knobs off (inner first). Lay the panel face down on the blocks.
2. Undo the four screws and lift off the body.
3. Lift the PCB out; caps that stay in their key holes come out from the front. The standoffs stay glued in
   the plate.
4. To reassemble, push any cap that came out back onto its plunger and square the rows again (step 1),
   set the PCB and body back on (as in step 6, without glue, checking that every cap stands up through its
   hole) and do step 8: the screws find the standoffs again.

A standoff that has to come out: first try it cold with a 5 mm nut driver; a hex in a round pocket often
breaks loose. Heat is the last resort: epoxy softens at about 100 °C, but the front face is only 1.9 mm
away and its UV print does not take much heat. Then lay the plate face down on a damp cloth, heat the
standoff with the soldering iron in short bursts and turn it out; scrape the old epoxy out of the pocket
before gluing a new one in as above.

### Caps, light pipes, knobs

- Key caps: the switch plunger (TE's own STEP model of the 1-1825910-4) has a flat top of 1.26 mm radius with
  a 0.3 mm edge radius and then tapers about 2° per side, from 3.12 mm just under the top to 3.51 mm at the
  switch body; over the 2.7 mm deep cap socket it is 3.12 to 3.29 mm. The socket is a 3.8 mm bore (1.3 mm of
  wall at the narrow cap sides, 1.05 mm on a print with the outline 0.2 mm small and the bore 0.3 mm large,
  nothing open to the outside) with four rigid ribs 1.2 mm wide along its wall, attached over their whole
  length, that follow the plunger's cone: they touch it over 2.04 mm, so a cap that grips cannot rock. They
  stop 0.35 mm under the socket ceiling, clear of the plunger's rounded edge, so the flat ceiling sits on the
  plunger top: the plunger, not the fit, sets the cap height (2.5 mm proud), and the socket ends 0.1 mm or
  more under the plate face (0.01 mm with the plate bowed 0.1 mm towards the board; the socket stays inside
  the cap either way, so that limit is cosmetic). A firm press (10 N, about six times the switch force) bends
  the board under the key by up to about 0.76 mm (the front and back rows are 18 mm from the body posts, which
  do not stop them), and with the plate bowed up the cap can dip up to 0.79 mm under the plate back (a little
  more on a board bowed away from the plate; the 0.1 mm edge break still leads it back in). The bent board
  tilts the cap with its plunger by up to about 0.87°, which moves it up to 0.18 mm sideways at the
  plate face. A cap at the edge of its per-key allowance has less room than that (0.07 mm, 0.01 mm turned 1°),
  so on a firm press it may lightly rub the face edge of its hole on one side. It cannot catch or stick:
  tilted, turned 1° and printed 0.2 mm large, it still leaves 0.21 mm across its hole, so it never touches
  both sides at once, and the touch comes with the press and goes with it. While its side bears on the face
  edge, its bottom edge is pulled inside the hole; while its side is free, its bottom edge stands only 0.01 mm
  out of the line of its side, and the back edges of the key holes are broken 0.1 to 0.2 mm (on the drawing)
  to lead it back in. The worst case is a scuff on that side of the cap, in the band up to about 1.1 mm above
  the face at rest (`check_fit.py` has both rows). A 0.3 mm lead-in at the mouth starts the cap straight. The
  ribs, wall and holes meet the full-colour (WJP) minimums of 1.0 mm.
- Cap sets: a rigid friction fit wants about 0.02 to 0.15 mm of interference on the diameter (holds from
  0.02; up to 0.15 the narrow ribs still give enough to push the cap down by hand), but JLC3DP's resin
  holes vary by about ±0.2 to 0.3 mm (±0.1 to 0.2 mm on their WJP page). So the order has four full sets
  of 28 caps that differ only in the rib circle, 3.05 (set D), 3.15 (A), 3.25 (B) and 3.35 mm (C) at the
  socket mouth, where the plunger is 3.29 mm (0.16 mm less at the top of the ribs, along the cone). On a
  true print D grips with 0.24 mm (too tight), A with 0.14 mm, B with 0.04 mm and C is 0.06 mm loose; D
  fits a print whose rib circle comes out 0.09 to 0.22 mm large, A 0.01 mm small to 0.12 mm large, B
  0.11 mm small to 0.02 mm large, C 0.21 to 0.08 mm small: together they cover a print 0.21 mm small to
  0.22 mm large. The set is marked on the cap underside, inside the key hole where it never shows: one
  dimple for A, two for B, three for C, four for D (1.0 mm across, 0.9 mm deep, in the corners between
  the socket and the outline).
- Choosing the set: try one cap of each set on a spare loose key (no tools; [on arrival](#on-arrival)),
  so pulling off a tight cap loads no soldered switch. The right set pushes down by hand until the cap
  sits on the plunger top (it stops hard there; on the board its top is then level with its neighbours),
  holds when the key is turned over and does not wobble. One of the four sets fits. If two sets fit, take
  the tighter one (from tight to loose: D, A, B, C). Too tight means the cap stops short of the plunger top
  or needs more than a firm thumb; too loose means it falls off or rocks. Without a spare key, try them on a soldered
  key from loose to tight (C, B, A, D) and stop at the first set that holds, so no tight cap has to be
  pulled off. Fit all 28 caps of that set and keep the other three as spares. If even C is too tight, or
  even D too loose, reprint with `stack.CAP_SETS` moved by 0.1 mm.
- Legends: Barlow Semi Condensed Bold, grown all round by 0.055 mm, so every coloured stroke (including
  the D→ arrow and the flip-flop icon) is at least 0.4 mm wide, JLC3DP's minimum for full-colour lines;
  check_fit.py measures it on the generated texture. The tactile bars on SHIFT, UP and DN are 1.0 mm wide
  but only 0.5 mm proud, under JLC3DP's 0.8 mm for embossed detail: a taller front bar would hide the bottom
  of the SHIFT and DN legends from the seat (check_fit.py checks the sightline at 45°).
- Light pipes are plain rods 0.3 mm under their holes on the diameter (the holes are +0.1/-0 on the drawing,
  anodising takes about 0.05 mm off them, and the resin may print 0.2 mm off), glued in flush with the face.
  Under the 4 mm plate only 0.7 mm is left above the LEDs, too little for a collar that keeps a loose pipe
  captive without ever touching the plate. Glued, the 3.6 mm pipe's bottom stays at least 0.25 mm over an LED
  soldered 0.2 mm proud (LED top 5.3 +0.3/-0.1 mm, pipe ±0.1, plate ±0.1, standoff gap -0.1, the board lifted
  0.05 mm by a support post and bowed 0.1 mm towards the plate, the plate 0.1 mm towards the board), so the
  board never pushes on it. The LEDs sit near the middle of the long span between the corner screws, so the
  flatness of both counts: JLCPCB allows 0.75 % bow (over 1 mm on this board), the stack takes 0.1 mm; the
  plate drawing asks for flatness 0.1 mm after bead blasting and anodising (blasting can bow a thin plate; ISO
  2768-K alone would allow 0.4 mm over the plate's length); and the LED itself then clears the plate back by
  0.025 mm (over bare pocket floors, see [Fastening](#fastening)). Check the board on arrival (see [On
  arrival](#on-arrival)); a board bowed more gets its LEDs seated flat, which gives back the 0.2 mm a proud
  LED is allowed. Both pipes print on a 2.2 x 2.0 mm bar over their tops, on 1.1 mm necks: break them off,
  sand the stub off with the top and polish it before gluing. The order has two bars, one spare.
- The rods (Ø1.5 and Ø1.3 mm, 3.6 mm long) are longer than JLC3DP's guideline for resin pillars (Ø1.0 mm
  up to 1 mm tall, Ø2.0 mm up to 4 mm), so they may be flagged in the review or break. Fallback: PMMA
  end-glow optical fibre, Ø1.5 mm for SHIFT and Ø1.0 to 1.25 mm for UNIT, cut to 3.6 mm with a fresh
  blade, both ends sanded flat and polished, glued in the same way.
- Knob bores are drawn at the datasheet shaft size (`stack.FIT` = 0): the shafts are toleranced +0/-0.05
  and +0/-0.1 mm, which leaves 0 to 0.1 mm real clearance on a true print, but JLC3DP's resin holes vary by
  about ±0.3 mm. The knobs are held by friction only, so one outer ring, one FMS ring, one inner and the
  RANGE knob also come with a bore 0.2 mm tighter and 0.2 mm looser (`stack.FIT_VARIANTS`). Try those
  first and keep the one that grips. A bore that is still too tight opens with a drill of the shaft size by
  hand (6.0 mm outer, 3.5 mm inner, 2.5 mm RANGE), then a needle file on the D flat; in the outer knob
  drill from below only up to the key (4.41 mm deep) and file the rest, or the drill takes the key off.
  Never drill past the existing bore depth (mark the drill with tape at it): the inner and the RANGE knob
  sit with their bore end on the shaft or lever tip, so a deeper bore lowers the knob, and the RANGE skirt
  has only 0.12 mm over the plate at full tilt. A loose one holds with a strip of tape on the shaft.
  Reprint the rest with that `FIT` if needed.
- The knobs stand 19.9 mm above the plate (29.9 above the PCB), set by the uncut PEC11D shafts. The outer knob
  rests with its key (1.4 mm wide, 0.7 mm into the slot past the shaft surface, 0.5 mm with a small shaft and
  the print) on the floor of the shaft slot. The key stays clear of the inner shaft that runs through the slot
  even on a loose knob pushed towards it, clears even the narrowest slot (2.0 ±0.3) when it prints 0.2 mm wide
  (so it stays under the 1.5 mm JLC3DP asks for on positioning features), and sets the knob height: 1.09 mm
  over the plate, 0.02 mm left with the PEC11D's tolerances (±0.3 under 10 mm, ±0.5 from 10 mm, RSS), the
  highest plate face (standoffs, pocket depth, plate thickness, anodising and a bow away from the board, 0.045
  mm there) and the rim 0.011 mm lower on an encoder tilted as far as its seating check allows (the rim
  reaches 2.65 mm past the edge of the body it tilts on). The knob grips 4.1 mm of the 6 mm shaft above the
  bushing (3.7 mm with a shallow slot); its counterbore clears the bushing by 0.9 mm (0.03 mm left with the
  tolerances). The inner knob grips 6.3 mm of the 7 mm D flat (7.0 ±0.3), so its bore end, not the round shaft
  under a short flat, sits on the shaft tip, and it clears the outer one by 1.0 mm when pushed (0.22 mm with
  the shaft and print tolerances).
- Garmin proportions: all three outer rings are Ø17, the inner knobs Ø12, so 2.5 mm of ring shows each
  side. The outer ring ends flush with the 6 mm shaft top: a neck rising into the inner knob would need a
  recess round it that leaves less than JLC3DP's 1.0 mm resin minimum in a Ø12 knob once a loose knob,
  the print tolerances (±0.2 mm outside, ±0.3 mm on holes) and the shafts' play are counted. The inner
  knob's Ø8.0 recess only has to clear the 6 mm shaft top when the shaft tolerances lift it: 1.0 mm
  radially, 0.5 mm with a loose knob (0.3 mm off centre), a small hole and 0.05 mm between the shafts.
  The walls, at their thinnest print: 1.4 mm round the recess at the bottom of the inner knob's flutes,
  3.2 mm (FMS 2.8 mm) round the Ø8.8 counterbore over the bushing, which still clears it by 0.3 mm
  radially. Every wall and clearance here is a `check_fit.py` row.
- FREQ and FMS sit one above the other with the same size, so the FMS ring has a different grip: 14 flutes
  0.9 mm deep instead of 24 at 0.45 mm. It reads as the same fluted ring from a distance, but the
  fingers find the coarser ridges at once. At the knob top, where the taper makes them narrowest, the
  grooves are 1.7 mm wide at half depth on the FMS ring, 1.0 mm on the other rings and 0.86 mm on the
  inner knobs (20 flutes, still a finer knurl than the rings'), all over the 0.8 mm resin detail.
- `mech/check_fit.py` draws sections through the ALT/HDG knob, the RANGE knob and the SHIFT light pipe and
  checks every clearance, including the RANGE skirt at full 9° tilt about the datasheet fulcrum (5.55 mm over
  the PCB, 4.65 mm off the axis on the side the lever tilts to): at least 0.12 mm over the plate with the knob
  low, the plate face high and bowed up, and the RKJXT tilted on its seat (taken with the fulcrum on the axis,
  which lets the skirt dip further). The Ø16.6 skirt (Ø16.4 on a small print) still covers the 11.1 mm hole
  (11.3 at ISO 2768-m) at full tilt with the lever 0.88 mm off the hole (board, plate, PCB and the RKJXT on
  its pins) and a loose knob 0.3 mm off the lever, by 0.03 mm (the highest knob, its rim at cos 9°, moved 0.06
  mm by the fulcrum's offset, on an RKJXT lifted and tilted as far as its seating check allows). The four pan
  arrows start at r 9.65 mm round the hole centre, 0.02 mm outside that skirt seen square on (Ø16.8 on a large
  print, with the same offsets and the tilted RKJXT, upright); from the seat the skirt 2.3 mm over the plate
  hides a little more. Its rim is 1.1 mm thick (1.0 mm on a thin print).
- BOOT: two bridge pads on the underside of the PCB under a 5 mm hole in the case floor. Bridge them
  with a small screwdriver while plugging in USB. Recovery only: normal updates enter the bootloader
  from software.
- Four self-adhesive feet up to 10 mm across, on the four flat 12 mm pads under the corners (with or without
  the steel plate). The aluminium plate adds about 83 g; the printed body is hollow under its 2 mm floor
  (about 38 cm³, 2 mm ribs down to the desk plane, no slot under 0.8 mm; the two back foot pads are joined
  to the screw bosses). The panel may still slide when knobs are turned one-handed, so a recess in the
  bottom takes an optional 2 mm steel plate, 143 x 36 mm with two 15 x 15 mm notches at the back corners for
  the feet (about 74 g), held with double-sided tape on the rib ends; `steel.dxf` has its outline for a
  laser-cutting service. The 144 x 37 mm recess leaves 0.5 mm round it (0.16 mm with the body 0.4 % small
  and the plate cut 0.1 mm large), with the same notches. The recess stays in the hollow under the floor and
  leaves a 2.1 mm rim at the back, so no wall round it is thinner than JLC3DP's 2.0 mm for MJF parts over
  100 mm.

## Dimensions

| Item | Value |
| --- | --- |
| PCB | 160 × 60 mm, 4 layers, every SMD part on the bottom (see `pcb/board.py`) |
| Case | about 165 × 65 mm, 17 mm high at the front, 24 mm at the back (6° wedge). Chosen for a flat desk in front of the pilot; a steeper angle (12°) only pays off when the panel sits further away or lower |
| Key pitch | 11.85 mm horizontal (17.1 mm between AUTOPILOT and AUDIO), 11 mm vertical; 14.5 mm between rows 2 and 3 for the FMS line. Rows stay aligned across the panel on purpose, so the autopilot block shares that gap |
| Caps | 9.6 × 6.4 mm, 2.5 mm proud, one legend size (about 2.0 mm cap height, Barlow Semi Condensed Bold, strokes at least 0.4 mm), condensed face; the flip-flop icon is narrow so COM ⇆ does not shrink every legend |
| Dual knob centres | x 15 and 145, y 15 and 45 (30 mm apart; gap 13.2 mm left to the RANGE skirt, 13 mm right) |
| Knobs | avionics style: matte black resin, fine vertical flutes, slight taper, chamfered flat top, no index line. Outer ring Ø17 × 6.91 mm on all three (FMS with a coarser grip), inner knob Ø12 × 10.4 mm above it: 19.9 mm above the plate. RANGE Ø13.6 with a Ø16.6 skirt |
| SHIFT light | Ø1.5 mm light pipe in a Ø1.8 mm hole below the SHIFT cap, amber LED on the PCB |
| UNIT 2 light | Ø1.3 mm light pipe in a Ø1.6 mm hole right of the UNIT legend, white LED on the PCB |
| Amber | #d9a441 (RGB 217, 164, 65; nearest Pantone 7563 C, roughly RAL 1004): SHIFT cap legend, UV print on the plate, 3D view. JLCCNC is asked to match it, with its standard orange as the fallback; the caps and the 3D view follow what the plate gets (`stack.AMBER`, [Ordering](ordering.md#suppliers)) |
