# The environments build.sh runs the generators and tests in, from the nixpkgs locked in ../flake.lock.
# By hand: nix-shell nix/shells.nix -A gen (or firmware). The CI Nix store cache is keyed on the files in
# this directory.
let
  pkgs = import (import ./nixpkgs.nix) { };
  mpy-cross = import ./mpy-cross.nix pkgs;
  pinned = pkgs.lib.meta.availableOn pkgs.stdenv.hostPlatform mpy-cross;
in
{
  # every generator: the board (pcb/), the plate artwork and the OpenCascade solids (mech/)
  gen = pkgs.mkShell {
    packages = [
      (pkgs.python3.withPackages (
        ps: with ps; [
          pythonocc-core
          numpy
          scipy
          matplotlib
          pillow
          shapely
        ]
      ))
      pkgs.librsvg
    ];
  };
  # The firmware tests and their coverage. Where nix/mpy-cross.nix pins CircuitPython's mpy-cross, the shell
  # has it and its tests must run (REQUIRE_MPY_CROSS); elsewhere the shell says so and they skip. hid-tools
  # (Linux only) parses the report descriptor for tests/test_descriptor.py, which skips without it.
  firmware = pkgs.mkShell {
    packages = [
      (pkgs.python3.withPackages (
        ps:
        with ps;
        [
          pytest
          pytest-cov
        ]
        ++ pkgs.lib.optional pkgs.stdenv.hostPlatform.isLinux (toPythonModule pkgs.hid-tools)
      ))
    ]
    ++ pkgs.lib.optional pinned mpy-cross;
    shellHook =
      if pinned then
        "export REQUIRE_MPY_CROSS=1"
      else
        ''echo "no pinned CircuitPython mpy-cross for ${pkgs.stdenv.hostPlatform.system}: its tests skip" >&2'';
  };
}
