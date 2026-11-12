# Assembly

Put the panel together after the [bring-up](bring-up.md), and take it apart again. The last section covers
soldering, for the hand-soldering option and for rework. The tools are in the
[shopping list](ordering.md#shopping-list); why the parts are shaped as they are is in
[Mechanics](../architecture/mechanics.md).

## Putting it together

Five screws hold the plate, the board and the body together, and the light pipes are held by their shape.
Work face down on two blocks at least 25 mm high with a cloth on top: the encoder shafts stick out about
17.5 mm past the plate face. Put the blocks under the plate's long front edge and its back edge (the one with
the tongue, which goes over J1, the USB-C socket), at most 8 mm in (the nearest caps and shafts are about
10 mm in).

1. Caps: lay the board face up with J1 at the back; its front edge is the one away from J1. Push each cap of
   the [chosen set](bring-up.md#choosing-the-cap-set) onto the key whose name is printed in front of it
   (SHIFT: the key with the SHIFT light's cutout in front of it), legend upright, until it sits on the plunger
   top. The tactile bars of SHIFT and DN are then at the front edge, the bar of UP at the back edge. Square
   the caps: hold a steel rule against the front edges of each row and turn every cap until its edge lies flat
   on the rule. A cap turned by more than about 1° can rub its hole; one turned by more than about 5° lands on
   the plate back instead of in its hole.
2. Light pipes (before or after step 1): break both off their bar and sand the two stubs flush with the base
   on fine sandpaper laid on the table, no further (the visible tops stay as printed). The two pipes are the
   same. Lay the plate face down on the blocks and the cloth. Drop a pipe, rod first, into each of the two
   small round holes in the key field (the light holes: on the face, below the SHIFT key and beside the UNIT
   legend). Each rests on its shoulder on the plate back.
3. Board: lower it face down into the plate. The caps drop into their key holes and centre the board, and it
   comes to rest on the five bosses, the pipes' bases standing clear under it. Look at the face between the
   blocks: every cap must stand up through its hole. One that sits on the plate back was turned, so square it
   again.
4. Body: set it over the board, bottom up. The tongue on the plate's back edge goes into the slot in the
   body's back wall, over the USB-C socket.
   1. Put the five screws in from below, four at the corners and one in the middle of the key field (they are
      all the same), and turn each in by hand until it holds the body loosely.
   2. Centre the body by eye: slide it until its walls are flush with the plate's edges and the gaps on both
      sides of the tongue look the same, about 0.9 mm each. If the screws leave no room to slide, leave it:
      0.3 to 1.5 mm per side is within tolerance.
   3. Tighten the screws gently with the 2 mm hex key (two fingers on its short arm), the corners crosswise,
      then the middle one.

   A gap of about 1 mm stays between the wall tops and the plate all round: the bosses carry the plate, not
   the walls.
5. Knobs: turn the panel face up and [fit them](#fitting-the-knobs).
6. Feet: stick the four self-adhesive feet onto the flat pads under the corners.

### Fitting the knobs

Push the outer knob's key into the shaft slot until it sits on the slot floor, the inner knob onto the D flat
until its bore end sits on the shaft tip, and the RANGE knob onto the lever's D flat until its bore end sits
on the lever tip. The knobs are held by friction only, and resin bores vary, so the order has each knob type
also with a bore 0.2 mm tighter and 0.2 mm looser: keep whichever grips.

- Open a bore that is still too tight with a drill of the shaft size turned by hand (6.0 mm outer, 3.5 mm
  inner, 2.5 mm RANGE), then a needle file on the D flat. In the outer knob, drill from below only up to the
  key (3.8 mm deep) and file the rest, or the drill takes the key off.
- Never drill past the existing bore depth; mark it on the drill with tape. The inner and the RANGE knob sit
  with their bore end on the shaft or lever tip, so a deeper bore lowers the knob, and the RANGE knob clears
  the plate by only about 0.2 mm at full tilt.
- Hold a loose knob with a strip of tape on the shaft.
- If only the tight or loose variant grips, the order has too few of it for the outer rings and inner knobs.
  Set `FIT` in [mech/stack.py](../../mech/stack.py) to -0.2 (tight) or 0.2 (loose) and run
  [`./build.sh`](../architecture/generators.md#build): it rewrites all 12 knob files in `production/`. Order
  the types that ran short again: `knob-outer.step` and `knob-inner.step` with their `-tight` and `-loose`
  variants. `FIT` applies to every knob type, so an outer ring that needs tight and an inner knob that needs
  loose take two builds.

## Disassembly

1. Pull the knobs off (inner first). Lay the panel face down on the blocks.
2. Undo the five screws and lift off the body.
3. Lift the board out. Caps that stay in their key holes come out from the front. The light pipes stay on
   their shoulders in the plate as long as it lies face down.
4. To reassemble, push any cap that came out back onto its plunger and square the rows again (step 1 of
   [Putting it together](#putting-it-together)), check that both light pipes sit in their holes, and do
   steps 3 to 5.

## Hand-soldering

Only with the hand-soldering option, and for rework. The board comes with every SMD (surface-mount) part on
the bottom, the two LEDs included; the keys, encoders and RANGE control are soldered by hand from the bottom
side. The [bring-up](bring-up.md#flash-and-test) says when: the J1 shell tabs first, then flash and test the
bare board, then the keys, and the encoders and RANGE control last, as they are the parts that are hard to
remove again.

- J1 shell tabs: solder all four from the top before the first plug-in: flux, then feed solder into each slot
  until it is filled and wets the tab all round. The tabs are on GND (ground) and take the load of the plug
  ([why](../architecture/electronics.md#solder-mask)).
- Every part sits flat on the board: solder one pin, check from the side that the part sits flat and square
  (press it down while you reheat that pin if not), then solder the rest. Same for the 28 keys: a tilted key
  tilts its cap in the key hole. Leave the leads untrimmed.
- Encoders: solder the mounting lugs in their slots too; they carry the push of the knobs.
- RANGE control (RKJXT): it may sit off-centre on its pins; the plate leaves it room.
- The RKJXT's COM and ECOM pins are the closest hand-soldered pair on the board (0.38 mm of copper between the
  pads, RANGE_COM and GND): check them for a bridge with a magnifier and a continuity tester. A bridge makes
  COM 1, COM 2, FPL and PROC read pressed all the time, and the RANGE push sends no PTR.
