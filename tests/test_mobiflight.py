"""The MobiFlight profile generator (mobiflight/): the family tables against the button map, their codes, the
project against the format MobiFlight 11.2 and newer reads, the joysticks read from a saved project, the documented
workflows through the simulated panel and the profile to the codes, and the docs' lists of what does nothing."""
import json
import os
import re
import uuid
from types import SimpleNamespace

import buttonmap as BM
import pytest

from mobiflight import __main__ as cli
from mobiflight import families, ifr1, profile
from mobiflight.families import (
    ALONE_DISTANCES,
    AUTOPILOTS,
    COCKPITS,
    FAMILIES,
    NAVIGATORS,
    UNIT_NAVIGATORS,
    every_part,
    gtn,
    navigators,
    part,
    parts,
)
from mobiflight.families import black_square_bonanza as bksq
from mobiflight.families.black_square_bonanza import KFC150_VNV
from mobiflight.families.rpn import h, k
from sim import Sim
from tests.rpn import NUMBER, READ, REGISTER, TOKEN, every_path, run, sets, well_formed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = {1: ("Avionics Panel", "JS-9c35f3d0-667e-11f1-8001-444553540000"),
         2: ("Avionics Panel", "JS-9c35f3d0-667e-11f1-8002-444553540000")}
VJOY = {1: ("vJoy Device", "JS-0a1b2c3d-4e5f-11f1-8001-444553540000"),
        2: ("vJoy Device", "JS-0a1b2c3d-4e5f-11f1-8002-444553540000")}
FAMILY = pytest.mark.parametrize("key", sorted(FAMILIES))
PARTS = every_part()                                  # every avionics part, a navigator of one unit in each unit
TABLES = {**FAMILIES, **PARTS}
TABLE = pytest.mark.parametrize("key", sorted(TABLES))    # every profile and every part
BONANZA = "black-square-bonanza"


def joined_from(*keys):
    """The profiles joined from a part of one of these kinds and keys, as "cockpit-g1000" (part.compose keeps them
    in PARTS), sorted"""
    return tuple(sorted(k for k, f in FAMILIES.items() if set(keys) & set(getattr(f, "PARTS", ()))))


G1000 = tuple(sorted(set(joined_from("cockpit-g1000")) & set(joined_from("navigator-g1000"))))   # the G1000 NXi's
GARMIN = joined_from("autopilot-gfc700", "autopilot-gfc500")   # with Garmin's autopilot, the GFC 700 or GFC 500
BENDIX = joined_from("cockpit-bendix-king")                    # with the instruments round a Bendix/King autopilot
assert G1000 and GARMIN and BONANZA in BENDIX and len(BENDIX) > 1, "no profile joined from these parts: a key changed?"


@pytest.fixture(autouse=True)
def unstamped(monkeypatch):
    # the command line's default stamp is the commit of firmware/version.py, which git archive fills in: none, as
    # in a git checkout, so the tests compare the same projects in an archive too
    monkeypatch.setattr(profile, "VERSION", None)


def build(controllers=PANEL, key="g1000"):
    return profile.build(FAMILIES[key], controllers)


def items(project):
    return [item for config_file in project["ConfigFiles"] for item in config_file["ConfigItems"]]


def codes(key):
    """(device, button, event, code) for every code of a profile's or a part's table"""
    return [(device, button, event, code) for device, buttons in TABLES[key].DEVICE.items()
            for button, entry in buttons.items() for event, code in profile.actions(entry).items()]


# ---------------- the tables ----------------
@FAMILY
def test_every_button_is_mapped_or_listed_as_unmapped(key):
    family = FAMILIES[key]
    for device in (1, 2):
        mapped, unmapped = set(family.DEVICE[device]), set(family.UNMAPPED[device])
        assert mapped <= set(BM.DEVICE[device]) and unmapped <= set(BM.DEVICE[device]), device
        assert not mapped & unmapped, device
        assert mapped | unmapped == set(BM.DEVICE[device]), device
        assert all(reason for reason in family.UNMAPPED[device].values())


def uses(code):
    """The numbers and signs a code holds and what it sets, in the code's order: 10,+,K:HEADING_BUG_SET (a space
    in a variable's name as _). What a code reads and decides by is for the tests that run it."""
    out = []
    for token in TOKEN.findall(code):
        if sets(token):
            out.append(sets(token).replace(" ", "_"))
        elif NUMBER.fullmatch(token) or token in ("+", "-"):
            out.append(token)
    return ",".join(out)


@TABLE
def test_codes_are_well_formed(key):
    # every code is one MobiFlight takes (rpn.well_formed()), and down each way its blocks can go it leaves the stack
    # as it found it (rpn.every_path())
    for *_, code in codes(key):
        well_formed(code)
        every_path(code)


def test_every_path_finds_a_branch_that_leaves_the_stack_unbalanced():
    # a value left behind on a way no other test takes fails, as does one taken off an empty stack
    every_path("(A:AUTOPILOT MASTER, Bool) if{ 1 } els{ 0 } (>L:x)")
    for code in ("(A:AUTOPILOT MASTER, Bool) if{ 1 2 } els{ 0 } (>L:x)", "(A:AUTOPILOT MASTER, Bool) if{ + } 1 (>L:x)",
                 "(A:AUTOPILOT MASTER, Bool) if{ 4 } (>A:TRANSPONDER STATE:1, Enum)",      # a variable set from nothing
                 "(A:AUTOPILOT MASTER, Bool) if{ 1 sp0 } l0 (>L:x)"):                      # a register never stored
        with pytest.raises((AssertionError, IndexError, KeyError)):
            every_path(code)


def unit(variable):
    """The unit a variable is read in: degrees for a heading or course, millibars for the altimeter's setting, inHg
    for the one the COWS DA40's standby is set from, feet for an altitude, knots for the ground speed, nmiles for
    the GPS's distance, number for an index, the G1000's CDI source, a dimmer, a selector, a valve, a pump's switch
    or an L: variable's distance, feet per minute for a rate, enum for a state, bool for a flag (an autopilot's
    mode, as AUTOPILOT HEADING LOCK, which the IFR-1's lights read, or the IFR-1's own state, as a key that is
    down, but its squawk digit, its AP rings' window and the keys on the right's shared flags, numbers)"""
    if variable.startswith("AUTOPILOT ") and variable.endswith((" LOCK", " HOLD")):
        return "bool"
    if variable == f"L:{ifr1.SQUAWK_DIGIT}":
        return "number"                                  # the IFR-1's squawk digit selected, 0 to 3
    if variable in (f"L:{ifr1.AP_WINDOW}", f"L:{ifr1.AP_MODE}"):
        return "number"                                  # the sim's time the AP rings' window closes at; a mode
    if variable in {f"L:{ifr1._key_down(b)}" for b in ifr1.BUTTONS if ifr1._shared(b)}:
        return "number"                                  # the button a key on the right went down on (ifr1._key_mark)
    if ifr1.STATE in variable:
        return "bool"
    if re.search(r"HEADING|OBS|RADIAL|NAV LOCALIZER", variable):
        return "degrees"
    if variable.startswith("KOHLSMAN SETTING MB"):
        return "millibars"
    if variable.startswith("KOHLSMAN SETTING HG"):
        return "inhg"                                    # the PFD's, which the DA40's standby takes (aircraft.py)
    if variable in ("INDICATED ALTITUDE", "AUTOPILOT ALTITUDE LOCK VAR"):
        return "feet"
    if variable in ("GROUND VELOCITY", "AIRSPEED INDICATED", "AIRSPEED BARBER POLE", "DESIGN SPEED VS1"):
        return "knots"
    if variable == "E:SIMULATION TIME":
        return "seconds"                                 # the sim's clock, VNV's recalculation (parts.follow)
    if variable == "AUTOPILOT VERTICAL HOLD VAR":
        return "feet per minute"
    if variable.endswith(("AvPanel_VNV_Rate", "AvPanel_VNV_Next")):
        return "number"
    if variable == "GPS WP DISTANCE":
        return "nmiles"
    if variable == "TRANSPONDER CODE":
        return "number"                                  # its digits (parts.CODE)
    if variable.endswith("AvionicsPanel_Squawk"):
        return "number"                                  # the code VFR kept, as its digits (parts.vfr)
    if variable.endswith("Required_VS"):
        return "feet per minute"
    if variable.endswith(("SELECTED", "PFD_CDI_Source", "LightingKnob", "dmeMode", "RadarTilt", "DistanceNM",
                          "RNAV_DME", "AvionicsPanel_Baro", "AvionicsPanel_Standby_Baro", "KOHLSMAN SETTING HG:2",
                          "oxygenOn", "Switch_Pump_1")):
        return "number"
    return "enum" if variable.endswith("STATE") else "bool"


@TABLE
def test_reads_use_the_unit_of_their_kind(key):
    for _, button, _, code in codes(key):
        for token in TOKEN.findall(code):
            if READ.fullmatch(token):
                read = READ.fullmatch(token)
                if read[3]:                              # a B: input event's value, read without a unit
                    continue
                variable = read[1].split(":")[0] if read[1] else read[2] or read[4]
                assert token.rsplit(", ", 1)[1][:-1].lower() == unit(variable), (button, token)


# the H: events of each device by their prefixes, in their exact case (and no TDS GTN by Black Square's L: variables,
# which TDS's own key events replace): unit 1 works the MFD of the G1000 (unit 2 the PFD; on device 1 the PFD's CRS
# and BARO knobs, softkeys and, with SHIFT, RANGE, its inset map), the G3X Touch of index 1, the GNS 530 (SHIFT, RANGE
# the GNS 430's RNG), the GTN 750 and the KLN 90B, unit 2 the second; in the Bonanza, SHIFT with the RANGE knob works
# the second navigator, and the KR 87, the EDM 800 and the GTX 327 are on device 1 (the KR 87's FRQ key on both)
_BONANZA = ("kas297b_", "TRANSPONDER_Push_", "bksq_JpiButton_1_", "bksq_wradar1_", "adf_")
PREFIXES = {
    "g1000": {1: ("AS1000_MFD_", *(f"AS1000_PFD_{p}_" for p in ("CRS", "BARO", "SOFTKEYS", "RANGE", "JOYSTICK")),
                  "AS1000_VNAV_TOGGLE"),
              2: ("AS1000_MFD_SOFTKEYS_", "AS1000_PFD_")},
    "g3x": {1: ("AS3X_Touch_1_", "AS1000_VNAV_TOGGLE"), 2: ("AS3X_Touch_2_",)},
    "gns": {1: ("AS530_", "AS430_RNG_", "KAP140_"), 2: ("AS430_",)},
    "gtn": {1: ("KAP140_",), 2: ()},
    BONANZA: {1: ("AS530_", "GTN750_", "KLN90B_", "AS430_RNG_", "GTN650_Knob", "GTN650_Vol", "GTN650_2_Knob",
                  "GTN650_2_Vol", *_BONANZA),
               2: ("AS430_", "GTN650_", "adf_frqTransfert")},
}
PREFIXES["cows-da40"] = PREFIXES["g1000"]
PREFIXES["carenado-c182t"] = {1: (*PREFIXES["g1000"][1], "KAP140_"), 2: PREFIXES["g1000"][2]}
# the parts' own: an autopilot's and a cockpit's on device 1, a navigator's on its units' devices (and its map on
# device 1), by the model of a navigator of one unit
_OWN = {"autopilot-gfc700": ("AS1000_PFD_SOFTKEYS_", "AS1000_VNAV_TOGGLE"), "autopilot-gfc500": ("AS1000_VNAV_TOGGLE",),
        "autopilot-kap140": ("KAP140_",), "autopilot-kfc150": ("kas297b_",), "cockpit-g1000": ("AS1000_PFD_",),
        "cockpit-g3x": (), "cockpit-bendix-king": ()}
for key, p in PARTS.items():
    if p.KIND != "navigator":
        assert key in _OWN, f"{key}: give its prefixes in _OWN"
        PREFIXES[key] = {1: _OWN[key], 2: ()}
    elif key == "navigator-g3x":
        PREFIXES[key] = {1: ("AS3X_Touch_1_",), 2: ("AS3X_Touch_2_",)}
    elif key == "navigator-g1000":
        PREFIXES[key] = {1: ("AS1000_MFD_", "AS1000_PFD_RANGE_", "AS1000_PFD_JOYSTICK_", "AS1000_PFD_SOFTKEYS_"),
                         2: ("AS1000_MFD_SOFTKEYS_", "AS1000_PFD_")}
    else:
        model = re.match(r"navigator-(gns|gtn)(\d+)-(\w+-)?unit", key)
        assert model, f"{key}: a navigator of a new kind, give its prefixes here"
        own = (f"AS{model[2]}_",) if model[1] == "gns" else (f"GTN{model[2]}_",) if "pms50" in key else ()
        if "pms50" in key and p.UNITS != (1,):           # PMS50's GTN on COM 2 / NAV 2
            own = (f"GTN{model[2]}_2_",)
        # unit 2's map on device 1: the GNS's RNG keys, the PMS50 GTN's inner knob and volume
        on_1 = tuple(f"{o}{e}" for o in own for e in (("RNG_",) if model[1] == "gns" else ("KnobSmall", "Vol")))
        PREFIXES[key] = {1: own, 2: ()} if p.UNITS == (1,) else {1: on_1, 2: own}


@TABLE
def test_h_events_go_to_their_unit(key):
    for device, button, _, code in codes(key):
        for name in re.findall(r"\(>H:([\w-]+)\)", code):
            assert name.startswith(PREFIXES[key][device]), (device, button, name)
        assert "(>L:TDSGTNXI" not in code, (device, button)     # TDS's GTN by its key events (VNV reads one)


def writes(code):
    """[(name, sign)]: the events and variables a code sets, each with the + or - of the step it computes for the
    value, if it does"""
    out, sign, kept, last = [], None, None, None
    for token in TOKEN.findall(code):
        name = sets(token)
        if name:                                     # a value loaded from a register has the sign it was kept with
            out.append((name.split(":", 1)[1], kept if last and REGISTER.fullmatch(last) else sign))
        elif REGISTER.fullmatch(token) and not token.startswith("l"):
            kept = sign
        if name or token in ("if{", "els{", "}", "+", "-"):
            sign = token if token in ("+", "-") else None
        last = token
    return out


def words(name):
    """The words of an event's or variable's name, in lower case: RightLargeKnob_Left -> right, large, knob, left"""
    return re.split(r"[^a-z0-9]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower())


# the words of an event that increases or goes up (a GNS knob turned right, its map zoomed out, a step added), and
# of one that decreases or goes down; of several, as in AS1000_MFD_RANGE_INC, the last one counts. A GTN's inner
# knob zooms in clockwise: RANGE turns it the other way (GTN_ZOOM), so clockwise zooms out on every map.
UP, DOWN = {"inc", "up", "right", "dezoom", "+"}, {"dec", "down", "dn", "left", "zoom", "-"}
GTN_ZOOM = re.compile(r"GPS_PAGE_KNOB_|RKnobInner|GTN[67]50_(?:2_)?KnobSmall")


@TABLE
def test_turns_and_tilts_use_codes_of_their_direction(key):
    # every event a clockwise or UP button sends increases or goes up, by its name or the sign of the step it sets,
    # and the other way round; a tilt left or right sends events that go left or right
    for _, button, _, code in codes(key):
        last = button.rsplit("_", 1)[-1]
        if key == BONANZA and button in ("S_UP", "S_DN"):   # the EDM 800's buttons in the Bonanza: no direction
            continue
        for name, sign in writes(code):
            if re.search(r"Master\w*Lights|LightButton", name):   # a lights switch, on with its dimmer above 0
                continue
            if name.startswith("AvionicsPanel_"):        # the profile's own: a value kept for STD or VFR, forgotten
                continue
            way = [w for w in [*words(name), sign] if w in UP | DOWN]
            if name in TDS_VALUE_WAY:                # TDS's volume knob: its value says the way
                way = [TDS_VALUE_WAY[name][dict(run(code))["K:" + name] % 8]]
            zoom = button.removeprefix("S_") in ("RANGE_CW", "RANGE_CCW") and GTN_ZOOM.search(name)
            reverse = re.search(r"_(SPD|MACH)_VAR_", name) or zoom
            up, down = (DOWN, UP) if reverse else (UP, DOWN)          # nose up slows it; a GTN zooms in clockwise
            if last in ("CCW", "DN"):
                assert way and way[-1] in down, (button, name)
            elif last in ("CW", "UP"):
                assert way and way[-1] in up, (button, name)
            elif last in ("LEFT", "RIGHT") and not (key == BONANZA and "radarRange" in name):  # radar range: down, up
                assert last.lower() in words(name), (button, name)


# the words that name a ring of a dual knob in a code: the G1000 calls its FMS rings lower and upper, and the
# simulator's GPS key events, which TDS's GTN takes, turn the page group with the outer ring and the page with the
# inner one
OUTER, INNER = ("outer", "large", "lower", "group"), ("inner", "small", "upper", "page")
RINGS = {"ALT_1000": OUTER, "ALT_100": INNER, "FMS_OUTER": OUTER, "FMS_INNER": INNER}


@TABLE
def test_rings_use_codes_of_their_ring(key):
    # ALT's outer ring (1000 ft) and inner knob (100 ft), and FMS's, each turn the ring of their name; a code that
    # names no ring is for one knob, as the selected altitude of Garmin's autopilot (GFC 500 and GFC 700), whose
    # selector takes a value above 999 as the 1000 ft step (AltitudeSelectManager.ts), or names its step, as the
    # KAS 297B's events (kas297b_1000_INC)
    for _, button, _, code in codes(key):
        ring = RINGS.get(button.rsplit("_", 1)[0])
        if ring is not None:
            other, said = INNER if ring is OUTER else OUTER, [w for name, _ in writes(code) for w in words(name)]
            if any(w in said for w in OUTER + INNER):
                assert any(w in said for w in ring) and not any(w in said for w in other), (button, code)
            else:
                large = any(t.isdigit() and int(t) > 999 for t in [*TOKEN.findall(code), *said])
                assert large == (ring is OUTER), (button, code)


def radios(code):
    """The numbers of the radios a code acts on: in the names it sets (COM1_RECEIVE_SELECT,
    RADIO_VOR2_IDENT_TOGGLE), the index of a COM or NAV variable it reads, and the COM a transmitter is set to (the
    SDK's PILOT_TRANSMITTER_SET and COPILOT_TRANSMITTER_SET take 0 for COM 1)"""
    tokens = TOKEN.findall(code)
    out = set()
    for i, token in enumerate(tokens):
        out |= set(re.findall(r"(?:COM|NAV|VOR)([1-9])_", token))
        out |= set(re.findall(r"\(A:(?:COM|NAV) [A-Z0-9 ]+:([1-9]),", token))
        if re.fullmatch(r"\(>K:(CO)?PILOT_TRANSMITTER_SET\)", token):
            out.add(str(int(tokens[i - 1]) + 1))
    return out


def test_every_key_event_is_one_the_sdk_lists():
    # tests/key_events.txt holds the key events checked against the SDK's lists; the tables and the IFR-1's profiles
    # send those and only those, so a misspelt event, which the simulator would drop without a word, fails here
    with open(os.path.join(ROOT, "tests", "key_events.txt"), encoding="utf-8") as f:
        checked = {line.strip() for line in f if line.strip() and not line.startswith("#")}
    sent = {name for key in TABLES for *_, code in codes(key) for name in re.findall(r"\(>K:(?:2:)?([^)]*)\)", code)}
    sent |= {name for key in FAMILIES for entry in ifr1.build(key).DEVICE.values()
             for code in profile.actions(entry).values() for name in re.findall(r"\(>K:(?:2:)?([^)]*)\)", code)}
    assert sent - checked == set(), "not checked against the SDK: add them to tests/key_events.txt once found there"
    assert checked - sent == set(), "sent no more: take them out of tests/key_events.txt"


# where every H: event, L: variable and B: input event comes from, by its prefix: the avionics' and aircraft's own
# documentation or sources, as each table's docstring cites them; a name of no such prefix is a typo or an
# unsourced input
_WT_G1000 = "Working Title's G1000 NXi (msfs-avionics-mirror)"
_WT_GNS = "Working Title's GNS (InteractionEvent.ts)"
_PMS50 = "PMS50's GTN (PMS50's GTN750 events, which Black Square's guide follows)"
_BLACK_SQUARE = "Black Square's Bonanza guide, or a project the Bonanza is flown with"
SOURCES = {
    "A:": "the simulator's simulation variables (the SDK's lists)",
    "E:": "the simulator's environment variables (the SDK's list)",
    **dict.fromkeys(("B:LIGHTING_", "B:FUEL_PUMP_", "B:DEICE_"),
                    "the simulator's input events, as projects the aircraft are flown with use them"),
    "H:AS1000_": _WT_G1000,
    "L:PFD_CDI_Source": _WT_G1000,
    "H:AS3X_Touch_": "Working Title's G3X Touch (its H Event List)",
    "H:AS530_": _WT_GNS,
    "H:AS430_": _WT_GNS,
    "H:KAP140_": "the sim's KAP 140 (KAP140.js)",
    "H:GTN750_": _PMS50,
    "H:GTN650_": _PMS50,
    **dict.fromkeys(("L:AvionicsPanel_", "L:AvPanel_VNV"), "the profiles' own"),
    "L:TDSGTNXI_": "TDS's GTNXi manual (Reading specific TDS GTNXi Data)",
    "L:WTAP_": "Working Title's VNAV (sdk/autopilot/vnav/VNavEvents.ts)",
    **dict.fromkeys(("H:KLN90B_", "H:kas297b_", "H:bksq_", "H:adf_", "H:TRANSPONDER_Push_", "L:var_", "L:bksq_",
                     "L:OatMapCompassLightButton_", "L:TipTankTransferSwitch_"), _BLACK_SQUARE),
    "L:XFER_SWITCH": "the project the COWS DA40 is flown with",
    "L:KOHLSMAN SETTING HG:2": "the COWS DA40's standby altimeter (its knob's code in the aircraft)",
}


@TABLE
def test_every_other_input_has_a_source(key):
    # every set or read names an A:, B:, H:, K: or L: input, in that case; an H:, L: or B: name has the prefix of a
    # cited source
    for device, button, _, code in codes(key):
        assert set(re.findall(r"\(>?([A-Za-z]+):", code)) <= set("ABEHKL"), (key, device, button, code)
        for name in re.findall(r"\(>?([HLB]:[^),]+)", code):
            assert name.startswith(tuple(SOURCES)), (f"{name} ({key}, device {device}, {button}): no cited source for "
                                                     "its prefix; add the source to SOURCES and a heading to "
                                                     "tests/inputs.txt")


def test_every_other_input_is_one_its_source_names():
    # tests/inputs.txt holds every H:, L:, B: and A: name, each found in its source once and listed under it; the
    # tables use those and only those, so a misspelt name of a known prefix, or a misspelt simulation variable,
    # which reads 0 or sets nothing without a word, fails here
    checked, heading = {}, None                          # name -> the heading it is listed under
    with open(os.path.join(ROOT, "tests", "inputs.txt"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("# ") and line[2:].strip() in SOURCES.values():
                heading = line[2:].strip()
            elif line.strip() and not line.startswith("#"):
                assert line.strip() not in checked, f"{line.strip()} listed twice"
                checked[line.strip()] = heading
    for name, under in checked.items():                 # each under its source, as SOURCES names it
        assert under == next((v for p, v in SOURCES.items() if name.startswith(p)), None), (name, under)
    checked = set(checked)
    used = {name for key in TABLES for *_, code in codes(key) for name in re.findall(r"\(>?([AEHLB]:[^),]+)", code)}
    # and the IFR-1's (ifr1.py), but for its own state (ifr1.STATE, named by its buttons)
    used |= {name for key in FAMILIES for entry in ifr1.build(key).DEVICE.values()
             for code in profile.actions(entry).values() for name in re.findall(r"\(>?([AEHLB]:[^),]+)", code)
             if not name.startswith(f"L:{ifr1.STATE}")}
    used |= {name for key in FAMILIES for read in ifr1.build(key).LEDS.values()          # what its AP lights read
             for name in re.findall(r"\(>?([AEHLB]:[^),]+)", read) if not name.startswith(f"L:{ifr1.STATE}")}
    assert used - checked == set(), "not checked against its source: add them to tests/inputs.txt once found there"
    assert checked - used == set(), "used no more: take them out of tests/inputs.txt"


@TABLE
def test_numbered_buttons_use_codes_of_their_number(key):
    # MIC 1, COM 1 and NAV 1 audio work radio 1, the ones with 2 radio 2
    for _, button, _, code in codes(key):
        number = re.fullmatch(r"(?:MIC|COM|NAV)([12])(?:_AUDIO)?", button)
        if number is not None:
            assert radios(code) == {number[1]}, (button, code)


# TDS's GTNXi, by its manual ("Interfacing with Hardware"): the value of the GTN 750Xi unit 1 (device 1) and the
# GTN 650Xi unit 2 (device 2) in the key events of the bottom right knob (outer GROUP, inner PAGE), and the events of
# the keys, which take that value + 2 when the key goes down and + 4 when it comes up
TDS_UNIT = {1: 0, 2: 24}
TDS_KNOB = {"FMS_OUTER_CW": "GPS_GROUP_KNOB_INC", "FMS_OUTER_CCW": "GPS_GROUP_KNOB_DEC",
            "FMS_INNER_CW": "GPS_PAGE_KNOB_INC", "FMS_INNER_CCW": "GPS_PAGE_KNOB_DEC"}
TDS_KEY = {"HOME": "GPS_MENU_BUTTON", "DIRECT": "GPS_DIRECTTO_BUTTON", "FMS_CRSR": "GPS_CURSOR_BUTTON"}
# the volume knob (the manual's "Top Left Knob") on the RANGE tilt up and down (unit 2's with SHIFT, also on device
# 1), whose value is the unit's + 2 for down and + 4 for up, and its push on the RANGE push, a key
TDS_VALUE_WAY = {"GPS_BUTTON2": {2: "dec", 4: "inc"}}


def test_the_gtn_bezel_is_the_key_events_tds_documents():
    for device, value in TDS_UNIT.items():
        table = FAMILIES["gtn"].DEVICE[device]
        for button, event in TDS_KNOB.items():
            assert table[button] == k(event, value), (device, button)
        for button, event in TDS_KEY.items():
            assert table[button] == {"press": k(event, value + 2), "release": k(event, value + 4)}, (device, button)
    table = FAMILIES["gtn"].DEVICE[1]
    for shift, value in (("", TDS_UNIT[1]), ("S_", TDS_UNIT[2])):
        assert table[f"{shift}PAN_UP"] == k("GPS_BUTTON2", value + 4)
        assert table[f"{shift}PAN_DN"] == k("GPS_BUTTON2", value + 2)
        assert table[f"{shift}PTR"] == {"press": k("GPS_BUTTON1", value + 2), "release": k("GPS_BUTTON1", value + 4)}


@FAMILY
def test_a_held_key_is_let_go(key):
    # a button that sends on release is a key or push (no knob detent, repeat, tilt or RANGE push, which are short
    # presses) of TDS's GTN, and lets go of what its press holds down: each event of its press again with the value
    # of the key coming up (TDS's own key events: + 2 down, + 4 up), or the MD41's test L: variable set back to 0 on
    # TEST in the Bonanza. The short presses among them are the GTN's volume push on a RANGE push: a tap, whose
    # down and up still reach TDS. A key that tells a tap from a hold (the Bonanza's EDM 800 on SHIFT, UP and
    # SHIFT, DN) sends on its release only.
    for buttons in FAMILIES[key].DEVICE.values():
        for button, entry in buttons.items():
            acts = profile.actions(entry)
            if "onLongRelease" in acts:
                assert key == BONANZA and button in ("S_UP", "S_DN") and "onPress" not in acts, button
            elif button in ("VNV", "S_VNV") and VNV.get(key) == KAP140_VS:
                continue                                   # the KAP 140's VNV sets its rate again let go (below)
            elif "onRelease" in acts:
                short = re.search(r"(?:^|_)(?:CW|CCW|UP|DN|LEFT|RIGHT)$|PTR$", button)
                ptr = button.endswith("PTR")                       # the GTNs' volume push
                assert key in ("gtn", BONANZA) and (not short or ptr), button
                pressed, released = run(acts["onPress"], default=0), run(acts["onRelease"], default=0)
                for name, value in released:
                    if name == "L:var_md41Test":
                        assert (name, 1) in pressed and value == 0, button
                    else:
                        assert name.startswith("K:GPS_") and (name, value - 2) in pressed, (button, name, value)


@FAMILY
def test_units_share_only_the_adf_and_one_cdi(key):
    # unit 2 is the second radio and, beside the G1000, whose units share the MFD, the second navigator: only the
    # one ADF, a CDI and OBS the aircraft has once (docs/using/mapping.md#per-avionics) and the G1000's MFD get the
    # same code from both devices
    device = FAMILIES[key].DEVICE
    for button in set(device[1]) & set(device[2]):
        if device[1][button] == device[2][button]:
            assert button.startswith("ADF_") or button in ("CDI", "OBS") \
                or key in G1000 and not button.startswith(("COM_", "NAV_")), button


@FAMILY
def test_no_two_functions_send_the_same_code(key):
    # a button's codes are its own: only a function's copy with SHIFT (S_ENT and ENT, S_RANGE_CW and RANGE_CW) and
    # its copy in unit 2 (the test above) send what it sends. So no button sends another one's valid event.
    # The GTN profile's RANGE turns the GTN 750Xi's inner knob, which zooms its map on the map page: there it sends
    # what the FMS knob's inner ring sends the other way in unit 1 (it zooms in clockwise).
    functions = {}
    for buttons in FAMILIES[key].DEVICE.values():
        for button, entry in buttons.items():
            functions.setdefault(tuple(sorted(profile.actions(entry).items())), set()).add(button.removeprefix("S_"))
    shared = [{"RANGE_CW", "FMS_INNER_CCW"}, {"RANGE_CCW", "FMS_INNER_CW"}] * 2 if key == "gtn" else []   # both units
    assert sorted(map(sorted, (n for n in functions.values() if len(n) > 1))) == sorted(map(sorted, shared))


# What every function sets, as uses() gives it (a release after a /; @2 marks the function in unit 2, on device 2):
# the functions every family maps alike, then each family's others. A new, dropped, swapped or misspelt event and
# a changed value show here. The K: events are the MSFS 2024 SDK's key events; the H: events of the G1000 NXi,
# the G3X Touch and the GNS are Working Title's, the KAP 140's those of the sim's KAP140.js, and the KFC 150
# profile's H: events and L: variables those Black Square's guide lists, but for the GNS's D→ and RNG (Working
# Title's), TDS's GTN (TDS's own key events) and the lighting (as a project the Bonanza is flown with sets it); the
# DA40's and C182T's lighting the simulator's B: input events, as projects these aircraft are flown with set them;
# L:AvionicsPanel_G1000_Engine is the G1000 profile's own.
EVERY = """
    ADF_100_DN=K:ADF_100_DEC ADF_100_DN@2=K:ADF_100_DEC ADF_100_UP=K:ADF_100_INC ADF_100_UP@2=K:ADF_100_INC
    ADF_10_DN=K:ADF_10_DEC ADF_10_DN@2=K:ADF_10_DEC ADF_10_UP=K:ADF_10_INC ADF_10_UP@2=K:ADF_10_INC ADF_1_DN=K:ADF_1_DEC
    ADF_1_DN@2=K:ADF_1_DEC ADF_1_UP=K:ADF_1_INC ADF_1_UP@2=K:ADF_1_INC ADF_AUDIO=K:RADIO_ADF_IDENT_TOGGLE
    COM1=K:COM1_RECEIVE_SELECT COM2=K:COM2_RECEIVE_SELECT COM_121_5=121500000,K:COM_RADIO_SET_HZ
    COM_121_5@2=121500000,K:COM2_RADIO_SET_HZ COM_KHZ_DN=K:COM_RADIO_FRACT_DEC COM_KHZ_DN@2=K:COM2_RADIO_FRACT_DEC
    COM_KHZ_UP=K:COM_RADIO_FRACT_INC COM_KHZ_UP@2=K:COM2_RADIO_FRACT_INC COM_MHZ_DN=K:COM_RADIO_WHOLE_DEC
    COM_MHZ_DN@2=K:COM2_RADIO_WHOLE_DEC COM_MHZ_UP=K:COM_RADIO_WHOLE_INC COM_MHZ_UP@2=K:COM2_RADIO_WHOLE_INC
    COM_SWAP=K:COM1_RADIO_SWAP COM_SWAP@2=K:COM2_RADIO_SWAP DME_AUDIO=K:RADIO_DME1_IDENT_TOGGLE
    HDG_10_DN=10,-,K:HEADING_BUG_SET HDG_10_UP=10,+,K:HEADING_BUG_SET HDG_1_DN=K:HEADING_BUG_DEC
    HDG_1_UP=K:HEADING_BUG_INC HDG_SYNC=K:HEADING_BUG_SET IDENT=K:XPNDR_IDENT_ON NAV1_AUDIO=K:RADIO_VOR1_IDENT_TOGGLE
    NAV2_AUDIO=K:RADIO_VOR2_IDENT_TOGGLE NAV_KHZ_DN=K:NAV1_RADIO_FRACT_DEC NAV_KHZ_DN@2=K:NAV2_RADIO_FRACT_DEC
    NAV_KHZ_UP=K:NAV1_RADIO_FRACT_INC NAV_KHZ_UP@2=K:NAV2_RADIO_FRACT_INC NAV_MHZ_DN=K:NAV1_RADIO_WHOLE_DEC
    NAV_MHZ_DN@2=K:NAV2_RADIO_WHOLE_DEC NAV_MHZ_UP=K:NAV1_RADIO_WHOLE_INC NAV_MHZ_UP@2=K:NAV2_RADIO_WHOLE_INC
    NAV_SWAP=K:NAV1_RADIO_SWAP NAV_SWAP@2=K:NAV2_RADIO_SWAP SQK_D1_DN=K:XPNDR_1000_DEC,0,L:AvionicsPanel_Squawk_Kept
    SQK_D1_UP=K:XPNDR_1000_INC,0,L:AvionicsPanel_Squawk_Kept
    SQK_D2_DN=K:XPNDR_100_DEC,0,L:AvionicsPanel_Squawk_Kept SQK_D2_UP=K:XPNDR_100_INC,0,L:AvionicsPanel_Squawk_Kept
    SQK_D3_DN=K:XPNDR_10_DEC,0,L:AvionicsPanel_Squawk_Kept SQK_D3_UP=K:XPNDR_10_INC,0,L:AvionicsPanel_Squawk_Kept
    SQK_D4_DN=K:XPNDR_1_DEC,0,L:AvionicsPanel_Squawk_Kept SQK_D4_UP=K:XPNDR_1_INC,0,L:AvionicsPanel_Squawk_Kept
    VFR=7000,1000,4096,100,10,256,+,10,10,16,+,10,+,K:XPNDR_SET,0,L:AvionicsPanel_Squawk_Kept,4,A:TRANSPONDER_STATE:1,L:AvionicsPanel_Squawk,1,L:AvionicsPanel_Squawk_Kept,1000,4096,100,10,256,+,10,10,16,+,10,+,K:XPNDR_SET,4,A:TRANSPONDER_STATE:1
"""
SETS = {
    "g1000": """
        ADF_SWAP=K:ADF1_RADIO_SWAP ADF_SWAP@2=K:ADF1_RADIO_SWAP ALT=K:AP_ALT_HOLD ALT_1000_DN=1000,K:AP_ALT_VAR_DEC
        ALT_1000_UP=1000,K:AP_ALT_VAR_INC ALT_100_DN=K:AP_ALT_VAR_DEC ALT_100_UP=K:AP_ALT_VAR_INC AP=K:AP_MASTER
        APR=K:AP_APR_HOLD ARM=H:AS1000_PFD_SOFTKEYS_10 BARO_DN=H:AS1000_PFD_BARO_DEC
        BARO_STD=H:AS1000_PFD_SOFTKEYS_4,H:AS1000_PFD_SOFTKEYS_10
        BARO_UP=H:AS1000_PFD_BARO_INC BC=K:AP_BC_HOLD CABIN_LT=K:TOGGLE_CABIN_LIGHTS
        CDI=3,1,K:AP_NAV_SELECT_SET,1,2,K:AP_NAV_SELECT_SET,K:TOGGLE_GPS_DRIVES_NAV1
        CDI@2=3,1,K:AP_NAV_SELECT_SET,1,2,K:AP_NAV_SELECT_SET,K:TOGGLE_GPS_DRIVES_NAV1 CLR=H:AS1000_MFD_CLR
        CLR@2=H:AS1000_PFD_CLR CRS_10_DN=3,10,-,K:GPS_OBS_SET,2,10,-,K:VOR2_SET,10,-,K:VOR1_SET
        CRS_10_UP=3,10,+,K:GPS_OBS_SET,2,10,+,K:VOR2_SET,10,+,K:VOR1_SET CRS_1_DN=H:AS1000_PFD_CRS_DEC
        CRS_1_UP=H:AS1000_PFD_CRS_INC CRS_CTR=H:AS1000_PFD_CRS_PUSH DIRECT=H:AS1000_MFD_DIRECTTO
        DIRECT@2=H:AS1000_PFD_DIRECTTO DN=K:AP_VS_VAR_DEC,K:AP_SPD_VAR_INC,K:AP_PITCH_REF_INC_DN
        ENT=H:AS1000_MFD_ENT_Push ENT@2=H:AS1000_PFD_ENT_Push FD=K:TOGGLE_FLIGHT_DIRECTOR FLC=K:FLIGHT_LEVEL_CHANGE
        FMS_CRSR=H:AS1000_MFD_FMS_Upper_PUSH FMS_CRSR@2=H:AS1000_PFD_FMS_Upper_PUSH
        FMS_INNER_CCW=H:AS1000_MFD_FMS_Upper_DEC FMS_INNER_CCW@2=H:AS1000_PFD_FMS_Upper_DEC
        FMS_INNER_CW=H:AS1000_MFD_FMS_Upper_INC FMS_INNER_CW@2=H:AS1000_PFD_FMS_Upper_INC
        FMS_OUTER_CCW=H:AS1000_MFD_FMS_Lower_DEC FMS_OUTER_CCW@2=H:AS1000_PFD_FMS_Lower_DEC
        FMS_OUTER_CW=H:AS1000_MFD_FMS_Lower_INC FMS_OUTER_CW@2=H:AS1000_PFD_FMS_Lower_INC FPL=H:AS1000_MFD_FPL_Push
        FPL@2=H:AS1000_PFD_FPL_Push HDG=K:AP_HDG_HOLD
        HOME=H:AS1000_MFD_SOFTKEYS_11,0,L:AvionicsPanel_G1000_Engine,H:AS1000_MFD_SOFTKEYS_1,1,L:AvionicsPanel_G1000_Engine
        HOME@2=H:AS1000_MFD_SOFTKEYS_11,0,L:AvionicsPanel_G1000_Engine,H:AS1000_MFD_SOFTKEYS_1,1,L:AvionicsPanel_G1000_Engine
        LVL=K:AP_WING_LEVELER_ON,K:AP_PITCH_LEVELER_ON,K:AUTOPILOT_ON MAP=H:AS1000_MFD_SOFTKEYS_11
        MAP@2=H:AS1000_MFD_SOFTKEYS_11 MENU=H:AS1000_MFD_MENU_Push MENU@2=H:AS1000_PFD_MENU_Push
        MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET,1,K:COM1_RECEIVE_SELECT
        MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET,1,K:COM2_RECEIVE_SELECT MSG=H:AS1000_PFD_SOFTKEYS_12
        MSG@2=H:AS1000_PFD_SOFTKEYS_12 NAV=K:AP_NAV1_HOLD NRST=H:AS1000_PFD_SOFTKEYS_11 NRST@2=H:AS1000_PFD_SOFTKEYS_11
        OBS=K:GPS_OBS OBS@2=K:GPS_OBS PAN_DN=H:AS1000_MFD_JOYSTICK_DOWN PAN_LEFT=H:AS1000_MFD_JOYSTICK_LEFT
        PAN_RIGHT=H:AS1000_MFD_JOYSTICK_RIGHT PAN_UP=H:AS1000_MFD_JOYSTICK_UP PROC=H:AS1000_MFD_PROC_Push
        PROC@2=H:AS1000_PFD_PROC_Push PTR=H:AS1000_MFD_JOYSTICK_PUSH RANGE_CCW=H:AS1000_MFD_RANGE_DEC
        RANGE_CW=H:AS1000_MFD_RANGE_INC S_DN=K:AP_VS_VAR_DEC,K:AP_SPD_VAR_INC,K:AP_PITCH_REF_INC_DN
        S_ENT=H:AS1000_MFD_ENT_Push S_ENT@2=H:AS1000_PFD_ENT_Push S_FLC=K:FLIGHT_LEVEL_CHANGE
        S_PAN_DN=H:AS1000_PFD_JOYSTICK_DOWN S_PAN_LEFT=H:AS1000_PFD_JOYSTICK_LEFT
        S_PAN_RIGHT=H:AS1000_PFD_JOYSTICK_RIGHT S_PAN_UP=H:AS1000_PFD_JOYSTICK_UP S_PTR=H:AS1000_PFD_JOYSTICK_PUSH
        S_RANGE_CCW=H:AS1000_PFD_RANGE_DEC S_RANGE_CW=H:AS1000_PFD_RANGE_INC
        S_UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP S_VNV=H:AS1000_VNAV_TOGGLE S_VS=K:AP_VS_HOLD
        TERR=H:AS1000_MFD_SOFTKEYS_12 TERR@2=H:AS1000_MFD_SOFTKEYS_12
        UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP VNAV=H:AS1000_MFD_SOFTKEYS_10
        VNAV@2=H:AS1000_MFD_SOFTKEYS_10 VNV=H:AS1000_VNAV_TOGGLE VS=K:AP_VS_HOLD XPDR_MODE=1,1,4,A:TRANSPONDER_STATE:1
        YD=K:YAW_DAMPER_TOGGLE
    """,
    "g3x": """
        ADF_SWAP=K:ADF1_RADIO_SWAP ADF_SWAP@2=K:ADF1_RADIO_SWAP ALT=K:AP_ALT_HOLD ALT_1000_DN=1000,K:AP_ALT_VAR_DEC
        ALT_1000_UP=1000,K:AP_ALT_VAR_INC ALT_100_DN=K:AP_ALT_VAR_DEC ALT_100_UP=K:AP_ALT_VAR_INC AP=K:AP_MASTER
        APR=K:AP_APR_HOLD BARO_DN=1,K:KOHLSMAN_DEC
        BARO_STD=1,K:BAROMETRIC_STD_PRESSURE
        BARO_UP=1,K:KOHLSMAN_INC
        CABIN_LT=K:TOGGLE_CABIN_LIGHTS CDI=K:TOGGLE_GPS_DRIVES_NAV1 CDI@2=K:TOGGLE_GPS_DRIVES_NAV1
        CLR=H:AS3X_Touch_1_Back_Push CLR@2=H:AS3X_Touch_2_Back_Push
        CRS_10_DN=10,-,K:GPS_OBS_SET,2,10,-,K:VOR2_SET,10,-,K:VOR1_SET
        CRS_10_UP=10,+,K:GPS_OBS_SET,2,10,+,K:VOR2_SET,10,+,K:VOR1_SET
        CRS_1_DN=K:GPS_OBS_DEC,2,K:VOR2_OBI_DEC,K:VOR1_OBI_DEC CRS_1_UP=K:GPS_OBS_INC,2,K:VOR2_OBI_INC,K:VOR1_OBI_INC
        CRS_CTR=2,K:VOR2_SET,180,+,K:VOR2_SET,K:VOR1_SET,180,+,K:VOR1_SET DIRECT=H:AS3X_Touch_1_DirectTo_Push
        DIRECT@2=H:AS3X_Touch_2_DirectTo_Push DN=K:AP_VS_VAR_DEC,K:AP_SPD_VAR_INC,K:AP_PITCH_REF_INC_DN
        FD=K:TOGGLE_FLIGHT_DIRECTOR FLC=K:FLIGHT_LEVEL_CHANGE FMS_CRSR=H:AS3X_Touch_1_Knob_Inner_R_PUSH
        FMS_CRSR@2=H:AS3X_Touch_2_Knob_Inner_R_PUSH FMS_INNER_CCW=H:AS3X_Touch_1_Knob_Inner_R_DEC
        FMS_INNER_CCW@2=H:AS3X_Touch_2_Knob_Inner_R_DEC FMS_INNER_CW=H:AS3X_Touch_1_Knob_Inner_R_INC
        FMS_INNER_CW@2=H:AS3X_Touch_2_Knob_Inner_R_INC FMS_OUTER_CCW=H:AS3X_Touch_1_Knob_Outer_R_DEC
        FMS_OUTER_CCW@2=H:AS3X_Touch_2_Knob_Outer_R_DEC FMS_OUTER_CW=H:AS3X_Touch_1_Knob_Outer_R_INC
        FMS_OUTER_CW@2=H:AS3X_Touch_2_Knob_Outer_R_INC HDG=K:AP_HDG_HOLD
        LVL=K:AP_WING_LEVELER_ON,K:AP_PITCH_LEVELER_ON,K:AUTOPILOT_ON MENU=H:AS3X_Touch_1_Menu_Push
        MENU@2=H:AS3X_Touch_2_Menu_Push
        MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET,1,K:COM1_RECEIVE_SELECT
        MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET,1,K:COM2_RECEIVE_SELECT NAV=K:AP_NAV1_HOLD
        NRST=H:AS3X_Touch_1_NRST_Push
        NRST@2=H:AS3X_Touch_2_NRST_Push OBS=K:GPS_OBS OBS@2=K:GPS_OBS
        S_DN=K:AP_VS_VAR_DEC,K:AP_SPD_VAR_INC,K:AP_PITCH_REF_INC_DN S_FLC=K:FLIGHT_LEVEL_CHANGE
        S_UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP S_VNV=H:AS1000_VNAV_TOGGLE S_VS=K:AP_VS_HOLD
        UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP VNV=H:AS1000_VNAV_TOGGLE VS=K:AP_VS_HOLD
        XPDR_MODE=1,1,4,A:TRANSPONDER_STATE:1 YD=K:YAW_DAMPER_TOGGLE
    """,
    "gns": """
        S_VS=0,K:AP_PANEL_VS_ON VS=0,K:AP_PANEL_VS_ON
        ADF_SWAP=K:ADF1_RADIO_SWAP ADF_SWAP@2=K:ADF1_RADIO_SWAP ALT=H:KAP140_Push_ALT
        ALT_1000_DN=H:KAP140_Knob_Outer_DEC ALT_1000_UP=H:KAP140_Knob_Outer_INC ALT_100_DN=H:KAP140_Knob_Inner_DEC
        ALT_100_UP=H:KAP140_Knob_Inner_INC AP=H:KAP140_Push_AP APR=H:KAP140_Push_APR
        BARO_DN=K:KOHLSMAN_DEC,0,L:AvionicsPanel_Baro
        BARO_STD=1013.23,-,0.1,0,16,K:KOHLSMAN_SET,0,L:AvionicsPanel_Baro,L:AvionicsPanel_Baro,1,K:BAROMETRIC_STD_PRESSURE
        BARO_UP=K:KOHLSMAN_INC,0,L:AvionicsPanel_Baro BC=H:KAP140_Push_REV CABIN_LT=K:TOGGLE_CABIN_LIGHTS
        CDI=H:AS530_CDI_Push CDI@2=H:AS430_CDI_Push CLR=H:AS530_CLR_Push CLR@2=H:AS430_CLR_Push
        CRS_10_DN=10,-,K:VOR1_SET CRS_10_UP=10,+,K:VOR1_SET CRS_1_DN=K:VOR1_OBI_DEC CRS_1_UP=K:VOR1_OBI_INC
        CRS_CTR=K:VOR1_SET,180,+,K:VOR1_SET DIRECT=H:AS530_DirectTo_Push DIRECT@2=H:AS430_DirectTo_Push
        DN=H:KAP140_Push_DN ENT=H:AS530_ENT_Push ENT@2=H:AS430_ENT_Push FMS_CRSR=H:AS530_RightSmallKnob_Push
        FMS_CRSR@2=H:AS430_RightSmallKnob_Push FMS_INNER_CCW=H:AS530_RightSmallKnob_Left
        FMS_INNER_CCW@2=H:AS430_RightSmallKnob_Left FMS_INNER_CW=H:AS530_RightSmallKnob_Right
        FMS_INNER_CW@2=H:AS430_RightSmallKnob_Right FMS_OUTER_CCW=H:AS530_RightLargeKnob_Left
        FMS_OUTER_CCW@2=H:AS430_RightLargeKnob_Left FMS_OUTER_CW=H:AS530_RightLargeKnob_Right
        FMS_OUTER_CW@2=H:AS430_RightLargeKnob_Right FPL=H:AS530_FPL_Push FPL@2=H:AS430_FPL_Push HDG=H:KAP140_Push_HDG
        MAP=H:AS530_CLR_Push_Long MAP@2=H:AS430_CLR_Push_Long MENU=H:AS530_MENU_Push MENU@2=H:AS430_MENU_Push
        MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET,1,K:COM1_RECEIVE_SELECT
        MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET,1,K:COM2_RECEIVE_SELECT MSG=H:AS530_MSG_Push
        MSG@2=H:AS430_MSG_Push
        NAV=H:KAP140_Push_NAV OBS=H:AS530_OBS_Push OBS@2=H:AS430_OBS_Push PAN_DN=K:COM1_VOLUME_DEC
        PAN_UP=K:COM1_VOLUME_INC PROC=H:AS530_PROC_Push PROC@2=H:AS430_PROC_Push RANGE_CCW=H:AS530_RNG_Zoom
        RANGE_CW=H:AS530_RNG_Dezoom S_DN=H:KAP140_Push_DN S_ENT=H:AS530_ENT_Push S_ENT@2=H:AS430_ENT_Push
        S_PAN_DN=K:COM2_VOLUME_DEC S_PAN_UP=K:COM2_VOLUME_INC S_RANGE_CCW=H:AS430_RNG_Zoom S_RANGE_CW=H:AS430_RNG_Dezoom
        S_UP=H:KAP140_Push_UP
        S_VNV=-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,0,K:AP_PANEL_VS_ON,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next/-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next
        UP=H:KAP140_Push_UP VNAV=H:AS530_VNAV_Push
        VNV=-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,0,K:AP_PANEL_VS_ON,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next/-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next
        XPDR_MODE=1,1,4,A:TRANSPONDER_STATE:1
    """,
    "gtn": """
        S_VS=0,K:AP_PANEL_VS_ON VS=0,K:AP_PANEL_VS_ON
        ADF_SWAP=K:ADF1_RADIO_SWAP ADF_SWAP@2=K:ADF1_RADIO_SWAP ALT=H:KAP140_Push_ALT
        ALT_1000_DN=H:KAP140_Knob_Outer_DEC ALT_1000_UP=H:KAP140_Knob_Outer_INC ALT_100_DN=H:KAP140_Knob_Inner_DEC
        ALT_100_UP=H:KAP140_Knob_Inner_INC AP=H:KAP140_Push_AP APR=H:KAP140_Push_APR
        BARO_DN=K:KOHLSMAN_DEC,0,L:AvionicsPanel_Baro
        BARO_STD=1013.23,-,0.1,0,16,K:KOHLSMAN_SET,0,L:AvionicsPanel_Baro,L:AvionicsPanel_Baro,1,K:BAROMETRIC_STD_PRESSURE
        BARO_UP=K:KOHLSMAN_INC,0,L:AvionicsPanel_Baro BC=H:KAP140_Push_REV CABIN_LT=K:TOGGLE_CABIN_LIGHTS
        CRS_10_DN=10,-,K:VOR1_SET CRS_10_UP=10,+,K:VOR1_SET CRS_1_DN=K:VOR1_OBI_DEC CRS_1_UP=K:VOR1_OBI_INC
        CRS_CTR=K:VOR1_SET,180,+,K:VOR1_SET DIRECT=2,K:GPS_DIRECTTO_BUTTON/4,K:GPS_DIRECTTO_BUTTON
        DIRECT@2=26,K:GPS_DIRECTTO_BUTTON/28,K:GPS_DIRECTTO_BUTTON DN=H:KAP140_Push_DN
        FMS_CRSR=2,K:GPS_CURSOR_BUTTON/4,K:GPS_CURSOR_BUTTON FMS_CRSR@2=26,K:GPS_CURSOR_BUTTON/28,K:GPS_CURSOR_BUTTON
        FMS_INNER_CCW=0,K:GPS_PAGE_KNOB_DEC FMS_INNER_CCW@2=24,K:GPS_PAGE_KNOB_DEC FMS_INNER_CW=0,K:GPS_PAGE_KNOB_INC
        FMS_INNER_CW@2=24,K:GPS_PAGE_KNOB_INC FMS_OUTER_CCW=0,K:GPS_GROUP_KNOB_DEC
        FMS_OUTER_CCW@2=24,K:GPS_GROUP_KNOB_DEC FMS_OUTER_CW=0,K:GPS_GROUP_KNOB_INC
        FMS_OUTER_CW@2=24,K:GPS_GROUP_KNOB_INC HDG=H:KAP140_Push_HDG HOME=2,K:GPS_MENU_BUTTON/4,K:GPS_MENU_BUTTON
        HOME@2=26,K:GPS_MENU_BUTTON/28,K:GPS_MENU_BUTTON
        MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET,1,K:COM1_RECEIVE_SELECT
        MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET,1,K:COM2_RECEIVE_SELECT NAV=H:KAP140_Push_NAV
        PAN_DN=2,K:GPS_BUTTON2
        PAN_UP=4,K:GPS_BUTTON2 PTR=2,K:GPS_BUTTON1/4,K:GPS_BUTTON1 RANGE_CCW=0,K:GPS_PAGE_KNOB_INC
        RANGE_CW=0,K:GPS_PAGE_KNOB_DEC S_DN=H:KAP140_Push_DN S_PAN_DN=26,K:GPS_BUTTON2 S_PAN_UP=28,K:GPS_BUTTON2
        S_PTR=26,K:GPS_BUTTON1/28,K:GPS_BUTTON1 S_RANGE_CCW=24,K:GPS_PAGE_KNOB_INC S_RANGE_CW=24,K:GPS_PAGE_KNOB_DEC
        S_UP=H:KAP140_Push_UP
        S_VNV=0,-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,0,K:AP_PANEL_VS_ON,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next/0,-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next
        UP=H:KAP140_Push_UP
        VNV=0,-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,0,K:AP_PANEL_VS_ON,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next/0,-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next
        XPDR_MODE=1,1,4,A:TRANSPONDER_STATE:1
    """,
    BONANZA: """
        ADF_SWAP=H:adf_frqTransfert ADF_SWAP@2=H:adf_frqTransfert ALT=K:AP_ALT_HOLD ALT_1000_DN=H:kas297b_1000_DEC
        ALT_1000_UP=H:kas297b_1000_INC ALT_100_DN=H:kas297b_100_DEC ALT_100_UP=H:kas297b_100_INC AP=K:AP_MASTER
        APR=K:AP_APR_HOLD ARM=H:kas297b_ArmButton
        BARO_DN=0.3386389,1,-,0.3386389,16,K:KOHLSMAN_SET,2,K:2:KOHLSMAN_SET,0,L:AvionicsPanel_Baro
        BARO_STD=1013.23,-,0.1,0,16,K:KOHLSMAN_SET,2,K:2:KOHLSMAN_SET,0,L:AvionicsPanel_Baro,1,K:BAROMETRIC_STD_PRESSURE,2,K:BAROMETRIC_STD_PRESSURE,L:AvionicsPanel_Baro,1,K:BAROMETRIC_STD_PRESSURE,2,K:BAROMETRIC_STD_PRESSURE
        BARO_UP=0.3386389,1,+,0.3386389,16,K:KOHLSMAN_SET,2,K:2:KOHLSMAN_SET,0,L:AvionicsPanel_Baro BC=K:AP_BC_HOLD
        CABIN_LT=0,1,L:var_LIGHTING_Push_Cockpit_1,L:var_LIGHTING_Push_Cockpit_2,L:var_LIGHTING_Push_Cockpit_3,L:var_LIGHTING_Push_Cockpit_4,L:var_LIGHTING_Push_Cockpit_5,L:var_LIGHTING_Push_Cockpit_6,L:OatMapCompassLightButton_2,L:var_OatMapCompassLightButton_2
        CDI=K:TOGGLE_GPS_DRIVES_NAV1 CDI@2=H:AS430_CDI_Push CLR=H:AS530_CLR_Push,H:GTN750_BACK,H:KLN90B_CLR_Push
        CLR@2=H:AS430_CLR_Push,H:GTN650_2_BACK,H:GTN650_BACK CRS_10_DN=10,-,K:VOR1_SET CRS_10_UP=10,+,K:VOR1_SET
        CRS_1_DN=K:VOR1_OBI_DEC CRS_1_UP=K:VOR1_OBI_INC CRS_CTR=K:VOR1_SET,180,+,K:VOR1_SET
        DIRECT=H:AS530_DirectTo_Push,2,K:GPS_DIRECTTO_BUTTON,H:GTN750_DirectToPush,H:KLN90B_DCT_Push/4,K:GPS_DIRECTTO_BUTTON
        DIRECT@2=H:AS430_DirectTo_Push,10,K:GPS_DIRECTTO_BUTTON,26,K:GPS_DIRECTTO_BUTTON,H:GTN650_2_DirectToPush,H:GTN650_DirectToPush/12,K:GPS_DIRECTTO_BUTTON,28,K:GPS_DIRECTTO_BUTTON
        DN=100,K:AP_ALT_VAR_DEC,K:AP_VS_VAR_DEC,K:AP_PITCH_REF_INC_DN
        ENT=H:AS530_ENT_Push,H:GTN750_ENTER,H:KLN90B_ENT_Push ENT@2=H:AS430_ENT_Push,H:GTN650_2_ENTER,H:GTN650_ENTER
        FD=K:TOGGLE_FLIGHT_DIRECTOR FLC=5,-,0,L:var_RadarTilt
        FLOOD_LT_DN=5,-,0,L:var_GlareshieldLightingKnob,0,L:bksq_MasterGlareshieldLights,0,L:OatMapCompassLightButton_1,0,L:var_OatMapCompassLightButton_1
        FLOOD_LT_UP=5,+,100,L:var_GlareshieldLightingKnob,0,L:bksq_MasterGlareshieldLights,0,L:OatMapCompassLightButton_1,0,L:var_OatMapCompassLightButton_1
        FMS_CRSR=H:AS530_RightSmallKnob_Push,2,K:GPS_CURSOR_BUTTON,H:GTN750_KnobPush,H:KLN90B_RightCursor_Toggle/4,K:GPS_CURSOR_BUTTON
        FMS_CRSR@2=H:AS430_RightSmallKnob_Push,10,K:GPS_CURSOR_BUTTON,26,K:GPS_CURSOR_BUTTON,H:GTN650_2_KnobPush,H:GTN650_KnobPush/12,K:GPS_CURSOR_BUTTON,28,K:GPS_CURSOR_BUTTON
        FMS_INNER_CCW=H:AS530_RightSmallKnob_Left,0,K:GPS_PAGE_KNOB_DEC,H:GTN750_KnobSmallDec,H:KLN90B_RightSmallKnob_Left
        FMS_INNER_CCW@2=H:AS430_RightSmallKnob_Left,8,K:GPS_PAGE_KNOB_DEC,24,K:GPS_PAGE_KNOB_DEC,H:GTN650_2_KnobSmallDec,H:GTN650_KnobSmallDec
        FMS_INNER_CW=H:AS530_RightSmallKnob_Right,0,K:GPS_PAGE_KNOB_INC,H:GTN750_KnobSmallInc,H:KLN90B_RightSmallKnob_Right
        FMS_INNER_CW@2=H:AS430_RightSmallKnob_Right,8,K:GPS_PAGE_KNOB_INC,24,K:GPS_PAGE_KNOB_INC,H:GTN650_2_KnobSmallInc,H:GTN650_KnobSmallInc
        FMS_OUTER_CCW=H:AS530_RightLargeKnob_Left,0,K:GPS_GROUP_KNOB_DEC,H:GTN750_KnobLargeDec,H:KLN90B_RightLargeKnob_Left
        FMS_OUTER_CCW@2=H:AS430_RightLargeKnob_Left,8,K:GPS_GROUP_KNOB_DEC,24,K:GPS_GROUP_KNOB_DEC,H:GTN650_2_KnobLargeDec,H:GTN650_KnobLargeDec
        FMS_OUTER_CW=H:AS530_RightLargeKnob_Right,0,K:GPS_GROUP_KNOB_INC,H:GTN750_KnobLargeInc,H:KLN90B_RightLargeKnob_Right
        FMS_OUTER_CW@2=H:AS430_RightLargeKnob_Right,8,K:GPS_GROUP_KNOB_INC,24,K:GPS_GROUP_KNOB_INC,H:GTN650_2_KnobLargeInc,H:GTN650_KnobLargeInc
        FPL=H:AS530_FPL_Push FPL@2=H:AS430_FPL_Push GPSS=L:var_rnavDrivesHsi HALF_BANK=5,+,100,L:var_RadarTilt
        HDG=K:AP_PANEL_HEADING_HOLD HOME=2,K:GPS_MENU_BUTTON,H:GTN750_HomePush/4,K:GPS_MENU_BUTTON
        HOME@2=10,K:GPS_MENU_BUTTON,26,K:GPS_MENU_BUTTON,H:GTN650_2_HomePush,H:GTN650_HomePush/12,K:GPS_MENU_BUTTON,28,K:GPS_MENU_BUTTON
        LVL=1,+,5,L:var_dmeMode MAP=H:AS530_CLR_Push_Long MAP@2=H:AS430_CLR_Push_Long
        MENU=H:AS530_MENU_Push,H:GTN750_MENU,H:KLN90B_ALT_Push MENU@2=H:AS430_MENU_Push,H:GTN650_2_MENU,H:GTN650_MENU
        MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET,1,K:COM1_RECEIVE_SELECT,0,L:var_PilotTransmitSelector
        MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET,1,K:COM2_RECEIVE_SELECT,1,L:var_PilotTransmitSelector
        MSG=H:AS530_MSG_Push,H:GTN750_MSG,H:KLN90B_MSG_Push MSG@2=H:AS430_MSG_Push,H:GTN650_2_MSG,H:GTN650_MSG
        NAV=K:AP_NAV1_HOLD NRST=H:KLN90B_ApprArm_Push OBS=H:AS530_OBS_Push OBS@2=H:AS430_OBS_Push
        PANEL_LT_DN=5,-,0,L:var_FlightInstrumentsLightingKnob,L:var_EngineInstrumentsLightingKnob,L:var_SubpanelLightingKnob,0,L:bksq_MasterPanelLights
        PANEL_LT_UP=5,+,100,L:var_FlightInstrumentsLightingKnob,L:var_EngineInstrumentsLightingKnob,L:var_SubpanelLightingKnob,0,L:bksq_MasterPanelLights
        PAN_DN=K:COM1_VOLUME_DEC,2,K:GPS_BUTTON2,H:GTN750_VolDec PAN_LEFT=H:KLN90B_LeftLargeKnob_Left
        PAN_RIGHT=H:KLN90B_LeftLargeKnob_Right PAN_UP=K:COM1_VOLUME_INC,4,K:GPS_BUTTON2,H:GTN750_VolInc
        PROC=H:AS530_PROC_Push,H:GTN750_GoToPage-HOME-PageProcs
        PROC@2=H:AS430_PROC_Push,H:GTN650_2_GoToPage-HOME-PageProcs,H:GTN650_GoToPage-HOME-PageProcs
        PTR=2,K:GPS_BUTTON1,H:GTN750_VolPush,H:KLN90B_LeftCursor_Toggle/4,K:GPS_BUTTON1
        RANGE_CCW=H:AS530_RNG_Zoom,0,K:GPS_PAGE_KNOB_INC,H:GTN750_KnobSmallInc,H:KLN90B_LeftSmallKnob_Left
        RANGE_CW=H:AS530_RNG_Dezoom,0,K:GPS_PAGE_KNOB_DEC,H:GTN750_KnobSmallDec,H:KLN90B_LeftSmallKnob_Right
        S_DN=H:bksq_JpiButton_1_R_Short/H:bksq_JpiButton_1_R_Long
        S_ENT=H:AS530_ENT_Push,H:GTN750_ENTER,H:KLN90B_ENT_Push S_ENT@2=H:AS430_ENT_Push,H:GTN650_2_ENTER,H:GTN650_ENTER
        S_FLC=H:adf_AntAdf
        S_PAN_DN=K:COM2_VOLUME_DEC,10,K:GPS_BUTTON2,26,K:GPS_BUTTON2,H:GTN650_2_VolDec,H:GTN650_VolDec
        S_PAN_LEFT=H:bksq_wradar1_radarRangeDec S_PAN_RIGHT=H:bksq_wradar1_radarRangeInc
        S_PAN_UP=K:COM2_VOLUME_INC,12,K:GPS_BUTTON2,28,K:GPS_BUTTON2,H:GTN650_2_VolInc,H:GTN650_VolInc
        S_PTR=10,K:GPS_BUTTON1,26,K:GPS_BUTTON1,H:GTN650_2_VolPush,H:GTN650_VolPush/12,K:GPS_BUTTON1,28,K:GPS_BUTTON1
        S_RANGE_CCW=H:AS430_RNG_Zoom,8,K:GPS_PAGE_KNOB_INC,24,K:GPS_PAGE_KNOB_INC,H:GTN650_2_KnobSmallInc,H:GTN650_KnobSmallInc
        S_RANGE_CW=H:AS430_RNG_Dezoom,8,K:GPS_PAGE_KNOB_DEC,24,K:GPS_PAGE_KNOB_DEC,H:GTN650_2_KnobSmallDec,H:GTN650_KnobSmallDec
        S_UP=H:bksq_JpiButton_1_L_Short/H:bksq_JpiButton_1_L_Long S_VNV=H:adf_bfo S_VS=H:kas297b_VsButton TERR=K:GPS_OBS
        TEST=20,L:var_AutopilotStartupCounter,1,L:var_md41Test/0,L:var_md41Test
        UP=100,K:AP_ALT_VAR_INC,K:AP_VS_VAR_INC,K:AP_PITCH_REF_INC_UP
        VFR=7000,1000,4096,100,10,256,+,10,10,16,+,10,+,K:XPNDR_SET,0,L:AvionicsPanel_Squawk_Kept,H:TRANSPONDER_Push_ALT,L:AvionicsPanel_Squawk,1,L:AvionicsPanel_Squawk_Kept,1000,4096,100,10,256,+,10,10,16,+,10,+,K:XPNDR_SET,H:TRANSPONDER_Push_ALT
        VNAV=H:AS530_VNAV_Push
        VNV=0,0,-,0,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,K:AP_VS_VAR_SET_ENGLISH,H:kas297b_VsButton,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next
        VS=H:kas297b_VsButton XPDR_MODE=1,H:TRANSPONDER_Push_STBY,H:TRANSPONDER_Push_ALT YD=K:YAW_DAMPER_TOGGLE
    """,
    "cows-da40": """
        ADF_SWAP=K:ADF1_RADIO_SWAP ADF_SWAP@2=K:ADF1_RADIO_SWAP ALT=K:AP_ALT_HOLD ALT_1000_DN=1000,K:AP_ALT_VAR_DEC
        ALT_1000_UP=1000,K:AP_ALT_VAR_INC ALT_100_DN=K:AP_ALT_VAR_DEC ALT_100_UP=K:AP_ALT_VAR_INC AP=K:AP_MASTER
        APR=K:AP_APR_HOLD ARM=H:AS1000_PFD_SOFTKEYS_10
        BARO_DN=H:AS1000_PFD_BARO_DEC,1013.23,-,0.1,100,2992,0,100,100,100,-,1,4,1,+,1,-,3150,2800,100,L:KOHLSMAN_SETTING_HG:2,0,L:AvionicsPanel_Standby_Baro
        BARO_STD=H:AS1000_PFD_SOFTKEYS_4,H:AS1000_PFD_SOFTKEYS_10,1013.23,-,0.1,0,100,3150,2800,100,L:KOHLSMAN_SETTING_HG:2,0,L:AvionicsPanel_Standby_Baro,100,100,L:AvionicsPanel_Standby_Baro,2992,3150,2800,100,L:KOHLSMAN_SETTING_HG:2
        BARO_UP=H:AS1000_PFD_BARO_INC,1013.23,-,0.1,100,2992,0,100,100,100,-,1,4,1,-,1,+,3150,2800,100,L:KOHLSMAN_SETTING_HG:2,0,L:AvionicsPanel_Standby_Baro
        BC=K:AP_BC_HOLD CABIN_LT=0,1,B:LIGHTING_CABIN_1_Set,B:LIGHTING_CABIN_2_Set,B:LIGHTING_CABIN_3_Set
        CDI=3,1,K:AP_NAV_SELECT_SET,1,2,K:AP_NAV_SELECT_SET,K:TOGGLE_GPS_DRIVES_NAV1
        CDI@2=3,1,K:AP_NAV_SELECT_SET,1,2,K:AP_NAV_SELECT_SET,K:TOGGLE_GPS_DRIVES_NAV1 CLR=H:AS1000_MFD_CLR
        CLR@2=H:AS1000_PFD_CLR CRS_10_DN=3,10,-,K:GPS_OBS_SET,2,10,-,K:VOR2_SET,10,-,K:VOR1_SET
        CRS_10_UP=3,10,+,K:GPS_OBS_SET,2,10,+,K:VOR2_SET,10,+,K:VOR1_SET CRS_1_DN=H:AS1000_PFD_CRS_DEC
        CRS_1_UP=H:AS1000_PFD_CRS_INC CRS_CTR=H:AS1000_PFD_CRS_PUSH DIRECT=H:AS1000_MFD_DIRECTTO
        DIRECT@2=H:AS1000_PFD_DIRECTTO DN=K:AP_VS_VAR_DEC,K:AP_SPD_VAR_INC,K:AP_PITCH_REF_INC_DN
        ENT=H:AS1000_MFD_ENT_Push ENT@2=H:AS1000_PFD_ENT_Push FD=K:TOGGLE_FLIGHT_DIRECTOR FLC=K:FLIGHT_LEVEL_CHANGE
        FLOOD_LT_DN=5,-,0,B:LIGHTING_GLARESHIELD_1_Set FLOOD_LT_UP=5,+,100,B:LIGHTING_GLARESHIELD_1_Set
        FMS_CRSR=H:AS1000_MFD_FMS_Upper_PUSH FMS_CRSR@2=H:AS1000_PFD_FMS_Upper_PUSH
        FMS_INNER_CCW=H:AS1000_MFD_FMS_Upper_DEC FMS_INNER_CCW@2=H:AS1000_PFD_FMS_Upper_DEC
        FMS_INNER_CW=H:AS1000_MFD_FMS_Upper_INC FMS_INNER_CW@2=H:AS1000_PFD_FMS_Upper_INC
        FMS_OUTER_CCW=H:AS1000_MFD_FMS_Lower_DEC FMS_OUTER_CCW@2=H:AS1000_PFD_FMS_Lower_DEC
        FMS_OUTER_CW=H:AS1000_MFD_FMS_Lower_INC FMS_OUTER_CW@2=H:AS1000_PFD_FMS_Lower_INC FPL=H:AS1000_MFD_FPL_Push
        FPL@2=H:AS1000_PFD_FPL_Push HDG=K:AP_HDG_HOLD
        HOME=H:AS1000_MFD_SOFTKEYS_11,0,L:AvionicsPanel_G1000_Engine,H:AS1000_MFD_SOFTKEYS_1,1,L:AvionicsPanel_G1000_Engine
        HOME@2=H:AS1000_MFD_SOFTKEYS_11,0,L:AvionicsPanel_G1000_Engine,H:AS1000_MFD_SOFTKEYS_1,1,L:AvionicsPanel_G1000_Engine
        LVL=K:AP_WING_LEVELER_ON,K:AP_PITCH_LEVELER_ON,K:AUTOPILOT_ON MAP=H:AS1000_MFD_SOFTKEYS_11
        MAP@2=H:AS1000_MFD_SOFTKEYS_11 MENU=H:AS1000_MFD_MENU_Push MENU@2=H:AS1000_PFD_MENU_Push
        MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET,1,K:COM1_RECEIVE_SELECT
        MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET,1,K:COM2_RECEIVE_SELECT MSG=H:AS1000_PFD_SOFTKEYS_12
        MSG@2=H:AS1000_PFD_SOFTKEYS_12 NAV=K:AP_NAV1_HOLD NRST=H:AS1000_PFD_SOFTKEYS_11 NRST@2=H:AS1000_PFD_SOFTKEYS_11
        OBS=K:GPS_OBS OBS@2=K:GPS_OBS PANEL_LT_DN=5,-,0,B:LIGHTING_PANEL_1_Set
        PANEL_LT_UP=5,+,100,B:LIGHTING_PANEL_1_Set PAN_DN=H:AS1000_MFD_JOYSTICK_DOWN PAN_LEFT=H:AS1000_MFD_JOYSTICK_LEFT
        PAN_RIGHT=H:AS1000_MFD_JOYSTICK_RIGHT PAN_UP=H:AS1000_MFD_JOYSTICK_UP PROC=H:AS1000_MFD_PROC_Push
        PROC@2=H:AS1000_PFD_PROC_Push PTR=H:AS1000_MFD_JOYSTICK_PUSH RANGE_CCW=H:AS1000_MFD_RANGE_DEC
        RANGE_CW=H:AS1000_MFD_RANGE_INC S_DN=K:AP_VS_VAR_DEC,K:AP_SPD_VAR_INC,K:AP_PITCH_REF_INC_DN
        S_ENT=H:AS1000_MFD_ENT_Push S_ENT@2=H:AS1000_PFD_ENT_Push S_FLC=K:FLIGHT_LEVEL_CHANGE
        S_PAN_DN=H:AS1000_PFD_JOYSTICK_DOWN S_PAN_LEFT=H:AS1000_PFD_JOYSTICK_LEFT
        S_PAN_RIGHT=H:AS1000_PFD_JOYSTICK_RIGHT S_PAN_UP=H:AS1000_PFD_JOYSTICK_UP S_PTR=H:AS1000_PFD_JOYSTICK_PUSH
        S_RANGE_CCW=H:AS1000_PFD_RANGE_DEC S_RANGE_CW=H:AS1000_PFD_RANGE_INC
        S_UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP S_VNV=H:AS1000_VNAV_TOGGLE S_VS=K:AP_VS_HOLD
        TERR=H:AS1000_MFD_SOFTKEYS_12 TERR@2=H:AS1000_MFD_SOFTKEYS_12
        UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP VNAV=H:AS1000_MFD_SOFTKEYS_10
        VNAV@2=H:AS1000_MFD_SOFTKEYS_10 VNV=H:AS1000_VNAV_TOGGLE VS=K:AP_VS_HOLD XPDR_MODE=1,1,4,A:TRANSPONDER_STATE:1
        YD=K:YAW_DAMPER_TOGGLE
    """,
    "carenado-c182t": """
        S_VS=0,K:AP_PANEL_VS_ON VS=0,K:AP_PANEL_VS_ON
        ADF_SWAP=K:ADF1_RADIO_SWAP ADF_SWAP@2=K:ADF1_RADIO_SWAP ALT=H:KAP140_Push_ALT
        ALT_1000_DN=H:KAP140_Knob_Outer_DEC ALT_1000_UP=H:KAP140_Knob_Outer_INC ALT_100_DN=H:KAP140_Knob_Inner_DEC
        ALT_100_UP=H:KAP140_Knob_Inner_INC AP=H:KAP140_Push_AP APR=H:KAP140_Push_APR BARO_DN=H:AS1000_PFD_BARO_DEC
        BARO_STD=H:AS1000_PFD_SOFTKEYS_4,H:AS1000_PFD_SOFTKEYS_10
        BARO_UP=H:AS1000_PFD_BARO_INC BC=H:KAP140_Push_REV CABIN_LT=0,100,B:LIGHTING_CABIN_1_Set,B:LIGHTING_CABIN_2_Set
        CDI=3,1,K:AP_NAV_SELECT_SET,1,2,K:AP_NAV_SELECT_SET,K:TOGGLE_GPS_DRIVES_NAV1
        CDI@2=3,1,K:AP_NAV_SELECT_SET,1,2,K:AP_NAV_SELECT_SET,K:TOGGLE_GPS_DRIVES_NAV1 CLR=H:AS1000_MFD_CLR
        CLR@2=H:AS1000_PFD_CLR CRS_10_DN=3,10,-,K:GPS_OBS_SET,2,10,-,K:VOR2_SET,10,-,K:VOR1_SET
        CRS_10_UP=3,10,+,K:GPS_OBS_SET,2,10,+,K:VOR2_SET,10,+,K:VOR1_SET CRS_1_DN=H:AS1000_PFD_CRS_DEC
        CRS_1_UP=H:AS1000_PFD_CRS_INC CRS_CTR=H:AS1000_PFD_CRS_PUSH DIRECT=H:AS1000_MFD_DIRECTTO
        DIRECT@2=H:AS1000_PFD_DIRECTTO DN=H:KAP140_Push_DN ENT=H:AS1000_MFD_ENT_Push ENT@2=H:AS1000_PFD_ENT_Push
        FLOOD_LT_DN=5,-,0,B:LIGHTING_CABIN_1_Set,B:LIGHTING_CABIN_2_Set
        FLOOD_LT_UP=5,+,100,B:LIGHTING_CABIN_1_Set,B:LIGHTING_CABIN_2_Set
        FMS_CRSR=H:AS1000_MFD_FMS_Upper_PUSH FMS_CRSR@2=H:AS1000_PFD_FMS_Upper_PUSH
        FMS_INNER_CCW=H:AS1000_MFD_FMS_Upper_DEC FMS_INNER_CCW@2=H:AS1000_PFD_FMS_Upper_DEC
        FMS_INNER_CW=H:AS1000_MFD_FMS_Upper_INC FMS_INNER_CW@2=H:AS1000_PFD_FMS_Upper_INC
        FMS_OUTER_CCW=H:AS1000_MFD_FMS_Lower_DEC FMS_OUTER_CCW@2=H:AS1000_PFD_FMS_Lower_DEC
        FMS_OUTER_CW=H:AS1000_MFD_FMS_Lower_INC FMS_OUTER_CW@2=H:AS1000_PFD_FMS_Lower_INC FPL=H:AS1000_MFD_FPL_Push
        FPL@2=H:AS1000_PFD_FPL_Push HDG=H:KAP140_Push_HDG
        HOME=H:AS1000_MFD_SOFTKEYS_11,0,L:AvionicsPanel_G1000_Engine,H:AS1000_MFD_SOFTKEYS_1,1,L:AvionicsPanel_G1000_Engine
        HOME@2=H:AS1000_MFD_SOFTKEYS_11,0,L:AvionicsPanel_G1000_Engine,H:AS1000_MFD_SOFTKEYS_1,1,L:AvionicsPanel_G1000_Engine
        MAP=H:AS1000_MFD_SOFTKEYS_11 MAP@2=H:AS1000_MFD_SOFTKEYS_11 MENU=H:AS1000_MFD_MENU_Push
        MENU@2=H:AS1000_PFD_MENU_Push MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET,1,K:COM1_RECEIVE_SELECT
        MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET,1,K:COM2_RECEIVE_SELECT MSG=H:AS1000_PFD_SOFTKEYS_12
        MSG@2=H:AS1000_PFD_SOFTKEYS_12 NAV=H:KAP140_Push_NAV NRST=H:AS1000_PFD_SOFTKEYS_11
        NRST@2=H:AS1000_PFD_SOFTKEYS_11 OBS=K:GPS_OBS OBS@2=K:GPS_OBS
        PANEL_LT_DN=5,-,0,B:LIGHTING_POTENTIOMETER_3_Set,B:LIGHTING_PANEL_1_Set,B:LIGHTING_PEDESTRAL_1_Set,B:LIGHTING_POTENTIOMETER_4_Set
        PANEL_LT_UP=5,+,100,B:LIGHTING_POTENTIOMETER_3_Set,B:LIGHTING_PANEL_1_Set,B:LIGHTING_PEDESTRAL_1_Set,B:LIGHTING_POTENTIOMETER_4_Set
        PAN_DN=H:AS1000_MFD_JOYSTICK_DOWN PAN_LEFT=H:AS1000_MFD_JOYSTICK_LEFT PAN_RIGHT=H:AS1000_MFD_JOYSTICK_RIGHT
        PAN_UP=H:AS1000_MFD_JOYSTICK_UP PROC=H:AS1000_MFD_PROC_Push PROC@2=H:AS1000_PFD_PROC_Push
        PTR=H:AS1000_MFD_JOYSTICK_PUSH RANGE_CCW=H:AS1000_MFD_RANGE_DEC RANGE_CW=H:AS1000_MFD_RANGE_INC
        S_DN=H:KAP140_Push_DN S_ENT=H:AS1000_MFD_ENT_Push S_ENT@2=H:AS1000_PFD_ENT_Push
        S_PAN_DN=H:AS1000_PFD_JOYSTICK_DOWN S_PAN_LEFT=H:AS1000_PFD_JOYSTICK_LEFT
        S_PAN_RIGHT=H:AS1000_PFD_JOYSTICK_RIGHT S_PAN_UP=H:AS1000_PFD_JOYSTICK_UP S_PTR=H:AS1000_PFD_JOYSTICK_PUSH
        S_RANGE_CCW=H:AS1000_PFD_RANGE_DEC S_RANGE_CW=H:AS1000_PFD_RANGE_INC S_UP=H:KAP140_Push_UP
        S_VNV=-,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,0,K:AP_PANEL_VS_ON,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next/-,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next
        TERR=H:AS1000_MFD_SOFTKEYS_12 TERR@2=H:AS1000_MFD_SOFTKEYS_12 UP=H:KAP140_Push_UP VNAV=H:AS1000_MFD_SOFTKEYS_10
        VNAV@2=H:AS1000_MFD_SOFTKEYS_10
        VNV=-,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,0,K:AP_PANEL_VS_ON,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next/-,300,0,0,0,30,60,100,100,300,0,2000,1500,0,1.3,0.95,0,0,100,0,100,K:AP_VS_VAR_SET_ENGLISH,L:AvPanel_VNV_Rate,1,L:AvPanel_VNV,30,+,L:AvPanel_VNV_Next
        XPDR_MODE=1,1,4,A:TRANSPONDER_STATE:1
    """,
}


@FAMILY
def test_what_every_function_sets(key):
    # a family's own row replaces EVERY's: the Bonanza's VFR selects ALT with its GTX 327's key
    found = {f"{button}{'@2' * (device == 2)}={'/'.join(uses(code) for code in profile.actions(entry).values())}"
             for device, buttons in FAMILIES[key].DEVICE.items() for button, entry in buttons.items()}
    rows = dict(row.split("=", 1) for row in EVERY.split())
    rows.update(row.split("=", 1) for row in SETS[key].split())
    assert found == {f"{button}={uses_}" for button, uses_ in rows.items()}


def test_the_vfr_key_sets_the_squawk_asked_for():
    # XPNDR_SET takes the code in Bco16, a digit to a hex digit, which the code packs itself: the tables' 7000
    # (0x7000) unless another is asked for, and nothing else changes with it
    for key in FAMILIES:
        usual, other = items(build(key=key)), items(profile.build(FAMILIES[key], PANEL, "1200"))
        [(a, b)] = [(a, b) for a, b in zip(usual, other, strict=True) if a != b]
        assert a["Name"] == b["Name"] and a["Name"].startswith("VFR: XPNDR_SET, ")
        for item, code in ((a, 7000), (b, 1200)):
            [value] = [v for e, v in run(item["button"]["onPress"]["Command"], {
                "TRANSPONDER CODE:1": 4521, "L:AvionicsPanel_Squawk_Kept": 0}) if e == "K:XPNDR_SET"]
            assert value == int(str(code), 16), (key, value)
        assert items(profile.build(FAMILIES[key], PANEL, 1200)) == other
        assert items(profile.build(FAMILIES[key], PANEL, "7000")) == usual
    for bad in ("7800", "120", "12000", "VFR", "", 120):
        with pytest.raises(ValueError, match="not a squawk code"):
            profile.build(FAMILIES["g1000"], PANEL, bad)


def test_squawk_packs_the_digits_a_digit_to_a_hex_digit_for_every_code():
    # XPNDR_SET takes 0x1200 for 1200: the simulator does not convert an L: variable read as Bco16 (in flight 7000
    # went out as 0x1B58, which the transponder showed as 1350), so the code packs the digits itself
    for n in range(4096):
        digits = int(f"{n:04o}")                                     # every code of four digits 0 to 7, as a number
        assert run(parts.squawk(str(digits))) == [("K:XPNDR_SET", int(str(digits), 16))], digits
    assert "Bco16" not in parts.vfr()


@FAMILY
def test_vfr_toggles_the_vfr_code(key):
    # from another code VFR keeps it, squawks 7000 and selects ALT (Black Square's GTX 327 by its ALT key); on 7000
    # it squawks the code kept, once, and leaves the mode; with none kept it only selects ALT. 0000 is a code too.
    code = FAMILIES[key].DEVICE[1]["VFR"]
    alt = ("H:TRANSPONDER_Push_ALT", None) if key == BONANZA else ("A:TRANSPONDER STATE:1", 4)
    kept, keeps = "L:AvionicsPanel_Squawk", "L:AvionicsPanel_Squawk_Kept"
    for other in (4521, 0):
        out = run(code, {"TRANSPONDER CODE:1": other, keeps: 0})
        assert out == [(kept, other), (keeps, 1), ("K:XPNDR_SET", 0x7000), alt]
        out = run(code, {"TRANSPONDER CODE:1": 7000, keeps: 1, kept: other})
        assert out == [("K:XPNDR_SET", int(f"{other:04d}", 16)), (keeps, 0)]      # 4521 back as 0x4521
    assert run(code, {"TRANSPONDER CODE:1": 7000, keeps: 0}) == [alt]
    # a code entered with the squawk digits forgets the code kept
    for d, step in ((1, 1000), (2, 100), (3, 10), (4, 1)):
        for way, event in (("UP", "INC"), ("DN", "DEC")):
            assert run(FAMILIES[key].DEVICE[1][f"SQK_D{d}_{way}"]) == [(f"K:XPNDR_{step}_{event}", None), (keeps, 0)]


def test_a_vfr_code_replaces_the_squawk_of_the_table():
    # a table's VFR toggle keeps its code unless one is asked for, 1200 included, and its way to select ALT; a VFR
    # key that sets no squawk, or a squawk without the toggle, takes no code
    def command(entry, vfr):
        class Family:
            NAME = "test"
            DEVICE = {1: {"VFR": entry}, 2: {}}
        [item] = items(profile.build(Family, PANEL, vfr))
        return item["button"]["onPress"]["Command"]

    ident, alt = k("XPNDR_IDENT_ON"), h("TRANSPONDER_Push_ALT")
    assert command(parts.vfr(), None) == parts.vfr()
    assert command(parts.vfr(), "1200") == parts.vfr("1200")
    assert command(parts.vfr("1200", alt), "7000") == parts.vfr("7000", alt)
    assert command(ident, None) == ident
    for entry in (ident, k("XPNDR_SET", "7000"), parts.vfr() + " " + ident):
        with pytest.raises(ValueError, match="the VFR key of test has no VFR toggle"):
            command(entry, "1200")
    with pytest.raises(ValueError, match="not a squawk code"):
        command(ident, "7800")


def cdi_shows(key, source):
    """The variables by which a Garmin family's CDI shows source ("GPS", 1 or 2): the G3X Touch keeps GPS DRIVES
    NAV1 and AUTOPILOT NAV SELECTED on it, the G1000 NXi L:PFD_CDI_Source (3 for GPS), which it also writes when it
    starts, where AUTOPILOT NAV SELECTED may be stale"""
    if key in G1000:
        return {"L:PFD_CDI_Source": 3 if source == "GPS" else source, "GPS DRIVES NAV1": source == "GPS",
                "AUTOPILOT NAV SELECTED": 2}
    return {"GPS DRIVES NAV1": source == "GPS", "AUTOPILOT NAV SELECTED": 1 if source == "GPS" else source}


@pytest.mark.parametrize("key", [*G1000, "g3x"])
def test_the_fast_crs_step_sets_the_course_the_cdi_shows(key):
    # 10° on the GPS's OBS course, or on the course of the NAV radio the CDI shows, in whole degrees from 0 to 360
    table = FAMILIES[key].DEVICE[1]
    courses = {"GPS OBS VALUE": 355.4, "NAV OBS:1": 5, "NAV OBS:2": 180}
    for radio, up, down in ((1, 15, 355), (2, 190, 170)):
        variables = {**cdi_shows(key, radio), **courses}
        assert run(table["CRS_10_UP"], variables) == [(f"K:VOR{radio}_SET", up)]
        assert run(table["CRS_10_DN"], variables) == [(f"K:VOR{radio}_SET", down)]
    variables = {**cdi_shows(key, "GPS"), **courses}
    assert run(table["CRS_10_UP"], variables) == [("K:GPS_OBS_SET", 5)]
    assert run(table["CRS_10_DN"], variables) == [("K:GPS_OBS_SET", 345)]
    assert table["CRS_1_UP"] != table["CRS_10_UP"] and table["CRS_1_DN"] != table["CRS_10_DN"]


@FAMILY
def test_xpdr_mode_switches_between_standby_and_alt(key):
    # Working Title's G1000 NXi and G3X Touch and the KT 76 of the KAP 140 cockpit keep the transponder's mode in
    # TRANSPONDER STATE:1 (the SDK: 0 off, 1 standby, 2 test, 3 on, 4 ALT, 5 ground): standby or off goes to ALT,
    # any other mode to standby, also the ground mode a G3X Touch may turn ALT into on the ground
    # (TransponderAutoGroundAltManager.ts). Black Square's GTX 327 takes its ALT and STBY keys instead.
    code = FAMILIES[key].DEVICE[1]["XPDR_MODE"]
    alt, standby = ((("H:TRANSPONDER_Push_ALT", None), ("H:TRANSPONDER_Push_STBY", None)) if key == BONANZA
                    else (("A:TRANSPONDER STATE:1", 4), ("A:TRANSPONDER STATE:1", 1)))
    for mode, then in ((0, alt), (1, alt), (2, standby), (3, standby), (4, standby), (5, standby)):
        assert run(code, {"TRANSPONDER STATE:1": mode}) == [then]


@FAMILY
def test_com_1_and_com_2_switch_their_receiver_on_and_off(key):
    # each sets its own receiver to the opposite of what it is, but keeps the one transmitted on (an audio panel
    # always plays it); MIC 1 and MIC 2 transmit on their radio and listen to it
    table = FAMILIES[key].DEVICE[1]
    for radio, other in ((1, 2), (2, 1)):
        for listening in (0, 1):
            for talking in (0, 1):
                variables = {f"COM RECEIVE EX1:{radio}": listening, f"COM RECEIVE EX1:{other}": 1 - listening,
                             f"COM TRANSMIT:{radio}": talking, f"COM TRANSMIT:{other}": 1 - talking}
                assert run(table[f"COM{radio}"], variables) == [
                    (f"K:COM{radio}_RECEIVE_SELECT", bool(not listening or talking))], (radio, listening, talking)
        mic = run(table[f"MIC{radio}"])
        assert (f"K:COM{radio}_RECEIVE_SELECT", 1) in mic and ("K:PILOT_TRANSMITTER_SET", radio - 1) in mic


@FAMILY
def test_the_fast_hdg_step_moves_the_heading_bug(key):
    # 10° from where the bug is, not from the heading flown, in whole degrees from 0 to 360
    table = FAMILIES[key].DEVICE[1]
    variables = {"AUTOPILOT HEADING LOCK DIR:1": 355.4, "HEADING INDICATOR:1": 90}
    assert run(table["HDG_10_UP"], variables) == [("K:HEADING_BUG_SET", 5)]
    assert run(table["HDG_10_DN"], variables) == [("K:HEADING_BUG_SET", 345)]


@FAMILY
def test_the_hdg_push_sets_the_bug_to_the_heading(key):
    # the heading flown, in whole degrees from 0 to 359, half a degree rounded up
    code = FAMILIES[key].DEVICE[1]["HDG_SYNC"]
    for heading, bug in ((359.6, 0), (90.4, 90), (90.5, 91), (0.4, 0)):
        variables = {"HEADING INDICATOR:1": heading, "AUTOPILOT HEADING LOCK DIR:1": 200}
        assert run(code, variables) == [("K:HEADING_BUG_SET", bug)]


@pytest.mark.parametrize("key", BENDIX)
def test_the_fast_crs_step_of_a_bendix_king_cockpit_is_nav_1s(key):
    table = FAMILIES[key].DEVICE[1]
    variables = {"NAV OBS:1": 355, "NAV OBS:2": 90}
    assert run(table["CRS_10_UP"], variables) == [("K:VOR1_SET", 5)]
    assert run(table["CRS_10_DN"], variables) == [("K:VOR1_SET", 345)]


def test_the_g3x_slow_crs_step_is_on_what_the_cdi_shows():
    table = FAMILIES["g3x"].DEVICE[1]
    gps_obs, nav1, nav2 = (("K:GPS_OBS_INC", "K:GPS_OBS_DEC"), ("K:VOR1_OBI_INC", "K:VOR1_OBI_DEC"),
                           ("K:VOR2_OBI_INC", "K:VOR2_OBI_DEC"))
    for gps, radio, (up, down) in ((1, 1, gps_obs), (1, 2, gps_obs), (0, 1, nav1), (0, 2, nav2)):
        variables = {"GPS DRIVES NAV1": gps, "AUTOPILOT NAV SELECTED": radio}
        assert run(table["CRS_1_UP"], variables) == [(up, None)]
        assert run(table["CRS_1_DN"], variables) == [(down, None)]


def test_the_g3x_centres_the_course_of_the_nav_radio_the_cdi_shows():
    # CRS CTR: the localizer's course, or the course to the VOR (its radial + 180°), in whole degrees; nothing on
    # GPS or without a signal (the G1000 NXi takes its CRS push as an H: event)
    code = FAMILIES["g3x"].DEVICE[1]["CRS_CTR"]
    signals = {"NAV HAS LOCALIZER:1": 1, "NAV LOCALIZER:1": 94.6, "NAV HAS NAV:1": 1, "NAV RADIAL:1": 10,
               "NAV HAS LOCALIZER:2": 0, "NAV LOCALIZER:2": 0, "NAV HAS NAV:2": 1, "NAV RADIAL:2": 200.4}

    def centred(gps, radio, **changed):
        return run(code, {"GPS DRIVES NAV1": gps, "AUTOPILOT NAV SELECTED": radio, **signals, **changed})

    assert centred(0, 1) == [("K:VOR1_SET", 95)]
    assert centred(0, 2) == [("K:VOR2_SET", 20)]
    assert centred(0, 2, **{"NAV HAS NAV:2": 0}) == []
    assert centred(1, 1) == centred(1, 2) == []


@pytest.mark.parametrize("key", BENDIX)
def test_crs_ctr_of_a_bendix_king_cockpit_centres_nav_1(key):
    # the course of NAV 1, whose course the knob sets, whatever the CDI shows: the localizer's, or the course to
    # the VOR, in whole degrees; nothing without a signal
    code = FAMILIES[key].DEVICE[1]["CRS_CTR"]
    signals = {"NAV HAS LOCALIZER:1": 0, "NAV LOCALIZER:1": 0, "NAV HAS NAV:1": 1, "NAV RADIAL:1": 200.5}
    assert run(code, signals) == [("K:VOR1_SET", 21)]
    assert run(code, {**signals, "NAV HAS LOCALIZER:1": 1, "NAV LOCALIZER:1": 94.4}) == [("K:VOR1_SET", 94)]
    assert run(code, {**signals, "NAV HAS NAV:1": 0}) == []


def test_the_g1000_cdi_key_cycles_gps_nav_1_and_nav_2():
    # as the NXi's CDI softkey: GPS, NAV 1, NAV 2, GPS, in both units, also with a stale AUTOPILOT NAV SELECTED
    for device in (1, 2):
        code = FAMILIES["g1000"].DEVICE[device]["CDI"]
        for source, then in (("GPS", ("K:AP_NAV_SELECT_SET", 1)), (1, ("K:AP_NAV_SELECT_SET", 2)),
                             (2, ("K:TOGGLE_GPS_DRIVES_NAV1", None))):
            assert run(code, cdi_shows("g1000", source)) == [then]


@pytest.mark.parametrize("key", GARMIN)
def test_the_garmin_fd_key_does_nothing_with_the_autopilot_engaged(key):
    code = FAMILIES[key].DEVICE[1]["FD"]
    assert run(code, {"AUTOPILOT MASTER": 0}) == [("K:TOGGLE_FLIGHT_DIRECTOR", None)]
    assert run(code, {"AUTOPILOT MASTER": 1}) == []


@pytest.mark.parametrize("key", GARMIN)
def test_the_garmin_up_and_dn_step_the_reference_of_the_vertical_mode(key):
    # VS first, then IAS (nose up slows it), then pitch, and nothing in another mode
    table = FAMILIES[key].DEVICE[1]
    modes = ("AUTOPILOT VERTICAL HOLD", "AUTOPILOT FLIGHT LEVEL CHANGE", "AUTOPILOT PITCH HOLD")
    for on, up, down in (((1, 1, 1), "AP_VS_VAR_INC", "AP_VS_VAR_DEC"), ((0, 1, 1), "AP_SPD_VAR_DEC", "AP_SPD_VAR_INC"),
                         ((0, 0, 1), "AP_PITCH_REF_INC_UP", "AP_PITCH_REF_INC_DN"), ((0, 0, 0), None, None)):
        variables = dict(zip(modes, on, strict=True))
        for button, event in (("UP", up), ("S_UP", up), ("DN", down), ("S_DN", down)):
            assert run(table[button], variables) == ([(f"K:{event}", None)] if event else [])


TOGGLED_STD = sorted(key for key in FAMILIES if FAMILIES[key].DEVICE[1]["BARO_STD"] == parts.STD_TOGGLE["BARO_STD"])


def test_std_names_the_altimeter():
    # BAROMETRIC_STD_PRESSURE takes the index of the altimeter (the SDK): the first one; the G3X Touch sends it
    # alone, the Bendix/King cockpits as STD_TOGGLE does (below), the Bonanza to both its altimeters
    # (tests/test_ifr1.py, test_bonanza_baro_steps_and_restores_both_altimeters)
    assert TOGGLED_STD == ["gns", "gtn"]
    assert run(FAMILIES["g3x"].DEVICE[1]["BARO_STD"]) == [("K:BAROMETRIC_STD_PRESSURE", 1)]


@pytest.mark.parametrize("key", TOGGLED_STD)
def test_std_pressed_again_returns_to_the_setting_before(key):
    # from another setting STD keeps it and sets STD; within half a hPa of 1013.2 it sets the setting kept
    # (KOHLSMAN_SET: millibars * 16), once; with none kept it does nothing there
    code = FAMILIES[key].DEVICE[1]["BARO_STD"]
    assert run(code, {"KOHLSMAN SETTING MB:1": 1003.0, "L:AvionicsPanel_Baro": 0}) == [
        ("L:AvionicsPanel_Baro", 1003.0), ("K:BAROMETRIC_STD_PRESSURE", 1)]
    assert run(code, {"KOHLSMAN SETTING MB:1": 1013.25, "L:AvionicsPanel_Baro": 1003.0}) == [
        ("K:KOHLSMAN_SET", 16048), ("L:AvionicsPanel_Baro", 0)]
    assert run(code, {"KOHLSMAN SETTING MB:1": 1013.25, "L:AvionicsPanel_Baro": 0}) == []
    # 29.92 inHg is STD too; a QNH of 1013 hPa, 29.91 or 29.93 inHg is not, so a press there sets STD
    assert run(code, {"KOHLSMAN SETTING MB:1": 1013.21, "L:AvionicsPanel_Baro": 1003.0})[0][0] == "K:KOHLSMAN_SET"
    for qnh in (1013.0, 1012.87, 1013.55, 1020.0):
        assert run(code, {"KOHLSMAN SETTING MB:1": qnh, "L:AvionicsPanel_Baro": 1003.0}) == [
            ("L:AvionicsPanel_Baro", qnh), ("K:BAROMETRIC_STD_PRESSURE", 1)]
    # a turn of the BARO ring forgets the setting kept
    for button, event in (("BARO_UP", "K:KOHLSMAN_INC"), ("BARO_DN", "K:KOHLSMAN_DEC")):
        assert run(FAMILIES[key].DEVICE[1][button]) == [(event, None), ("L:AvionicsPanel_Baro", 0)]


def test_the_da40s_standby_altimeter_follows_the_pfd():
    # the NXi's knob and STD Baro as on the G1000 NXi, then the standby (aircraft.DA40_STANDBY): a detent sets it a
    # step of 0.01 inHg from the PFD's setting, to 0.01 inHg, within the standby's 28 to 31.5, and forgets the setting
    # STD kept; STD keeps the PFD's setting and sets 29.92, on STD sets the setting kept, once
    table, standby, kept = FAMILIES["cows-da40"].DEVICE[1], "L:KOHLSMAN SETTING HG:2", "L:AvionicsPanel_Standby_Baro"
    up, down = ("BARO_UP", "H:AS1000_PFD_BARO_INC"), ("BARO_DN", "H:AS1000_PFD_BARO_DEC")

    def detent(turn, pfd, standby_before, kept_before):
        """The standby a detent sets, with the PFD at pfd inHg (29.92 on STD)"""
        state = {"KOHLSMAN SETTING MB:1": pfd * 33.8639, "KOHLSMAN SETTING HG:1": pfd, standby: standby_before,
                 kept: kept_before}
        sent = run(table[turn[0]], state)
        assert sent[0] == (turn[1], None) and sent[2] == (kept, 0) and len(sent) == 3, sent
        return sent[1][1] if sent[1][0] == standby else sent

    for turn, pfd, want in ((up, 29.951, 29.96), (down, 29.951, 29.94), (up, 30.1249, 30.13), (up, 31.5, 31.5),
                            (down, 28.0, 28.0), (down, 27.5, 28.0)):
        assert detent(turn, pfd, 29.5, 29.5) == want, (turn, pfd)
    # turned back and forth with the NXi stepping 1 hPa, from whole hPa and from other settings, or 0.01 inHg: the
    # standby never moves against the turn and ends within 0.025 inHg of the PFD's setting, the same with the PFD in
    # inHg
    for nxi_step, starts in ((1 / 33.8639, [hpa / 33.8639 for hpa in range(1005, 1013)] + [29.8, 29.805]),
                             (0.01, (29.8, 30.12))):
        for start in starts:
            pfd, settled = start, round(start, 2)
            for sign in (1, 1, -1, 1, -1, -1, -1, 1, 1, 1, -1, 1, -1, -1):
                now = detent(up if sign > 0 else down, pfd, settled, 0)
                pfd += sign * nxi_step
                assert (now - settled) * sign >= 0 and abs(now - pfd) < 0.025, (nxi_step, start, now, pfd)
                assert nxi_step > 0.01 or abs(now - pfd) < 1e-6
                settled = now
    # a standby 0.01 to 0.03 inHg ahead of the PFD's setting in the turn's direction stays (0.01: the step's own),
    # one further off or behind takes the step from the PFD's
    for turn, standby_before, want in ((up, 29.91, 29.91), (up, 29.92, 29.92), (up, 29.93, 29.93),
                                       (up, 29.94, 29.91), (up, 29.88, 29.91), (down, 29.89, 29.89),
                                       (down, 29.88, 29.88), (down, 29.87, 29.87), (down, 29.86, 29.89),
                                       (down, 29.92, 29.89)):
        assert detent(turn, 29.90, standby_before, 0) == want, (turn, standby_before)
    # with the PFD in inHg, a standby off by up to 0.03 inHg (a STD push that missed STD Baro, its own knob) meets the
    # PFD within three detents either way without moving against the turn, and stays on it
    for turn, sign in ((up, 1), (down, -1)):
        for gap in (-3, -2, -1, 1, 2, 3, 5):
            pfd, settled = 29.90, round(29.90 + gap / 100, 2)
            for n in range(6):
                now = detent(turn, pfd, settled, 0)
                pfd = round(pfd + sign / 100, 2)
                assert (now - settled) * sign >= 0 or abs(gap) > 3, (turn, gap, n, now)
                assert n < 3 or abs(now - pfd) < 1e-6, (turn, gap, n, now, pfd)
                settled = now
    # on STD, from the setting the NXi leaves STD for: the one kept while the standby reads the panel's 29.92, else
    # the standby's own (STD from the cockpit; a QNH of 29.92)
    assert detent(up, 29.92, 29.92, 29.62) == 29.63
    assert detent(down, 29.92, 29.92, 29.62) == 29.61
    assert detent(up, 29.92, 30.12, 0) == 30.13
    assert detent(up, 29.92, 30.12, 29.62) == 30.13
    assert detent(down, 29.92, 29.92, 0) == 29.91
    softkeys = [("H:AS1000_PFD_SOFTKEYS_4", None), ("H:AS1000_PFD_SOFTKEYS_10", None)]
    assert run(table["BARO_STD"], {"KOHLSMAN SETTING MB:1": 1003.0, "KOHLSMAN SETTING HG:1": 29.6189, kept: 0}) == [
        *softkeys, (kept, 29.62), (standby, 29.92)]
    assert run(table["BARO_STD"], {"KOHLSMAN SETTING MB:1": 1013.21, kept: 29.62}) == [
        *softkeys, (standby, 29.62), (kept, 0)]
    assert run(table["BARO_STD"], {"KOHLSMAN SETTING MB:1": 1013.21, kept: 31.75}) == [
        *softkeys, (standby, 31.5), (kept, 0)]
    assert run(table["BARO_STD"], {"KOHLSMAN SETTING MB:1": 1013.25, kept: 0}) == softkeys


def test_the_kfc_150_rocker_steps_the_reference_of_the_mode():
    # the altitude held in ALT, else the rate in VS, else the pitch, and nothing in another mode
    table = FAMILIES[BONANZA].DEVICE[1]
    modes = ("AUTOPILOT ALTITUDE LOCK", "AUTOPILOT VERTICAL HOLD", "AUTOPILOT PITCH HOLD")
    for on, up, down in (((1, 1, 1), ("AP_ALT_VAR_INC", 100), ("AP_ALT_VAR_DEC", 100)),
                         ((0, 1, 1), ("AP_VS_VAR_INC", None), ("AP_VS_VAR_DEC", None)),
                         ((0, 0, 1), ("AP_PITCH_REF_INC_UP", None), ("AP_PITCH_REF_INC_DN", None)),
                         ((0, 0, 0), None, None)):
        variables = dict(zip(modes, on, strict=True))
        for button, sent in (("UP", up), ("DN", down)):
            assert run(table[button], variables) == ([(f"K:{sent[0]}", sent[1])] if sent else [])


# VNV's descent calculator in the autopilots without VNAV: by table, what enters VS (the KAP 140's event, before the
# rate; the KAS 297B's VS ENG key, after it) and the flags of the autopilot engaged in ALT hold, where it enters VS,
# in VS, where it does not, and off, where the KFC 150's VS ENG would set the flight director's mode and the KAP 140
# is in no ALT hold to leave
_AP = {"AUTOPILOT MASTER": 1, "AUTOPILOT PITCH HOLD": 0, "AUTOPILOT GLIDESLOPE ACTIVE": 0}
_OFF = {"AUTOPILOT MASTER": 0, "AUTOPILOT ALTITUDE LOCK": 0, "AUTOPILOT VERTICAL HOLD": 0, "AUTOPILOT PITCH HOLD": 0,
        "AUTOPILOT GLIDESLOPE ACTIVE": 0}
_IN_ALT = {**_AP, "AUTOPILOT ALTITUDE LOCK": 1, "AUTOPILOT VERTICAL HOLD": 0}
_IN_VS = {**_AP, "AUTOPILOT ALTITUDE LOCK": 0, "AUTOPILOT VERTICAL HOLD": 1}
KAP140_VS = (("K:AP_PANEL_VS_ON", 0), "before")
KFC150_VS = (("H:kas297b_VsButton", None), "after")
VNV = {"gns": KAP140_VS, "gtn": KAP140_VS, "carenado-c182t": KAP140_VS, "autopilot-kap140": KAP140_VS,
       BONANZA: KFC150_VS, "autopilot-kfc150": KFC150_VS}


NOW = 1000                     # the sim's clock in flight() (E:SIMULATION TIME, seconds)


def followed(rate):
    """What VNV keeps after setting a rate, for its recalculation (parts.follow): the rate, that it follows, and
    when it next works the rate out"""
    return [(f"L:{parts.VNV_RATE}", rate), (f"L:{parts.VNV_ACTIVE}", 1),
            (f"L:{parts.VNV_NEXT}", NOW + parts.VNV_INTERVAL)]


def vnv_sends(key, rate, engages=True):
    """What VNV or SHIFT, VNV sends in this table for a rate (None: nothing), entering VS or not"""
    if rate is None:
        return []
    (engage, where), set_vs = VNV[key], ("K:AP_VS_VAR_SET_ENGLISH", rate)
    if not engages:
        return [set_vs, *followed(rate)]
    return [*([engage, set_vs] if where == "before" else [set_vs, engage]), *followed(rate)]


def flight(altitude=8000, selected=4000, speed=120, tds=0, gps=0, ias=140, **more):
    """The variables VNV and SHIFT, VNV read: the altimeter's and the selected altitude (ft), the ground speed (kt),
    TDS's GTNXi's and the GPS's distance to the active waypoint (nm), the indicated airspeed (kt) against a stall
    speed of 60 kt and a Vne of 200 kt, the sim's clock, and more of them by name"""
    return {"INDICATED ALTITUDE": altitude, "AUTOPILOT ALTITUDE LOCK VAR:1": selected, "GROUND VELOCITY": speed,
            "L:TDSGTNXI_NextWaypointDistanceNM": tds, "GPS WP DISTANCE": gps, "L:var_rnavDrivesHsi": 0,
            "L:var_RNAV_DME": 0, "L:WTAP_VNAV_Required_VS": 0, "AIRSPEED INDICATED": ias, "DESIGN SPEED VS1": 60,
            "AIRSPEED BARBER POLE": 200, "E:SIMULATION TIME": NOW, **more}


def vnv(entry):
    """VNV's code as pressed (it sets the rate again as it is let go: test_vnv_sets_its_rate_again_...)"""
    return entry["press"] if isinstance(entry, dict) else entry


def text(entry):
    """an entry's codes, every event's, as one text"""
    return " ".join(profile.actions(entry).values())


@pytest.mark.parametrize("key", sorted(VNV))
def test_vnv_sets_the_rate_to_the_selected_altitude_at_the_waypoint(key):
    # (selected - altitude) / (distance / ground speed in minutes), rounded to 100 ft/min and kept between 300 and
    # 1500 ft/min down or 2000 ft/min up; VS entered unless it is on; nothing without a distance, at 30 knots or less,
    # within 100 ft of the selected altitude, in a climb below 1.3 times the stall speed (78 kt here) or in a
    # descent at 95 % of Vne (190 kt here) or faster
    code = vnv(TABLES[key].DEVICE[1]["VNV"])
    for case, rate in ((flight(gps=20), -400),                                    # 4000 ft in 10 min
                       (flight(9000, 4000, 140, gps=20), -600),                    # 583 ft/min, rounded
                       (flight(gps=5), -1500),                                     # 3000 ft/min, clamped
                       (flight(5000, 4000, 100, gps=20), -300),                    # 83 ft/min, clamped
                       (flight(3000, 7500, gps=10), 900),                          # a climb: 4500 ft in 5 min
                       (flight(3000, 9000, gps=5), 2000),                          # 2400 ft/min up, clamped
                       (flight(3000, 7500, gps=10, ias=77), None),                 # too slow to climb
                       (flight(3000, 7500, gps=10, ias=79), 900),
                       (flight(gps=20, ias=191), None),                            # too fast to descend
                       (flight(gps=20, ias=189), -400),
                       (flight(gps=20, ias=191, **{"AIRSPEED BARBER POLE": 0}), -400),   # no Vne given: no guard
                       (flight(3000, 3500, 100, gps=20), 300),                     # 42 ft/min up, clamped
                       (flight(), None),                                           # no distance
                       (flight(gps=-1), None),
                       (flight(speed=30, gps=20), None),                           # too slow
                       (flight(speed=0, gps=20), None),
                       (flight(4080, 4000, gps=20), None),                         # at the selected altitude
                       (flight(3920, 4000, gps=20), None),
                       (flight(4000, 4000, gps=20), None)):
        assert run(code, {**case, **_IN_ALT}) == vnv_sends(key, rate), (case, rate)
        assert run(code, {**case, **_IN_VS}) == vnv_sends(key, rate, False), (case, rate)   # VS is on: the rate
        assert run(code, {**case, **_OFF}) == vnv_sends(key, rate, False), (case, rate)     # off: the rate alone
        if VNV[key] == KFC150_VS:                                             # in pitch mode: VS ENG
            pitch = {**_AP, "AUTOPILOT ALTITUDE LOCK": 0, "AUTOPILOT VERTICAL HOLD": 0, "AUTOPILOT PITCH HOLD": 1}
            assert run(code, {**case, **pitch}) == vnv_sends(key, rate), (case, rate)
            glideslope = {**pitch, "AUTOPILOT GLIDESLOPE ACTIVE": 1}               # on a glideslope: not
            assert run(code, {**case, **glideslope}) == vnv_sends(key, rate, False), (case, rate)


@pytest.mark.parametrize("key", sorted(VNV))
def test_vnv_takes_the_first_distance_above_0(key):
    # TDS's GTNXi's where a TDS GTN is fitted (or the autopilot part alone does not know), then the GPS's (Working
    # Title's GNS and G1000 NXi write it); in the Bonanza first the KNS 81's RNAV distance, while the HSI shows RNAV
    code = vnv(TABLES[key].DEVICE[1]["VNV"])

    def rate(**case):
        return [v for name, v in run(code, flight(**case, **_IN_VS)) if name == "K:AP_VS_VAR_SET_ENGLISH"]
    if key in ("gns", "carenado-c182t"):                    # the GPS alone: a TDS variable there is left over
        assert rate(tds=20, gps=40) == [-300] and rate(tds=20) == []
        return
    assert rate(tds=20, gps=40) == [-400]
    assert rate(tds=0, gps=40) == [-300]                    # 4000 ft in 20 min, clamped to 300
    assert rate(tds=-1, gps=10) == [-800]
    rnav = {"L:var_rnavDrivesHsi": 1, "L:var_RNAV_DME": 10}
    assert rate(tds=20, **rnav) == ([-800] if key == BONANZA else [-400])   # the Bonanza's own KNS 81
    assert rate(tds=20, **{**rnav, "L:var_rnavDrivesHsi": 0}) == [-400]


@pytest.mark.parametrize("key", sorted(k for k, (engage, _) in VNV.items() if engage == KAP140_VS))
def test_vnv_sets_its_rate_again_as_it_is_let_go(key):
    # behind WT's G1000 NXi or GNS VS comes a frame after AP_PANEL_VS_ON and takes the present vertical speed: the
    # KAP 140's release sets the rate again, without entering VS a second time
    entry = TABLES[key].DEVICE[1]["VNV"]
    assert set(entry) == {"press", "release"}
    assert entry == TABLES[key].DEVICE[1]["S_VNV"]
    released = run(entry["release"], {**flight(gps=20, tds=20), **_IN_VS})
    assert released == [("K:AP_VS_VAR_SET_ENGLISH", -400), *followed(-400)]
    assert VNV[key][0][0][2:] not in entry["release"]
    assert ("K:AP_VS_VAR_SET_ENGLISH", -400) in run(entry["press"], {**flight(gps=20, tds=20), **_IN_ALT})


@pytest.mark.parametrize("key", [BONANZA, "autopilot-kfc150"])
def test_the_kfc150s_vnv_sends_on_press_alone(key):
    # the rate, then VS ENG, once: the rate set again on release, while VS ENG takes it, stopped VNV working
    entry = TABLES[key].DEVICE[1]["VNV"]
    assert isinstance(entry, str) and "if{ (>H:kas297b_VsButton) }" in entry


def test_vnv_reads_the_distances_of_the_navigators_it_is_composed_with():
    # unit 1's first (a GNS's, PMS50's GTN's and the NXi's: the GPS's; a TDS GTN's: TDS's), then unit 2's, then the
    # GPS's if neither gave it; none adds nothing
    def reads(unit1, unit2):
        family = part.compose("x", AUTOPILOTS["kap140"], COCKPITS["bendix-king"], *navigators(unit1, unit2))
        code = vnv(family.DEVICE[1]["VNV"])
        return sorted((d for d in ("TDSGTNXI", "GPS WP DISTANCE") if d in code), key=code.index)
    assert reads("gns530", "gtn650-tds2") == ["GPS WP DISTANCE", "TDSGTNXI"]
    assert reads("gtn750-tds1", "gns430") == reads("gtn750-tds1", "none") == ["TDSGTNXI", "GPS WP DISTANCE"]
    assert reads("gtn750-pms50", "none") == reads("gns530", "gns430") == reads("none", "none") == ["GPS WP DISTANCE"]
    assert "TDSGTNXI" in text(AUTOPILOTS["kap140"].DEVICE[1]["VNV"])      # alone: it cannot know
    # the NXi's required vertical speed, with its navigator whatever the profile; the KFC 150 without the KNS 81
    nxi = part.compose("x", AUTOPILOTS["kap140"], COCKPITS["g1000"], NAVIGATORS["g1000"]).DEVICE[1]["VNV"]
    assert nxi == FAMILIES["carenado-c182t"].DEVICE[1]["VNV"] and "WTAP_VNAV_Required_VS" in text(nxi)
    assert not any("WTAP" in text(p.DEVICE[1].get("VNV", "")) for p in AUTOPILOTS.values())
    assert "RNAV" not in text(AUTOPILOTS["kfc150"].DEVICE[1]["VNV"])
    assert "RNAV" in text(FAMILIES[BONANZA].DEVICE[1]["VNV"])


def test_an_autopilot_part_alone_reads_every_navigators_distance():
    # the parts zip's kap140 and kfc150 cannot know the navigator: every distance a navigator gives, then the GPS's
    declared = {d for make in UNIT_NAVIGATORS.values() for unit in (1, 2) for d in make(unit).DISTANCES}
    declared |= {d for p in NAVIGATORS.values() for d in p.DISTANCES}
    assert set(ALONE_DISTANCES) == declared and ALONE_DISTANCES[-1] == part.GPS_DISTANCE
    assert len(ALONE_DISTANCES) == len(declared) > 1
    for key, vnv, built in (("kap140", parts.KAP140_VNV, parts.KAP140_AUTOPILOT),
                            ("kfc150", KFC150_VNV, bksq.AUTOPILOT)):
        assert AUTOPILOTS[key].DEVICE[1]["VNV"] == vnv(distances=ALONE_DISTANCES), key
        assert PARTS[f"autopilot-{key}"].DEVICE[1]["S_VNV"] == PARTS[f"autopilot-{key}"].DEVICE[1]["VNV"], key
        # a copy (part.alone): the part as built keeps its VNV's defaults, which compose() replaces in turn
        assert built.DEVICE[1]["VNV"] == built.DEVICE[1]["S_VNV"] == vnv(), key
    assert {k for k, p in AUTOPILOTS.items() if p.VNV} == {"kap140", "kfc150"}


def test_gps_last_keeps_each_read_once_and_the_gps_distance_last():
    # as joined() and the parts alone order theirs; one without the GPS's gets none
    gps, tds = part.GPS_DISTANCE, gtn.TDS_DISTANCE
    assert part.gps_last([gps, tds, gps, "x", tds]) == (tds, "x", gps)
    assert part.gps_last([tds, "x"]) == (tds, "x") and part.gps_last([]) == ()


FOLLOWING = {f"L:{parts.VNV_ACTIVE}": 1, f"L:{parts.VNV_RATE}": -400, f"L:{parts.VNV_NEXT}": NOW + 30,
             "AUTOPILOT VERTICAL HOLD": 1, "AUTOPILOT VERTICAL HOLD VAR:1": -400, "AUTOPILOT MASTER": 1}


def test_a_codes_name_leaves_out_vnvs_bookkeeping():
    # the card's VNV line, and MobiFlight's item name, list what a pilot recognises: VNV's own variables made the
    # Bonanza's card spill onto a second page
    assert profile.label(FAMILIES[BONANZA].DEVICE[1]["VNV"]) == "AP_VS_VAR_SET_ENGLISH, kas297b_VsButton"
    assert not any(name in profile.label(parts.follow()[1]) for name in profile.UNNAMED)


def test_vnvs_recalculation_codes_are_well_formed_and_fit():
    # each of the two codes alone in MobiFlight's message, leaving the stack empty down every path (the light's read
    # comes after it)
    for args in ({"distances": (part.GPS_DISTANCE,), "required": None}, FAMILIES[BONANZA].VNV_ARGS,
                 FAMILIES["carenado-c182t"].VNV_ARGS):
        for code in parts.follow(**args):
            well_formed(code)
            every_path(code)


def test_vnvs_recalculation_watches_the_rate_and_the_speed_guards():
    watch, _ = parts.follow()
    stop = (f"L:{parts.VNV_ACTIVE}", 0)

    def watched(**changes):
        return run(watch, {**flight(gps=20), **FOLLOWING, **changes})
    assert watched() == []                                              # within 5 s of setting the rate: not yet
    late = {"E:SIMULATION TIME": NOW + 6}
    assert watched(**late) == []                                        # VS holds the rate set
    assert watched(**late, **{"AUTOPILOT VERTICAL HOLD": 0}) == [stop]   # VS ended (captured, another mode)
    assert watched(**late, **{"AUTOPILOT MASTER": 0}) == [stop]          # the autopilot off, its VS flag left on
    assert watched(**{"E:SIMULATION TIME": NOW - 3600}) == [stop]           # the sim's clock gone back: no stale VNV
    assert watched(**late, **{"AUTOPILOT VERTICAL HOLD VAR:1": -700}) == [stop]      # the rate changed by hand
    assert watched(**late, **{"AUTOPILOT VERTICAL HOLD VAR:1": -430}) == []          # within 50 ft/min: the same
    descent_fast = {**late, "AIRSPEED INDICATED": 195}
    assert watched(**descent_fast) == [("K:AP_VS_VAR_SET_ENGLISH", -300), stop]      # at 95 % of Vne: ease, stop
    climb = {**late, f"L:{parts.VNV_RATE}": 900, "AUTOPILOT VERTICAL HOLD VAR:1": 900}
    assert watched(**climb) == []
    assert watched(**climb, **{"AIRSPEED INDICATED": 75}) == [("K:AP_VS_VAR_SET_ENGLISH", 0), stop]   # level off
    assert watched(**climb, **{"AIRSPEED INDICATED": 195}) == []        # fast in a climb: fine
    assert watched(**late, **{f"L:{parts.VNV_ACTIVE}": 0, "AUTOPILOT VERTICAL HOLD": 0}) == []   # not following


def test_vnvs_recalculation_works_the_rate_out_every_30_seconds():
    _, update = parts.follow()

    def updated(**changes):
        return run(update, {**flight(gps=20), **FOLLOWING, **changes})
    assert updated(**{"E:SIMULATION TIME": NOW + 29}) == []                 # not due yet
    due = NOW + 31
    later = flight(7000, 4000, 120, gps=5)                              # 3000 ft in 2.5 min: 1200 ft/min
    assert run(update, {**later, **FOLLOWING, "E:SIMULATION TIME": due}) == [
        ("K:AP_VS_VAR_SET_ENGLISH", -1200), (f"L:{parts.VNV_RATE}", -1200),
        (f"L:{parts.VNV_NEXT}", due + parts.VNV_INTERVAL)]
    # where the new rate may not be flown: 300 ft/min toward the selected altitude, then stop
    stop = (f"L:{parts.VNV_ACTIVE}", 0)
    for case, eased in ((flight(4050, 4000, gps=5), -300),             # 100 ft or less to go
                        (flight(gps=0), -300),                          # no distance any more (waypoint passed)
                        (flight(gps=20, ias=195), -300),                # a descent at 95 % of Vne
                        (flight(3000, 7500, gps=10, ias=70), 0)):       # a climb too slow: level off
        assert run(update, {**case, **FOLLOWING, "E:SIMULATION TIME": due}) == [
            stop, ("K:AP_VS_VAR_SET_ENGLISH", eased), (f"L:{parts.VNV_RATE}", eased),
            (f"L:{parts.VNV_NEXT}", due + parts.VNV_INTERVAL)], case
    assert updated(**{"E:SIMULATION TIME": due, f"L:{parts.VNV_ACTIVE}": 0}) == []
    # a stale VNV (another flight, or the panel's project alone) sends nothing with VS not flown; watch stops it
    assert updated(**{"E:SIMULATION TIME": due, "AUTOPILOT MASTER": 0, "AUTOPILOT VERTICAL HOLD": 0}) == []
    assert updated(**{"E:SIMULATION TIME": due, "AUTOPILOT VERTICAL HOLD": 0}) == []


def test_the_c182t_vnv_takes_the_g1000_nxis_required_rate_first():
    # the NXi's VSR, rounded and clamped, when it descends at 300 ft/min or more; else the calculation, also for a
    # climb, where a VSR (a descent) does not apply
    code = vnv(FAMILIES["carenado-c182t"].DEVICE[1]["VNV"])
    for vsr, case, rate in ((-650, flight(gps=20), -700), (-650, flight(), -700), (-2000, flight(), -1500),
                            (-300, flight(gps=20), -300), (-300, flight(), -300),
                            (-20, flight(gps=20), -400), (-250, flight(gps=20), -400),   # a constraint far ahead
                            (-20, flight(), None),
                            (650, flight(gps=20), -400),             # a climb: the calculation
                            (650, flight(), None), (0, flight(gps=20), -400), (900, flight(3000, 7500), None),
                            (-650, flight(3950, 4000, gps=20), None), (-650, flight(3000, 4000, gps=20), 300)):
        sent = [("K:AP_VS_VAR_SET_ENGLISH", rate), *followed(rate)] if rate else []
        assert run(code, {**case, **_IN_VS, "L:WTAP_VNAV_Required_VS": vsr}) == sent, (vsr, case)
    # the KAP 140 part, as in the GNS and GTN profiles, has no VSR
    assert "WTAP" not in text(FAMILIES["gns"].DEVICE[1]["VNV"]) + text(PARTS["autopilot-kap140"].DEVICE[1]["VNV"])


@pytest.mark.parametrize("key", sorted(set(VNV) - {BONANZA}))
def test_shift_vnv_is_vnv(key):
    # VNV has no amber legend: a stray SHIFT changes nothing (controls.md), also in a profile joined from the parts
    assert TABLES[key].DEVICE[1]["S_VNV"] == TABLES[key].DEVICE[1]["VNV"]
    joined = part.compose("x", AUTOPILOTS["kap140"], COCKPITS["bendix-king"], *navigators("gtn750-tds1", "gns430"))
    assert joined.DEVICE[1]["S_VNV"] == joined.DEVICE[1]["VNV"]


def test_the_bonanza_keeps_shift_vnv_for_the_kr_87s_bfo():
    assert FAMILIES[BONANZA].DEVICE[1]["S_VNV"] == h("adf_bfo")


# the dimmers of the aircraft that know theirs: each ring's first variable (as read), what it sets alike and the
# switches on above 0; the cabin light push's first light (as read), what it sets and the value of "on"
DIMMERS = {
    BONANZA: {"PANEL_LT": ("L:var_FlightInstrumentsLightingKnob", ("L:var_FlightInstrumentsLightingKnob",
                           "L:var_EngineInstrumentsLightingKnob", "L:var_SubpanelLightingKnob"),
                           ("L:bksq_MasterPanelLights",)),
              "FLOOD_LT": ("L:var_GlareshieldLightingKnob", ("L:var_GlareshieldLightingKnob",),
                           ("L:bksq_MasterGlareshieldLights", "L:OatMapCompassLightButton_1",
                            "L:var_OatMapCompassLightButton_1"))},
    "cows-da40": {"PANEL_LT": ("B:LIGHTING_PANEL_1", ("B:LIGHTING_PANEL_1_Set",), ()),
                  "FLOOD_LT": ("B:LIGHTING_GLARESHIELD_1", ("B:LIGHTING_GLARESHIELD_1_Set",), ())},
    "carenado-c182t": {"PANEL_LT": ("B:LIGHTING_POTENTIOMETER_3", ("B:LIGHTING_POTENTIOMETER_3_Set",
                                    "B:LIGHTING_PANEL_1_Set", "B:LIGHTING_PEDESTRAL_1_Set",
                                    "B:LIGHTING_POTENTIOMETER_4_Set"), ()),
                       "FLOOD_LT": ("B:LIGHTING_CABIN_1", ("B:LIGHTING_CABIN_1_Set", "B:LIGHTING_CABIN_2_Set"), ())},
}
CABIN = {
    BONANZA: ("L:var_LIGHTING_Push_Cockpit_1", (*(f"L:var_LIGHTING_Push_Cockpit_{n}" for n in range(1, 7)),
                                                 "L:OatMapCompassLightButton_2",
                                                 "L:var_OatMapCompassLightButton_2"), 1),
    "cows-da40": ("B:LIGHTING_CABIN_1", tuple(f"B:LIGHTING_CABIN_{n}_Set" for n in (1, 2, 3)), 1),
    "carenado-c182t": ("B:LIGHTING_CABIN_1", ("B:LIGHTING_CABIN_1_Set", "B:LIGHTING_CABIN_2_Set"), 100),
}


@pytest.mark.parametrize("key", sorted(DIMMERS))
def test_the_dimmers_step_5_from_0_to_100_and_switch_their_lights(key):
    table = FAMILIES[key].DEVICE[1]
    for button, (read, writes, switches) in DIMMERS[key].items():
        for value, up, down in ((50, 55, 45), (98, 100, 93), (3, 8, 0), (100, 100, 95), (0, 5, 0)):
            for way, then in (("UP", up), ("DN", down)):
                assert run(table[f"{button}_{way}"], {read: value}) == [
                    *((w, then) for w in writes), *((s, then > 0) for s in switches)], (button, way, value)


@pytest.mark.parametrize("key", sorted(CABIN))
def test_the_cabin_light_push_turns_the_cabin_lights_on_or_off(key):
    read, writes, on = CABIN[key]
    for was, then in ((0, on), (on, 0), (30, 0)):
        assert run(FAMILIES[key].DEVICE[1]["CABIN_LT"], {read: was}) == [(w, then) for w in writes], was


def test_the_bonanza_switches_step_and_toggle():
    # the DME's selector one position on and round, the HSI's source toggled, the EDM 800's
    # buttons by tap and hold, and TEST with the MD41's test held
    table = FAMILIES[BONANZA].DEVICE[1]
    assert [run(table["LVL"], {"L:var_dmeMode": n}) for n in (0, 3, 4)] == [[("L:var_dmeMode", n)] for n in (1, 4, 0)]
    for on in (0, 1):
        assert run(table["GPSS"], {"L:var_rnavDrivesHsi": on}) == [("L:var_rnavDrivesHsi", not on)]
    assert table["S_UP"] == {"release": "(>H:bksq_JpiButton_1_L_Short)", "long": "(>H:bksq_JpiButton_1_L_Long)"}
    assert table["S_DN"] == {"release": "(>H:bksq_JpiButton_1_R_Short)", "long": "(>H:bksq_JpiButton_1_R_Long)"}
    assert run(table["TEST"]["press"], {"AUTOPILOT MASTER": 0}) == [("L:var_AutopilotStartupCounter", 20),
                                                                    ("L:var_md41Test", 1)]
    # engaged: the lamp test alone, and FD nothing (the KFC 150 keeps its flight director)
    assert run(table["TEST"]["press"], {"AUTOPILOT MASTER": 1}) == [("L:var_md41Test", 1)]
    assert run(table["FD"], {"AUTOPILOT MASTER": 1}) == []
    assert run(table["FD"], {"AUTOPILOT MASTER": 0}) == [("K:TOGGLE_FLIGHT_DIRECTOR", None)]


def test_the_g1000_std_push_toggles_std():
    # the PFD's PFD Opt and STD Baro softkeys, whatever the setting, which toggle STD and restore the setting before
    # it; never BAROMETRIC_STD_PRESSURE, which the NXi passes on to the sim, which sets 29.92 before the NXi keeps it
    code = FAMILIES["g1000"].DEVICE[1]["BARO_STD"]
    assert run(code) == [("H:AS1000_PFD_SOFTKEYS_4", None), ("H:AS1000_PFD_SOFTKEYS_10", None)]
    assert "BAROMETRIC_STD_PRESSURE" not in code


def test_the_g1000_home_key_toggles_the_engine_menu():
    # ENGINE (the MFD's first softkey), then BACK (its 11th), in both units, by the profile's own L: variable
    for device in (1, 2):
        code = FAMILIES["g1000"].DEVICE[device]["HOME"]
        assert run(code, {"L:AvionicsPanel_G1000_Engine": 0}) == [("H:AS1000_MFD_SOFTKEYS_1", None),
                                                                 ("L:AvionicsPanel_G1000_Engine", 1)]
        assert run(code, {"L:AvionicsPanel_G1000_Engine": 1}) == [("H:AS1000_MFD_SOFTKEYS_11", None),
                                                                 ("L:AvionicsPanel_G1000_Engine", 0)]


def test_actions_take_a_press_a_release_or_both():
    assert profile.actions("a") == {"onPress": "a"}
    assert profile.actions({"press": "a", "release": "b"}) == {"onPress": "a", "onRelease": "b"}
    assert profile.actions({"release": "b"}) == {"onRelease": "b"}
    assert profile.actions({"release": "b", "long": "c"}) == {"onRelease": "b", "onLongRelease": "c"}
    assert profile.actions({"hold": "a"}) == {"onHold": "a"}
    for bad in ({}, {"repeat": "a"}):
        with pytest.raises(ValueError):
            profile.actions(bad)


# ---------------- the docs' lists of what does nothing ----------------
# the controls as the docs name them in those lists, by their buttons; a button's copy with SHIFT (S_VS, S_ENT,
# S_PTR and so on) goes with it, unless the name is followed by "without SHIFT"
DOC_NAMES = {
    **{name: (name,) for name in ("TEST", "ARM", "GPSS", "BC", "FD", "YD", "VS", "FLC", "VNV", "LVL", "HOME", "CDI",
                                  "OBS", "FPL", "MENU", "PROC", "CLR", "ENT", "MSG", "NRST", "TERR", "VNAV", "MAP",
                                  "PTR")},
    "½ BANK": ("HALF_BANK",),
    "RANGE": ("RANGE_CW", "RANGE_CCW"),
    "the map's pan": ("PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT"),
    "the FREQ push": ("FREQ_PUSH",),
    "the dimmers": ("PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN"),
    "the flood dimmer": ("FLOOD_LT_UP", "FLOOD_LT_DN"),
    "the RANGE knob tilted left or right": ("PAN_LEFT", "PAN_RIGHT"),
}
SECTIONS = {"g1000": "G1000 NXi", "g3x": "GFC 500 and G3X Touch", "gns": "GNS 530/430",
            "gtn": "TDS GTN 750Xi and 650Xi", BONANZA: "Black Square Bonanza", "cows-da40": "COWS DA40",
            "carenado-c182t": "Carenado C182T"}


def doc(name):
    """A page of docs/using/ with its lines joined"""
    with open(os.path.join(ROOT, "docs", "using", name), encoding="utf-8") as f:
        return " ".join(f.read().split())


def listed(text, device):
    """[button] of this device a list names, in its order: its controls, apart, and without the reasons in
    parentheses; one named "in unit 2" counts on device 2 only, and one "without SHIFT" without its shifted
    copy"""
    out = []
    for item in re.split(r",\s*|\s+and\s+", re.sub(r"\s*\([^()]*\)", "", text)):
        name = item.removesuffix(" in unit 2")
        plain = name.removesuffix(" without SHIFT")       # without its copy with SHIFT
        assert plain in DOC_NAMES, item
        if name == item or device == 2:
            shifts = ("",) if plain != name else ("", "S_")
            out += [b for button in DOC_NAMES[plain] for b in (s + button for s in shifts) if b in BM.DEVICE[device]]
    return out


def once(buttons):
    """The buttons as a set, none named twice"""
    assert len(set(buttons)) == len(buttons), sorted(b for b in buttons if buttons.count(b) > 1)
    return set(buttons)


@FAMILY
def test_mapping_md_lists_what_does_nothing(key):
    # "Does nothing in every profile" and the family's "Does nothing in this profile" name its unmapped buttons,
    # each once
    text = doc("mapping.md")
    [every] = re.findall(r"Does nothing in every profile: (.+?)\. ", text)
    [section] = [s for s in text.split("### ") if s.startswith(SECTIONS[key] + " ")]
    [own] = re.findall(r"Does nothing in this profile: (.+?)\.(?: |$)", section.split(" ## ")[0])
    for device in (1, 2):
        assert once(listed(every, device) + listed(own, device)) == set(FAMILIES[key].UNMAPPED[device]), device


@pytest.mark.parametrize("key, unit", [("gtn", "GTN"), ("g3x", "G3X Touch")])
def test_compatibility_md_lists_the_touchscreen_functions(key, unit):
    # what does nothing with a GTN or G3X Touch is what the family has on the touchscreen only, and it is unmapped
    [text] = re.findall(rf"these controls do nothing with an? {unit}: (.+?)\. ", doc("compatibility.md"))
    for device in (1, 2):
        touch = set(FAMILIES[key].TOUCHSCREEN) & set(BM.DEVICE[device])
        assert once(listed(text, device)) == touch and touch <= set(FAMILIES[key].UNMAPPED[device]), device


# ---------------- the project ----------------
ITEM = ("GUID", "Active", "Name", "Type", "Controller", "Device", "button")
BUTTON = ("onPress", "onRelease", "onLongRelease", "onHold", "LongReleaseDelay", "HoldDelay", "RepeatDelay")


@TABLE
def test_the_project_has_the_structure_mobiflight_reads(key):
    # MobiFlight 11.3.1: Project (Name, Sim, Features, Aircraft, ConfigFiles, "_version" 0.10), an embedded
    # ConfigFile, InputConfigItem with Controller {Name, Serial} and Device {Type Button, Name "Button N"},
    # ButtonInputConfig, MSFS2020CustomInputAction {Command} with the table's code; a part's project as a profile's
    table = TABLES[key]
    project = json.loads(profile.dumps(profile.build(table, PANEL)))
    assert tuple(project) == ("Name", "Sim", "Features", "Aircraft", "ConfigFiles", "_version")
    assert project["_version"] == "0.10" and project["Sim"] == "msfs" and project["Aircraft"] == []
    assert project["Features"] == {"FSUIPC": False, "ProSim": False}
    [config_file] = project["ConfigFiles"]
    label = f"Avionics Panel: {table.TITLE}" if hasattr(table, "KIND") else "Avionics Panel"   # a part: its tab
    assert {k: v for k, v in config_file.items() if k != "ConfigItems"} == {
        "Label": label, "FileName": None, "ReferenceOnly": False, "EmbedContent": True}
    serials = {serial: device for device, (_, serial) in PANEL.items()}
    numbers = {(device, BM.BUTTON[device][name] + 1): name for device in (1, 2) for name in BM.DEVICE[device]}
    seen = set()
    for item in config_file["ConfigItems"]:
        assert tuple(item) == ITEM and item["Type"] == "InputConfigItem" and item["Active"] is True
        assert str(uuid.UUID(item["GUID"])) == item["GUID"]
        assert (item["Controller"]["Name"], item["Controller"]["Serial"]) in PANEL.values()
        device = serials[item["Controller"]["Serial"]]
        assert item["Device"]["Type"] == "Button"
        number = int(re.fullmatch(r"Button ([1-9][0-9]*)", item["Device"]["Name"])[1])
        assert number <= BM.SIZE[device] and (device, number) not in seen
        seen.add((device, number))
        button = item["button"]
        assert tuple(button) == BUTTON and (button["LongReleaseDelay"], button["HoldDelay"]) == (350, 350)
        assert button["RepeatDelay"] == 0 and button["onHold"] is None
        entry = profile.actions(table.DEVICE[device][numbers[device, number]])
        events = ("onPress", "onRelease", "onLongRelease")
        assert {event: act["Command"] for event in events if (act := button[event])} == entry
        for event in entry:
            assert tuple(button[event]) == ("Type", "Command")
            assert button[event]["Type"] == "MSFS2020CustomInputAction"
    assert len(seen) == len(table.DEVICE[1]) + len(table.DEVICE[2])         # every row of the table, no other
    assert len({item["GUID"] for item in config_file["ConfigItems"]}) == len(config_file["ConfigItems"])


@FAMILY
def test_button_numbers_match_buttons_md(key, buttons_md):
    serials = {serial: device for device, (_, serial) in PANEL.items()}
    got = {}
    for item in items(build(key=key)):
        device = serials[item["Controller"]["Serial"]]
        name = re.fullmatch(r"(\w+)(, unit 2)?: .+", item["Name"])
        assert bool(name[2]) == (device == 2)
        got[device, name[1]] = int(item["Device"]["Name"].split()[1])
    assert got == {(d, n): buttons_md[d][n] for d in (1, 2) for n in FAMILIES[key].DEVICE[d]}


@FAMILY
@pytest.mark.parametrize("joysticks", [VJOY, profile.UNBOUND])
def test_other_joysticks_change_only_the_controllers(key, joysticks):
    panel, other = profile.dumps(build(PANEL, key)), profile.dumps(build(joysticks, key))
    assert other != panel
    for device in (1, 2):
        for i in (0, 1):
            other = other.replace(json.dumps(joysticks[device][i]), json.dumps(PANEL[device][i]))
    assert other == panel


def test_a_project_without_guids_asks_for_both_joysticks():
    # MobiFlight 11.3.1 binds a controller that is not connected to the connected one of its name and serial
    # prefix (ControllerAutoBinder.AnalyzeSingleBinding), and asks when two are connected: the panel's joysticks.
    # Each says which device it is where MobiFlight asks, under the name.
    assert build() != build(profile.UNBOUND) == profile.build(FAMILIES["g1000"])
    assert [name for name, _ in profile.UNBOUND.values()] == [profile.NAME] * 2
    for device, (_, serial) in profile.UNBOUND.items():
        assert serial.startswith("JS-") and f"device-{device}" in serial and not profile.SERIAL.fullmatch(serial)


def test_release_events_are_written():
    class Family:
        NAME = "test"
        DEVICE = {1: {"AP": {"press": k("TEST_KEY", 2), "release": k("TEST_KEY", 4)}},
                  2: {"ENT": {"release": h("AS1000_MFD_ENT_Push")}}}
    first, second = items(profile.build(Family, PANEL))
    assert first["Name"] == "AP: TEST_KEY"
    assert first["button"]["onRelease"] == {"Type": "MSFS2020CustomInputAction", "Command": "4 (>K:TEST_KEY)"}
    assert second["Name"] == "ENT, unit 2: AS1000_MFD_ENT_Push" and second["button"]["onPress"] is None
    assert second["Device"]["Name"] == "Button 10"


def test_serials():
    assert profile.serial("JS-9C35F3D0-667E-11F1-8001-444553540000") == PANEL[1][1]
    for bad in ("9c35f3d0-667e-11f1-8001-444553540000", "JS-{9c35f3d0-667e-11f1-8001-444553540000}", "JS-x"):
        with pytest.raises(ValueError):
            profile.serial(bad)


# ---------------- the joysticks from a saved project ----------------
HOTAS = ("T.16000M", "JS-05cf8dd0-3e56-11eb-8004-444553540000")


def saved(tmp_path, *bound):
    """A project as MobiFlight saves it, with these (controller name, serial, button number) bound"""
    config_items = [{"GUID": str(uuid.uuid4()), "Active": True, "Name": "", "Type": "InputConfigItem",
                     "Controller": {"Name": name, "Serial": serial},
                     "Device": {"Type": "Button", "Name": f"Button {number}"},
                     "button": {"onPress": None, "onRelease": None}} for name, serial, number in bound]
    config_items.append({"GUID": str(uuid.uuid4()), "Type": "OutputConfigItem",
                         "Controller": {"Name": "Board", "Serial": "SN-1234"}, "Device": {"Name": "LED"}})
    project = {"Name": "guids", "ConfigFiles": [{"ConfigItems": config_items}], "_version": "0.10"}
    path = tmp_path / "saved.mfproj"
    path.write_text("﻿" + json.dumps(project), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("bound, joysticks", [
    # ENT in unit 2 (device 2, Button 10) and in unit 1 (device 1, Button 83), and a HOTAS button
    (((*PANEL[2], 10), (*HOTAS, 99), (*PANEL[1], 83), (*PANEL[1], 1)), PANEL),
    (((*VJOY[1], 83), (*VJOY[2], 10)), VJOY),
    # another pair of joysticks of one name: the panel's name wins
    (((*VJOY[1], 83), (*VJOY[2], 10), (*PANEL[1], 83), (*PANEL[2], 10)), PANEL),
])
def test_joysticks_from_a_saved_project(tmp_path, bound, joysticks):
    assert profile.controllers_from(saved(tmp_path, *bound)) == joysticks


@FAMILY
def test_a_generated_project_reads_back_its_joysticks(tmp_path, key):
    out = tmp_path / "out.mfproj"
    out.write_text(profile.dumps(build(VJOY, key)), encoding="utf-8")
    assert profile.controllers_from(str(out)) == VJOY
    # one without GUIDs has none to read back
    out.write_text(profile.dumps(build(profile.UNBOUND, key)), encoding="utf-8")
    with pytest.raises(ValueError, match="found 0 such pairs"):
        profile.controllers_from(str(out))


@pytest.mark.parametrize("bound, pairs", [
    (((*PANEL[1], 10), (*PANEL[2], 10)), 0),                    # both joysticks only up to Button 64
    (((*PANEL[1], 83), (*VJOY[2], 10)), 0),                     # two names
    (((*PANEL[1], 83),), 0),
    (((*VJOY[1], 83), (*VJOY[2], 10), (*HOTAS[:1], HOTAS[1][:-1] + "1", 83), (*HOTAS, 10)), 2),
])
def test_saved_projects_that_do_not_tell_the_joysticks_apart(tmp_path, bound, pairs):
    with pytest.raises(ValueError, match=f"need ENT bound on both joysticks.*found {pairs} such pairs"):
        profile.controllers_from(saved(tmp_path, *bound))


@pytest.mark.parametrize("name", [None, 7])
def test_a_joystick_saved_without_a_name_keeps_none(tmp_path, name):
    # (a name that is no text is read as none: it keys the joysticks, which a number or a list would not)
    unnamed = {d: (name, joystick) for d, (_, joystick) in PANEL.items()}
    assert profile.controllers_from(saved(tmp_path, (*unnamed[1], 83), (*unnamed[2], 10))) == {
        d: (None, joystick) for d, (_, joystick) in PANEL.items()}


def test_a_saved_serial_in_upper_case_is_read_as_saved(tmp_path):
    upper = {d: (name, joystick[:3] + joystick[3:].upper()) for d, (name, joystick) in PANEL.items()}
    assert profile.controllers_from(saved(tmp_path, (*upper[1], 83), (*upper[2], 10))) == upper


def test_a_serial_saved_in_two_cases_is_one_joystick(tmp_path):
    # the first spelling saved is kept
    upper = {d: (name, joystick[:3] + joystick[3:].upper()) for d, (name, joystick) in PANEL.items()}
    bound = [(*PANEL[1], 83), (*upper[1], 84), (*PANEL[2], 10)]
    assert profile.controllers_from(saved(tmp_path, *bound)) == PANEL


@pytest.mark.parametrize("text", ["[]", "3", '{"ConfigFiles": 3}', '{"ConfigFiles": [3, {"ConfigItems": [[], 3]}]}',
                                  '{"ConfigFiles": [{"ConfigItems": [{"Type": "InputConfigItem", "Controller": 3, '
                                  '"Device": {"Name": 83}}]}]}'])
def test_a_saved_file_that_is_no_project_is_an_error_not_a_crash(tmp_path, text):
    path = tmp_path / "x.mfproj"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="not a MobiFlight project" if not text.startswith("{") else "found 0"):
        profile.controllers_from(str(path))


# ---------------- the command line ----------------
def report(err, key, controllers):
    """Checks the command's report: per device the buttons mapped, then each unmapped button with its reason,
    one line per reason"""
    for device, section in zip((1, 2), re.split(r"^device [12] .*\n", err, flags=re.M)[1:], strict=True):
        name, serial = controllers[device]
        assert f"device {device} ({name}, {serial}): {len(FAMILIES[key].DEVICE[device])} buttons mapped\n" in err
        lines = re.findall(r"^  unmapped ([A-Z0-9_, ]+): (.+)$", section, flags=re.M)
        assert len({reason for _, reason in lines}) == len(lines)
        listed = [(button, reason) for buttons, reason in lines for button in buttons.split(", ")]
        assert sorted(listed) == sorted(FAMILIES[key].UNMAPPED[device].items())


@FAMILY
def test_command_line_without_joysticks(tmp_path, capsys, monkeypatch, key):
    monkeypatch.chdir(tmp_path)
    cli.main(["--family", key])                     # as its download: avionics-panel-g1000.mfproj, as its card says
    written = (tmp_path / f"avionics-panel-{key}.mfproj").read_text(encoding="utf-8")
    assert written == profile.dumps(build(profile.UNBOUND, key))
    report(capsys.readouterr().err, key, profile.UNBOUND)


@FAMILY
def test_command_line_from_a_saved_project(tmp_path, capsys, monkeypatch, key):
    monkeypatch.chdir(tmp_path)
    cli.main(["--family", key, "--from", saved(tmp_path, (*PANEL[1], 83), (*PANEL[2], 10))])
    assert (tmp_path / f"avionics-panel-{key}.mfproj").read_text(encoding="utf-8") == profile.dumps(build(key=key))
    report(capsys.readouterr().err, key, PANEL)


def test_the_project_read_is_never_written_over(tmp_path, capsys, monkeypatch):
    # a saved project named as the download, read with --from, keeps the user's own bindings: refused, unwritten
    monkeypatch.chdir(tmp_path)
    path = tmp_path / profile.filename("g1000")
    os.rename(saved(tmp_path, (*PANEL[1], 83), (*PANEL[2], 10)), path)
    before = path.read_bytes()
    for args in (["--family", "g1000"], ["--family", "g1000", "-o", str(path)], ["--parts-zip", str(path)]):
        with pytest.raises(SystemExit):
            cli.main([*args, "--from", path.name])
        assert "is the project --from reads" in capsys.readouterr().err and path.read_bytes() == before


def test_command_line_with_serials(tmp_path):
    out = tmp_path / "out.mfproj"
    cli.main(["--family", "g1000", "--serials", PANEL[1][1], PANEL[2][1].upper(), "-o", str(out)])
    assert out.read_text(encoding="utf-8") == profile.dumps(build())


def test_command_line_with_a_vfr_code(tmp_path):
    out = tmp_path / "out.mfproj"
    cli.main(["--family", "gns", "--vfr", "1200", "-o", str(out)])
    assert out.read_text(encoding="utf-8") == profile.dumps(profile.build(FAMILIES["gns"], profile.UNBOUND, "1200"))
    assert '"1200 sp0 (A:TRANSPONDER CODE:1, number) l0 == if{' in out.read_text(encoding="utf-8")


def test_the_stamp_goes_in_the_name_alone(tmp_path):
    # the commit names the project; the items stay as they are, GUIDs and all, so a newer profile replaces them
    stamped, plain = profile.build(FAMILIES["g1000"], stamp="2026-11-14, 5d1c305"), profile.build(FAMILIES["g1000"])
    assert stamped["Name"] == "Avionics Panel: G1000 NXi (2026-11-14, 5d1c305)"
    assert plain["Name"] == "Avionics Panel: G1000 NXi"
    assert {**stamped, "Name": plain["Name"]} == plain
    out = tmp_path / "out.mfproj"
    cli.main(["--family", "g1000", "--stamp", "2026-11-14, 5d1c305", "-o", str(out)])
    assert out.read_text(encoding="utf-8") == profile.dumps(stamped)


def test_the_command_line_stamps_with_the_commit_of_version_py(tmp_path, monkeypatch):
    # a release's files (git archive, the simulator's zip) name their commit in firmware/version.py; a git
    # checkout keeps the placeholder, and a project made there has no stamp unless --stamp gives one
    path = tmp_path / "version.py"
    path.write_text('VERSION = "$Format:%cs, %h$"\n')
    assert profile.version(path) is None and profile.version(tmp_path / "missing.py") is None
    path.write_text('VERSION = "2026-11-14, 5d1c305"\n')
    assert profile.version(path) == "2026-11-14, 5d1c305"
    monkeypatch.setattr(profile, "VERSION", profile.version(path))
    out, parts = tmp_path / "out.mfproj", tmp_path / "parts.zip"
    cli.main(["--autopilot", "kap140", "--cockpit", "g1000", "--navigator", "g1000", "-o", str(out)])
    assert json.loads(out.read_text(encoding="utf-8"))["Name"].endswith(" (2026-11-14, 5d1c305)")
    cli.main(["--family", "g1000", "--stamp", "test", "-o", str(out)])
    assert json.loads(out.read_text(encoding="utf-8"))["Name"] == "Avionics Panel: G1000 NXi (test)"
    cli.main(["--parts-zip", str(parts)])
    import zipfile
    with zipfile.ZipFile(parts) as z:
        assert all(json.loads(z.read(n))["Name"].endswith(" (2026-11-14, 5d1c305)") for n in z.namelist())
    assert profile.version() is None or re.fullmatch(r"\d{4}-\d\d-\d\d, [0-9a-f]{7,40}", profile.version())


def test_a_project_is_named_as_the_download_its_card_names(tmp_path, monkeypatch):
    # without -o: a profile as its download and its card name it (test_command_line_without_joysticks), parts
    # given on the command line as the panel's alone
    monkeypatch.chdir(tmp_path)
    cli.main(["--autopilot", "kap140", "--cockpit", "g1000", "--navigator", "g1000"])
    assert os.listdir(tmp_path) == ["avionics-panel.mfproj"]
    assert "profile avionics-panel-g1000.mfproj," in cli.card.page(FAMILIES["g1000"], "g1000")
    assert profile.filename("autopilot-kap140") == "avionics-panel-autopilot-kap140.mfproj"   # as in the parts zip


def test_the_command_line_lists_the_profiles_and_the_parts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli.main(["--list"])
    lines = capsys.readouterr().out.splitlines()
    units = " ".join(sorted(UNIT_NAVIGATORS) + ["none"])
    assert lines == [f"--family: {' '.join(sorted(FAMILIES))}", f"--ifr1: {' '.join(sorted(FAMILIES))}",
                     f"--autopilot: {' '.join(sorted(AUTOPILOTS))}",
                     f"--cockpit: {' '.join(sorted(COCKPITS))}", f"--navigator: {' '.join(sorted(NAVIGATORS))}",
                     f"--unit1, --unit2: {units}"]
    assert not os.listdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--list", "--family", "g1000"])
    for other in (["--cockpit", "g1000"], ["-o", "x.mfproj"], ["--stamp", "x"]):    # what --list would ignore
        with pytest.raises(SystemExit):
            cli.main(["--list", *other])


@pytest.mark.parametrize("args", [
    ["--serials", PANEL[1][1]],
    ["--serials", PANEL[1][1], PANEL[2][1], "--from", "x"],
    ["--serials", PANEL[1][1], PANEL[1][1]],
    ["--serials", "JS-x", PANEL[2][1]],
    ["--from", "missing.mfproj"],
    ["--family", "g3000"],
    ["-o", "missing-folder/out.mfproj"],
    ["--vfr", "7008"],
    ["--vfr"],
])
def test_command_line_errors(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--family", "g1000", *args])
    assert not os.listdir(tmp_path)


# ---------------- the avionics parts ----------------
def test_the_kinds_of_parts_cover_every_button_once():
    # an autopilot, a cockpit and a navigator in each unit: together every button of both devices, none twice
    for device in (1, 2):
        scopes = [part.scope("autopilot"), part.scope("cockpit"), part.scope("navigator", (1,)),
                  part.scope("navigator", (2,))]
        every = [button for scope in scopes for button in scope[device]]
        assert sorted(every) == sorted(BM.DEVICE[device]), device


@pytest.mark.parametrize("key", sorted(PARTS))
def test_every_unmapped_button_of_a_part_has_a_reason(key):
    # part() holds a part to its kind's buttons (below); each one it leaves unmapped says why
    for device in (1, 2):
        assert all(PARTS[key].UNMAPPED[device].values()), device


def test_compose_refuses_a_keyword_it_does_not_know():
    # unmapped= is gone (an aircraft's reasons are its parts'): a lower-case keyword fails rather than being kept
    with pytest.raises(TypeError, match="unmapped"):
        part.compose("x", AUTOPILOTS["kap140"], COCKPITS["g1000"], NAVIGATORS["g1000"], unmapped={1: {"FD": "x"}})


def test_part_refuses_a_part_that_misses_or_doubles_a_button_of_its_kind():
    every = {1: dict.fromkeys(part.scope("autopilot")[1], "x")}
    part.part("x", "X", "autopilot", {}, every)                          # all unmapped: covered
    missing = {1: {b: r for b, r in every[1].items() if b != "AP"}}
    with pytest.raises(ValueError, match="covers"):
        part.part("x", "X", "autopilot", {}, missing)
    with pytest.raises(ValueError, match="twice"):
        part.part("x", "X", "autopilot", {1: {"AP": "1 (>K:AP_MASTER)"}}, every)
    with pytest.raises(ValueError, match="no such kind"):
        part.scope("panel")


def test_any_parts_make_a_whole_profile():
    # every autopilot, cockpit and navigator choice covers every button, as the generator joins them
    def unit(key, n):
        return part.empty(n) if key == "none" else UNIT_NAVIGATORS[key](n)
    pairs = [(n,) for n in NAVIGATORS.values()] + [
        (unit(a, 1), unit(b, 2)) for a in [*UNIT_NAVIGATORS, "none"] for b in [*UNIT_NAVIGATORS, "none"]]
    for autopilot in AUTOPILOTS.values():
        for cockpit in COCKPITS.values():
            for units in pairs:
                whole = part.compose("x", autopilot, cockpit, *units)
                for device in (1, 2):
                    assert set(whole.DEVICE[device]) | set(whole.UNMAPPED[device]) == set(BM.DEVICE[device])
    with pytest.raises(ValueError, match="needs one autopilot, one cockpit"):
        part.compose("x", AUTOPILOTS["kap140"], COCKPITS["g1000"], UNIT_NAVIGATORS["gns530"](1))
    with pytest.raises(ValueError, match="needs one autopilot, one cockpit"):
        part.compose("x", AUTOPILOTS["kap140"], AUTOPILOTS["gfc700"], NAVIGATORS["g1000"])


def test_every_profile_is_joined_from_parts():
    # one shape: compose()'s, with the parts it is made of
    for key, family in FAMILIES.items():
        kinds = [p.split("-")[0] for p in family.PARTS]
        assert sorted(set(kinds)) == ["autopilot", "cockpit", "navigator"] and len(kinds) >= 3, key
    assert FAMILIES[BONANZA].PARTS == ("autopilot-kfc150", "cockpit-bendix-king",
                                       "navigator-black-square-bonanza-unit1", "navigator-black-square-bonanza-unit2")


def test_joined_navigators_send_every_ones_codes():
    # each button every navigator's codes that map it, in their order, a key's press and release apart; one that
    # none maps the first one's reason; rows (as unit 1 has them) replace buttons, reasons the reasons of buttons none
    # maps; distances each once
    gns430, tds650, pms650 = (UNIT_NAVIGATORS[key](2) for key in ("gns430", "gtn650-tds1", "gtn650-pms50"))
    both = part.joined("x", "X", gns430, tds650, pms650, rows={"CDI": "1 (>K:A)", "PTR": "2 (>K:A)"},
                       reasons={"NRST": "none here"})
    assert both.KEY == "x-unit2" and both.UNITS == (2,) and both.DISTANCES == (gtn.TDS_DISTANCE, part.GPS_DISTANCE)
    assert both.DEVICE[2]["FMS_OUTER_CW"] == " ".join(n.DEVICE[2]["FMS_OUTER_CW"] for n in (gns430, tds650, pms650))
    assert both.DEVICE[2]["DIRECT"] == {
        "press": f"{gns430.DEVICE[2]['DIRECT']} {tds650.DEVICE[2]['DIRECT']['press']} {pms650.DEVICE[2]['DIRECT']}",
        "release": tds650.DEVICE[2]["DIRECT"]["release"]}
    assert both.DEVICE[1]["S_RANGE_CW"].startswith(gns430.DEVICE[1]["S_RANGE_CW"])      # unit 2's map, with SHIFT
    assert both.UNMAPPED[2]["TERR"] == gns430.UNMAPPED[2]["TERR"]
    assert both.DEVICE[2]["CDI"] == "1 (>K:A)" and both.UNMAPPED[2]["NRST"] == "none here"
    assert both.DEVICE[1]["S_PTR"] == "2 (>K:A)" and "PTR" not in both.DEVICE[1]   # unit 2's map: with SHIFT
    with pytest.raises(ValueError, match="joins navigators of one unit"):
        part.joined("x", "X", gns430, UNIT_NAVIGATORS["gns530"](1))
    with pytest.raises(ValueError, match="joins navigators of one unit"):
        part.joined("x", "X", gns430, AUTOPILOTS["kap140"])
    with pytest.raises(ValueError, match=r"\['CDI'\] both mapped and unmapped"):
        part.joined("x", "X", gns430, tds650, rows={"CDI": "1 (>K:A)"}, reasons={"CDI": "none here"})
    with pytest.raises(ValueError, match=r"\['S_PAN_UP'\] are no buttons of a unit as unit 1 has them"):
        part.joined("x", "X", gns430, tds650, rows={"S_PAN_UP": "1 (>K:A)"})              # unit 2's name for it
    with pytest.raises(ValueError, match=r"\['AP'\] are no buttons of a unit"):
        part.joined("x", "X", gns430, tds650, reasons={"AP": "an autopilot's"})
    with pytest.raises(ValueError, match="MSG is a navigator's, not for a reason"):        # it would hide its code
        part.joined("x", "X", gns430, tds650, reasons={"MSG": "none here"})
    with pytest.raises(ValueError, match="REQUIRED_VS would go unread"):
        part.joined("x", "X", gns430, SimpleNamespace(**{**vars(tds650), "REQUIRED_VS": "(L:X, number)"}))


def test_joined_navigators_send_a_key_up_after_a_hold_too():
    # one navigator tells a tap from a hold, another sends its key-up on release: after a hold the other's key-up
    # goes out with the hold's code, so its key is never left down
    tds = UNIT_NAVIGATORS["gtn650-tds1"](2)
    held = part.navigator("held", "Held", {"DIRECT": {"release": "1 (>K:A)", "long": "2 (>K:A)"}},
                          {b: "x" for b in part.UNIT if b != "DIRECT"} | dict.fromkeys(part.MAP, "x"), 2)
    key = part.joined("x", "X", tds, held).DEVICE[2]["DIRECT"]
    down, up = tds.DEVICE[2]["DIRECT"]["press"], tds.DEVICE[2]["DIRECT"]["release"]
    assert key == {"press": down, "release": f"{up} 1 (>K:A)", "long": f"{up} 2 (>K:A)"}
    acts = profile.actions(key)
    assert up in acts["onRelease"] and up in acts["onLongRelease"]
    # a plain code beside a tap and a hold goes out on the press
    plain = part.navigator("plain", "Plain", {"DIRECT": "3 (>K:A)"},
                           {b: "x" for b in part.UNIT if b != "DIRECT"} | dict.fromkeys(part.MAP, "x"), 2)
    assert part.joined("x", "X", plain, held).DEVICE[2]["DIRECT"] == {
        "press": "3 (>K:A)", "release": "1 (>K:A)", "long": "2 (>K:A)"}


def test_the_bonanzas_units_are_their_navigators():
    # every button of a unit is its navigators' plain join (from the module's tuples, as joined() takes them), but
    # its own rows: a row of the unit's own over another of a navigator's buttons fails here
    for unit, joined, navs, own in ((1, bksq.UNIT1, bksq.UNIT1_NAVIGATORS, {"CDI", "NRST", "TERR"}),
                                    (2, bksq.UNIT2, bksq.UNIT2_NAVIGATORS, set())):
        plain = part.joined("x", "X", *navs)
        for d in (1, 2):
            for button, entry in plain.DEVICE[d].items():
                if not (d == unit and button in own):
                    assert joined.DEVICE[d][button] == entry, (unit, d, button)


def test_a_parts_project_names_its_tab_and_keeps_its_own_items():
    # a part's project is named, and labelled as the tab MobiFlight adds, by the part; no two items of all the
    # parts and profiles share a GUID, so tabs of parts stack in one project
    guids = []
    for key, p in PARTS.items():
        project = profile.build(p, PANEL)
        assert project["Name"] == project["ConfigFiles"][0]["Label"] == f"Avionics Panel: {p.TITLE}", key
        guids += [item["GUID"] for item in items(project)]
    assert PARTS["autopilot-kap140"].TITLE == "KAP 140 autopilot"
    assert PARTS["navigator-gns430-unit2"].TITLE == "GNS 430 in unit 2"
    assert build()["ConfigFiles"][0]["Label"] == "Avionics Panel"
    guids += [item["GUID"] for key in FAMILIES for item in items(build(key=key))]
    assert len(set(guids)) == len(guids)


# TDS's values of its units in its key events, as its manual lists them ("Interfacing with Hardware")
TDS_MANUAL = {("750", 1): 0, ("650", 1): 8, ("750", 2): 16, ("650", 2): 24}


@pytest.mark.parametrize("key", sorted(k for k in PARTS if "-tds" in k))
def test_a_tds_navigator_part_sends_its_tds_units_value(key):
    p = PARTS[key]
    model, tds_unit = re.search(r"gtn(750|650)-tds([12])", key).groups()
    value, unit = TDS_MANUAL[model, int(tds_unit)], p.UNITS[0]
    table, s = p.DEVICE[unit], "S_" if unit == 2 else ""
    assert table["HOME"] == {"press": k("GPS_MENU_BUTTON", value + 2), "release": k("GPS_MENU_BUTTON", value + 4)}
    assert table["FMS_INNER_CW"] == k("GPS_PAGE_KNOB_INC", value)
    assert p.DEVICE[1][f"{s}RANGE_CW"] == k("GPS_PAGE_KNOB_DEC", value)
    assert p.DEVICE[1][f"{s}PAN_UP"] == k("GPS_BUTTON2", value + 4)


def test_every_part_has_a_key_of_its_own(monkeypatch):
    # the navigators of one unit in each unit; two parts of a kind with one key fail
    assert {k for k in PARTS if k.startswith("navigator-") and k.endswith(("-unit1", "-unit2"))} == {
        f"navigator-{make(u).KEY}" for make in UNIT_NAVIGATORS.values() for u in (1, 2)}
    monkeypatch.setitem(families.AUTOPILOTS, "again", AUTOPILOTS["kap140"])
    with pytest.raises(ValueError, match="share a key"):
        families.every_part()


def test_command_line_with_parts(tmp_path):
    out = tmp_path / "out.mfproj"
    cli.main(["--autopilot", "kap140", "--cockpit", "g1000", "--navigator", "g1000", "-o", str(out)])
    whole = part.compose("KAP 140 autopilot, G1000 NXi cockpit, G1000 NXi navigator", AUTOPILOTS["kap140"],
                         COCKPITS["g1000"], NAVIGATORS["g1000"])
    assert out.read_text(encoding="utf-8") == profile.dumps(profile.build(whole))
    assert profile.build(whole)["ConfigFiles"][0]["ConfigItems"][0]["Controller"] == {
        "Name": "Avionics Panel", "Serial": "JS-device-1"}
    cli.main(["--autopilot", "kap140", "--cockpit", "bendix-king", "--unit1", "gtn750-tds1", "--unit2", "none",
              "-o", str(out)])
    project = json.loads(out.read_text(encoding="utf-8"))
    assert not [item for item in items(project) if item["Controller"]["Serial"] == "JS-device-2"
                and item["Device"]["Name"] == f"Button {BM.BUTTON[2]['HOME'] + 1}"]


def test_the_parts_zip_holds_a_project_of_every_part(tmp_path):
    import zipfile
    out, again = tmp_path / "parts.zip", tmp_path / "again.zip"
    cli.main(["--parts-zip", str(out), "--vfr", "1200"])
    cli.main(["--parts-zip", str(again), "--vfr", "1200"])
    assert out.read_bytes() == again.read_bytes()                 # the same parts make the same zip
    with zipfile.ZipFile(out) as z:
        assert sorted(z.namelist()) == sorted(f"avionics-panel-{key}.mfproj" for key in PARTS)
        for key, p in PARTS.items():
            vfr = "1200" if p.KIND == "cockpit" else None
            assert z.read(f"avionics-panel-{key}.mfproj").decode() == profile.dumps(profile.build(p, vfr=vfr)), key
        assert {info.external_attr >> 16 for info in z.infolist()} == {0o644}   # rw-r--r-- when unpacked


def test_an_output_takes_its_place_only_once_written(tmp_path):
    # through a new file in the same folder: the old one stays until the new one is whole, and the new one has the
    # mode open() would give it, or the old one's
    out = tmp_path / "x.mfproj"
    out.write_text("old")
    with pytest.raises(RuntimeError), cli.replacing(str(out)) as f:
        f.write("half")
        raise RuntimeError
    assert os.listdir(tmp_path) == ["x.mfproj"] and out.read_text() == "old"
    with cli.replacing(str(out)) as f:
        f.write("new")
    mask = os.umask(0)
    os.umask(mask)
    assert os.listdir(tmp_path) == ["x.mfproj"] and out.read_text() == "new"
    if os.name != "nt":
        assert out.stat().st_mode & 0o777 == 0o666 & ~mask
        out.chmod(0o640)
        with cli.replacing(str(out)) as f:
            f.write("kept")
        assert out.stat().st_mode & 0o777 == 0o640


@pytest.mark.skipif(os.name == "nt", reason="symbolic links need rights on Windows")
def test_an_output_through_a_link_replaces_the_file_it_points_to(tmp_path):
    # as a project linked into MobiFlight's folder: the link stays and MobiFlight reads the new project
    (tmp_path / "mobiflight").mkdir()
    real, link = tmp_path / "mobiflight" / "g1000.mfproj", tmp_path / "g1000.mfproj"
    real.write_text("old")
    link.symlink_to(real)
    with cli.replacing(str(link)) as f:
        f.write("new")
    assert link.is_symlink() and real.read_text() == "new"
    assert sorted(os.listdir(tmp_path / "mobiflight")) == ["g1000.mfproj"]


def test_a_failed_write_leaves_no_parts_zip(tmp_path, monkeypatch):
    # as a project that fails to write: no zip with some parts
    build, built = profile.build, []

    def fail(part, *args):
        if built:
            raise ValueError("no project")
        built.append(part)
        return build(part, *args)
    monkeypatch.setattr(profile, "build", fail)
    with pytest.raises(SystemExit):
        cli.main(["--parts-zip", str(tmp_path / "parts.zip")])
    assert built and not os.listdir(tmp_path)


@pytest.mark.parametrize("args", [
    ["--autopilot", "kap140"],
    ["--autopilot", "kap140", "--cockpit", "g1000"],
    ["--autopilot", "kap140", "--cockpit", "g1000", "--unit1", "gns530"],
    ["--autopilot", "kap140", "--cockpit", "g1000", "--navigator", "g1000", "--unit1", "gns530"],
    ["--family", "g1000", "--cockpit", "g1000"],
    ["--family", "g1000", "--autopilot", "kap140"],
    ["--parts-zip", "x.zip", "--cockpit", "g1000"],
    ["--parts-zip", "x.zip", "-o", "y.mfproj"],
    ["--parts-zip", "x.zip", "--vfr", "7008"],
    ["--autopilot", "kap140", "--cockpit", "g1000", "--unit1", "gns530", "--unit2", "g1000"],
    ["--autopilot", "kap140", "--cockpit", "g1000", "--unit1", "gtn750-tds1", "--unit2", "gtn750-tds1"],
])
def test_command_line_errors_with_parts(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(args)
    assert not os.listdir(tmp_path)


def test_one_navigator_named_by_unit_goes_in_both_units(tmp_path):
    # PMS50 names its GTN by the COM it is on (GTN750_, GTN750_2_): a GTN 750 in each unit works one each, where two
    # of any other navigator would share every code
    out = tmp_path / "x.mfproj"
    cli.main(["--autopilot", "kap140", "--cockpit", "bendix-king", "--unit1", "gtn750-pms50", "--unit2",
              "gtn750-pms50", "-o", str(out)])
    assert out.exists()
    for unit in sorted(UNIT_NAVIGATORS):
        assert bool(cli.codes(UNIT_NAVIGATORS[unit](1)) & cli.codes(UNIT_NAVIGATORS[unit](2))) == \
            ("pms50" not in unit), unit


# ---------------- workflows (docs/using/controls.md) through the panel and the profiles ----------------
def sent(sim, key="g1000", swapped=False):
    """The codes MobiFlight sends for what it saw go down on both joysticks, in order per device (an unmapped
    button sends none); swapped: with the project's two joysticks bound the wrong way round"""
    by_button = {(item["Controller"]["Serial"], item["Device"]["Name"]): item["button"]["onPress"]["Command"]
                 for item in items(build(key=key)) if item["button"]["onPress"]}
    assert sim.held(1) == [] and sim.held(2) == []
    out = ([], [])
    for device in (1, 2):
        for name in sim.presses(device):
            bound = 3 - device if swapped else device
            command = by_button.get((PANEL[bound][1], f"Button {BM.BUTTON[device][name] + 1}"))
            if command:
                out[device - 1].append(command)
    return out


@FAMILY
def test_the_heading_bug_checks_the_binding(key):
    # the check of docs/using/mapping.md, step 4: with SHIFT off, a detent of the ALT/HDG inner knob moves the
    # heading bug by 1° in every family, in either unit, and nothing with the joysticks bound the wrong way round
    # (device 2's Button 39 is the FREQ push, which sends nothing, and it has no Button 40)
    [ring, moves] = re.findall(r"With the amber light by SHIFT off \([^)]*\), turn the (.+?) one detent: the (.+?) "
                               r"must move by 1 degree\.", doc("mapping.md"))[0]
    assert (ring, moves) == ("inner knob of the ALT/HDG knob", "heading bug")
    for unit in (1, 2):
        sim = Sim()
        if unit == 2:
            sim.tap("SHIFT")
            sim.tap("HOME")
        sim.turn("ALTHDG_INNER", 1)
        assert sent(sim, key) == ([k("HEADING_BUG_INC")], [])
        assert sent(sim, key, swapped=True) == ([], [])


# every family tunes the radios and the transponder directly (mobiflight/families/parts.py)
@FAMILY
def test_tune_com1_and_swap(key):
    sim = Sim()
    sim.turn("FREQ_OUTER", 2)
    sim.turn("FREQ_INNER", -3)
    sim.tap("COM_SWAP")
    assert sent(sim, key) == ([k("COM_RADIO_WHOLE_INC")] * 2 + [k("COM_RADIO_FRACT_DEC")] * 3
                              + [k("COM1_RADIO_SWAP")], [])


@FAMILY
def test_tune_com2_and_swap(key):
    # SHIFT, HOME (UNIT) first: radio 2
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("HOME")
    sim.turn("FREQ_INNER", 2)
    sim.tap("COM_SWAP")
    assert sent(sim, key) == ([], [k("COM2_RADIO_FRACT_INC")] * 2 + [k("COM2_RADIO_SWAP")])


@FAMILY
def test_tune_nav1(key):
    sim = Sim()
    sim.tap("FREQ_PUSH")
    sim.turn("FREQ_OUTER", 1)
    sim.turn("FREQ_INNER", 1)
    sim.tap("NAV_SWAP")
    assert sent(sim, key) == ([k("NAV1_RADIO_WHOLE_INC"), k("NAV1_RADIO_FRACT_INC"), k("NAV1_RADIO_SWAP")], [])


@FAMILY
def test_tune_nav2(key):
    # in unit 2 the FREQ push, the turns and NAV ⇆ come from device 2: NAV 2
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("HOME")
    sim.tap("FREQ_PUSH")
    sim.turn("FREQ_OUTER", -1)
    sim.turn("FREQ_INNER", 1)
    sim.tap("NAV_SWAP")
    assert sent(sim, key) == ([], [k("NAV2_RADIO_WHOLE_DEC"), k("NAV2_RADIO_FRACT_INC"), k("NAV2_RADIO_SWAP")])


@FAMILY
def test_squawk_and_ident(key):
    # 1200 to 7012, a digit at a time, then SHIFT, VFR (IDENT)
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("FREQ_INNER", 6)
    for detents in (-2, 1, 2):               # the next digit, then its turns
        sim.turn("FREQ_OUTER", 1)
        sim.turn("FREQ_INNER", detents)
    sim.wait(3500)
    sim.tap("SHIFT")
    sim.tap("VFR")
    forget = " 0 (>L:AvionicsPanel_Squawk_Kept)"         # a code entered forgets the one VFR kept
    assert sent(sim, key) == ([k("XPNDR_1000_INC") + forget] * 6 + [k("XPNDR_100_DEC") + forget] * 2
                              + [k("XPNDR_10_INC") + forget] + [k("XPNDR_1_INC") + forget] * 2
                              + [k("XPNDR_IDENT_ON")], [])


@FAMILY
def test_121_5_tunes_the_units_com(key):
    # SHIFT, COM ⇆ (121.5) in unit 1, then in unit 2 (SHIFT, HOME): COM 1, then COM 2 to 121.5 MHz
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("COM_SWAP")
    sim.tap("SHIFT")
    sim.tap("HOME")
    sim.tap("SHIFT")
    sim.tap("COM_SWAP")
    assert sent(sim, key) == ([k("COM_RADIO_SET_HZ", 121500000)], [k("COM2_RADIO_SET_HZ", 121500000)])


def test_the_g1000_unit_2_is_the_pfd():
    # SHIFT, HOME (UNIT), then CLR and an FMS inner detent: the PFD's, from device 2; then SHIFT, RANGE: the PFD's
    # inset map, from device 1 in either unit
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("HOME")
    sim.tap("CLR")
    sim.turn("FMS_INNER", 1)
    sim.tap("SHIFT")
    sim.turn("RANGE", 1)
    assert sent(sim) == ([h("AS1000_PFD_RANGE_INC")], [h("AS1000_PFD_CLR"), h("AS1000_PFD_FMS_Upper_INC")])


def test_g1000_after_takeoff():
    # SHIFT, FD (YD), then AP
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("FD")
    sim.tap("AP")
    assert sent(sim) == ([k("YAW_DAMPER_TOGGLE"), k("AP_MASTER")], [])
