"""TDS GTN 750Xi and 650Xi in the KAP 140 cockpit, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md), as in the Cessna 172 Skyhawk Classic with TDS's GTNs. The GTN
750Xi is TDS's unit 1 (COM 1, NAV 1) and the GTN 650Xi its unit 2 (COM 2, NAV 2), as TDS's MSFS 2024 aircraft
integrations load them (the C172's attaches the bezels marcfsx-tdssim-gtnxi750u1 and marcfsx-tdssim-gtnxi650u2).
TDS numbers the units per model: aircraft that load the 650Xi as unit 1, as Black Square's do, are not covered. What
the profile does differently from the real units is in docs/using/mapping.md#tds-gtn-750xi-and-650xi.

TDS takes only the GTNs' bezel from outside (TDS GTNXi manual, rev. 19, "Interfacing with Hardware"). The table
sets the L: variables TDS's MSFS 2024 bezels write for their keys and knobs, as YourControls' FS2024
TDS_GTNXi.yaml syncs them (TDSGTNXI750U1_HomeKey and so on): a key is 1 while held and 0 when let go, and a knob
detent sets its variable to 1. The radios are tuned with the simulator's own key events, which the GTNs show; the
rest is the parts the tables share (parts.py).
"""
from mobiflight.families import parts
from mobiflight.families.rpn import lvar

NAME = "GTN 750Xi/650Xi"


def _held(variable):
    """A bezel key, held as long as the panel's key or push"""
    return {"press": lvar(variable, 1), "release": lvar(variable, 0)}


def _bezel(model, unit):
    """The bezel of TDS's GTNXi of this model ("750", "650") and unit: HOME, D→, the dual knob and its push, held
    as long as the panel's key or push, so a held push flips the frequencies"""
    p = f"TDSGTNXI{model}U{unit}_"
    return {
        "HOME": _held(p + "HomeKey"),
        "DIRECT": _held(p + "DTOKey"),
        "FMS_OUTER_CW": lvar(p + "RKnobOuterInc", 1),
        "FMS_OUTER_CCW": lvar(p + "RKnobOuterDec", 1),
        "FMS_INNER_CW": lvar(p + "RKnobInnerInc", 1),
        "FMS_INNER_CCW": lvar(p + "RKnobInnerDec", 1),
        "FMS_CRSR": _held(p + "RKnobCRSR"),
    }


_TOUCH = "a touchscreen function of the GTN: TDS takes only its bezel (HOME, D→, the knobs) from outside"
_UNIT_UNMAPPED = {
    **dict.fromkeys(("CDI", "OBS", "FPL", "MENU", "PROC", "CLR", "ENT", "S_ENT", "VNAV", "MSG", "NRST", "TERR",
                     "MAP"), _TOUCH),
    **parts.RADIO_UNMAPPED,
}

DEVICE = {
    1: {**parts.KAP140_COCKPIT, **_bezel("750", 1), **parts.RADIO[1], **parts.ADF},
    2: {**_bezel("650", 2), **parts.RADIO[2], **parts.ADF},
}
UNMAPPED = {
    1: {
        **parts.KAP140_COCKPIT_UNMAPPED,
        **dict.fromkeys(parts.RANGE_KNOB, "the GTN pans its map on the touchscreen, and zooms it there or with the "
                                          "inner FMS knob on the map page"),
        **_UNIT_UNMAPPED,
    },
    2: _UNIT_UNMAPPED,
}
