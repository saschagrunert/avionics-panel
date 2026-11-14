"""The profiles, and the avionics parts most of them are made of (part.py). A profile is a namespace with

- NAME: the profile as the project names it;
- DEVICE: {1: {button: entry}, 2: {button: entry}}, by the button names of firmware/buttonmap.py. An entry is
  MobiFlight calculator code (rpn.py), sent on press, or {"press": code, "release": code, "long": code} (any may
  be left out) for a control that needs the release too, or that sends "long" instead of "release" when let go
  after a hold (profile.LONG_MS);
- UNMAPPED: {1: {button: reason}, 2: {button: reason}}, every other button of the device, with the reason it
  sends nothing in this profile.

A profile of an avionics family joins one autopilot, one cockpit and the navigators of both units (part.compose);
an aircraft's profile may be a module of its own, as Black Square's Bonanza's, whose tablet selects among several
navigators at once. Each module names the source of its events; codes beyond a plain key or H: event say theirs
where they are written.

A new part is one more entry in AUTOPILOTS, COCKPITS or NAVIGATORS, or in UNIT_NAVIGATORS for a navigator of one
unit (a function of the unit it goes in, as gns.NAVIGATORS and gtn.NAVIGATORS give them); a new profile one more
line in FAMILIES.
"""
from mobiflight.families import aircraft, black_square_bonanza, g3x, g1000, gns, gtn, parts
from mobiflight.families.part import GPS_DISTANCE, compose, empty

AUTOPILOTS = {p.KEY: p for p in (g1000.AUTOPILOT, g3x.AUTOPILOT, parts.KAP140_AUTOPILOT,
                                 black_square_bonanza.AUTOPILOT)}
COCKPITS = {p.KEY: p for p in (g1000.COCKPIT, g3x.COCKPIT, parts.BENDIX_KING)}
NAVIGATORS = {p.KEY: p for p in (g1000.NAVIGATOR, g3x.NAVIGATOR)}     # both units
UNIT_NAVIGATORS = {**gns.NAVIGATORS, **gtn.NAVIGATORS}               # key -> function of the unit
# The distances an autopilot part alone reads for VNV, not knowing its navigator (the parts zip): every navigator's,
# the sim's GPS WP DISTANCE last; a profile joined from parts reads only its navigators' (part.compose)
ALONE_DISTANCES = tuple(dict.fromkeys(
    d for p in (*NAVIGATORS.values(), *(make(unit) for make in UNIT_NAVIGATORS.values() for unit in (1, 2)))
    for d in getattr(p, "DISTANCES", ()) if d != GPS_DISTANCE)) + (GPS_DISTANCE,)
for _autopilot in AUTOPILOTS.values():
    if getattr(_autopilot, "VNV", None):
        _autopilot.DEVICE[1]["VNV"] = _autopilot.DEVICE[1]["S_VNV"] = _autopilot.VNV(distances=ALONE_DISTANCES)


def navigators(unit1, unit2):
    """The navigators of unit 1 and unit 2 by their keys (UNIT_NAVIGATORS); "none" for a unit without one"""
    return tuple(empty(unit) if key == "none" else UNIT_NAVIGATORS[key](unit) for unit, key in ((1, unit1), (2, unit2)))


def every_part():
    """Every part, the navigators of one unit in each unit: {kind-key: part}, as the parts zip names them"""
    every = [*AUTOPILOTS.values(), *COCKPITS.values(), *NAVIGATORS.values(),
             *(make(unit) for make in UNIT_NAVIGATORS.values() for unit in (1, 2))]
    out = {f"{p.KIND}-{p.KEY}": p for p in every}
    if len(out) != len(every):
        raise ValueError("two parts of one kind share a key")
    return out


FAMILIES = {
    "g1000": compose("G1000 NXi", g1000.AUTOPILOT, g1000.COCKPIT, g1000.NAVIGATOR),
    "g3x": compose("GFC 500 and G3X Touch", g3x.AUTOPILOT, g3x.COCKPIT, g3x.NAVIGATOR, TOUCHSCREEN=g3x.TOUCHSCREEN),
    "gns": compose("GNS 530/430", parts.KAP140_AUTOPILOT, parts.BENDIX_KING, *navigators("gns530", "gns430")),
    "gtn": compose("GTN 750Xi/650Xi", parts.KAP140_AUTOPILOT, parts.BENDIX_KING,
                   *navigators("gtn750-tds1", "gtn650-tds2"),
                   TOUCHSCREEN=(*gtn.TOUCHSCREEN, *(f"S_{b}" for b in gtn.TOUCHSCREEN if b.startswith("PAN_")))),
    "black-square-bonanza": black_square_bonanza,
    "cows-da40": compose("COWS DA40", g1000.AUTOPILOT, g1000.COCKPIT, g1000.NAVIGATOR, rows={1: aircraft.DA40_LIGHTS}),
    "carenado-c182t": compose("Carenado C182T", parts.KAP140_AUTOPILOT, g1000.COCKPIT, g1000.NAVIGATOR,
                              rows={1: aircraft.C182T_LIGHTS}, unmapped={1: aircraft.C182T_UNMAPPED}),
}
