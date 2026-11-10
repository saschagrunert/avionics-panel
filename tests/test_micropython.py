"""The firmware runs on CircuitPython, which compiles with MicroPython's parser: syntax that CPython accepts
(like *-unpacking inside a list literal) can fail on the board, and the CPython tests would never notice.
Compile every file that goes on the board with the MicroPython unix port. build.sh provides it and sets
REQUIRE_MICROPYTHON=1, so CI fails instead of skipping when it is missing."""
import os
import shutil
import subprocess

import pytest

FIRMWARE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firmware")
FILES = sorted(f for f in os.listdir(FIRMWARE) if f.endswith(".py") and not f.startswith(("test_", "make_")))
MICROPYTHON = shutil.which("micropython")


@pytest.mark.parametrize("name", FILES)
def test_firmware_compiles_with_micropython(name):
    if not MICROPYTHON:
        if os.environ.get("REQUIRE_MICROPYTHON"):
            pytest.fail("micropython not on PATH")
        pytest.skip("micropython not on PATH (build.sh provides it)")
    with open(os.path.join(FIRMWARE, name)) as f:
        source = f.read()
    code = f"compile({source!r}, {name!r}, 'exec')"
    run = subprocess.run([MICROPYTHON, "-c", code], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
