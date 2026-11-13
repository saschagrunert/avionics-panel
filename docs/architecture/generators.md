# Generators

How the outputs are made: every file in `production/`, renders 5 to 8, the schematic and the fits table in
[Mechanics](mechanics.md#fits) are generated, by `./build.sh` or by the scripts one by one. Generated files
are named `avionics-panel-rev1-*`.

| Directory | Contents | Start with |
| --- | --- | --- |
| [pcb/](../../pcb/) | Board generator: RP2040 on the bottom, 4 layers, routed and checked | [board.py](../../pcb/board.py), [check.py](../../pcb/check.py) |
| [mech/](../../mech/) | Body, front plate, knobs, light pipes, key caps, plate artwork | [stack.py](../../mech/stack.py) (the heights and tolerances), [check_fit.py](../../mech/check_fit.py) |
| [firmware/](../../firmware/) | CircuitPython for the panel's RP2040 | [code.py](../../firmware/code.py), [panel.py](../../firmware/panel.py), [buttonmap.py](../../firmware/buttonmap.py) |
| [sim/](../../sim/) | The firmware on stand-in hardware, for the tests and live as a HID device ([Firmware](firmware.md#code-and-tests)) | [\_\_init\_\_.py](../../sim/__init__.py), [hardware.py](../../sim/hardware.py), [live.py](../../sim/live.py) |
| [mobiflight/](../../mobiflight/) | MobiFlight profiles per avionics family, from a table of sim events for each; the `build` workflow puts them on the releases ([Mapping](../using/mapping.md#generated-profiles)) | [profile.py](../../mobiflight/profile.py), [families/parts.py](../../mobiflight/families/parts.py), [families/g1000.py](../../mobiflight/families/g1000.py) |
| [viewer/](../../viewer/) | The 3D view (three.js), [live here](https://saschagrunert.de/avionics-panel/) | [index.html](../../viewer/index.html) |
| [production/](../../production/) | The files to order | [Ordering](../building/ordering.md) |
| [renders/](../../renders/) | Pictures | |

## Build

`./build.sh` regenerates everything, runs every check and copies the results to `production/`, `renders/` and
`docs/architecture/` (the schematic); `./build.sh --route` re-runs the board routing first (a few minutes).
Its sections run in parallel and print their outputs in a fixed order, the firmware tests with their coverage
first. A failed section does not stop the others, and the build then exits 1; Ctrl-C stops everything. It
needs [Nix](https://nixos.org/download) and is tested only on Linux; on Windows run it in WSL 2.

Renders 1 to 4 and 9 are stills of the 3D view, not part of the build:
`nix-shell nix/shells.nix -A shots --run "python3 viewer/shots.py"` writes them, after a change to the view or
to `viewer/geometry.js`.

The linters of the `lint` workflow run in `nix-shell nix/shells.nix -A lint`: `ruff check .`,
`shellcheck build.sh`, `shfmt -d .`, `markdownlint-cli2`,
`lychee --offline --include-fragments --no-progress .`, `typos . .github`, `actionlint` and
`zizmor --offline .` (without `--offline` and with `GH_TOKEN` set, zizmor also asks GitHub about the pinned
actions).

## Where to change what

| To change | Edit | What follows |
| --- | --- | --- |
| A legend on a cap or on the plate | `KEY_LEGENDS` and `KNOB_LEGENDS` in [mech/stack.py](../../mech/stack.py) | The caps, the plate artwork, the board's silkscreen and the 3D view read them; `tests/test_labels.py` holds the firmware's names to them |
| What a key, a push or a ring does | Its button in [buttonmap.py](../../firmware/buttonmap.py), its logic in [panel.py](../../firmware/panel.py), its shortcut in [keys.py](../../firmware/keys.py), its legend, and its event in every table of [mobiflight/families/](../../mobiflight/families/) | `./build.sh` rewrites `BUTTONS.md` and `KEYS.md`; [Controls](../using/controls.md) and [Compatibility](../using/compatibility.md) describe it |
| A timing: SHIFT, the repeats, the pulses | The constants at the top of [panel.py](../../firmware/panel.py) | [Controls](../using/controls.md) and [Firmware](firmware.md) quote them |
| A pin | [code.py](../../firmware/code.py) and its net in [pcb/board.py](../../pcb/board.py) | `tests/test_pins.py` compares the two; the board needs `./build.sh --route` |
| A height, a fit or a tolerance | [mech/stack.py](../../mech/stack.py); the body's own sizes in [make_mech.py](../../mech/make_mech.py) | `check_fit.py` measures the solids against them and rewrites the fits table in [Mechanics](mechanics.md#fits) |
| What a profile sends to the sim | The family's table in [mobiflight/families/](../../mobiflight/families/); the rows several families share in [parts.py](../../mobiflight/families/parts.py) | `tests/test_mobiflight.py` checks the tables; the `build` workflow publishes the profiles |

## Scripts

The steps one by one, with Nix from the repository root: `nix-shell nix/shells.nix -A gen` (OpenCascade,
numpy, scipy, matplotlib, pillow, shapely, librsvg), then the script inside its directory. The firmware tests
run in `nix-shell nix/shells.nix -A firmware` (pytest, pytest-cov; on Linux hid-tools and CircuitPython's
`mpy-cross`, whose tests fail there when either is missing and skip elsewhere).

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
| `mech/` | `python3 make_caps.py` | Key caps; with `--single` also one zip per cap |
| `mech/` | `python3 make_mech.py` | Body |
| `mech/` | `python3 make_plate_step.py` | Plate STEP and its drawing, `plate.pdf` |
| `mech/` | `python3 make_knobs.py` | Knobs, light pipes |
| `mech/` | `python3 check_fit.py` | Sections and clearances; it also writes the fits table in [Mechanics](mechanics.md#fits) |
| `mech/` | `python3 make_viewer_data.py` | `viewer/geometry.js`, the dimensions the 3D view takes from the generators |
| `firmware/` | `python3 make_buttons.py >BUTTONS.md` | The button numbers of both joysticks, for MobiFlight |
| `firmware/` | `python3 make_keys.py >KEYS.md` | The shortcuts of the [keyboard mode](../using/keyboard.md) |
| Repository root | `pytest` | The [firmware tests](firmware.md#code-and-tests); `tests/test_checkers.py` runs the checkers in the gen shell through nix-shell and skips without it |
| Repository root | `python3 -m sim.page` | The [simulator](../using/simulator.md): the firmware on the PC, played in the browser |
| Repository root | `python3 -m mobiflight --family g1000` | The MobiFlight profile of a family ([Mapping](../using/mapping.md#generated-profiles)) |
| Repository root | `python3 windows/make_zip.py` | The simulator's zip for Windows ([Simulator](../using/simulator.md#windows)) |
| Repository root | `python3 viewer/shots.py` | Renders 1 to 4 and 9, in the `shots` shell |

## Routing seeds

`run_route.py <seed>` routes the board from a random seed. It writes `routed.json` only when every net is
routed, none with a detour and the USB pair within its length limits, which is what `check.py` accepts;
otherwise the file stays as it is and the script exits 1. The build uses seed 1. `run_route.py <seed> x`
writes `routed_<seed>.json` instead of `routed.json`, for trying seeds in parallel.

## Nix

Every Nix package comes from the nixpkgs revision locked in `flake.lock`, so a local build on x86-64 Linux
and CI write the same files (STEP, PDF and PNG output depends on the OpenCascade and matplotlib versions).
`nix/nixpkgs.nix` reads the lock without the flakes feature, and `nix/shells.nix` defines the environments
above from it: `gen`, `firmware`, `lint` and `shots`. Dependabot proposes newer nixpkgs-unstable revisions as
pull requests (monthly, each at least a week old), and CI fails on any output that the update changes: run
`./build.sh` on that branch and commit what changed. To move nixpkgs by hand:
`nix --extra-experimental-features 'nix-command flakes' flake update nixpkgs`, then `./build.sh`, and commit
`flake.lock` with every output that changed.
