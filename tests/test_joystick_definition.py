"""MobiFlight's joystick definition of the panel (mobiflight/joystick.py): valid against MobiFlight's schema, named
as the panel's joysticks are, a label for each button by its BUTTONS.md names on both devices, for the button names
MobiFlight and the profiles use, and written the same each time.

mfjoystick.schema.json is MobiFlight's src/MobiFlightConnector/Joysticks/mfjoystick.schema.json (MobiFlight-Connector,
MIT licence: mfjoystick.schema-LICENSE), as MobiFlight 11.3.1 ships it, with a final newline added; 11.2.0 ships the
same. MobiFlight validates a definition with Newtonsoft's JSON Schema (JsonBackedObject.LoadFromFile); validate() below
checks the keywords the schema uses, and fails on one it does not know, so a newer schema that needs more shows here."""
import json
import os
import re

import buttonmap as BM
import pytest

from mobiflight import __main__ as cli
from mobiflight import joystick, profile
from mobiflight.families import FAMILIES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "tests", "mfjoystick.schema.json"), encoding="utf-8") as f:
    SCHEMA = json.load(f)
TYPES = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float)}
NOTES = {"$id", "$schema", "title", "description", "default", "definitions"}     # keywords that check nothing


def validate(value, schema, where="$"):
    """Raises AssertionError where value breaks the schema"""
    known = NOTES | {"type", "required", "properties", "items", "enum", "pattern", "dependentRequired"}
    assert set(schema) <= known, f"{where}: keywords this check does not know: {sorted(set(schema) - known)}"
    if "type" in schema:
        kind = schema["type"]
        assert isinstance(value, TYPES[kind]) and not isinstance(value, bool), f"{where}: not a {kind}"
    if "enum" in schema:
        assert value in schema["enum"], f"{where}: {value!r} not in {schema['enum']}"
    if "pattern" in schema and isinstance(value, str):
        assert re.search(schema["pattern"], value), f"{where}: {value!r} does not match {schema['pattern']}"
    if isinstance(value, dict):
        for name in schema.get("required", ()):
            assert name in value, f"{where}: {name} missing"
        for name, needs in schema.get("dependentRequired", {}).items():
            assert name not in value or all(n in value for n in needs), f"{where}: {name} needs {needs}"
        for name, sub in schema.get("properties", {}).items():
            if name in value:
                validate(value[name], sub, f"{where}.{name}")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            validate(item, schema["items"], f"{where}[{i}]")


def test_the_definition_is_valid_against_mobiflights_schema():
    validate(joystick.definition(), SCHEMA)


def test_the_check_catches_what_mobiflight_refuses():
    good = joystick.definition()
    for bad in ({"Inputs": []}, {**good, "InstanceName": 1}, {**good, "Inputs": [{"Id": 1, "Type": "Button"}]},
                {**good, "Inputs": [{"Id": "1", "Type": "Button", "Label": "x"}]},
                {**good, "Inputs": [{"Id": 1, "Type": "Key", "Label": "x"}]},
                {**good, "Outputs": [{"Id": "led", "Label": "LED", "Byte": 0}]}):
        with pytest.raises(AssertionError):
            validate(bad, SCHEMA)
    with pytest.raises(AssertionError, match="keywords"):
        validate({}, {"minItems": 1})


def test_the_definition_is_found_by_the_panels_name_alone():
    # MobiFlight matches InstanceName to the joystick's name, which boot.py gives both devices; without IDs, it
    # labels no other Pico that runs CircuitPython
    d = joystick.definition()
    assert d["InstanceName"] == profile.NAME == "Avionics Panel"
    with open(os.path.join(ROOT, "firmware", "boot.py"), encoding="utf-8") as f:
        assert f'usb_hid.set_interface_name("{profile.NAME}")' in f.read()
    assert "VendorId" not in d and "ProductId" not in d and "Outputs" not in d


def test_every_button_is_labelled_by_its_names_on_both_devices(buttons_md):
    # one input per button device 1 sends, numbered from 1 as MobiFlight and BUTTONS.md number them; its label
    # names it on device 1 and, where device 2 has the button, on device 2 (unit 2); the others are device 1's alone
    names = {(d, number): name for d, numbers in buttons_md.items() for name, number in numbers.items()}
    inputs = joystick.definition()["Inputs"]
    assert [i["Id"] for i in inputs] == list(range(1, len(BM.DEVICE[1]) + 1))
    for i in inputs:
        n = i["Id"]
        want = f"Button {n}: {names[1, n]} | " + (f"unit 2: {names[2, n]}" if (2, n) in names else "device 1 only")
        assert i["Type"] == "Button" and i["Label"] == want, n
    assert inputs[0]["Label"] == "Button 1: AP | unit 2: CDI"
    assert inputs[82]["Label"] == "Button 83: ENT | device 1 only"
    assert inputs[9]["Label"] == "Button 10: DN | unit 2: ENT"


def test_the_labels_go_to_the_buttons_the_profiles_map():
    # MobiFlight names an input "<Type> <Id>" (JoystickInput.Name), as a project names its button: every button a
    # profile maps has a label that names it on its device
    labels = {f"{i['Type']} {i['Id']}": i["Label"] for i in joystick.definition()["Inputs"]}
    for key, family in FAMILIES.items():
        for config_file in profile.build(family)["ConfigFiles"]:
            for item in config_file["ConfigItems"]:
                device = int(item["Controller"]["Serial"][-1])
                button = item["Name"].split(":")[0].removesuffix(", unit 2")
                label = labels[item["Device"]["Name"]]
                named = label.split(" | ")[0].split(": ")[1] if device == 1 else label.split("unit 2: ")[1]
                assert named == button, (key, item["Name"])


def test_the_command_writes_the_definition(tmp_path):
    out, again = tmp_path / "avionics-panel.joystick.json", tmp_path / "again.joystick.json"
    cli.main(["--joystick-definition", str(out)])
    cli.main(["--joystick-definition", str(again)])
    assert out.read_bytes() == again.read_bytes() == joystick.dumps(joystick.definition()).encode()
    assert json.loads(out.read_text(encoding="utf-8")) == joystick.definition()


def test_a_failed_write_leaves_no_definition(tmp_path, monkeypatch):
    def fail(definition):
        raise ValueError("no definition")
    monkeypatch.setattr(joystick, "dumps", fail)
    with pytest.raises(SystemExit):
        cli.main(["--joystick-definition", str(tmp_path / "x.joystick.json")])
    assert not os.listdir(tmp_path)


@pytest.mark.parametrize("args", [
    ["--joystick-definition", "avionics-panel.json"],
    ["--joystick-definition", "x.joystick.json", "--vfr", "1200"],
    ["--joystick-definition", "x.joystick.json", "-o", "y.joystick.json"],
    ["--joystick-definition", "x.joystick.json", "--from", "guids.mfproj"],
    ["--joystick-definition", "x.joystick.json", "--cards", "x.zip"],
    ["--joystick-definition", "missing/x.joystick.json"],
])
def test_command_line_errors_with_the_definition(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(args)
    assert not os.listdir(tmp_path)
