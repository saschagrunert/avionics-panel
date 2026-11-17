"""The Octavi IFR-1's profiles (mobiflight/ifr1.py) and their cards and cheat sheets (mobiflight/ifr1_card.py): the
buttons are MobiFlight's, every one is mapped or unmapped with a reason, every use sends its panel source's code, the
new code (squawk pairs, NAV 2's course, the ⇆ modifier, the lights) does what it says when run as the simulator's
RPN, and the project and the command line write what MobiFlight reads."""
import html
import itertools
import json
import re
import zipfile

import pytest

from mobiflight import __main__ as cli
from mobiflight import ifr1, ifr1_card, profile
from mobiflight.families import FAMILIES, parts
from tests.test_mobiflight import READ, TOKEN, VALUE, run, sets
from tests.test_mobiflight import unit as unit_of

FAMILY = pytest.mark.parametrize("key", sorted(FAMILIES))
PROFILES = {key: ifr1.build(key) for key in FAMILIES}

# the 96 buttons as MobiFlight 11.3.1's OctaviHandler makes them, in its order, written out from its constructor
# (OctaviHandler.cs, octavi.joystick.json's five shifted modes), each "Button_" and this
HANDLER = """
SHIFT_SW UNSHIFT_SW COM1_OI COM1_OD COM1_II COM1_ID COM1_TOG COM2_OI COM2_OD COM2_II COM2_ID COM2_TOG NAV1_OI
NAV1_OD NAV1_II NAV1_ID NAV1_TOG NAV2_OI NAV2_OD NAV2_II NAV2_ID NAV2_TOG FMS1_OI FMS1_OD FMS1_II FMS1_ID
FMS1_TOG FMS1_CRSR FMS1_DCT FMS1_MENU FMS1_CLR FMS1_ENT FMS1_CDI FMS1_OBS FMS1_MSG FMS1_FPL FMS1_VNAV FMS1_PROC
FMS2_OI FMS2_OD FMS2_II FMS2_ID FMS2_TOG FMS2_CRSR FMS2_DCT FMS2_MENU FMS2_CLR FMS2_ENT FMS2_CDI FMS2_OBS
FMS2_MSG FMS2_FPL FMS2_VNAV FMS2_PROC AP_OI AP_OD AP_II AP_ID AP_TOG AP_CRSR AP_AP AP_HDG AP_NAV AP_APR AP_ALT
AP_VS XPDR_OI XPDR_OD XPDR_II XPDR_ID XPDR_TOG COM1^_OI COM1^_OD COM1^_II COM1^_ID COM1^_TOG COM2^_OI COM2^_OD
COM2^_II COM2^_ID COM2^_TOG NAV1^_OI NAV1^_OD NAV1^_II NAV1^_ID NAV1^_TOG NAV2^_OI NAV2^_OD NAV2^_II NAV2^_ID
NAV2^_TOG XPDR^_OI XPDR^_OD XPDR^_II XPDR^_ID XPDR^_TOG
"""


def codes(key):
    """(button, event, code) for every code of an IFR-1 profile"""
    return [(button, event, code) for button, entry in PROFILES[key].DEVICE.items()
            for event, code in profile.actions(entry).items()]


def test_the_buttons_are_mobiflights():
    assert tuple(f"Button_{name}" for name in HANDLER.split()) == ifr1.BUTTONS


@FAMILY
def test_every_button_is_mapped_or_unmapped_with_a_reason(key):
    p = PROFILES[key]
    assert not set(p.DEVICE) & set(p.UNMAPPED)
    assert set(p.DEVICE) | set(p.UNMAPPED) == set(ifr1.BUTTONS)
    assert all(isinstance(r, str) and r for r in p.UNMAPPED.values())
    assert "Button_SHIFT_SW" in p.UNMAPPED and "Button_UNSHIFT_SW" in p.DEVICE


@FAMILY
def test_codes_are_well_formed(key):
    # as the panel's (test_mobiflight.test_codes_are_well_formed): known tokens, closed blocks, something set, no
    # "@", room in MobiFlight's 1024-byte message
    for button, event, code in codes(key):
        tokens = TOKEN.findall(code)
        assert " ".join(tokens) == code and "@" not in code, (button, event)
        assert len(code.encode()) < 1000, (button, event)
        depth = 0
        for token in tokens:
            assert READ.fullmatch(token) or sets(token) or VALUE.fullmatch(token), (button, token)
            depth += (token in ("if{", "els{")) - (token == "}")
            assert depth >= 0, (button, code)
        assert depth == 0 and any(sets(token) for token in tokens), (button, event)


@FAMILY
def test_reads_use_the_unit_of_their_kind(key):
    # as the panel's (test_mobiflight.unit()): the squawk in BCD16, a course in degrees, a flag as a bool
    reads = [code for *_, code in codes(key)] + list(PROFILES[key].LEDS.values())
    for code in reads:
        for token in TOKEN.findall(code):
            read = READ.fullmatch(token)
            if read and not read[3]:
                variable = read[1].split(":")[0] if read[1] else read[2]
                assert token.rsplit(", ", 1)[1][:-1].lower() == unit_of(variable), token


@FAMILY
def test_every_use_sends_its_panel_sources_code(key):
    # a Panel source sends what the panel button sends in the profile, whole, or carries its reason; an Own source
    # is one of the module's own codes; and the button's codes hold every code its uses send
    family, p = FAMILIES[key], PROFILES[key]
    own = {o.code for o in (*ifr1.NAV2_COURSE.values(), *ifr1.SQUAWK_PAIRS.values(), ifr1.KAP140_VS, ifr1.CLEAR)}
    for button, used in p.USES.items():
        sent = " ".join(profile.actions(p.DEVICE[button]).values()) if button in p.DEVICE else ""
        for use, u in used.items():
            if isinstance(u.source, ifr1.Panel):
                table, rest = family.DEVICE[u.source.device], family.UNMAPPED[u.source.device]
                if u.source.button in table:
                    assert u.entry == table[u.source.button] and u.reason is None, (button, use)
                    assert ifr1.tapped(u.entry) in sent or all(
                        code in sent for code in profile.actions(u.entry).values()), (button, use)
                else:
                    assert u.entry is None and u.reason == rest[u.source.button], (button, use)
            elif isinstance(u.source, ifr1.Own):
                assert u.entry in own and u.entry in sent, (button, use)
            else:
                assert u.source is None and u.entry is None, (button, use)


# the rows every profile takes from the panel alike: (IFR-1 button, use) -> (device, panel button)
ROWS = {
    **{(f"Button_{m}_{r}", "turn"): (d, f"{kind}_{step}_{way}") for m, d, kind in (
        ("COM1", 1, "COM"), ("COM2", 2, "COM"), ("NAV1", 1, "NAV"), ("NAV2", 2, "NAV"))
       for r, step, way in (("OI", "MHZ", "UP"), ("OD", "MHZ", "DN"), ("II", "KHZ", "UP"), ("ID", "KHZ", "DN"))},
    ("Button_COM1_TOG", "key"): (1, "COM_SWAP"), ("Button_COM1_TOG", "hold"): (1, "COM_121_5"),
    ("Button_COM2_TOG", "key"): (2, "COM_SWAP"), ("Button_COM2_TOG", "hold"): (2, "COM_121_5"),
    ("Button_NAV1_TOG", "key"): (1, "NAV_SWAP"), ("Button_NAV2_TOG", "key"): (2, "NAV_SWAP"),
    ("Button_COM1^_OI", "turn"): (1, "HDG_10_UP"), ("Button_COM1^_OD", "turn"): (1, "HDG_10_DN"),
    ("Button_COM1^_II", "turn"): (1, "HDG_1_UP"), ("Button_COM1^_ID", "turn"): (1, "HDG_1_DN"),
    ("Button_COM1^_TOG", "key"): (1, "HDG_SYNC"),
    ("Button_COM2^_OI", "turn"): (1, "BARO_UP"), ("Button_COM2^_OD", "turn"): (1, "BARO_DN"),
    ("Button_COM2^_II", "turn"): (1, "BARO_UP"), ("Button_COM2^_ID", "turn"): (1, "BARO_DN"),
    ("Button_COM2^_TOG", "key"): (1, "BARO_STD"),
    ("Button_NAV1^_OI", "turn"): (1, "CRS_10_UP"), ("Button_NAV1^_OD", "turn"): (1, "CRS_10_DN"),
    ("Button_NAV1^_II", "turn"): (1, "CRS_1_UP"), ("Button_NAV1^_ID", "turn"): (1, "CRS_1_DN"),
    ("Button_NAV1^_TOG", "key"): (1, "CRS_CTR"),
    ("Button_XPDR^_OI", "turn"): (1, "PANEL_LT_UP"), ("Button_XPDR^_OD", "turn"): (1, "PANEL_LT_DN"),
    ("Button_XPDR^_II", "turn"): (1, "FLOOD_LT_UP"), ("Button_XPDR^_ID", "turn"): (1, "FLOOD_LT_DN"),
    ("Button_XPDR^_TOG", "key"): (1, "CABIN_LT"),
    ("Button_AP_OI", "turn"): (1, "ALT_100_UP"), ("Button_AP_OI", "held"): (1, "ALT_1000_UP"),
    ("Button_AP_OD", "turn"): (1, "ALT_100_DN"), ("Button_AP_OD", "held"): (1, "ALT_1000_DN"),
    ("Button_AP_II", "turn"): (1, "UP"), ("Button_AP_ID", "turn"): (1, "DN"), ("Button_AP_CRSR", "key"): (1, "VNV"),
    ("Button_XPDR_TOG", "tap"): (1, "IDENT"), ("Button_XPDR_TOG", "hold"): (1, "VFR"),
    **{(f"Button_XPDR_{r}", "once"): (1, "XPDR_MODE") for r in ifr1.KNOB},
    ("Button_AP_AP", "key"): (1, "AP"), ("Button_AP_HDG", "key"): (1, "HDG"), ("Button_AP_NAV", "key"): (1, "NAV"),
    ("Button_AP_APR", "key"): (1, "APR"), ("Button_AP_APR", "hold"): (1, "BC"),
    ("Button_AP_ALT", "key"): (1, "ALT"), ("Button_AP_ALT", "hold"): (1, "ARM"),
}


@FAMILY
def test_each_row_takes_its_panel_button(key):
    used = PROFILES[key].USES
    for (button, use), (device, name) in ROWS.items():
        assert used[button][use].source == ifr1.Panel(device, name), (button, use)
    assert used["Button_AP_VS"]["key"].source in (ifr1.Panel(1, "VS"), ifr1.KAP140_VS)
    for ring, own in ifr1.NAV2_COURSE.items():
        assert used[f"Button_NAV2^_{ring}"][ring == "TOG" and "key" or "turn"].source == own
    for ring, own in ifr1.SQUAWK_PAIRS.items():
        assert used[f"Button_XPDR_{ring}"]["turn"].source == own


@FAMILY
def test_fms1_and_fms2_take_their_units_keys_and_knob(key):
    used, p = PROFILES[key].USES, PROFILES[key]
    keys = {"DCT": "DIRECT", "MENU": "MENU", "CLR": "CLR", "ENT": "ENT", "CDI": "CDI", "OBS": "OBS", "MSG": "MSG",
            "FPL": "FPL", "VNAV": "VNAV", "PROC": "PROC", "CRSR": "FMS_CRSR"}
    rings = {"OI": "FMS_OUTER_CW", "OD": "FMS_OUTER_CCW", "II": "FMS_INNER_CW", "ID": "FMS_INNER_CCW"}
    for mode, unit in zip(("FMS1", "FMS2"), p.UNITS, strict=True):
        for ifr1_key, panel in {**keys, **rings}.items():
            use = "key" if ifr1_key in keys else "turn"
            assert used[f"Button_{mode}_{ifr1_key}"][use].source == ifr1.Panel(unit, panel), (mode, ifr1_key)
        assert used[f"Button_{mode}_TOG"]["tap"].source == ifr1.Panel(unit, "HOME")
        shift = "S_" if unit == 2 else ""
        for ring, way in (("II", "CW"), ("ID", "CCW")):
            assert used[f"Button_{mode}_{ring}"]["held"].source == ifr1.Panel(1, f"{shift}RANGE_{way}")


@pytest.mark.parametrize(("key", "tap", "hold"), [
    ("g1000", "FLC", "LVL"), ("cows-da40", "FLC", "LVL"), ("g3x", "FLC", "LVL"), ("gns", None, None),
    ("gtn", None, None), ("carenado-c182t", None, None), ("black-square-bonanza", "FD", "YD")])
def test_the_modifier_in_ap_taps_and_holds_by_autopilot(key, tap, hold):
    used = PROFILES[key].USES["Button_AP_TOG"]
    assert used["tap"].source == (tap and ifr1.Panel(1, tap)) and used["hold"].source == (hold and ifr1.Panel(1, hold))


@FAMILY
def test_every_key_event_is_one_checked_against_the_sdk(key):
    # tests/key_events.txt holds the key events checked against the SDK; the IFR-1 sends no others
    with open("tests/key_events.txt", encoding="utf-8") as f:
        checked = {line.strip() for line in f if line.strip() and not line.startswith("#")}
    sent = {name for *_, code in codes(key) for name in re.findall(r"\(>K:([^)]*)\)", code)}
    assert sent <= checked


@FAMILY
def test_the_ifr1_keeps_its_state_apart_from_the_panels(key):
    # every L: variable a code sets beyond the panel codes it sends is one of the IFR-1's own (the squawk pairs
    # forget the code VFR kept, as the panel's digits do)
    p = PROFILES[key]
    for button, entry in p.DEVICE.items():
        code = " ".join(profile.actions(entry).values())
        for u in p.USES[button].values():
            if isinstance(u.source, ifr1.Panel) and u.entry is not None:
                code = code.replace(ifr1.tapped(u.entry), "")
        for name in re.findall(r"\(>L:([A-Za-z0-9_]+)\)", code):
            assert name.startswith("AvionicsPanel_IFR1_") or name == "AvionicsPanel_Squawk_Kept", (button, name)


# ---------------- what the codes do ----------------
def squawk(code, ring):
    """The code a squawk ring's detent sets from this code (four octal digits as text)"""
    out = run(ifr1.SQUAWK_PAIRS[ring].code, {"TRANSPONDER CODE:1": int(code, 16)})
    assert out[-1] == ("L:AvionicsPanel_Squawk_Kept", 0)
    (event, value), = [o for o in out if o[0] == "K:XPNDR_SET"]
    return f"{value:04x}"


@pytest.mark.parametrize(("code", "ring", "want"), [
    ("7000", "OI", "7100"), ("7700", "OI", "0000"), ("0723", "OI", "1023"), ("1023", "OD", "0723"),
    ("0000", "OD", "7700"), ("7000", "II", "7001"), ("7007", "II", "7010"), ("7077", "II", "7000"),
    ("7000", "ID", "7077"), ("1234", "ID", "1233"), ("4567", "OI", "4667"), ("1200", "ID", "1277")])
def test_a_squawk_ring_steps_its_two_digits_and_keeps_the_others(code, ring, want):
    assert squawk(code, ring) == want


def test_every_squawk_code_steps_round_and_back():
    for high, low in itertools.product(range(64), repeat=2):
        code = f"{high // 8}{high % 8}{low // 8}{low % 8}"
        for up, down in (("OI", "OD"), ("II", "ID")):
            stepped = squawk(code, up)
            assert re.fullmatch("[0-7]{4}", stepped) and squawk(stepped, down) == code


def test_crs2_turns_and_centres_nav_2():
    assert run(ifr1.NAV2_COURSE["OI"].code, {"NAV OBS:2": 355}) == [("K:VOR2_SET", 5)]
    assert run(ifr1.NAV2_COURSE["OD"].code, {"NAV OBS:2": 5}) == [("K:VOR2_SET", 355)]
    assert run(ifr1.NAV2_COURSE["II"].code) == [("K:VOR2_OBI_INC", None)]
    assert run(ifr1.NAV2_COURSE["ID"].code) == [("K:VOR2_OBI_DEC", None)]
    assert run(ifr1.NAV2_COURSE["TOG"].code, {"NAV HAS LOCALIZER:2": 0, "NAV HAS NAV:2": 1, "NAV RADIAL:2": 90}) \
        == [("K:VOR2_SET", 270)]


def press(state, entry, event="press"):
    """Runs an entry's code of this event ("press", "release", "long"; a code alone is a press) with the L:
    variables of state, which it updates: what it sent besides them"""
    code = entry if isinstance(entry, str) else entry.get(event)
    if code is None:
        return []
    unset = {f"L:{name}": 0 for name in re.findall(r"\(L:(AvionicsPanel_IFR1_\w+), Bool\)", code)}   # read as 0
    out = run(code, {**unset, **state})
    for name, value in out:
        if name.startswith("L:"):
            state[name] = value
    return [o for o in out if not o[0].startswith("L:AvionicsPanel_IFR1_")]


DA40 = PROFILES["cows-da40"].DEVICE
FLC, LVL = FAMILIES["cows-da40"].DEVICE[1]["FLC"], FAMILIES["cows-da40"].DEVICE[1]["LVL"]


def test_a_tap_of_the_modifier_sends_its_tap():
    state = {}
    assert press(state, DA40["Button_AP_TOG"]) == []
    assert press(state, DA40["Button_AP_TOG"], "release") == run(FLC)
    assert state["L:AvionicsPanel_IFR1_AP"] == 0


def test_a_hold_of_the_modifier_sends_its_hold():
    state = {}
    press(state, DA40["Button_AP_TOG"])
    assert press(state, DA40["Button_AP_TOG"], "long") == run(LVL)
    assert state["L:AvionicsPanel_IFR1_AP"] == 0


def test_a_ring_turned_with_the_modifier_held_sends_its_held_code_and_the_modifier_nothing():
    state = {}
    assert press(state, DA40["Button_AP_OI"]) == [("K:AP_ALT_VAR_INC", None)]
    press(state, DA40["Button_AP_TOG"])
    assert press(state, DA40["Button_AP_OI"]) == [("K:AP_ALT_VAR_INC", 1000)]
    assert press(state, DA40["Button_AP_OD"]) == [("K:AP_ALT_VAR_DEC", 1000)]
    assert press(state, DA40["Button_AP_TOG"], "release") == []
    assert press(state, DA40["Button_AP_OI"]) == [("K:AP_ALT_VAR_INC", None)]


def test_a_change_of_mode_lets_go_of_every_modifier():
    for name in ifr1.MODIFIED:
        state = {}
        press(state, DA40[f"Button_{name}_TOG"])
        assert state[f"L:AvionicsPanel_IFR1_{name}"] == 1
        press(state, DA40["Button_UNSHIFT_SW"])
        assert state[f"L:AvionicsPanel_IFR1_{name}"] == 0


@pytest.mark.parametrize("pressed", ["FMS1", "FMS2", "AP", "XPDR"])
@pytest.mark.parametrize("released", ["FMS1", "FMS2", "AP", "XPDR"])
@pytest.mark.parametrize("event", ["release", "long"])
def test_a_modifier_let_go_after_a_change_of_mode_sends_nothing(pressed, released, event):
    # MobiFlight delivers the release to the mode the user changed to, after Button_UNSHIFT_SW
    state = {"TRANSPONDER CODE:1": 0x7000}
    press(state, DA40[f"Button_{pressed}_TOG"])
    press(state, DA40["Button_UNSHIFT_SW"])
    assert press(state, DA40[f"Button_{released}_TOG"], event) == []


@pytest.mark.parametrize("button", ["AP_APR", "AP_ALT", "COM1_TOG", "COM2_TOG", "FMS1_CLR", "FMS2_PROC"])
@pytest.mark.parametrize("event", ["release", "long"])
def test_a_key_with_a_hold_let_go_after_a_change_of_mode_sends_nothing(button, event):
    state = {}
    press(state, DA40[f"Button_{button}"])
    press(state, DA40["Button_UNSHIFT_SW"])
    assert press(state, DA40[f"Button_{button}"], event) == []
    press(state, DA40[f"Button_{button}"])                               # pressed and let go in one mode: it sends
    assert press(state, DA40[f"Button_{button}"], event) != []


def test_the_fms_ring_with_the_modifier_held_sets_the_units_map_range():
    state = {}
    press(state, DA40["Button_FMS1_TOG"])
    assert press(state, DA40["Button_FMS1_II"]) == [("H:AS1000_PFD_RANGE_INC", None)]
    assert press(state, DA40["Button_FMS1_TOG"], "release") == []
    assert press(state, DA40["Button_FMS1_II"]) == [("H:AS1000_PFD_FMS_Upper_INC", None)]


def test_the_xpdr_rings_with_the_modifier_held_switch_the_mode_once_a_hold():
    state = {"TRANSPONDER STATE:1": 1, "TRANSPONDER CODE:1": 0x7000}
    press(state, DA40["Button_XPDR_TOG"])
    assert press(state, DA40["Button_XPDR_OI"]) == [("A:TRANSPONDER STATE:1", 4)]
    assert press(state, DA40["Button_XPDR_II"]) == []                   # one switch a hold
    assert press(state, DA40["Button_XPDR_TOG"], "long") == []          # and no VFR after a detent
    press(state, DA40["Button_XPDR_TOG"])
    assert press(state, DA40["Button_XPDR_TOG"], "release") == [("K:XPNDR_IDENT_ON", None)]


@FAMILY
def test_holding_xpdr_toggles_the_vfr_code(key):
    used = PROFILES[key].USES["Button_XPDR_TOG"]
    assert used["hold"].entry == FAMILIES[key].DEVICE[1]["VFR"] and used["tap"].entry == FAMILIES[key].DEVICE[1][
        "IDENT"]


def test_a_vfr_code_replaces_the_one_xpdr_holds():
    p = ifr1.build("g1000", "1200")
    assert "0x1200" in p.DEVICE["Button_XPDR_TOG"]["long"] and "0x7000" not in p.DEVICE["Button_XPDR_TOG"]["long"]
    with pytest.raises(ValueError):
        ifr1.build("g1000", "1280")


@FAMILY
def test_a_held_key_sends_its_amber_function_and_ap_and_nav_send_on_press(key):
    family, p = FAMILIES[key], PROFILES[key]
    held = {"Button_AP_APR": (1, "BC"), "Button_AP_ALT": (1, "ARM"), "Button_COM1_TOG": (1, "COM_121_5"),
            "Button_COM2_TOG": (2, "COM_121_5")}
    for mode, unit in zip(("FMS1", "FMS2"), p.UNITS, strict=True):
        held.update({f"Button_{mode}_CLR": (unit, "MAP"), f"Button_{mode}_MENU": (unit, "NRST"),
                     f"Button_{mode}_PROC": (unit, "TERR")})
    for button, (device, amber) in held.items():
        entry, plain = p.DEVICE.get(button), p.USES[button]["key"].entry
        if amber in family.DEVICE[device] and family.DEVICE[device][amber] != plain:
            # the tap on the release only, once the key went down in this mode (a press of its own)
            down = f"AvionicsPanel_IFR1_{button.removeprefix('Button_')}_Down"
            assert entry["press"] == f"1 (>L:{down})", button
            assert ifr1.tapped(family.DEVICE[device][amber]) in entry["long"], button
            if plain is not None:
                assert ifr1.tapped(plain) in entry["release"], button
            for code in (entry["release"], entry["long"]):
                assert code.startswith(f"(L:{down}, Bool) if{{") and code.endswith(f"0 (>L:{down})"), button
        else:
            assert entry == plain, button
    for button in ("Button_AP_AP", "Button_AP_NAV", "Button_AP_HDG"):
        assert p.DEVICE[button] == family.DEVICE[1][button.rsplit("_", 1)[1]]


@pytest.mark.parametrize(("key", "fms1", "fms2"), [
    ("g1000", "AS1000_PFD_", "AS1000_MFD_"), ("cows-da40", "AS1000_PFD_", "AS1000_MFD_"),
    ("carenado-c182t", "AS1000_PFD_", "AS1000_MFD_"), ("gns", "AS530_", "AS430_"),
    ("g3x", "AS3X_Touch_1_", "AS3X_Touch_2_"),
    ("black-square-bonanza", "AS530_", "AS430_")])
def test_fms1_and_fms2_are_the_units_a_display_is_numbered_by(key, fms1, fms2):
    p = PROFILES[key]
    assert fms1 in p.DEVICE["Button_FMS1_OI"] and fms2 not in p.DEVICE["Button_FMS1_OI"]
    assert fms2 in p.DEVICE["Button_FMS2_OI"] and fms1 not in p.DEVICE["Button_FMS2_OI"]


def test_the_bonanzas_outer_ring_with_the_modifier_held_is_the_kln_90bs_left_outer_knob():
    used = PROFILES["black-square-bonanza"].USES
    assert used["Button_FMS1_OI"]["held"].source == ifr1.Panel(1, "PAN_RIGHT")
    assert used["Button_FMS1_II"]["held"].source == ifr1.Panel(1, "RANGE_CW")
    assert used["Button_FMS2_OI"]["held"].source == ifr1.Panel(1, "S_RANGE_CW")


def test_the_kap_140s_vs_key_leaves_alt_hold():
    for key in ("gns", "gtn", "carenado-c182t"):
        assert PROFILES[key].DEVICE["Button_AP_VS"] == parts.KAP140_VS
    assert PROFILES["cows-da40"].DEVICE["Button_AP_VS"] == FAMILIES["cows-da40"].DEVICE[1]["VS"]


# ---------------- the lights ----------------
FLAGS = ("AUTOPILOT MASTER", "AUTOPILOT HEADING LOCK", "AUTOPILOT NAV1 LOCK", "AUTOPILOT APPROACH HOLD",
         "AUTOPILOT ALTITUDE LOCK", "AUTOPILOT VERTICAL HOLD", "AUTOPILOT BACKCOURSE HOLD")


@pytest.mark.parametrize("autopilot", sorted(ifr1.LEDS))
def test_every_light_reads_0_or_1_and_sets_nothing(autopilot):
    reads = ifr1.LEDS[autopilot]
    assert tuple(reads) == ifr1.LIGHTS
    for read in reads.values():
        assert not any(sets(t) for t in TOKEN.findall(read))
        for values in itertools.product((0, 1), repeat=len(FLAGS)):
            stack = run(f"{read} (>L:Out)", dict(zip(FLAGS, values, strict=True)))
            assert stack[0][1] in (0, 1, True, False)


@pytest.mark.parametrize("autopilot", sorted(ifr1.LEDS))
def test_each_light_shows_its_own_flag(autopilot):
    # each light alone with its flag (and with the autopilot engaged, which the KAP 140's need); BC lights APR
    # where the autopilot's APR shows BC
    own = dict(zip(ifr1.LIGHTS, FLAGS, strict=False))
    for name, flag in own.items():
        assert light(autopilot, name) == 0, name
        on = {"AUTOPILOT MASTER": 1, flag: 1}
        assert light(autopilot, name, **on) == 1, name
        for other in own:
            if other not in (name, "AP Master"):
                assert light(autopilot, other, **on) == 0, (name, other)
    assert light(autopilot, "AP APR", **{"AUTOPILOT MASTER": 1, "AUTOPILOT BACKCOURSE HOLD": 1}) == (
        autopilot in ("kap140", "kfc150"))


def light(autopilot, name, **flags):
    return int(run(f"{ifr1.LEDS[autopilot][name]} (>L:Out)", dict.fromkeys(FLAGS, 0) | flags)[0][1])


def test_the_kap_140s_mode_lights_go_with_the_autopilot_and_apr_shows_rev():
    on = {"AUTOPILOT MASTER": 1}
    assert light("kap140", "AP HDG", **{"AUTOPILOT HEADING LOCK": 1}) == 0
    assert light("kap140", "AP HDG", **on, **{"AUTOPILOT HEADING LOCK": 1}) == 1
    assert light("kap140", "AP APR", **on, **{"AUTOPILOT BACKCOURSE HOLD": 1}) == 1
    assert light("gfc700", "AP HDG", **{"AUTOPILOT HEADING LOCK": 1}) == 1        # on the flight director alone
    assert light("kfc150", "AP APR", **{"AUTOPILOT BACKCOURSE HOLD": 1}) == 1


@pytest.mark.parametrize(("key", "autopilot"), [
    ("g1000", "gfc700"), ("cows-da40", "gfc700"), ("g3x", "gfc500"), ("gns", "kap140"), ("gtn", "kap140"),
    ("carenado-c182t", "kap140"), ("black-square-bonanza", "kfc150")])
def test_each_profile_has_its_autopilots_lights(key, autopilot):
    assert ifr1.LEDS[autopilot] == PROFILES[key].LEDS


# ---------------- the project ----------------
@FAMILY
def test_the_project_has_the_structure_mobiflight_reads(key):
    project = ifr1.project(PROFILES[key], "2026-11-17, abc1234")
    assert project["_version"] == profile.SCHEMA
    assert project["Name"] == f"Avionics Panel for the IFR-1: {FAMILIES[key].NAME} (2026-11-17, abc1234)"
    (config,) = project["ConfigFiles"]
    items = config["ConfigItems"]
    inputs = [i for i in items if i["Type"] == "InputConfigItem"]
    outputs = [i for i in items if i["Type"] == "OutputConfigItem"]
    assert len(items) == len(inputs) + len(outputs) and len({i["GUID"] for i in items}) == len(items)
    controller = {"Name": "IFR1", "Serial": "JS-096db160-8ba2-11ed-8002-444553540000"}   # Octavi's registry fix
    assert all(i["Controller"] == controller and i["Active"] is True for i in items)
    assert [i["Device"]["Name"] for i in inputs] == [b for b in ifr1.BUTTONS if b in PROFILES[key].DEVICE]
    for item in inputs:
        assert item["Device"]["Type"] == "Button" and item["button"]["onHold"] is None
        if item["Device"]["Name"].rsplit("_", 1)[1] in ifr1.KNOB:     # a knob sends presses alone
            assert item["button"]["onRelease"] is None and item["button"]["onLongRelease"] is None
    # the labels of octavi.joystick.json's outputs, which MobiFlight finds a light by
    assert [o["Device"]["Pin"] for o in outputs] == ["AP Master", "AP HDG", "AP NAV", "AP APR", "AP ALT", "AP VS"]
    for out in outputs:
        assert out["Source"]["SimConnectValue"]["VarType"] == 2 and out["DeviceType"] == "Output"
        assert out["Device"]["Type"] == "Output" and out["Device"]["Name"] == out["Device"]["Pin"]
    assert json.loads(profile.dumps(project)) == project


def test_the_command_line_writes_an_ifr1_project(tmp_path, capsys):
    out = tmp_path / "x.mfproj"
    cli.main(["--ifr1", "carenado-c182t", "--vfr", "1200", "-o", str(out), "--stamp", "s"])
    project = json.loads(out.read_text(encoding="utf-8"))
    assert project["Name"] == "Avionics Panel for the IFR-1: Carenado C182T (s)"
    assert "0x1200" in out.read_text(encoding="utf-8")
    err = capsys.readouterr().err
    assert "93 buttons mapped" in err and "unmapped XPDR^_II, XPDR^_ID: the C182T dims" in err


@pytest.mark.parametrize("extra", [["--from", "x.mfproj"], ["--serials", "JS-a", "JS-b"], ["--unit1", "gns530"],
                                   ["--cockpit", "g1000"]])
def test_the_ifr1_takes_no_joysticks_or_parts(extra, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--ifr1", "g1000", *extra])
    assert "--ifr1 is a whole profile, bound to the IFR-1" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_the_cards_zip_holds_the_ifr1s_cards_and_cheat_sheets(tmp_path):
    out = tmp_path / "cards.zip"
    cli.main(["--cards", str(out)])
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    for key in FAMILIES:
        assert {f"avionics-panel-ifr1-{key}-card.html", f"avionics-panel-ifr1-{key}-sheet.html"} <= names


# ---------------- the card and the cheat sheet ----------------
@FAMILY
@pytest.mark.parametrize("words", [False, True])
def test_a_page_lists_every_reason_and_names_the_profile(key, words):
    page = ifr1_card.page(PROFILES[key], "v", words)
    assert f"IFR-1: {FAMILIES[key].NAME}" in page and ifr1.filename(key) in page
    p = PROFILES[key]
    shown = {r for b, r in p.UNMAPPED.items() if b != "Button_SHIFT_SW"}
    # and the reasons of uses that send nothing on a mapped button: a tap or ⇆'s tap the profile leaves unmapped
    shown |= {u.reason for b, used in p.USES.items() if b in p.DEVICE and b != "Button_UNSHIFT_SW"
              for use, u in used.items() if u.reason and use in ("key", "tap", "turn")}
    for reason in shown:
        assert html.escape(reason) in page, reason
    assert ("<footer>" in page) == bool(shown)


@FAMILY
def test_every_mapped_use_has_words(key):
    # what the cheat sheet says comes from the panel's words; a use that sends something has some (Grid.say)
    words = ifr1_card.words_of(key)
    for used in PROFILES[key].USES.values():
        for u in used.values():
            if isinstance(u.source, ifr1.Panel) and u.entry is not None:
                assert words[u.source.device, u.source.button], u.source


def test_the_card_names_the_units_of_fms1_and_fms2():
    page = ifr1_card.page(PROFILES["cows-da40"])
    assert "FMS1: PFD" in page and "FMS2: MFD" in page
    assert "FMS1: GNS 530" in ifr1_card.page(PROFILES["gns"])


@FAMILY
def test_the_ifr1_page_links_every_profiles_downloads(key):
    with open("docs/using/ifr1.md", encoding="utf-8") as f:
        page = f.read()
    assert f"/rolling/{ifr1.filename(key)}" in page
    for kind in ("card.html", "sheet.html"):
        assert f"/cards/avionics-panel-ifr1-{key}-{kind}" in page


def test_the_cells_say_what_the_controls_do():
    da40 = ifr1_card.page(PROFILES["cows-da40"], words=True)
    assert "<td><i>tap:</i> COM 1 flip-flop; <i>hold:</i> COM 1 to 121.5</td>" in da40
    assert "<td>selected altitude 100 ft; <i>⇆ held:</i> 1000 ft</td>" in da40
    assert "<td><i>tap:</i> FLC mode; <i>hold:</i> wings and pitch level, engages AP</td>" in da40
    assert "<td>COM 2 MHz</td><td>COM 2 kHz</td>" in da40 and "COM 2 to 121.5" in da40
    assert "<th>CRS1 (NAV1 shifted)</th><td>course of the CDI (PFD CRS knob) 10°</td>" in da40
    assert "<th>CRS2 (NAV2 shifted)</th><td>NAV 2 course +10° / NAV 2 course -10°</td>" in da40
    assert "a hold of over 0.35 s" in da40
    card = ifr1_card.page(PROFILES["cows-da40"])
    assert "<td><i>tap:</i> COM1_RADIO_SWAP; <i>hold:</i> COM_RADIO_SET_HZ</td>" in card
    assert "<td><i>tap:</i> AP_APR_HOLD; <i>hold:</i> AP_BC_HOLD</td>" in card
    assert "FMS1: PFD" in ifr1_card.page(PROFILES["g3x"]) and "FMS2: MFD" in ifr1_card.page(PROFILES["g3x"])
    bonanza = ifr1_card.page(PROFILES["black-square-bonanza"], words=True)
    assert "GNS 430 CDI: GPS or VLOC" in bonanza and "course of the CDI" not in bonanza
    assert "<td><i>tap:</i> flight director; <i>hold:</i> yaw damper, if fitted</td>" in bonanza
    assert "<td>heading bug 10°</td><td>heading bug 1°</td>" in da40 and "<td>COM 2 flip-flop" not in da40
    assert "<i>tap:</i> COM 2 flip-flop" in da40 and "<td>NAV 2 flip-flop</td>" in da40
    c182t = ifr1_card.page(PROFILES["carenado-c182t"], words=True)
    assert "only held while turning a ring" in c182t
    assert "<i>⇆ held, first detent:</i> transponder standby or ALT" in c182t


def test_the_words_are_escaped(monkeypatch):
    words = ifr1_card.words_of("cows-da40")
    monkeypatch.setattr(ifr1_card, "words_of", lambda key: {**words, (1, "NAV_SWAP"): "<b>a & b</b>"})
    page = ifr1_card.page(PROFILES["cows-da40"], words=True)
    assert "&lt;b&gt;a &amp; b&lt;/b&gt;" in page and "<b>a & b</b>" not in page


@pytest.mark.parametrize("key", ["gtn", "black-square-bonanza"])
def test_a_gtn_key_sends_its_key_up_only_where_it_went_down(key):
    # TDS's GTN keys are held as long as the panel's key: a release in another mode sends no key-up there
    device = PROFILES[key].DEVICE
    for first, second in (("FMS1", "FMS2"), ("FMS2", "FMS1")):
        for name in ("DCT", "CRSR"):
            state = {}
            down = press(state, device[f"Button_{first}_{name}"])
            assert down and press(state, device[f"Button_{second}_{name}"], "release") == []
            up = press(state, device[f"Button_{first}_{name}"], "release")
            assert [n for n, _ in up] == [n for n, _ in down if n.startswith("K:GPS_")]


def test_a_tap_sends_a_gtn_keys_press_before_its_release():
    # ⇆ tapped in FMS1 of the GTN profile sends HOME, which TDS's GTN takes as a key down and up: down first
    home = FAMILIES["gtn"].DEVICE[1]["HOME"]
    assert isinstance(home, dict) and home["press"] and home["release"]
    state = {}
    press(state, PROFILES["gtn"].DEVICE["Button_FMS1_TOG"])
    assert press(state, PROFILES["gtn"].DEVICE["Button_FMS1_TOG"], "release") == run(home["press"]) + run(
        home["release"])
