"""TDS GTN 750Xi and 650Xi in the KAP 140 cockpit, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md) as HubHop presets, as in the Cessna 172 Skyhawk Classic
with TDS's GTNs. The GTN 750Xi is TDS's unit 1 (COM 1, NAV 1) and the GTN 650Xi its unit 2 (COM 2, NAV 2), as
TDS's MSFS 2024 aircraft mods load them. TDS numbers the units per model: aircraft that load the 650Xi as unit 1,
as Black Square's do, are not covered (HubHop has no presets for it). What the profile does differently from the
real units is in docs/using/mapping.md#tds-gtn-750xi-and-650xi.

TDS takes only the GTNs' bezel from outside (TDS GTNXi manual, rev. 19, "Interfacing with Hardware"). HubHop's
TDS presets set TDS's L: variables (TDSGTNXI750U1_HomeKEY and so on), as TDS's own MSFS 2024 bezel attachments
do; the manual gives K: events with a unit value instead (GPS_MENU_BUTTON and so on), for which HubHop has
presets for one unit of each model, pressing and releasing at once, and none for the knobs (GPS_PAGE_KNOB,
GPS_GROUP_KNOB). The radios are tuned with the simulator's own key events, which the GTNs show; the rest is
the parts the tables share (parts.py).
"""
from mobiflight.families import parts

NAME = "GTN 750Xi/650Xi"


def _bezel(model, unit):
    """The bezel of TDS's GTNXi of this model ("750", "650") and unit: HOME, D→, the dual knob and its push,
    held as long as the panel's key or push, so a held push flips the frequencies. 121.5 holds the volume knob
    pushed, which tunes 121.5 after about 2 s (a short press toggles the squelch)."""
    p = f"TDS Sim.GTNXi {model} {unit}.TDS_GTN{model}U{unit}_"
    return {
        "HOME": {"press": p + "Home_Press", "release": p + "Home_Rls"},
        "DIRECT": {"press": p + "Direct_to_Press", "release": p + "Direct_to_Rls"},
        "COM_121_5": {"press": p + "Vol_Press", "release": p + "Vol_Rls"},
        "FMS_OUTER_CW": p + "Large_Knob_Inc",
        "FMS_OUTER_CCW": p + "Large_Knob_Dec",
        "FMS_INNER_CW": p + "Small_Knob_Inc",
        "FMS_INNER_CCW": p + "Small_Knob_Dec",
        "FMS_CRSR": {"press": p + "Knob_Push_Press", "release": p + "Knob_Push_Rls"},
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
