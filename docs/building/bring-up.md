# Bring-up

Check the parts on arrival, then flash CircuitPython and the firmware onto the bare board and test every key,
knob and light, before the plate goes on. The tools are in the [shopping list](ordering.md#shopping-list); how
the firmware works is in [Firmware](../architecture/firmware.md).

## On arrival

Full assembly (the default), in this order:

1. Rail edge (the long front edge, away from J1, the USB-C socket): check that the rail is gone and both
   corners are round (R3). File a square corner to R3 and sand off a burr.
2. Plate threads: turn one of the M3 screws into each of the five bosses by hand with the 2 mm hex key, about
   ten turns, and out again. It must run freely: an anodised thread that was neither masked nor cut again
   stops it early (take it up with JLCCNC). Do not drive it home: without the body it would go past the 6.0 mm
   of full thread.
3. Joints the remark asked for: check that the two mounting lugs of each encoder are soldered in their slots
   (bottom side), and that all four J1 shell tab slots are filled from the top with the solder wetting the
   tabs. If not, solder them as in [Hand-soldering](assembly.md#hand-soldering).
4. Parts: check that the keys, the encoders and the RANGE control sit flat on the board. Reheat the pins of
   one that does not while pressing it down, or use the second board for the panel.
5. Cap set: [choose it](#choosing-the-cap-set) on one of the spare keys from the LCSC order.

Solder bridges need no check now: steps 6 and 7 of [Flash and test](#flash-and-test) read every key, ring,
tilt and push.

Hand-soldering: steps 1, 2 and 5 only; the soldering follows in [Flash and test](#flash-and-test).

A board that arrives with a rail anyway, or with a V-cut (scored and snapped) edge that does not fit the body:

1. If the rail is still on, break it off along its score with flat-nose pliers, without bending the board.
2. Take that edge down with a flat file or coarse sandpaper on a block until the board drops into the body
   (outdoors or wet: glass-fibre dust).

## Choosing the cap set

The order has four sets of 28 caps (A to D, one to four dimples on the bottom) that differ only in their
grip ([why](../architecture/mechanics.md#key-caps)). Try one cap of each set on a spare key (no tools), so
pulling off a tight cap loads no soldered key.

- The right set pushes down by hand until the cap sits on the plunger top (it stops hard there; on the board
  its top is then level with its neighbours), holds when the key is turned over and does not wobble.
- Too tight: the cap stops short of the plunger top or needs more than a firm thumb. Too loose: it falls off
  or rocks.
- If two sets fit, take the tighter one (from tight to loose: D, A, B, C).
- Without a spare key, try them on a soldered key from loose to tight (C, B, A, D) and stop at the first set
  that holds, so no tight cap has to be pulled off.
- If even C is too tight, raise `CAP_SETS_MOVE` in [mech/stack.py](../../mech/stack.py) by 0.1 mm for each
  set it missed by; if even D is too loose, lower it the same way (up to 0.3 mm either way; one round may not
  do). Run [`./build.sh`](../architecture/generators.md#build) and order the four `caps-*.zip`
  again from `production/`: each round reprints all four sets.

Keep the other three sets as spares.

## Flash and test

Full assembly: the board arrives with everything on, so only the checks below apply; if one board fails in
step 1 or 2, the other takes over (a fault on both: [When bring-up fails](#when-bring-up-fails)).
Hand-soldering: the J1 shell tabs and the through-hole parts go on in steps 1, 4 and 7, the encoders and the
RANGE control last ([Ordering](ordering.md#assembly-variants)). On Linux, after every copy to RPI-RP2 or
CIRCUITPY run `sync` and let it finish before you replug.

1. Before the first power-up (hand-soldering: first solder the four J1 shell tabs,
   [Hand-soldering](assembly.md#hand-soldering)):
   1. Look over the bottom side (RP2040, USB-C, regulator).
   2. With the multimeter's continuity beeper, measure from GND (ground) to both pads of the fuse F1 (VBUS_R
      on J1's side, VBUS_F on the regulator's) and to 3V3 (the 3.3 V supply) at C_OUT0. None may be a short:
      a short beeps without stopping and reads a few ohms or less; a chirp that stops is the capacitors
      charging.
   3. Switch the multimeter to diode mode, red probe on F1's pad on the regulator's side (VBUS_F), black on
      R_DP's outer pad (D+ between U4 and R_DP). A good board reads open or climbs past about 1.5 V (any path
      runs through the regulator, a load and one of U4's diodes in series). A steady 0.5 to 0.8 V from the
      start means U4 is turned by 180°: its GND pin then sits on VBUS_F and a steering diode conducts into D+,
      which the continuity check in step 2 does not show as a short. Have U4 replaced before the first
      power-up ([why](../architecture/electronics.md#usb-protection)).

   Where the parts are, board bottom up with J1 at the top edge (the bottom silkscreen names only the bigger
   parts, and not F1):
   - F1: the largest two-pad part on the board (3.2 x 1.6 mm, its pads 3 mm apart), along the long edge about
     4 mm below J1's pad row, between U4 and U3.
   - U4 (named on the silkscreen), the electrostatic discharge (ESD) array: the six-pin part right below J1's
     contacts.
   - U3, the regulator: the three-pin part beside J1.
   - R_DP: the lower of the two small resistors that lie one below the other along the long edge, about 5 mm
     below the RP2040's corner on U3's side (the upper one is R_DM). Probe its outer pad, the end away from
     the RP2040 and towards the nearer short edge.
   - C_OUT0: the small capacitor on U3's side towards the board edge.
   - GND: J1's metal shell, the easiest place for the black probe.
2. Plug in USB. With empty flash the RP2040 starts its USB bootloader and shows a drive called RPI-RP2. Check
   that 3V3 reads 3.2 to 3.4 V across C_OUT0 (or from its 3V3 end to J1's shell).
3. Copy the [CircuitPython 9.2.9 UF2 file for the Raspberry Pi Pico][uf2] (same chip, 2 MB flash, 12 MHz
   crystal) to RPI-RP2; the firmware is tested on 9.2.9. The board restarts with a CIRCUITPY drive.
4. Hand-soldering only: solder the 28 keys, seated flat ([Hand-soldering](assembly.md#hand-soldering)), but
   not yet the encoders and the RANGE control.
5. Copy `boot.py`, `code.py`, `panel.py` and `buttonmap.py` from [firmware/](../../firmware/) to CIRCUITPY
   (the repository's `code.py`, with `PICO_TEST = False` and `divisor=2`, not the copy edited for the Pico
   bench). Then:
   1. Replug with SHIFT held until CIRCUITPY appears ([update mode](#normal-and-update-mode)): `boot.py` only
      runs at power-up.
   2. Open the serial console (Linux: for example `tio /dev/ttyACM0`; Windows: the serial console of Thonny or
      Mu, or PuTTY on the panel's COM port, which Device Manager lists under Ports). Press Ctrl-C, then
      Ctrl-D: `code.py` runs again and prints "Avionics Panel rev 1 ready", or, if `boot.py` did not run, a
      traceback ending in `RuntimeError: joysticks missing: copy boot.py and replug the panel`.
   3. Replug without SHIFT: CIRCUITPY and the serial port must not appear. If they still do, SHIFT reads as
      held (row GP2, column GP6).
6. Check the joysticks:
   - Windows: "Set up USB game controllers" (`joy.cpl`) must show two "Avionics Panel" devices (if it shows
     another name, see [Mapping](../using/mapping.md#device-name)). It only shows 32 buttons per device, so
     read the buttons in MobiFlight's input view or a DirectInput tester that shows all 128 (for example
     Pointy's Joystick Test).
   - Linux: `evtest` and `jstest` show one input device with device 1's first 80 buttons and nothing of
     device 2. Check the buttons with `hid-recorder`: run `pipx install hid-tools`, then
     `sudo ~/.local/bin/hid-recorder`, and pick "Avionics Panel": each report shows `ReportID: 4` (device 1)
     or `5` (device 2) and a `Button:` list of 0 and 1 in button order.
   - Check every key and both lights (before the plate goes on, the LEDs shine up through their cutouts in the
     board) against [BUTTONS.md](../../firmware/BUTTONS.md). Device 2 only responds while unit 2 is selected
     (SHIFT, HOME); [Mapping](../using/mapping.md#two-joysticks) says how to tell the two apart.
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
   3. Do the loop pass time and GP25 checks of [First board](#first-board); the knob timing and the lights
      follow after assembly and mapping.

Then the panel goes together: [Putting it together](assembly.md#putting-it-together).

## When bring-up fails

By the step of [Flash and test](#flash-and-test) that shows the fault:

- Step 1, a short or the U4 reading: check the second board the same way. A fault on both is a placement
  error: do not power either board; send JLCPCB photos of both and the readings, and ask for rework.
- Step 2, no RPI-RP2 drive: try another cable (a charge-only cable shows nothing) and another USB port, then
  measure 3V3 again. With 3V3 right, look at J1's contacts and the crystal Y1 under the magnifier for bridges
  or a lifted pin (solder wick for a bridge). Still nothing: put this board aside and use the second one.
- Step 6, a key that never registers: check its diode, the SOD-123 next to it on the bottom, under the
  magnifier: its cathode band must be on the pad with the silkscreen bar. Turn a reversed one round with the
  iron. Then check the key's four solder joints (hand-soldering).
- Step 6, a key that registers as another one, or several keys at once: a solder bridge, or the phantom press
  of a slow column. Under the magnifier, clear a bridge with solder wick; for a phantom, check that the
  column's 10 k pull-up (R_PU0 to R_PU6, bottom side) is soldered.

## First board

On the first board; step 7.3 of [Flash and test](#flash-and-test) says which checks come before assembly:

- Knob timing: MobiFlight must count every detent of a quick turn
  ([why](../architecture/firmware.md#knob-steps)). It needs a MobiFlight mapping and a running sim, so it can
  wait until [mapping](../using/mapping.md).
  1. Map `FMS_INNER_CW` of both devices to a counter you can read in the sim (for example heading bug +1 in
     MobiFlight).
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
- Lights: judge both behind their light pipes once the panel is assembled.
  - The brightness is `LED_DUTY` in [code.py](../../firmware/code.py): 0x4800 for SHIFT and 0x5500 for UNIT,
    about 28 and 33 % of full. Change those first (up to 0xFFFF).
  - If the console showed "LED drive strength not set" in step 5 of [Flash and test](#flash-and-test), the
    lights stay dimmer at the RP2040's 4 mA default.
  - Only if the white light is still too dim at full duty (a part from the highest forward voltage bin):
    bridge R_UNIT's pads with solder or fit a 0603 0 R (for example C21189) in its place
    ([why](../architecture/electronics.md#lights)), then keep `LED_DUTY[1]` at 0x8000 or less.

## Normal and update mode

In normal use the panel shows up as the two joysticks only: `boot.py` hides the CIRCUITPY drive and the serial
console, so nothing on the PC can write to the firmware. To keep both for an update, hold SHIFT while plugging
in until CIRCUITPY appears (about 2 s; `boot.py` reads SHIFT up to 1 s after power-up, so a short press is
missed). A board without `boot.py` (a fresh CircuitPython install) always shows them. Test and map the
joysticks only after a plain replug ([why](../using/mapping.md#update-mode-and-guids)).

## Updates and recovery

Plug in with SHIFT held until CIRCUITPY appears, copy the changed files to CIRCUITPY (on Linux, run `sync`),
then replug without SHIFT before using MobiFlight. To reach the bootloader without the BOOT pads (for a new
CircuitPython version), plug in the same way, open the serial console, press Ctrl-C, then Enter at "Press
any key to enter the REPL" (CircuitPython's interactive prompt), and run this:

```python
import microcontroller
microcontroller.on_next_reset(microcontroller.RunMode.UF2)
microcontroller.reset()
```

If CircuitPython ever stops booting: bridge the two BOOT pads, under the 5 mm hole in the body floor, with the
tip of the 2 mm hex key or a small screwdriver while plugging in USB, and start again at step 3 of [Flash and
test](#flash-and-test). A new UF2 keeps the files on CIRCUITPY, `boot.py` too; if SHIFT no longer brings the
drive back, copy Raspberry Pi's [`flash_nuke.uf2`](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2)
(it downloads as `nuke_universal.uf2`) to RPI-RP2 first, which erases the whole flash.

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
its header, so the FREQ knob moves to GP12 to GP15 and its push to GP22; the RANGE turn stays on
GP28/GP29 and goes untested there. Wire it up (pins are the GPn numbers, not the header pin numbers; the
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
- Whether the GUIDs (the IDs Windows gives game controllers) differ: do MobiFlight and `joy.cpl` list the
  joysticks as new controllers after a plug-in with SHIFT held
  ([Mapping](../using/mapping.md#update-mode-and-guids))?

`PICO_TEST` puts the SHIFT light on the Pico's own LED and prints the unit instead, so the bench says
nothing about the real lights. Mappings made on the bench do not carry over to the board
([Mapping](../using/mapping.md#update-mode-and-guids)).

[uf2]: https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-9.2.9.uf2
