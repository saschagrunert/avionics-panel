"""TDS's GTN 750Xi and 650Xi as navigator parts (part.py), in MSFS 2024: what each button does with them
(docs/using/controls.md, docs/using/compatibility.md), each as TDS's unit 1 or unit 2 in the panel's unit 1 or 2, and
pms50's GTN 750 and 650. The GTN profile (families/__init__.py) joins the KAP 140 autopilot and the Bendix/King cockpit,
as in the Cessna 172 Skyhawk Classic with TDS's GTNs, with the GTN 750Xi unit 1 in unit 1 (COM 1, NAV 1) and the GTN
650Xi unit 2 in unit 2 (COM 2, NAV 2). TDS numbers the units per model (TDS GTNXi manual, "Interfacing with Hardware");
that its MSFS 2024 aircraft integrations load the 650Xi as unit 2 is assumed from the bezel names of the C172's
(marcfsx-tdssim-gtnxi750u1 and marcfsx-tdssim-gtnxi650u2), and the parts cover the other ways. What the profile does
differently from the real units is in docs/using/mapping.md#tds-gtn-750xi-and-650xi.

TDS takes only the GTNs' bezel from outside, as the simulator's GPS key events with a value that names the unit (the
manual's "Interfacing with Hardware"): a knob detent sends the unit's value, a key that value plus 2 when it goes down
and plus 4 when it comes up, and the volume knob ("Top Left Knob") the same to turn it down and up. The radios are tuned
with the simulator's own key events in the cockpit part: the manual says the GTNs "are able to control the Flight
Simulator COM and NAV radio frequencies", and that they show frequencies set from outside is assumed
(docs/using/mapping.md). The RANGE knob of the unit works the GTN's inner knob, its volume knob and its push (_map).
"""
from functools import partial

from mobiflight.families import part
from mobiflight.families.rpn import h, k

# TDS's value of each unit in its key events (the manual's "Interfacing with Hardware": the GTN 750Xi and the GTN
# 650Xi, each as unit 1 and unit 2), and what a key adds to it: down, up; the volume knob adds the same to turn down
# and up
TDS = {("750", 1): 0, ("650", 1): 8, ("750", 2): 16, ("650", 2): 24}
# the GTNXi's distance to the next waypoint (TDS's manual, "Reading specific TDS GTNXi Data"), for VNV (parts.descent)
TDS_DISTANCE = "(L:TDSGTNXI_NextWaypointDistanceNM, Number)"
KEY_DOWN, KEY_UP = 2, 4


def _held(event, value):
    """A bezel key, held as long as the panel's key or push"""
    return {"press": k(event, value + KEY_DOWN), "release": k(event, value + KEY_UP)}


def _bezel(value):
    """The bezel of the TDS GTNXi of this value: HOME, D→, the dual knob (outer GROUP, inner PAGE) and its push,
    held as long as the panel's key or push, so a held push flips the frequencies"""
    return {
        "HOME": _held("GPS_MENU_BUTTON", value),
        "DIRECT": _held("GPS_DIRECTTO_BUTTON", value),
        "FMS_OUTER_CW": k("GPS_GROUP_KNOB_INC", value),
        "FMS_OUTER_CCW": k("GPS_GROUP_KNOB_DEC", value),
        "FMS_INNER_CW": k("GPS_PAGE_KNOB_INC", value),
        "FMS_INNER_CCW": k("GPS_PAGE_KNOB_DEC", value),
        "FMS_CRSR": _held("GPS_CURSOR_BUTTON", value),
    }


def _map(value):
    """The RANGE knob: turned, the inner knob (GPS_PAGE_KNOB), which zooms the map on the map page. Clockwise zooms
    out, as the GNS's and the G1000's RANGE do, so it turns the inner knob the other way: on Garmin's touchscreen
    units the inner knob zooms in clockwise (the AXIS pilot's guide, "Adjusting the MFW Map Range"), assumed for the
    GTN too. Tilted up and down, the volume knob (GPS_BUTTON2, the manual's "Top Left Knob"); pushed, its push
    (GPS_BUTTON1), which toggles squelch: the panel sends the RANGE push as a tap when it is let go
    (firmware/panel.py), so a held push, 121.5 on the GTN, does not reach it, and the tap still goes down and up."""
    return {
        "RANGE_CW": k("GPS_PAGE_KNOB_DEC", value),
        "RANGE_CCW": k("GPS_PAGE_KNOB_INC", value),
        "PAN_UP": k("GPS_BUTTON2", value + KEY_UP),
        "PAN_DN": k("GPS_BUTTON2", value + KEY_DOWN),
        "PTR": _held("GPS_BUTTON1", value),
    }


_TOUCH = "a touchscreen function of the GTN: it takes only its bezel (HOME, D→, the knobs) from outside"
_TOUCH_KEYS = ("CDI", "OBS", "FPL", "MENU", "PROC", "CLR", "ENT", "S_ENT", "VNAV", "MSG", "NRST", "TERR", "MAP")
_PAN = ("PAN_LEFT", "PAN_RIGHT")
# what the GTN has on its touchscreen only (docs/using/compatibility.md), for unit 1 (unit 2's map with SHIFT)
TOUCHSCREEN = (*_TOUCH_KEYS, *_PAN)
_UNMAPPED = {**dict.fromkeys(_TOUCH_KEYS, _TOUCH), **dict.fromkeys(_PAN, "the GTN pans its map on the touchscreen")}


def tds(model, tds_unit, unit):
    """TDS's GTN 750Xi or 650Xi ("750", "650") as TDS's unit 1 or 2 (tds_unit: how the aircraft loads it), in the
    panel's unit 1 or 2"""
    value = TDS[model, tds_unit]
    return part.navigator(f"gtn{model}-tds{tds_unit}", f"TDS GTN {model}Xi (TDS unit {tds_unit})",
                          {**_bezel(value), **_map(value)}, _UNMAPPED, unit, (TDS_DISTANCE,))


def pms50(model, unit):
    """pms50's GTN 750 or 650 by the H: events Black Square's guide lists for it (GTN750_, GTN650_): HOME, D→, the
    dual knob and its push, and the volume knob on the RANGE tilt; it takes no volume push from outside"""
    p = f"GTN{model}_"
    rows = {
        "HOME": h(p + "HomePush"),
        "DIRECT": h(p + "DirectToPush"),
        "FMS_OUTER_CW": h(p + "KnobLargeInc"),
        "FMS_OUTER_CCW": h(p + "KnobLargeDec"),
        "FMS_INNER_CW": h(p + "KnobSmallInc"),
        "FMS_INNER_CCW": h(p + "KnobSmallDec"),
        "FMS_CRSR": h(p + "KnobPush"),
        "RANGE_CW": h(p + "KnobSmallDec"),
        "RANGE_CCW": h(p + "KnobSmallInc"),
        "PAN_UP": h(p + "VolInc"),
        "PAN_DN": h(p + "VolDec"),
    }
    return part.navigator(f"gtn{model}-pms50", f"pms50 GTN {model}", rows,
                          {**_UNMAPPED, "PTR": "the pms50 GTN takes no volume push from outside"}, unit)


NAVIGATORS = {
    **{f"gtn{model}-tds{t}": partial(tds, model, t) for model in ("750", "650") for t in (1, 2)},
    **{f"gtn{model}-pms50": partial(pms50, model) for model in ("750", "650")},
}
