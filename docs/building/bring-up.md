# Bring-up

Check the parts on arrival, then flash CircuitPython and the firmware onto the bare board and test every key,
knob and light, before the plate goes on. The tools are in the [shopping list](ordering.md#shopping-list); how
the firmware works is in [Firmware](../architecture/firmware.md).

## On arrival

Full assembly (the default), in this order:

1. Rail edge (the long edge away from J1): the rail is gone and both corners are round (R3). File a square
   corner to R3 (it would stand 0.74 mm into the body) and sand off a burr.
2. Plate threads: turn one of the M3 screws into each boss by hand with the 2 mm hex key, about ten turns, and
   out again. It must run freely: an anodised thread that was neither masked nor cut again stops it early
   (take it up with JLCCNC). Don't drive it home: without the body it would go past the 6.0 mm of full thread.
3. Seating: the plate pockets leave the encoders and the RANGE control little room
   ([why](../architecture/mechanics.md#seating)), so check what JLCPCB soldered:
   - Encoders: a 0.05 mm feeler blade must not slide under an encoder body anywhere round it, and the lugs are
     soldered.
   - RANGE control (RKJXT): press the loose one from the LCSC order fully down into the footprint of a bare
     board and note at each of its four [gauge spots](assembly.md#gauge-spots) the thickest blade (or stack)
     that slides under its base frame: that is the reference, about 0.40 mm. On each assembled board that
     blade must slide in at every spot and that blade plus 0.03 mm must not. If both boards read outside the
     same way, read the loose part again in another bare board first.
   - The keys sit flat.

   A part that stands proud: reheat its pins while pressing it down, or use the second board for the panel.
4. J1 shell tabs: all four slots filled from the top and wetting the tabs; if not, solder them as in
   [Hand-soldering](assembly.md#hand-soldering).
5. Cap set: [choose it](#choosing-the-cap-set) on one of the spare keys from the LCSC order.

Nothing else needs a tool: the leads stay untrimmed, and a solder bridge shows up in steps 6 and 7 of
[Flash and test](#flash-and-test), where every key, ring, tilt and push is read.

Hand-soldering option: the board is milled all round and fits the body as delivered. Check the plate threads
and choose the cap set (the two spare keys come with the LCSC set); the rest follows in
[Flash and test](#flash-and-test).

Should a board arrive with a rail anyway, break it off along its score with pliers, without bending the board.
Then take that edge down with a flat file or coarse sandpaper on a block until the board drops into the body
(outdoors or wet: glass-fibre dust).

## Choosing the cap set

The order has four sets of 28 caps (A to D, one to four dimples on the bottom) that differ only in their
grip ([why](../architecture/mechanics.md#caps-light-pipes-knobs)). Try one cap of each set on a spare key (no
tools), so pulling off a tight cap loads no soldered key.

- The right set pushes down by hand until the cap sits on the plunger top (it stops hard there; on the board
  its top is then level with its neighbours), holds when the key is turned over and does not wobble.
- Too tight: the cap stops short of the plunger top or needs more than a firm thumb. Too loose: it falls off
  or rocks.
- If two sets fit, take the tighter one (from tight to loose: D, A, B, C).
- Without a spare key, try them on a soldered key from loose to tight (C, B, A, D) and stop at the first set
  that holds, so no tight cap has to be pulled off.
- If even C is too tight, or even D too loose, reprint with `CAP_SETS` in [mech/stack.py](../../mech/stack.py)
  moved by 0.1 mm for each set it missed by (up to 0.3 mm; one round may not do).

Keep the other three sets as spares.

## Flash and test

Full assembly: the board arrives with everything on, so only the checks below apply; if it fails in step 1
or 2, the second board takes over. Hand-soldering: the J1 shell tabs and the through-hole parts go on in
steps 1, 4 and 7, the encoders and the RANGE control last ([Ordering](ordering.md#assembly-variants)).

1. Before the first power-up (hand-soldering: first solder the four J1 shell tabs,
   [Hand-soldering](assembly.md#hand-soldering)):
   1. Look over the bottom side (RP2040, USB-C, regulator).
   2. With the multimeter, measure VBUS to GND on both pads of the fuse F1 (J1's side and the regulator's) and
      3V3 to GND (across C_OUT0). None may be a short.
   3. Switch the multimeter to diode mode, red probe on F1's pad on the regulator's side (VBUS_F), black on
      R_DP's outer pad (D+ between U4 and R_DP). A good board reads open or climbs past about 1.5 V (any path
      runs through the regulator, a load and one of U4's diodes in series). A steady 0.5 to 0.8 V from the
      start means U4 is turned by 180°: its GND pin then sits on VBUS_F and a steering diode conducts into D+,
      which the resistance range does not show as a short. Have U4 replaced before the first power-up
      ([why](../architecture/electronics.md#usb-protection)).

   Where the parts are (the bottom silkscreen names only the bigger parts, and not F1):
   - F1: the largest two-pad part on the board (3.2 x 1.6 mm, its pads 3 mm apart), along the long edge about
     4 mm below J1's pad row, between U4 and U3.
   - U4, the ESD array (named): the six-pin part right below J1's contacts.
   - U3, the regulator: the three-pin part beside J1.
   - R_IN: a small resistor across the board between J1's pad row and F1's pad nearer U4.
   - R_DP: the lower of the two small resistors that lie one below the other along the long edge, about 5 mm
     below the RP2040's corner on U3's side (the upper one is R_DM). Probe its outer pad, the end away from
     the RP2040 and towards the nearer short edge.
   - C_OUT0: the small capacitor on U3's side towards the board edge.
   - GND: J1's metal shell, the easiest place for the black probe.
2. Plug in USB. With empty flash the RP2040 starts its USB bootloader and shows a drive called RPI-RP2. Check
   that 3V3 reads about 3.3 V across C_OUT0 (or from its 3V3 end to J1's shell).
3. Copy the [CircuitPython 9.2.9 UF2 for the Raspberry Pi Pico][uf2] (same chip, 2 MB flash, 12 MHz crystal)
   to RPI-RP2. The firmware is checked against 9.2.9; newer versions are untested, and the board page on
   circuitpython.org does not offer 9.2. The board restarts with a CIRCUITPY drive.
4. Hand-soldering only: solder the 28 keys, seated flat ([Hand-soldering](assembly.md#hand-soldering)), but
   not yet the encoders and the RANGE control.
5. Copy `boot.py`, `code.py`, `panel.py` and `buttonmap.py` from [firmware/](../../firmware/) to CIRCUITPY
   (the repository's `code.py`, with `PICO_TEST = False` and `divisor=2`, not the copy edited for the Pico
   bench). Then:
   1. Replug with SHIFT held until CIRCUITPY appears ([update mode](#normal-and-update-mode)): `boot.py` only
      runs at power-up.
   2. Open the serial console (Linux: for example `tio /dev/ttyACM0`; Windows: the serial console of Thonny or
      Mu, or PuTTY on the panel's COM port, which Device Manager lists under Ports). CircuitPython only writes
      to the serial port while a terminal has it open, so what `code.py` printed at start-up is already gone:
      press Ctrl-C (`code.py` releases every button and stops) and then Ctrl-D, which runs it again. `code.py`
      then prints "Avionics Panel rev 1 ready", or, if `boot.py` did not run, a traceback ending in
      `RuntimeError: joysticks missing: copy boot.py and replug the panel`.
   3. Replug without SHIFT: CIRCUITPY and the serial port must not appear. If they still do, SHIFT reads as
      held (row GP2, column GP6).
6. Check the joysticks on Windows:
   - "Set up USB game controllers" (`joy.cpl`) must show two "Avionics Panel" devices (if it shows another
     name, see [Mapping](../using/mapping.md#device-name)). It only shows 32 buttons per device.
   - Check every key and both lights (before the plate goes on, the LEDs shine up through their cutouts in the
     board) with MobiFlight's input view or a DirectInput tester that shows all 128 buttons (for example
     Pointy's Joystick Test), against [BUTTONS.md](../../firmware/BUTTONS.md). Device 2 only responds while
     unit 2 is selected (SHIFT, HOME); [Mapping](../using/mapping.md#two-joysticks) says how to tell the two
     apart.
   - Column check: hold each key and check that the button of the matrix position right below it (same column
     of `MATRIX` in [buttonmap.py](../../firmware/buttonmap.py)) stays released. A column that recovers too
     slowly shows a phantom press there ([why](../architecture/electronics.md#gpio-map)), even where that part
     is not fitted yet (hand-soldering: the RANGE control and the encoder pushes). The likeliest pairs are UP
     to DN, DN to `RANGE_A` (a PAN button) and ENT to the FMS push (`FMS_CRSR`). Below HOME is SHIFT, which
     sends no button: while HOME is held, the amber light must stay off. If a phantom shows up, check that
     column's pull-up before going on.
7. Hand-soldering: unplug and solder the three encoders and the RANGE control first. Both variants:
   1. Check every ring (direction, outer / inner), the RANGE tilt directions and every push the same way as
      the keys in step 6. If a ring turns the wrong way, flip its reverse flag (the last field, `False` to
      `True`) in `RINGS` in [code.py](../../firmware/code.py). If outer and inner are swapped, swap the two
      ring names there (`ALTHDG_OUTER` and `ALTHDG_INNER`, for example). Copy `code.py` again with SHIFT held.
      A wrong RANGE tilt direction is fixed in `PAN_DIRS` in [panel.py](../../firmware/panel.py).
   2. Repeat the column check with the parts fitted: hold DN, no PAN button; hold ENT, no `FMS_CRSR`; hold
      PROC for a second and let go, no PTR during the hold or after it (the RANGE centre contact sits below
      PROC, and the firmware sends PTR only once that contact opens again).
   3. Do the [first-board checks](#first-board).

Then the panel goes together: [Assembly](assembly.md#putting-it-together).

## When bring-up fails

The steps are those of [Flash and test](#flash-and-test).

- No RPI-RP2 drive (step 2): try another cable (a charge-only cable shows nothing) and another USB port, then
  measure 3V3 again. With 3V3 right, look at J1's contacts and the crystal Y1 under the magnifier for bridges
  or a lifted pin (solder wick for a bridge). Still nothing: put this board aside and use the second one. The
  bench Pico can also serve as an SWD probe on the board's SWCLK and SWDIO pads (bottom, next to the RP2040;
  GND on J1's shell) with Raspberry Pi's debugprobe firmware, to see whether the RP2040 answers at all.
- A key that never registers (step 6): check its diode, the SOD-123 next to it on the bottom, under the
  magnifier: its cathode band must be on the pad with the silkscreen bar. Turn a reversed one round with the
  iron. Then check the key's four solder joints (hand-soldering).
- A key that registers as another one, or several keys at once: a solder bridge, or the phantom press of a
  slow column (step 6).
- A ring that counts the wrong way or rings swapped: `RINGS` in `code.py` (step 7).

## First board

On the first board, after step 7 of [Flash and test](#flash-and-test):

- Knob timing: MobiFlight must count every detent of a quick turn
  ([why](../architecture/firmware.md#knob-steps)). It needs a MobiFlight mapping and a running sim, so it can
  wait until [mapping](../using/mapping.md).
  1. Map `FMS_INNER_CW` to a counter you can read in the sim (for example heading bug +1 in MobiFlight).
  2. Spin the FMS inner ring 8 detents quickly: the bug must move by 8°.
  3. Repeat in unit 2 while UP is held (FMS on device 2, UP repeating on device 1).
  4. Repeat in unit 2 with the FMS inner ring and the ALT/HDG knob turning at the same time (ALT/HDG on
     device 1).

  If steps go missing, tune `PRESS_MS`, `GAP_MS` and `MAX_QUEUE` in [panel.py](../../firmware/panel.py) (a
  step longer than the 120 ms tilt repeat slows a held tilt down).
- Loop pass time: the firmware times every pulse in passes of its main loop, so each pass adds to the 56 ms
  of a press and of a gap. To measure it, add this to `code.py` temporarily: before the `try:` above
  `while True:` the line `n_pass = t_mark = t_prev = worst = 0`, and right after the line that sets `t` in the
  loop:

  ```python
          if t_prev:
              worst = max(worst, t - t_prev)
          t_prev = t
          n_pass += 1
          if t - t_mark >= 1000:
              print(n_pass, "passes, longest", worst, "ms")
              n_pass, t_mark, worst = 0, t, 0
  ```

  Read it on the console ([update mode](#normal-and-update-mode)) idle, while a knob spins and while a tilt is
  held, with a program reading the joysticks (on Linux keep `evtest` open, or every send stalls). The longest
  pass counts: up to about 4 ms a held tilt keeps its 120 ms repeat, beyond that it slows down. Copy the
  repository's `code.py` back afterwards.
- GP25: check that the FREQ outer ring counts normally once `code.py` runs
  ([why](../architecture/firmware.md#pins)).
- The lights: judge both behind their light pipes once the panel is assembled. If the console (step 5) shows
  "LED drive strength not set", the lights stay dimmer at the RP2040's 4 mA default. The brightness is
  `LED_DUTY` in [code.py](../../firmware/code.py): 0x4800 for SHIFT and 0x4000 for UNIT, about 28 and 25 % of
  full; change those first (up to 0xFFFF). Only if the white light is still too dim at full duty (a part from
  the highest forward voltage bin), bridge R_UNIT's pads with solder or fit a 0603 0 R (for example C21189) in
  its place ([Electronics](../architecture/electronics.md#lights)), then keep `LED_DUTY[1]` at 0x8000 or less.

## Normal and update mode

In normal use the panel shows up as the two joysticks only: `boot.py` hides the CIRCUITPY drive and the serial
console, so nothing on the PC can write to the firmware. To keep both for an update, hold SHIFT while plugging
in until CIRCUITPY appears (about 2 s; `boot.py` reads SHIFT up to 1 s after power-up, so a short press is
missed). A board without `boot.py` (a fresh CircuitPython install) always shows them. Test and map the
joysticks only after a plain replug ([why](../using/mapping.md#update-mode-and-guids)).

## Updates and recovery

Plug in with SHIFT held until CIRCUITPY appears, copy the changed files to CIRCUITPY, then replug without
SHIFT before using MobiFlight. To reach the bootloader without the BOOT pads (for a new CircuitPython
version), plug in the same way, open the serial console, press Ctrl-C, then Enter at "Press any key to enter
the REPL", and run this:

```python
import microcontroller
microcontroller.on_next_reset(microcontroller.RunMode.UF2)
microcontroller.reset()
```

If CircuitPython ever stops booting: bridge the two BOOT pads, under the 5 mm hole in the body floor, with the
tip of the 2 mm hex key or a small screwdriver while plugging in USB, and start again at step 3 of [Flash and
test](#flash-and-test). A new UF2 keeps the files on CIRCUITPY, `boot.py` too; if SHIFT no longer brings the
drive back, copy Raspberry Pi's [`flash_nuke.uf2`](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2) to
RPI-RP2 first, which erases the whole flash.

## Pico bench

Before the boards arrive, the firmware runs on a plain Raspberry Pi Pico or Pico H with a few buttons and one
encoder. That also tests the riskiest assumption early: whether MobiFlight tells apart two joysticks from one
USB device that both carry the name "Avionics Panel".

Parts:

- A Pico or Pico H (RP2040) with headers, not a Pico W (its radio takes GP23, GP24, GP25 and GP29) and not a
  Pico 2 (RP2350, which needs another CircuitPython build).
- A data-capable micro-USB cable, a breadboard and jumper wires.
- A few push buttons and a 1N4148 diode.
- One cheap EC11-type encoder with push and 30 detents / 15 pulses per turn (not one of the panel's three
  PEC11D).

Set `PICO_TEST = True` in [code.py](../../firmware/code.py): a plain Pico lacks GP23, GP24, GP25 and GP29 on
its header, so the FREQ knob moves to GP12 to GP15 and its push to GP22; the RANGE encoder still runs on
GP28/GP29 but cannot be turned there. Wire it up (pins are the GPn numbers, not the header pin numbers; the
keys are matrix positions, row and column in `MATRIX` in [buttonmap.py](../../firmware/buttonmap.py)):

- SHIFT as on the board, a button from GP6 to GP2 through the diode (anode at GP6), or bridge GP6 to GP2 with
  a wire from plugging in until CIRCUITPY appears: without it the Pico hides its drive as soon as `boot.py` is
  on it.
- UP: a button from GP1 to GP5. HOME: a button from GP6 to GP5 (SHIFT, then HOME switches the unit). Plain
  buttons work as long as no three of them are held at once.
- The encoder as the FMS inner ring, whose pins stay the same in `PICO_TEST`: A to GP16, B to GP17, common to
  GND (`rotaryio` pulls A and B up); its push from GP10 to GP0 (FMS push). `code.py` counts a detent every two
  quadrature steps (`divisor=2`), as the PEC11D's 30 detents and 15 pulses per turn need. A 20 detent / 20
  pulse part (common among cheap EC11 and KY-040 encoders) counts each detent twice, and the 8-step queue can
  hide that in the timing check. For such a part set `divisor=4` in `code.py` on the bench, and back to 2 for
  the board.

Run steps 3, 5 and 6 of [Flash and test](#flash-and-test) as on the board and check:

- Two joysticks in MobiFlight, both named "Avionics Panel": 128 buttons on device 1, 64 on device 2.
- The knob timing as on the [first board](#first-board), with the bench encoder as the FMS inner ring. For the
  test with both joysticks, select unit 2, hold UP (device 1) and spin the encoder (device 2). After a plain
  replug the console is off, so unit 2 shows as the encoder and HOME sending on device 2 (plain HOME on device
  1 means unit 1).
- Encoder directions, ring order (outer / inner) and the RANGE tilt directions (`PAN_DIRS` in
  [panel.py](../../firmware/panel.py)), as far as one bench encoder and the buttons show them.
- Whether the GUIDs differ: do MobiFlight and `joy.cpl` list the joysticks as new controllers after a plug-in
  with SHIFT held ([Mapping](../using/mapping.md#update-mode-and-guids))?

`PICO_TEST` puts the SHIFT light on the Pico's own LED and prints the unit instead, so the bench says
nothing about the real lights. Mappings made on the bench do not carry over to the board
([Mapping](../using/mapping.md#update-mode-and-guids)).

[uf2]: https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-9.2.9.uf2
