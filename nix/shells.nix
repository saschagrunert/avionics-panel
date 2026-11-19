# The environments build.sh runs the generators and tests in, the one of the lint workflow and the one for the
# renders of the 3D view, from the nixpkgs locked in ../flake.lock. By hand: nix-shell nix/shells.nix -A gen (or
# firmware, lint, shots). The CI Nix store caches are keyed on the files in this directory.
let
  pkgs = import (import ./nixpkgs.nix) { };
  mpy-cross = import ./mpy-cross.nix pkgs;
  pinned = pkgs.lib.meta.availableOn pkgs.stdenv.hostPlatform mpy-cross;
  linux = pkgs.stdenv.hostPlatform.isLinux;
  # the one browser of Playwright's set that tests/test_simjs.py runs
  chromium-headless = pkgs.playwright-driver.browsers.override {
    withChromium = false;
    withFirefox = false;
    withWebkit = false;
    withFfmpeg = false;
  };
  # the fonts the browser prints the cards in (tests/test_card.py), these alone and none of the host's: a condensed
  # one of the cards' list (Roboto Condensed), Arial's metrics (Liberation Sans, for Arial and sans-serif) and
  # DejaVu for the symbols (arrows, ⇆)
  fonts = pkgs.writeText "fonts.conf" ''
    <?xml version="1.0"?>
    <!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
    <fontconfig>
      <dir>${pkgs.roboto}/share/fonts</dir>
      <dir>${pkgs.liberation_ttf}/share/fonts</dir>
      <dir>${pkgs.dejavu_fonts}/share/fonts</dir>
      <alias binding="same"><family>Arial</family><prefer><family>Liberation Sans</family></prefer></alias>
      <alias><family>sans-serif</family><prefer><family>Liberation Sans</family><family>DejaVu Sans</family></prefer></alias>
    </fontconfig>
  '';
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
  # has it and its tests must run (REQUIRE_MPY_CROSS); elsewhere the shell says so and they skip. On Linux it
  # has hid-tools, which parses the report descriptor for tests/test_descriptor.py, and those tests must run
  # (REQUIRE_HID_TOOLS); elsewhere they skip. On Linux it also has Playwright for Python and the Chromium
  # (headless shell) of its version, for tests/test_simjs.py and tests/test_card.py's print, which must run there
  # too (REQUIRE_BROWSER), with the fonts above alone. Its Python must be the minor version the simulator's zip
  # for Windows ships (REQUIRE_ZIP_PYTHON, tests/test_windows_zip.py).
  firmware = pkgs.mkShell {
    packages = [
      (pkgs.python3.withPackages (
        ps:
        with ps;
        [
          pytest
          pytest-cov
        ]
        ++ pkgs.lib.optionals linux [
          (toPythonModule pkgs.hid-tools)
          playwright
        ]
      ))
    ]
    ++ pkgs.lib.optional pinned mpy-cross;
    shellHook =
      "export REQUIRE_ZIP_PYTHON=1\n"
      + pkgs.lib.optionalString linux ''
        export REQUIRE_HID_TOOLS=1 REQUIRE_BROWSER=1 PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
        export PLAYWRIGHT_BROWSERS_PATH=${chromium-headless} FONTCONFIG_FILE=${fonts}
      ''
      + (
        if pinned then
          "export REQUIRE_MPY_CROSS=1"
        else
          ''echo "no pinned CircuitPython mpy-cross for ${pkgs.stdenv.hostPlatform.system}: its tests skip" >&2''
      );
  };
  # the linters, as .github/workflows/lint.yml runs them, one step each
  lint = pkgs.mkShell {
    packages = with pkgs; [
      ruff
      shellcheck
      shfmt
      markdownlint-cli2
      lychee
      typos
      actionlint
      zizmor
    ];
  };
  # viewer/shots.py: renders 1 to 4 and 9, with Chromium's software WebGL
  shots = pkgs.mkShell {
    packages = [
      pkgs.python3
      pkgs.chromium
    ];
  };
}
