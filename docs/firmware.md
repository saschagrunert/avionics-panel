# Firmware

CircuitPython on the panel's RP2040, in [firmware/](../firmware/).

Every state lives in the firmware and is sent as fixed joystick buttons, so MobiFlight mappings never
need variables or preconditions and can't get out of sync with the panel:

- SHIFT: one-shot for keys, kept through a knob session ([Controls](controls.md#shift)). Shifted
  functions are their own buttons.
- UNIT: the firmware keeps the state and drives the white light. Unit 2 versions of the FMS keys, FMS
  knob, CDI and OBS (a GNS 430 as unit 2 has its own), flip-flops and frequency knob are sent on a
  second USB joystick device: 117 of 128 buttons on device 1, 39 of 64 on device 2 ([BUTTONS.md](../firmware/BUTTONS.md),
  which also says what sends each button). The cockpit lighting behind SHIFT on the FMS knob stays on
  device 1 in either unit. Button numbers are frozen from the first build on: new buttons go at the end
  of a device, retired ones keep their slot. A snapshot test in `firmware/test_panel.py` checks it.
- Frequency knob: the push cycles COM, NAV, ADF, and each mode sends its own turn buttons. For
  avionics that show their own tuning cursor (GNS, GTN) the planned profile maps all modes to the unit's knob
  and the push to its C/V, so the unit keeps the state. For avionics without one (G1000, KX 155/165,
  KR 87) the mode returns to COM 10 s after the last turn or push, so you always start from COM.
- Knob acceleration ([table](controls.md#knobs)), UP / DN auto-repeat and the pan tilt repeat rate
  are done in the firmware.
- Squawk with SHIFT: the outer ring steps the first two digits, the inner ring the last two (octal,
  0 to 7 per digit).
- RANGE: a tilt closes its direction switch and "com"; on a slow tilt "com" can close well before the
  direction. So the centre push (PTR) is sent on release, and only if no direction closed during the
  press. Tilt repeats like UP / DN (first after 300 ms, then every 120 ms).
- Knob detents are button pulses: 56 ms pressed, 56 ms released, so 112 ms per step (about 9 steps per
  second), up to 8 queued per button. MobiFlight polls joysticks from a 20 ms timer, which Windows' 15.6 ms
  clock stretches to about 31 ms, and only sees the state at each poll: press and gap both have to outlast
  a poll, or two detents merge into one. The PC fetches reports every 8 ms (the HID endpoint's interval),
  and both joysticks share that endpoint. With a report still waiting from the previous loop pass and
  both devices changing in the current one, an edge can arrive up to three frames (24 ms) late: a 50 ms
  gap can reach the PC as 26 ms, shorter than a poll. `check_timing` in [panel.py](../firmware/panel.py)
  keeps press and gap at 32 + 3 x 8 = 56 ms or more. A fast spin of a one-step-per-detent knob (FMS, COM
  kHz) can lose steps beyond the 8 queued and runs on for up to 0.9 s. Turning the other way drops the steps
  still queued in the old direction, so the knob stops at once. Measure on the bench whether MobiFlight
  counts every detent of a quick turn: spin the bench encoder (wired as the FMS inner ring, see the end
  of this page) 8 detents quickly and count the steps in the sim, then again in UNIT 2 while UP is held
  (FMS on device 2; UP always sends on device 1 and repeats every 125 ms, so both joysticks share the
  endpoint). On the first board, repeat it with the FMS inner ring and the ALT/HDG knob turning at the
  same time in UNIT 2 (ALT/HDG on device 1). If steps go missing, tune PRESS_MS, GAP_MS and
  MAX_QUEUE in panel.py (a step must not be longer than the 120 ms tilt repeat).
- Errors: if the main loop raises, `code.py` releases every button (the PC keeps the last report
  otherwise, so a key could stay held), prints the traceback, waits 2 s and restarts itself, also when
  printing fails (a `MemoryError` may leave no room to format it). The pause lets
  Ctrl-C on the serial console stop even a crash loop at the REPL. There is no watchdog: every wait in
  the loop is bounded, and a watchdog reset would drop the joysticks off USB and run `boot.py` again.
- USB: reports are only sent while the host has the panel mounted and not suspended. A host that
  enumerates the panel but never reads it (Linux, while no program has the joystick open) makes each
  send wait 2 s and fail. Both joysticks share one USB interface, so they fail alike and share one
  back-off: after a failed send neither device tries for 1 s, then 2, 4 and up to 8 s, so a loop pass
  never stalls for more than 2 s, and in the end the loop stalls for 2 s of every 10. On a Linux bench,
  keep `evtest` or `jstest` open on either joystick (opening one makes the host poll both), or the
  lights and timers stutter.

## Code

[firmware/](../firmware/): `boot.py` sets up the two joysticks, `code.py` reads the hardware, `panel.py`
holds all the logic above, `buttonmap.py` numbers the buttons, `make_buttons.py` (PC only) writes
`BUTTONS.md`. Run `pytest` from the repository root for the host tests: `test_panel.py` covers
`panel.py`, `test_code.py` runs `code.py` against stub hardware modules, `test_boot.py` runs `boot.py`,
`tests/test_pins.py` checks every pin `code.py` uses against the nets in `pcb/board.py`, and
`tests/test_micropython.py` compiles every board file with CircuitPython 9.2's own `mpy-cross`, the
board's compiler, and with the MicroPython unix port from nixpkgs. MicroPython alone is not enough:
CircuitPython 9.2 is built on an older MicroPython, so newer syntax could pass it and still fail on the
board. `mpy-cross` is not in nixpkgs: on Linux x86-64 and ARM64, `build.sh` builds
[firmware/mpy-cross.nix](../firmware/mpy-cross.nix), which fetches Adafruit's 9.2.9 build for those two,
pinned by its hash and points it at the glibc from nixpkgs (the binary expects the usual FHS loader in
`/lib64` or `/lib`, which NixOS lacks); on other systems it prints a notice and that check skips.
`build.sh` also provides MicroPython. Each check skips without its compiler; `build.sh` sets
`REQUIRE_MICROPYTHON=1` and, where it provides `mpy-cross`, `REQUIRE_MPY_CROSS=1`, which turn the skips
into failures. Both check syntax only: a module or argument the board's build lacks shows up on the bench.
Seven `rotaryio` encoders use 7 of the RP2040's 8 PIO state machines; the Pico bench creates all seven
too.
Before the boards arrive, the firmware runs on a plain Raspberry Pi Pico with a few buttons and one
encoder. That also tests the riskiest assumption early: whether MobiFlight tells apart two joysticks
from one USB device that both carry the name "Avionics Panel".

## Install and bring-up

In normal use the panel shows up as the two joysticks only: `boot.py` hides the CIRCUITPY drive and the
serial console, so nothing on the PC can write to the firmware or complain about a drive pulled without
ejecting it. To keep both for an update, hold SHIFT while plugging in and keep it held until CIRCUITPY
appears (about 2 s): CircuitPython waits up to 1 s after power-up (its safe-mode window) before `boot.py`
reads SHIFT, so a short press while plugging in is missed. A board without `boot.py` (a fresh
CircuitPython install) always shows them.

The joysticks also enumerate differently in that mode: with the drive and the console on, they sit on
another USB interface number, so Windows may list them as two more game controllers with their own
DirectInput GUIDs. MobiFlight keys its controllers by that GUID, so test the joysticks and create
mappings only after a plain replug (without SHIFT), and ignore any extra "Avionics Panel" controllers
that show up while SHIFT kept the drive.

The steps are the same for both [assembly variants](ordering.md#assembly-variants), bar the soldering:
an economic board arrives with only the SMD bottom side and gets its J1 tabs and through-hole parts
soldered in steps 1, 4 and 7, the encoders and the RANGE control last, so a board that turns out dead
before then doesn't take the expensive parts with it. A fully assembled board arrives with everything
on: skip the soldering and run the same checks. That protection is lost: a board that fails in step 1 or
2 has its encoders and RANGE control on already (they come off only by desoldering), and the second board
takes over. Do the [arrival checks](mechanics.md#on-arrival) first.

1. Before the first power-up: solder the four J1 shell tabs from the top (economic variant,
   [Mechanics](mechanics.md#hand-soldering); in the full variant check that JLCPCB filled them), look over
   the bottom side (RP2040, USB-C, regulator), then measure VBUS to GND (across C_IN) and 3V3 to GND
   (across C_OUT0); neither may be a short.
2. Plug in USB. With empty flash the RP2040 starts its USB bootloader and shows a drive called RPI-RP2.
   Check that 3V3 reads about 3.3 V across C_OUT0 or one of C_D0 to C_D3.
3. Copy the [CircuitPython 9.2.9 UF2 for the Raspberry Pi Pico][uf2] (same chip, 2 MB flash, 12 MHz
   crystal) to RPI-RP2. The firmware is checked against 9.2.9, the version `mpy-cross.nix` pins; newer
   versions are untested, and the board page on circuitpython.org no longer offers 9.2. The board restarts
   with a CIRCUITPY drive.
4. Economic variant: solder the 28 keys and the two LEDs (seated flat, cathode to the square pad, see
   [Mechanics](mechanics.md#hand-soldering)), but not yet the encoders and the RANGE control: they are
   the expensive parts, and a board that turns out dead in the next steps would take them with it. Full
   variant: nothing to solder.
5. Copy `boot.py`, `code.py`, `panel.py` and `buttonmap.py` to CIRCUITPY, then replug with SHIFT held
   until CIRCUITPY appears: `boot.py` only runs at power-up, and SHIFT keeps the drive and the console.
   CircuitPython only writes to the serial port while a terminal has it open, so what `code.py` printed
   at start-up is already gone: open the console (for example `tio /dev/ttyACM0`), press Ctrl-C
   (`code.py` releases every button and stops) and then Ctrl-D, which runs it again. It prints "Avionics
   Panel rev 1 ready", or, if `boot.py` didn't run, a traceback ending in `RuntimeError: joysticks
   missing: copy boot.py and replug the panel`. Replug without SHIFT: CIRCUITPY and the serial port no
   longer appear. If they still do, SHIFT reads as held (row GP2, column GP6). Test the joysticks only
   from this plain replug on, not in SHIFT mode (see above).
6. Windows "Set up USB game controllers" (joy.cpl) must show two "Avionics Panel" devices, but it only
   shows 32 buttons per device. Check every key and both lights with MobiFlight's input view or a
   DirectInput tester that shows all 128 buttons, against [BUTTONS.md](../firmware/BUTTONS.md). Device 2
   only responds while UNIT 2 is selected (SHIFT, HOME). Both devices show the same name in MobiFlight,
   which keys them by GUID: tell them apart by their button count (128 on device 1, 64 on device 2) or
   with MobiFlight's input scan (a plain AP press comes from device 1, ENT in UNIT 2 from device 2).
   Create the MobiFlight mappings on these two controllers, never on ones that appeared in SHIFT mode.
   Then hold each key and check that the button of the matrix position right below it (same column of
   `MATRIX` in [buttonmap.py](../firmware/buttonmap.py)) stays released: a column that recovers too slowly
   after its row is scanned shows a phantom press there, even where that part isn't fitted yet (economic
   variant: the RANGE control and the encoder pushes). The
   likeliest pairs are UP to DN, DN to RANGE_A (a PAN button) and ENT to the FMS push (FMS_CRSR). Below
   HOME is SHIFT, which sends no button: while HOME is held, the amber light must stay off. If a phantom
   shows up, check that column's pull-up before going on.
7. Economic variant: unplug and solder the three encoders and the RANGE control. Both variants: check
   every ring (direction, outer / inner), the RANGE tilt directions and every push the same way, then the
   [first-board checks](#first-board). Repeat the column check with the parts fitted: hold DN, no PAN
   button; hold ENT, no FMS_CRSR.
8. Later updates: plug in with SHIFT held until CIRCUITPY appears, copy the changed files to CIRCUITPY,
   then replug without SHIFT before using MobiFlight: in SHIFT mode it may see the panel as new
   controllers, and mappings made there would not match the normal ones. To reach the bootloader without
   the BOOT pads (a new CircuitPython version), plug in the same way, open the serial console, press
   Ctrl-C, then Enter at "Press any key to enter the REPL", and run this:

   ```python
   import microcontroller
   microcontroller.on_next_reset(microcontroller.RunMode.UF2)
   microcontroller.reset()
   ```

   If CircuitPython ever stops booting: bridge the BOOT pads through the hole in the case floor while
   plugging in USB, and start again at step 3. A new UF2 keeps the files on CIRCUITPY, `boot.py` too; if
   SHIFT no longer brings the drive back, copy Raspberry Pi's `flash_nuke.uf2` to RPI-RP2 first, which
   erases the whole flash.

### First board

On the first board, after step 7:

- Knob timing with two knobs: spin the FMS inner ring and the ALT/HDG knob at the same time in UNIT 2
  (FMS on device 2, ALT/HDG on device 1) and count the steps in the sim, as in the knob timing at the top
  of this page.
- Phantom presses: a held key must not press the one right below it in its matrix column (UP to DN, DN to
  RANGE_A, ENT to FMS push, HOME to SHIFT: the amber light), steps 6 and 7.
- GP25: the Pico CircuitPython build drives it as its status LED during boot and in safe mode, and here it
  is the FREQ outer encoder's B line (harmless, limited current). Check that the FREQ outer ring counts
  normally once `code.py` runs. A custom board definition would avoid it. Moving that line to the spare
  GP14 was tried: its fan-out is boxed in, and none of 13 router seeds could route it.
- The white UNIT light: if it is too dim, fit 0 R for R_UNIT ([Electronics](electronics.md#lights)). The
  Pico bench can't tell: `PICO_TEST` prints the UNIT state instead of lighting an LED.

### Pico bench

Before the boards arrive, run the firmware on a plain Pico with `PICO_TEST = True` in
[code.py](../firmware/code.py): a plain Pico lacks GP23, GP24, GP25 and GP29 on its header, so the FREQ
knob moves to GP12-15 and its push to GP22; the RANGE encoder still runs on GP28/GP29 but can't be turned
there. Run the same steps as on the board and check:

- Two joysticks in MobiFlight, both named "Avionics Panel": 128 buttons on device 1, 64 on device 2.
- The knob pulse timing (112 ms per step, at the top of this page), also with both joysticks sending at
  once (below).
- Encoder directions, ring order (outer / inner) and the RANGE tilt directions (`PAN_DIRS` in
  [panel.py](../firmware/panel.py)), as far as one bench encoder and the buttons show them.
- Whether the GUIDs differ: do MobiFlight and joy.cpl list the joysticks as new controllers after a
  plug-in with SHIFT held (drive and console on)? See the start of this section.

Pins are the GPn numbers, not the header pin numbers; the keys are matrix positions (row and column in
`MATRIX` in [buttonmap.py](../firmware/buttonmap.py)):

- SHIFT as on the board, a button from GP6 to GP2 (diode anode at GP6), or bridge GP6 to GP2 with a wire
  from plugging in until CIRCUITPY appears: without it the Pico hides its drive as soon as `boot.py` is on
  it.
- UP: a button from GP1 to GP5. HOME: a button from GP6 to GP5 (SHIFT, then HOME toggles UNIT;
  `PICO_TEST` prints the unit). Plain buttons work as long as no three of them are held at once.
- The encoder as the FMS inner ring, whose pins stay the same in `PICO_TEST`: A to GP16, B to GP17,
  common to GND (`rotaryio` pulls A and B up); its push from GP10 to GP0 (FMS push). Use one with 30
  detents and 15 pulses per turn like the PEC11D: `code.py` counts a detent every two quadrature steps
  (`divisor=2`), so a 20 detent / 20 pulse part (common among cheap EC11 and KY-040 encoders) counts each
  detent twice, and the 8-step queue can hide that in the timing check. For such a part set `divisor=4`
  in `code.py` on the bench, and back to 2 for the board.

For the timing check with both joysticks, select UNIT 2, hold UP (device 1, repeating every 125 ms) and
spin the encoder (device 2). After a plain replug the console is off, so the `PICO_TEST` UNIT print is not
visible: UNIT 2 shows as the encoder and HOME sending on device 2 (plain HOME on device 1 means UNIT 1).

[uf2]: https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-9.2.9.uf2
