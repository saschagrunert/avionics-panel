"""Makes the firmware modules and the simulator (sim/) importable for the tests, behind the standard library (see
pytest.ini), loads the generators' modules for them (load()) and hid-tools' parser (hid_parser()), and reads
BUTTONS.md's table (buttons_md)."""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path += [os.path.join(ROOT, "firmware"), ROOT]


def hid_parser():
    """hid-tools' parser of report descriptors (hidtools.hid), which the firmware shell (nix/shells.nix) has on
    Linux. Without it the test or module that asks skips; where REQUIRE_HID_TOOLS is set, as in that shell, it
    fails."""
    try:
        import hidtools.hid
    except ImportError:
        if os.environ.get("REQUIRE_HID_TOOLS"):
            pytest.fail("hid-tools missing, and REQUIRE_HID_TOOLS is set")
        pytest.skip("hid-tools missing (nix/shells.nix provides it on Linux)", allow_module_level=True)
    return hidtools.hid


def load(name, path):
    """a module by its path from the repository root, as module `name`, with sys.path as it was before, so
    neither mech/ nor pcb/ stays on it for the whole test run"""
    saved = sys.path[:]
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path[:] = saved
    return module


@pytest.fixture(scope="session")
def buttons_md():
    """{device: {name: button number}} of the table in firmware/BUTTONS.md"""
    out = {1: {}, 2: {}}
    with open(os.path.join(ROOT, "firmware", "BUTTONS.md"), encoding="utf-8") as f:
        for line in f:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("|") and cells[2:] != ["Device 1", "Device 2"] and cells[0] != "---":
                for device, cell in zip((1, 2), cells[2:], strict=True):
                    if cell:
                        out[device][cells[0]] = int(cell)
    return out
