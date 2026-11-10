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
  KR 87) the mode returns to COM 10 s after the last turn, so you always start from COM.
- Knob acceleration ([table](controls.md#knobs)), UP / DN auto-repeat and the pan tilt repeat rate
  are done in the firmware.
- Squawk with SHIFT: the outer ring steps the first two digits, the inner ring the last two (octal,
  0 to 7 per digit).
- RANGE: a tilt closes its direction switch and "com"; on a slow tilt "com" can close well before the
  direction. So the centre push (PTR) is sent on release, and only if no direction closed during the
  press. Tilt repeats like UP / DN (first after 300 ms, then every 120 ms).
- Knob detents are button pulses: 50 ms pressed, 40 ms released, so 90 ms per step (about 11 steps per
  second), up to 8 queued per button. MobiFlight polls joysticks from a 20 ms timer, which Windows' 15.6 ms
  clock stretches to about 31 ms, and only sees the state at each poll: press and gap both have to outlast
  a poll, or two detents merge into one. A fast spin of a one-step-per-detent knob (FMS, COM kHz) can
  lose steps beyond the 8 queued and runs on for up to 0.72 s. Turning the other way drops the steps
  still queued in the old direction, so the knob stops at once. Measure on the bench whether MobiFlight
  counts every detent of a quick turn, and tune PRESS_MS, GAP_MS and MAX_QUEUE in
  [panel.py](../firmware/panel.py) if not (a step must stay shorter than the 120 ms tilt repeat).
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
`tests/test_micropython.py` compiles every board file with the MicroPython unix port (CircuitPython's
parser). It skips when `micropython` is not on the PATH; `build.sh` provides it and sets
`REQUIRE_MICROPYTHON=1`, which turns the skip into a failure. Seven `rotaryio` encoders use 7 of the
RP2040's 8 PIO state machines; the Pico bench creates all seven too.
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

1. Before the first power-up: look over the bottom side (RP2040, USB-C, regulator), then measure
   VBUS to GND (across C_IN) and 3V3 to GND (across C_OUT0); neither may be a short.
2. Plug in USB. With empty flash the RP2040 starts its USB bootloader and shows a drive called RPI-RP2.
   Check that 3V3 reads about 3.3 V across C_OUT0 or one of C_D0 to C_D3.
3. Copy the CircuitPython UF2 for the Raspberry Pi Pico (same chip, 2 MB flash, 12 MHz crystal; from
   [circuitpython.org](https://circuitpython.org/board/raspberry_pi_pico/), version 9 or later) to
   RPI-RP2. The board restarts with a CIRCUITPY drive.
4. Solder the 28 keys and the two LEDs, but not yet the encoders and the RANGE control: they are the
   expensive parts, and a board that turns out dead in the next steps would take them with it.
5. Copy `boot.py`, `code.py`, `panel.py` and `buttonmap.py` to CIRCUITPY, then replug with SHIFT held
   until CIRCUITPY appears: `boot.py` only runs at power-up, and SHIFT keeps the drive and the console.
   The console (for example `tio /dev/ttyACM0`) shows "Avionics Panel rev 1 ready". If `boot.py` didn't
   run, `code.py` stops with a traceback ending in `RuntimeError: joysticks missing: copy boot.py and
   replug the panel`. Replug without SHIFT: CIRCUITPY and the serial port no longer appear. If they
   still do, SHIFT reads as held (row GP2, column GP6). Test the joysticks only from this plain replug
   on, not in SHIFT mode (see above).
6. Windows "Set up USB game controllers" (joy.cpl) must show two "Avionics Panel" devices, but it only
   shows 32 buttons per device. Check every key and both lights with MobiFlight's input view or a
   DirectInput tester that shows all 128 buttons, against [BUTTONS.md](../firmware/BUTTONS.md). Device 2
   only responds while UNIT 2 is selected (SHIFT, HOME). Create the MobiFlight mappings on these two
   controllers, never on ones that appeared in SHIFT mode.
7. Unplug, solder the three encoders and the RANGE control, and check every ring (direction, outer /
   inner), the RANGE tilt directions and every push the same way.
8. Later updates: plug in with SHIFT held until CIRCUITPY appears, copy the changed files to CIRCUITPY,
   then replug without SHIFT before using MobiFlight: in SHIFT mode it may see the panel as new
   controllers, and mappings made there would not match the normal ones. To reach the bootloader without
   the BOOT pads (a new CircuitPython version), plug in the same way and run this in the serial console's
   REPL:

   ```python
   import microcontroller
   microcontroller.on_next_reset(microcontroller.RunMode.UF2)
   microcontroller.reset()
   ```

   If CircuitPython ever stops booting: bridge the BOOT pads through the hole in the case floor while
   plugging in USB, and start again at step 3. A new UF2 keeps the files on CIRCUITPY, `boot.py` too; if
   SHIFT no longer brings the drive back, copy Raspberry Pi's `flash_nuke.uf2` to RPI-RP2 first, which
   erases the whole flash.

Before the boards arrive, run the same steps on a plain Pico with `PICO_TEST = True` (see
[Status](status.md#bench-and-first-board)). Wire SHIFT on the Pico as on the board, a button from GP6
to GP2 (diode anode at GP6), or bridge GP6 to GP2 with a wire from plugging in until CIRCUITPY
appears: without it the Pico hides its drive as soon as `boot.py` is on it.
