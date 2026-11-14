"""Working Title's GNS 530 and 430 as navigator parts (part.py), in MSFS 2024: what each button does with them
(docs/using/controls.md, docs/using/compatibility.md), each in the panel's unit 1 or 2. The GNS profile
(families/__init__.py) joins them to the KAP 140 autopilot and the Bendix/King cockpit, as in the Cessna 172 Skyhawk
Classic: the GNS 530 is unit 1 (COM 1, NAV 1) and the GNS 430 unit 2 (COM 2, NAV 2), beside the KAP 140, a KR 87 ADF, a
KT 76 transponder and a KMA 28 audio panel. The same profile drives KX 155/165 radios without a GNS: the radios are the
simulator's, and the GNS events then do nothing. Two GNS of the same type are not covered: the events cannot tell the
two apart. What the profile does differently from the real units is in docs/using/mapping.md#gns-530430.

The GNS keys and knobs are the H: events Working Title's GNS takes (InteractionEvent.ts in
microsoft/msfs-avionics-mirror, MSFS 2024 SU5), after the prefix of its template, AS530 or AS430 (WT530.tsx,
WT430.tsx); the KAP 140, the radios, ADF, transponder and audio panel are the parts the tables share (parts.py).
ENT sends the plain function with SHIFT too, so a stray SHIFT does no harm.
"""
from functools import partial

from mobiflight.families import part
from mobiflight.families.rpn import h, k


def _gns(unit):
    """The keys and the right-hand knob of a GNS, by its template ("AS530", "AS430")"""
    return {
        "CDI": h(f"{unit}_CDI_Push"),
        "FPL": h(f"{unit}_FPL_Push"),
        "DIRECT": h(f"{unit}_DirectTo_Push"),
        "MENU": h(f"{unit}_MENU_Push"),
        "PROC": h(f"{unit}_PROC_Push"),
        "CLR": h(f"{unit}_CLR_Push"),
        "ENT": h(f"{unit}_ENT_Push"),
        "OBS": h(f"{unit}_OBS_Push"),
        "MSG": h(f"{unit}_MSG_Push"),
        "MAP": h(f"{unit}_CLR_Push_Long"),                      # hold CLR
        "S_ENT": h(f"{unit}_ENT_Push"),
        "FMS_OUTER_CW": h(f"{unit}_RightLargeKnob_Right"),
        "FMS_OUTER_CCW": h(f"{unit}_RightLargeKnob_Left"),
        "FMS_INNER_CW": h(f"{unit}_RightSmallKnob_Right"),
        "FMS_INNER_CCW": h(f"{unit}_RightSmallKnob_Left"),
        "FMS_CRSR": h(f"{unit}_RightSmallKnob_Push"),
    }


_NO_JOYSTICK = "the GNS has no joystick: it pans its map with the FMS knob after a CRSR push"


def navigator(model, unit):
    """The GNS 530 or 430 ("530", "430") in unit 1 or 2, by its template's events: its keys and right-hand knob, and on
    the RANGE knob its RNG key (clockwise zooms out) and, tilted up and down, the volume of the unit's COM radio,
    the GNS's volume knob (as Black Square's guide lists it for its GNS 530)"""
    prefix = f"AS{model}"
    rows = {
        **_gns(prefix),
        "RANGE_CW": h(f"{prefix}_RNG_Dezoom"),
        "RANGE_CCW": h(f"{prefix}_RNG_Zoom"),
        "PAN_UP": k(f"COM{unit}_VOLUME_INC"),
        "PAN_DN": k(f"COM{unit}_VOLUME_DEC"),
        **({"VNAV": h(f"{prefix}_VNAV_Push")} if model == "530" else {}),
    }
    unmapped = {
        "HOME": "the GNS has no HOME key: free for your own mapping (docs/using/compatibility.md)",
        "NRST": "the GNS has no NRST key: the nearest pages are a page group of their own (FMS outer ring)",
        "TERR": "the GNS has no TERR key",
        **dict.fromkeys(("PAN_LEFT", "PAN_RIGHT", "PTR"), _NO_JOYSTICK),
        **({} if model == "530" else {"VNAV": "the GNS 430 has no VNAV key"}),
    }
    return part.navigator(f"gns{model}", f"GNS {model}", rows, unmapped, unit)


NAVIGATORS = {f"gns{model}": partial(navigator, model) for model in ("530", "430")}
