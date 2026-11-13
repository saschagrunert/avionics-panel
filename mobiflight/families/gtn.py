"""TDS GTN 750Xi and 650Xi in the KAP 140 cockpit, in MSFS 2024: what each button does there (docs/using/controls.md,
docs/using/compatibility.md), as in the Cessna 172 Skyhawk Classic with TDS's GTNs. The GTN 750Xi is TDS's unit 1
(COM 1, NAV 1) and the GTN 650Xi its unit 2 (COM 2, NAV 2). TDS numbers the units per model (TDS GTNXi manual,
revision 19, "Interfacing with Hardware"); that its MSFS 2024 aircraft integrations load the 650Xi as unit 2 is
assumed from the bezel names of the C172's (marcfsx-tdssim-gtnxi750u1 and marcfsx-tdssim-gtnxi650u2). Aircraft that
load the 650Xi as unit 1, as Black Square's do, are not covered: the KFC 150 profile covers those (kfc150.py). What
the profile does differently from the real units is in docs/using/mapping.md#tds-gtn-750xi-and-650xi.

TDS takes only the GTNs' bezel from outside, as the simulator's GPS key events with a value that names the unit (the
manual's "Interfacing with Hardware"): a knob detent sends the unit's value, a key that value plus 2 when it goes
down and plus 4 when it comes up. The radios are tuned with the simulator's own key events: the manual says the GTNs
"are able to control the Flight Simulator COM and NAV radio frequencies", and that they show frequencies set from
outside is assumed (docs/using/mapping.md). SHIFT with the RANGE knob, which the GTN has no use for, works the GTN
750Xi's volume knob ("Top Left Knob"), whose key events take the unit's value plus 2 to turn it down and plus 4 to
turn it up (the values a key sends when it goes down and up), and its push. The rest is the parts the tables share
(parts.py).
"""
from mobiflight.families import parts
from mobiflight.families.rpn import k

NAME = "GTN 750Xi/650Xi"
GTN750_1, GTN650_2 = 0, 24       # the value of the GTN 750Xi unit 1 and of the GTN 650Xi unit 2 in the key events
_DOWN, _UP = 2, 4                # added to it for a key: down, up


def _held(event, unit):
    """A bezel key, held as long as the panel's key or push"""
    return {"press": k(event, unit + _DOWN), "release": k(event, unit + _UP)}


def _bezel(unit):
    """The bezel of the TDS GTNXi of this value: HOME, D→, the dual knob (outer GROUP, inner PAGE) and its push,
    held as long as the panel's key or push, so a held push flips the frequencies"""
    return {
        "HOME": _held("GPS_MENU_BUTTON", unit),
        "DIRECT": _held("GPS_DIRECTTO_BUTTON", unit),
        "FMS_OUTER_CW": k("GPS_GROUP_KNOB_INC", unit),
        "FMS_OUTER_CCW": k("GPS_GROUP_KNOB_DEC", unit),
        "FMS_INNER_CW": k("GPS_PAGE_KNOB_INC", unit),
        "FMS_INNER_CCW": k("GPS_PAGE_KNOB_DEC", unit),
        "FMS_CRSR": _held("GPS_CURSOR_BUTTON", unit),
    }


# SHIFT, RANGE: the volume knob of the GTN 750Xi unit 1 (GPS_BUTTON2: turned down, up) and its push (GPS_BUTTON1),
# which toggles squelch. The panel sends the RANGE push as a tap when it is let go (firmware/panel.py), so a held
# push, 121.5 on the GTN, does not reach it; the tap still goes down and up as a key.
_VOLUME = {
    "S_RANGE_CW": k("GPS_BUTTON2", GTN750_1 + _UP),
    "S_RANGE_CCW": k("GPS_BUTTON2", GTN750_1 + _DOWN),
    "S_PTR": _held("GPS_BUTTON1", GTN750_1),
}
_TOUCH = "a touchscreen function of the GTN: TDS takes only its bezel (HOME, D→, the knobs) from outside"
_TOUCH_KEYS = ("CDI", "OBS", "FPL", "MENU", "PROC", "CLR", "ENT", "S_ENT", "VNAV", "MSG", "NRST", "TERR", "MAP")
# what the GTN has on its touchscreen only (docs/using/compatibility.md)
_MAP = tuple(b for b in parts.RANGE_KNOB if b not in _VOLUME)       # the RANGE knob without the volume knob
TOUCHSCREEN = (*_TOUCH_KEYS, *_MAP)
_UNIT_UNMAPPED = {
    **dict.fromkeys(_TOUCH_KEYS, _TOUCH),
    **parts.RADIO_UNMAPPED,
}

DEVICE = {
    1: {**parts.KAP140_COCKPIT, **_VOLUME, **_bezel(GTN750_1), **parts.RADIO[1], **parts.ADF},
    2: {**_bezel(GTN650_2), **parts.RADIO[2], **parts.ADF},
}
UNMAPPED = {
    1: {
        **parts.KAP140_COCKPIT_UNMAPPED,
        **dict.fromkeys(_MAP, "the GTN pans its map on the touchscreen, and zooms it there or with the inner FMS "
                              "knob on the map page"),
        **_UNIT_UNMAPPED,
    },
    2: _UNIT_UNMAPPED,
}
