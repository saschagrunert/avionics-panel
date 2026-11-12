"""The MobiFlight project (.mfproj) for one avionics family, for both joysticks.

The format is MobiFlight 11's JSON project, schema "_version" 0.10, as MobiFlight 11.3.1 reads and writes it
(src/MobiFlightConnector/ in its repository: Base/Project.cs, Base/ConfigFile.cs, Base/ConfigItem.cs,
Base/Controller.cs, MobiFlight/InputConfigItem.cs, MobiFlight/InputConfig/ButtonInputConfig.cs and
MSFS2020CustomInputAction.cs; the shape is that of its Joysticks/wingflex/projects/msfs/*.mfproj). Every
button is one InputConfigItem: the joystick as Controller {Name, Serial "JS-" + DirectInput instance GUID},
the button as Device {"Type": "Button", "Name": "Button N"} (N from 1, as BUTTONS.md numbers them), and its
actions as MSFS2020CustomInputAction {Command, PresetId}, which MobiFlight 11 uses for MSFS 2020 and 2024.
MobiFlight matches an event to an item by the serial and the button name; on loading it binds the project's
controllers to the connected ones by name and serial. With onLongRelease empty it runs onRelease however long
the button was held (ButtonInputConfig.ResolveDispatchedEvent), which a key held on purpose relies on.
"""
import importlib.util
import json
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = "0.10"
NAME = "Avionics Panel"          # both joysticks' DirectInput instance name (boot.py)
# the item GUIDs depend on the family, device and button only, so a project for other joysticks differs from
# this one in the controllers alone
ITEMS = uuid.uuid5(uuid.NAMESPACE_URL, "avionics-panel/mobiflight")
SERIAL = re.compile(r"JS-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
BUTTON = re.compile(r"Button ([0-9]+)")
EVENTS = {"press": "onPress", "release": "onRelease"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BM = _load("_mobiflight_buttonmap", os.path.join(HERE, "..", "firmware", "buttonmap.py"))


def key(preset):
    """How the tables name a HubHop preset: vendor.aircraft.label, as HubHop's editor lists it"""
    return f"{preset['vendor']}.{preset['aircraft']}.{preset['label']}"


def actions(entry):
    """A table entry -> {"onPress": preset name, "onRelease": preset name}, without the events that send
    nothing. An entry is a preset name (sent on press) or a dict with "press" and/or "release"."""
    if isinstance(entry, str):
        entry = {"press": entry}
    if not entry or set(entry) - set(EVENTS):
        raise ValueError(f"not a table entry: {entry!r}")
    return {EVENTS[event]: name for event, name in entry.items()}


def serial(text):
    """ "JS-<guid>", checked, with the GUID in lower case as .NET prints it"""
    out = text[:3] + text[3:].lower()
    if not SERIAL.fullmatch(out):
        raise ValueError(f"not a joystick serial (JS- and the DirectInput instance GUID): {text!r}")
    return out


def build(family, controllers, presets):
    """The project as a dict. controllers: {1: (name, serial), 2: (name, serial)}; presets: preset name ->
    HubHop preset, for every name the family uses (hubhop.lookup)."""
    items = []
    for device in (1, 2):
        name, joystick = controllers[device]
        for button, entry in sorted(family.DEVICE[device].items(), key=lambda kv: BM.BUTTON[device][kv[0]]):
            acts = {event: presets[preset] for event, preset in actions(entry).items()}
            first = acts.get("onPress", acts.get("onRelease"))
            button_config = dict.fromkeys(("onPress", "onRelease", "onLongRelease", "onHold"))
            button_config.update({event: {"Type": "MSFS2020CustomInputAction", "Command": p["code"],
                                          "PresetId": p["id"]} for event, p in acts.items()})
            button_config.update(LongReleaseDelay=350, HoldDelay=350, RepeatDelay=0)
            items.append({
                "GUID": str(uuid.uuid5(ITEMS, f"{family.NAME}/{device}/{button}")),
                "Active": True,
                "Name": f"{button}{', unit 2' if device == 2 else ''}: {first['label']}",
                "Type": "InputConfigItem",
                "Controller": {"Name": name, "Serial": serial(joystick)},
                "Device": {"Type": "Button", "Name": f"Button {BM.BUTTON[device][button] + 1}"},
                "button": button_config,
            })
    return {
        "Name": f"{NAME}: {family.NAME}",
        "Sim": "msfs",
        "Features": {"FSUIPC": False, "ProSim": False},
        "Aircraft": [],
        "ConfigFiles": [{"Label": NAME, "FileName": None, "ReferenceOnly": False, "EmbedContent": True,
                         "ConfigItems": items}],
        "_version": SCHEMA,
    }


def dumps(project):
    return json.dumps(project, indent=2, ensure_ascii=False) + "\n"


def controllers_from(path):
    """{1: (name, serial), 2: (name, serial)} from a project saved in MobiFlight with ENT bound in unit 1
    (device 1, Button 83) and in unit 2 (device 2, Button 10). The two are the joysticks of one name of which
    one has a button bound above device 2's last (device 1) and the other not; other joysticks may be bound
    too, and if they form such a pair as well, the one named like the panel wins."""
    with open(path, encoding="utf-8-sig") as f:
        project = json.load(f)
    found = {}                   # (name, serial) -> button numbers bound to it
    for config_file in project.get("ConfigFiles") or []:
        for item in config_file.get("ConfigItems") or []:
            controller, device = item.get("Controller") or {}, item.get("Device") or {}
            match = BUTTON.fullmatch(device.get("Name") or "")
            if item.get("Type") == "InputConfigItem" and SERIAL.fullmatch(controller.get("Serial") or "") and match:
                found.setdefault((controller.get("Name"), controller["Serial"]), set()).add(int(match[1]))
    pairs = {}
    for name in {c[0] for c in found}:
        joysticks = [c for c in found if c[0] == name]
        high = [c for c in joysticks if max(found[c]) > BM.SIZE[2]]
        if len(joysticks) == 2 and len(high) == 1:
            pairs[name] = {1: high[0], 2: next(c for c in joysticks if c != high[0])}
    if len(pairs) > 1 and NAME in pairs:
        pairs = {NAME: pairs[NAME]}
    if len(pairs) != 1:
        raise ValueError(f"{path}: need ENT bound on both joysticks of the panel, in unit 1 (Button 83) and in "
                         f"unit 2 (Button 10); found {len(pairs)} such pairs of joysticks")
    return next(iter(pairs.values()))
