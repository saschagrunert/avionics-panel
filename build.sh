#!/usr/bin/env bash
# Regenerate every output, run all checks and copy the results to production/ and renders/.
# Usage: ./build.sh [--route]    --route also re-runs the board routing (seed 3, a few minutes).
# Needs Nix (nix-shell) for the Python environments; stops at the first failed check.
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  "" | --route) ;;
  *)
    echo "usage: ./build.sh [--route]" >&2
    exit 2
    ;;
esac
export PYTHONUNBUFFERED=1 # progress shows up as it happens, also through the filters below
# start clean: an output a generator no longer writes must not survive into production/
rm -rf pcb/avionics-panel-rev1-* mech/avionics-panel-rev1-* # (make.py clears pcb/gerbers itself)
GEN='python3.withPackages (ps: with ps; [ numpy scipy matplotlib scikit-image pillow ])'
OCC='python3.withPackages (ps: with ps; [ pythonocc-core numpy matplotlib ])'
gen() { (cd "$1" && nix-shell -p "$GEN" librsvg --run "$2"); }
occ() { (cd "$1" && nix-shell -p "$OCC" --run "$2"); }

echo "== board"
gen pcb "python3 precheck.py"
[ "${1:-}" = "--route" ] && gen pcb "python3 run_route.py 3"
gen pcb "python3 make.py >/dev/null && python3 check.py && python3 render.py >/dev/null && python3 make_bom.py >/dev/null && python3 make_schematic.py"

echo "== plate artwork"
gen mech "python3 make_plate_art.py && rsvg-convert -w 2400 avionics-panel-rev1-plate-preview.svg -o avionics-panel-rev1-plate-preview.png"

echo "== caps, body, plate, knobs, fits"
occ mech "python3 make_caps.py && python3 make_mech.py && python3 make_plate_step.py && python3 make_knobs.py && python3 check_fit.py && python3 make_viewer_data.py" | sed 's/\x1b\[[0-9;]*m//g' | { grep -v '^\s*$\|\*\*\|Step File\|Transfer\|WorkSession' || true; }

echo "== firmware"
# MicroPython (its own test suite fails to build in nixpkgs, so without it) checks the firmware compiles
# with MicroPython's parser, which CircuitPython uses
MPY='(micropython.overrideAttrs (_: { doCheck = false; }))'
# CircuitPython 9.2 is built on an older MicroPython: its own mpy-cross is the board's compiler. Not in
# nixpkgs: firmware/mpy-cross.nix fetches Adafruit's build (pinned by hash) and points it at Nix's glibc
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64 | Linux-aarch64)
    MPY_CROSS=$(nix-build --no-out-link firmware/mpy-cross.nix)/bin/mpy-cross
    export MPY_CROSS REQUIRE_MPY_CROSS=1
    ;;
  *) echo "no pinned CircuitPython mpy-cross for $(uname -sm): the firmware is only checked with MicroPython" >&2 ;;
esac
REQUIRE_MICROPYTHON=1 nix-shell -p "python3.withPackages (ps: [ ps.pytest ])" "$MPY" \
  --run "pytest -v && cd firmware && python3 make_buttons.py >BUTTONS.md && rm -rf __pycache__"

echo "== copy"
rm -f production/avionics-panel-rev1-* # a removed output then shows up as a deleted file
cp pcb/avionics-panel-rev1-{BOM.csv,CPL.csv,THT-LCSC.csv,gerbers.zip} production/
cp pcb/avionics-panel-rev1-schematic.pdf docs/
cp mech/avionics-panel-rev1-{body,plate}.step mech/avionics-panel-rev1-body.stl \
  mech/avionics-panel-rev1-knob-* mech/avionics-panel-rev1-lightpipes.* \
  mech/avionics-panel-rev1-caps-{A,B,C,D}.zip mech/avionics-panel-rev1-caps-single-{A,B,C,D}.zip \
  mech/avionics-panel-rev1-{plate,steel}.dxf \
  mech/avionics-panel-rev1-plate-drawing.pdf production/
cp pcb/render-front.png renders/5-pcb-top.png
cp pcb/render-back.png renders/6-pcb-bottom.png
cp mech/avionics-panel-rev1-plate-preview.png renders/7-plate-artwork.png
cp mech/fit-check.png renders/8-fit-check.png
rm -rf pcb/__pycache__ mech/__pycache__
echo "done: production/ and renders/ are up to date (renders 1-4 come from the 3D viewer)"
