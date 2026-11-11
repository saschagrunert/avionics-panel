# Bring-up

Flash CircuitPython and the firmware onto the bare board and test every key, knob and light, before the plate
goes on. Do the [arrival checks](assembly.md#on-arrival) first. How the firmware works is in
[Firmware](../architecture/firmware.md).

## Normal and update mode

In normal use the panel shows up as the two joysticks only: `boot.py` hides the CIRCUITPY drive and the serial
console, so nothing on the PC can write to the firmware or complain about a drive pulled without ejecting it.
To keep both for an update, hold SHIFT while plugging in and keep it held until CIRCUITPY appears (about 2 s):
CircuitPython waits up to 1 s after power-up (its safe-mode window) before `boot.py` reads SHIFT, so a short
press while plugging in is missed. A board without `boot.py` (a fresh CircuitPython install) always shows
them. Test and map the joysticks only after a plain replug ([why](../using/mapping.md#update-mode-and-guids)).

## Steps

The default, fully assembled board arrives with everything on: only the checks below. A board that fails in
step 1 or 2 has its encoders and RANGE control on already, and the second board takes over. With the
hand-soldering option the board gets its J1 tabs and through-hole parts in steps 1, 4 and 7, the encoders and
the RANGE control last, so a board that turns out dead before then doesn't take them with it.

1. Before the first power-up (hand-soldering: first solder the four J1 shell tabs,
   [Assembly](assembly.md#hand-soldering)), look over the bottom side (RP2040, USB-C, regulator), then measure
   VBUS to GND on both pads of the fuse F1 (J1's side and the regulator's) and 3V3 to GND (across C_OUT0) with
   the multimeter; none may be a short. Then switch the multimeter to diode mode, red probe on F1's pad on the
   regulator's side (VBUS_F), black on R_DP's pad towards J1 (D+ between U4 and R_DP). A good board reads open
   or climbs past about 1.5 V (any path runs through the regulator, a load and one of U4's diodes in series).
   A steady 0.5 to 0.8 V from the start means U4 is turned by 180 degrees: its GND pin then sits on VBUS_F and
   a steering diode conducts forward into D+, which the resistance range does not show as a short. Plugged in
   like that, the board burns R_IN open and likely damages U4: have U4 replaced before the first power-up.
   Where the parts are: the bottom silkscreen names only the bigger parts, and not F1. F1 is the largest
   two-pad part on the board (3.2 x 1.6 mm, its pads 3 mm apart), lying along the long edge about 4 mm below
   J1's pad row, between the ESD array U4 (named, the six-pin part right below J1's contacts) and the
   regulator U3 (the three-pin part beside J1). R_IN, a small resistor, lies across the board between J1's pad
   row and F1's pad nearer U4. C_OUT0 is the small capacitor on U3's side towards the board edge. J1's metal
   shell is GND and the easiest place for the black probe.
2. Plug in USB. With empty flash the RP2040 starts its USB bootloader and shows a drive called RPI-RP2. Check
   that 3V3 reads about 3.3 V across C_OUT0 (or from its 3V3 end to J1's shell).
3. Copy the [CircuitPython 9.2.9 UF2 for the Raspberry Pi Pico][uf2] (same chip, 2 MB flash, 12 MHz crystal)
   to RPI-RP2. The firmware is checked against 9.2.9, the version `firmware/mpy-cross.nix` pins; newer
   versions are untested, and the board page on circuitpython.org no longer offers 9.2. The board restarts
   with a CIRCUITPY drive.
4. Hand-soldering only: solder the 28 keys ([seated flat](assembly.md#hand-soldering)), but not yet the
   encoders and the RANGE control.
5. Copy `boot.py`, `code.py`, `panel.py` and `buttonmap.py` from [firmware/](../../firmware/) to CIRCUITPY
   (the repository's `code.py`, with `PICO_TEST = False` and `divisor=2`, not the copy edited for the Pico
   bench), then replug with SHIFT held until CIRCUITPY appears: `boot.py` only runs at power-up, and SHIFT
   keeps the drive and the console. CircuitPython only writes to the serial port while a terminal has it open,
   so what `code.py` printed at start-up is already gone: open the console (Linux: for example `tio
   /dev/ttyACM0`; Windows: the serial console of Thonny or Mu, or PuTTY on the panel's COM port, which Device
   Manager lists under Ports), press Ctrl-C (`code.py` releases every button and stops) and then Ctrl-D, which
   runs it again. It prints "Avionics Panel rev 1 ready", or, if `boot.py` didn't run, a traceback ending in
   `RuntimeError: joysticks missing: copy boot.py and replug the panel`. Replug without SHIFT: CIRCUITPY and
   the serial port no longer appear. If they still do, SHIFT reads as held (row GP2, column GP6).
6. Windows "Set up USB game controllers" (joy.cpl) must show two "Avionics Panel" devices (if it shows another
   name, see [Mapping](../using/mapping.md#device-name)), but it only shows 32 buttons per device. Check every
   key and both lights (before the plate goes on, the LEDs shine up through their cutouts in the board) with
   MobiFlight's input view or a DirectInput tester that shows all 128 buttons (for example Pointy's Joystick
   Test), against [BUTTONS.md](../../firmware/BUTTONS.md). Device 2 only responds while UNIT 2 is selected
   (SHIFT, HOME); [Mapping](../using/mapping.md#two-joysticks) says how to tell the two apart. Then hold each
   key and check that the button of the matrix position right below it (same column of `MATRIX` in
   [buttonmap.py](../../firmware/buttonmap.py)) stays released: a column that recovers too slowly after its
   row is scanned shows a phantom press there, even where that part isn't fitted yet (hand-soldering: the
   RANGE control and the encoder pushes). The likeliest pairs are UP to DN, DN to RANGE_A (a PAN button) and
   ENT to the FMS push (FMS_CRSR). Below HOME is SHIFT, which sends no button: while HOME is held, the amber
   light must stay off. If a phantom shows up, check that column's pull-up before going on.
7. Hand-soldering: unplug and solder the three encoders and the RANGE control first. Both variants: check
   every ring (direction, outer / inner), the RANGE tilt directions and every push the same way, then the
   [first-board checks](#first-board). Repeat the column check with the parts fitted: hold DN, no PAN button;
   hold ENT, no FMS_CRSR. A ring that turns the wrong way or swapped rings are fixed in `RINGS` in
   [code.py](../../firmware/code.py): flip the ring's reverse flag (the last field, `False` to `True`) for a
   wrong direction, and swap the two ring names (`ALTHDG_OUTER` and `ALTHDG_INNER`, say) if outer and inner
   come out the wrong way round. Copy `code.py` again with SHIFT held. A RANGE tilt direction that comes out
   wrong is fixed in `PAN_DIRS` in [panel.py](../../firmware/panel.py).

Then the panel goes together: [Assembly](assembly.md#assembly).

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

If CircuitPython ever stops booting: bridge the two BOOT pads, under the 5 mm hole in the case floor, with the
tip of the 2 mm hex key or a small screwdriver while plugging in USB, and start again at step 3. A new UF2
keeps the files on CIRCUITPY, `boot.py` too; if SHIFT no longer brings the drive back, copy Raspberry Pi's
[`flash_nuke.uf2`](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2) to RPI-RP2 first, which erases the
whole flash.

## When bring-up fails

- No RPI-RP2 drive (step 2): try another cable (a charge-only cable shows nothing) and another USB port, then
  measure 3V3 again. With 3V3 right, look at J1's contacts and the crystal Y1 under the magnifier for bridges
  or a lifted pin (solder wick for a bridge). Still nothing: put this board aside and use the second one. The
  bench Pico can also serve as an SWD probe on the board's SWCLK and SWDIO pads (bottom, next to the RP2040;
  GND on J1's shell) with Raspberry Pi's debugprobe firmware, to see whether the RP2040 answers at all.
- A key that never registers (step 6): check its diode, the SOD-123 next to it on the bottom, under the
  magnifier: its cathode band must be on the pad with the silk bar. A reversed one is turned round with the
  iron. Then check the key's four solder joints (hand-soldering).
- A key that registers as another one, or several keys at once: a solder bridge, or the phantom press of a
  slow column (step 6).
- A ring that counts the wrong way or rings swapped: `RINGS` in `code.py` (step 7).

## First board

On the first board, after step 7:

- Knob timing: MobiFlight must count every detent of a quick turn
  ([why](../architecture/firmware.md#knob-steps)). It needs a MobiFlight mapping and a running sim, so it can
  wait until [mapping](../using/mapping.md). Map FMS_INNER_CW to a counter you can read in the sim (for
  example heading bug +1 in MobiFlight), spin the FMS inner ring 8 detents quickly, and the bug must move by
  8°. Repeat in UNIT 2 while UP is held (FMS on device 2, UP repeating on device 1), and with the FMS inner
  ring and the ALT/HDG knob turning at the same time in UNIT 2 (ALT/HDG on device 1). If steps go missing,
  tune `PRESS_MS`, `GAP_MS` and `MAX_QUEUE` in [panel.py](../../firmware/panel.py) (a step must not be longer
  than the 120 ms tilt repeat).
- Phantom presses: a held key must not press the one right below it in its matrix column (UP to DN, DN to
  RANGE_A, ENT to the FMS push, HOME to SHIFT: the amber light), steps 6 and 7.
- GP25: the Pico CircuitPython build drives it as its status LED during boot and in safe mode, and here it is
  the FREQ outer encoder's B line (harmless, limited current). Check that the FREQ outer ring counts normally
  once `code.py` runs.
- The lights: judge both behind their light pipes once the panel is assembled. If the console (step 5) shows
  "LED drive strength not set", the lights stay dimmer at the RP2040's 4 mA default. The brightness is
  `LED_DUTY` in [code.py](../../firmware/code.py): 0x4800 for SHIFT and 0x4000 for UNIT, about 28 and 25 % of
  full; change those first (up to 0xFFFF). Only if the white light is still too dim at full duty (a part from
  the highest forward voltage bin), bridge R_UNIT's pads with solder or fit a 0603 0 R (for example C21189) in
  its place ([Electronics](../architecture/electronics.md#lights)), then keep `LED_DUTY[1]` at 0x8000 or less.

## Pico bench

Before the boards arrive, the firmware runs on a plain Raspberry Pi Pico or Pico H with a few buttons and one
encoder. That also tests the riskiest assumption early: whether MobiFlight tells apart two joysticks from one
USB device that both carry the name "Avionics Panel".

Parts: a Pico or Pico H (RP2040) with headers, not a Pico W (its radio takes GP23, GP24, GP25 and GP29) and
not a Pico 2 (RP2350, which needs another CircuitPython build); a data-capable micro-USB cable, a breadboard
and jumper wires, a few push buttons, one cheap EC11-type encoder with push and 30 detents / 15 pulses per
turn (not one of the panel's three PEC11D), and a 1N4148 diode.

Set `PICO_TEST = True` in [code.py](../../firmware/code.py): a plain Pico lacks GP23, GP24, GP25 and GP29 on
its header, so the FREQ knob moves to GP12 to GP15 and its push to GP22; the RANGE encoder still runs on
GP28/GP29 but can't be turned there. Wire it up (pins are the GPn numbers, not the header pin numbers; the
keys are matrix positions, row and column in `MATRIX` in [buttonmap.py](../../firmware/buttonmap.py)):

- SHIFT as on the board, a button from GP6 to GP2 through the diode (anode at GP6), or bridge GP6 to GP2 with
  a wire from plugging in until CIRCUITPY appears: without it the Pico hides its drive as soon as `boot.py` is
  on it.
- UP: a button from GP1 to GP5. HOME: a button from GP6 to GP5 (SHIFT, then HOME toggles UNIT). Plain buttons
  work as long as no three of them are held at once.
- The encoder as the FMS inner ring, whose pins stay the same in `PICO_TEST`: A to GP16, B to GP17, common to
  GND (`rotaryio` pulls A and B up); its push from GP10 to GP0 (FMS push). Use one with 30 detents and 15
  pulses per turn like the PEC11D: `code.py` counts a detent every two quadrature steps (`divisor=2`), so a 20
  detent / 20 pulse part (common among cheap EC11 and KY-040 encoders) counts each detent twice, and the
  8-step queue can hide that in the timing check. For such a part set `divisor=4` in `code.py` on the bench,
  and back to 2 for the board.

Run steps 3, 5 and 6 as on the board and check:

- Two joysticks in MobiFlight, both named "Avionics Panel": 128 buttons on device 1, 64 on device 2.
- The knob timing as on the [first board](#first-board), with the bench encoder as the FMS inner ring. For the
  test with both joysticks, select UNIT 2, hold UP (device 1) and spin the encoder (device 2). After a plain
  replug the console is off, so UNIT 2 shows as the encoder and HOME sending on device 2 (plain HOME on device
  1 means UNIT 1).
- Encoder directions, ring order (outer / inner) and the RANGE tilt directions (`PAN_DIRS` in
  [panel.py](../../firmware/panel.py)), as far as one bench encoder and the buttons show them.
- Whether the GUIDs differ: do MobiFlight and joy.cpl list the joysticks as new controllers after a plug-in
  with SHIFT held ([Mapping](../using/mapping.md#update-mode-and-guids))?

`PICO_TEST` puts the SHIFT light on the Pico's own LED and prints the UNIT state instead, so the bench says
nothing about the real lights. Mappings made on the bench don't carry over to the board
([Mapping](../using/mapping.md#update-mode-and-guids)).

[uf2]: https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-9.2.9.uf2
