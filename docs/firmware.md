# Firmware

CircuitPython on the panel's RP2040, in [firmware/](../firmware/).

Every state lives in the firmware and is sent as fixed joystick buttons, so MobiFlight mappings never
need variables or preconditions and can't get out of sync with the panel:

- SHIFT: one-shot for keys, kept through a knob session ([Controls](controls.md#shift)). Shifted
  functions are their own buttons.
- UNIT: the firmware keeps the state and drives the white light. Unit 2 versions of the FMS keys, FMS
  knob, CDI and OBS (a GNS 430 as unit 2 has its own), flip-flops and frequency knob are sent on a
  second USB joystick device: 117 of 128 buttons on device 1, 44 of 64 on device 2 ([BUTTONS.md](../firmware/BUTTONS.md)).
- Frequency knob: the push cycles COM, NAV, ADF, and each mode sends its own turn buttons. For
  avionics that show their own tuning cursor (GNS, GTN) the profile maps all modes to the unit's knob
  and the push to its C/V, so the unit keeps the state. For avionics without one (G1000, KX 155/165,
  KR 87) the mode returns to COM 10 s after the last turn, so you always start from COM.
- Knob acceleration ([table](controls.md#knobs)), UP / DN auto-repeat and the pan tilt repeat rate
  are done in the firmware.
- Squawk with SHIFT: the outer ring steps the first two digits, the inner ring the last two (octal,
  0 to 7 per digit).
- RANGE: a tilt closes its direction switch and "com"; on a slow tilt "com" can close well before the
  direction. So the centre push (PTR) is sent on release, and only if no direction closed during the
  press. Tilt repeats like UP / DN (first after 300 ms, then every 120 ms).
- Knob detents are button pulses: 40 ms pressed, 25 ms released, up to 12 queued per button. That is
  about 15 steps per second; a fast spin of a one-step-per-detent knob (FMS, COM kHz) can lose steps or
  run on for up to 0.8 s. Measure on the Pico how often MobiFlight samples the buttons and tune
  PRESS_MS, GAP_MS and MAX_QUEUE in [panel.py](../firmware/panel.py).

## Code

[firmware/](../firmware/): `boot.py` sets up the two joysticks, `code.py` reads the hardware, `panel.py`
holds all the logic above, `buttonmap.py` numbers the buttons and writes `BUTTONS.md`. Run `pytest` from
the repository root for the host tests: `test_panel.py` covers `panel.py`, `test_code.py` runs `code.py`
against stub hardware modules. Seven `rotaryio` encoders use 7 of the RP2040's 8 PIO state machines.
Before the boards arrive, the firmware runs on a plain Raspberry Pi Pico with a few buttons and one
encoder. That also tests the riskiest assumption early: whether MobiFlight tells apart two joysticks
from one USB device that both carry the name "Avionics Panel".

## Install and bring-up

1. Before the first power-up: look over the bottom side (RP2040, USB-C, regulator), then measure
   VBUS to GND and 3V3 to GND; neither may be a short.
2. Plug in USB. With empty flash the RP2040 starts its USB bootloader and shows a drive called RPI-RP2.
   Check 3V3 on a test point (C_D0 to C_D3) reads about 3.3 V.
3. Copy the CircuitPython UF2 for the Raspberry Pi Pico (same chip, 2 MB flash, 12 MHz crystal) to
   RPI-RP2. The board restarts with a CIRCUITPY drive.
4. Copy `boot.py`, `code.py`, `panel.py` and `buttonmap.py` to CIRCUITPY, then replug: `boot.py` only
   runs at power-up.
5. Windows "Set up USB game controllers" (joy.cpl) must show two "Avionics Panel" devices. Press every
   key and turn every ring, and compare with [BUTTONS.md](../firmware/BUTTONS.md).
6. If CircuitPython ever stops booting: bridge the BOOT pads through the hole in the case floor while
   plugging in USB, and start again at step 3. Normal updates just copy files to CIRCUITPY.

Before the boards arrive, run the same steps on a plain Pico with `PICO_TEST = True` (see
[Status](status.md#bench-and-first-board)).
