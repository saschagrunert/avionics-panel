"""The MobiFlight profile generator (mobiflight/): the family tables against the button map, HubHop's database as
downloaded, the project against the format MobiFlight 11 reads, the joysticks read from a saved project, and
the documented workflows through the simulated panel and the profile to the presets. These run on a made-up
preset database; `py -m mobiflight.hubhop` and its CI job check the tables against HubHop's."""
import http.server
import json
import os
import re
import threading
import uuid

import buttonmap as BM
import pytest

from mobiflight import __main__ as cli
from mobiflight import hubhop, profile
from mobiflight.families import FAMILIES
from sim import Sim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = {1: ("Avionics Panel", "JS-9c35f3d0-667e-11f1-8001-444553540000"),
         2: ("Avionics Panel", "JS-9c35f3d0-667e-11f1-8002-444553540000")}
VJOY = {1: ("vJoy Device", "JS-0a1b2c3d-4e5f-11f1-8001-444553540000"),
        2: ("vJoy Device", "JS-0a1b2c3d-4e5f-11f1-8002-444553540000")}
FAMILY = pytest.mark.parametrize("key", sorted(FAMILIES))


def preset(name, **fields):
    """A made-up HubHop input preset of this name, its code the name in parentheses"""
    vendor, aircraft, label = name.split(".", 2)
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_OID, name)), "path": name, "vendor": vendor, "aircraft": aircraft,
            "label": label, "code": f"({name})", "presetType": "Input", **fields}


DATABASE = [preset(name) for name in sorted(hubhop.names())]
PRESETS = {profile.key(p): p for p in DATABASE}


@pytest.fixture
def database(tmp_path):
    """The made-up database as a downloaded file"""
    path = tmp_path / "hubhop-presets.json"
    path.write_text(json.dumps(DATABASE), encoding="utf-8")
    return str(path)


def build(controllers=PANEL, key="g1000"):
    return profile.build(FAMILIES[key], controllers, PRESETS)


def items(project):
    return [item for config_file in project["ConfigFiles"] for item in config_file["ConfigItems"]]


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


UP, DOWN = {"inc", "up"}, {"dec", "down", "dn"}


@FAMILY
def test_turns_and_tilts_use_presets_of_their_direction(key):
    # a clockwise or UP button names a preset that increases or goes up, and the other way round; a tilt left
    # or right one that goes left or right
    for buttons in FAMILIES[key].DEVICE.values():
        for button, entry in buttons.items():
            last = button.rsplit("_", 1)[-1]
            for name in profile.actions(entry).values():
                words = set(re.split(r"[^a-z0-9]+", name.split(".", 2)[2].lower()))
                if last in ("CCW", "DN"):
                    assert words & DOWN and not words & UP, (button, name)
                elif last in ("CW", "UP"):
                    assert words & UP and not words & DOWN, (button, name)
                elif last in ("LEFT", "RIGHT"):
                    assert last.lower() in words, (button, name)


@FAMILY
def test_unit_2_tunes_other_radios(key):
    # unit 2 is the second COM and NAV radio: no COM or NAV button sends the same preset from both devices
    device = FAMILIES[key].DEVICE
    for button in device[2]:
        if button.startswith(("COM_", "NAV_")) and button in device[1]:
            assert device[1][button] != device[2][button], button


# ---------------- HubHop's database ----------------
def test_lookup_takes_the_input_preset_of_each_name():
    name = "Microsoft.Generic.YAW_DAMPER_TOGGLE"
    output = preset(name, presetType="Output", id=str(uuid.uuid4()))
    assert hubhop.lookup([output, PRESETS[name]], {name}) == {name: PRESETS[name]}


@pytest.mark.parametrize("database, error", [
    ([], r"Microsoft.Generic.YAW_DAMPER_TOGGLE: 0 presets"),
    ([PRESETS["Microsoft.Generic.YAW_DAMPER_TOGGLE"]] * 2, r"Microsoft.Generic.YAW_DAMPER_TOGGLE: 2 presets"),
])
def test_lookup_fails_on_a_missing_or_ambiguous_name(database, error):
    with pytest.raises(ValueError, match=f"(?s){error}.*HubHop changed; the family table needs an update"):
        hubhop.lookup(database, {"Microsoft.Generic.YAW_DAMPER_TOGGLE"})


NOT_THE_DATABASE = {                     # replies and files that are not HubHop's database, and the error
    "html": (b"<html>maintenance</html>", "not HubHop's preset database: Expecting value"),
    "object": (b'{"presets": []}', "not a JSON list of presets"),
    "strings": (b'["a", "b"]', "not a JSON list of presets"),
    "no_vendor": (json.dumps([{k: v for k, v in DATABASE[0].items() if k != "vendor"}]).encode(),
                  "each hold id, vendor, aircraft, label, code, presetType"),
    "not_utf8": (b"[\xff]", "not HubHop's preset database"),
}


@pytest.mark.parametrize("case", sorted(NOT_THE_DATABASE))
def test_load_fails_clearly(tmp_path, case):
    data, error = NOT_THE_DATABASE[case]
    path = tmp_path / "presets.json"
    path.write_bytes(data)
    with pytest.raises(ValueError, match=error):
        hubhop.load(str(path))


def test_load_says_how_to_download(tmp_path):
    with pytest.raises(ValueError, match="cannot read HubHop's presets .* download them with `py -m mobiflight"):
        hubhop.load(str(tmp_path / "missing.json"))


class Server(http.server.BaseHTTPRequestHandler):
    """HubHop as it might answer: the database, something else, an error, or a transfer cut off"""
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.strip("/")
        if path not in ("db", "empty", "cut", *NOT_THE_DATABASE):
            self.send_error(int(path) if path.isdigit() else 404)
            return
        body = {"db": json.dumps(DATABASE).encode(), "empty": b"[]", "cut": b"[" + b" " * 500}.get(path) or \
            NOT_THE_DATABASE[path][0]
        self.send_response(200)
        self.send_header("Content-Length", str(100_000 if path == "cut" else len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def server():
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Server) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}/"
        httpd.shutdown()


def test_download_saves_and_checks_the_database(tmp_path, server, capsys):
    out = tmp_path / "saved.json"
    hubhop.main(["-o", str(out), "--url", server + "db"])
    assert json.loads(out.read_text(encoding="utf-8")) == DATABASE
    assert "every preset of the family tables found" in capsys.readouterr().err


@pytest.mark.parametrize("path, error", [
    ("cut", "cannot download HubHop's presets .*IncompleteRead"),
    ("500", "cannot download HubHop's presets .*HTTP Error 500"),
    ("missing", "cannot download HubHop's presets .*HTTP Error 404"),
    *[(case, error) for case, (_, error) in sorted(NOT_THE_DATABASE.items())],
])
def test_a_failed_download_keeps_the_saved_database(tmp_path, server, path, error):
    out = tmp_path / "saved.json"
    out.write_text("good", encoding="utf-8")
    with pytest.raises(SystemExit, match=f"(?s){error}.*saved.json is unchanged"):
        hubhop.main(["-o", str(out), "--url", server + path])
    assert out.read_text(encoding="utf-8") == "good"


def test_a_database_without_a_tables_preset_is_saved_with_the_error(tmp_path, server):
    out = tmp_path / "saved.json"
    with pytest.raises(SystemExit, match=f"saved {re.escape(str(out))}, but these names do not name exactly one"):
        hubhop.main(["-o", str(out), "--url", server + "empty"])
    assert out.read_text(encoding="utf-8") == "[]"


def test_a_database_that_cannot_be_saved(tmp_path, server):
    with pytest.raises(SystemExit, match="cannot save HubHop's presets"):
        hubhop.main(["-o", str(tmp_path / "missing" / "saved.json"), "--url", server + "db"])


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
    # ButtonInputConfig, MSFS2020CustomInputAction {Command, PresetId}
    project = json.loads(profile.dumps(build(key=key)))
    assert tuple(project) == ("Name", "Sim", "Features", "Aircraft", "ConfigFiles", "_version")
    assert project["_version"] == "0.10" and project["Sim"] == "msfs" and project["Aircraft"] == []
    assert project["Features"] == {"FSUIPC": False, "ProSim": False}
    [config_file] = project["ConfigFiles"]
    assert {k: v for k, v in config_file.items() if k != "ConfigItems"} == {
        "Label": "Avionics Panel", "FileName": None, "ReferenceOnly": False, "EmbedContent": True}
    by_id = {p["id"]: p for p in DATABASE}
    serials = {serial: device for device, (_, serial) in PANEL.items()}
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
        acts = [button[event] for event in ("onPress", "onRelease") if button[event] is not None]
        assert acts
        for act in acts:
            assert tuple(act) == ("Type", "Command", "PresetId") and act["Type"] == "MSFS2020CustomInputAction"
            assert act["Command"] == by_id[act["PresetId"]]["code"]
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
def test_other_joysticks_change_only_the_controllers(key):
    panel, vjoy = profile.dumps(build(PANEL, key)), profile.dumps(build(VJOY, key))
    assert vjoy != panel
    for device in (1, 2):
        for i in (0, 1):
            vjoy = vjoy.replace(json.dumps(VJOY[device][i]), json.dumps(PANEL[device][i]))
    assert vjoy == panel


def test_release_events_are_written():
    class Family:
        NAME = "test"
        DEVICE = {1: {"AP": {"press": "Microsoft.G1000 (2024).AP - Toggle",
                             "release": "Microsoft.G1000 (2024).HDG - Toggle"}},
                  2: {"ENT": {"release": "Microsoft.Generic.AS1000_MFD_ENT_Push"}}}
    first, second = items(profile.build(Family, PANEL, PRESETS))
    assert first["Name"] == "AP: AP - Toggle"
    assert first["button"]["onRelease"]["Command"] == "(Microsoft.G1000 (2024).HDG - Toggle)"
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


def test_a_generated_project_reads_back_its_joysticks(tmp_path):
    out = tmp_path / "out.mfproj"
    out.write_text(profile.dumps(build(VJOY)), encoding="utf-8")
    assert profile.controllers_from(str(out)) == VJOY


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
def test_command_line_from_a_saved_project(tmp_path, database, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.main(["--family", "g1000", "--from", saved(tmp_path, (*PANEL[1], 83), (*PANEL[2], 10)),
              "--hubhop", database])
    assert (tmp_path / "g1000.mfproj").read_text(encoding="utf-8") == profile.dumps(build())
    assert "unmapped (the reasons are in mobiflight/families/g1000.py): TEST, ARM" in capsys.readouterr().err


def test_command_line_with_serials(tmp_path, database):
    out = tmp_path / "out.mfproj"
    cli.main(["--family", "g1000", "--serials", PANEL[1][1], PANEL[2][1].upper(), "--hubhop", database,
              "-o", str(out)])
    assert out.read_text(encoding="utf-8") == profile.dumps(build())


@pytest.mark.parametrize("args", [
    [],
    ["--serials", PANEL[1][1]],
    ["--serials", PANEL[1][1], PANEL[2][1], "--from", "x"],
    ["--serials", PANEL[1][1], PANEL[1][1]],
    ["--serials", "JS-x", PANEL[2][1]],
    ["--from", "missing.mfproj"],
    ["--serials", PANEL[1][1], PANEL[2][1], "--hubhop", "missing.json"],
])
def test_command_line_errors(tmp_path, database, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    hubhop_file = [] if "--hubhop" in args else ["--hubhop", database]
    with pytest.raises(SystemExit):
        cli.main(["--family", "g1000", *hubhop_file, *args])
    assert not os.listdir(tmp_path) or os.listdir(tmp_path) == ["hubhop-presets.json"]


def test_command_line_with_a_file_that_is_not_the_database(tmp_path, capsys):
    path = tmp_path / "presets.json"
    path.write_bytes(NOT_THE_DATABASE["no_vendor"][0])
    with pytest.raises(SystemExit):
        cli.main(["--family", "g1000", "--serials", PANEL[1][1], PANEL[2][1], "--hubhop", str(path),
                  "-o", str(tmp_path / "out.mfproj")])
    assert "is not HubHop's preset database" in capsys.readouterr().err
    assert not (tmp_path / "out.mfproj").exists()


# ---------------- workflows (docs/using/controls.md) through the panel and the G1000 profile ----------------
def sent(sim):
    """The presets MobiFlight sends for what it saw go down on both joysticks, in order per device (an unmapped
    button sends none)"""
    by_button = {(item["Controller"]["Serial"], item["Device"]["Name"]): item["button"]["onPress"]["Command"]
                 for item in items(build())}
    assert sim.held(1) == [] and sim.held(2) == []
    out = ([], [])
    for device in (1, 2):
        for name in sim.presses(device):
            command = by_button.get((PANEL[device][1], f"Button {BM.BUTTON[device][name] + 1}"))
            if command:
                out[device - 1].append(command[1:-1])      # the made-up code is the preset's name in ()
    return out


GEN = "Microsoft.Generic."


def test_g1000_tune_com1_and_swap():
    sim = Sim()
    sim.turn("FREQ_OUTER", 2)
    sim.turn("FREQ_INNER", -3)
    sim.tap("COM_SWAP")
    assert sent(sim) == ([GEN + "COM_RADIO_WHOLE_INC"] * 2 + [GEN + "COM_RADIO_FRACT_DEC"] * 3
                         + [GEN + "COM1_RADIO_SWAP"], [])


def test_g1000_tune_com2_and_swap():
    # SHIFT, HOME (UNIT) first: radio 2
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("HOME")
    sim.turn("FREQ_INNER", 2)
    sim.tap("COM_SWAP")
    assert sent(sim) == ([], [GEN + "COM2_RADIO_FRACT_INC"] * 2 + [GEN + "COM2_RADIO_SWAP"])


def test_g1000_tune_nav1():
    sim = Sim()
    sim.tap("FREQ_PUSH")
    sim.turn("FREQ_OUTER", 1)
    sim.turn("FREQ_INNER", 1)
    sim.tap("NAV_SWAP")
    assert sent(sim) == ([GEN + "NAV1_RADIO_WHOLE_INC", GEN + "NAV1_RADIO_FRACT_INC", GEN + "NAV1_RADIO_SWAP"], [])


def test_g1000_tune_nav2():
    # in unit 2 the FREQ push, the turns and NAV ⇆ come from device 2: NAV 2
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("HOME")
    sim.tap("FREQ_PUSH")
    sim.turn("FREQ_OUTER", -1)
    sim.turn("FREQ_INNER", 1)
    sim.tap("NAV_SWAP")
    assert sent(sim) == ([], [GEN + "NAV2_RADIO_WHOLE_DEC", GEN + "NAV2_RADIO_FRACT_INC", GEN + "NAV2_RADIO_SWAP"])


def test_g1000_squawk_and_ident():
    # 1200 to 7000, then SHIFT, VFR (IDENT)
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("FREQ_INNER", 6)
    sim.turn("FREQ_OUTER", 1)
    sim.turn("FREQ_INNER", -2)
    sim.wait(3500)
    sim.tap("SHIFT")
    sim.tap("VFR")
    assert sent(sim) == ([GEN + "XPNDR_1000_INC"] * 6 + [GEN + "XPNDR_100_DEC"] * 2 + [GEN + "TransponderIDT"], [])


def test_g1000_after_takeoff():
    # SHIFT, FD (YD), then AP
    sim = Sim()
    sim.tap("SHIFT")
    sim.tap("FD")
    sim.tap("AP")
    assert sent(sim) == ([GEN + "YAW_DAMPER_TOGGLE", "Microsoft.G1000 (2024).AP - Toggle"], [])
