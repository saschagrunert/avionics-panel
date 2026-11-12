"""GNS 530/430 (Working Title) in the KAP 140 cockpit, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md) as HubHop presets, as in the Cessna 172 Skyhawk Classic.
The GNS 530 is unit 1 (COM 1, NAV 1) and the GNS 430 unit 2 (COM 2, NAV 2), beside the KAP 140, a KR 87 ADF, a
KT 76 transponder and a KMA 28 audio panel. The same table drives KX 155/165 radios without a GNS: the radios
are the simulator's, and the GNS events then do nothing. What the profile does differently from the real units
is in docs/using/mapping.md#gns-530430.

The GNS keys and knobs are their H: events (AS530_*, AS430_*), which the Working Title GNS takes like Asobo's;
the KAP 140, the radios, ADF, transponder and audio panel are the parts the tables share (parts.py). HubHop has
no GNS presets made for MSFS 2024. ENT and the RANGE turns send the plain function with SHIFT too, so a stray
SHIFT does no harm.
"""
from mobiflight.families import parts

NAME = "GNS 530/430"

GNS530 = parts.GEN + "AS530_"
GNS430 = parts.GEN + "AS430_"


def _gns(p):
    """The keys and the right-hand knob of a GNS, by its presets' prefix"""
    return {
        "CDI": p + "CDI_Push",
        "FPL": p + "FPL_Push",
        "DIRECT": p + "DirectTo_Push",
        "MENU": p + "MENU_Push",
        "PROC": p + "PROC_Push",
        "CLR": p + "CLR_Push",
        "ENT": p + "ENT_Push",
        "OBS": p + "OBS_Push",
        "MSG": p + "MSG_Push",
        "MAP": p + "CLR_Push_Long",                       # hold CLR
        "S_ENT": p + "ENT_Push",
        "FMS_OUTER_CW": p + "RightLargeKnob_Right",
        "FMS_OUTER_CCW": p + "RightLargeKnob_Left",
        "FMS_INNER_CW": p + "RightSmallKnob_Right",
        "FMS_INNER_CCW": p + "RightSmallKnob_Left",
        "FMS_CRSR": p + "RightSmallKnob_Push",
    }


_UNIT_UNMAPPED = {
    "HOME": "the GNS has no HOME key: free for your own mapping (docs/using/compatibility.md)",
    "NRST": "the GNS has no NRST key: the nearest pages are a page group of their own (FMS outer ring)",
    "TERR": "the GNS has no TERR key",
    "COM_121_5": "the Working Title GNS's COM flip-flop has no long press, and no HubHop preset tunes 121.5",
    **parts.RADIO_UNMAPPED,
}

DEVICE = {
    1: {
        **parts.KAP140_COCKPIT,
        # RANGE: the GNS 530's RNG key; clockwise zooms out
        "RANGE_CW": GNS530 + "RNG_Dezoom",
        "RANGE_CCW": GNS530 + "RNG_Zoom",
        "S_RANGE_CW": GNS530 + "RNG_Dezoom",
        "S_RANGE_CCW": GNS530 + "RNG_Zoom",
        # unit 1: the GNS 530, radio 1
        **_gns(GNS530),
        "VNAV": GNS530 + "VNAV_Push",
        **parts.RADIO[1],
        **parts.ADF,
    },
    2: {**_gns(GNS430), **parts.RADIO[2], **parts.ADF},
}
UNMAPPED = {
    1: {
        **parts.KAP140_COCKPIT_UNMAPPED,
        **dict.fromkeys(parts.PAN, "the GNS has no joystick: it pans its map with the FMS knob after a CRSR push"),
        **_UNIT_UNMAPPED,
    },
    2: {**_UNIT_UNMAPPED, "VNAV": "the GNS 430 has no VNAV key"},
}
