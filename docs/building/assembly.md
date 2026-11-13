# Assembly

Put the panel together after the [bring-up](bring-up.md), and take it apart again. The tools are in the
[shopping list](ordering.md#shopping-list); why the parts are shaped as they are is in
[Mechanics](../architecture/mechanics.md).

## Putting it together

Five screws hold the plate, the board and the body together, and the light pipes are held by their shape; the
[exploded view](../../renders/3-exploded.png) shows the parts in order. Work face down on two blocks at least
25 mm high with a cloth on top: the encoder shafts stick out about 17.5 mm past the plate face. Put the blocks
under the plate's long front edge and its back edge (the one with the tongue, which goes over J1, the USB-C
socket), at most 6 mm in: the SHIFT light's hole starts 6.6 mm from the front edge (6.45 mm at the ends of
its tolerances), and a block under it would push the pipe up, so that the board lands on the pipe instead of
the bosses. The nearest caps and shafts are about 10 mm in.

1. Caps: lay the board face up with J1 at the back; its front edge is the one away from J1. Push each cap of
   the [chosen set](bring-up.md#choosing-the-cap-set) onto the key whose name is printed in front of it
   (SHIFT: the key with the SHIFT light's cutout in front of it), legend upright, until it sits on the plunger
   top. For a cap that is loose or too tight on its key, take the same legend from the next set. The tactile
   bars of SHIFT and DN are then at the front edge, the bar of UP at the back edge. Square the caps: hold a
   steel rule against the front edges of each row and turn every cap until its edge lies flat on the rule. A
   cap left turned rubs in its hole or lands on the plate back instead.
2. Light pipes (before or after step 1): break both off their bar and sand the two stubs flush with the base
   on fine sandpaper laid on the table, no further (the visible tops stay as printed). The two pipes are the
   same. Lay the plate face down on the blocks and the cloth. Drop a pipe, rod first, into each of the two
   small round holes among the key holes: one between the front row of key holes and the front edge, one
   between the two front rows. Each rests on its shoulder on the plate back. A rod that has grown too tight for
   its hole (resin keeps changing size in its first week) sands free in a fold of the fine sandpaper.
3. Board: lower it face down into the plate, J1 towards the plate's tongue. The caps drop into their key
   holes and centre the board, and it comes to rest on the five bosses, the pipes' bases standing clear under
   it. Look at the face between the blocks: every cap must stand up through its hole. One that sits on the
   plate back was turned, so square it again.
4. Body: set it over the board, bottom up. The tongue on the plate's back edge goes into the slot in the
   body's back wall, over the USB-C socket.
   1. Drop the five screws into the holes in the body's underside, which now faces up: four at the corners
      and one in the middle of the key field (they are all the same). Turn each in with the hex key until it
      holds the body loosely (the counterbores are too deep to start them by hand). A screw that does not pass
      its body hole: lift the body off, open that hole with the 4.2 mm drill, its drawn size, turned by hand,
      and set the body on again; the flange still covers it.
   2. Centre the body by eye: slide it until its walls are flush with the plate's edges and the gaps on both
      sides of the tongue look the same, about 0.9 mm each. If the screws leave no room to slide, leave it:
      0.3 to 1.5 mm per side is within tolerance.
   3. Tighten the screws gently with the 2 mm hex key (two fingers on its short arm, about 0.3 N m), the
      corners crosswise, then the middle one. Tighten them again the same way after a week: the PA12 under the
      flanges settles.
   4. Feet: stick the four self-adhesive feet onto the flat pads under the corners.

   A gap of about 1 mm stays between the wall tops and the plate all round: the bosses carry the plate, not
   the walls. Check it after tightening; where a wall touches the plate, take that wall top down with the
   flat file or the sandpaper on a block until the gap shows.
5. Turn the panel face up and check:
   - Keys: press the four keys at the corners of the key field (AP, COM ⇆, DN and ENT). Each must go down
     and come back freely. If one rubs in its hole, loosen the five screws by a turn, push that cap towards
     the middle of its hole, which moves the board with it, and tighten the screws again.
   - Cable: plug in the USB-C cable. Its overmould must go into the body's opening without force, and the
     plug must seat in the socket. One that does not is too large
     ([which cable](ordering.md#shopping-list)).
6. Knobs: [fit them](#fitting-the-knobs).

The panel is then ready for [Mapping](../using/mapping.md). If a light is too bright or too dim behind its
pipe, [change its brightness](bring-up.md#light-brightness).

### Fitting the knobs

The knobs are held by friction alone, and printed bores vary, so the order has every knob in five bores,
0.1 mm apart ([why](../architecture/mechanics.md#knobs)). One to five dimples name the bore: 1 is the
tightest, 5 the loosest. They are deep round pits, 0.9 mm across, on one arc with a gap after the third, so
four read as three and one, five as three and two. An outer ring has them in its bottom face, an inner knob
inside the recess in its underside, the RANGE knob in its dished underside. Where the marks cannot be read,
any of the five that goes on by hand and holds is the one to keep. Resin keeps changing size in its first
week, so fit the knobs a few days after they arrive. The FMS knob takes the outer ring with the 14 deep
flutes; ALT/HDG and FREQ take the rings with 24 fine ones.

For each shaft, try the five bores from the loosest (5) to the tightest (1) and keep the first that grips,
so no tight knob has to be pulled off again. A knob goes on by hand, the panel face up on the desk; one that
grips stays on when the panel is turned over and does not wobble.

- Outer ring: push its key into the shaft slot until it sits on the slot floor. Turn it a little back and
  forth: one that moves without its shaft does not grip. Its key has about a detent of play in the slot,
  which only the bore's grip takes out.
- Inner knob: push it onto the D flat until its bore end sits on the shaft tip.
- RANGE knob: push it onto the lever's D flat until its bore end sits on the lever tip. Then tilt it fully
  in every direction, also between two, and push it while tilted: the skirt must not touch the plate. A knob
  that does not grip cocks on the lever at full tilt until its skirt touches.
- A knob that needs more than a firm thumb is too tight: do not force it, as the force goes into the
  encoder's shaft (the inner one is the push switch).
- An outer ring that rubs the plate when turned (the encoders' heights vary, and so does a support mark
  left on its bottom face): take it off, sand its bottom face on the fine sandpaper laid on the table, a few
  strokes at a time, until it clears. Then push the inner knob: it must still click without touching the
  ring.
- An inner knob that touches its ring when pushed: sand the rim of its underside the same way.
- If even bore 1 does not grip, or even bore 5 is too tight, set `FIT` in
  [mech/stack.py](../../mech/stack.py) to -0.5 (1 was loose) or 0.5 (5 was tight), so that the five new
  bores go on where the old ones ended. Run [`./build.sh`](../architecture/generators.md#build) and order
  the five files of that knob again. `FIT` moves the bores of every knob type, so order only the type that
  missed. Bag or discard the first set of that knob before the second arrives: the new knobs have the same
  file names and dimple counts.

## Disassembly

1. Pull the knobs off, inner first, the panel face up on the desk: rock each while pulling, and never lever
   against the plate. Lay the panel face down on the blocks.
2. Undo the five screws and lift off the body.
3. Lift the board out. Caps that stay in their key holes come out from the front. The light pipes stay on
   their shoulders in the plate as long as it lies face down.
4. To reassemble, push any cap that came out back onto its plunger and square the rows again (step 1 of
   [Putting it together](#putting-it-together)), check that both light pipes sit in their holes, and do
   steps 3 to 6.
