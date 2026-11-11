#!/usr/bin/env bash
# Regenerate every output, run all checks and copy the results to production/ and renders/.
# Usage: ./build.sh [--route]    --route also re-runs the board routing (seed 5, a few minutes) first.
# Needs Nix (nix-shell) for the Python environments, all from the nixpkgs revision locked in flake.lock
# (read through nix/nixpkgs.nix, so without the flakes feature).
# The independent sections run in parallel. Each one stops at its first failed step and prints its output in
# one piece when it ends; the build fails if any section failed, after all of them have finished.
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
  REQUIRE_MICROPYTHON=1 nix-shell "$SHELLS" -A firmware \
    --run "pytest -v && cd firmware && python3 make_buttons.py >BUTTONS.md && rm -rf __pycache__"
}

# Routing goes first and shows its progress: it takes minutes, and the board section reads its routed.json.
# Nothing else reads the routing (the other sections import board.py, which does not).
BOARD="python3 make.py >/dev/null && python3 check.py && python3 render.py >/dev/null && python3 make_bom.py >/dev/null && python3 make_schematic.py"
if [ "${1:-}" = --route ]; then
  echo "== placement check and routing"
  gen pcb "python3 precheck.py && python3 run_route.py 5"
else
  BOARD="python3 precheck.py && $BOARD"
fi

# section NAME COMMAND...: runs the command in the background with its output in a log of its own; the loop
# below prints each log when its section ends
LOGS=$(mktemp -d)
NAMES=()
PIDS=()
section() {
  local i=${#NAMES[@]}
  NAMES+=("$1")
  shift
  set -m # job control: the section gets a process group of its own, which stop() ends as a whole
  (
    set +m # and everything in it stays in that group
    # the command runs as a job of its own, so set -e still holds inside it (an `if` around it would turn
    # set -e off for everything it runs)
    "$@" </dev/null >"$LOGS/$i.log" 2>&1 &
    start=$SECONDS
    if wait $!; then status=0; else status=$?; fi
    echo "$status $((SECONDS - start))" >"$LOGS/$i.tmp"
    mv "$LOGS/$i.tmp" "$LOGS/$i.status"
  ) &
  PIDS+=("$!")
  set +m
}
# The sections do not get the terminal's signals (Ctrl-C, Ctrl-\, a hangup): their process groups are not
# the terminal's, and bash starts background jobs with Ctrl-C ignored. So whenever this shell ends, it ends
# every section's process group first and waits until the groups are empty (at most 5 s, then KILL).
# (Ctrl-Z suspends only this shell; the sections run on.)
running() {
  local pid
  for pid in "${PIDS[@]}"; do if kill -0 -- "-$pid" 2>/dev/null; then return 0; fi; done
  return 1
}
kill_sections() {
  local pid n=0
  for pid in "${PIDS[@]}"; do kill -TERM -- "-$pid" 2>/dev/null || true; done
  wait || true # the sections' own shells; their children (nix-shell, Python workers) end a moment later
  while [ $n -lt 50 ] && running; do
    sleep 0.1
    n=$((n + 1))
  done
  for pid in "${PIDS[@]}"; do kill -KILL -- "-$pid" 2>/dev/null || true; done
  PIDS=()
}
trap 'kill_sections; rm -rf "$LOGS"' EXIT
# stop SIGNAL: end the sections, name the ones that did not finish, then die of the signal, so that a
# calling shell sees it
stop() {
  trap '' INT TERM HUP QUIT
  trap - EXIT
  kill_sections
  for i in "${!NAMES[@]}"; do
    if [ ! -e "$LOGS/$i.status" ]; then echo "stopped: ${NAMES[$i]}" >&2 || true; fi
  done
  rm -rf "$LOGS"
  trap - "$1"
  kill -s "$1" $$
  exit 1 # (not reached)
}
for sig in INT TERM HUP QUIT; do
  # shellcheck disable=SC2064 # the signal's name goes in now
  trap "stop $sig" "$sig"
done
# Which generator reads which output: check_fit.py reads the caps (make_caps.py) and the body STL
# (make_mech.py), and builds the knobs itself; no other generator reads another one's files.
section "board" gen pcb "$BOARD"
section "plate artwork" gen mech "python3 make_plate_art.py && rsvg-convert -w 2400 avionics-panel-rev1-plate-preview.svg -o avionics-panel-rev1-plate-preview.png"
section "knobs, light pipes" occ mech "python3 make_knobs.py"
section "caps, body, fits" occ mech "python3 make_caps.py && python3 make_mech.py && python3 check_fit.py"
section "plate, viewer data" occ mech "python3 make_plate_step.py && python3 make_viewer_data.py"
section "firmware" firmware

# A failed section does not stop the others: they take seconds, and a run then reports every failed check.
FAILED=()
left=${#NAMES[@]}
while [ "$left" -gt 0 ]; do
  for i in "${!NAMES[@]}"; do
    if [ ! -e "$LOGS/$i.status" ] || [ -e "$LOGS/$i.shown" ]; then continue; fi
    read -r status secs <"$LOGS/$i.status"
    echo "== ${NAMES[$i]} (${secs} s)"
    cat "$LOGS/$i.log"
    if [ "$status" != 0 ]; then
      echo "== ${NAMES[$i]}: FAILED (exit $status)"
      FAILED+=("${NAMES[$i]}")
    fi
    touch "$LOGS/$i.shown"
    left=$((left - 1))
  done
  if [ "$left" -gt 0 ]; then sleep 0.2; fi
done
wait
PIDS=() # all ended: nothing for the EXIT trap to stop
if [ ${#FAILED[@]} -gt 0 ]; then
  printf 'failed: %s\n' "${FAILED[@]}" >&2
  exit 1
fi

echo "== copy"
rm -f production/avionics-panel-rev1-* # a removed output then shows up as a deleted file
cp pcb/avionics-panel-rev1-{BOM,CPL,BOM-full,CPL-full,THT-LCSC}.csv pcb/avionics-panel-rev1-gerbers.zip production/
cp pcb/avionics-panel-rev1-schematic.pdf docs/architecture/
cp mech/avionics-panel-rev1-{body,plate,usb-filler}.step mech/avionics-panel-rev1-{body,usb-filler}.stl \
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
