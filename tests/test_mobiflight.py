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
from mobiflight.families.rpn import b, h, k, lvar
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


# a code's tokens: a variable, read as (A:NAME:INDEX, unit) or set as (>X:NAME), a number or an operator
TOKEN = re.compile(r"\([^()]*\)|[^\s()]+")
READ = re.compile(r"\(A:[A-Z0-9 ]+(:[1-9])?, [A-Za-z]+\)")
WRITE = re.compile(r"\(>(K:[A-Z0-9_]+|[BHL]:[A-Za-z0-9_]+)\)")
VALUE = re.compile(r"[0-9]+|0x[0-9A-F]+|[-+!]|==|dnor|near|if\{|els\{|\}")


@FAMILY
def test_codes_are_well_formed(key):
    # every token reads a simulation variable, sets an event or variable, or is a number or operator, every block
    # is closed, every input event's _Inc or _Dec gets its step of 1 or more, and every code sets something; no
    # "@", which MobiFlight would replace with the button's value
    for device, button, event, code in codes(key):
        tokens = TOKEN.findall(code)
        assert " ".join(tokens) == code and "@" not in code, (device, button, event)
        depth = 0
        for i, token in enumerate(tokens):
            assert READ.fullmatch(token) or WRITE.fullmatch(token) or VALUE.fullmatch(token), (button, token)
            depth += (token in ("if{", "els{")) - (token == "}")
            assert depth >= 0, (button, code)
            if re.fullmatch(r"\(>B:\w+_(Inc|Dec)\)", token):
                assert i and tokens[i - 1].isdigit() and int(tokens[i - 1]) >= 1, (button, code)
        assert depth == 0 and any(WRITE.fullmatch(token) for token in tokens), (device, button, event)


def unit(variable):
    """The unit a simulation variable is read in: degrees for a heading or course, number for an index, bool for
    a flag"""
    if re.search(r"HEADING|OBS|RADIAL|NAV LOCALIZER", variable):
        return "degrees"
    return "number" if variable.endswith("SELECTED") else "bool"


@FAMILY
def test_reads_use_the_unit_of_their_kind(key):
    for _, button, _, code in codes(key):
        for variable, read_unit in re.findall(r"\(A:([A-Z0-9 ]+)(?::[1-9])?, ([A-Za-z]+)\)", code):
            assert read_unit.lower() == unit(variable), (button, variable)


# the H: events and L: variables of each family's units, by their prefix, in their exact case
PREFIXES = {
    "g1000": {1: ("AS1000_MFD_",), 2: ("AS1000_MFD_",)},
    "g3x": {1: ("AS3X_Touch_1_", "AS1000_VNAV_TOGGLE"), 2: ("AS3X_Touch_2_",)},
    "gns": {1: ("AS530_", "KAP140_"), 2: ("AS430_",)},
    "gtn": {1: ("TDSGTNXI750U1_", "KAP140_"), 2: ("TDSGTNXI650U2_",)},
}


@FAMILY
def test_h_events_and_l_variables_go_to_their_unit(key):
    for device, button, _, code in codes(key):
        for name in re.findall(r"\(>[HL]:(\w+)\)", code):
            assert name.startswith(PREFIXES[key][device]), (device, button, name)


def writes(code):
    """[(name, sign)]: the events and variables a code sets, each with the + or - of the step it computes for the
    value, if it does"""
    out, sign = [], None
    for token in TOKEN.findall(code):
        name = WRITE.fullmatch(token)
        if name:
            out.append((name[1].split(":", 1)[1], sign))
        if name or token in ("if{", "els{", "}", "+", "-"):
            sign = token if token in ("+", "-") else None
    return out


def words(name):
    """The words of an event's or variable's name, in lower case: RKnobOuterInc -> r, knob, outer, inc"""
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


# the words that name a ring of a dual knob in a code: the G1000 calls its FMS rings lower and upper
OUTER, INNER = ("outer", "large", "lower"), ("inner", "small", "upper")
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


@FAMILY
def test_a_held_key_is_let_go(key):
    # a key that sets an L: variable to 1 on press (TDS's HOME and the like) sets it back to 0 on release; a
    # knob's detent (a turn) only sets it
    for device, buttons in FAMILIES[key].DEVICE.items():
        for button, entry in buttons.items():
            acts = profile.actions(entry)
            held = re.fullmatch(r"1 \(>L:(\w+)\)", acts.get("onPress", ""))
            if held and not button.endswith(("_CW", "_CCW", "_UP", "_DN")):
                assert acts.get("onRelease") == lvar(held[1], 0), (device, button)
            if "onRelease" in acts:
                assert held and acts["onRelease"] == lvar(held[1], 0), (device, button)


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
        DEVICE = {1: {"AP": {"press": lvar("TEST_KEY", 1), "release": lvar("TEST_KEY", 0)}},
                  2: {"ENT": {"release": h("AS1000_MFD_ENT_Push")}}}
    first, second = items(profile.build(Family, PANEL))
    assert first["Name"] == "AP: TEST_KEY"
    assert first["button"]["onRelease"] == {"Type": "MSFS2020CustomInputAction", "Command": "0 (>L:TEST_KEY)"}
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


@pytest.mark.parametrize("args", [
    ["--serials", PANEL[1][1]],
    ["--serials", PANEL[1][1], PANEL[2][1], "--from", "x"],
    ["--serials", PANEL[1][1], PANEL[1][1]],
    ["--serials", "JS-x", PANEL[2][1]],
    ["--from", "missing.mfproj"],
    ["--family", "g3000"],
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
