# Hand-soldering

An option for those who like to solder. JLCPCB assembles only the bottom side of the board, with every SMD
(surface-mount) part and the two LEDs. The 28 keys, the three encoders and the RANGE control are soldered at
home from the bottom side, the four shell tabs of J1 (the USB-C socket) from the top. JLCPCB then charges
about half the setup and stencil fees and nothing for the through-hole parts and joints. The encoders and the
RANGE control go on last, after the board has been tested, as they are the parts that are hard to remove
again. This page has what differs from [Ordering](ordering.md) and [Bring-up](bring-up.md);
[Soldering](#soldering) also serves rework on a board that JLCPCB assembled.

## Ordering

- Step 2 of [Order step by step](ordering.md#order-step-by-step): only the crystals, no encoders.
- LCSC, at once and as an order and a parcel of its own (LCSC stocks few of the encoders): upload
  `THT-LCSC.csv` to LCSC's BOM tool. It is one board's set: 30 keys (28 and two spares, C589907), 3 encoders
  (C19270361) and 1 RANGE control (C160841); the `Needed` column gives the count per board. Order a second
  set for the spare board if wanted.
- JLCPCB: Standard assembly of the bottom side only, with `BOM.csv` and `CPL.csv` (the BOM step must find all
  25 lines with stock for 2 boards) and no PCBA remark. The PCB settings, the PCB remark, the edge rail and
  the bottom side of the [placement preview](ordering.md#placement-preview) stay the same.
- Locally: the soldering iron, solder, flux, solder wick and the magnifier of the
  [shopping list](ordering.md#shopping-list).

## On arrival and bring-up

[On arrival](bring-up.md#on-arrival): steps 1, 2 and 5 only (the rail edge, the plate threads and the cap
set, tried on a loose key).

[Flash and test](bring-up.md#flash-and-test) runs as written, with three stops for soldering:

1. Before step 1: the four J1 shell tabs.
2. After step 3: unplug, then solder the 28 keys. Steps 4 and 5 test them; the column check of step 5 holds
   even though the encoders and the RANGE control are not on yet.
3. After step 5: unplug, then solder the three encoders and the RANGE control. After step 6, repeat the
   column check for DN, ENT and PROC with the parts fitted.

## Soldering

- J1 shell tabs: solder all four from the top before the first plug-in: flux, then feed solder into each slot
  until it is filled and wets the tab all round. The tabs are on GND (ground) and take the load of the plug
  ([why](../architecture/electronics.md#through-hole-parts)).
- Every part sits flat on the board: solder one pin, check from the side that the part sits flat and square
  (press it down while you reheat that pin if not), then solder the rest. Same for the 28 keys: a tilted key
  tilts its cap in the key hole. Leave the leads untrimmed.
- Encoders: solder the mounting lugs in their slots too; they carry the push of the knobs.
- RANGE control (RKJXT): it may sit off-centre on its pins; the plate leaves it room.
- The RKJXT's COM and ECOM pins are the closest hand-soldered pair on the board (0.38 mm of copper between the
  pads, RANGE_COM and GND): check them for a bridge with a magnifier and a continuity tester. A bridge makes
  COM 1, COM 2, FPL and PROC read pressed all the time, and the RANGE push sends no PTR.
