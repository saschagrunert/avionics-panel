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
  unit 1 or unit 2; one that has both units (the G1000's MFD and PFD, the G3X Touch's displays) fills both. An
  aircraft whose own selection puts any of several navigators in a unit (Black Square's Bonanza, by its tablet) joins
  them there (joined()).

Every profile is compose()'s: one autopilot, one cockpit and the navigators of both units (one part for both, or
one for each), an aircraft's own rows over them.
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
GPS_DISTANCE = "(A:GPS WP DISTANCE, nmiles)"   # the sim's distance to the active waypoint, which most navigators write
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


def part(key, name, kind, device, unmapped, units=(1, 2), **extra):
    """A part: its key (as the generator and the zip name it), NAME (the avionics) and TITLE (with its kind, and a
    navigator of one unit with the unit), KIND, UNITS (a navigator's) and its DEVICE and UNMAPPED tables, which
    must cover its scope() exactly, and extra's attributes (a navigator's DISTANCES and REQUIRED_VS, an autopilot's
    VNV, compose()). An autopilot's VNV fills its VNV and SHIFT, VNV rows, alike, with the code of its defaults:
    alone() and compose() give it the distances it reads."""
    if kind == "autopilot" and extra.get("VNV"):
        vnv = extra["VNV"]()
        device = {**device, 1: {**device.get(1, {}), "VNV": vnv, "S_VNV": vnv}}
    want = scope(kind, units)
    for d in (1, 2):
        rows, rest = set(device.get(d, {})), set(unmapped.get(d, {}))
        if rows & rest or rows | rest != set(want[d]):
            raise ValueError(f"{key}: device {d} covers {sorted(rows | rest)} with {sorted(rows & rest)} twice, "
                             f"not {sorted(want[d])}")
    title = f"{name} in unit {units[0]}" if kind == "navigator" and len(units) == 1 else f"{name} {kind}"
    return SimpleNamespace(KEY=key, NAME=name, TITLE=title, KIND=kind, UNITS=tuple(units),
                           DEVICE={d: dict(device.get(d, {})) for d in (1, 2)},
                           UNMAPPED={d: dict(unmapped.get(d, {})) for d in (1, 2)}, **extra)


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


def navigator(key, name, rows, unmapped, unit, distances=(GPS_DISTANCE,)):
    """A navigator of one unit, from its rows and unmapped buttons as unit 1 has them; distances: the RPN reads of
    its distance to the active waypoint (compose()), by default the sim's GPS WP DISTANCE, which Working Title's
    navigators write from their flight plans"""
    return part(f"{key}-unit{unit}", name, "navigator", place(rows, unit), place(unmapped, unit), (unit,),
                DISTANCES=tuple(distances))


def _sent(entry, event):
    """What an entry sends on this event ("press", "release", "long"), or None: a code alone is sent on press"""
    if isinstance(entry, str):
        return entry if event == "press" else None
    return entry.get(event)


def _joined(entries):
    """The entries of several navigators for one button as one: each event's codes in their order. Where one tells a
    tap from a hold ("long"), a release after a hold sends its "long" and the others' plain release: their key-up
    goes out on every release (profile.actions sends "release" after a tap only)."""
    if all(isinstance(e, str) for e in entries):
        return " ".join(entries)
    held = any(_sent(e, "long") for e in entries)
    out = {}
    for event in ("press", "release", "long"):
        codes = [code for e in entries
                 if (code := _sent(e, event) or (event == "long" and held and _sent(e, "release")))]
        if codes:
            out[event] = " ".join(codes)
    return out


def joined(key, name, *navigators, rows=None, reasons=None):
    """Navigators of one unit at once, as an aircraft that puts any of them there: a button sends the codes of every
    one that maps it, in their order, each event apart (a key's press and release), and one that none maps keeps the
    first one's reason. As unit 1 has them (navigator()), rows replace buttons, and reasons replace the reasons of
    buttons none of them maps (a reason over a navigator's code would hide what it gains later), none in both.
    DISTANCES are theirs, in their order, each once, the sim's GPS WP DISTANCE last; a navigator with a REQUIRED_VS
    is refused, as nothing would read it (none of one unit has one today: the G1000 NXi's is of both units)."""
    found = {p.UNITS for p in navigators}
    if len(found) != 1 or any(p.KIND != "navigator" or len(p.UNITS) != 1 for p in navigators):
        raise ValueError(f"{key}: joins navigators of one unit, not {', '.join(p.KEY for p in navigators)}")
    if any(getattr(p, "REQUIRED_VS", None) for p in navigators):
        raise ValueError(f"{key}: a joined navigator's REQUIRED_VS would go unread")
    (units,) = found
    (unit,) = units
    both = sorted(set(rows or {}) & set(reasons or {}))
    if both:
        raise ValueError(f"{key}: {both} both mapped and unmapped")
    stray = sorted((set(rows or {}) | set(reasons or {})) - set(UNIT) - set(MAP))
    if stray:
        raise ValueError(f"{key}: {stray} are no buttons of a unit as unit 1 has them (UNIT, MAP: PAN_UP, not "
                         "S_PAN_UP)")
    device, rest = {1: {}, 2: {}}, {1: {}, 2: {}}
    for d, buttons in scope("navigator", units).items():
        for button in buttons:
            entries = [p.DEVICE[d][button] for p in navigators if button in p.DEVICE[d]]
            if entries:
                device[d][button] = _joined(entries)
            else:
                rest[d][button] = next(p.UNMAPPED[d][button] for p in navigators)
    for d, own in place(rows or {}, unit).items():
        for button, entry in own.items():
            rest[d].pop(button, None)
            device[d][button] = entry
    for d, own in place(reasons or {}, unit).items():
        for button, reason in own.items():
            if button in device[d]:
                raise ValueError(f"{key}: {button} is a navigator's, not for a reason")
            rest[d][button] = reason
    distances = gps_last(r for p in navigators for r in getattr(p, "DISTANCES", ()))
    return part(f"{key}-unit{unit}", name, "navigator", device, rest, units, DISTANCES=distances)


def empty(unit):
    """No navigator in this unit: radios alone, as a KX 155"""
    reason = f"no navigator in unit {unit}"
    rows = dict.fromkeys((*UNIT, *MAP), reason)
    return part(f"none-unit{unit}", "none", "navigator", {}, place(rows, unit), (unit,), DISTANCES=())


def gps_last(reads):
    """Distance reads (RPN) each once, in their order, but the sim's GPS WP DISTANCE last, if it is among them: of
    navigators that one unit may hold any of (joined()), or of every navigator (families/__init__.py), none of which
    goes first"""
    reads = dict.fromkeys(reads)
    return (*(r for r in reads if r != GPS_DISTANCE), *((GPS_DISTANCE,) if GPS_DISTANCE in reads else ()))


def distances(*navigators):
    """The distances VNV reads with these navigators (compose()): their own, unit 1's first, each once, then the
    sim's GPS WP DISTANCE if none of them gave it; unit 1's GPS WP DISTANCE stays ahead of unit 2's own, unlike
    gps_last()"""
    reads = [d for p in sorted(navigators, key=lambda p: p.UNITS) for d in getattr(p, "DISTANCES", ())]
    return tuple(dict.fromkeys((*reads, GPS_DISTANCE)))


def alone(autopilot, distances):
    """An autopilot part as offered alone (the parts zip, families/__init__.py), not knowing its navigator: its VNV,
    if it has one, reads these distances, and VNV and SHIFT, VNV send it alike; compose() gives a profile the
    distances of its navigators instead"""
    if not getattr(autopilot, "VNV", None):
        return autopilot
    vnv = autopilot.VNV(distances=distances)
    device = {1: {**autopilot.DEVICE[1], "VNV": vnv, "S_VNV": vnv}, 2: dict(autopilot.DEVICE[2])}
    return SimpleNamespace(**{**vars(autopilot), "DEVICE": device})


def compose(name, *parts, rows=None, unmapped=None, **extra):
    """The profile of these parts, one of each kind and navigators for both units: NAME, DEVICE and UNMAPPED
    (families/__init__.py), PARTS (their kinds and keys, as "cockpit-g1000") and extra's attributes. No two parts
    cover a button: part() holds each part to its kind's scope, and the scopes do not overlap. An aircraft's own rows
    ({device: {button: entry}}) and unmapped buttons ({device: {button: reason}}) replace the parts' for those
    buttons, as its own lights. An autopilot whose VNV reads the navigator's distance (its VNV: the code of
    distances= and required=, for VNV and SHIFT, VNV alike) gets the distances the navigators give (DISTANCES), unit
    1's first, then the sim's GPS WP DISTANCE if none gave it, and the REQUIRED_VS of the first navigator with one,
    unit 1's first: no profile reads a variable of a navigator it lacks, which another aircraft of the session may
    have left."""
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
    vnv = [p.VNV for p in parts if getattr(p, "VNV", None)]
    if vnv:
        navigators = sorted((p for p in parts if p.KIND == "navigator"), key=lambda p: p.UNITS)
        required = next((p.REQUIRED_VS for p in navigators if getattr(p, "REQUIRED_VS", None)), None)
        device[1]["VNV"] = device[1]["S_VNV"] = vnv[0](distances=distances(*navigators), required=required)
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
