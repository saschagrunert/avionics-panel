"""Every GPIO the firmware uses against the board: code.py and boot.py (CircuitPython, no access to pcb/) name
their pins themselves; these tests run them on the simulator's stand-in hardware (sim/hardware.py) and compare
with the nets in pcb/board.py."""
import importlib.util
import os

import buttonmap as BM
import test_boot

from sim.hardware import RINGS, Board

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICO = [("\nPICO_TEST = False\n", "\nPICO_TEST = True\n")]   # code.py edited for the Pico bench


def load(name, path):
    """a module by file path, so pcb/ does not go on sys.path for the whole test run"""
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = load("_pins_board", "pcb/board.py")
NET = {p.name: p.net for p in B.build()}


def firmware(pico_test=False):
    """the pins code.py hands to keypad, rotaryio and pwmio"""
    hw = Board().boot().run(5, PICO if pico_test else ())
    rings = dict(zip([r[0] for r in hw.code["RINGS"]], hw.encoders, strict=True))
    assert sorted(rings) == sorted(RINGS)
    return hw, rings


def ring_nets(ring):
    """board nets of a ring's A / B lines: ring 1 (A, B) of a dual encoder is the outer knob, ring 2 the inner"""
    if ring == "RANGE":
        return NET["RANGE.ENCA"], NET["RANGE.ENCB"]
    knob, part = ring.rsplit("_", 1)
    pins = ("A", "B") if part == "OUTER" else ("A2", "B2")
    return tuple(NET[f"ENC_{knob}.{p}"] for p in pins)


def all_pins(hw):
    pins = list(hw.matrix.rows) + list(hw.matrix.cols) + list(hw.direct.pins)
    pins += [p for e in hw.encoders for p in e.pins] + [led.pin for led in hw.leds]
    return pins


def test_matrix_rows_and_columns():
    hw, _ = firmware()
    assert list(hw.matrix.rows) == B.ROW_GP and list(hw.matrix.cols) == B.COL_GP
    assert hw.matrix.columns_to_anodes is True


def test_every_matrix_key_sits_on_its_row_and_column():
    # keys: switch on the row line, diode from the column (anode) to the switch; row 4: the RANGE switches,
    # ALT/HDG and FMS pushes, each with its common on the row line and its diode from its column
    hw, _ = firmware()
    rows, cols = hw.matrix.rows, hw.matrix.cols
    for r, row in enumerate(BM.MATRIX[:4]):
        for c, _name in enumerate(row):
            assert NET[f"K{r}{c}.A"] == NET[f"K{r}{c}.B"] == rows[r]
            assert NET[f"DK{r}{c}.A"] == cols[c] and NET[f"DK{r}{c}.K"] == NET[f"K{r}{c}.D"]
    switch = {"RANGE_A": ("D_RANGE_A", "RANGE.A", "RANGE.PUSH"), "RANGE_B": ("D_RANGE_B", "RANGE.B", "RANGE.PUSH"),
              "RANGE_C": ("D_RANGE_C", "RANGE.C", "RANGE.PUSH"), "RANGE_D": ("D_RANGE_D", "RANGE.D", "RANGE.PUSH"),
              "RANGE_COM": ("D_RANGE_COM", "RANGE.COM", "RANGE.PUSH"),
              "ALTHDG_PUSH": ("D_ALTHDG", "ENC_ALTHDG.E", "ENC_ALTHDG.D"),
              "FMS_PUSH": ("D_FMS", "ENC_FMS.E", "ENC_FMS.D")}
    for c, name in enumerate(BM.MATRIX[4]):
        diode, contact, common = switch[name]
        assert NET[diode + ".A"] == cols[c] and NET[diode + ".K"] == NET[contact] and NET[common] == rows[4]


def test_freq_push_and_lights():
    hw, _ = firmware()
    assert hw.direct.pins == (NET["ENC_FREQ.E"],) and NET["ENC_FREQ.D"] == "GND"
    assert hw.direct.value_when_pressed is False and hw.direct.pull is True
    assert [led.pin for led in hw.leds] == [B.LEDS["SHIFT"][1], B.LEDS["UNIT"][1]]


def test_encoder_rings():
    _, rings = firmware()
    for ring, enc in rings.items():
        assert enc.pins == ring_nets(ring), ring
        assert abs(int(enc.pins[0][2:]) - int(enc.pins[1][2:])) == 1, ring   # rotaryio on RP2040: sequential
    for ref in ("ENC_ALTHDG", "ENC_FREQ", "ENC_FMS"):
        assert NET[ref + ".C"] == NET[ref + ".C2"] == "GND"


def test_encoder_divisor():
    # rotaryio counts quadrature edges / divisor: 4 edges per pulse, and both encoder types give 30 detents per
    # 15 pulses (Bourns PEC11D-4120F-S0015, Alps RKJXT1F42001), so 2 edges per detent
    _, rings = firmware()
    assert {enc.divisor for enc in rings.values()} == {2}


def test_no_pin_used_twice():
    for pico_test in (False, True):
        pins = all_pins(firmware(pico_test)[0])
        assert len(pins) == len(set(pins)), pico_test


def test_pico_test_pins():
    # the bench moves only the FREQ knob, its push and the lights; everything else is the board's. Every pin
    # is on the Pico header (GP0-22, GP26-28), apart from the onboard LED (GP25) for SHIFT and GP29 (VSYS
    # divider) for RANGE B, which can't turn on the bench but keeps the 7th PIO encoder
    board, board_rings = firmware()
    pico, pico_rings = firmware(pico_test=True)
    assert (pico.matrix.rows, pico.matrix.cols) == (board.matrix.rows, board.matrix.cols)
    for ring in RINGS:
        if not ring.startswith("FREQ"):
            assert pico_rings[ring].pins == board_rings[ring].pins, ring
    header = {f"GP{i}" for i in list(range(23)) + [26, 27, 28]}
    off_header = {p for p in all_pins(pico) if p not in header}
    assert off_header == {"GP25", "GP29"}
    assert [led.pin for led in pico.leds] == ["GP25"] and pico_rings["RANGE"].pins[1] == "GP29"


def test_boot_reads_the_board_shift_key():
    # boot.py finds SHIFT only on the board's row and column of SHIFT: with the switch closed there it keeps
    # the drive, with it anywhere else (a wrong pin in boot.py) it would hide it
    r, c = next((r, row.index("SHIFT")) for r, row in enumerate(BM.MATRIX) if "SHIFT" in row)
    pins = (B.ROW_GP[r], B.COL_GP[c])
    assert pins == test_boot.SHIFT_PINS
    assert NET[f"K{r}{c}.A"] == pins[0] and NET[f"DK{r}{c}.A"] == pins[1]
    assert not test_boot.hidden(test_boot.boot(shift=True, pins=pins))
    assert test_boot.hidden(test_boot.boot(shift=False, pins=pins))
