# The environments build.sh runs the generators and tests in, from the nixpkgs locked in ../flake.lock.
# By hand: nix-shell nix/shells.nix -A gen (or occ, firmware). The CI Nix store cache is keyed on this file
# too, so a change here reaches the cache (MicroPython, built from source, is not on cache.nixos.org).
let
  pkgs = import (import ./nixpkgs.nix) { };
in
{
  # the board (pcb/) and the plate artwork
  gen = pkgs.mkShell {
    packages = [
      (pkgs.python3.withPackages (
        ps: with ps; [
          numpy
          scipy
          matplotlib
          pillow
        ]
      ))
      pkgs.librsvg
    ];
  };
  # the OpenCascade solids: caps, body, plate, knobs, fit check, viewer data
  occ = pkgs.mkShell {
    packages = [
      (pkgs.python3.withPackages (
        ps: with ps; [
          pythonocc-core
          numpy
          matplotlib
        ]
      ))
    ];
  };
  # The firmware tests. MicroPython (its own test suite fails to build in nixpkgs, so without it) checks the
  # firmware compiles with MicroPython's parser, which CircuitPython uses.
  firmware = pkgs.mkShell {
    packages = [
      (pkgs.python3.withPackages (ps: [ ps.pytest ]))
      (pkgs.micropython.overrideAttrs (_: {
        doCheck = false;
      }))
    ];
  };
}
