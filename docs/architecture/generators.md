# Generators

How the outputs are made: every file in `production/` and renders 5 to 8 are generated, by `./build.sh` or by
the scripts one by one. Generated files are named `avionics-panel-rev1-*`.

| Directory | Contents | Start with |
| --- | --- | --- |
| [pcb/](../../pcb/) | Board generator: RP2040 on the bottom, 4 layers, routed and checked | [board.py](../../pcb/board.py), [check.py](../../pcb/check.py) |
| [mech/](../../mech/) | Body, front plate, knobs, light pipes, key caps, plate artwork | [stack.py](../../mech/stack.py) (the heights and tolerances), [check_fit.py](../../mech/check_fit.py) |
| [firmware/](../../firmware/) | CircuitPython for the panel's RP2040 | [code.py](../../firmware/code.py), [panel.py](../../firmware/panel.py), [buttonmap.py](../../firmware/buttonmap.py) |
| [sim/](../../sim/) | The firmware on stand-in hardware, for the tests ([Firmware](firmware.md#code-and-tests)) | [\_\_init\_\_.py](../../sim/__init__.py), [hardware.py](../../sim/hardware.py) |
| [viewer/](../../viewer/) | The 3D view (three.js), [live here](https://saschagrunert.de/avionics-panel/) | [index.html](../../viewer/index.html) |
| [production/](../../production/) | The files to order | [Ordering](../building/ordering.md) |
| [renders/](../../renders/) | Pictures | |

## Build

`./build.sh` regenerates everything, runs every check and copies the results to `production/` and `renders/`;
`./build.sh --route` re-runs the board routing first. Its sections run in parallel and print their outputs in
a fixed order, the firmware tests with their coverage first. A failed section does not stop the others, and
the build then exits 1; Ctrl-C stops everything.

Renders 1 to 4 and 9 are stills of the 3D view, not part of the build. Open
[viewer/index.html](../../viewer/index.html) with the fragment after the URL (it hides the page's controls),
at a device pixel ratio of 1 and with the dark colour scheme, and save the picture from the canvas. Load the
page at the final size: a resize after the load shifts the top view by a few pixels.

| Render | Fragment | Viewport (px) |
| --- | --- | --- |
| 1 hero | `#shot-h` | 1800 x 1100 |
| 2 top | `#shot-c` | 2150 x 905 |
| 3 exploded | `#shot-e` | 1800 x 1100 |
| 4 seated | `#shot-a` | 1800 x 1100 |
| 9 bottom | `#shot-b` | 1800 x 1100 |

## Scripts

The steps one by one, with Nix from the repository root: `nix-shell nix/shells.nix -A <shell>`, then the
script inside its directory. The shells: `gen` (numpy, scipy, matplotlib, pillow, librsvg), `occ`
(OpenCascade, for the exact solids) and `firmware` (pytest, pytest-cov, MicroPython).

| Shell | Directory | Script | Does |
| --- | --- | --- | --- |
| `gen` | `pcb/` | `python3 precheck.py` | Placement clearances, bottom-side part bodies, mount keep-outs |
| `gen` | `pcb/` | `python3 run_route.py 8` | Routing, writes `routed.json` for a fully routed board ([seeds](#routing-seeds)) |
| `gen` | `pcb/` | `python3 make.py` | Gerbers |
| `gen` | `pcb/` | `python3 make_bom.py` | BOM (parts list) and CPL (placement file) |
| `gen` | `pcb/` | `python3 check.py` | The electrical and manufacturing checks, on the Gerbers, BOM and CPL ([Electronics](electronics.md)) |
| `gen` | `pcb/` | `python3 render.py` | Board renders |
| `gen` | `pcb/` | `python3 make_schematic.py` | Schematic |
| `gen` | `mech/` | `python3 make_plate_art.py` | Plate artwork |
| `occ` | `mech/` | `python3 make_caps.py` | Key caps |
| `occ` | `mech/` | `python3 make_mech.py` | Body |
| `occ` | `mech/` | `python3 make_plate_step.py` | Plate STEP and drawing |
| `occ` | `mech/` | `python3 make_knobs.py` | Knobs, light pipes |
| `occ` | `mech/` | `python3 check_fit.py` | Sections and clearances ([Mechanics](mechanics.md)) |
| `occ` | `mech/` | `python3 make_viewer_data.py` | `viewer/geometry.js`, the dimensions the 3D view takes from the generators |
| `firmware` | Repository root | `pytest` | The [firmware tests](firmware.md#code-and-tests) |

## Routing seeds

`run_route.py <seed>` routes the board from a random seed. It writes `routed.json` only when every net is
routed, none with a detour and the USB pair within its length limits, which is what `check.py` accepts;
otherwise the file stays as it is and the script exits 1. The build uses seed 8. `run_route.py <seed> x`
writes `routed_<seed>.json` instead of `routed.json`, for trying seeds in parallel.

## Nix

Every Nix package comes from the nixpkgs revision locked in `flake.lock`, so a local build and CI write the
same files (STEP, STL, PDF and PNG output depends on the OpenCascade and matplotlib versions).
`nix/nixpkgs.nix` reads the lock without the flakes feature, and `nix/shells.nix` defines the environments
above from it. Dependabot proposes newer nixpkgs-unstable revisions as pull requests (weekly, each at least a
week old), and CI fails on any output that the update changes: run `./build.sh` on that branch and commit what
changed. To move nixpkgs by hand: `nix --extra-experimental-features 'nix-command flakes' flake update
nixpkgs`, then `./build.sh`, and commit `flake.lock` with every output that changed.
