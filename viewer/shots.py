"""Renders 1 to 4 and 9 (renders/), stills of the 3D view: index.html with a #shot- fragment, which hides the
page's controls, in headless Chromium at a device pixel ratio of 1 and in the dark colour scheme. WebGL runs in
software (SwiftShader), so the pictures do not depend on the graphics card. Not part of the build: run it after a
change to the view or to geometry.js.

    nix-shell nix/shells.nix -A shots --run "python3 viewer/shots.py"

Python's standard library and a `chromium` on the PATH, which that shell has from the locked nixpkgs; the
environment variable CHROMIUM names another one, such as google-chrome.
"""
import os
import pathlib
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RENDERS = os.path.join(os.path.dirname(HERE), "renders")
PAGE = pathlib.Path(HERE, "index.html").as_uri()
# picture, fragment, window (px). The page loads at its final size: a resize after the load shifts the top view by
# a few pixels.
SHOTS = (("1-hero", "shot-h", 1800, 1100), ("2-top", "shot-c", 2150, 905), ("3-exploded", "shot-e", 1800, 1100),
         ("4-seated", "shot-a", 1800, 1100), ("9-bottom", "shot-b", 1800, 1100))
TRANSPARENT = "shot-c"     # the top view has no background: its picture keeps the alpha channel
# the page waits for its fonts and draws on the next frame: this much of the page's own time, which runs as fast as
# the page allows
BUDGET_MS = 10000
TIMEOUT_S = 120


def chromium(browser, fragment, width, height, *args):
    """Runs the page with a fragment in a window of its own profile, which goes with it; its output"""
    with tempfile.TemporaryDirectory() as profile:
        return subprocess.run(
            [browser, "--headless=new", f"--user-data-dir={profile}", "--no-first-run", "--hide-scrollbars",
             "--allow-file-access-from-files", "--force-device-scale-factor=1", "--force-color-profile=srgb",
             "--force-dark-mode", "--disable-gpu", "--enable-unsafe-swiftshader", f"--window-size={width},{height}",
             f"--virtual-time-budget={BUDGET_MS}", *args, f"{PAGE}#{fragment}"],
            check=True, capture_output=True, text=True, timeout=TIMEOUT_S).stdout


def main():
    browser = os.environ.get("CHROMIUM", "chromium")
    try:
        # the page shows a message in place of the view when it cannot draw it (no WebGL, a file missing)
        if 'class="fail"' in chromium(browser, SHOTS[0][1], *SHOTS[0][2:], "--dump-dom"):
            sys.exit(f"shots.py: the 3D view does not come up in {browser}")
        for name, fragment, width, height in SHOTS:
            path = os.path.join(RENDERS, f"{name}.png")
            alpha = ["--default-background-color=00000000"] if fragment == TRANSPARENT else []
            chromium(browser, fragment, width, height, f"--screenshot={path}", *alpha)
            with open(path, "rb") as f:
                size = struct.unpack(">II", f.read(24)[16:])       # the PNG's IHDR
            if size != (width, height):
                sys.exit(f"shots.py: {path} is {size[0]} x {size[1]} px, not {width} x {height}")
            print(f"{os.path.relpath(path)}: {width} x {height}")
    except (OSError, subprocess.SubprocessError) as e:
        sys.exit(f"shots.py: {e}")


if __name__ == "__main__":
    main()
