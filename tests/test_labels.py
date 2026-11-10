"""The key legends live in mech/stack.py: the caps, the plate, the 3D view and the board silkscreen read them
from there. The firmware button map (CircuitPython, no access to stack.py) keeps its own names; these tests
make sure they agree."""
import importlib.util
import os

import buttonmap as BM
from panel import Panel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, path):
    """a module by file path, so neither mech/ nor pcb/ goes on sys.path for the whole test run"""
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = load("_labels_stack", "mech/stack.py")
AUDIO = ("MIC1", "COM1", "MIC2", "COM2")              # their shift legends select audio sources
SPECIAL = {"121.5": "COM_121_5", "½ BANK": "HALF_BANK"}


def key_name(label):
    """cap label -> firmware key name: COM ⇆ -> COM_SWAP, D→ -> DIRECT, MIC 1 -> MIC1"""
    return {"D→": "DIRECT"}.get(label, label.replace(" ⇆", "_SWAP").replace(" ", ""))


def shift_name(key, legend):
    """amber legend -> firmware button name of the shifted key"""
    if not legend:
        return "S_" + key                              # no legend: the key's own shifted button
    if legend in SPECIAL:
        return SPECIAL[legend]
    if key in AUDIO:
        return legend.replace(" ", "") + "_AUDIO"      # NAV 1 -> NAV1_AUDIO
    return legend.replace(" ⇆", "_SWAP").replace(" ", "_")


def test_firmware_keys_match_the_caps():
    assert [list(row) for row in BM.MATRIX[:4]] == [[key_name(label) for label, _ in row] for row in S.KEY_LEGENDS]


def test_firmware_shift_functions_match_the_legends():
    for row in S.KEY_LEGENDS:
        for label, legend in row:
            key = key_name(label)
            if key == "SHIFT":                         # the modifier itself
                continue
            if key == "HOME":                          # SHIFT + HOME is UNIT: firmware state, no button
                assert legend == "UNIT"
                continue
            assert BM.shifted(key) == shift_name(key, legend), (label, legend)
            assert BM.shifted(key) in BM.BUTTON[1], key


# the push word of each knob legend -> the button that push sends (FMS: unit button, also on device 1)
PUSH = {"SYNC": "HDG_SYNC", "STD": "BARO_STD", "PTR": "PTR", "COM/NAV/ADF": "FREQ_PUSH", "XPDR": "XPDR_MODE",
        "CRSR": "FMS_CRSR", "CABIN": "CABIN_LT"}


def pushed(knob, shifted):
    """the device 1 buttons the firmware sends for a push of this knob, plain or after SHIFT"""
    p, names = Panel(), {b: n for n, b in BM.BUTTON[1].items()}
    if shifted:
        p.key("SHIFT", True, 0)
        p.key("SHIFT", False, 1)
    src, out = "RANGE_COM" if knob == "RANGE" else knob + "_PUSH", set()
    for t, down in ((10, True), (500, False)):         # RANGE sends PTR on release
        p.key(src, down, t)
        p.tick(t + 1)
        out |= {names[b] for b in p.buttons(1)}
    return out


def test_knob_push_legends_match_the_firmware():
    # the push named on each knob ring (plain legend outside, SHIFT legend inside) is what that knob sends
    for knob, legends in S.KNOB_LEGENDS.items():
        for shifted, legend in enumerate(legends):
            if legend is None:
                continue
            assert " · PUSH " in legend or legend.startswith("PUSH "), (knob, legend)
            assert pushed(knob, shifted) == {PUSH[legend.split("PUSH ")[-1]]}, (knob, legend)
