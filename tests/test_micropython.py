"""The firmware runs on CircuitPython, which compiles with MicroPython's parser: syntax that CPython accepts
(like *-unpacking inside a list literal) can fail on the board, and the CPython tests would never notice.

Two compilers check every file that goes on the board. CircuitPython 9.2's own mpy-cross is the board's
compiler (CircuitPython 9.2 is built on an older MicroPython than nixpkgs has): build.sh builds Adafruit's
binary, pinned by hash, with firmware/mpy-cross.nix, passes it in MPY_CROSS and sets REQUIRE_MPY_CROSS=1
(on Linux x86-64 and ARM64; elsewhere it skips that check).
The MicroPython unix port from nixpkgs runs everywhere Nix does: build.sh provides it and sets
REQUIRE_MICROPYTHON=1. Each check skips without its compiler, and fails instead when its REQUIRE variable is
set."""
import os
import shutil
import subprocess

import pytest

FIRMWARE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firmware")
FILES = sorted(f for f in os.listdir(FIRMWARE) if f.endswith(".py") and not f.startswith(("test_", "make_")))
MICROPYTHON = shutil.which("micropython")
MPY_CROSS = os.environ.get("MPY_CROSS")
MPY_CROSS_VERSION = "CircuitPython 9.2."


def need(tool, required, what):
    if not tool:
        if os.environ.get(required):
            pytest.fail(f"{what} missing")
        pytest.skip(f"{what} missing (build.sh provides it)")


@pytest.mark.parametrize("name", FILES)
def test_firmware_compiles_with_micropython(name):
    need(MICROPYTHON, "REQUIRE_MICROPYTHON", "micropython on the PATH")
    with open(os.path.join(FIRMWARE, name)) as f:
        source = f.read()
    code = f"compile({source!r}, {name!r}, 'exec')"
    run = subprocess.run([MICROPYTHON, "-c", code], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr


def mpy_cross(path):
    return subprocess.run([MPY_CROSS, "-o", os.devnull, path], capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("name", FILES)
def test_firmware_compiles_with_circuitpython_mpy_cross(name):
    need(MPY_CROSS, "REQUIRE_MPY_CROSS", "CircuitPython's mpy-cross (MPY_CROSS)")
    run = mpy_cross(os.path.join(FIRMWARE, name))
    assert run.returncode == 0, run.stdout + run.stderr


def test_mpy_cross_is_circuitpython_9_2(tmp_path):
    # the right compiler, and one that really rejects what the board rejects
    need(MPY_CROSS, "REQUIRE_MPY_CROSS", "CircuitPython's mpy-cross (MPY_CROSS)")
    version = subprocess.run([MPY_CROSS, "--version"], capture_output=True, text=True, timeout=60).stdout
    assert version.startswith(MPY_CROSS_VERSION), version
    bad = tmp_path / "star.py"
    bad.write_text("a = [1]\nb = [*a, 2]\n")
    assert mpy_cross(str(bad)).returncode != 0
