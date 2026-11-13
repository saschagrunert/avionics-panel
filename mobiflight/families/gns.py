"""GNS 530/430 (Working Title) in the KAP 140 cockpit, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md), as in the Cessna 172 Skyhawk Classic. The GNS 530 is unit 1
(COM 1, NAV 1) and the GNS 430 unit 2 (COM 2, NAV 2), beside the KAP 140, a KR 87 ADF, a KT 76 transponder and a
KMA 28 audio panel. The same table drives KX 155/165 radios without a GNS: the radios are the simulator's, and the
GNS events then do nothing. Two GNS of the same type are not covered: the table's events cannot tell the two
apart. What the profile does differently from the real units is in docs/using/mapping.md#gns-530430.

The GNS keys and knobs are the H: events Working Title's GNS takes (InteractionEvent.ts in
microsoft/msfs-avionics-mirror, MSFS 2024 SU5), after the prefix of its template, AS530 or AS430 (WT530.tsx,
WT430.tsx); the KAP 140, the radios, ADF, transponder and audio panel are the parts the tables share (parts.py).
ENT sends the plain function with SHIFT too, so a stray SHIFT does no harm.
"""
from mobiflight.families import parts
from mobiflight.families.rpn import h

NAME = "GNS 530/430"


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


_UNIT_UNMAPPED = {
    "HOME": "the GNS has no HOME key: free for your own mapping (docs/using/compatibility.md)",
    "NRST": "the GNS has no NRST key: the nearest pages are a page group of their own (FMS outer ring)",
    "TERR": "the GNS has no TERR key",
    **parts.RADIO_UNMAPPED,
}

DEVICE = {
    1: {
        **parts.KAP140_COCKPIT,
        # RANGE: the GNS 530's RNG key, and with SHIFT the GNS 430's; clockwise zooms out
        "RANGE_CW": h("AS530_RNG_Dezoom"),
        "RANGE_CCW": h("AS530_RNG_Zoom"),
        "S_RANGE_CW": h("AS430_RNG_Dezoom"),
        "S_RANGE_CCW": h("AS430_RNG_Zoom"),
        # unit 1: the GNS 530, radio 1
        **_gns("AS530"),
        "VNAV": h("AS530_VNAV_Push"),
        **parts.RADIO[1],
        **parts.ADF,
    },
    2: {**_gns("AS430"), **parts.RADIO[2], **parts.ADF},
}
UNMAPPED = {
    1: {
        **parts.KAP140_COCKPIT_UNMAPPED,
        **dict.fromkeys(parts.PAN, "the GNS has no joystick: it pans its map with the FMS knob after a CRSR push"),
        **_UNIT_UNMAPPED,
    },
    2: {**_UNIT_UNMAPPED, "VNAV": "the GNS 430 has no VNAV key"},
}
