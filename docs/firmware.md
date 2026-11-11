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
  counts every detent of a quick turn: map FMS_INNER_CW to a counter you can read in the sim (for example
  heading bug +1 in MobiFlight), spin the bench encoder (wired as the FMS inner ring, see the end of this
  page) 8 detents quickly, and the bug must move by 8°; then again in UNIT 2 while UP is held
  (FMS on device 2; UP always sends on device 1 and repeats every 125 ms, so both joysticks share the
  endpoint). On the first board, repeat it with the FMS inner ring and the ALT/HDG knob turning at the
  same time in UNIT 2 (ALT/HDG on device 1). If steps go missing, tune PRESS_MS, GAP_MS and
  MAX_QUEUE in panel.py (a step must not be longer than the 120 ms tilt repeat).
- Keys and pushes follow the same rule: a quick tap stays pressed for at least 56 ms, and a new press
  of the same button waits until that button has been released for 56 ms. MobiFlight then sees every
  tap, and a fast double tap (CLR twice, a flip-flop) stays two presses. A longer press is sent as long
  as it is held (and 30 ms more, see below); right after a quick tap of the same button it starts up to
  112 ms late, once the tap and its gap are over.
- Switch bounce: the keys are scanned every 20 ms and a press is passed on at the first scan that reads
  it (no added delay). A switch that bounces for longer than a scan shows up as a release and a new
  press one scan later, which the 56 ms minimum press would turn into two presses (AP on and straight
  off again). So a release of a key or push waits 30 ms: a new press of it in that time was a bounce,
  and the press goes on as if never released. A switch that chatters while held stays one press
  throughout: UP and a tilt keep repeating (a repeat due in those 30 ms waits for them, the ones after
  it keep their time), and a shifted push or tilt keeps SHIFT. The 30 ms count from the scans that read
  the release and the press (`keypad.Event.timestamp`), not from the loop pass that picks them up, so a
  pass that waits for the PC can't stretch a bounce past them. CircuitPython 9.2 scans the keys from its
  1/1024 s tick interrupt, so the two scans of such a bounce are about 20 ms apart, more when code that
  runs with interrupts off holds the second one up: `check_timing` keeps the 30 ms at least one and a
  half scans, half a scan to spare. A finger lifts and comes back in no less than about 60 ms, so a real
  double tap stays two presses. The cost: every release reaches the PC 30 ms late, so a held key, UP /
  DN repeat or tilt stops 30 ms later (no extra step), a shifted push or tilt keeps SHIFT for 3 s from
  30 ms after it is let go, and the RANGE centre push sends PTR 30 ms after its release. In those 30 ms
  the push or tilt still counts as held, so a key pressed then doesn't end its SHIFT session and a
  second SHIFT tap then doesn't cancel it (the light stays on and shows it). Only the other hand can do
  that within 30 ms of the release, and until then the release may still turn out a bounce. Presses, the
  SHIFT one-shot and UNIT act on the press and are not delayed. After a keypad overflow, `code.py`
  releases a key whose release was lost at once, without the wait. Raising the keypad's
  `debounce_threshold` instead would delay every press and release by a scan (20 ms) and the recovery
  after a lost event too.
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
  lights and timers stutter. Linux maps at most 80 buttons per joystick, so `evtest` and `jstest` never
  show device 1's buttons 81 to 117: check buttons on Windows, in MobiFlight or a DirectInput tester.

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
that show up while SHIFT kept the drive. Don't add them to MobiFlight's excluded joysticks: that setting
matches by name, so it would exclude both real devices too.

`boot.py` gives the joysticks' HID interface the name "Avionics Panel" as well as the USB product. In
SHIFT mode the panel is a composite device (drive, console and joysticks), and there Windows names a
joystick after its interface, which CircuitPython otherwise calls "CircuitPython HID". Windows also keeps
the first name it saw for a USB ID, and every Pico running CircuitPython shares one (VID 239A, PID 80F4), the
Pico bench included. If joy.cpl or MobiFlight shows "CircuitPython HID" or another old name in step 6,
unplug the panel, delete this registry key (regedit) and plug it in again:

```text
HKEY_CURRENT_USER\System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_239A&PID_80F4
```

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
   (across C_OUT0) with the multimeter; neither may be a short. The bottom silkscreen names only the
   bigger parts: C_IN and C_OUT0 are the two small capacitors right next to the regulator U3 (the
   three-pin part beside J1), C_IN between U3 and J1, C_OUT0 on U3's side towards the board edge. J1's
   metal shell is GND and the easiest place for the black probe.
2. Plug in USB. With empty flash the RP2040 starts its USB bootloader and shows a drive called RPI-RP2.
   Check that 3V3 reads about 3.3 V across C_OUT0 (or from its 3V3 end to J1's shell).
3. Copy the [CircuitPython 9.2.9 UF2 for the Raspberry Pi Pico][uf2] (same chip, 2 MB flash, 12 MHz
   crystal) to RPI-RP2. The firmware is checked against 9.2.9, the version `mpy-cross.nix` pins; newer
   versions are untested, and the board page on circuitpython.org no longer offers 9.2. The board restarts
   with a CIRCUITPY drive.
4. Economic variant: solder the 28 keys and the two LEDs (seated flat, cathode to the square pad, see
   [Mechanics](mechanics.md#hand-soldering)), but not yet the encoders and the RANGE control: they are
   the expensive parts, and a board that turns out dead in the next steps would take them with it. Full
   variant: nothing to solder.
5. Copy `boot.py`, `code.py`, `panel.py` and `buttonmap.py` from the repository to CIRCUITPY (the
   repository's `code.py`, with `PICO_TEST = False` and `divisor=2`, not the copy edited for the Pico
   bench), then replug with SHIFT held until CIRCUITPY appears: `boot.py` only runs at power-up, and SHIFT
   keeps the drive and the console. CircuitPython only writes to the serial port while a terminal has it
   open, so what `code.py` printed at start-up is already gone: open the console (Linux: for example
   `tio /dev/ttyACM0`; Windows: the serial console of Thonny or Mu, or PuTTY on the panel's COM port, which
   Device Manager lists under Ports), press Ctrl-C
   (`code.py` releases every button and stops) and then Ctrl-D, which runs it again. It prints "Avionics
   Panel rev 1 ready", or, if `boot.py` didn't run, a traceback ending in `RuntimeError: joysticks
   missing: copy boot.py and replug the panel`. Replug without SHIFT: CIRCUITPY and the serial port no
   longer appear. If they still do, SHIFT reads as held (row GP2, column GP6). Test the joysticks only
   from this plain replug on, not in SHIFT mode (see above).
6. Windows "Set up USB game controllers" (joy.cpl) must show two "Avionics Panel" devices, but it only
   shows 32 buttons per device. Check every key and both lights with MobiFlight's input view or a
   DirectInput tester that shows all 128 buttons (for example Pointy's Joystick Test), against
   [BUTTONS.md](../firmware/BUTTONS.md). Device 2
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
   button; hold ENT, no FMS_CRSR. A ring that turns the wrong way or swapped rings are fixed in `RINGS` in
   [code.py](../firmware/code.py): flip the ring's reverse flag (the last field, `False` to `True`) for a
   wrong direction, and swap the two ring names (`ALTHDG_OUTER` and `ALTHDG_INNER`, say) if outer and
   inner come out the wrong way round. Copy `code.py` again with SHIFT held. A RANGE tilt direction that
   comes out wrong is fixed in `PAN_DIRS` in [panel.py](../firmware/panel.py).
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
   SHIFT no longer brings the drive back, copy Raspberry Pi's
   [`flash_nuke.uf2`](https://datasheets.raspberrypi.com/soft/flash_nuke.uf2) to RPI-RP2 first, which
   erases the whole flash.

### When bring-up fails

- No RPI-RP2 drive (step 2): try another cable (a charge-only cable shows nothing) and another USB port,
  then measure 3V3 again. With 3V3 right, look at J1's contacts and the crystal Y1 under the magnifier for
  bridges or a lifted pin (solder wick for a bridge). Still nothing: put this board aside and use the
  second one. The bench Pico can also serve as an SWD probe on the board's SWCLK and SWDIO pads (bottom,
  next to the RP2040; GND on J1's shell) with Raspberry Pi's debugprobe firmware, to see whether the
  RP2040 answers at all.
- A key that never registers (step 6): check its diode, the SOD-123 next to it on the bottom, under the
  magnifier: its cathode band must be on the pad with the silk bar. A reversed one is turned round with
  the iron. Then check the key's four solder joints (economic variant).
- A key that registers as another one, or several keys at once: a solder bridge, or the phantom press of a
  slow column (step 6).
- A ring that counts the wrong way or rings swapped: `RINGS` in `code.py` (step 7).

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
- The white UNIT light: judge it behind its light pipe once the panel is assembled. The firmware drives it
  at `LED_DUTY[1]` = 0x3000 in [code.py](../firmware/code.py), about 19 % of full, so raise that first (up
  to 0xFFFF; the SHIFT light uses `LED_DUTY[0]`). Only if it is still too dim at full duty, bridge
  R_UNIT's pads with solder or fit a 0603 0 R (for example C21189, a few cents at LCSC) in its place
  ([Electronics](electronics.md#lights)). The Pico bench can't tell: `PICO_TEST` prints the UNIT state
  instead of lighting an LED.

Then the panel goes together: [Assembly and gluing](mechanics.md#assembly-and-gluing).

### Pico bench

Before the boards arrive, run the firmware on a plain Pico or Pico H (RP2040; not a Pico W, whose radio
uses GP23, GP24, GP25 and GP29, and not a Pico 2, which needs another CircuitPython build) with
`PICO_TEST = True` in
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

Mappings made on the bench don't carry over to the board: the board reports another USB serial
number, so Windows gives its joysticks new DirectInput instance GUIDs, and MobiFlight keys each
controller by that GUID. Map the board's joysticks again.

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
