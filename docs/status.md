# Status

Rev 1 is designed and checked; nothing is ordered yet.

## Before ordering

- Upload the current files to the three quotes (see the [checklist](ordering.md#checklist)).
- JLCCNC reviews the plate before payment. Ask in the remark whether they accept the blind M2.5
  threads (1.2 mm full thread in a 2.2 mm drill, 0.8 mm left to the front), and watch for a flag on the
  0.5 mm webs between the light holes and the SHIFT and UNIT key holes; if they flag those, shrink the
  SHIFT pipe to 1.6 mm and the UNIT pipe to 1.4 mm in [mech/stack.py](../mech/stack.py).

## Bench and first board

- Run the firmware on a Pico first (`PICO_TEST = True` in [code.py](../firmware/code.py): a plain Pico
  lacks GP23, GP24, GP25 and GP29 on its header, so the FREQ knob moves to GP12-15 and its push to GP22,
  and the RANGE turn is left out). Check: two joysticks in MobiFlight, the
  [knob pulse timing](firmware.md), encoder directions, ring order (outer / inner) and the RANGE tilt
  directions (`PAN_DIRS` in [panel.py](../firmware/panel.py)).
- On the first board, check GP25: the Pico CircuitPython build drives it as its status LED during boot
  and in safe mode, and here it is the FREQ outer encoder's B line (harmless, limited current). A custom
  board definition would avoid it.
- Check the white UNIT light; if it is too dim, fit 0 R for R_UNIT ([Electronics](electronics.md#lights)).

## In the sim

- Verify which GTN 750Xi functions TDS exposes as events. HOME, D→ and the knob are bezel controls;
  FPL, PROC, MENU, CLR, ENT, MSG, NRST, TERR, VNAV, CDI and OBS are touchscreen functions on the real
  GTN and only work from the panel if TDS offers events for them.
- One MobiFlight profile per avionics family (G1000, GTN 750Xi, GNS 530/430, Bendix/King, GFC 500/G3X),
  following the [compatibility tables](compatibility.md) and [BUTTONS.md](../firmware/BUTTONS.md).

## Rev 2

- No ESD protection or fuse on USB, common for DIY boards.
- Four 100 nF caps serve the RP2040's six IOVDD pins plus USB_VDD and ADC_AVDD, where Raspberry Pi's
  minimal design has one per IOVDD pin (the 3V3 and GND inner planes make it very likely fine).

## Done

- RANGE footprint checked against JLC's own (C160841), encoder footprint against JLC's own
  (C19270361); LED and resistor part numbers; plate attachment; knob and light-pipe models; rev 1
  firmware; live JLC quotes (2026-11-09).
- Reddit feedback: FD plain with YD shifted, DME audio instead of MKR, CRS and BARO kept behind SHIFT.
- First external review: the regulator, crystal and USB-C footprints are mirrored for the bottom side
  (the USB-C pad row follows JLC's footprint of C165948), the second VBUS pad is tied, SWD debug pads
  and PCB support posts added, key switch changed to TE 1-1825910-4 (the C&K PTS645SL95 is out of
  stock at JLC).
- Encoders changed from the Alps EC11EBB24C03 (not recommended for new designs) to the Bourns
  PEC11D-4120F-S0015.
- Second review: code.py retries a HID report instead of stopping when USB is not ready at power-up,
  the JLCPCB BOM and CPL hold only the bottom side, the body bosses are 0.8 mm thick around the screw
  heads, and the knobs come with tighter and looser bore variants.
