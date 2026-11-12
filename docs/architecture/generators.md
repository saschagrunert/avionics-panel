# Generators

How the outputs are made: every file in `production/` and renders 5 to 8 are generated, by `./build.sh` or by
the scripts one by one. Generated files are named `avionics-panel-rev1-*`.

| Directory | Contents | Start with |
| --- | --- | --- |
| [pcb/](../../pcb/) | Board generator: RP2040 on the bottom, 4 layers, routed and checked | [board.py](../../pcb/board.py), [check.py](../../pcb/check.py) |
| [mech/](../../mech/) | Body, front plate, knobs, light pipes, key caps, plate artwork | [stack.py](../../mech/stack.py) (the heights and tolerances), [check_fit.py](../../mech/check_fit.py) |
| [firmware/](../../firmware/) | CircuitPython for the panel's RP2040 | [code.py](../../firmware/code.py), [panel.py](../../firmware/panel.py), [buttonmap.py](../../firmware/buttonmap.py) |
| [sim/](../../sim/) | The firmware on stand-in hardware, for the tests and live as a HID device ([Firmware](firmware.md#code-and-tests)) | [\_\_init\_\_.py](../../sim/__init__.py), [hardware.py](../../sim/hardware.py), [live.py](../../sim/live.py) |
| [mobiflight/](../../mobiflight/) | MobiFlight profiles per avionics family, from a table of sim events for each; the `windows` workflow puts them on the releases ([Mapping](../using/mapping.md#generated-profiles)) | [profile.py](../../mobiflight/profile.py), [families/parts.py](../../mobiflight/families/parts.py), [families/g1000.py](../../mobiflight/families/g1000.py) |
| [viewer/](../../viewer/) | The 3D view (three.js), [live here](https://saschagrunert.de/avionics-panel/) | [index.html](../../viewer/index.html) |
| [production/](../../production/) | The files to order | [Ordering](../building/ordering.md) |
| [renders/](../../renders/) | Pictures | |

## Build

`./build.sh` regenerates everything, runs every check and copies the results to `production/` and `renders/`;
`./build.sh --route` re-runs the board routing first (a few minutes). Its sections run in parallel and print
their outputs in a fixed order, the firmware tests with their coverage first. A failed section does not stop
the others, and the build then exits 1; Ctrl-C stops everything. It needs [Nix](https://nixos.org/download)
and is tested only on Linux; on Windows run it in WSL 2.

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

The steps one by one, with Nix from the repository root: `nix-shell nix/shells.nix -A gen` (OpenCascade,
numpy, scipy, matplotlib, pillow, shapely, librsvg), then the script inside its directory. The firmware tests
run in `nix-shell nix/shells.nix -A firmware` (pytest, pytest-cov; on Linux hid-tools and CircuitPython's
`mpy-cross`).

| Directory | Script | Does |
| --- | --- | --- |
| `pcb/` | `python3 precheck.py` | Placement clearances, bottom-side part bodies, mount keep-outs |
| `pcb/` | `python3 run_route.py 1` | Routing, writes `routed.json` for a fully routed board ([seeds](#routing-seeds)) |
| `pcb/` | `python3 make.py` | Gerbers |
| `pcb/` | `python3 make_bom.py` | BOM (parts list) and CPL (placement file) |
| `pcb/` | `python3 check.py` | The electrical and manufacturing checks, on the Gerbers, BOM and CPL ([Electronics](electronics.md)) |
| `pcb/` | `python3 render.py` | Board renders |
| `pcb/` | `python3 make_schematic.py` | Schematic |
| `mech/` | `python3 make_plate_art.py` | Plate artwork |
| `mech/` | `python3 make_caps.py` | Key caps |
| `mech/` | `python3 make_mech.py` | Body |
| `mech/` | `python3 make_plate_step.py` | Plate STEP and drawing |
| `mech/` | `python3 make_knobs.py` | Knobs, light pipes |
| `mech/` | `python3 check_fit.py` | Sections and clearances ([Mechanics](mechanics.md)) |
| `mech/` | `python3 make_viewer_data.py` | `viewer/geometry.js`, the dimensions the 3D view takes from the generators |
| Repository root | `pytest` | The [firmware tests](firmware.md#code-and-tests) |

## Routing seeds

`run_route.py <seed>` routes the board from a random seed. It writes `routed.json` only when every net is
routed, none with a detour and the USB pair within its length limits, which is what `check.py` accepts;
otherwise the file stays as it is and the script exits 1. The build uses seed 1. `run_route.py <seed> x`
writes `routed_<seed>.json` instead of `routed.json`, for trying seeds in parallel.

## Nix

Every Nix package comes from the nixpkgs revision locked in `flake.lock`, so a local build and CI write the
same files (STEP, STL, PDF and PNG output depends on the OpenCascade and matplotlib versions).
`nix/nixpkgs.nix` reads the lock without the flakes feature, and `nix/shells.nix` defines the two environments
above from it. Dependabot proposes newer nixpkgs-unstable revisions as pull requests (weekly, each at least a
week old), and CI fails on any output that the update changes: run `./build.sh` on that branch and commit what
changed. To move nixpkgs by hand: `nix --extra-experimental-features 'nix-command flakes' flake update
nixpkgs`, then `./build.sh`, and commit `flake.lock` with every output that changed.
