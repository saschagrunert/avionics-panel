# Avionics Panel [![Firmware test coverage](https://codecov.io/gh/saschagrunert/avionics-panel/graph/badge.svg)](https://codecov.io/gh/saschagrunert/avionics-panel)

DIY desktop panel for GA avionics in flight sims ([G1000][g1000], [TDS GTN 750Xi/650Xi][gtnxi],
[GNS 530/430][gns530], [GFC 500][gfc500] with the G3X Touch, [Bendix/King][bendixking] radios with the
[KAP 140][kap140]): autopilot, audio, radio and FMS keys, three dual concentric knobs and a RANGE knob that
tilts to pan. It shows up on the PC as two USB joysticks, mapped in [MobiFlight][mobiflight]; the
[ready profiles](docs/using/mapping.md#generated-profiles) are for MSFS 2024 with MobiFlight 11.2 or newer on
Windows. Its [keyboard mode](docs/using/keyboard.md), not yet tried in MSFS, makes it a USB keyboard for MSFS
on consoles and without MobiFlight.

[![Top view: autopilot keys and ALT/HDG and RANGE knobs left, audio, radio and FMS keys, FREQ and FMS knobs right](renders/2-top.png)](https://saschagrunert.de/avionics-panel/)

<p align="center">
  <a href="https://saschagrunert.de/avionics-panel/">Interactive 3D view</a><br>
  More renders:
  <a href="renders/1-hero.png">hero</a>,
  <a href="renders/2-top.png">top</a>,
  <a href="renders/3-exploded.png">exploded</a>,
  <a href="renders/4-seated.png">seated view</a>,
  <a href="renders/9-bottom.png">bottom</a>,
  <a href="renders/5-pcb-top.png">board top</a>,
  <a href="renders/6-pcb-bottom.png">board bottom</a><br>
  Resources:
  <a href="renders/7-plate-artwork.png">plate artwork</a>,
  <a href="production/avionics-panel-rev1-plate.pdf">plate drawing</a>,
  <a href="renders/8-fit-check.png">fit check</a>,
  <a href="docs/architecture/avionics-panel-rev1-schematic.pdf">schematic</a>
</p>

## Build one

The files in [production/](production/) are ready to order from the JLC group (JLCPCB, JLCCNC, JLC3DP), with
the screws and a few items from a local shop. That is the only supported route; other manufacturers can work
from the same files, unsupported. The boards arrive fully assembled: nothing to solder, a few checks, then
screws and knobs. Hand-soldering the keys, encoders and RANGE control is an option. The
[build overview](docs/building/README.md) has the steps from ordering to mapping.

## Docs

Using the panel:

- [Mapping](docs/using/mapping.md): the ready MobiFlight profiles, and mapping the two joysticks by hand
- [Controls](docs/using/controls.md): what each key and knob does
- [Compatibility](docs/using/compatibility.md): what each control maps to per avionics family and aircraft
- [Keyboard mode](docs/using/keyboard.md): the panel as a keyboard, for MSFS on Xbox and PS5 and without
  MobiFlight
- [Simulator](docs/using/simulator.md): the panel on the PC before the hardware exists,
  [download for Windows][sim-zip]

Building one, in build order:

- [Overview](docs/building/README.md): the steps from ordering to mapping
- [Ordering](docs/building/ordering.md): what to order where, with the
  [shopping list](docs/building/ordering.md#shopping-list)
- [Bring-up](docs/building/bring-up.md): from the parcels to a flashed and tested board
- [Assembly](docs/building/assembly.md): putting the panel together and fitting the knobs
- [Hand-soldering](docs/building/hand-soldering.md): soldering the through-hole parts yourself

How it works:

- [Electronics](docs/architecture/electronics.md): the RP2040 board, with its
  [schematic](docs/architecture/avionics-panel-rev1-schematic.pdf)
- [Firmware](docs/architecture/firmware.md): from keys and knobs to joystick buttons
- [Mechanics](docs/architecture/mechanics.md): plate, body, caps, light pipes and knobs, and their fits

Working on the design:

- [Generators](docs/architecture/generators.md): the scripts behind every file, and `./build.sh`

[g1000]: https://www.garmin.com/en-US/p/588901/
[gtnxi]: https://www.tdssim.com/tdsgtnxi
[gns530]: https://www.garmin.com/en-US/p/8052/
[gfc500]: https://www.garmin.com/en-US/p/604257/
[bendixking]: https://en.wikipedia.org/wiki/Bendix/King
[kap140]: https://www.honeywellaerospace.com/content/dam/bendixking/en/documents/document-lists/downloads-and-manuals/006-18034-0000-KAP-140-Pilots-Guide.pdf
[mobiflight]: https://mobiflight.com/
[sim-zip]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-sim-windows.zip
