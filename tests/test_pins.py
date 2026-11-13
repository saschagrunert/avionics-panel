"""Every GPIO the firmware uses against the board: code.py and boot.py (CircuitPython, no access to pcb/) name
their pins themselves; these tests run them on the simulator's stand-in hardware (sim/hardware.py) and compare
with the nets in pcb/board.py. The stand-in's own wiring is compared with them too."""
import buttonmap as BM
import test_boot

from conftest import load
from sim.hardware import COL_PINS, CONTACTS, RING_PINS, RINGS, ROW_PINS, Board

PICO = [("\nPICO_TEST = False\n", "\nPICO_TEST = True\n")]   # code.py edited for the Pico bench
B = load("_pins_board", "pcb/board.py")
NET = {p.name: p.net for p in B.build()}
# a contact behind a series resistor R_GP<n> (pcb/board.py: R_GP25, GP25 to the FREQ outer ring's B line): the
# firmware's pin is the GPIO on the resistor's other pad
SERIES = {NET[f"{ref}.2"]: NET[f"{ref}.1"] for ref in {n.split(".")[0] for n in NET} if ref.startswith("R_GP")}


def firmware(pico_test=False):
    """the pins code.py hands to keypad, rotaryio and pwmio"""
    hw = Board().boot().run(5, PICO if pico_test else ())
    rings = dict(zip([r[0] for r in hw.code["RINGS"]], hw.encoders, strict=True))
    assert sorted(rings) == sorted(RINGS)
    return hw, rings


def ring_nets(ring):
    """board nets of a ring's A / B lines: ring 1 (A, B) of a dual encoder is the outer knob, ring 2 the inner"""
    if ring == "RANGE":
        pads = ("RANGE.ENCA", "RANGE.ENCB")
    else:
        knob, part = ring.rsplit("_", 1)
        pads = tuple(f"ENC_{knob}.{p}" for p in (("A", "B") if part == "OUTER" else ("A2", "B2")))
    return tuple(SERIES.get(NET[p], NET[p]) for p in pads)


def all_pins(hw):
    pins = list(hw.matrix.rows) + list(hw.matrix.cols) + list(hw.direct.pins)
    pins += [p for e in hw.encoders for p in e.pins] + [led.pin for led in hw.leds]
    return pins


def test_matrix_rows_and_columns():
    # code.py names the rows and columns in buttonmap.MATRIX's order, as the board has them, and hands the
    # keypad every one of them, in its scan order
    hw, _ = firmware()
    assert list(hw.code["ROW_PINS"]) == B.ROW_GP and list(hw.code["COL_PINS"]) == B.COL_GP
    assert sorted(hw.matrix.rows) == sorted(B.ROW_GP) and sorted(hw.matrix.cols) == sorted(B.COL_GP)
    assert hw.matrix.columns_to_anodes is True


def test_the_keypad_scans_shift_first():
    # the keypad reports the changes of one scan in the order of its key numbers. SHIFT is key 0, so it comes
    # before a key pressed in the same scan, and each RANGE direction comes before "com" (panel.py tells a tilt
    # from a centre push by that). Each key number is the switch code.py takes it for
    hw, _ = firmware()
    names = hw.code["sources"][0].names
    assert names[0] == "SHIFT" and sorted(names) == sorted(n for row in BM.MATRIX for n in row)
    assert all(names.index(d) < names.index("RANGE_COM") for d in ("RANGE_A", "RANGE_B", "RANGE_C", "RANGE_D"))
    assert [CONTACTS[n] for n in names] == hw.matrix.contacts


def test_the_simulator_is_wired_as_the_board():
    # the stand-in hardware closes its switches and turns its rings on the board's pins, whatever code.py
    # names, so a wrong pin or a swapped pair in code.py fails the firmware's tests
    assert list(ROW_PINS) == B.ROW_GP and list(COL_PINS) == B.COL_GP
    assert CONTACTS["FREQ_PUSH"] == NET["ENC_FREQ.E"]
    assert {ring: ring_nets(ring) for ring in RINGS} == RING_PINS


def test_every_matrix_key_sits_on_its_row_and_column():
    # keys: switch on the row line, diode from the column (anode) to the switch; row 4: the RANGE switches,
    # ALT/HDG and FMS pushes, each with its common on the row line and its diode from its column
    hw, _ = firmware()
    rows, cols = hw.code["ROW_PINS"], hw.code["COL_PINS"]
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
    shift, unit = (led.pin for led in hw.leds)
    assert (shift, unit) == (B.LEDS["SHIFT"][1], B.LEDS["UNIT"][1])
    # SHIFT: the pin through R_SHIFT to the LED's anode, the cathode on GND
    assert {NET["R_SHIFT.1"], NET["R_SHIFT.2"]} == {shift, NET["LED_SHIFT.A"]} and NET["LED_SHIFT.K"] == "GND"
    # UNIT: the pin on Q_UNIT's gate (pad 1 of JLC's footprint) and on its pull-down; the source (pad 2) on GND,
    # the drain (pad 3) on the LED's cathode, and the anode through R_UNIT on VBUS_F
    assert NET["Q_UNIT.1"] == unit and {NET["R_UNIT_PD.1"], NET["R_UNIT_PD.2"]} == {"GND", unit}
    assert NET["Q_UNIT.2"] == "GND" and NET["Q_UNIT.3"] == NET["LED_UNIT.K"] != "GND"
    assert {NET["R_UNIT.1"], NET["R_UNIT.2"]} == {"VBUS_F", NET["LED_UNIT.A"]}


def test_encoder_rings():
    _, rings = firmware()
    for ring, enc in rings.items():
        assert enc.pins == ring_nets(ring), ring                 # A, then B: swapped, the ring counts backwards
        assert abs(int(enc.pins[0][2:]) - int(enc.pins[1][2:])) == 1, ring   # rotaryio on RP2040: sequential
    for ref in ("ENC_ALTHDG", "ENC_FREQ", "ENC_FMS"):
        assert NET[ref + ".C"] == NET[ref + ".C2"] == "GND"
    # GP25, CircuitPython's status LED on the Pico build, reaches its contact only through its series resistor
    assert {NET["ENC_FREQ.B"]: "GP25"} == SERIES


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


def test_boot_reads_the_board_unit_key():
    # UNIT is the HOME key: boot.py switches the mode only with the switch on the board's row and column of HOME
    r, c = next((r, row.index("HOME")) for r, row in enumerate(BM.MATRIX) if "HOME" in row)
    assert (B.ROW_GP[r], B.COL_GP[c]) == test_boot.UNIT_PINS
    assert NET[f"K{r}{c}.A"] == B.ROW_GP[r] and NET[f"DK{r}{c}.A"] == B.COL_GP[c]
    assert test_boot.boot(unit=True).keyboard and not test_boot.boot().keyboard
