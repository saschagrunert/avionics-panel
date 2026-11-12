"""Makes the firmware modules and the simulator (sim/) importable for the tests, behind the standard library (see
pytest.ini)."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path += [os.path.join(ROOT, "firmware"), ROOT]
