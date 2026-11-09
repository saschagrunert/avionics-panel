#!/usr/bin/env bash
# Regenerate every output, run all checks and copy the results to production/ and renders/.
# Usage: ./build.sh [--route]    --route also re-runs the board routing (seed 4, about a minute).
# Needs Nix (nix-shell) for the Python environments; stops at the first failed check.
set -euo pipefail
cd "$(dirname "$0")"
GEN='python3.withPackages (ps: with ps; [ numpy scipy matplotlib scikit-image pillow ])'
OCC='python3.withPackages (ps: with ps; [ pythonocc-core numpy matplotlib ])'
gen() { (cd "$1" && nix-shell -p "$GEN" librsvg --run "$2"); }
occ() { (cd "$1" && nix-shell -p "$OCC" --run "$2"); }

echo "== board"
gen pcb "python3 precheck.py"
[ "${1:-}" = "--route" ] && gen pcb "python3 run_route.py 4"
gen pcb "python3 make.py >/dev/null && python3 check.py && python3 render.py >/dev/null && python3 make_bom.py >/dev/null"

echo "== caps, plate artwork"
gen mech "python3 make_caps.py && python3 make_plate_art.py && rsvg-convert -w 2400 avionics-panel-rev1-plate-preview.svg -o avionics-panel-rev1-plate-preview.png"

echo "== body, plate, knobs, fits"
occ mech "python3 make_mech.py && python3 make_plate_step.py && python3 make_knobs.py && python3 check_fit.py" | sed 's/\x1b\[[0-9;]*m//g' | { grep -v '^\s*$\|\*\*\|Step File\|Transfer\|WorkSession' || true; }

echo "== firmware"
(cd firmware && python3 test_panel.py >/dev/null && python3 buttonmap.py > BUTTONS.md && rm -rf __pycache__)
echo "firmware tests passed"

echo "== copy"
cp pcb/avionics-panel-rev1-{BOM.csv,CPL.csv,THT-LCSC.csv,gerbers.zip} production/
cp mech/avionics-panel-rev1-{body,spacer,plate}.step mech/avionics-panel-rev1-{body,spacer}.stl \
   mech/avionics-panel-rev1-knob-* mech/avionics-panel-rev1-lightpipes.* \
   mech/avionics-panel-rev1-caps.{obj,mtl,png,zip} mech/avionics-panel-rev1-plate.dxf \
   mech/avionics-panel-rev1-plate-drawing.pdf production/
cp pcb/render-front.png renders/5-pcb-top.png
cp pcb/render-back.png renders/6-pcb-bottom.png
cp mech/avionics-panel-rev1-plate-preview.png renders/7-plate-artwork.png
cp mech/fit-check.png renders/8-fit-check.png
rm -rf pcb/__pycache__ mech/__pycache__
echo "done: production/ and renders/ are up to date (renders 1-4 come from the 3D viewer)"
