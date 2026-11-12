# Generators

How the outputs are made: every file in `production/` and `renders/` is generated, by `./build.sh` or by the
scripts one by one. Generated files are named `avionics-panel-rev1-*`.

| Directory | Contents | Start with |
| --- | --- | --- |
| [pcb/](../../pcb/) | board generator: RP2040 on the bottom, 4 layers, routed and checked | [board.py](../../pcb/board.py), [check.py](../../pcb/check.py) |
| [mech/](../../mech/) | body, front plate, knobs, light pipes, key caps, plate artwork | [stack.py](../../mech/stack.py) (every height and fit), [check_fit.py](../../mech/check_fit.py) |
| [firmware/](../../firmware/) | CircuitPython for the panel's RP2040 | [code.py](../../firmware/code.py), [panel.py](../../firmware/panel.py), [buttonmap.py](../../firmware/buttonmap.py) |
| [viewer/](../../viewer/) | three.js 3D view, [live here](https://saschagrunert.de/avionics-panel/) | [index.html](../../viewer/index.html) |
| [production/](../../production/) | the files to order | [Ordering](../building/ordering.md) |
| [renders/](../../renders/) | pictures | |

## Build

`./build.sh` regenerates everything, runs every check and copies the results to `production/` and `renders/`;
`./build.sh --route` re-runs the board routing first. Its sections run in parallel and print their outputs in
a fixed order, the firmware tests with their coverage first. A failed section does not stop the others, and
the build then exits 1; Ctrl-C stops everything. Renders 1 to 4 are screenshots of the 3D view (`#shot-h`,
`#shot-c`, `#shot-e`, `#shot-a` after the URL; `#shot-c` is the clean top view).

## Scripts

The steps one by one, with Nix from the repository root: `nix-shell nix/shells.nix -A <shell>`, then the
script inside its directory. The shells: `gen` (numpy, scipy, matplotlib, pillow, librsvg), `occ`
(OpenCascade, for the exact solids) and `firmware` (pytest, pytest-cov, MicroPython).

| Shell | Directory | Script | Does |
| --- | --- | --- | --- |
| `gen` | `pcb/` | `python3 precheck.py` | placement clearances and bottom-side part bodies |
| `gen` | `pcb/` | `python3 run_route.py 5` | routing, writes `routed.json` ([seeds](#routing-seeds)) |
| `gen` | `pcb/` | `python3 make.py` | Gerbers |
| `gen` | `pcb/` | `python3 check.py` | the electrical and manufacturing checks ([Electronics](electronics.md)) |
| `gen` | `pcb/` | `python3 render.py` | board renders |
| `gen` | `pcb/` | `python3 make_bom.py` | BOM (parts list) and CPL (placement file) |
| `gen` | `pcb/` | `python3 make_schematic.py` | schematic |
| `gen` | `mech/` | `python3 make_plate_art.py` | plate artwork |
| `occ` | `mech/` | `python3 make_caps.py` | key caps |
| `occ` | `mech/` | `python3 make_mech.py` | body, USB-C filler, steel plate DXF |
| `occ` | `mech/` | `python3 make_plate_step.py` | plate STEP and drawing |
| `occ` | `mech/` | `python3 make_knobs.py` | knobs, light pipes |
| `occ` | `mech/` | `python3 check_fit.py` | sections and clearances ([Mechanics](mechanics.md)) |
| `occ` | `mech/` | `python3 make_viewer_data.py` | `viewer/geometry.js`, the dimensions the 3D view takes from the generators |
| `firmware` | repository root | `pytest` | the [firmware tests](firmware.md#code-and-tests) |

## Routing seeds

`run_route.py <seed>` routes the board from a random seed. Seed 5 routes every net without a detour and within
the USB length limits, as do 1, 2, 3, 4, 7, 9, 13 and 14 of seeds 1 to 14. `run_route.py <seed> x` writes
`routed_<seed>.json` instead of `routed.json`, for trying seeds in parallel.

## Nix

Every Nix package comes from the nixpkgs revision locked in `flake.lock`, so a local build and CI write the
same files (STEP, STL, PDF and PNG output depends on the OpenCascade and matplotlib versions).
`nix/nixpkgs.nix` reads the lock without the flakes feature, and `nix/shells.nix` defines the environments
above from it. Dependabot proposes newer nixpkgs-unstable revisions as pull requests (weekly, each at least a
week old), and CI fails on any output that the update changes: run `./build.sh` on that branch and commit what
changed. To move nixpkgs by hand: `nix --extra-experimental-features 'nix-command flakes' flake update
nixpkgs`, then `./build.sh`, and commit `flake.lock` with every output that changed.
