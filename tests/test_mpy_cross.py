"""The firmware runs on CircuitPython, which compiles with MicroPython's parser: syntax that CPython accepts
(like *-unpacking inside a list literal) can fail on the board, and the CPython tests would never notice.

CircuitPython 9.2's own mpy-cross, the board's compiler, checks every file that goes on the board. The firmware
shell (nix/shells.nix) puts it on the PATH on Linux x86-64 and ARM64 and sets REQUIRE_MPY_CROSS=1 there, which
makes a missing compiler fail these tests; elsewhere they skip."""
import os
import shutil
import subprocess

import pytest

FIRMWARE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firmware")
FILES = sorted(f for f in os.listdir(FIRMWARE) if f.endswith(".py") and not f.startswith(("test_", "make_")))
MPY_CROSS = shutil.which("mpy-cross")
MPY_CROSS_VERSION = "CircuitPython 9.2."


def mpy_cross(path):
    if not MPY_CROSS:
        if os.environ.get("REQUIRE_MPY_CROSS"):
            pytest.fail("CircuitPython's mpy-cross missing, and REQUIRE_MPY_CROSS is set")
        pytest.skip("CircuitPython's mpy-cross missing (nix/shells.nix)")
    return subprocess.run([MPY_CROSS, "-o", os.devnull, path], capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("name", FILES)
def test_firmware_compiles_with_circuitpython_mpy_cross(name):
    run = mpy_cross(os.path.join(FIRMWARE, name))
    assert run.returncode == 0, run.stdout + run.stderr


def test_mpy_cross_is_circuitpython_9_2(tmp_path):
    # the right compiler, and one that really rejects what the board rejects
    bad = tmp_path / "star.py"
    bad.write_text("a = [1]\nb = [*a, 2]\n")
    assert mpy_cross(str(bad)).returncode != 0
    version = subprocess.run([MPY_CROSS, "--version"], capture_output=True, text=True, timeout=60).stdout
    assert version.startswith(MPY_CROSS_VERSION), version
