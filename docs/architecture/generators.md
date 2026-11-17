# Generators

How the outputs are made: every file in `production/`, renders 5 to 8, the schematic, the fits table in
[Mechanics](mechanics.md#fits), `firmware/BUTTONS.md` and `KEYS.md` and `viewer/geometry.js` are generated,
by `./build.sh` or by the scripts one by one. The files to order and the schematic are named
`avionics-panel-rev1-*`.

| Directory | Contents | Start with |
| --- | --- | --- |
| [pcb/](../../pcb/) | Board generator: RP2040 on the bottom, 4 layers, routed and checked | [board.py](../../pcb/board.py), [check.py](../../pcb/check.py) |
| [mech/](../../mech/) | Body, front plate, knobs, light pipes, key caps, plate artwork | [stack.py](../../mech/stack.py) (the heights and tolerances), [check_fit.py](../../mech/check_fit.py) |
| [firmware/](../../firmware/) | CircuitPython for the panel's RP2040 | [code.py](../../firmware/code.py), [panel.py](../../firmware/panel.py), [buttonmap.py](../../firmware/buttonmap.py) |
| [sim/](../../sim/) | The firmware on stand-in hardware, for the tests and live as a HID device ([Firmware](firmware.md#code-and-tests)) | [\_\_init\_\_.py](../../sim/__init__.py), [hardware.py](../../sim/hardware.py), [live.py](../../sim/live.py) |
| [mobiflight/](../../mobiflight/) | MobiFlight profiles per avionics family or aircraft, joined from avionics parts (autopilot, cockpit, navigators), each a table of sim events, a zip of the parts, a quick-reference card of each profile and MobiFlight's joystick definition of the panel; the `build` workflow puts them on the releases ([Mapping](../using/mapping.md#generated-profiles)) | [profile.py](../../mobiflight/profile.py), [families/part.py](../../mobiflight/families/part.py), [families/parts.py](../../mobiflight/families/parts.py), [families/g1000.py](../../mobiflight/families/g1000.py), [card.py](../../mobiflight/card.py), [joystick.py](../../mobiflight/joystick.py) |
| [viewer/](../../viewer/) | The 3D view (three.js), [live here](https://saschagrunert.de/avionics-panel/), and the panel page: played with the simulator ([sim.js](../../viewer/sim.js)) or in the browser alone, the firmware's `panel.py` in MicroPython ([play.js](../../viewer/play.js), [play.py](../../viewer/play.py)) | [index.html](../../viewer/index.html) |
| [production/](../../production/) | The files to order | [Ordering](../building/ordering.md) |
| [renders/](../../renders/) | Pictures | |

## Build

`./build.sh` regenerates everything, runs every check and copies the results to `production/`, `renders/` and
`docs/architecture/` (the schematic); `./build.sh --route` re-runs the board routing first (a few minutes),
and a failed routing stops the build there, with the routing's own exit status. The sections run in
parallel and print their outputs in a fixed order, the tests first. Their coverage table measures the files
that go on the board ([.coveragerc](../../.coveragerc)), not the simulator, the generators or the profiles.
A failed section does not stop the others, and the build then exits 1; Ctrl-C stops everything. It needs
[Nix](https://nixos.org/download) and is tested only on Linux; on Windows run it in WSL 2.

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
| A legend on a cap or on the plate | `KEY_LEGENDS` and `KNOB_LEGENDS` in [mech/stack.py](../../mech/stack.py) | The caps, the plate artwork, the board's silkscreen, the 3D view and the quick-reference cards read them; `tests/test_labels.py` holds the firmware's names to them |
| What a key, a push or a ring does | Its button in [buttonmap.py](../../firmware/buttonmap.py), its logic in [panel.py](../../firmware/panel.py), its shortcut in [keys.py](../../firmware/keys.py), its legend, and its event in every table of [mobiflight/families/](../../mobiflight/families/) | `./build.sh` rewrites `BUTTONS.md` and `KEYS.md`; [Controls](../using/controls.md) and [Compatibility](../using/compatibility.md) describe it |
| A timing: SHIFT, the repeats, the pulses | The constants at the top of [panel.py](../../firmware/panel.py) | [Controls](../using/controls.md), [Firmware](firmware.md), [Keyboard mode](../using/keyboard.md), [Mapping](../using/mapping.md) and [Simulator](../using/simulator.md) quote them |
| A pin | [code.py](../../firmware/code.py) and its net in [pcb/board.py](../../pcb/board.py) | `tests/test_pins.py` compares the two; the board needs `./build.sh --route` |
| A height, a fit or a tolerance | [mech/stack.py](../../mech/stack.py); the body's own sizes in [make_mech.py](../../mech/make_mech.py) | `check_fit.py` measures the solids against them and rewrites the fits table in [Mechanics](mechanics.md#fits) |
| What a profile sends to the sim | Its parts' tables in [mobiflight/families/](../../mobiflight/families/), joined in [\_\_init\_\_.py](../../mobiflight/families/__init__.py); the rows several parts share in [parts.py](../../mobiflight/families/parts.py) ([how](#adding-an-aircraft-or-a-part)) | `tests/test_mobiflight.py` checks the tables; the `build` workflow publishes the profiles and their cards; a new key event goes into `tests/key_events.txt` once it is found in the SDK's lists of key events, a new H:, L:, B: or A: name into `tests/inputs.txt` under its source once that source names it, and a new source into `SOURCES` in `tests/test_mobiflight.py` and as a heading in `tests/inputs.txt` |

## Scripts

The steps one by one, with Nix from the repository root: `nix-shell nix/shells.nix -A gen` (OpenCascade,
numpy, scipy, matplotlib, pillow, shapely, librsvg), then the script inside its directory. The firmware tests
run in `nix-shell nix/shells.nix -A firmware` (pytest, pytest-cov; on Linux hid-tools, Playwright with its
Chromium for the panel page's script and CircuitPython's `mpy-cross`, whose tests fail there when one is
missing and skip elsewhere). Without Nix these run from the repository root on python3 alone: `pytest` (with
pytest installed; the tests whose tools are missing skip, and `tests/test_simjs.py` also takes Playwright for
Node), `python3 -m sim.page`, `python3 -m mobiflight` and `python3 windows/make_zip.py`.

None of them writes the commit into a committed file, so a commit builds the same outputs. The files users
download name their commit instead: `firmware/version.py` holds a placeholder that git archive fills in with
the commit's date and short hash (`export-subst` in `.gitattributes`, for a release's source code and GitHub's
Download ZIP), and so does `windows/make_zip.py` in the zip, with `-dirty` after the hash for files that are
not committed. The firmware prints it on its console, the page shows it, and the profiles end their name in it
(the `build` workflow fills in `version.py` with git archive before it makes them).

| Directory | Script | Does |
| --- | --- | --- |
| `pcb/` | `python3 precheck.py` | Placement clearances, bottom-side part bodies, mount keep-outs |
| `pcb/` | `python3 run_route.py 7` | Routing, writes `routed.json` for a fully routed board ([seeds](#routing-seeds)) |
| `pcb/` | `python3 make.py` | Gerbers |
| `pcb/` | `python3 make_bom.py` | BOM (parts list) and CPL (placement file) |
| `pcb/` | `python3 check.py` | The electrical and manufacturing checks, on the Gerbers, BOM and CPL ([Electronics](electronics.md)) |
| `pcb/` | `python3 render.py` | Board renders |
| `pcb/` | `python3 make_schematic.py` | Schematic |
| `mech/` | `python3 make_plate_art.py` | Plate artwork; reads its DXF back against the layers it built |
| `mech/` | `python3 make_caps.py` | Key caps; with `--single` also one zip per cap |
| `mech/` | `python3 make_mech.py` | Body |
| `mech/` | `python3 make_plate_step.py` | Plate STEP and its drawing, `plate.pdf`; reads the STEP back against the solid it built, face for face |
| `mech/` | `python3 make_knobs.py` | Knobs, light pipes |
| `mech/` | `python3 check_fit.py` | Sections and clearances, measured on the files ordered and the plate as built ([Mechanics](mechanics.md#fits)); it also writes the fits table there |
| `mech/` | `python3 make_viewer_data.py` | `viewer/geometry.js`, the dimensions the 3D view takes from the generators |
| `firmware/` | `python3 make_buttons.py >BUTTONS.md` | The button numbers of both joysticks, for MobiFlight |
| `firmware/` | `python3 make_keys.py >KEYS.md` | The shortcuts of the [keyboard mode](../using/keyboard.md) |
| Repository root | `pytest` | The [firmware tests](firmware.md#code-and-tests); `tests/test_checkers.py` runs the checkers on known-bad cases and `tests/test_production.py` compares the files in `production/` with each other, both in the gen shell through nix-shell, and they skip without it |
| Repository root | `python3 -m sim.page` | The [simulator](../using/simulator.md): the firmware on the PC, played in the browser |
| Repository root | `python3 -m mobiflight --family g1000` | The MobiFlight profile of a family or aircraft, or of avionics parts, or the parts zip ([Mapping](../using/mapping.md#generated-profiles)); `--stamp` puts any text in place of the commit in its name |
| Repository root | `python3 -m mobiflight --cards cards.zip` | The [quick-reference cards](../using/mapping.md#quick-reference-cards), one page of HTML per profile, and beside each its [cheat sheet](../using/aircraft/README.md) as SVG, both named with the commit as the profiles (`--stamp` too) |
| Repository root | `python3 -m mobiflight --sheets docs/using/aircraft` | The [aircraft cheat sheets](../using/aircraft/README.md), one SVG per profile from `mobiflight/sheet_text.py`; `tests/test_sheet.py` fails while they are out of date |
| Repository root | `python3 -m mobiflight --joystick-definition avionics-panel.joystick.json` | MobiFlight's [joystick definition](../using/mapping.md#button-names-in-mobiflight), which names the buttons |
| Repository root | `python3 windows/make_zip.py` | The simulator's zip for Windows ([Simulator](../using/simulator.md#windows)), with `profile.bat` for the profiles; it writes the commit into the zip's `firmware/version.py` |
| Repository root | `python3 viewer/shots.py` | Renders 1 to 4 and 9, in the `shots` shell |

The scripts share these modules: in `pcb/`, [board.py](../../pcb/board.py) (the board), `geom.py` (distances
between copper items, copper paths, routed lengths), `gerber_io.py` (the Gerber and drill files read back, for
`check.py` and `render.py`, in the format `make.py` writes and no other) and `route.py` (the router, with its
soft costs and keep-outs for this board); in `mech/`, [stack.py](../../mech/stack.py) (the heights and
tolerances) and `occ_util.py` (OpenCascade helpers).

## Adding an aircraft or a part

A profile is a table per device of button names ([buttonmap.py](../../firmware/buttonmap.py)) to MobiFlight
calculator code, written with [rpn.py](../../mobiflight/families/rpn.py), plus every other button with the
reason it sends nothing. Every profile is joined from parts ([part.py](../../mobiflight/families/part.py)), and
every part has a kind, which fixes the buttons it covers (`part.scope()`):

- autopilot: the autopilot keys and their SHIFT functions except HDG's (CRS CTR), UP and DN with and without
  SHIFT, and the ALT/HDG knob's altitude, heading and push;
- cockpit: CRS CTR (SHIFT, HDG), the ALT/HDG knob with SHIFT, the audio panel, the transponder, the lighting,
  and the radios and ADF of both units;
- navigator: a unit's keys and FMS knob, and its map on the RANGE knob (without SHIFT for unit 1, with SHIFT
  for unit 2). One for both units (the G1000's MFD and PFD) or one for each unit (a GNS, a GTN), written for
  unit 1: `part.navigator()` moves its rows to device 2 and to the shifted RANGE buttons for unit 2.

`part.part()` checks that a part's rows and unmapped buttons cover its scope exactly, none twice, and
`part.compose()` that a profile has one autopilot, one cockpit and the navigators of both units. The kinds'
scopes do not overlap (a test checks it), so no button is covered twice. So one part of each kind is always a
whole profile, and parts of different kinds stack as tabs of one MobiFlight project.

To add:

- A part: a module in [families/](../../mobiflight/families/) (or a few rows in
  [parts.py](../../mobiflight/families/parts.py) when it reuses the shared ones), with `part.part()` or
  `part.navigator()`, then one more entry in `AUTOPILOTS`, `COCKPITS` or `NAVIGATORS` in
  [\_\_init\_\_.py](../../mobiflight/families/__init__.py), or for a navigator of one unit its function of
  the unit in `UNIT_NAVIGATORS`. The generator's options and the parts zip follow from there; the parts list in
  [Mapping](../using/mapping.md#avionics-parts) does not, so add the part to it by hand.
- A profile of an avionics family: one line in `FAMILIES`, `compose()` of its parts. Its download needs, in
  [Mapping](../using/mapping.md), a link with its reference at the end of the file and its name in the
  `--family` list of the steps, its card's web link in Quick-reference cards, its words in
  `mobiflight/sheet_text.py` and its cheat sheet's page with its web link in `docs/using/aircraft/` (tests check
  these); a
  line in [Compatibility](../using/compatibility.md) and its name in that page's opening list of profiles; and
  its name in the `start.bat --family` lists of [Simulator](../using/simulator.md#legend) and of
  `windows/README.txt`.
- An aircraft: the same, with `rows=` for what the aircraft does its own way (its lighting, say) and
  `unmapped=` for what it lacks, as the DA40's and the C182T's lines in `FAMILIES` do with the tables in
  [aircraft.py](../../mobiflight/families/aircraft.py). An aircraft that puts any of several navigators in a
  unit, as Black Square's Bonanza by its tablet, joins them there with `part.joined()`: each button sends the
  codes of every one that maps it, in their order; its own rows replace theirs, and its reasons replace those
  of buttons none of them maps. Rows and reasons are written as for unit 1, as for `part.navigator()`
  (`PAN_UP`, not `S_PAN_UP`, for unit 2's map). The Bonanza's module
  ([black_square_bonanza.py](../../mobiflight/families/black_square_bonanza.py)) does that with the GNS, GTN
  and KLN 90B navigators, and joins them to its KFC 150 part and the Bendix/King cockpit with its own rows.
- An event or variable that no profile used before: its line in `tests/key_events.txt` or `tests/inputs.txt`,
  as the table [above](#where-to-change-what) says.

Each module's docstring names the source of its events, and a code that does more than send one event says its
source where it is written. The sources, the most reliable first: the aircraft's or the avionics' own
documentation for home cockpits (Black Square's guide, TDS's "Interfacing with Hardware"); the avionics'
source ([Working Title's](https://github.com/microsoft/msfs-avionics-mirror), MSFS's own instruments); the
MSFS 2024 SDK's key events and simulation variables; then a project the aircraft is flown with, or HubHop's
presets in MobiFlight, which users write, so try them in the sim. Write down in the docstring what is assumed
and not tried.

[tests/test_mobiflight.py](../../tests/test_mobiflight.py) checks every profile and part:

- `test_every_button_is_mapped_or_listed_as_unmapped` and `test_a_part_covers_the_buttons_of_its_kind` hold the
  tables to the button map;
- `test_codes_are_well_formed`, `test_reads_use_the_unit_of_their_kind`, `test_h_events_go_to_their_unit` (add
  the part's or profile's H: prefixes to `PREFIXES`) and the checks of directions, rings and numbers read the
  codes;
- `test_what_every_function_sets` compares each profile with its line in `SETS`: every button, `@2` for device
  2, `=` and what its code sets as `uses()` writes it (the numbers and signs and the events and variables it
  sets, in order; a release after a `/`), on top of the rows `EVERY` holds for all profiles. A new profile
  needs its entry in `SETS`; for a changed row, run the test and copy the found set into the entry once it
  reads right;
- `test_mapping_md_lists_what_does_nothing` compares the profile's "Does nothing in this profile" in
  [Mapping](../using/mapping.md) with its unmapped buttons: a new profile needs its section there and in
  `SECTIONS`, and the groups at the top of the file (`G1000`, `GARMIN`, `BENDIX`) pick the shared tests it runs;
- the workflow tests at the end play the documented steps on the simulated panel and check what the profiles
  send; `run()` works a code as the sim's RPN does, so a code that computes a value gets a test of its own with
  it.

[tests/test_card.py](../../tests/test_card.py) checks the cards, which every profile gets without more work. An
[aircraft request](../../.github/ISSUE_TEMPLATE/aircraft.yml) asks for what a profile needs.

## Routing seeds

`run_route.py <seed>` routes the board from a random seed. It writes `routed.json` only when every net is
routed, none with a detour and the USB pair within its length limits, which is what `check.py` accepts;
otherwise the file stays as it is and the script exits 1. The build uses seed 7. `run_route.py <seed> x`
writes `routed_<seed>.json` instead of `routed.json`, for trying seeds in parallel.

## Nix

Every Nix package comes from the nixpkgs revision locked in `flake.lock`, so a local build on x86-64 Linux
and CI write the same files (most outputs depend on the versions of OpenCascade, matplotlib, shapely and
librsvg, `viewer/geometry.js` and the fits table included).
`nix/nixpkgs.nix` reads the lock without the flakes feature, and `nix/shells.nix` defines the environments
above from it: `gen`, `firmware`, `lint` and `shots`. Dependabot proposes newer nixpkgs-unstable revisions as
pull requests (monthly, each at least a week old), and CI fails on any output that the update changes: run
`./build.sh` on that branch and commit what changed. To move nixpkgs by hand:
`nix --extra-experimental-features 'nix-command flakes' flake update nixpkgs`, then `./build.sh`, and commit
`flake.lock` with every output that changed.
