"""Makes the firmware modules importable for the tests, behind the standard library (see pytest.ini)."""
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "firmware"))
