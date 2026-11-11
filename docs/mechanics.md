# Mechanics

Body, front plate, knobs, light pipes and key caps. Every height and fit is in
[mech/stack.py](../mech/stack.py); [mech/check_fit.py](../mech/check_fit.py) checks the clearances.

## Stack and assembly

Stack (z = 0 is the PCB top). The plate's bosses set its back 6.0 to 6.1 mm over the PCB, 6.05 nominal; the
stack is drawn with the back at 6.0 and the face at 10.0, and `check_fit.py` takes the bosses' +0.1 in every row:

| z (mm) | Part |
| --- | --- |
| -7.6 to -5.6 | body floor, 2 mm (1.6 at the front edge); below it the 6° wedge is hollow down to the desk plane (-7.2 at the front, about -14 at the back), with 2 mm ribs, a solid band along the front, four foot pads and a recess for an optional steel plate |
| -5.6 to -1.6 | 4 bosses (Ø8 on the PCB, joined to the corner walls) carry the PCB corners; 2 posts under the middle (between the key blocks) end 0.25 mm under the PCB |
| -3.2 | counterbore seats (Ø8.4, 1.9 mm wall), 1.6 mm of PA12 up to the PCB: the flanged button heads below them stay recessed |
| -1.6 to 0 | PCB; the two LEDs on its underside shine up through 2.2 x 2.4 mm cutouts in it |
| 0 to 6 | the plate's 4 bosses (Ø5.5, tapped M3) stand on the PCB: they alone set the plate height, 6.05 ±0.05 mm over the PCB to the plate back (anodising: see [Fastening](#fastening)); the body walls end at 5.35. The two light pipes stand on the board, their shoulders under the plate back. Encoder bodies 8 mm (±0.3), RANGE body 8.6 mm, key switch bodies 3.6 mm |
| 1.0 to 4.85 | USB-C filler in the back wall's notch, on the two ledges beside the plug opening (face up) |
| 6 to 10 | 4 mm (±0.1 before anodising) aluminium web of the plate, milled with its bosses from 12 mm stock; pockets 2.8 mm (encoders, at least 1.1 mm left) and 3.25 mm (RANGE, at least 0.65 mm left) deep from below, +0/-0.1 |
| 6.8 to 12.5 | key caps, socket ceiling on the plunger top (9.5), 2.5 mm proud |
| 11.09 to 18 | outer knob ring |
| 19.5 to 29.9 | inner knob, sitting on the 28 mm tip of the inner shaft |

### Fastening

- Four M3 x 8 flanged button-head screws (ISO 7380-2, 2 mm hex key; flange 6.32 to 7.0 mm across, head
  1.65 mm high) come from below and hold everything: body boss, PCB, plate boss. No washers; nothing shows
  on the front. The flange bears on the floor of the 8.4 mm counterbore
  round the 4.2 mm body hole: with the screw against the hole wall (0.82 mm off) the smallest flange still
  covers the hole all round by 0.09 mm. The counterbore wall stops the largest flange 0.55 mm off centre,
  before the shank reaches the hole wall, so the floor corner of the counterbore stays sharp (MJF's own
  rounding, 0.2 mm or less assumed): the flange rim (at least 0.55 mm high) then meets the foot of the wall,
  not a slope under the flange.
- The plate is milled from 12 mm 6061 stock: the 4 mm web and four Ø5.5 mm bosses on its back at the corner
  mounts, 6.05 ±0.05 mm high, each tapped M3-6H from its end face (full thread at least 6.0 mm deep, drilled
  7.5 mm plus the drill point). The screw pulls the plate boss against the PCB and the PCB against the body
  boss: the bosses alone set the plate height, and the threads take the screws' preload, about a tenth of
  what 2.75 mm of thread in 6061 holds.
- Screw length: from the counterbore seat to the PCB top is 3.2 mm (±0.3 MJF, ±0.16 PCB), so the tip of an
  M3 x 8 (±0.29) ends 4.05 to 5.55 mm into the boss. Less the incomplete end of the screw (2 pitches) and the
  0.3 mm countersink at the mouth, at least 2.75 mm (5.5 turns) of full thread engage, and the tip stays
  0.45 mm short of the end of the full thread. An M3 x 6 would engage under 1 mm, an M3 x 10 would reach the
  drill point. The drill point stays at least 1.65 mm behind the front face (thin plate, low boss).
- Anodising grows every surface by up to about 0.025 mm, which would take about 0.1 mm off a thread's pitch
  diameter, more than the 6H band: the drawing asks for the threads masked while anodising or cut again
  afterwards. It lets the boss end faces be anodised or bare (masking may leave them bare), all four alike.
  Over bare ends the back face sits up to 0.025 mm lower; on anodised ends the whole plate stands 0.025 mm
  higher and its front face grows as much, so the highest front face is 6.1 + 4.1 + 0.05 = 10.25 mm over the
  PCB (4.0 ±0.1 mm before anodising). `check_fit.py` takes the worse case in every row.
- The boss height centres the plate: 6.0 to 6.1 mm puts it 0.05 mm higher than the 6.0 the stack is drawn at,
  between the rows that want it low (the outer knobs keep 0.12 mm over the face, the RANGE skirt 0.22 mm) and
  those that want it high (0.10 mm over the RKJXT and at the RANGE pocket's floor corner, the cap sockets 0.11
  mm under the face, the encoder pockets 0.26 mm over the bodies, the USB-C filler 0.16 mm, the body walls
  0.08 mm). At JLCCNC's default ±0.1 mm instead every one still passes with 0.05 mm less on one side (the
  walls with 0.03 mm). The pocket rows also take the board bowed 0.1 mm towards the plate in the middle
  (`stack.PCB_BOW`, JLCPCB allows more, a 4-layer board is usually far flatter), about 0.045 mm at the knobs.
  The drawing asks for flatness 0.1 mm; every row still passes up to about 0.17 mm (the light pipes' room over
  their bases goes first, then the body walls).
- Positions: the key caps centre the board in the 10.2 x 7.0 mm key holes (+0.1/-0 after anodising, so at
  least 0.3 mm per side, against about 0.23 mm of per-key errors, RSS), and in holes at +0.1 it can still
  sit up to about 0.44 mm off. A cap can turn on its round plunger, and a turned cap has less room: at 1°
  about 0.24 mm, just over the per-key errors, and past about 5° it no longer goes into its hole at all. So
  each row of caps is squared against a steel rule before the plate goes on (assembly step 1);
  `check_fit.py` takes the room at 1°. The plate's bosses fix the screws, and the board floats on them: its
  3.8 mm holes (3.6 to 4.0 with JLCPCB's ±0.2) pass the M3 wherever the caps put the board (that takes 0.255
  mm: the bosses and key holes on the plate, the board's holes, centring, the thread's play; the holes leave
  0.30 mm), the boss end (Ø5.5 ±0.1) still covers the widest hole all round by 0.10 mm with the board 0.6 mm
  off a screw, and it stays 0.2 mm inside the 3.6 mm copper keep-out ([pcb/check.py](../pcb/check.py) checks
  the copper on the Gerbers).
- The same board offset (plus the plate, PCB and pin tolerances, about 0.77 mm radially) moves the controls in
  their plate openings. Every opening here is at ISO 2768-m (±0.2) and loses about 0.05 mm to the anodising,
  which `check_fit.py` counts. It also takes the encoders and the RKJXT seated as far as their checks allow
  (see [on arrival](#on-arrival)): an encoder 0.05 mm proud (`stack.SEAT_GAP`), which lifts its lugs 0.05 mm,
  or tilted by that over the body, which moves its bushing up to 0.04 mm sideways at the plate face; the RKJXT
  with no gauge spot under its base frame 0.05 mm higher than on a seated part (`stack.RKJXT_SEAT`), which
  tilts it by up to 0.05 mm over 11.8 mm (see the RANGE control under [hand-soldering](#hand-soldering)) and
  lifts the corners of its octagon up to 0.064 mm. And it takes the plate bowed towards the board as far as
  the drawing's flatness 0.1 mm allows, up to about half of that near the knobs on a plate bowed across its
  width. The Ø9.3 encoder holes still leave 0.06 mm round the bushings (7.0 +0.3; 0.11 mm with the encoder
  flat), and the 15.6 x 20 encoder pockets 0.07 mm beside the side lugs (13.1 ±0.5 across, the PEC11D
  drawing) and 0.26 mm over the bodies. The RKJXT floats more on its pins (0.26 mm instead of 0.15, see
  [hand-soldering](#hand-soldering)), 0.88 mm in all: the Ø19.6 RANGE pocket still leaves 0.41 mm round its
  body (16.4 mm across corners above z 4 in Alps' STEP model, +0.3 assumed; it stands on a Ø13.5 foot, and
  the 17.2 mm base frame, 0.40 to 2.55 mm over the board, stays under the plate) and 0.10 mm over it. So the
  floor corners of all four body pockets stay small (R0.3 at most, on the plate drawing; the encoder lugs
  and the RKJXT's corner then clear it by 0.07 and 0.10 mm), and the Ø11.1 RANGE hole clears its Ø7.2 hub
  (Alps' STEP model) at full tilt by 0.20 mm (the tilt fulcrum sits 4.65 mm off the axis, which moves the hub
  0.06 mm further out). The holes stay hidden under the knobs: seen from above, an outer ring covers its
  encoder hole by 1.2 mm even at its tapered top, printed small and off the hole by all of the above.
- The body holes (4.2 mm, counterbores 8.4 mm) pass the screws where the plate's bosses put them, with the
  MJF body up to 0.33 mm off over its length and the bosses 0.1 mm (0.02 mm to spare); at least 1.6 mm of
  wall stays outside each counterbore and 1.9 mm round it inside, 1.6 mm with the counterbore and the boss
  both printed 0.3 mm off (JLC3DP asks for more than 1.5 mm on fastener features). The cavity leaves 0.5 mm
  per side round the PCB, so the board fits even with the body 0.4 % small: the milled outline (±0.2 mm) as
  delivered, 0.15 mm per side across the width with the full variant's V-cut rail edge (±0.4 mm), and V-cut
  short edges, should JLCPCB add rails there anyway, once they are sanded to 160.2 mm or less ([on
  arrival](#on-arrival)); the walls and the ribs under the floor are 2.0 mm (JLC3DP's MJF wall for parts over
  100 mm).
- The body walls end 0.65 mm under the plate back, the smallest gap that never closes: MJF ±0.3 mm on the
  wall height over the boss tops under the PCB, a board 0.16 mm thin, the plate back 0.025 mm low over bare
  boss ends and bowed 0.086 mm down at the middle of a long wall, and the bosses at their lowest leave 0.08
  mm at the drawing's ±0.05 and 0.03 mm at JLCCNC's default ±0.1. Walls that reached the plate would take the
  screws' clamp off the board.
- The USB-C opening in the back wall is 15.8 x 8.4 mm (R0.5 at the bottom, square at the top) and runs on up
  through the top of the wall as a notch 20.8 mm wide: JLC's socket (C165948) sticks out 0.52 mm past the
  board edge, level with the cavity wall, so a closed wall above the opening would catch it while the board
  goes in. Round a plug overmould of the USB-C maximum (12.35 x 6.5 mm, even with square corners), its top
  being the filler below, it leaves 0.06 mm with the board anywhere in the cavity
  (0.5 mm gap, and one short edge taken as V-cut, up to 0.4 mm short, although both variants mill it), the
  opening where MJF puts it over the 127.5 mm from the side wall (±0.51 mm, which also covers a body printed
  large), J1 placed 0.1 mm off, the opening's bottom ±0.3 mm against the bosses under the PCB and the
  opening printed 0.15 mm small. Under the opening the body is solid down to the desk, 0.8 mm wider than it
  on each side.
- Once the body is on, a filler block (`usb-filler.step`, printed with the body, 19.7 x 2.0 x 3.85 mm)
  closes the notch above the opening from the back, flush with the wall, so only the plug opening shows.
  The notch is 2.5 mm wider than the opening on each side, and the wall under it ends in two flat ledges
  level with the opening's top. With the panel face up the filler rests on them: its bottom is the
  opening's top edge, 1.0 mm over the PCB and held by the body like the rest of the opening (the overmould
  above), and as it spans the opening it cannot drop into the plug's path. Pushed against one side of the
  notch it still rests 0.8 mm on the far ledge. Its top stays 0.5 mm under the wall top, and under the plate
  back even on the highest ledges (body printed high, thin board, plate back at its lowest and bowed
  0.05 mm down there). Face down it may slide onto the plate back, up to about 2.3 mm higher, which only
  opens the plug's path further. Nothing in the wall can stop it moving inward: a lip wider than the notch
  does not go in from outside, and a step in the notch would leave body walls under JLC3DP's 2.0 mm. On
  the desk the 6° tilt pulls it inward with about a tenth of its weight, which friction on the ledges
  holds (PA12 on PA12, 0.2 or more assumed), and a dab of removable adhesive putty (Blu Tack) on each side
  face holds it on top of that: the notch leaves 0.25 to 0.85 mm per side round it (both parts ±0.3 mm),
  room for the putty either way. Not glue: lifting the body may take the filler with it, and it has to
  come out of the notch before the body goes back on the board, where it would stop the socket on the way
  in; and press-fit ribs cannot hold over MJF's ±0.3 mm on both the notch and the filler. Pushed flush, it
  reaches at most 0.6 mm past the cavity wall, over the board edge but at least 0.39 mm above it, and
  stays short of J1's shell tabs (their pads start 1.2 mm in from the board edge; their tips and solder
  fillets may stand higher than the filler's bottom, so only that distance keeps them apart).
- The plate's bosses stand 4.0 mm from the cavity walls. On its screw the body stays within 0.82 mm of each
  boss's axis (4.2 mm hole, its radius up to 0.15 mm large, the M3 at its smallest), and MJF puts the hole
  within 0.3 mm of its 4.0 mm from the walls, so a boss (Ø5.5 +0.1) still clears the wall by 0.08 mm at the
  end of that play, and the four fit between the walls at once with 0.78 mm per side.
- Held only at the corners (153 mm apart), the PCB sags about 0.1 mm under a normal key press (about 1.6 N)
  in the middle, and 0.3 to 0.5 mm, as much as the switch travel, under about 5 N (a plate model of the bare
  board clamped between the plate's and the body's bosses, see `stack.PRESS_FIRM`). Two posts at board
  positions (72.3, 30.8) and (98.6, 30.8), free of bottom parts and pins, end 0.25 mm under its underside: a
  firm press near them bends the board onto them, and a post printed 0.3 mm high (MJF) lifts the board by
  0.05 mm at most, which the light-pipe rows in check_fit.py count.

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
2. Plate threads: turn one of the M3 screws into each boss by hand with the 2 mm hex key, about ten turns
   (5 mm), until about 3 mm of shank still shows, and out again. It must run freely: an anodised thread that
   was neither masked nor cut again stops it early (take it up with JLCCNC; the drawing asks for M3-6H after
   anodising). Don't drive it home: the hole's full thread ends 6.0 mm in, while an 8 mm screw seated without
   the body would go 8 mm deep; in the panel its tip reaches 5.55 mm at most.
3. Full variant only, the work JLCPCB did on the top side (see the
   [order remark](ordering.md#full-variant-through-hole-parts-at-jlcpcb)):
   - Encoders flat on the board: a 0.05 mm feeler gauge must not slide under the body of an encoder anywhere
     round it (`stack.SEAT_GAP`), and the encoder lugs are soldered. The RANGE control (RKJXT): press the
     loose one from the LCSC order fully down into the footprint of a bare board and read the gap under its
     base frame at its four gauge spots (see the RANGE control under [hand-soldering](#hand-soldering)): that
     is the reference. On each assembled board, at every spot the blade (or stack) that slid in on the
     reference must slide in and that blade plus 0.03 mm must not; in practice the same reading on all four
     sides, about 0.40 mm (Alps' STEP model). Then no spot stands 0.05 mm prouder than on a seated part
     (`stack.RKJXT_SEAT`: 0.03 mm plus up to 0.02 mm between two parts' flanges, assumed), and the pockets
     leave 0.10 mm over the RKJXT and at their floor corners. If both boards read outside the same way, read
     the loose part again in another bare board before reworking either: the reference is then more likely off
     than both soldered parts. The 28 keys sit flat and square: a tilted key tilts its cap in the key hole. A
     part that stands proud: reheat its pins while pressing it down, or use the second board for the panel.
   - Leads: no lead may stick out more than 2 mm under the board (calipers, or a ruler held across the
     bottom); the board sits only 4.0 mm over the body floor. Cut longer ones with side cutters, then check
     the joint.
   - J1 shell tabs: all four slots filled from the top and wetting the tabs; if not, solder them as in
     [hand-soldering](#hand-soldering).
   - No solder bridges on the bottom, between a through-hole pin or J1 shell tab and the SMD pads next to
     it and above all between the RKJXT's COM and ECOM pins (see the RANGE control below): magnifier and
     continuity tester.
4. Cap set, both variants: try the four sets on one of the spare loose keys (two come with the economic
   LCSC set; add two to the LCSC order in the full variant), so pulling off a tight cap pulls at no
   soldered switch ([caps](#caps-light-pipes-knobs)). Without a spare, wait until the keys are on (in the
   economic variant after [bring-up](firmware.md#install-and-bring-up) step 4) and try them on a soldered
   key from loose to tight (C, B, A, D), stopping at the first that holds.

Then [bring-up](firmware.md#install-and-bring-up).

### Hand-soldering

Economic variant: the board comes with every SMD part on the bottom, the two LEDs included; the keys,
encoders and RANGE control are soldered by hand from the bottom side. Flash and test the bare board first
(steps 1 to 3 of [Install and bring-up](firmware.md#install-and-bring-up): the bottom side and USB need no
through-hole part), then solder the keys and check them, and the encoders and RANGE control last: they are
the parts that are hard to remove again. In the full variant JLCPCB fits all of them and solders the J1
shell tabs; only the [arrival checks](#on-arrival) remain (seating, leads, J1 tabs, no bridges), and the
notes below explain what they check.

- USB-C shell tabs: solder all four J1 shell tabs from the top before the first plug-in: flux, then feed
  solder into each slot until it is filled and wets the tab all round (they are GND). The paste Gerber
  puts paste on the shell pads (pin-in-paste), but that is about 0.12 mm³ of solder against about
  0.8 mm³ of slot, so the reflow leaves a fillet on the bottom at most. The tabs, not the 0.3 mm
  contacts, take the load of the plug.
- Every part sits flat on the board. The plate leaves little room: with the parts flat, the encoder pockets
  clear the encoder bodies by 0.31 mm and the RANGE pocket the RKJXT by 0.16 mm at worst (the plate bowed
  towards them as far as the drawing allows), less at the pocket floor corners, so an encoder may stand at
  most 0.05 mm proud (`stack.SEAT_GAP`) and the RKJXT 0.03 mm (checked against its own reading before
  soldering, see the RANGE control below): a 0.05 mm feeler gauge must not slide under an encoder body.
  Solder one pin, check from the side that the part sits flat and square (press it down while you reheat
  that pin if not), then solder the rest. Same for the 28 keys: a tilted key tilts its cap in the key hole.
  Cut every lead to 2 mm or less on the bottom: the board sits only 4.0 mm over the body floor
  (`check_fit.py` has the row).
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

### Assembly

Nothing is glued: the screws hold the board between the plate's bosses and the body, and the light pipes are
held by their shape. The encoder shafts stick out 18 mm past the plate face, so the plate rests face down on
two blocks (books, wood) at least 25 mm high under its long front and back edges, at most 8 mm in from the
edge (the nearest caps and shafts are about 10 mm in), with a cloth on top.

1. Push all caps of the chosen set onto their plungers (see [caps](#caps-light-pipes-knobs)), tactile
   bars as in the 3D view, down until each one sits on its plunger top. Then square them: hold a steel
   rule against the front edges of each row of caps and turn every cap until its edge lies flat on the
   rule. A cap turned by more than about 1° can rub its hole; one turned by more than about 5° lands on
   the plate back instead of in its hole.
2. Light pipes: break both off their bar and sand the two stubs flush with the base on fine sandpaper laid on
   the table, no further (the visible tops stay as printed). The two pipes are the same. Lay the plate face
   down on the blocks and the cloth and drop each pipe into a light hole from the back, rod first: the SHIFT
   hole below the SHIFT key and the UNIT hole between the HOME and SHIFT keys. Each rests on its shoulder on
   the plate back.
3. Board: lower it face down into the plate: the caps drop into their key holes and centre the board, and it
   comes to rest on the four bosses, the pipes' bases standing clear under it. Look at the face between the
   blocks: every cap must stand up through its hole; one that sits on the plate back was turned, so square it
   again.
4. Body: set it over the board, bottom up. Put the four screws in from below, turn each in by hand, then
   tighten them gently with the 2 mm hex key (two fingers on its short arm), crosswise. Then look along the
   gap between the wall tops and the plate back all round (0.65 mm, a thin even line): where it is closed,
   the wall and not the bosses would carry the plate there and the board would not be clamped. Take the body
   off again and sand that wall top down a little on sandpaper laid flat on the table, then try again.
5. USB-C filler: turn the panel over (face up) with its back towards you. Put a small dab of adhesive
   putty (Blu Tack, black or white) on the inner, chamfered half of each side face of the filler (a dab
   further out is scraped off at the notch's edges and smears the back face), set it chamfered edges
   first onto the two ledges in the notch above the plug opening, and push it in with the 1.0 mm blade of
   the feeler gauge set, not a finger (nothing stops it inward; a thin blade bends and pushes it past
   flush): hold the blade flat against the back wall, its long side across the notch and its upper edge
   just under the plate edge, which can stand proud of the wall (a wide steel rule would bear on the plate
   instead), with its holder hanging past the nearer end of the back wall, and press on it close to the
   notch on both sides until it lies flat on the wall there. The filler is then flush and sits on both
   ledges. Check that a USB-C plug still goes all the way in.
6. Fit the knobs: outer knob key into the shaft slot, pushed down until the key sits on the slot floor,
   inner knob onto the D flat until its bore end sits on the shaft tip, and the RANGE knob onto the
   lever's D flat until its bore end sits on the lever tip.
7. Feet: stick the four self-adhesive feet onto the flat pads under the corners. With the steel plate,
   tape it into its recess first (notches at the back corners, round the back feet); the feet go on the
   same pads either way. Turning the panel over for this can slide the filler off its ledges: check it
   is back down on both ledges and flush afterwards (step 5).

### Disassembly

1. Pull the knobs off (inner first). Lay the panel face down on the blocks.
2. Undo the four screws and lift off the body. The USB-C filler comes off with it in its notch, or, where
   the board or the socket is in its way, slides out through the notch's open top and stays on the plate
   back; nothing has to come out first. Before the body goes back on, take the filler out of its notch
   (push it out from the inside): there it would stop the socket. If it stayed on the plate back, pick it
   off: the wall top would land on it.
3. Lift the PCB out; caps that stay in their key holes come out from the front. The light pipes stay on
   their shoulders in the plate as long as it lies face down.
4. To reassemble, push any cap that came out back onto its plunger and square the rows again (step 1),
   check that both light pipes sit in their holes, and do steps 3 to 6.

To take the filler out with the body on, press a ball of the same putty onto its outer face and pull it
straight out (tape grips the MJF surface poorly). Do it with the panel face up: face down the filler can
slide off its ledges towards the plate back.

### Caps, light pipes, knobs

- Key caps: the switch plunger (TE's own STEP model of the 1-1825910-4) has a flat top of 1.26 mm radius with
  a 0.3 mm edge radius and then tapers about 2° per side, from 3.12 mm just under the top to 3.51 mm at the
  switch body; over the 2.7 mm deep cap socket it is 3.12 to 3.29 mm. The socket is a 3.8 mm bore (1.3 mm of
  wall at the narrow cap sides, 1.05 mm on a print with the outline 0.2 mm small and the bore 0.3 mm large,
  nothing open to the outside) with four rigid ribs 1.2 mm wide along its wall, attached over their whole
  length, that follow the plunger's cone: they touch it over 2.04 mm, so a cap that grips cannot rock. They
  stop 0.35 mm under the socket ceiling, clear of the plunger's rounded edge, so the flat ceiling sits on the
  plunger top: the plunger, not the fit, sets the cap height (2.5 mm proud), and the socket ends 0.1 mm or
  more under the plate face (0.11 mm with the plate bowed 0.1 mm towards the board; the socket stays inside
  the cap either way, so that limit is cosmetic). A firm press (10 N, about six times the switch force) bends
  the board under the key by up to about 0.76 mm (the front and back rows are 18 mm from the body posts, which
  do not stop them), and with the plate bowed up the cap can dip up to 0.69 mm under the plate back (a little
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
- Light pipes (clear SLA resin) are stepped rods held by their shape alone: a Ø2.8 mm base that stands on the
  board over its LED's cutout, up to a shoulder 5.35 mm up, and a Ø2.0 mm rod, 3.65 mm long, through a Ø2.3
  mm hole in the plate (0.3 mm under the hole: anodising takes about 0.05 mm off it and the resin may print 0.2
  mm off). Every length may print 0.2 mm off (JLC3DP's resin), and the snap-off stubs are sanded flush, no
  further, so up to 0.1 mm may stay on; the stack takes all of that, with nothing to measure or trim. Lifted,
  the shoulder stops on the plate back round the hole (whose back edge is sharp, so the shoulder sits on the
  flat face), and the top is then still 0.05 mm under the face of the thinnest plate (3.9 mm): it can never
  stand proud. It is never clamped either: the base, long and with a stub on, stays 0.08 mm under the smallest
  gap from the board to the plate back (plate back low and bowed 0.1 mm down, the board bowed 0.1 mm up and
  lifted on a post). A clamp cannot be bounded: the bare board is about 13 (SHIFT) and 17 N/mm (UNIT) stiff
  there, but 87 and 400 N/mm where a post touches it (a plate model of the bare board), so 0.1 mm of clamp
  would load a pipe with up to 40 N. In use the pipe rests on the board and its top sits 1.10 mm under the
  face in the nominal stack, 1.85 mm at worst. From the seat (45°) 43 % of the SHIFT light's top shows in
  the nominal stack (29 % with the rod against the near side of its hole), but only about a fifth of the UNIT
  light's (23 %, 8 % with the rod against the near side): it sits 2.3 mm behind the SHIFT cap, which stands
  2.5 mm over the face within its width; at the worst depth neither shows. The base is
  wider than the cutout, so it cannot drop into it, and with the pipe and the board as far off as they go it may
  tip about the cutout's edge only as far as the rod in its hole allows, its rim staying 0.06 mm over the LED's
  lens. It covers the LED's die, stays out from under the key holes (0.30 mm for SHIFT, 0.10 mm for UNIT, with
  the holes' ±0.1 position: a firmly pressed cap dips under the plate back, inside its hole's outline) and
  clear of the switch bodies (0.18 and 0.20 mm). Both pipes print on one 2.2 x 2.0 mm bar under their bases, on
  Ø1.0 mm necks (JLC3DP's resin parts start at 10 x 2 x 2 mm), so the visible tops stay as printed. The order
  has two bars, one spare.
- The LEDs are reverse-mount 1206 parts on the bottom of the board, their lens up in a 2.2 x 2.4 mm cutout
  through the board ([Electronics](electronics.md#lights)), so nothing stands on the top side but the pipe.
- Knob bores are drawn at the datasheet shaft size (`stack.FIT` = 0): the shafts are toleranced +0/-0.05
  and +0/-0.1 mm, which leaves 0 to 0.1 mm real clearance on a true print, but JLC3DP's resin holes vary by
  about ±0.3 mm. The knobs are held by friction only, so one outer ring, one FMS ring, one inner and the
  RANGE knob also come with a bore 0.2 mm tighter and 0.2 mm looser (`stack.FIT_VARIANTS`). Try those
  first and keep the one that grips. A bore that is still too tight opens with a drill of the shaft size by
  hand (6.0 mm outer, 3.5 mm inner, 2.5 mm RANGE), then a needle file on the D flat; in the outer knob
  drill from below only up to the key (4.41 mm deep) and file the rest, or the drill takes the key off.
  Never drill past the existing bore depth (mark the drill with tape at it): the inner and the RANGE knob
  sit with their bore end on the shaft or lever tip, so a deeper bore lowers the knob, and the RANGE skirt
  has only 0.22 mm over the plate at full tilt. A loose one holds with a strip of tape on the shaft.
  Reprint the rest with that `FIT` if needed.
- The knobs stand 19.9 mm above the plate (29.9 above the PCB), set by the uncut PEC11D shafts. The outer knob
  rests with its key (1.4 mm wide, 0.7 mm into the slot past the shaft surface, 0.5 mm with a small shaft and
  the print) on the floor of the shaft slot. The key stays clear of the inner shaft that runs through the slot
  even on a loose knob pushed towards it, clears even the narrowest slot (2.0 ±0.3) when it prints 0.2 mm wide
  (so it stays under the 1.5 mm JLC3DP asks for on positioning features), and sets the knob height: 1.09 mm
  over the plate, 0.12 mm left with the PEC11D's tolerances (±0.3 under 10 mm, ±0.5 from 10 mm, RSS), the
  highest plate face (bosses, plate thickness, anodising and a bow away from the board, 0.045
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
  the PCB, 4.65 mm off the axis on the side the lever tilts to): at least 0.22 mm over the plate with the knob
  low, the plate face high and bowed up, and the RKJXT tilted on its seat (taken with the fulcrum on the axis,
  which lets the skirt dip further). The Ø16.6 skirt (Ø16.4 on a small print) still covers the 11.1 mm hole
  (11.3 at ISO 2768-m) at full tilt with the lever 0.88 mm off the hole (board, plate, PCB and the RKJXT on
  its pins) and a loose knob 0.3 mm off the lever, by 0.03 mm (the highest knob, its rim at cos 9°, moved 0.06
  mm by the fulcrum's offset, on an RKJXT lifted and tilted as far as its seating check allows). The four pan
  arrows start at r 9.65 mm round the hole centre, 0.02 mm outside that skirt seen square on (Ø16.8 on a large
  print, with the same offsets and the tilted RKJXT, upright); from the seat the skirt 2.3 mm over the plate
  hides a little more. Its rim is 1.1 mm thick (1.0 mm on a thin print).
- BOOT: two bridge pads on the underside of the PCB under a 5 mm hole in the case floor. Bridge them with the
  tip of the 2 mm hex key or a small screwdriver while plugging in USB. Recovery only: normal updates enter
  the bootloader from software.
- Four self-adhesive feet up to 10 mm across, on the four flat 12 mm pads under the corners (with or without
  the steel plate). The aluminium plate adds about 85 g; the printed body is hollow under its 2 mm floor
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
| SHIFT light | stepped light pipe, Ø2.0 mm rod in a Ø2.3 mm hole below the SHIFT cap, amber reverse-mount LED under the PCB |
| UNIT 2 light | stepped light pipe, Ø2.0 mm rod in a Ø2.3 mm hole right of the UNIT legend, white reverse-mount LED under the PCB |
| Amber | #d9a441 (RGB 217, 164, 65; nearest Pantone 7563 C, roughly RAL 1004): SHIFT cap legend, UV print on the plate, 3D view. JLCCNC is asked to match it, with its standard orange as the fallback; the caps and the 3D view follow what the plate gets (`stack.AMBER`, [Ordering](ordering.md#suppliers)) |
