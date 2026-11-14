"""The avionics parts a profile is made of, and the buttons each kind of part covers.

A part maps the buttons of its kind and lists the rest of them as unmapped, with the reason; parts of different
kinds cover different buttons, so they stack: as tabs of one MobiFlight project (the parts zip) or merged into one
project (compose(), the generator's --autopilot, --cockpit and --navigator or --unit1 and --unit2).

- autopilot: the autopilot keys and their SHIFT copies, UP and DN, and the ALT/HDG knob's altitude and heading
  (with its push, the heading bug's sync);
- cockpit: the ALT/HDG knob with SHIFT (course, altimeter, STD and CRS CTR), the audio panel, the transponder, the
  lighting, and the radios and ADF of both units (FREQ knob and flip-flops);
- navigator: the unit keys (CDI, OBS, HOME and the FMS keys) and the FMS knob of a unit, and that unit's map on the
  RANGE knob: without SHIFT for unit 1, with SHIFT for unit 2. A navigator of one unit (a GNS, a GTN) goes in
  unit 1 or unit 2; one that has both units (the G1000's MFD and PFD, the G3X Touch's displays) fills both.
"""
from types import SimpleNamespace

AUTOPILOT = ("AP", "ALT", "HDG", "FD", "VS", "NAV", "UP", "FLC", "APR", "DN", "VNV", "LVL", "TEST", "ARM", "YD",
             "S_VS", "GPSS", "S_UP", "S_FLC", "BC", "S_DN", "S_VNV", "HALF_BANK", "ALT_100_UP", "ALT_100_DN",
             "ALT_1000_UP", "ALT_1000_DN", "HDG_1_UP", "HDG_1_DN", "HDG_10_UP", "HDG_10_DN", "HDG_SYNC")
RADIOS = ("COM_SWAP", "NAV_SWAP", "COM_121_5", "ADF_SWAP", "COM_MHZ_UP", "COM_MHZ_DN", "COM_KHZ_UP", "COM_KHZ_DN",
          "NAV_MHZ_UP", "NAV_MHZ_DN", "NAV_KHZ_UP", "NAV_KHZ_DN", "ADF_100_UP", "ADF_100_DN", "ADF_1_UP", "ADF_1_DN",
          "ADF_10_UP", "ADF_10_DN", "FREQ_PUSH")
COCKPIT = {
    1: ("CRS_CTR", "CRS_1_UP", "CRS_1_DN", "CRS_10_UP", "CRS_10_DN", "BARO_UP", "BARO_DN", "BARO_STD",
        "MIC1", "COM1", "MIC2", "COM2", "ADF_AUDIO", "NAV1_AUDIO", "DME_AUDIO", "NAV2_AUDIO",
        "SQK_D1_UP", "SQK_D1_DN", "SQK_D2_UP", "SQK_D2_DN", "SQK_D3_UP", "SQK_D3_DN", "SQK_D4_UP", "SQK_D4_DN",
        "IDENT", "VFR", "XPDR_MODE", "PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN", "CABIN_LT",
        *RADIOS),
    2: RADIOS,
}
UNIT = ("CDI", "OBS", "HOME", "FPL", "DIRECT", "MENU", "PROC", "CLR", "ENT", "S_ENT", "VNAV", "MSG", "NRST", "TERR",
        "MAP", "FMS_OUTER_CW", "FMS_OUTER_CCW", "FMS_INNER_CW", "FMS_INNER_CCW", "FMS_CRSR")
MAP = ("RANGE_CW", "RANGE_CCW", "PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT", "PTR")   # unit 1's; unit 2's with S_


def scope(kind, units=(1, 2)):
    """{device: (button, ...)} that a part of this kind covers; a navigator, of these units"""
    if kind == "autopilot":
        return {1: AUTOPILOT, 2: ()}
    if kind == "cockpit":
        return dict(COCKPIT)
    if kind != "navigator":
        raise ValueError(f"no such kind of part: {kind!r}")
    return {1: (*(UNIT if 1 in units else ()), *(f"{'S_' if unit == 2 else ''}{b}" for unit in units for b in MAP)),
            2: UNIT if 2 in units else ()}


def part(key, name, kind, device, unmapped, units=(1, 2)):
    """A part: its key (as the generator and the zip name it), NAME (the avionics) and TITLE (with its kind, and a
    navigator of one unit with the unit), KIND, UNITS (a navigator's) and its DEVICE and UNMAPPED tables, which
    must cover its scope() exactly"""
    want = scope(kind, units)
    for d in (1, 2):
        rows, rest = set(device.get(d, {})), set(unmapped.get(d, {}))
        if rows & rest or rows | rest != set(want[d]):
            raise ValueError(f"{key}: device {d} covers {sorted(rows | rest)} with {sorted(rows & rest)} twice, "
                             f"not {sorted(want[d])}")
    title = f"{name} in unit {units[0]}" if kind == "navigator" and len(units) == 1 else f"{name} {kind}"
    return SimpleNamespace(KEY=key, NAME=name, TITLE=title, KIND=kind, UNITS=tuple(units),
                           DEVICE={d: dict(device.get(d, {})) for d in (1, 2)},
                           UNMAPPED={d: dict(unmapped.get(d, {})) for d in (1, 2)})


def place(rows, unit):
    """A navigator's rows for one unit, written for unit 1 ({button: entry}, its map on RANGE without SHIFT), on the
    unit's device: {device: {button: entry}}; unit 2's map goes on device 1 with SHIFT"""
    out = {1: {}, 2: {}}
    for button, entry in rows.items():
        if button in MAP:
            out[1][f"{'S_' if unit == 2 else ''}{button}"] = entry
        else:
            out[unit][button] = entry
    return out


def navigator(key, name, rows, unmapped, unit):
    """A navigator of one unit, from its rows and unmapped buttons as unit 1 has them"""
    return part(f"{key}-unit{unit}", name, "navigator", place(rows, unit), place(unmapped, unit), (unit,))


def empty(unit):
    """No navigator in this unit: radios alone, as a KX 155"""
    reason = f"no navigator in unit {unit}"
    rows = dict.fromkeys((*UNIT, *MAP), reason)
    return part(f"none-unit{unit}", "none", "navigator", {}, place(rows, unit), (unit,))


def compose(name, *parts, rows=None, unmapped=None, **extra):
    """The profile of these parts, one of each kind and navigators for both units: NAME, DEVICE and UNMAPPED, as a
    family module has them (families/__init__.py), PARTS (their kinds and keys, as "cockpit-g1000") and extra's
    attributes. An aircraft's own
    rows ({device: {button: entry}}) and unmapped buttons ({device: {button: reason}}) replace the parts' for those
    buttons, as its own lights."""
    kinds = [p.KIND for p in parts]
    units = sorted(u for p in parts if p.KIND == "navigator" for u in p.UNITS)
    if sorted(kinds) != sorted(["autopilot", "cockpit", *["navigator"] * (len(kinds) - 2)]) or units != [1, 2]:
        raise ValueError(f"{name}: needs one autopilot, one cockpit and the navigators of units 1 and 2, not "
                         f"{', '.join(p.KEY for p in parts)}")
    device, rest = {1: {}, 2: {}}, {1: {}, 2: {}}
    for p in parts:
        for d in (1, 2):
            device[d].update(p.DEVICE[d])
            rest[d].update(p.UNMAPPED[d])
    for d in (1, 2):
        both = set((rows or {}).get(d, {})) & set((unmapped or {}).get(d, {}))
        if both:
            raise ValueError(f"{name}: {sorted(both)} both mapped and unmapped on device {d}")
        for button, entry in (rows or {}).get(d, {}).items():
            rest[d].pop(button, None)
            device[d][button] = entry
        for button, reason in (unmapped or {}).get(d, {}).items():
            device[d].pop(button, None)
            rest[d][button] = reason
    return SimpleNamespace(NAME=name, DEVICE=device, UNMAPPED=rest, PARTS=tuple(f"{p.KIND}-{p.KEY}" for p in parts),
                           **extra)
