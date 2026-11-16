# Bring-up

Check the parts on arrival, then flash CircuitPython and the firmware onto the bare board and test every key,
knob and light, before the plate goes on. The tools are in the [shopping list](ordering.md#shopping-list); how
the firmware works is in [Firmware](../architecture/firmware.md). With the hand-soldering option, read
[Hand-soldering](hand-soldering.md#on-arrival-and-bring-up) alongside.

## On arrival

In this order:

1. Rail edge (the long front edge, away from J1, the USB-C socket): check that the rail is gone and both
   corners are round (a 3 mm radius). File a square corner round and sand off a burr.
2. Plate threads: turn one of the M3 screws into each of the five bosses by hand with the 2 mm hex key,
   eleven turns (5.5 mm: about as deep as the screw reaches in use, a turn short of the end of the full
   thread), and out again. It must run freely: a thread that was anodised or holds blasting grit stops it
   early (take it up with JLCCNC). Do not drive it home: without the body it would go past the full thread.
3. Joints the PCBA remark asked for: check that the two mounting lugs of each encoder are soldered in their
   slots (bottom side), and that all four J1 shell tab slots are filled from the top with the solder wetting
   the tabs. If not, solder them ([Soldering](hand-soldering.md#soldering)).
4. Parts: check that the keys, the encoders and the RANGE control sit flat on the board. Reheat the pins of
   one that does not while pressing it down, or use the second board for the panel.
5. Cap set: [choose it](#choosing-the-cap-set).

Solder bridges need no check now: steps 5 and 6 of [Flash and test](#flash-and-test) read every key, ring,
tilt and push.

A board that arrives with a rail anyway, or with a V-cut (scored and snapped) edge that does not fit the body:

1. If the rail is still on, break it off along its score with flat-nose pliers, without bending the board.
2. Take that edge down with a flat file or 240 grit sandpaper on a block until the board drops into the body
   (outdoors or wet: glass-fibre dust).

## Choosing the cap set

The caps come in four sets (A to D, one to four dimples on the bottom) that differ only in their grip
([why](../architecture/mechanics.md#key-caps)). The order has all four in full. Before fitting the caps, try
the AP cap of each set on the AP key of the board (no tools), set B's first, the likeliest to fit: if it
holds, the others need not be tried; if it is too loose, try A, then D; if it is too tight, try C. Stop as
soon as one of the cases below is settled. With the hand-soldering option, try them on a loose key.

- A cap that holds pushes down by hand until it sits on the plunger top (it stops hard there), stays on when
  the board is turned over and does not wobble.
- Too loose: it falls off or rocks. Too tight: it stops short of the plunger top or needs more than a firm
  thumb.
- B holds: fit set B.
- B is too loose: fit the first of A and D that holds. B is too tight: fit C, if it holds.
- Two neighbours miss in opposite directions, the looser one too loose and the tighter one too tight (B too
  tight and C too loose, B too loose and A too tight, or A too loose and D too tight): the print sits between
  them. Try both sets on a few more keys and fit the one that holds on more of them.
- None holds (even C too tight, or even D too loose): in [mech/stack.py](../../mech/stack.py) raise
  `CAP_SETS_MOVE` by 0.1 mm for each set it missed by if C was too tight, or lower it the same way if D was
  too loose (up to 0.3 mm either way), and set both `sets` and `first` in `CAP_ORDER` to that end set, C after
  a raise or D after a lowering. Run [`./build.sh`](../architecture/generators.md#build) and order only that
  set from `production/` (`caps-C.zip` or `caps-D.zip`): after a move, the other sets repeat sizes that
  already missed. Try it the same way; if it still misses, move again (one round may not do).
- If JLC3DP asked for one model per file, the order has set B and only the AP cap of A, C and D as gauges.
  Try them the same way; if a gauge holds where B does not, order that set from the same download as the first
  order, as its `caps-single-*.zip`, and keep set B for the meantime.

The print varies a little from cap to cap. A cap that turns out loose or tight on its own key when the caps
go on takes the same legend from the next tighter or looser set in hand, or is ordered again from that set:
its zip is in `caps-single-<set>.zip` (`cap-A-05-COM-1.zip` and so on). The AP key keeps the cap that held on
it.

## Flash and test

The board arrives with everything on. If one board fails in step 1 or 2, the other takes over (a fault on
both: [When bring-up fails](#when-bring-up-fails)). On Linux, after every copy to RPI-RP2 or CIRCUITPY run
`sync` and let it finish before you replug.

1. Before the first power-up:
   1. Look over the bottom side (RP2040, USB-C, regulator).
   2. With the multimeter's continuity beeper, measure from GND (ground) to both pads of the fuse F1 (VBUS_R
      on J1's side, VBUS_F on the regulator's) and to 3V3 (the 3.3 V supply) at C_OUT0. None may be a short:
      a short beeps without stopping and reads a few ohms or less; a chirp that stops is the capacitors
      charging.
   3. Switch the multimeter to diode mode, red probe on F1's pad on the regulator's side (VBUS_F), black on
      R_DP's outer pad (D+ between U4 and R_DP). A good board reads open or climbs past about 1.5 V (any path
      runs through the regulator, a load and one of U4's diodes in series). A steady 0.5 to 0.8 V from the
      start means U4 is turned by 180°: its GND pin then sits on VBUS_F and a steering diode conducts into D+,
      which the continuity check of step 1.2 does not show as a short. Have U4 replaced before the first
      power-up ([why](../architecture/electronics.md#usb-protection)).

   Where the parts are, board bottom up with J1 at the top edge, as in the
   [render of the bottom](../../renders/6-pcb-bottom.png) (the bottom silkscreen names only the bigger parts,
   and not F1):
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
2. Plug in USB. For the first plug-in of each board, use a current-limited USB supply or a USB power meter
   with a cut-off, set to about 200 mA, if one is at hand. Otherwise plug into a powered hub or a USB charger
   first, not straight into the PC. Unplug at once if anything smells or gets hot: a short behind the fuse
   scorches R_IN, and one on 3V3 heats U3 ([why](../architecture/electronics.md#usb-protection)). Check that
   3V3 reads 3.2 to 3.4 V across C_OUT0 (or from its 3V3 end to J1's shell). On a port with data, the PC's or
   a hub's, the RP2040 starts its USB bootloader with empty flash and shows a drive called RPI-RP2; from a
   charger or a supply without data, plug into the PC once 3V3 is right.
3. Copy the [CircuitPython 9.2.9 UF2 file for the Raspberry Pi Pico][uf2] (same chip, 2 MB flash, 12 MHz
   crystal) to RPI-RP2. The firmware is written for 9.2.9 and tested on the PC against its source; this board
   (or the Pico bench) is its first run on hardware. The board restarts with a CIRCUITPY drive.
4. Copy `boot.py`, `code.py`, `panel.py`, `buttonmap.py`, `keys.py` and `version.py` from
   [firmware/](../../firmware/) to CIRCUITPY (the repository's `code.py`, with `PICO_TEST = False` and
   `divisor=2`, not the copy edited for the Pico bench). Then:
   1. Replug with SHIFT held until CIRCUITPY appears ([update mode](#normal-and-update-mode)): `boot.py` only
      runs at power-up.
   2. Open the serial console (Linux: for example `tio /dev/ttyACM0`; Windows: the serial console of Thonny or
      Mu, or PuTTY on the panel's COM port, which Device Manager lists under Ports). Press Ctrl-C, then
      Ctrl-D: `code.py` runs again and prints "Avionics Panel rev 1 ready" and, in brackets, the version of
      the files: the date and short hash of their commit, as in "(2026-11-14, 5d1c305)". `version.py` holds
      it in the source code of a release and in GitHub's Code, Download ZIP; a git checkout prints "(version
      unknown)", and git log names its commit. A line before it that names a ring "between two detents" means
      that knob was not resting on a detent: turn it to one and press Ctrl-D again. A traceback instead, again
      every 2 s, whose last line says that the joysticks are missing and to copy `boot.py`, means `boot.py` has
      not run: copy it and replug as in step 4.1. "ready" means that it has run.
   3. Replug without SHIFT: CIRCUITPY and the serial port must not appear. If they still do, look at the
      console: "You are in safe mode because:" means CircuitPython skipped `boot.py`
      ([When bring-up fails](#when-bring-up-fails)); otherwise SHIFT reads as held (row GP2, column GP6).
5. Check the joysticks:
   - Windows: "Set up USB game controllers" (`joy.cpl`) must show two "Avionics Panel" devices (if it shows
     another name, see [Mapping](../using/mapping.md#device-name)). It only shows 32 buttons per device, so
     read the buttons in MobiFlight's input view or a DirectInput tester that shows all 128 (for example
     Pointy's Joystick Test).
   - Linux: check the buttons with `hid-recorder`, as `evtest` and `jstest` show only some of them
     ([why](../using/mapping.md#linux)): run `pipx install hid-tools`, then
     `sudo ~/.local/bin/hid-recorder`, and pick "Avionics Panel": each report shows `ReportID: 4` (device 1)
     or `5` (device 2) and a `Button:` list of 0 and 1 in button order. If the lights stay dark, Linux has
     suspended the panel ([Linux](../using/mapping.md#linux)).
   - Check every key against [BUTTONS.md](../../firmware/BUTTONS.md). Device 2 only responds while unit 2 is
     selected (SHIFT, HOME); [Mapping](../using/mapping.md#two-joysticks) says how to tell the two apart.
   - Check the three lights (before the plate goes on, the LEDs shine up through their cutouts in the board).
     Tap SHIFT: the amber light comes on, for 3 s (a second tap meanwhile cancels it). Once it is off, tap
     SHIFT, then HOME: the white UNIT light comes on, unit 2 (the same again goes back to unit 1). Push FREQ
     briefly: after a count of short flashes the green light stays on (NAV); push again and it blinks slowly
     (ADF); push again and it stays off (COM).
   - Column check: a column that recovers too slowly shows a phantom press of the same column in the next
     scanned row ([why](../architecture/electronics.md#gpio-map)). `code.py` scans the rows of `MATRIX` in
     [buttonmap.py](../../firmware/buttonmap.py) in the order 3, 0, 1, 2, 4 (`SCAN_ROWS`), so these are the
     pairs that can show one. Hold the first key of each pair and check that the second stays released:
     - Row 3 to row 0: DN to AP, FLC to ALT, LVL to HDG, SHIFT to MIC1 (see the note after this list), PROC to
       COM1, CLR to CDI, ENT to `COM_SWAP`.
     - Row 0 to row 1: AP to FD, ALT to VNV, HDG to NAV, MIC1 to MIC2, COM1 to COM2, CDI to VFR, `COM_SWAP` to
       `NAV_SWAP`.
     - Row 1 to row 2: FD to UP, VNV to VS, NAV to APR, MIC2 to HOME, COM2 to FPL, VFR to DIRECT, `NAV_SWAP`
       to MENU.
     - Row 2 to row 4: UP to `RANGE_A` (`PAN_UP`), VS to `RANGE_B`, APR to `RANGE_C`, HOME to `RANGE_D` (PAN
       buttons too), FPL to `RANGE_COM`, DIRECT to the ALT/HDG push (`HDG_SYNC`), MENU to the FMS push
       (`FMS_CRSR`). `RANGE_COM` sends PTR only once it opens again: hold FPL for a second and let go, no PTR
       during the hold or after it.

     Row 4 is scanned last: nothing follows it. The worst real case is DN making a phantom AP (GP1, at 168 mm
     the longest column). For SHIFT to MIC1, hold SHIFT alone 1 s: the amber light comes on, then blinks dim
     and bright (locked). If it goes dark instead, a phantom MIC1 went out as `ADF_AUDIO`. Tap SHIFT to unlock
     before going on. If a phantom shows up, check that column's pull-up before going on.
6. Check every ring (direction, outer / inner), the RANGE tilt directions and every push the same way as the
   keys in step 5. If a ring turns the wrong way, flip its reverse flag (the last field, `False` to `True`) in
   `RINGS` in [code.py](../../firmware/code.py). If outer and inner are swapped, swap the two ring names there
   (`ALTHDG_OUTER` and `ALTHDG_INNER`, for example). A wrong RANGE tilt direction is fixed in `PAN_DIRS` in
   [panel.py](../../firmware/panel.py). To load a changed file, plug in with SHIFT held, copy it to
   CIRCUITPY, then replug without SHIFT.

Then the panel goes together: [Putting it together](assembly.md#putting-it-together).

## When bring-up fails

By the step of [Flash and test](#flash-and-test) that shows the fault:

- Step 1, a short or the U4 reading: check the second board the same way. A fault on both is a placement
  error: do not power either board; send JLCPCB photos of both and the readings, and ask for rework.
- Step 2, no RPI-RP2 drive: try another cable (a charge-only cable shows nothing) and another USB port, then
  measure 3V3 again. With 3V3 right, look at J1's contacts and the crystal Y1 under the magnifier for bridges
  or a lifted pin (solder wick for a bridge). Still nothing: put this board aside and use the second one.
- Step 4.1 or later, no CIRCUITPY with SHIFT held or no joysticks in step 5, and the SHIFT, UNIT and FREQ
  lights take turns for a moment after plugging in: HOME, the key above SHIFT, was held instead and switched the
  panel to the keyboard mode. Plug in once with HOME held to switch back
  ([Normal and update mode](#normal-and-update-mode)), then once more with SHIFT held.
- Step 4.2, any other traceback on the console: copy the console output and report it in a GitHub issue, with
  the version line.
- Step 4.3 or later, CIRCUITPY and the console appear without SHIFT, no joysticks, and the console shows "You
  are in safe mode because:": CircuitPython started in safe mode, which skips `boot.py`, after a supply dip
  in its first second or a crash. Unplug for a few seconds and plug in again; if it comes back at every
  plug-in, put this board aside and use the second one.
- Step 5, a key that never registers: check its diode, the SOD-123 next to it on the bottom, under the
  magnifier: its cathode band must be on the pad with the silkscreen bar. Turn a reversed one round with the
  iron. Then check the key's four solder joints.
- Step 5, a key that registers as another one, or several keys at once: a solder bridge, or the phantom press
  of a slow column. Under the magnifier, clear a bridge with solder wick; for a phantom, check that the
  column's 10 k pull-up (R_PU0 to R_PU6, bottom side) is soldered.

## Light brightness

Judge the lights behind their light pipes once the panel is assembled. The brightness is `LED_DUTY` in
[code.py](../../firmware/code.py): 0x4800 for SHIFT, 0x5500 for UNIT and 0x7B00 for FREQ (28, 33 and 48 %), up
to 0xFFFF. The green FREQ LED gives about half the amber's light at the same current, so its duty is
about 1.7 times SHIFT's; push FREQ to NAV to see it lit, and set it to look as bright as the amber light. If
the console showed "LED drive strength not set" in step 4 of [Flash and test](#flash-and-test), the SHIFT or
FREQ light stays dimmer at the RP2040's 4 mA default.

## Normal and update mode

In normal use the panel shows up as the two joysticks only: `boot.py` hides the CIRCUITPY drive and the serial
console, so nothing on the PC can write to the firmware. To keep both for an update, hold SHIFT while plugging
in until CIRCUITPY appears (about 2 s; `boot.py` reads SHIFT up to 1 s after power-up, so a short press is
missed). A board without `boot.py` (a fresh CircuitPython install) always shows them. Test and map the
joysticks only after a plain replug ([why](../using/mapping.md#update-mode-and-guids)).

The HOME key (shift legend UNIT) held while plugging in switches between the joysticks and the
[keyboard mode](../using/keyboard.md), which the panel keeps until it is switched back, also with SHIFT held
for an update. Bring-up uses the joysticks: if the SHIFT, UNIT and FREQ lights take turns after plugging in,
the panel is in keyboard mode.

## Updates and recovery

Plug in with SHIFT held until CIRCUITPY appears, copy the changed files to CIRCUITPY (on Linux, run `sync`),
then replug without SHIFT before using MobiFlight. Copy `version.py` with them, so that the console names the
files' new version (step 4.2 of [Flash and test](#flash-and-test)).

Stay on CircuitPython 9.2.9, the version the firmware is written for: circuitpython.org's Pico page offers
10.x by default, so take the UF2 from the link in step 3 of [Flash and test](#flash-and-test). To install it
again, or if CircuitPython ever stops booting: bridge the two BOOT pads, under the 6.1 mm hole in the body
floor, with the tip of the 2 mm hex key, then connect USB with the bridge held, and start again at step 3. A
new UF2 keeps the files on CIRCUITPY, `boot.py` too; if SHIFT no longer brings the drive back, copy Raspberry
Pi's [`flash_nuke.uf2`](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2) (it downloads as
`nuke_universal.uf2`) to RPI-RP2 first, which erases the whole flash.

## Pico bench

Before the boards arrive, the firmware runs on a plain Raspberry Pi Pico or Pico H with a few buttons and one
encoder. That shows early whether MobiFlight tells apart the two joysticks, which come from one USB device and
both carry the name "Avionics Panel".

Parts:

- A Pico or Pico H (RP2040) with headers, not a Pico W (its radio takes GP23, GP24, GP25 and GP29) and not a
  Pico 2 (RP2350, which needs another CircuitPython build).
- A data-capable micro-USB cable, a breadboard and jumper wires.
- A few push buttons, a 1N4148 diode and three 10 k resistors.
- One cheap EC11-type encoder with push and 30 detents / 15 pulses per turn (not one of the panel's three
  PEC11D).

Set `PICO_TEST = True` in [code.py](../../firmware/code.py): a plain Pico lacks GP23, GP24, GP25 and GP29 on
its header, so the FREQ knob moves to GP12 to GP15 and its push to GP22; the RANGE turn stays on GP28/GP29 and
goes untested there. That leaves no pin for the UNIT and FREQ lights: the console prints the unit and the FREQ
mode instead (UNIT 2, FREQ NAV), and the SHIFT light is the Pico's own LED. Wire it up (pins are the GPn
numbers, not the header pin numbers; the keys are matrix positions, row and column in `MATRIX` in
[buttonmap.py](../../firmware/buttonmap.py)):

- SHIFT as on the board, a button from GP6 to GP2 through the diode (anode at GP6), or bridge GP6 to GP2 with
  a wire from plugging in until CIRCUITPY appears: without it the Pico hides its drive as soon as `boot.py` is
  on it.
- UP: a button from GP1 to GP5. HOME: a button from GP6 to GP5 (SHIFT, then HOME switches the unit). Plain
  buttons work as long as no three of them are held at once.
- A 10 k resistor from each of GP1, GP6 and GP10 to 3V3: the column pull-ups of the board (R_PU0 to R_PU6),
  without which a column recovers too slowly between two rows of a scan and can show phantom presses.
- The encoder as the FMS inner ring, whose pins stay the same in `PICO_TEST`: A to GP16, B to GP17, common to
  GND (`rotaryio` pulls A and B up); its push from GP10 to GP0 (FMS push). `code.py` counts a detent every two
  quadrature steps (`divisor=2`), as the PEC11D's 30 detents and 15 pulses per turn need. A 20 detent / 20
  pulse part (common among cheap EC11 and KY-040 encoders) counts each detent twice, and the 8-step queue can
  hide that when a quick spin is counted. For such a part set `divisor=4` in `code.py` on the bench, and back
  to 2 for the board.

Run steps 3, 4 and 5 of [Flash and test](#flash-and-test) as on the board, step 4 with the bench's `code.py`
(the one edited above), and check:

- Two joysticks in MobiFlight, both named "Avionics Panel": 128 buttons on device 1, 64 on device 2.
- The [knob timing](../using/mapping.md#knob-timing), with the bench encoder as the FMS inner ring:
  MobiFlight must count every detent of a quick spin. For the test with both joysticks, select unit 2, hold
  UP (device 1) and spin the encoder (device 2). After a plain replug the console is off, so unit 2 shows as
  the encoder and HOME sending on device 2 (plain HOME on device 1 means unit 1).
- Encoder directions, ring order (outer / inner) and the RANGE tilt directions (`PAN_DIRS` in
  [panel.py](../../firmware/panel.py)), as far as one bench encoder and the buttons show them.
- Whether the GUIDs (the IDs Windows gives game controllers) differ: do MobiFlight and `joy.cpl` list the
  joysticks as new controllers after a plug-in with SHIFT held
  ([Mapping](../using/mapping.md#update-mode-and-guids))?

`PICO_TEST` puts the SHIFT light on the Pico's own LED and prints the unit instead, so the bench says
nothing about the real lights.

[uf2]: https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-9.2.9.uf2
