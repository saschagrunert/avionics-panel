#!/usr/bin/env bash
# Regenerate every output, run all checks and copy the results to production/ and renders/.
# Usage: ./build.sh [--route]    --route also re-runs the board routing (seed 8, about half a minute) first.
# Needs Nix (nix-shell) for the Python environments, all from the nixpkgs revision locked in flake.lock
# (read through nix/nixpkgs.nix, so without the flakes feature).
# The independent sections run in parallel. Each one stops at its first failed step. Their outputs are printed
# in the order the sections are listed below, each in one piece once it and the ones before it have ended. The
# build fails (exit 1) if any section failed, after all of them have finished. Ctrl-C stops the sections and
# exits 1.
set -euo pipefail
cd "$(dirname "$0")"
case "${1:-}" in
  "" | --route) ;;
  *)
    echo "usage: ./build.sh [--route]" >&2
    exit 2
    ;;
esac
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 # no __pycache__ races between the sections
# every Nix package (nix/shells.nix, and <nixpkgs> in firmware/mpy-cross.nix) comes from the locked nixpkgs
NIX_PATH="nixpkgs=$(nix-instantiate --eval nix/nixpkgs.nix | tr -d '"')"
export NIX_PATH
SHELLS=$PWD/nix/shells.nix # the environments
# start clean: an output a generator no longer writes must not survive into production/
rm -rf pcb/avionics-panel-rev1-* mech/avionics-panel-rev1-* # (make.py clears pcb/gerbers itself)
gen() { (cd "$1" && nix-shell "$SHELLS" -A gen --run "$2"); }
# without OpenCascade's STEP writer statistics; stderr through the same pipe, so it stays in order
occ() { (cd "$1" && nix-shell "$SHELLS" -A occ --run "$2") 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | { grep -v '^\s*$\|\*\*\|Step File\|Transfer\|WorkSession' || true; }; }

firmware() {
  # (MicroPython, in nix/shells.nix, checks the firmware compiles with MicroPython's parser)
  # CircuitPython 9.2 is built on an older MicroPython: its own mpy-cross is the board's compiler. Not in
  # nixpkgs: firmware/mpy-cross.nix fetches Adafruit's build (pinned by hash) and points it at Nix's glibc
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64 | Linux-aarch64)
      MPY_CROSS=$(nix-build --no-out-link firmware/mpy-cross.nix)/bin/mpy-cross
      export MPY_CROSS REQUIRE_MPY_CROSS=1
      ;;
    *) echo "no pinned CircuitPython mpy-cross for $(uname -sm): the firmware is only checked with MicroPython" >&2 ;;
  esac
  # (--cov measures what .coveragerc names, as a table and as coverage.xml, which CI sends to Codecov)
  REQUIRE_MICROPYTHON=1 nix-shell "$SHELLS" -A firmware \
    --run "pytest -v --cov --cov-report=term-missing --cov-report=xml && cd firmware && python3 make_buttons.py >BUTTONS.md"
}

# Routing goes first and shows its progress: it takes about half a minute, and the board section reads its
# routed.json.
# Nothing else reads the routing (the other sections import board.py, which does not).
BOARD="python3 make.py >/dev/null && python3 check.py && python3 render.py >/dev/null && python3 make_bom.py >/dev/null && python3 make_schematic.py"
if [ "${1:-}" = --route ]; then
  echo "== placement check and routing"
  gen pcb "python3 precheck.py && python3 run_route.py 8"
else
  BOARD="python3 precheck.py && $BOARD"
fi

# section NAME COMMAND...: runs the command in the background, its output in a log of its own. Job control gives
# each section a process group of its own, which stop() below ends as a whole.
LOGS=$(mktemp -d)
trap 'rm -rf "$LOGS"' EXIT
NAMES=()
PIDS=()
section() {
  local i=${#NAMES[@]}
  NAMES+=("$1")
  shift
  set -m
  (
    set +m # and everything the section starts stays in its group
    "$@"
  ) </dev/null >"$LOGS/$i.log" 2>&1 &
  PIDS+=("$!")
  set +m
}
# The sections are not in the terminal's process group, so Ctrl-C reaches only this shell: it ends every
# section's group and waits for them. Nothing outside the build is signalled, so a calling script goes on.
stop() {
  trap '' INT TERM HUP QUIT
  local pid
  for pid in "${PIDS[@]}"; do kill -- "-$pid" 2>/dev/null || true; done
  wait
  echo "stopped" >&2
  exit 1
}
trap stop INT TERM HUP QUIT
# Which generator reads which output: check_fit.py reads the caps (make_caps.py) and the body STL
# (make_mech.py), and builds the knobs, the plate and the plate's legends itself (it imports their generators);
# no other generator reads another one's files.
section "firmware" firmware
section "board" gen pcb "$BOARD"
section "plate artwork" gen mech "python3 make_plate_art.py && rsvg-convert -w 2400 avionics-panel-rev1-plate-preview.svg -o avionics-panel-rev1-plate-preview.png"
section "knobs, light pipes" occ mech "python3 make_knobs.py"
section "caps, body, fits" occ mech "python3 make_caps.py && python3 make_mech.py && python3 check_fit.py"
section "plate, viewer data" occ mech "python3 make_plate_step.py && python3 make_viewer_data.py"

# A failed section does not stop the others: they take seconds, and a run then reports every failed check.
FAILED=()
for i in "${!NAMES[@]}"; do
  if wait "${PIDS[$i]}"; then status=0; else status=$?; fi
  echo "== ${NAMES[$i]}"
  cat "$LOGS/$i.log"
  if [ "$status" != 0 ]; then
    echo "== ${NAMES[$i]}: FAILED (exit $status)"
    FAILED+=("${NAMES[$i]}")
  fi
done
if [ ${#FAILED[@]} -gt 0 ]; then
  printf 'failed: %s\n' "${FAILED[@]}" >&2
  exit 1
fi

echo "== copy"
rm -f production/avionics-panel-rev1-* # a removed output then shows up as a deleted file
cp pcb/avionics-panel-rev1-{BOM,CPL,BOM-full,CPL-full,THT-LCSC}.csv pcb/avionics-panel-rev1-gerbers.zip production/
cp pcb/avionics-panel-rev1-schematic.pdf docs/architecture/
cp mech/avionics-panel-rev1-{body,plate,lightpipes}.step mech/avionics-panel-rev1-knob-*.step \
  mech/avionics-panel-rev1-body.stl mech/avionics-panel-rev1-caps-{A,B,C,D}.zip \
  mech/avionics-panel-rev1-plate.dxf mech/avionics-panel-rev1-plate-drawing.pdf production/
cp pcb/render-front.png renders/5-pcb-top.png
cp pcb/render-back.png renders/6-pcb-bottom.png
cp mech/avionics-panel-rev1-plate-preview.png renders/7-plate-artwork.png
cp mech/fit-check.png renders/8-fit-check.png
echo "done: production/ and renders/ are up to date (renders 1-4 come from the 3D viewer)"
