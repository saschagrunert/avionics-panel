"""The key legends live in mech/stack.py: the caps, the plate, the 3D view and the board silkscreen read them
from there. The firmware button map (CircuitPython, no access to stack.py) keeps its own names; these tests
make sure they agree."""
import importlib.util
import os

import buttonmap as BM

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
