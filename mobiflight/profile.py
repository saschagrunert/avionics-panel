"""The MobiFlight project (.mfproj) of a profile or of an avionics part, for both joysticks.

The format is MobiFlight's JSON project, schema "_version" 0.10 (MobiFlight 11.2 and newer; 11.1 reads 0.9 and loads a
newer project unmigrated), as MobiFlight 11.3.1 reads and writes it (src/MobiFlightConnector/ in its repository:
Base/Project.cs, Base/ConfigFile.cs, Base/ConfigItem.cs, Base/Controller.cs, MobiFlight/InputConfigItem.cs,
MobiFlight/InputConfig/ButtonInputConfig.cs and MSFS2020CustomInputAction.cs; the shape is that of its
Joysticks/wingflex/projects/msfs/*.mfproj). Every button is one InputConfigItem: the joystick as Controller {Name,
Serial "JS-" + DirectInput instance GUID}, the button as Device {"Type": "Button", "Name": "Button N"} (N from 1, as
BUTTONS.md numbers them), and its actions as MSFS2020CustomInputAction {Command}, which MobiFlight 11 uses for MSFS 2020
and 2024. Without a PresetId, MobiFlight runs the Command as it is and shows it as custom code. With onLongRelease empty
it runs onRelease however long the button was held (ButtonInputConfig, ResolveDispatchedEvent from 11.3, alike in 11.2),
which a key held on purpose relies on; with onLongRelease it runs that one instead for a button held longer than
LongReleaseDelay (LONG_MS), so a key tells a tap from a hold.

MobiFlight matches an event to an item by the serial and the button name. On loading a project it binds each of
its controllers to a connected one (Controllers/ControllerAutoBinder.cs): the one of the same name and serial,
else the one connected controller of its name. Where two connected controllers have that name, as the panel's
joysticks do, it asks for the binding instead (Extras, Controller Bindings). A project made without the user's
GUIDs names both joysticks as the panel does, each with a serial that says which device it is (UNBOUND), so
MobiFlight asks once for both.

A stamp in the project's name, as "Avionics Panel: G1000 NXi (2026-11-14, 5d1c305)", says which commit made it:
the one firmware/version.py names in a release's files (VERSION), or any other text. The item GUIDs leave it out,
as they leave out the joysticks.
"""
import importlib.util
import json
import os
import re
import uuid

from mobiflight.families import parts

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = "0.10"
NAME = "Avionics Panel"          # both joysticks' DirectInput instance name (boot.py)
UNBOUND = {1: (NAME, "JS-device-1"), 2: (NAME, "JS-device-2")}
# the item GUIDs depend on the profile's name or the part's title, the device and the button only, so a project for
# other joysticks differs from this one in the controllers alone
ITEMS = uuid.uuid5(uuid.NAMESPACE_URL, "avionics-panel/mobiflight")
SERIAL = re.compile(r"JS-[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
BUTTON = re.compile(r"Button ([0-9]+)")
EVENTS = {"press": "onPress", "release": "onRelease", "long": "onLongRelease", "hold": "onHold"}
LONG_MS = 350                    # a button held longer than this is a hold: onLongRelease, not onRelease
HOLD_MS = 350                    # MobiFlight's default for onHold
# what a code sets: (>K:EVENT), (>K:2:EVENT), (>A:VARIABLE, unit) and so on
WRITES = re.compile(r"\(>[ABHKL]:(?:2:)?([^),]+)[^)]*\)")


def filename(key=None):
    """A project's file name: a profile's or a part's by its key (as "g1000" or "autopilot-kap140"), as the
    downloads, the parts zip and the cards name it and the command line writes it by default; without a key, one
    of the parts given on the command line"""
    return f"avionics-panel-{key}.mfproj" if key else "avionics-panel.mfproj"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BM = _load("_mobiflight_buttonmap", os.path.join(HERE, "..", "firmware", "buttonmap.py"))


VERSION_PY = os.path.join(HERE, "..", "firmware", "version.py")


def version(path=VERSION_PY):
    """The commit of these files as firmware/version.py names it ("2026-11-14, 5d1c305"), which git archive (a
    release's source code) and windows/make_zip.py fill in; None in a git checkout, which keeps the placeholder"""
    text = str(getattr(_load("_mobiflight_version", path), "VERSION", "$")) if os.path.isfile(path) else "$"
    return None if text.startswith("$") else text


VERSION = version()


def actions(entry):
    """A table entry -> {"onPress": code, "onRelease": code, "onLongRelease": code, "onHold": code}, without the events
    that send nothing. An entry is a code (sent on press) or a dict with "press", "release", "long" (sent on a release
    after a hold, when "release" goes after a tap only) and/or "hold" (sent once when held HoldDelay, still down:
    button_config())."""
    if isinstance(entry, str):
        entry = {"press": entry}
    if not entry or set(entry) - set(EVENTS):
        raise ValueError(f"not a table entry: {entry!r}")
    return {EVENTS[event]: code for event, code in entry.items()}


def label(code):
    """What a code is named by in MobiFlight's list: the events and variables it sets, each once (an item's
    codes joined: its press, release and long release)"""
    return ", ".join(dict.fromkeys(WRITES.findall(code)))


def lowered(text):
    """A serial with its GUID in lower case, as .NET prints it"""
    return text[:3] + text[3:].lower()


def serial(text):
    """ "JS-<guid>", checked, with the GUID in lower case as .NET prints it"""
    out = lowered(text)
    if not SERIAL.fullmatch(out):
        raise ValueError(f"not a joystick serial (JS- and the DirectInput instance GUID): {text!r}")
    return out


def tables(family, vfr=None):
    """A profile's or a part's DEVICE tables, {1: {button: entry}, 2: {button: entry}}, with the VFR key's squawk
    vfr in place of the one in the family's table (None: that one); ValueError for a code that is none, or for a
    family whose VFR key has no VFR toggle. The IFR-1's profiles take theirs from here too (ifr1.py)."""
    out = {1: dict(family.DEVICE[1]), 2: family.DEVICE[2]}
    if vfr is not None:
        parts.vfr(vfr)                                        # a wrong code fails first
        toggle = parts.vfr_toggle(out[1].get("VFR"))
        if not toggle:
            raise ValueError(f"the VFR key of {family.NAME} has no VFR toggle")
        out[1]["VFR"] = parts.vfr(vfr, toggle["alt"])        # with the family's way to select ALT
    return out


def button_config(acts, long_delay=LONG_MS, hold_delay=HOLD_MS):
    """An item's "button": its actions ({"onPress": code, ...}, actions()) as custom code, the others null, and the
    delays (long_delay: of onLongRelease, hold_delay: of onHold)"""
    config = dict.fromkeys(("onPress", "onRelease", "onLongRelease", "onHold"))
    config.update({event: {"Type": "MSFS2020CustomInputAction", "Command": code} for event, code in acts.items()})
    config.update(LongReleaseDelay=long_delay, HoldDelay=hold_delay, RepeatDelay=0)
    return config


def project(name, label, items):
    """A project of these items in one embedded config file named label, as MobiFlight saves it"""
    return {
        "Name": name,
        "Sim": "msfs",
        "Features": {"FSUIPC": False, "ProSim": False},
        "Aircraft": [],
        "ConfigFiles": [{"Label": label, "FileName": None, "ReferenceOnly": False, "EmbedContent": True,
                         "ConfigItems": items}],
        "_version": SCHEMA,
    }


def build(family, controllers=UNBOUND, vfr=None, stamp=None):
    """The project of a profile or a part (families/) as a dict. controllers: {1: (name, serial), 2: (name,
    serial)}, the user's joysticks or UNBOUND. vfr: the squawk the VFR key sets (tables()). stamp: the text in
    brackets after the project's name, as the commit (None: none). A part's project names it in its label, which
    MobiFlight shows as the tab it adds."""
    part = hasattr(family, "KIND")             # a part, as a tab of its own beside others: named in its label
    title = family.TITLE if part else family.NAME
    device_tables = tables(family, vfr)
    items = []
    for device in (1, 2):
        name, joystick = controllers[device]
        for button, entry in sorted(device_tables[device].items(), key=lambda kv: BM.BUTTON[device][kv[0]]):
            acts = actions(entry)
            items.append({
                "GUID": str(uuid.uuid5(ITEMS, f"{title}/{device}/{button}")),
                "Active": True,
                "Name": f"{button}{', unit 2' if device == 2 else ''}: {label(' '.join(acts.values()))}",
                "Type": "InputConfigItem",
                "Controller": {"Name": name, "Serial": joystick},
                "Device": {"Type": "Button", "Name": f"Button {BM.BUTTON[device][button] + 1}"},
                "button": button_config(acts),
            })
    return project(f"{NAME}: {title}{f' ({stamp})' if stamp else ''}", f"{NAME}: {title}" if part else NAME, items)


def dumps(project):
    return json.dumps(project, indent=2, ensure_ascii=False) + "\n"


def _field(obj, key, kind):
    """obj[key] if obj is an object and that is a kind, else kind's empty value: a saved project is read as
    it comes, a field of another type is as good as missing"""
    value = obj.get(key) if isinstance(obj, dict) else None
    return value if isinstance(value, kind) else kind()


def controllers_from(path):
    """{1: (name, serial), 2: (name, serial)} from a project saved in MobiFlight with ENT bound in unit 1
    (device 1, Button 83) and in unit 2 (device 2, Button 10). The two are the joysticks of one name of which
    one has a button bound above device 2's last (device 1) and the other not; other joysticks may be bound
    too, and if they form such a pair as well, the one named like the panel wins. A serial is matched in any
    case and kept as it was saved. ValueError for a file that is no project."""
    with open(path, encoding="utf-8-sig") as f:
        project = json.load(f)
    if not isinstance(project, dict):
        raise ValueError(f"{path}: not a MobiFlight project")
    found = {}                   # (name, serial in lower case) -> button numbers bound to it
    saved = {}                   # its key in found -> (name, serial) as first saved
    for config_file in _field(project, "ConfigFiles", list):
        for item in _field(config_file, "ConfigItems", list):
            controller, device = _field(item, "Controller", dict), _field(item, "Device", dict)
            joystick, match = _field(controller, "Serial", str), BUTTON.fullmatch(_field(device, "Name", str))
            if (_field(item, "Type", str) == "InputConfigItem" and SERIAL.fullmatch(lowered(joystick))
                    and match):
                name = controller.get("Name") if isinstance(controller.get("Name"), str) else None   # (as saved)
                key = (name, lowered(joystick))
                saved.setdefault(key, (name, joystick))
                found.setdefault(key, set()).add(int(match[1]))
    pairs = {}
    for name in {c[0] for c in found}:
        joysticks = [c for c in found if c[0] == name]
        high = [c for c in joysticks if max(found[c]) > BM.SIZE[2]]
        if len(joysticks) == 2 and len(high) == 1:
            pairs[name] = {1: saved[high[0]], 2: saved[next(c for c in joysticks if c != high[0])]}
    if len(pairs) > 1 and NAME in pairs:
        pairs = {NAME: pairs[NAME]}
    if len(pairs) != 1:
        raise ValueError(f"{path}: need ENT bound on both joysticks of the panel, in unit 1 (Button 83) and in "
                         f"unit 2 (Button 10); found {len(pairs)} such pairs of joysticks")
    return next(iter(pairs.values()))
