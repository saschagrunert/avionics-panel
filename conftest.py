"""Makes the firmware modules and the simulator (sim/) importable for the tests, behind the standard library (see
pytest.ini), and loads the generators' modules for them (load())."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path += [os.path.join(ROOT, "firmware"), ROOT]


def load(name, path):
    """a module by its path from the repository root, as module `name`, with sys.path as it was before, so
    neither mech/ nor pcb/ stays on it for the whole test run"""
    saved = sys.path[:]
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path[:] = saved
    return module
