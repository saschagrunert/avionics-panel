# Avionics Panel [![Firmware test coverage](https://codecov.io/gh/saschagrunert/avionics-panel/graph/badge.svg)](https://codecov.io/gh/saschagrunert/avionics-panel)

DIY desktop panel for GA avionics in flight sims ([G1000][g1000], [GTN 750][gtn750], [GNS 530/430][gns530],
[Bendix/King][bendixking], [GFC 500][gfc500]): autopilot, audio, radio and FMS keys, three dual concentric
knobs and a RANGE knob that tilts to pan. It shows up on the PC as two USB joysticks, mapped in
[MobiFlight][mobiflight].

[![Top view: autopilot keys and ALT/HDG and RANGE knobs left, audio, radio and FMS keys, FREQ and FMS knobs right](renders/2-top.png)](https://saschagrunert.de/avionics-panel/)

<p align="center">
  <a href="https://saschagrunert.de/avionics-panel/">Interactive 3D view</a><br>
  More renders:
  <a href="renders/1-hero.png">hero</a>,
  <a href="renders/2-top.png">top</a>,
  <a href="renders/3-exploded.png">exploded</a>,
  <a href="renders/4-seated.png">seated view</a>,
  <a href="renders/5-pcb-top.png">PCB top</a>,
  <a href="renders/6-pcb-bottom.png">PCB bottom</a><br>
  Resources:
  <a href="renders/7-plate-artwork.png">plate artwork</a>,
  <a href="production/avionics-panel-rev1-plate-drawing.pdf">plate drawing</a>,
  <a href="renders/8-fit-check.png">fit check</a>,
  <a href="docs/architecture/avionics-panel-rev1-schematic.pdf">schematic</a>
</p>

## Build one

The files in [production/](production/) are ready to order. The docs describe ordering from the JLC group
(JLCPCB, JLCCNC, JLC3DP, JLCMC, LCSC), which is a suggestion, not a requirement: other manufacturers can work
from the same files. Ordered that way, the boards arrive fully assembled: nothing to solder, a few checks, then
screws and knobs. Hand-soldering the keys, encoders and RANGE control is an option. The
[build overview](docs/building/README.md) has the steps from ordering to mapping.

## Docs

Using the panel:

- [Controls](docs/using/controls.md): what each key and knob does, [SHIFT](docs/using/controls.md#shift),
  workflows, [knobs](docs/using/controls.md#knobs),
  [keys](docs/using/controls.md#keys-label-shift-legend-in-parentheses)
- [Compatibility](docs/using/compatibility.md): what each control does on the G1000, GFC 500, GTN, GNS and
  Bendix/King, by aircraft
- [Mapping](docs/using/mapping.md): the two joysticks, update mode and GUIDs, the device name

Building one, in build order:

- [Overview](docs/building/README.md): the steps from ordering to mapping
- [Ordering](docs/building/ordering.md): what to order where, the order remarks, the
  [shopping list](docs/building/ordering.md#shopping-list), review questions, shipping
- [Bring-up](docs/building/bring-up.md): checks on arrival, the cap set, flashing, testing, first-board checks,
  updates and recovery, the Pico bench
- [Assembly](docs/building/assembly.md): assembly, disassembly, hand-soldering (an option)

How it works:

- [Electronics](docs/architecture/electronics.md): RP2040 board, USB protection, GPIO map, lights,
  [schematic](docs/architecture/avionics-panel-rev1-schematic.pdf)
- [Firmware](docs/architecture/firmware.md): state, knob timing, switch bounce, USB, tests
- [Mechanics](docs/architecture/mechanics.md): stack, fastening, seating, caps, light pipes, knobs,
  [dimensions](docs/architecture/mechanics.md#dimensions)

Working on the design:

- [Generators](docs/architecture/generators.md): the directories, `./build.sh`, the scripts one by one, the
  locked Nix environment

[g1000]: https://www.garmin.com/en-US/p/588901/
[gtn750]: https://www.garmin.com/en-US/p/67886/
[gns530]: https://www.garmin.com/en-US/p/8052/
[bendixking]: https://www.bendixking.com/
[gfc500]: https://www.garmin.com/en-US/p/604257/
[mobiflight]: https://mobiflight.com/
