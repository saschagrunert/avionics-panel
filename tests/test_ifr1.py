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
from mobiflight import cards, ifr1, ifr1_card, ifr1_grid, ifr1_sheet, profile
from mobiflight.families import FAMILIES, parts
from tests.rpn import READ, TOKEN, every_path, run, sets, well_formed
from tests.test_mobiflight import unit as unit_of

FAMILY = pytest.mark.parametrize("key", sorted(FAMILIES))
PROFILES = {key: ifr1.build(key) for key in FAMILIES}
EXTRA = {key: ifr1.EXTRA.get(key, dict)() for key in FAMILIES}       # each profile's uses over the panel's

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
    assert "Button_SHIFT_SW" in p.DEVICE and "Button_UNSHIFT_SW" in p.DEVICE


@FAMILY
def test_codes_are_well_formed(key):
    # as the panel's (test_mobiflight.test_codes_are_well_formed): known tokens, closed blocks, something set, no
    # "@", room in MobiFlight's 1024-byte message, and the stack as found down every way of its blocks
    for *_, code in codes(key):
        well_formed(code)
        every_path(code)


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


def sent_by(p, button, use):
    """What an IFR-1 button sends for one of its uses, run as MobiFlight sends its events (every variable 1): a
    detent alone or with ⇆ held, a key pressed and let go, held, or held TALK_MS; None where its entry has no event
    for it"""
    entry, state = p.DEVICE[button], {}
    if use == "held":
        state[f"L:{ifr1._var(ifr1.mode(button))}"] = 1
    if isinstance(entry, str):
        return press(state, entry, default=1)
    out = press(state, entry, default=1)
    event = {"key": "release", "tap": "release", "hold": "long" if {"long", "hold"} <= set(entry) else "hold",
             "long_hold": "hold"}[use]
    if event not in entry:
        return None
    out += press(state, entry, event, default=1)
    if use == "hold" and "_Again" in entry.get("hold", ""):                # a hold of two steps: let go after it
        out += press(state, entry, "release", default=1)
    return out


@FAMILY
def test_every_use_sends_its_panel_sources_code(key):
    # a Panel source sends what the panel button sends in the profile, whole, or carries its reason; a Plus the
    # panel button's code at once, then the IFR-1's own; and the button sends each use's code, run, on its event
    family, p = FAMILIES[key], PROFILES[key]
    for button, used in p.USES.items():
        for use, u in used.items():
            if isinstance(u.source, ifr1.Panel):
                table, rest = family.DEVICE[u.source.device], family.UNMAPPED[u.source.device]
                if u.source.button in table:
                    assert u.entry == table[u.source.button] and u.reason is None, (button, use)
                else:
                    assert u.entry is None and u.reason == rest[u.source.button], (button, use)
            elif isinstance(u.source, ifr1.Own):
                assert u.entry == u.source.code, (button, use)
            elif isinstance(u.source, ifr1.Plus):
                panel = family.DEVICE[u.source.panel.device][u.source.panel.button]
                assert u.entry == f"{ifr1.tapped(panel)} {u.source.own.code}", (button, use)
            else:
                assert u.source is None and u.entry is None, (button, use)
            if u.entry is None or button.endswith("SHIFT_SW"):
                continue
            want = press({}, ifr1.tapped(u.entry), default=1)
            if use == "hold" and "_Again" in p.DEVICE[button].get("hold", ""):                  # two steps, apart
                want = press({}, u.entry, default=1) + press({}, u.entry, "release", default=1)
            if isinstance(u.entry, dict) and set(u.entry) == {"press", "release"} and use == "key":
                want = press({}, u.entry, default=1) + press({}, u.entry, "release", default=1)   # a GTN key-up
            assert sent_by(p, button, use) == want, (button, use)


# the rows every profile takes from the panel alike: (IFR-1 button, use) -> (device, panel button)
ROWS = {
    **{(f"Button_{m}_{r}", "turn"): (d, f"{kind}_{step}_{way}") for m, d, kind in (
        ("COM1", 1, "COM"), ("COM2", 2, "COM"), ("NAV1", 1, "NAV"), ("NAV2", 2, "NAV"))
       for r, step, way in (("OI", "MHZ", "UP"), ("OD", "MHZ", "DN"), ("II", "KHZ", "UP"), ("ID", "KHZ", "DN"))},
    ("Button_COM1_TOG", "key"): (1, "COM_SWAP"), ("Button_COM1_TOG", "hold"): (1, "COM1"),
    ("Button_COM1_TOG", "long_hold"): (1, "MIC1"),
    ("Button_COM2_TOG", "key"): (2, "COM_SWAP"), ("Button_COM2_TOG", "hold"): (1, "COM2"),
    ("Button_COM2_TOG", "long_hold"): (1, "MIC2"),
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
    ("Button_XPDR_OI", "held"): (1, "PANEL_LT_UP"), ("Button_XPDR_OD", "held"): (1, "PANEL_LT_DN"),
    ("Button_XPDR_II", "held"): (1, "FLOOD_LT_UP"), ("Button_XPDR_ID", "held"): (1, "FLOOD_LT_DN"),
    ("Button_XPDR^_TOG", "key"): (1, "VFR"), ("Button_XPDR^_TOG", "hold"): (1, "CABIN_LT"),
    ("Button_AP_OI", "turn"): (1, "ALT_1000_UP"), ("Button_AP_OD", "turn"): (1, "ALT_1000_DN"),
    ("Button_AP_II", "turn"): (1, "ALT_100_UP"), ("Button_AP_ID", "turn"): (1, "ALT_100_DN"),
    ("Button_AP_II", "held"): (1, "UP"), ("Button_AP_ID", "held"): (1, "DN"), ("Button_AP_CRSR", "hold"): (1, "VNV"),
    ("Button_XPDR_TOG", "tap"): (1, "IDENT"),
    ("Button_AP_AP", "key"): (1, "AP"), ("Button_AP_HDG", "key"): (1, "HDG"), ("Button_AP_NAV", "key"): (1, "NAV"),
    ("Button_AP_APR", "key"): (1, "APR"), ("Button_AP_APR", "hold"): (1, "BC"),
    ("Button_AP_ALT", "key"): (1, "ALT"), ("Button_AP_ALT", "hold"): (1, "ARM"),
}


@FAMILY
def test_each_row_takes_its_panel_button(key):
    used = PROFILES[key].USES
    for (button, use), (device, name) in ROWS.items():
        source = used[button][use].source
        if isinstance(source, ifr1.Own) and (button, use) in EXTRA[key]:     # the profile's own in place of it
            continue
        if isinstance(source, ifr1.Plus) and (button, use) in EXTRA[key]:     # the panel's, and the profile's own
            source = source.panel
        assert source == ifr1.Panel(device, name), (button, use)
    assert used["Button_AP_VS"]["key"].source == ifr1.Panel(1, "VS")
    for ring, own in ifr1.NAV2_COURSE.items():
        assert used[f"Button_NAV2^_{ring}"][ring == "TOG" and "key" or "turn"].source == own
    for ring, own in ifr1.SQUAWK_PAIRS.items():
        assert used[f"Button_XPDR_{ring}"]["turn"].source == own
    for button in ("Button_AP_TOG", "Button_XPDR_TOG", "Button_FMS1_TOG", "Button_FMS2_TOG"):
        assert used[button]["hold"].source is None, button               # a modifier has no hold
    assert used["Button_AP_CRSR"]["key"].source is None                    # VNV held only


@FAMILY
def test_fms1_and_fms2_take_their_units_keys_and_knob(key):
    used, p = PROFILES[key].USES, PROFILES[key]
    keys = {"DCT": "DIRECT", "MENU": "MENU", "CLR": "CLR", "ENT": "ENT", "CDI": "CDI", "OBS": "OBS", "MSG": "MSG",
            "FPL": "FPL", "VNAV": "VNAV", "PROC": "PROC", "CRSR": "FMS_CRSR"}
    rings = {"OI": "FMS_OUTER_CW", "OD": "FMS_OUTER_CCW", "II": "FMS_INNER_CW", "ID": "FMS_INNER_CCW"}
    for mode, unit in zip(("FMS1", "FMS2"), p.UNITS, strict=True):
        tds = ifr1.tds_gtn(FAMILIES[key], unit)
        for ifr1_key, panel in {**keys, **rings}.items():
            use = "key" if ifr1_key in keys else "turn"
            source = used[f"Button_{mode}_{ifr1_key}"][use].source
            if (f"Button_{mode}_{ifr1_key}", use) in EXTRA[key]:          # the profile's own, over the panel's
                assert source == EXTRA[key][f"Button_{mode}_{ifr1_key}", use], (mode, ifr1_key)
                source = getattr(source, "panel", ifr1.Panel(unit, panel))
            elif tds and ifr1_key in ifr1.TDS_KEYS:                       # TDS's GTN: its volume and push
                continue
            elif ifr1_key == "VNAV" and key in ("g1000", "cows-da40"):          # the NXi's VNAV: its GFC 700's VNV
                assert source == ifr1.Panel(1, "VNV"), mode
                continue
            assert source == ifr1.Panel(unit, panel), (mode, ifr1_key)
        assert used[f"Button_{mode}_TOG"]["tap"].source == ifr1.Panel(unit, "HOME")
        shift = "S_" if unit == 2 else ""
        for ring, way in (("II", "CW"), ("ID", "CCW")):
            assert used[f"Button_{mode}_{ring}"]["held"].source == ifr1.Panel(1, f"{shift}RANGE_{way}")


@pytest.mark.parametrize(("key", "held"), [
    ("g1000", "FLC"), ("cows-da40", "FLC"), ("g3x", "FLC"), ("gns", None), ("gtn", None), ("carenado-c182t", None),
    ("black-square-bonanza", "FD")])
def test_the_modifier_in_ap_only_modifies_and_vs_held_is_flc_or_fd(key, held):
    used = PROFILES[key].USES["Button_AP_TOG"]
    assert used["tap"].source is None and used["hold"].source is None
    vs = PROFILES[key].USES["Button_AP_VS"]
    assert vs.get("hold") is None if held is None else vs["hold"].source == ifr1.Panel(1, held)
    for name in ifr1.MODIFIED:                    # let go after a hold as after a tap: its tap, and it leaves its layer
        entry = PROFILES[key].DEVICE.get(f"Button_{name}_TOG")
        assert entry is None or (entry["long"] == entry["release"] and entry["long"].endswith(
            f"0 (>L:{ifr1._var(name)})")), name


@FAMILY
def test_every_key_event_is_one_checked_against_the_sdk(key):
    # tests/key_events.txt holds the key events checked against the SDK; the IFR-1 sends no others
    with open("tests/key_events.txt", encoding="utf-8") as f:
        checked = {line.strip() for line in f if line.strip() and not line.startswith("#")}
    sent = {name for *_, code in codes(key) for name in re.findall(r"\(>K:(?:2:)?([^)]*)\)", code)}
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
            elif isinstance(u.source, ifr1.Own) and u.source in EXTRA[key].values():   # the aircraft's own state
                code = code.replace(u.entry, "")
        for name in re.findall(r"\(>L:([A-Za-z0-9_]+)\)", code):
            assert name.startswith("AvPanelIFR1_") or name == "AvionicsPanel_Squawk_Kept", (button, name)


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


def press(state, entry, event="press", default=None):
    """Runs an entry's code of this event ("press", "release", "long", "hold"; a code alone is a press) with the L:
    variables of state, which it updates: what it sent besides them (default: as rpn.run()'s)"""
    code = entry if isinstance(entry, str) else entry.get(event)
    if code is None:
        return []
    unset = {f"L:{name}": 0 for name in re.findall(r"\(L:(AvPanelIFR1_\w+), Bool\)", code)}   # read as 0
    out = run(code, {**unset, **state}, default=default)
    for name, value in out:
        if name.startswith("L:"):
            state[name] = value
    return [o for o in out if not o[0].startswith("L:AvPanelIFR1_")]


DA40 = PROFILES["cows-da40"].DEVICE
FLC, LVL = FAMILIES["cows-da40"].DEVICE[1]["FLC"], FAMILIES["cows-da40"].DEVICE[1]["LVL"]


def test_a_tap_of_the_modifier_sends_its_tap():
    state = {}
    assert press(state, DA40["Button_AP_TOG"]) == []
    assert press(state, DA40["Button_AP_TOG"], "release") == []                 # AP's ⇆ has no tap
    assert state["L:AvPanelIFR1_AP"] == 0
    assert press(state, DA40["Button_XPDR_TOG"]) == []
    assert press(state, DA40["Button_XPDR_TOG"], "release") == [("K:XPNDR_IDENT_ON", None)]


@pytest.mark.parametrize("name", [m for m in ifr1.MODIFIED if m != "AP"])    # AP's ⇆ has no tap
def test_a_modifier_held_without_a_turn_sends_its_tap(name):
    # ⇆ held HOLD_MS or longer and let go without a detent: its tap all the same, as a slow IDENT or HOME
    state = {"TRANSPONDER CODE:1": 0x7000, "L:AvionicsPanel_G1000_Engine": 0}
    press(state, DA40[f"Button_{name}_TOG"])
    tapped = press(dict(state), DA40[f"Button_{name}_TOG"], "release")
    assert tapped and press(state, DA40[f"Button_{name}_TOG"], "long") == tapped
    assert state[f"L:AvPanelIFR1_{name}"] == 0


def test_a_ring_turned_with_the_modifier_held_sends_its_held_code_and_the_modifier_nothing():
    state = {"AUTOPILOT VERTICAL HOLD": 1}
    assert press(state, DA40["Button_AP_OI"]) == [("K:AP_ALT_VAR_INC", 1000)]
    assert press(state, DA40["Button_AP_II"]) == [("K:AP_ALT_VAR_INC", None)]
    press(state, DA40["Button_AP_TOG"])
    assert press(state, DA40["Button_AP_OI"]) == [("K:AP_ALT_VAR_INC", 1000)]       # the same with ⇆ held
    assert press(state, DA40["Button_AP_II"]) == [("K:AP_VS_VAR_INC", None)]        # the rate
    assert press(state, DA40["Button_AP_TOG"], "release") == []
    assert press(state, DA40["Button_AP_II"]) == [("K:AP_ALT_VAR_INC", None)]


def test_a_change_of_mode_lets_go_of_every_modifier():
    for name in ifr1.MODIFIED:
        state = {}
        press(state, DA40[f"Button_{name}_TOG"])
        assert state[f"L:AvPanelIFR1_{name}"] == 1
        press(state, DA40["Button_UNSHIFT_SW"])
        assert state[f"L:AvPanelIFR1_{name}"] == 0


@pytest.mark.parametrize("pressed", ["FMS1", "FMS2", "AP", "XPDR"])
@pytest.mark.parametrize("released", ["FMS1", "FMS2", "AP", "XPDR"])
@pytest.mark.parametrize("event", ["release", "long"])
def test_a_modifier_let_go_after_a_change_of_mode_sends_nothing(pressed, released, event):
    # MobiFlight delivers the release to the mode the user changed to, after Button_UNSHIFT_SW
    state = {"TRANSPONDER CODE:1": 0x7000}
    press(state, DA40[f"Button_{pressed}_TOG"])
    press(state, DA40["Button_UNSHIFT_SW"])
    assert press(state, DA40[f"Button_{released}_TOG"], event) == []


@pytest.mark.parametrize("button", ["AP_APR", "AP_ALT", "AP_CRSR", "COM1_TOG", "COM2_TOG", "FMS1_CLR", "FMS2_PROC"])
def test_a_key_with_a_hold_let_go_or_held_after_a_change_of_mode_sends_nothing(button):
    entry = DA40[f"Button_{button}"]
    for event in ("release", "long", "hold"):
        if event not in entry or (event == "release" and button == "AP_CRSR"):   # VNV: held only
            continue
        state = {"COM RECEIVE EX1:1": 0, "COM RECEIVE EX1:2": 0, "COM TRANSMIT:1": 0, "COM TRANSMIT:2": 0}
        press(state, entry)
        press(state, DA40["Button_UNSHIFT_SW"])
        assert press(state, entry, event) == [], event
        press(state, entry)                                              # pressed and let go in one mode: it sends
        assert press(state, entry, event) != [], event


@FAMILY
def test_a_key_held_sends_its_hold_at_once_and_nothing_when_let_go(key):
    # every key with a hold but ⇆ of COM1 and COM2: onHold, then nothing on the release that follows
    p = PROFILES[key]
    for button, entry in p.DEVICE.items():
        if not isinstance(entry, dict) or "hold" not in entry or "long" in entry or "_Again" in entry["hold"]:
            continue
        state, down = {}, f"L:{ifr1._down(button.removeprefix('Button_'))}"
        press(state, entry)
        press(state, entry, "hold", default=1)
        assert state[down] == 0 and press(state, entry, "release", default=1) == [], button


@pytest.mark.parametrize("com", (1, 2))
def test_com_tap_and_two_holds_send_only_one_action(com):
    device = PROFILES["black-square-bonanza"].DEVICE
    entry = device[f"Button_COM{com}_TOG"]
    state = {f"COM RECEIVE EX1:{com}": 1, f"COM TRANSMIT:{com}": 0}
    assert press(state, entry) == []
    assert press(state, entry, "release") == [(f"K:COM{com}_RADIO_SWAP", None)]
    assert press(state, entry) == []
    assert press(state, entry, "long") == [(f"K:COM{com}_RECEIVE_SELECT", 0)]
    assert press(state, entry) == []
    assert press(state, entry, "hold") == [
        ("K:PILOT_TRANSMITTER_SET", com - 1),
        ("K:COPILOT_TRANSMITTER_SET", com - 1),
        (f"K:COM{com}_RECEIVE_SELECT", 1),
        ("L:var_PilotTransmitSelector", com - 1),
    ]
    assert press(state, entry, "long") == []
    press(state, entry)
    press(state, device["Button_UNSHIFT_SW"])
    assert press(state, entry, "hold") == []
    assert press(state, entry, "long") == []


@pytest.mark.parametrize("com", (1, 2))
def test_the_longer_com_hold_sends_nothing_once_shifted(com):
    # the knob push into HDG or BARO with ⇆ still down: MobiFlight sends Button_SHIFT_SW, and its hold to the COM
    # button all the same; the release reaches the shifted ⇆
    device = PROFILES["cows-da40"].DEVICE
    state = {}
    press(state, device[f"Button_COM{com}_TOG"])
    press(state, device["Button_SHIFT_SW"])
    assert press(state, device[f"Button_COM{com}_TOG"], "hold") == []


@FAMILY
def test_entering_shift_lets_go_of_the_toggle_of_the_modes_with_a_shift_only(key):
    p = PROFILES[key]
    shift, unshift = p.DEVICE["Button_SHIFT_SW"], p.DEVICE["Button_UNSHIFT_SW"]
    flags = re.findall(r"\(>L:(\w+)\)", shift)
    assert set(flags) < set(re.findall(r"\(>L:(\w+)\)", unshift))   # each also let go of on a change of mode
    assert "AvPanelIFR1_COM1_TOG" in flags and "AvPanelIFR1_COM2_TOG" in flags
    for flag in flags:
        assert flag.removeprefix("AvPanelIFR1_").split("_")[0] in ifr1.SHIFTED, flag


def test_bonanza_baro_steps_and_restores_both_altimeters():
    device = PROFILES["black-square-bonanza"].DEVICE
    state = {"KOHLSMAN SETTING MB:1": 1000, "L:AvionicsPanel_Baro": 0}
    for ring, expected in (("OI", 16005), ("II", 16005), ("OD", 15995), ("ID", 15995)):
        assert press(state, device[f"Button_COM2^_{ring}"]) == [
            ("K:KOHLSMAN_SET", expected), ("K:KOHLSMAN_SET", (expected, 2)), ("L:AvionicsPanel_Baro", 0),
        ]
    std = device["Button_COM2^_TOG"]               # STD keeps the setting where the panel's STD does
    press(state, std)
    assert press(state, std, "release") == [
        ("L:AvionicsPanel_Baro", 1000), ("K:BAROMETRIC_STD_PRESSURE", 1), ("K:BAROMETRIC_STD_PRESSURE", 2),
    ]
    state["KOHLSMAN SETTING MB:1"] = 1013.21       # 29.92 inHg
    press(state, std)
    assert press(state, std, "release") == [
        ("K:KOHLSMAN_SET", 16000), ("K:KOHLSMAN_SET", (16000, 2)), ("L:AvionicsPanel_Baro", 0),
    ]
    press(state, std)                              # on STD with nothing kept: both to STD, as one may not be
    assert press(state, std, "release") == [("K:BAROMETRIC_STD_PRESSURE", 1), ("K:BAROMETRIC_STD_PRESSURE", 2)]


def test_the_fms_ring_with_the_modifier_held_sets_the_units_map_range():
    state = {}
    press(state, DA40["Button_FMS1_TOG"])
    assert press(state, DA40["Button_FMS1_II"]) == [("H:AS1000_PFD_RANGE_INC", None)]
    assert press(state, DA40["Button_FMS1_TOG"], "release") == []
    assert press(state, DA40["Button_FMS1_II"]) == [("H:AS1000_PFD_FMS_Upper_INC", None)]


@pytest.mark.parametrize(("state", "alt", "standby"), [
    (0, [("A:TRANSPONDER STATE:1", 4)], []), (1, [("A:TRANSPONDER STATE:1", 4)], []),       # off, standby
    (3, [], [("A:TRANSPONDER STATE:1", 1)]), (4, [], [("A:TRANSPONDER STATE:1", 1)])])     # on, ALT
def test_the_mode_rings_switch_the_transponder_one_way_each(state, alt, standby):
    # clockwise ALT, counter-clockwise standby, either ring, however far it turns
    for up, down in (("OI", "OD"), ("II", "ID")):
        assert press({"TRANSPONDER STATE:1": state}, DA40[f"Button_XPDR^_{up}"]) == alt
        assert press({"TRANSPONDER STATE:1": state}, DA40[f"Button_XPDR^_{down}"]) == standby
    bonanza = BONANZA.DEVICE
    assert press({"TRANSPONDER STATE:1": 1}, bonanza["Button_XPDR^_OI"]) == [("H:TRANSPONDER_Push_ALT", None)]
    assert press({"TRANSPONDER STATE:1": 4}, bonanza["Button_XPDR^_OD"]) == [("H:TRANSPONDER_Push_STBY", None)]


def test_the_xpdr_rings_with_the_modifier_held_dim_and_a_tap_idents():
    state = {"TRANSPONDER CODE:1": 0x7000, "B:LIGHTING_PANEL_1": 50}
    press(state, DA40["Button_XPDR_TOG"])
    assert press(state, DA40["Button_XPDR_OI"]) == [("B:LIGHTING_PANEL_1_Set", 55)]
    assert press(state, DA40["Button_XPDR_TOG"], "release") == []           # no IDENT after a detent
    press(state, DA40["Button_XPDR_TOG"])
    assert press(state, DA40["Button_XPDR_TOG"], "release") == [("K:XPNDR_IDENT_ON", None)]


@FAMILY
def test_mode_toggles_the_vfr_code_and_held_the_cabin_light(key):
    used = PROFILES[key].USES["Button_XPDR^_TOG"]
    assert used["key"].entry == FAMILIES[key].DEVICE[1]["VFR"]
    assert used["hold"].entry == FAMILIES[key].DEVICE[1]["CABIN_LT"]
    assert PROFILES[key].USES["Button_XPDR_TOG"]["tap"].entry == FAMILIES[key].DEVICE[1]["IDENT"]


def test_a_vfr_code_replaces_the_one_mode_toggles():
    p = ifr1.build("g1000", "1200")
    code = p.DEVICE["Button_XPDR^_TOG"]["release"]
    assert "0x1200" in code and "0x7000" not in code
    with pytest.raises(ValueError):
        ifr1.build("g1000", "1280")


@FAMILY
def test_a_held_key_sends_its_amber_function_and_ap_and_nav_send_on_press(key):
    family, p = FAMILIES[key], PROFILES[key]
    held = {"Button_AP_APR": (1, "BC"), "Button_AP_ALT": (1, "ARM"), "Button_COM1_TOG": (1, "COM1"),
            "Button_COM2_TOG": (1, "COM2")}
    for mode, unit in zip(("FMS1", "FMS2"), p.UNITS, strict=True):
        held.update({f"Button_{mode}_CLR": (unit, "MAP"), f"Button_{mode}_MENU": (unit, "NRST"),
                     f"Button_{mode}_PROC": (unit, "TERR")})
    for button, (device, amber) in held.items():
        if (button, "hold") in EXTRA[key]:                    # a hold of the profile's own (test_the_bonanza_...)
            continue
        entry, plain = p.DEVICE.get(button), p.USES[button]["key"].entry
        if amber in family.DEVICE[device] and family.DEVICE[device][amber] != plain:
            # the tap on the release only, once the key went down in this mode (a press of its own)
            down = f"AvPanelIFR1_{button.removeprefix('Button_')}"
            hold = entry["long"] if "long" in entry else entry["hold"]     # ⇆ of COM1 and COM2 when let go
            assert entry["press"] == f"1 (>L:{down})", button
            assert ifr1.tapped(family.DEVICE[device][amber]) in hold, button
            if plain is not None:
                assert ifr1.tapped(plain) in entry["release"], button
            for code in (entry["release"], hold):
                assert code.startswith(f"(L:{down}, Bool) if{{") and code.endswith(f"0 (>L:{down})"), button
        else:
            assert entry == plain, button
    for button in ("Button_AP_AP", "Button_AP_NAV", "Button_AP_HDG"):         # but where it has a hold (VS, GPSS)
        if "hold" not in p.USES[button]:
            assert p.DEVICE[button] == family.DEVICE[1][button.rsplit("_", 1)[1]]
    assert "hold" not in p.USES["Button_AP_AP"]                           # disengaging cannot wait for the release


@pytest.mark.parametrize(("key", "fms1", "fms2"), [
    ("g1000", "AS1000_PFD_", "AS1000_MFD_"), ("cows-da40", "AS1000_PFD_", "AS1000_MFD_"),
    ("carenado-c182t", "AS1000_PFD_", "AS1000_MFD_"), ("gns", "AS530_", "AS430_"),
    ("g3x", "AS3X_Touch_1_", "AS3X_Touch_2_"),
    ("black-square-bonanza", "AS530_", "AS430_")])
def test_fms1_and_fms2_are_the_units_a_display_is_numbered_by(key, fms1, fms2):
    p = PROFILES[key]
    assert fms1 in p.DEVICE["Button_FMS1_OI"] and fms2 not in p.DEVICE["Button_FMS1_OI"]
    assert fms2 in p.DEVICE["Button_FMS2_OI"] and fms1 not in p.DEVICE["Button_FMS2_OI"]


def test_the_outer_ring_with_the_modifier_held_is_the_gtns_volume():
    # the GTN's volume knob, as its inner knob, the inner ring's range, would repeat the inner ring: in the GTN
    # profile the panel's tilt up and down (TDS's volume knob), in the Bonanza each navigator's own, the KLN 90B's
    # left outer knob in FMS1
    gtn = PROFILES["gtn"].USES
    for mode, unit in (("FMS1", 1), ("FMS2", 2)):
        prefix = "" if unit == 1 else "S_"
        assert gtn[f"Button_{mode}_OI"]["held"].source == ifr1.Panel(1, f"{prefix}PAN_UP")
        assert gtn[f"Button_{mode}_OD"]["held"].source == ifr1.Panel(1, f"{prefix}PAN_DN")
        assert gtn[f"Button_{mode}_II"]["held"].source == ifr1.Panel(1, f"{prefix}RANGE_CW")
    used, device = BONANZA.USES, BONANZA.DEVICE
    source = used["Button_FMS1_OI"]["held"].source
    assert source.panel == ifr1.Panel(1, "PAN_RIGHT")
    assert source.own.code == "(>H:AS530_RNG_Dezoom) 4 (>K:GPS_BUTTON2) (>H:GTN750_VolInc)"
    state = {}
    press(state, device["Button_FMS2_TOG"])
    assert press(state, device["Button_FMS2_OD"]) == [
        ("H:AS430_RNG_Zoom", None), ("K:GPS_BUTTON2", 10), ("K:GPS_BUTTON2", 26), ("H:GTN650_2_VolDec", None),
        ("H:GTN650_VolDec", None)]
    assert used["Button_FMS1_II"]["held"].source == ifr1.Panel(1, "RANGE_CW")
    assert used["Button_FMS2_II"]["held"].source == ifr1.Panel(1, "S_RANGE_CW")


def test_the_kap_140s_vs_key_leaves_alt_hold():
    for key in ("gns", "gtn", "carenado-c182t"):
        assert PROFILES[key].DEVICE["Button_AP_VS"] == parts.KAP140_VS
    assert ifr1.tapped(FAMILIES["cows-da40"].DEVICE[1]["VS"]) in PROFILES["cows-da40"].DEVICE["Button_AP_VS"]["release"]


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
        name, button = item["Device"]["Name"], item["button"]
        entry = PROFILES[key].DEVICE[name]
        assert item["Device"]["Type"] == "Button" and button["LongReleaseDelay"] == ifr1.HOLD_MS
        assert bool(button["onHold"]) == (isinstance(entry, dict) and "hold" in entry), name
        # the longer hold of ⇆ in COM1 and COM2 after TALK_MS, every other after HOLD_MS
        assert button["HoldDelay"] == (ifr1.TALK_MS if name in ("Button_COM1_TOG", "Button_COM2_TOG") else
                                       ifr1.HOLD_MS), name
        assert not any(n.startswith(ifr1.STATE) for n in item["Name"].split(": ", 1)[1].split(", ")), name
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
    assert "96 buttons mapped" in err and "unmapped XPDR" not in err
    # a profile that leaves buttons unmapped lists them by reason, every one once (the G3X: its FMS keys and HOME)
    cli.main(["--ifr1", "g3x", "-o", str(out)])
    err = capsys.readouterr().err
    p = PROFILES["g3x"]
    assert f"{len(p.DEVICE)} buttons mapped" in err
    listed = re.findall(r"^  unmapped (.+?): (.+)$", err, re.M)
    assert {b for names, _ in listed for b in names.split(", ")} == {b.removeprefix("Button_") for b in p.UNMAPPED}
    assert {r for _, r in listed} == set(p.UNMAPPED.values())


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
        assert set(cards.files(key)[2:]) <= names


# ---------------- the card and the cheat sheet ----------------
@FAMILY
@pytest.mark.parametrize("words", [False, True])
def test_a_page_lists_every_reason_and_names_the_profile(key, words):
    page = ifr1_card.page(PROFILES[key], "v", words)
    assert f"IFR-1: {FAMILIES[key].NAME}" in page and ifr1.filename(key) in page
    p = PROFILES[key]
    shown = set(p.UNMAPPED.values())
    # and the reasons of uses that send nothing on a mapped button: a tap or ⇆'s tap the profile leaves unmapped
    shown |= {u.reason for b, used in p.USES.items() if b in p.DEVICE and not b.endswith("SHIFT_SW")
              for use, u in used.items() if u.reason and use in ("key", "tap", "turn")}
    for reason in shown:
        assert html.escape(reason) in page, reason
    assert ("<footer>" in page) == bool(shown)


@FAMILY
def test_every_mapped_use_has_words(key):
    # what the cheat sheet says comes from the panel's words; a use that sends something has some (Grid.say)
    words = ifr1_grid.words_of(key)
    for used in PROFILES[key].USES.values():
        for u in used.values():
            source = u.source.panel if isinstance(u.source, ifr1.Plus) else u.source
            if isinstance(source, ifr1.Panel) and u.entry is not None:
                assert words[source.device, source.button], source


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


def said(key):
    """{callout: [row]} of a profile's cheat sheet, as plain text (ifr1_sheet.plain())"""
    return ifr1_sheet.plain(PROFILES[key])


def test_the_cells_say_what_the_controls_do():
    da40 = said("cows-da40")
    assert ("⇆: tap: COM 1 flip-flop; hold: listen, on or off; kept if talked on; hold 2 s: "
            "talk on, hear COM 1") in da40["COM1"]
    assert {"outer: selected altitude 1000 ft", "push: hold: VNAV", "⇆: only held while turning a ring"} <= set(
        da40["AP"])
    assert "other modes: tap: VS mode; hold: FLC mode" in da40["B_VS"]
    assert da40["AP"][2].startswith("inner: selected altitude 100 ft; ⇆ held: nose up")
    assert {"outer: COM 2 MHz", "inner: COM 2 kHz",
            "⇆: tap: COM 2 flip-flop; hold: listen, on or off; kept if talked on; hold 2 s: "
            "talk on, hear COM 2"} <= set(da40["COM2"])
    assert da40["NAV1"][da40["NAV1"].index("CRS1 (NAV1 shifted)") + 1] == \
        "outer: course of the CDI (PFD CRS knob) 10°"
    assert "outer: NAV 2 course 10°" in da40["NAV2"]
    assert "⇆: tap: NAV 2 flip-flop; hold: listen to the NAV 2 ident" in da40["NAV2"]
    assert {"outer: heading bug 10°", "inner: heading bug 1°"} <= set(da40["COM1"])
    assert {"MODE (XPDR shifted)", "rings: transponder ALT / transponder standby"} <= set(da40["XPDR"])
    assert "outer: first two squawk digits; ⇆ held: panel lights, 5 % steps" in da40["XPDR"]
    assert "its hold at once when held 0.7 s" in ifr1_card.page(PROFILES["cows-da40"], words=True)
    card = ifr1_card.page(PROFILES["cows-da40"])
    assert ("<td><i>tap:</i> COM1_RADIO_SWAP; <i>hold:</i> COM1_RECEIVE_SELECT; "
            "<i>hold 2 s:</i> PILOT_TRANSMITTER_SET, COPILOT_TRANSMITTER_SET, COM1_RECEIVE_SELECT</td>") in card
    assert "<td><i>tap:</i> AP_APR_HOLD; <i>hold:</i> AP_BC_HOLD</td>" in card
    assert "FMS1: PFD" in ifr1_card.page(PROFILES["g3x"]) and "FMS2: MFD" in ifr1_card.page(PROFILES["g3x"])
    bonanza = said("black-square-bonanza")
    assert "FMS2 CDI: tap: GNS 430 CDI: GPS or VLOC; hold: fuel boost pump: off → low → high → off" in bonanza["B_AP"]
    assert not any("course of the CDI" in row for rows in bonanza.values() for row in rows)
    assert "⇆: only held while turning a ring" in bonanza["AP"]
    assert "Knob" in bonanza["KNOB"][0] and "XPDR to MODE" in bonanza["KNOB"][1] and bonanza["DCT"][0] == "D→"
    c182t = said("carenado-c182t")
    assert any("only held while turning a ring" in row for rows in c182t.values() for row in rows)


def test_the_words_are_escaped(monkeypatch):
    words = ifr1_grid.words_of("cows-da40")
    monkeypatch.setattr(ifr1_grid, "words_of", lambda key: {**words, (1, "NAV_SWAP"): "<b>a & b</b>"})
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


# ---------------- the Black Square Bonanza's own uses ----------------
BONANZA = PROFILES["black-square-bonanza"]


@pytest.mark.parametrize(("mode", "key", "use", "gtn"), [
    ("FMS1", "MENU", "key", "4 (>K:GPS_BUTTON2)"),
    ("FMS1", "CLR", "key", "2 (>K:GPS_BUTTON2)"),
    ("FMS1", "ENT", "key", "2 (>K:GPS_BUTTON1) 4 (>K:GPS_BUTTON1)"),
    ("FMS2", "MENU", "hold", "12 (>K:GPS_BUTTON2) 28 (>K:GPS_BUTTON2)"),
    ("FMS2", "CLR", "key", "10 (>K:GPS_BUTTON2) 26 (>K:GPS_BUTTON2)"),
    ("FMS2", "ENT", "key", "10 (>K:GPS_BUTTON1) 12 (>K:GPS_BUTTON1) 26 (>K:GPS_BUTTON1) 28 (>K:GPS_BUTTON1)")])
def test_the_bonanzas_menu_clr_and_ent_also_set_tds_volume_and_squelch(mode, key, use, gtn):
    # the GNS's, KLN 90B's and PMS50's key (PMS50's MENU, BACK and ENTER), then TDS's volume or its push, which TDS
    # takes on no other key (its unit's values: the 750 as unit 1, the 650 as unit 1 or 2). FMS2's MENU sends them
    # held, as its tap is the EDM 800's STEP.
    unit = 1 if mode == "FMS1" else 2
    panel = FAMILIES["black-square-bonanza"].DEVICE[unit][key]
    assert BONANZA.USES[f"Button_{mode}_{key}"][use].entry == f"{panel} {gtn}"
    assert re.search(r"GTN[67]50_(MENU|BACK|ENTER)", panel) and "GPS_BUTTON" not in panel


def test_the_bonanzas_ent_says_its_squelch_is_tds_only():
    sheet = said("black-square-bonanza")
    assert sheet["ENT"][1:] == ["FMS1: ENT; TDS GTN 750 volume push: squelch, or ident with NAV",
                                "FMS2: tap: ENT; TDS GTN 650 volume push: squelch, or ident with NAV; hold: KFC 150 "
                                "self-test, autopilot off only"]


def test_the_bonanzas_cockpit_functions_take_the_slots_that_send_nothing_in_every_selection():
    used, family = BONANZA.USES, FAMILIES["black-square-bonanza"]
    assert used["Button_AP_NAV"]["hold"].entry == family.DEVICE[1]["GPSS"] and "hold" not in used["Button_FMS1_CDI"]
    assert used["Button_COM1^_TOG"]["key"].entry == (f"{family.DEVICE[1]['HDG_SYNC']} (A:HEADING INDICATOR:1, "
                                                    "degrees) near dnor (>K:VOR1_SET)")
    assert used["Button_FMS2_VNAV"]["key"].entry == family.DEVICE[1]["LVL"]
    assert used["Button_FMS2_ENT"]["hold"].entry == ("(A:AUTOPILOT MASTER, Bool) ! if{ "
                                                     "20 (>L:var_AutopilotStartupCounter) }")
    assert used["Button_FMS2_MENU"]["key"].entry == family.DEVICE[1]["S_UP"]["release"]
    assert used["Button_FMS2_PROC"]["key"].entry == family.DEVICE[1]["S_DN"]["release"]
    assert used["Button_FMS2_PROC"]["hold"].entry == family.DEVICE[2]["PROC"]
    # nothing in the panel's profile for unit 2's VNAV, NRST and TERR; and no hold of ⇆ in FMS1 or FMS2 in any
    # profile, as a detent that comes with its press would leave it to send that hold
    assert {"VNAV", "NRST", "TERR"} <= set(family.UNMAPPED[2])
    assert all(PROFILES[k].USES[f"Button_{m}_TOG"]["hold"].source is None for k in FAMILIES for m in ("FMS1", "FMS2"))
    assert not BONANZA.UNMAPPED
    assert used["Button_FMS2_MSG"]["hold"].entry == "(L:var_oxygenOn, Number) 0 > ! 100 * (>L:var_oxygenOn)"


def test_the_bonanzas_edm_800_takes_a_tap_of_menu_and_proc_in_fms2():
    # STEP and LEAN FIND on a tap, pressed often; the GNS 430's MENU (with the GTN 650's volume up) and PROC held
    device, state = BONANZA.DEVICE, {}
    for key, tap, hold in (("MENU", [("H:bksq_JpiButton_1_L_Short", None)],
                            [("H:AS430_MENU_Push", None), ("H:GTN650_2_MENU", None), ("H:GTN650_MENU", None),
                             ("K:GPS_BUTTON2", 12), ("K:GPS_BUTTON2", 28)]),
                           ("PROC", [("H:bksq_JpiButton_1_R_Short", None)],
                            [("H:AS430_PROC_Push", None), ("H:GTN650_2_GoToPage-HOME-PageProcs", None),
                             ("H:GTN650_GoToPage-HOME-PageProcs", None)])):
        press(state, device[f"Button_FMS2_{key}"])
        assert press(state, device[f"Button_FMS2_{key}"], "release") == tap, key
        press(state, device[f"Button_FMS2_{key}"])
        assert press(state, device[f"Button_FMS2_{key}"], "hold") == hold, key
    # FMS1's MENU and PROC keep the KLN 90B's and GNS 530's keys on a tap
    assert "KLN90B_ALT_Push" in device["Button_FMS1_MENU"]["release"]


def test_the_bonanzas_holds_in_fms1_and_fms2_run_as_the_cockpit():
    device = BONANZA.DEVICE
    state = {"L:var_rnavDrivesHsi": 0, "L:var_oxygenOn": 0, "L:var_AirConditionerSwitch": 0}
    press(state, device["Button_AP_NAV"])
    assert press(state, device["Button_AP_NAV"], "hold") == [("L:var_rnavDrivesHsi", 1)]
    assert press(state, device["Button_AP_NAV"], "release") == []       # let go: nothing until pressed again
    press(state, device["Button_FMS2_MSG"])
    assert press(state, device["Button_FMS2_MSG"], "hold") == [("L:var_oxygenOn", 100)]    # the valve, fully open
    state["L:var_oxygenOn"] = 40                                                                # partly open: shut
    press(state, device["Button_FMS2_MSG"])
    assert press(state, device["Button_FMS2_MSG"], "hold") == [("L:var_oxygenOn", 0)]
    press(state, device["Button_FMS2_MSG"])
    assert press(state, device["Button_FMS2_MSG"], "release") == [("H:AS430_MSG_Push", None), ("H:GTN650_2_MSG", None),
                                                                  ("H:GTN650_MSG", None)]
    for on in (1, 0):                                  # the air conditioner, with its blower on high or off
        press(state, device["Button_FMS2_VNAV"])
        assert press(state, device["Button_FMS2_VNAV"], "hold") == [("L:var_AirConditionerSwitch", on),
                                                                    ("L:var_airConditioningBlowerSwitch", 2 * on)]
    state["L:var_dmeMode"] = 0
    press(state, device["Button_FMS2_VNAV"])
    assert press(state, device["Button_FMS2_VNAV"], "release") == [("L:var_dmeMode", 1)]   # a tap: the DME


def test_the_bonanzas_sheet_says_what_the_merged_keys_do():
    sheet = said("black-square-bonanza")
    assert sheet["MENU"][1:] == ["FMS1: tap: MENU (KLN 90B: ALT); TDS GTN 750 volume up; hold: MD41 APR ARM (unit 1)",
                                 "FMS2: tap: EDM 800 STEP; hold: MENU; TDS GTN 650 volume up"]
    assert ("outer: navigator's outer right knob; ⇆ held: KLN 90B left outer knob; GNS 530 map range; GTN 750 volume"
            in sheet["FMS1"])
    assert "⇆: tap: GTN HOME" in sheet["FMS1"] and "⇆: tap: GTN HOME" in sheet["FMS2"]
    assert "FMS1 CDI: GPS or VLOC (GNS, HSI, MD41)" in sheet["B_AP"]
    assert "other modes: tap: NAV mode; hold: HSI source: NAV 1 or RNAV" in sheet["B_NAV"]
    assert "other modes: tap: KAS 297B VS ENG; hold: flight director (only with AP off)" in sheet["B_VS"]
    assert "⇆: heading bug to the heading; HSI course to the heading" in sheet["COM1"]
    assert "FMS2 VNAV: tap: KDI 572R DME selector, next; hold: air conditioner and blower on or off" in sheet["B_ALT"]
    assert "FMS2 MSG: tap: MSG; hold: oxygen on or off" in sheet["B_NAV"]
    assert "FMS2 PROC: tap: EDM 800 LEAN FIND; hold: PROC (GNS; PMS50 GTN: procedures)" in sheet["B_VS"]
    assert "FMS2 FPL: tap: FPL (GNS); hold: tip tank pumps: both off if either runs, else both on" in sheet["B_APR"]


# ---------------- the cheat sheet's drawing ----------------
def overlap(a, b, gap=0):
    (ax, ay, aw, ah), (bx, by, bw, bh) = a, b
    return ax < bx + bw + gap and bx < ax + aw + gap and ay < by + bh + gap and by < ay + ah + gap


def cross(p, q, r, s):
    """whether the segments pq and rs cross (touching ends do not count)"""
    def turn(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = turn(r, s, p), turn(r, s, q), turn(p, q, r), turn(p, q, s)
    return d1 * d2 < 0 and d3 * d4 < 0


@FAMILY
def test_the_drawing_has_a_box_and_a_line_for_every_control_apart_from_each_other(key):
    sheet = ifr1_sheet.Sheet(PROFILES[key])
    drawing = sheet.svg()
    height = float(re.search(r'viewBox="0 0 \d+ ([\d.]+)"', drawing)[1])
    assert set(sheet.boxes) == set(sheet.leads) == set(ifr1_sheet.ROUTES)
    device = (sheet.x0, sheet.y0, ifr1_sheet.BODY[0] * ifr1_sheet.S, ifr1_sheet.BODY[1] * ifr1_sheet.S)
    for name, box in sheet.boxes.items():
        x, y, w, h = box
        assert x >= 0 and x + w <= ifr1_sheet.W and y >= 0 and y + h <= height, name
        assert not overlap(box, device, 8), name
        for other, second in sheet.boxes.items():
            assert name == other or not overlap(box, second), (name, other)
    for (a, pa), (b, pb) in itertools.combinations(sheet.leads.items(), 2):
        for p, q in zip(pa, pa[1:], strict=False):
            for r, s in zip(pb, pb[1:], strict=False):
                assert not cross(p, q, r, s), (a, b)
    # no line passes through a box but its own
    for name, points in sheet.leads.items():
        for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
            for t in (i / 100 for i in range(101)):
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                for other, (bx, by, bw, bh) in sheet.boxes.items():
                    assert other == name or not (bx < x < bx + bw and by < y < by + bh), (name, other)
    # each line starts on its box's edge and ends on its control, inside the device
    for name, points in sheet.leads.items():
        x, y, w, h = sheet.boxes[name]
        (sx, sy), (ex, ey) = points[0], points[-1]
        assert x - 0.1 <= sx <= x + w + 0.1 and y - 0.1 <= sy <= y + h + 0.1, name
        assert sx in (x, x + w) or sy in (y, y + h), name
        assert device[0] < ex < device[0] + device[2] and device[1] < ey < device[1] + device[3], name


def test_the_routes_inside_the_device_keep_clear_of_the_keys_knob_and_each_other():
    s = ifr1_sheet
    rects = {**{m: s._edges(*s._mode_key(m)) for row in s.MODE_GRID for m in row},
             **{k: s._edges(s.RIGHT_COL, y) for k, y in zip(s.RIGHT_KEYS, s.ROWS, strict=True)},
             **{f"B_{w}": s._edges(x, s.BOTTOM_ROW, *s.BOTTOM_KEY) for (w, _), x in zip(s.BOTTOM, s.BOTTOM_COLS,
                                                                                        strict=True)},
             "SWAP": s._edges(*s.SWAP)}
    for name, (_, points) in s.ROUTES.items():
        for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
            assert x0 == x1 or y0 == y1, name                          # across and up or down only
            for t in (i / 50 for i in range(1, 50)):                     # a point along the segment
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                assert (x - s.KNOB[0]) ** 2 + (y - s.KNOB[1]) ** 2 > (s.KNOB[2] + 0.5) ** 2 or name == "KNOB", name
                for other, (left, top, right, bottom) in rects.items():
                    inside = left - 0.4 < x < right + 0.4 and top - 0.4 < y < bottom + 0.4
                    assert other == name or not inside, (name, other)          # a line leaves its own key
    for (a, (_, pa)), (b, (_, pb)) in itertools.combinations(s.ROUTES.items(), 2):
        for p, q in zip(pa, pa[1:], strict=False):
            for r, t in zip(pb, pb[1:], strict=False):
                assert not cross(p, q, r, t), (a, b)


def test_the_sheet_page_draws_the_ifr1():
    page = ifr1_card.page(BONANZA, words=True)
    assert page.count("<svg") == 1 and "<table>" not in page and "<footer>" not in page
    assert ">COM1</text>" in page and ">-D→</text>" in page and ">PROC</text>" in page


@FAMILY
def test_holding_nav_crs_and_baro_toggles_their_audio_and_pitot_heat_and_a_tap_does_what_it_did(key):
    # ⇆ held in NAV1, NAV2, CRS1, CRS2 and BARO, where it sent nothing before: a hold sends the simulator's event, a
    # tap what ⇆ sent before, on its release
    device, family = PROFILES[key].DEVICE, FAMILIES[key]
    holds = {"NAV1_TOG": "K:RADIO_VOR1_IDENT_TOGGLE", "NAV2_TOG": "K:RADIO_VOR2_IDENT_TOGGLE",
             "NAV1^_TOG": "K:MARKER_SOUND_TOGGLE", "NAV2^_TOG": "K:RADIO_DME1_IDENT_TOGGLE",
             "COM2^_TOG": "K:PITOT_HEAT_TOGGLE"}
    taps = {"NAV1_TOG": family.DEVICE[1]["NAV_SWAP"], "NAV2_TOG": family.DEVICE[2]["NAV_SWAP"],
            "NAV1^_TOG": family.DEVICE[1]["CRS_CTR"], "NAV2^_TOG": ifr1.NAV2_COURSE["TOG"].code,
            "COM2^_TOG": EXTRA[key]["Button_COM2^_TOG", "key"].code if ("Button_COM2^_TOG", "key") in EXTRA[key]
            else family.DEVICE[1]["BARO_STD"]}
    for button, event in holds.items():
        entry = device[f"Button_{button}"]
        down = f"L:AvPanelIFR1_{button.replace('^', '_Shifted')}"
        assert re.fullmatch(r"L:\w+", down) and entry["press"] == f"1 (>{down})", button
        assert f"(>{event})" in entry["hold"] and ifr1.tapped(taps[button]) in entry["release"], button
        assert f"0 (>{down})" in device["Button_UNSHIFT_SW"], button   # let go on a change of mode or leaving shift


def test_the_bonanzas_fms2_holds_run_its_tip_tanks_prop_heat_and_fuel_pump():
    device = BONANZA.DEVICE

    def hold(key, state):
        press(state, device[f"Button_FMS2_{key}"])
        return press(state, device[f"Button_FMS2_{key}"], "hold")
    # the tip tank pumps: both off where either runs, so a hold after one was switched in the cockpit stops both
    for left, right, then in ((0, 0, 1), (1, 1, 0), (1, 0, 0), (0, 1, 0)):
        state = {"L:TipTankTransferSwitch_L": left, "L:TipTankTransferSwitch_R": right}
        assert hold("FPL", state) == [("L:TipTankTransferSwitch_L", then), ("L:TipTankTransferSwitch_R", then)]
    # the fuel boost pump, one position on from the cockpit's: off, low, high, off
    for now, then in ((0, 1), (1, 2), (2, 0)):
        assert hold("CDI", {"L:var_FUEL_Switch_Pump_1": now}) == [("L:var_FUEL_Switch_Pump_1", then)], now
    assert hold("OBS", {}) == [("B:DEICE_Propeller_1_Toggle", 1)]      # prop heat, by its input event
    state = {}
    press(state, device["Button_FMS2_OBS"])
    assert press(state, device["Button_FMS2_OBS"], "release") == [("H:AS430_OBS_Push", None)]   # a tap: the GNS's


@pytest.mark.parametrize("key", ["cows-da40", "carenado-c182t"])
def test_the_da40_and_c182t_hold_cdi_in_fms2_for_the_electric_fuel_pump(key):
    device, family = PROFILES[key].DEVICE, FAMILIES[key]
    for now in (0, 1):
        state = {"B:FUEL_PUMP_1": now}
        press(state, device["Button_FMS2_CDI"])
        assert press(state, device["Button_FMS2_CDI"], "hold") == [("B:FUEL_PUMP_1_Set", not now)]
    unit, down = PROFILES[key].UNITS[1], "L:AvPanelIFR1_FMS2_CDI"     # FMS2: the MFD, the panel's unit 1
    assert device["Button_FMS2_CDI"]["release"] == f"({down}, Bool) if{{ {family.DEVICE[unit]['CDI']} }} 0 (>{down})"


def test_the_da40_holds_fpl_in_fms2_for_the_ngs_fuel_transfer_pump():
    device = PROFILES["cows-da40"].DEVICE
    for now in (0, 1):
        state = {"L:XFER_SWITCH": now}
        press(state, device["Button_FMS2_FPL"])
        assert press(state, device["Button_FMS2_FPL"], "hold") == [("L:XFER_SWITCH", not now)]
    assert "Button_FMS2_FPL" not in EXTRA["carenado-c182t"]
    assert said("cows-da40")["B_APR"][-1] == "FMS2 FPL: tap: FPL; hold: NG fuel transfer pump on or off"


@FAMILY
def test_the_button_for_a_change_of_mode_lets_go_of_every_held_key_of_the_profile_and_fits(key):
    # Button_UNSHIFT_SW clears every modifier and the down flag of every key with a hold the profile has, and no
    # other key's, so it fits MobiFlight's message whatever a profile adds
    p = PROFILES[key]
    clear = p.DEVICE["Button_UNSHIFT_SW"]
    held = {button for button, entry in p.DEVICE.items() if isinstance(entry, dict) and "hold" in entry}
    want = [*(f"0 (>L:AvPanelIFR1_{m})" for m in ifr1.MODIFIED)]
    for b in ifr1.BUTTONS:
        if b in held:
            down = ifr1._down(b.removeprefix("Button_"))
            want += [f"0 (>L:{down})", *([f"0 (>L:{down}_Again)"] if f"{down}_Again" in p.DEVICE[b]["hold"] else [])]
    assert clear == " ".join(want) and len(clear.encode()) < 1000
    for button in held:
        assert p.DEVICE[button]["press"] == f"1 (>L:{ifr1._down(button.removeprefix('Button_'))})", button


@pytest.mark.parametrize(("key", "button"), [("g1000", "NAV1_TOG"), ("gns", "NAV2^_TOG"), ("cows-da40", "FMS2_CDI"),
                                             ("black-square-bonanza", "FMS2_MENU")])
def test_a_hold_key_let_go_after_a_change_of_mode_sends_nothing(key, button):
    device = PROFILES[key].DEVICE
    for event in ("release", "hold"):
        state = {}
        press(state, device[f"Button_{button}"])
        press(state, device["Button_UNSHIFT_SW"])                  # the mode changed with the key held
        assert press(state, device[f"Button_{button}"], event) == [], (button, event)


def test_the_course_follows_the_heading_round_north():
    code = BONANZA.USES["Button_COM1^_TOG"]["key"].source.own.code
    for heading, course in ((359.6, 0), (0.4, 0), (90.5, 91), (180.2, 180)):
        assert run(code, {"HEADING INDICATOR:1": heading}) == [("K:VOR1_SET", course)], heading


@pytest.mark.parametrize("key", ["gns", "gtn", "carenado-c182t"])
def test_the_kap_140s_vnv_held_sets_its_rate_again_as_it_is_let_go(key):
    # as the panel's (tests/test_mobiflight.py): VS and the rate at once when held, the rate again a frame later,
    # as the key is let go after the hold; a tap sends nothing, and a release before the hold no second rate
    entry = PROFILES[key].DEVICE["Button_AP_CRSR"]
    sim = {"INDICATED ALTITUDE": 8000, "AUTOPILOT ALTITUDE LOCK VAR:1": 4000, "GROUND VELOCITY": 120,
           "GPS WP DISTANCE": 20, "L:TDSGTNXI_NextWaypointDistanceNM": 20, "L:WTAP_VNAV_Required_VS": 0,
           "AUTOPILOT MASTER": 1, "AUTOPILOT ALTITUDE LOCK": 1}
    state = dict(sim)
    press(state, entry)
    held = press(state, entry, "hold")
    assert ("K:AP_PANEL_VS_ON", 0) in held and held[-1] == ("K:AP_VS_VAR_SET_ENGLISH", -400)   # 4000 ft, 10 min
    assert "long" not in entry                                           # any release after the hold: a late one too
    assert press(state, entry, "release") == [("K:AP_VS_VAR_SET_ENGLISH", -400)]
    assert press(state, entry, "release") == []                          # once
    state = dict(sim)
    press(state, entry)
    assert press(state, entry, "release") == []                          # a tap: VNV is held only
    assert PROFILES["cows-da40"].USES["Button_FMS1_VNAV"]["key"].source == ifr1.Panel(1, "VNV")
    assert PROFILES["carenado-c182t"].USES["Button_FMS1_VNAV"]["key"].source != ifr1.Panel(1, "VNV")


def test_a_longer_hold_takes_the_place_of_a_hold_that_sends_nothing():
    # ⇆ of COM1 or COM2 in a profile that leaves the radio's audio unmapped: its talk hold at HOLD_MS, at once
    use = ifr1.Use
    used = {"key": use(None, "1 (>K:A)", None), "hold": use(None, None, "no audio panel"),
            "long_hold": use(None, "1 (>K:B)", None)}
    assert ifr1.holds(used) == ("1 (>K:A)", "1 (>K:B)", None)
    entry = ifr1.entry("Button_COM1_TOG", used)
    assert set(entry) == {"press", "release", "hold"} and "(>K:B)" in entry["hold"]
    both = {**used, "hold": use(None, "1 (>K:C)", None)}
    assert ifr1.holds(both) == ("1 (>K:A)", "1 (>K:C)", "1 (>K:B)")
    assert set(ifr1.entry("Button_COM1_TOG", both)) == {"press", "release", "long", "hold"}


def test_a_ring_with_only_a_held_use_sends_nothing_without_the_modifier():
    code = ifr1.knob("AP", None, "1 (>K:A)")
    assert press({}, code) == [] and press({f"L:{ifr1._var('AP')}": 1}, code) == [("K:A", 1)]
    assert ifr1.knob("AP", None, None) is None


def test_a_modifier_with_a_hold_is_refused():
    used = {"tap": ifr1.Use(None, "1 (>K:A)", None), "hold": ifr1.Use(None, "1 (>K:B)", None)}
    with pytest.raises(ValueError):
        ifr1.entry("Button_AP_TOG", used)


def test_a_modifier_with_nothing_to_do_is_unmapped_with_a_reason(monkeypatch):
    # AP's ⇆ has no tap; were UP and DN unmapped, its rings would take nothing with it held: unmapped, with a reason
    uses = ifr1.uses

    def without_up_and_dn(key):
        out = uses(key)
        for ring in ifr1.KNOB:
            out[f"Button_AP_{ring}"].pop("held", None)
        return out
    monkeypatch.setattr(ifr1, "uses", without_up_and_dn)
    p = ifr1.build("g1000")
    assert "Button_AP_TOG" not in p.DEVICE and p.UNMAPPED["Button_AP_TOG"] == ifr1.NO_USE
    assert "Turned" not in p.DEVICE["Button_AP_II"]                      # its rings mark no turn for it


def test_an_entry_that_tells_a_tap_from_a_hold_cannot_go_out_at_once():
    with pytest.raises(ValueError):
        ifr1.tapped({"press": "1 (>K:A)", "long": "1 (>K:B)"})


def test_the_buttons_that_let_go_are_named_by_what_they_do():
    project = ifr1.project(BONANZA)
    names = {i["Device"]["Name"]: i["Name"] for i in project["ConfigFiles"][0]["ConfigItems"]
             if i["Type"] == "InputConfigItem"}
    assert names["Button_UNSHIFT_SW"] == "UNSHIFT_SW: lets go of ⇆ and the held keys of every mode"
    assert names["Button_SHIFT_SW"] == "SHIFT_SW: lets go of ⇆ in the modes with a shift"
    assert names["Button_AP_APR"] == "AP_APR: AP_APR_HOLD, AP_BC_HOLD"


def test_tds_gtns_take_their_volume_by_their_part():
    # the GTN profile's units, TDS's GTNs; not the Bonanza's tablet selections (bonanza_extra()) or another navigator
    assert [ifr1.tds_gtn(FAMILIES["gtn"], u) for u in (1, 2)] == ["GTN 750", "GTN 650"]
    assert not any(ifr1.tds_gtn(FAMILIES[k], u) for k in FAMILIES if k != "gtn" for u in (1, 2))


def test_the_bonanzas_self_test_runs_with_the_autopilot_off_only():
    code = BONANZA.USES["Button_FMS2_ENT"]["hold"].entry
    assert run(code, {"AUTOPILOT MASTER": 0}) == [("L:var_AutopilotStartupCounter", 20)]
    assert run(code, {"AUTOPILOT MASTER": 1}) == []


def test_a_plus_that_sends_nothing_is_unmapped_with_the_panels_reason():
    family = FAMILIES["g1000"]
    table = {**family.DEVICE, 1: {k: v for k, v in family.DEVICE[1].items() if k != "MENU"}}
    unmapped = {**family.UNMAPPED, 1: {**family.UNMAPPED[1], "MENU": "a reason"}}
    used = ifr1.resolve(table, type("F", (), {"UNMAPPED": unmapped}), ifr1.Plus(ifr1.Panel(1, "MENU"),
                                                                                ifr1.Own("nothing", "")))
    assert used.entry is None and used.reason == "a reason"


def test_the_gtn_profile_puts_tds_volume_and_its_push_on_menu_clr_and_ent():
    device = PROFILES["gtn"].DEVICE
    for mode, value in (("FMS1", 0), ("FMS2", 24)):           # TDS's GTN 750Xi unit 1, GTN 650Xi unit 2
        assert press({}, device[f"Button_{mode}_MENU"]) == [("K:GPS_BUTTON2", value + 4)]
        assert press({}, device[f"Button_{mode}_CLR"]) == [("K:GPS_BUTTON2", value + 2)]
        state = {}
        assert press(state, device[f"Button_{mode}_ENT"]) == [("K:GPS_BUTTON1", value + 2)]
        assert press(state, device[f"Button_{mode}_ENT"], "release") == [("K:GPS_BUTTON1", value + 4)]


@FAMILY
def test_every_flag_a_hold_tests_is_let_go_on_a_change_of_mode(key):
    # independent of how build() finds the keys with a hold: each IFR-1 flag a hold, or a release after one, reads
    # goes to 0 in Button_UNSHIFT_SW
    device = PROFILES[key].DEVICE
    clear = device["Button_UNSHIFT_SW"]
    for button, entry in device.items():
        for event in ("long", "hold"):
            if isinstance(entry, dict) and event in entry:
                for flag in re.findall(r"\(L:(AvPanelIFR1_\w+), Bool\) (?:\(L:\w+, Bool\) ! and )?if\{",
                                       entry[event]):
                    assert f"0 (>L:{flag})" in clear, (button, flag)


def test_pms50_gtns_in_unit_1_and_unit_2_share_no_event():
    # PMS50 names its GTN on COM 1 / NAV 1 GTN750_ or GTN650_, on COM 2 / NAV 2 GTN750_2_ or GTN650_2_: two GTNs of a
    # model drive one each; only the Bonanza, whose guide names its GTN 650 GTN650_, sends that beside it
    from mobiflight.families import gtn
    def events(model, unit):
        return {e for table in gtn.pms50(model, unit).DEVICE.values() for entry in table.values()
                for code in profile.actions(entry).values() for e in re.findall(r"\(>H:([\w-]+)\)", code)}
    for first, second in itertools.product(("750", "650"), repeat=2):
        assert events(first, 1) and not events(first, 1) & events(second, 2), (first, second)


def test_the_gtn_sheet_says_which_key_turns_the_volume_up():
    sheet = said("gtn")
    assert sheet["MENU"][1:3] == ["FMS1: GTN 750 volume up", "FMS2: GTN 650 volume up"]
    assert sheet["CLR"][1:3] == ["FMS1: GTN 750 volume down", "FMS2: GTN 650 volume down"]
