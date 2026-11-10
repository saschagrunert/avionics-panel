# CircuitPython 9.2's mpy-cross, the board's compiler (tests/test_micropython.py checks the firmware with
# it). Not in nixpkgs: Adafruit's 9.2.9 build, pinned by its hash. Despite the ".static" in its name it is
# linked against glibc and expects the usual FHS loader (/lib64 or /lib: /lib64/ld-linux-x86-64.so.2,
# /lib/ld-linux-aarch64.so.1), which NixOS lacks, so autoPatchelf points it at the glibc from nixpkgs.
# build.sh builds it with nix-build.
let
  pkgs = import <nixpkgs> { };
  builds = {
    x86_64-linux = {
      file = "linux-amd64/mpy-cross-linux-amd64-9.2.9.static";
      sha256 = "02zwg4b3z4vrzxip2dx9n12hqrwgs690h7b8pavirvva07f06dcq";
    };
    aarch64-linux = {
      file = "linux-aarch64/mpy-cross-linux-aarch64-9.2.9.static-aarch64";
      sha256 = "16bl9vmj4js8jpw6ybs6fd2n14mia9wxiisz1isdqplyszlfkkd5";
    };
  };
  system = pkgs.stdenv.hostPlatform.system;
  build = builds.${system} or (throw "no pinned CircuitPython mpy-cross for ${system}");
  src = pkgs.fetchurl {
    url = "https://adafruit-circuit-python.s3.amazonaws.com/bin/mpy-cross/${build.file}";
    inherit (build) sha256;
    executable = true; # the hash covers the file with its executable bit (nix-prefetch-url --executable)
  };
in
pkgs.runCommand "mpy-cross-9.2.9" { nativeBuildInputs = [ pkgs.autoPatchelfHook ]; } ''
  install -Dm755 ${src} $out/bin/mpy-cross
  autoPatchelf $out
''
