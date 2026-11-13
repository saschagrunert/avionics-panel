"""Makes the firmware modules and the simulator (sim/) importable for the tests, behind the standard library (see
pytest.ini), loads the generators' modules for them (load()) and hid-tools' parser (hid_parser())."""
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
