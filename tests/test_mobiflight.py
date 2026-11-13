"""The MobiFlight profile generator (mobiflight/): the family tables against the button map, their codes, the
project against the format MobiFlight 11 reads, the joysticks read from a saved project, and the documented
workflows through the simulated panel and the profile to the codes."""
import json
import os
import re
import uuid

import buttonmap as BM
import pytest

from mobiflight import __main__ as cli
from mobiflight import profile
from mobiflight.families import FAMILIES
from mobiflight.families.rpn import b, h, k
from sim import Sim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = {1: ("Avionics Panel", "JS-9c35f3d0-667e-11f1-8001-444553540000"),
         2: ("Avionics Panel", "JS-9c35f3d0-667e-11f1-8002-444553540000")}
VJOY = {1: ("vJoy Device", "JS-0a1b2c3d-4e5f-11f1-8001-444553540000"),
        2: ("vJoy Device", "JS-0a1b2c3d-4e5f-11f1-8002-444553540000")}
FAMILY = pytest.mark.parametrize("key", sorted(FAMILIES))


def build(controllers=PANEL, key="g1000"):
    return profile.build(FAMILIES[key], controllers)


def items(project):
    return [item for config_file in project["ConfigFiles"] for item in config_file["ConfigItems"]]


def codes(key):
    """(device, button, event, code) for every code of a family's table"""
    return [(device, button, event, code) for device, buttons in FAMILIES[key].DEVICE.items()
            for button, entry in buttons.items() for event, code in profile.actions(entry).items()]


def buttons_md():
    """(device, name) -> button number, from the table in firmware/BUTTONS.md"""
    out = {}
    with open(os.path.join(ROOT, "firmware", "BUTTONS.md"), encoding="utf-8") as f:
        for line in f:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 4 and cells[2].isdigit():
                for device, number in ((1, cells[2]), (2, cells[3])):
                    if number:
                        out[device, cells[0]] = int(number)
    return out


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


# a code's tokens: a variable, read as (A:NAME:INDEX, unit) or set as (>X:NAME) or (>A:NAME:INDEX, unit), a number
# or an operator
TOKEN = re.compile(r"\([^()]*\)|[^\s()]+")
READ = re.compile(r"\(A:([A-Z0-9 ]+(?::[1-9])?), [A-Za-z]+\)")
WRITE = re.compile(r"\(>(?:(K:[A-Z0-9_]+|[BH]:[A-Za-z0-9_]+)|(A:[A-Z ]+:[1-9]), Enum)\)")
NUMBER = re.compile(r"[0-9]+|0x[0-9A-F]+")
VALUE = re.compile(NUMBER.pattern + r"|[-+!>]|==|dnor|near|if\{|els\{|\}")


def sets(token):
    """What a token sets, as K:EVENT or A:VARIABLE:INDEX, or None"""
    write = WRITE.fullmatch(token)
    return write and (write[1] or write[2])


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


def run(code, variables=()):
    """Runs a code as the simulator's RPN does, on these simulation variables ({name: value}): [(what it set,
    value)], with None for an event sent without a value"""
    variables, stack, out = dict(variables), [], []
    binary = {"+": lambda x, y: x + y, "-": lambda x, y: x - y, ">": lambda x, y: x > y, "==": lambda x, y: x == y}
    unary = {"!": lambda x: not x, "near": round, "dnor": lambda x: x % 360}

    def block(tokens, live):
        """Runs the tokens up to the } that closes their block, if live, and returns the ones after it"""
        while tokens and tokens[0] != "}":
            token, tokens = tokens[0], tokens[1:]
            if token == "if{":
                taken = live and bool(stack.pop())
                tokens = block(tokens, taken)
                if tokens[:1] == ["els{"]:
                    tokens = block(tokens[1:], live and not taken)
            elif not live:
                continue
            elif READ.fullmatch(token):
                stack.append(variables[READ.fullmatch(token)[1]])
            elif sets(token):
                out.append((sets(token), stack.pop() if stack else None))
            elif token in binary:
                right = stack.pop()
                stack.append(binary[token](stack.pop(), right))
            elif token in unary:
                stack.append(unary[token](stack.pop()))
            else:
                stack.append(int(token, 0))
        return tokens[1:]

    block(TOKEN.findall(code), True)
    assert not stack, code
    return out


@FAMILY
def test_codes_are_well_formed(key):
    # every token reads a simulation variable, sets an event or variable, or is a number or operator, every block
    # is closed, every input event's _Inc or _Dec gets its step of 1 or more, and every code sets something; no
    # "@", which MobiFlight would replace with the button's value; and a code fits the 1024 bytes of the message
    # MobiFlight's WASM module takes it in (MOBIFLIGHT_MESSAGE_SIZE in its Module.cpp), with room for the command
    # in front of it
    for device, button, event, code in codes(key):
        tokens = TOKEN.findall(code)
        assert " ".join(tokens) == code and "@" not in code, (device, button, event)
        assert len(code.encode()) < 1000, (device, button, event)
        depth = 0
        for i, token in enumerate(tokens):
            assert READ.fullmatch(token) or sets(token) or VALUE.fullmatch(token), (button, token)
            depth += (token in ("if{", "els{")) - (token == "}")
            assert depth >= 0, (button, code)
            if re.fullmatch(r"\(>B:\w+_(Inc|Dec)\)", token):
                assert i and tokens[i - 1].isdigit() and int(tokens[i - 1]) >= 1, (button, code)
        assert depth == 0 and any(sets(token) for token in tokens), (device, button, event)


def unit(variable):
    """The unit a simulation variable is read in: degrees for a heading or course, number for an index, enum for
    a state, bool for a flag"""
    if re.search(r"HEADING|OBS|RADIAL|NAV LOCALIZER", variable):
        return "degrees"
    return "number" if variable.endswith("SELECTED") else "enum" if variable.endswith("STATE") else "bool"


@FAMILY
def test_reads_use_the_unit_of_their_kind(key):
    for _, button, _, code in codes(key):
        for variable, read_unit in re.findall(r"\(A:([A-Z0-9 ]+)(?::[1-9])?, ([A-Za-z]+)\)", code):
            assert read_unit.lower() == unit(variable), (button, variable)


# the H: events of each family's units, by their prefix, in their exact case
PREFIXES = {
    "g1000": {1: ("AS1000_MFD_",), 2: ("AS1000_MFD_",)},
    "g3x": {1: ("AS3X_Touch_1_", "AS1000_VNAV_TOGGLE"), 2: ("AS3X_Touch_2_",)},
    "gns": {1: ("AS530_", "KAP140_"), 2: ("AS430_",)},
    "gtn": {1: ("KAP140_",), 2: ()},
}


@FAMILY
def test_h_events_go_to_their_unit(key):
    for device, button, _, code in codes(key):
        for name in re.findall(r"\(>H:(\w+)\)", code):
            assert name.startswith(PREFIXES[key][device]), (device, button, name)


def writes(code):
    """[(name, sign)]: the events and variables a code sets, each with the + or - of the step it computes for the
    value, if it does"""
    out, sign = [], None
    for token in TOKEN.findall(code):
        name = sets(token)
        if name:
            out.append((name.split(":", 1)[1], sign))
        if name or token in ("if{", "els{", "}", "+", "-"):
            sign = token if token in ("+", "-") else None
    return out


def words(name):
    """The words of an event's or variable's name, in lower case: RightLargeKnob_Left -> right, large, knob, left"""
    return re.split(r"[^a-z0-9]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower())


# the words of an event that increases or goes up (a GNS knob turned right, its map zoomed out, a step added), and
# of one that decreases or goes down; of several, as in AS1000_RANGE_ZOOM_MFD_Inc, the last one counts
UP, DOWN = {"inc", "up", "right", "dezoom", "+"}, {"dec", "down", "dn", "left", "zoom", "-"}


@FAMILY
def test_turns_and_tilts_use_codes_of_their_direction(key):
    # every event a clockwise or UP button sends increases or goes up, by its name or the sign of the step it sets,
    # and the other way round; a tilt left or right sends events that go left or right
    for _, button, _, code in codes(key):
        last = button.rsplit("_", 1)[-1]
        for name, sign in writes(code):
            way = [w for w in [*words(name), sign] if w in UP | DOWN]
            up, down = (DOWN, UP) if re.search(r"_(SPD|MACH)_VAR_", name) else (UP, DOWN)  # nose up slows it
            if last in ("CCW", "DN"):
                assert way and way[-1] in down, (button, name)
            elif last in ("CW", "UP"):
                assert way and way[-1] in up, (button, name)
            elif last in ("LEFT", "RIGHT"):
                assert last.lower() in words(name), (button, name)


# the words that name a ring of a dual knob in a code: the G1000 calls its FMS rings lower and upper, and the
# simulator's GPS key events, which TDS's GTN takes, turn the page group with the outer ring and the page with the
# inner one
OUTER, INNER = ("outer", "large", "lower", "group"), ("inner", "small", "upper", "page")
RINGS = {"ALT_1000": OUTER, "ALT_100": INNER, "FMS_OUTER": OUTER, "FMS_INNER": INNER}


@FAMILY
def test_rings_use_codes_of_their_ring(key):
    # ALT's outer ring (1000 ft) and inner knob (100 ft), and FMS's, each turn the ring of their name; a code that
    # names no ring is for one knob, as the GFC 500's ALT SEL, whose selector takes a value above 999 as the
    # 1000 ft step (AltitudeSelectManager.ts)
    for _, button, _, code in codes(key):
        ring = RINGS.get(button.rsplit("_", 1)[0])
        if ring is not None:
            other, said = INNER if ring is OUTER else OUTER, [w for name, _ in writes(code) for w in words(name)]
            if any(w in said for w in OUTER + INNER):
                assert any(w in said for w in ring) and not any(w in said for w in other), (button, code)
            else:
                large = any(t.isdigit() and int(t) > 999 for t in TOKEN.findall(code))
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


@FAMILY
def test_numbered_buttons_use_codes_of_their_number(key):
    # MIC 1, COM 1 and NAV 1 audio work radio 1, the ones with 2 radio 2
    for _, button, _, code in codes(key):
        number = re.fullmatch(r"(?:MIC|COM|NAV)([12])(?:_AUDIO)?", button)
        if number is not None:
            assert radios(code) == {number[1]}, (button, code)


# TDS's GTNXi, by its manual (revision 19, "Interfacing with Hardware"): the value of the GTN 750Xi unit 1 (device 1)
# and the GTN 650Xi unit 2 (device 2) in the key events of the bottom right knob (outer GROUP, inner PAGE), and the
# events of the keys, which take that value + 2 when the key goes down and + 4 when it comes up
TDS_UNIT = {1: 0, 2: 24}
TDS_KNOB = {"FMS_OUTER_CW": "GPS_GROUP_KNOB_INC", "FMS_OUTER_CCW": "GPS_GROUP_KNOB_DEC",
            "FMS_INNER_CW": "GPS_PAGE_KNOB_INC", "FMS_INNER_CCW": "GPS_PAGE_KNOB_DEC"}
TDS_KEY = {"HOME": "GPS_MENU_BUTTON", "DIRECT": "GPS_DIRECTTO_BUTTON", "FMS_CRSR": "GPS_CURSOR_BUTTON"}


def test_the_gtn_bezel_is_the_key_events_tds_documents():
    for device, value in TDS_UNIT.items():
        table = FAMILIES["gtn"].DEVICE[device]
        for button, event in TDS_KNOB.items():
            assert table[button] == k(event, value), (device, button)
        for button, event in TDS_KEY.items():
            assert table[button] == {"press": k(event, value + 2), "release": k(event, value + 4)}, (device, button)


@FAMILY
def test_a_held_key_is_let_go(key):
    # a button that sends on release is a key or push (no knob detent, repeat or tilt, which are short presses), and
    # sends the event of its press with another value: TDS's keys, down and up
    for device, buttons in FAMILIES[key].DEVICE.items():
        for button, entry in buttons.items():
            acts = profile.actions(entry)
            if "onRelease" in acts:
                assert key == "gtn" and button in TDS_KEY, (device, button)
                [(press, down)], [(release, up)] = run(acts["onPress"]), run(acts["onRelease"])
                assert press == release and down != up, (device, button)


@FAMILY
def test_units_share_only_the_adf_and_one_cdi(key):
    # unit 2 is the second radio and, beside the G1000, whose units share the MFD, the second navigator: only the
    # one ADF, a CDI and OBS the aircraft has once (docs/using/mapping.md#per-avionics) and the G1000's MFD get the
    # same code from both devices
    device = FAMILIES[key].DEVICE
    for button in set(device[1]) & set(device[2]):
        if device[1][button] == device[2][button]:
            assert button.startswith("ADF_") or button in ("CDI", "OBS") \
                or key == "g1000" and not button.startswith(("COM_", "NAV_")), button


@FAMILY
def test_no_two_functions_send_the_same_code(key):
    # a button's codes are its own: only a function's copy with SHIFT (S_ENT and ENT, S_RANGE_CW and RANGE_CW) and
    # its copy in unit 2 (the test above) send what it sends. So no button sends another one's valid event.
    functions = {}
    for buttons in FAMILIES[key].DEVICE.values():
        for button, entry in buttons.items():
            functions.setdefault(tuple(sorted(profile.actions(entry).items())), set()).add(button.removeprefix("S_"))
    assert [names for names in functions.values() if len(names) > 1] == []


# What every function sets, as uses() gives it (a release after a /; @2 marks the function in unit 2, on device 2):
# the functions every family maps alike, then each family's others. A new, dropped, swapped or misspelt event and
# a changed value show here. The K: events are the MSFS 2024 SDK's key events; the H: events of the G1000's MFD,
# the G3X Touch and the GNS are Working Title's.
EVERY = """
    ADF_100_DN=K:ADF_100_DEC ADF_100_DN@2=K:ADF_100_DEC ADF_100_UP=K:ADF_100_INC ADF_100_UP@2=K:ADF_100_INC
    ADF_10_DN=K:ADF_10_DEC ADF_10_DN@2=K:ADF_10_DEC ADF_10_UP=K:ADF_10_INC ADF_10_UP@2=K:ADF_10_INC
    ADF_1_DN=K:ADF_1_DEC ADF_1_DN@2=K:ADF_1_DEC ADF_1_UP=K:ADF_1_INC ADF_1_UP@2=K:ADF_1_INC
    ADF_AUDIO=K:RADIO_ADF_IDENT_TOGGLE ADF_SWAP=K:ADF1_RADIO_SWAP ADF_SWAP@2=K:ADF1_RADIO_SWAP
    BARO_STD=1,K:BAROMETRIC_STD_PRESSURE CABIN_LT=K:TOGGLE_CABIN_LIGHTS COM1=K:COM1_RECEIVE_SELECT
    COM2=K:COM2_RECEIVE_SELECT COM_121_5=121500000,K:COM_RADIO_SET_HZ COM_121_5@2=121500000,K:COM2_RADIO_SET_HZ
    COM_KHZ_DN=K:COM_RADIO_FRACT_DEC COM_KHZ_DN@2=K:COM2_RADIO_FRACT_DEC COM_KHZ_UP=K:COM_RADIO_FRACT_INC
    COM_KHZ_UP@2=K:COM2_RADIO_FRACT_INC COM_MHZ_DN=K:COM_RADIO_WHOLE_DEC COM_MHZ_DN@2=K:COM2_RADIO_WHOLE_DEC
    COM_MHZ_UP=K:COM_RADIO_WHOLE_INC COM_MHZ_UP@2=K:COM2_RADIO_WHOLE_INC COM_SWAP=K:COM1_RADIO_SWAP
    COM_SWAP@2=K:COM2_RADIO_SWAP DME_AUDIO=K:RADIO_DME1_IDENT_TOGGLE HDG_10_DN=10,-,K:HEADING_BUG_SET
    HDG_10_UP=10,+,K:HEADING_BUG_SET IDENT=K:XPNDR_IDENT_ON MIC1=0,K:PILOT_TRANSMITTER_SET,0,K:COPILOT_TRANSMITTER_SET
    MIC2=1,K:PILOT_TRANSMITTER_SET,1,K:COPILOT_TRANSMITTER_SET NAV1_AUDIO=K:RADIO_VOR1_IDENT_TOGGLE
    NAV2_AUDIO=K:RADIO_VOR2_IDENT_TOGGLE NAV_KHZ_DN=K:NAV1_RADIO_FRACT_DEC NAV_KHZ_DN@2=K:NAV2_RADIO_FRACT_DEC
    NAV_KHZ_UP=K:NAV1_RADIO_FRACT_INC NAV_KHZ_UP@2=K:NAV2_RADIO_FRACT_INC NAV_MHZ_DN=K:NAV1_RADIO_WHOLE_DEC
    NAV_MHZ_DN@2=K:NAV2_RADIO_WHOLE_DEC NAV_MHZ_UP=K:NAV1_RADIO_WHOLE_INC NAV_MHZ_UP@2=K:NAV2_RADIO_WHOLE_INC
    NAV_SWAP=K:NAV1_RADIO_SWAP NAV_SWAP@2=K:NAV2_RADIO_SWAP SQK_D1_DN=K:XPNDR_1000_DEC SQK_D1_UP=K:XPNDR_1000_INC
    SQK_D2_DN=K:XPNDR_100_DEC SQK_D2_UP=K:XPNDR_100_INC SQK_D3_DN=K:XPNDR_10_DEC SQK_D3_UP=K:XPNDR_10_INC
    SQK_D4_DN=K:XPNDR_1_DEC SQK_D4_UP=K:XPNDR_1_INC VFR=0x1200,K:XPNDR_SET XPDR_MODE=1,1,4,A:TRANSPONDER_STATE:1
"""
SETS = {
    "g1000": """
        ALT=B:AS1000_AUTOPILOT_ALTITUDE_PFD_TOGGLE ALT_1000_DN=1,B:AS1000_ALTITUDE_OUTER_PFD_Dec
        ALT_1000_UP=1,B:AS1000_ALTITUDE_OUTER_PFD_Inc ALT_100_DN=1,B:AS1000_ALTITUDE_INNER_PFD_Dec
        ALT_100_UP=1,B:AS1000_ALTITUDE_INNER_PFD_Inc AP=B:AS1000_AUTOPILOT_AP_PFD_TOGGLE
        APR=B:AS1000_AUTOPILOT_APPROACH_PFD_TOGGLE BARO_DN=1,B:AS1000_BARO_PFD_Dec BARO_UP=1,B:AS1000_BARO_PFD_Inc
        BC=B:AS1000_AUTOPILOT_BACKCOURSE_PFD_TOGGLE CDI=K:TOGGLE_GPS_DRIVES_NAV1 CDI@2=K:TOGGLE_GPS_DRIVES_NAV1
        CLR=H:AS1000_MFD_CLR CLR@2=H:AS1000_MFD_CLR CRS_10_DN=10,-,K:GPS_OBS_SET,2,10,-,K:VOR2_SET,10,-,K:VOR1_SET
        CRS_10_UP=10,+,K:GPS_OBS_SET,2,10,+,K:VOR2_SET,10,+,K:VOR1_SET CRS_1_DN=1,B:AS1000_COURSE_PFD_Dec
        CRS_1_UP=1,B:AS1000_COURSE_PFD_Inc CRS_CTR=B:AS1000_COURSE_PUSH_PFD_PUSH DIRECT=H:AS1000_MFD_DIRECTTO
        DIRECT@2=H:AS1000_MFD_DIRECTTO DN=B:AS1000_AUTOPILOT_VERTICALSPEED_DOWN_PFD_PUSH ENT=H:AS1000_MFD_ENT_Push
        ENT@2=H:AS1000_MFD_ENT_Push FD=B:AS1000_AUTOPILOT_FD_PFD_TOGGLE
        FLC=B:AS1000_AUTOPILOT_FLIGHTLEVELCHANGE_PFD_TOGGLE FMS_CRSR=H:AS1000_MFD_FMS_Upper_PUSH
        FMS_CRSR@2=H:AS1000_MFD_FMS_Upper_PUSH FMS_INNER_CCW=H:AS1000_MFD_FMS_Upper_DEC
        FMS_INNER_CCW@2=H:AS1000_MFD_FMS_Upper_DEC FMS_INNER_CW=H:AS1000_MFD_FMS_Upper_INC
        FMS_INNER_CW@2=H:AS1000_MFD_FMS_Upper_INC FMS_OUTER_CCW=H:AS1000_MFD_FMS_Lower_DEC
        FMS_OUTER_CCW@2=H:AS1000_MFD_FMS_Lower_DEC FMS_OUTER_CW=H:AS1000_MFD_FMS_Lower_INC
        FMS_OUTER_CW@2=H:AS1000_MFD_FMS_Lower_INC FPL=H:AS1000_MFD_FPL_Push FPL@2=H:AS1000_MFD_FPL_Push
        HDG=B:AS1000_AUTOPILOT_HEADING_PFD_TOGGLE HDG_1_DN=1,B:AS1000_HEADING_PFD_Dec
        HDG_1_UP=1,B:AS1000_HEADING_PFD_Inc HDG_SYNC=B:AS1000_HEADING_SYNC_PFD_PUSH
        LVL=K:AP_WING_LEVELER_ON,K:AP_PITCH_LEVELER_ON,K:AUTOPILOT_ON MENU=H:AS1000_MFD_MENU_Push
        MENU@2=H:AS1000_MFD_MENU_Push NAV=B:AS1000_AUTOPILOT_NAVIGATION_PFD_TOGGLE PAN_DN=H:AS1000_MFD_JOYSTICK_DOWN
        PAN_LEFT=H:AS1000_MFD_JOYSTICK_LEFT PAN_RIGHT=H:AS1000_MFD_JOYSTICK_RIGHT PAN_UP=H:AS1000_MFD_JOYSTICK_UP
        PROC=H:AS1000_MFD_PROC_Push PROC@2=H:AS1000_MFD_PROC_Push PTR=H:AS1000_MFD_JOYSTICK_PUSH
        RANGE_CCW=1,B:AS1000_RANGE_ZOOM_MFD_Dec RANGE_CW=1,B:AS1000_RANGE_ZOOM_MFD_Inc
        S_DN=B:AS1000_AUTOPILOT_VERTICALSPEED_DOWN_PFD_PUSH S_ENT=H:AS1000_MFD_ENT_Push S_ENT@2=H:AS1000_MFD_ENT_Push
        S_FLC=B:AS1000_AUTOPILOT_FLIGHTLEVELCHANGE_PFD_TOGGLE S_PAN_DN=H:AS1000_MFD_JOYSTICK_DOWN
        S_PAN_LEFT=H:AS1000_MFD_JOYSTICK_LEFT S_PAN_RIGHT=H:AS1000_MFD_JOYSTICK_RIGHT
        S_PAN_UP=H:AS1000_MFD_JOYSTICK_UP S_PTR=H:AS1000_MFD_JOYSTICK_PUSH S_RANGE_CCW=1,B:AS1000_RANGE_ZOOM_MFD_Dec
        S_RANGE_CW=1,B:AS1000_RANGE_ZOOM_MFD_Inc S_UP=B:AS1000_AUTOPILOT_VERTICALSPEED_UP_PFD_PUSH
        S_VNV=B:AS1000_AUTOPILOT_VERTICAL_NAVIGATION_PFD_TOGGLE S_VS=B:AS1000_AUTOPILOT_VERTICALSPEED_PFD_TOGGLE
        UP=B:AS1000_AUTOPILOT_VERTICALSPEED_UP_PFD_PUSH VNV=B:AS1000_AUTOPILOT_VERTICAL_NAVIGATION_PFD_TOGGLE
        VS=B:AS1000_AUTOPILOT_VERTICALSPEED_PFD_TOGGLE YD=K:YAW_DAMPER_TOGGLE
    """,
    "g3x": """
        ALT=K:AP_ALT_HOLD ALT_1000_DN=1000,K:AP_ALT_VAR_DEC ALT_1000_UP=1000,K:AP_ALT_VAR_INC
        ALT_100_DN=K:AP_ALT_VAR_DEC ALT_100_UP=K:AP_ALT_VAR_INC AP=K:AP_MASTER APR=K:AP_APR_HOLD
        BARO_DN=1,K:KOHLSMAN_DEC BARO_UP=1,K:KOHLSMAN_INC CDI=K:TOGGLE_GPS_DRIVES_NAV1 CDI@2=K:TOGGLE_GPS_DRIVES_NAV1
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
        FMS_OUTER_CW@2=H:AS3X_Touch_2_Knob_Outer_R_INC HDG=K:AP_HDG_HOLD HDG_1_DN=K:HEADING_BUG_DEC
        HDG_1_UP=K:HEADING_BUG_INC HDG_SYNC=K:HEADING_BUG_SET
        LVL=K:AP_WING_LEVELER_ON,K:AP_PITCH_LEVELER_ON,K:AUTOPILOT_ON MENU=H:AS3X_Touch_1_Menu_Push
        MENU@2=H:AS3X_Touch_2_Menu_Push NAV=K:AP_NAV1_HOLD NRST=H:AS3X_Touch_1_NRST_Push
        NRST@2=H:AS3X_Touch_2_NRST_Push OBS=K:GPS_OBS OBS@2=K:GPS_OBS
        S_DN=K:AP_VS_VAR_DEC,K:AP_SPD_VAR_INC,K:AP_PITCH_REF_INC_DN S_FLC=K:FLIGHT_LEVEL_CHANGE
        S_UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP S_VNV=H:AS1000_VNAV_TOGGLE S_VS=K:AP_VS_HOLD
        UP=K:AP_VS_VAR_INC,K:AP_SPD_VAR_DEC,K:AP_PITCH_REF_INC_UP VNV=H:AS1000_VNAV_TOGGLE VS=K:AP_VS_HOLD
        YD=K:YAW_DAMPER_TOGGLE
    """,
    "gns": """
        ALT=H:KAP140_Push_ALT ALT_1000_DN=H:KAP140_Knob_Outer_DEC ALT_1000_UP=H:KAP140_Knob_Outer_INC
        ALT_100_DN=H:KAP140_Knob_Inner_DEC ALT_100_UP=H:KAP140_Knob_Inner_INC AP=H:KAP140_Push_AP
        APR=H:KAP140_Push_APR BARO_DN=K:KOHLSMAN_DEC BARO_UP=K:KOHLSMAN_INC BC=H:KAP140_Push_REV CDI=H:AS530_CDI_Push
        CDI@2=H:AS430_CDI_Push CLR=H:AS530_CLR_Push CLR@2=H:AS430_CLR_Push CRS_10_DN=10,-,K:VOR1_SET
        CRS_10_UP=10,+,K:VOR1_SET CRS_1_DN=K:VOR1_OBI_DEC CRS_1_UP=K:VOR1_OBI_INC DIRECT=H:AS530_DirectTo_Push
        DIRECT@2=H:AS430_DirectTo_Push DN=H:KAP140_Push_DN ENT=H:AS530_ENT_Push ENT@2=H:AS430_ENT_Push
        FMS_CRSR=H:AS530_RightSmallKnob_Push FMS_CRSR@2=H:AS430_RightSmallKnob_Push
        FMS_INNER_CCW=H:AS530_RightSmallKnob_Left FMS_INNER_CCW@2=H:AS430_RightSmallKnob_Left
        FMS_INNER_CW=H:AS530_RightSmallKnob_Right FMS_INNER_CW@2=H:AS430_RightSmallKnob_Right
        FMS_OUTER_CCW=H:AS530_RightLargeKnob_Left FMS_OUTER_CCW@2=H:AS430_RightLargeKnob_Left
        FMS_OUTER_CW=H:AS530_RightLargeKnob_Right FMS_OUTER_CW@2=H:AS430_RightLargeKnob_Right FPL=H:AS530_FPL_Push
        FPL@2=H:AS430_FPL_Push HDG=H:KAP140_Push_HDG HDG_1_DN=K:HEADING_BUG_DEC HDG_1_UP=K:HEADING_BUG_INC
        HDG_SYNC=K:HEADING_BUG_SET MAP=H:AS530_CLR_Push_Long MAP@2=H:AS430_CLR_Push_Long MENU=H:AS530_MENU_Push
        MENU@2=H:AS430_MENU_Push MSG=H:AS530_MSG_Push MSG@2=H:AS430_MSG_Push NAV=H:KAP140_Push_NAV
        OBS=H:AS530_OBS_Push OBS@2=H:AS430_OBS_Push PROC=H:AS530_PROC_Push PROC@2=H:AS430_PROC_Push
        RANGE_CCW=H:AS530_RNG_Zoom RANGE_CW=H:AS530_RNG_Dezoom S_DN=H:KAP140_Push_DN S_ENT=H:AS530_ENT_Push
        S_ENT@2=H:AS430_ENT_Push S_RANGE_CCW=H:AS530_RNG_Zoom S_RANGE_CW=H:AS530_RNG_Dezoom S_UP=H:KAP140_Push_UP
        UP=H:KAP140_Push_UP VNAV=H:AS530_VNAV_Push
    """,
    "gtn": """
        ALT=H:KAP140_Push_ALT ALT_1000_DN=H:KAP140_Knob_Outer_DEC ALT_1000_UP=H:KAP140_Knob_Outer_INC
        ALT_100_DN=H:KAP140_Knob_Inner_DEC ALT_100_UP=H:KAP140_Knob_Inner_INC AP=H:KAP140_Push_AP
        APR=H:KAP140_Push_APR BARO_DN=K:KOHLSMAN_DEC BARO_UP=K:KOHLSMAN_INC BC=H:KAP140_Push_REV
        CRS_10_DN=10,-,K:VOR1_SET CRS_10_UP=10,+,K:VOR1_SET CRS_1_DN=K:VOR1_OBI_DEC CRS_1_UP=K:VOR1_OBI_INC
        DIRECT=2,K:GPS_DIRECTTO_BUTTON/4,K:GPS_DIRECTTO_BUTTON
        DIRECT@2=26,K:GPS_DIRECTTO_BUTTON/28,K:GPS_DIRECTTO_BUTTON DN=H:KAP140_Push_DN
        FMS_CRSR=2,K:GPS_CURSOR_BUTTON/4,K:GPS_CURSOR_BUTTON FMS_CRSR@2=26,K:GPS_CURSOR_BUTTON/28,K:GPS_CURSOR_BUTTON
        FMS_INNER_CCW=0,K:GPS_PAGE_KNOB_DEC FMS_INNER_CCW@2=24,K:GPS_PAGE_KNOB_DEC FMS_INNER_CW=0,K:GPS_PAGE_KNOB_INC
        FMS_INNER_CW@2=24,K:GPS_PAGE_KNOB_INC FMS_OUTER_CCW=0,K:GPS_GROUP_KNOB_DEC
        FMS_OUTER_CCW@2=24,K:GPS_GROUP_KNOB_DEC FMS_OUTER_CW=0,K:GPS_GROUP_KNOB_INC
        FMS_OUTER_CW@2=24,K:GPS_GROUP_KNOB_INC HDG=H:KAP140_Push_HDG HDG_1_DN=K:HEADING_BUG_DEC
        HDG_1_UP=K:HEADING_BUG_INC HDG_SYNC=K:HEADING_BUG_SET HOME=2,K:GPS_MENU_BUTTON/4,K:GPS_MENU_BUTTON
        HOME@2=26,K:GPS_MENU_BUTTON/28,K:GPS_MENU_BUTTON NAV=H:KAP140_Push_NAV S_DN=H:KAP140_Push_DN
        S_UP=H:KAP140_Push_UP UP=H:KAP140_Push_UP
    """,
}


@FAMILY
def test_what_every_function_sets(key):
    found = {f"{button}{'@2' * (device == 2)}={'/'.join(uses(code) for code in profile.actions(entry).values())}"
             for device, buttons in FAMILIES[key].DEVICE.items() for button, entry in buttons.items()}
    assert found == set((EVERY + SETS[key]).split())


def test_the_vfr_key_sets_the_squawk_asked_for():
    # XPNDR_SET takes the code as BCO16, its four digits as hex: the tables' 1200 unless another is asked for, and
    # nothing else changes with it
    for key in FAMILIES:
        usual, other = items(build(key=key)), items(profile.build(FAMILIES[key], PANEL, "7000"))
        [(a, b)] = [(a, b) for a, b in zip(usual, other, strict=True) if a != b]
        assert a["Name"] == b["Name"] == "VFR: XPNDR_SET"
        assert run(a["button"]["onPress"]["Command"]) == [("K:XPNDR_SET", 0x1200)]
        assert run(b["button"]["onPress"]["Command"]) == [("K:XPNDR_SET", 0x7000)]
        assert items(profile.build(FAMILIES[key], PANEL, 7000)) == other
        assert items(profile.build(FAMILIES[key], PANEL, "1200")) == usual
    for bad in ("7800", "120", "12000", "VFR", "", 120):
        with pytest.raises(ValueError, match="not a squawk code"):
            profile.build(FAMILIES["g1000"], PANEL, bad)


def test_a_vfr_code_replaces_the_squawk_of_the_table():
    # a table with another squawk on its VFR key keeps it unless a code is asked for, 1200 included; one whose VFR
    # key sets no squawk, or more than that, takes no code
    def command(entry, vfr):
        class Family:
            NAME = "test"
            DEVICE = {1: {"VFR": entry}, 2: {}}
        [item] = items(profile.build(Family, PANEL, vfr))
        return item["button"]["onPress"]["Command"]

    ident = k("XPNDR_IDENT_ON")
    assert command(k("XPNDR_SET", "0x7000"), None) == k("XPNDR_SET", "0x7000")
    assert command(k("XPNDR_SET", "0x7000"), "1200") == k("XPNDR_SET", "0x1200")
    assert command(ident, None) == ident
    for entry in (ident, k("XPNDR_SET", "0x1200") + " " + ident):
        with pytest.raises(ValueError, match="the VFR key of test sets no squawk"):
            command(entry, "1200")
    with pytest.raises(ValueError, match="not a squawk code"):
        command(ident, "7800")


@pytest.mark.parametrize("key", ["g1000", "g3x"])
def test_the_fast_crs_step_sets_the_course_the_cdi_shows(key):
    # Working Title's G1000 NXi and G3X Touch keep GPS DRIVES NAV1 and AUTOPILOT NAV SELECTED on their CDI: 10° on
    # the GPS's OBS course, or on the course of the NAV radio it shows, in whole degrees from 0 to 360
    table = FAMILIES[key].DEVICE[1]
    courses = {"GPS OBS VALUE": 355.4, "NAV OBS:1": 5, "NAV OBS:2": 180}
    for radio, up, down in ((1, 15, 355), (2, 190, 170)):
        variables = {"GPS DRIVES NAV1": 0, "AUTOPILOT NAV SELECTED": radio, **courses}
        assert run(table["CRS_10_UP"], variables) == [(f"K:VOR{radio}_SET", up)]
        assert run(table["CRS_10_DN"], variables) == [(f"K:VOR{radio}_SET", down)]
        variables["GPS DRIVES NAV1"] = 1
        assert run(table["CRS_10_UP"], variables) == [("K:GPS_OBS_SET", 5)]
        assert run(table["CRS_10_DN"], variables) == [("K:GPS_OBS_SET", 345)]
    assert table["CRS_1_UP"] != table["CRS_10_UP"] and table["CRS_1_DN"] != table["CRS_10_DN"]


@FAMILY
def test_xpdr_mode_switches_between_standby_and_alt(key):
    # Working Title's G1000 NXi and G3X Touch and the KT 76 of the KAP 140 cockpit keep the transponder's mode in
    # TRANSPONDER STATE:1 (the SDK: 0 off, 1 standby, 2 test, 3 on, 4 ALT, 5 ground): standby or off goes to ALT,
    # any other mode to standby, also the ground mode a G3X Touch may turn ALT into on the ground
    # (TransponderAutoGroundAltManager.ts)
    code = FAMILIES[key].DEVICE[1]["XPDR_MODE"]
    for mode, then in ((0, 4), (1, 4), (2, 1), (3, 1), (4, 1), (5, 1)):
        assert run(code, {"TRANSPONDER STATE:1": mode}) == [("A:TRANSPONDER STATE:1", then)]


@FAMILY
def test_com_1_and_com_2_switch_their_receiver_on_and_off(key):
    # each sets its own receiver to the opposite of what it is
    table = FAMILIES[key].DEVICE[1]
    for radio, other in ((1, 2), (2, 1)):
        for listening in (0, 1):
            variables = {f"COM RECEIVE EX1:{radio}": listening, f"COM RECEIVE EX1:{other}": 1 - listening}
            assert run(table[f"COM{radio}"], variables) == [(f"K:COM{radio}_RECEIVE_SELECT", not listening)]


@FAMILY
def test_the_fast_hdg_step_moves_the_heading_bug(key):
    # 10° from where the bug is, not from the heading flown, in whole degrees from 0 to 360
    table = FAMILIES[key].DEVICE[1]
    variables = {"AUTOPILOT HEADING LOCK DIR:1": 355.4, "HEADING INDICATOR:1": 90}
    assert run(table["HDG_10_UP"], variables) == [("K:HEADING_BUG_SET", 5)]
    assert run(table["HDG_10_DN"], variables) == [("K:HEADING_BUG_SET", 345)]


@pytest.mark.parametrize("key", ["g3x", "gns", "gtn"])
def test_the_hdg_push_sets_the_bug_to_the_heading(key):
    # the heading flown, in whole degrees from 0 to 359 (the G1000 has an input event for the push)
    code = FAMILIES[key].DEVICE[1]["HDG_SYNC"]
    for heading, bug in ((359.6, 0), (90.4, 90), (0.4, 0)):
        variables = {"HEADING INDICATOR:1": heading, "AUTOPILOT HEADING LOCK DIR:1": 200}
        assert run(code, variables) == [("K:HEADING_BUG_SET", bug)]


@pytest.mark.parametrize("key", ["gns", "gtn"])
def test_the_fast_crs_step_of_the_kap_140_cockpit_is_nav_1s(key):
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
    # GPS or without a signal
    code = FAMILIES["g3x"].DEVICE[1]["CRS_CTR"]
    signals = {"NAV HAS LOCALIZER:1": 1, "NAV LOCALIZER:1": 94.6, "NAV HAS NAV:1": 1, "NAV RADIAL:1": 10,
               "NAV HAS LOCALIZER:2": 0, "NAV LOCALIZER:2": 0, "NAV HAS NAV:2": 1, "NAV RADIAL:2": 200.4}

    def centred(gps, radio, **changed):
        return run(code, {"GPS DRIVES NAV1": gps, "AUTOPILOT NAV SELECTED": radio, **signals, **changed})

    assert centred(0, 1) == [("K:VOR1_SET", 95)]
    assert centred(0, 2) == [("K:VOR2_SET", 20)]
    assert centred(0, 2, **{"NAV HAS NAV:2": 0}) == []
    assert centred(1, 1) == centred(1, 2) == []


def test_the_g3x_fd_key_does_nothing_with_the_autopilot_engaged():
    code = FAMILIES["g3x"].DEVICE[1]["FD"]
    assert run(code, {"AUTOPILOT MASTER": 0}) == [("K:TOGGLE_FLIGHT_DIRECTOR", None)]
    assert run(code, {"AUTOPILOT MASTER": 1}) == []


def test_the_g3x_up_and_dn_step_the_reference_of_the_vertical_mode():
    # VS first, then IAS (nose up slows it), then pitch, and nothing in another mode
    table = FAMILIES["g3x"].DEVICE[1]
    modes = ("AUTOPILOT VERTICAL HOLD", "AUTOPILOT FLIGHT LEVEL CHANGE", "AUTOPILOT PITCH HOLD")
    for on, up, down in (((1, 1, 1), "AP_VS_VAR_INC", "AP_VS_VAR_DEC"), ((0, 1, 1), "AP_SPD_VAR_DEC", "AP_SPD_VAR_INC"),
                         ((0, 0, 1), "AP_PITCH_REF_INC_UP", "AP_PITCH_REF_INC_DN"), ((0, 0, 0), None, None)):
        variables = dict(zip(modes, on, strict=True))
        for button, event in (("UP", up), ("S_UP", up), ("DN", down), ("S_DN", down)):
            assert run(table[button], variables) == ([(f"K:{event}", None)] if event else [])


@FAMILY
def test_std_names_the_altimeter(key):
    # BAROMETRIC_STD_PRESSURE takes the index of the altimeter (the SDK): the first one
    assert run(FAMILIES[key].DEVICE[1]["BARO_STD"]) == [("K:BAROMETRIC_STD_PRESSURE", 1)]


def test_actions_take_a_press_a_release_or_both():
    assert profile.actions("a") == {"onPress": "a"}
    assert profile.actions({"press": "a", "release": "b"}) == {"onPress": "a", "onRelease": "b"}
    assert profile.actions({"release": "b"}) == {"onRelease": "b"}
    for bad in ({}, {"hold": "a"}):
        with pytest.raises(ValueError):
            profile.actions(bad)


# ---------------- the project ----------------
ITEM = ("GUID", "Active", "Name", "Type", "Controller", "Device", "button")
BUTTON = ("onPress", "onRelease", "onLongRelease", "onHold", "LongReleaseDelay", "HoldDelay", "RepeatDelay")


@FAMILY
def test_the_project_has_the_structure_mobiflight_reads(key):
    # MobiFlight 11.3.1: Project (Name, Sim, Features, Aircraft, ConfigFiles, "_version" 0.10), an embedded
    # ConfigFile, InputConfigItem with Controller {Name, Serial} and Device {Type Button, Name "Button N"},
    # ButtonInputConfig, MSFS2020CustomInputAction {Command} with the table's code
    project = json.loads(profile.dumps(build(key=key)))
    assert tuple(project) == ("Name", "Sim", "Features", "Aircraft", "ConfigFiles", "_version")
    assert project["_version"] == "0.10" and project["Sim"] == "msfs" and project["Aircraft"] == []
    assert project["Features"] == {"FSUIPC": False, "ProSim": False}
    [config_file] = project["ConfigFiles"]
    assert {k: v for k, v in config_file.items() if k != "ConfigItems"} == {
        "Label": "Avionics Panel", "FileName": None, "ReferenceOnly": False, "EmbedContent": True}
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
        assert button["RepeatDelay"] == 0 and button["onLongRelease"] is None and button["onHold"] is None
        entry = profile.actions(FAMILIES[key].DEVICE[device][numbers[device, number]])
        assert {event: act["Command"] for event in ("onPress", "onRelease") if (act := button[event])} == entry
        for event in entry:
            assert tuple(button[event]) == ("Type", "Command")
            assert button[event]["Type"] == "MSFS2020CustomInputAction"
    assert len({item["GUID"] for item in config_file["ConfigItems"]}) == len(config_file["ConfigItems"])


@FAMILY
def test_button_numbers_match_buttons_md(key):
    numbers = buttons_md()
    serials = {serial: device for device, (_, serial) in PANEL.items()}
    got = {}
    for item in items(build(key=key)):
        device = serials[item["Controller"]["Serial"]]
        name = re.fullmatch(r"(\w+)(, unit 2)?: .+", item["Name"])
        assert bool(name[2]) == (device == 2)
        got[device, name[1]] = int(item["Device"]["Name"].split()[1])
    assert got == {k: numbers[k] for d in (1, 2) for k in [(d, n) for n in FAMILIES[key].DEVICE[d]]}


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
    cli.main(["--family", key])
    assert (tmp_path / f"{key}.mfproj").read_text(encoding="utf-8") == profile.dumps(build(profile.UNBOUND, key))
    report(capsys.readouterr().err, key, profile.UNBOUND)


@FAMILY
def test_command_line_from_a_saved_project(tmp_path, capsys, monkeypatch, key):
    monkeypatch.chdir(tmp_path)
    cli.main(["--family", key, "--from", saved(tmp_path, (*PANEL[1], 83), (*PANEL[2], 10))])
    assert (tmp_path / f"{key}.mfproj").read_text(encoding="utf-8") == profile.dumps(build(key=key))
    report(capsys.readouterr().err, key, PANEL)


def test_command_line_with_serials(tmp_path):
    out = tmp_path / "out.mfproj"
    cli.main(["--family", "g1000", "--serials", PANEL[1][1], PANEL[2][1].upper(), "-o", str(out)])
    assert out.read_text(encoding="utf-8") == profile.dumps(build())


def test_command_line_with_a_vfr_code(tmp_path):
    out = tmp_path / "out.mfproj"
    cli.main(["--family", "gns", "--vfr", "7000", "-o", str(out)])
    assert out.read_text(encoding="utf-8") == profile.dumps(profile.build(FAMILIES["gns"], profile.UNBOUND, "7000"))
    assert '"0x7000 (>K:XPNDR_SET)"' in out.read_text(encoding="utf-8")


@pytest.mark.parametrize("args", [
    ["--serials", PANEL[1][1]],
    ["--serials", PANEL[1][1], PANEL[2][1], "--from", "x"],
    ["--serials", PANEL[1][1], PANEL[1][1]],
    ["--serials", "JS-x", PANEL[2][1]],
    ["--from", "missing.mfproj"],
    ["--family", "g3000"],
    ["--vfr", "7008"],
    ["--vfr"],
])
def test_command_line_errors(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(["--family", "g1000", *args])
    assert not os.listdir(tmp_path)


# ---------------- workflows (docs/using/controls.md) through the panel and the profiles ----------------
def sent(sim, key="g1000"):
    """The codes MobiFlight sends for what it saw go down on both joysticks, in order per device (an unmapped
    button sends none)"""
    by_button = {(item["Controller"]["Serial"], item["Device"]["Name"]): item["button"]["onPress"]["Command"]
                 for item in items(build(key=key)) if item["button"]["onPress"]}
    assert sim.held(1) == [] and sim.held(2) == []
    out = ([], [])
    for device in (1, 2):
        for name in sim.presses(device):
            command = by_button.get((PANEL[device][1], f"Button {BM.BUTTON[device][name] + 1}"))
            if command:
                out[device - 1].append(command)
    return out


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
    assert sent(sim, key) == ([k("XPNDR_1000_INC")] * 6 + [k("XPNDR_100_DEC")] * 2 + [k("XPNDR_10_INC")]
                              + [k("XPNDR_1_INC")] * 2 + [k("XPNDR_IDENT_ON")], [])


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


def test_g1000_after_takeoff():
    # SHIFT, FD (YD), then AP
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("FD")
    sim.tap("AP")
    assert sent(sim) == ([k("YAW_DAMPER_TOGGLE"), b("AS1000_AUTOPILOT_AP_PFD_TOGGLE")], [])
