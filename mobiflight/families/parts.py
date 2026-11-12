"""The parts several family tables share: {button: entry} rows, and {button: reason} for the buttons a part
leaves unmapped, joined into a table's DEVICE and UNMAPPED dicts (__init__.py).

The radios, ADF, transponder, audio panel and the instruments around the KAP 140 take the simulator's own key
events (K:), which act the same in every aircraft and whatever unit shows them; the KAP 140 takes the H: events
of the one MSFS ships (KAP140_*). HubHop has no presets for these made for MSFS 2024.
"""
GEN = "Microsoft.Generic."
KAP = GEN + "KAP140_"

# ---------------- the simulator's radios, tuned directly ----------------
# COM 1 / NAV 1 from unit 1 and COM 2 / NAV 2 from unit 2, whichever unit or tuning box shows them
RADIO = {
    1: {
        "COM_SWAP": GEN + "COM1_RADIO_SWAP",
        "NAV_SWAP": GEN + "NAV1_RADIO_SWAP",
        "COM_MHZ_UP": GEN + "COM_RADIO_WHOLE_INC",
        "COM_MHZ_DN": GEN + "COM_RADIO_WHOLE_DEC",
        "COM_KHZ_UP": GEN + "COM_RADIO_FRACT_INC",
        "COM_KHZ_DN": GEN + "COM_RADIO_FRACT_DEC",
        "NAV_MHZ_UP": GEN + "NAV1_RADIO_WHOLE_INC",
        "NAV_MHZ_DN": GEN + "NAV1_RADIO_WHOLE_DEC",
        "NAV_KHZ_UP": GEN + "NAV1_RADIO_FRACT_INC",
        "NAV_KHZ_DN": GEN + "NAV1_RADIO_FRACT_DEC",
    },
    2: {
        "COM_SWAP": GEN + "COM2_RADIO_SWAP",
        "NAV_SWAP": GEN + "NAV2_RADIO_SWAP",
        "COM_MHZ_UP": GEN + "COM2_RADIO_WHOLE_INC",
        "COM_MHZ_DN": GEN + "COM2_RADIO_WHOLE_DEC",
        "COM_KHZ_UP": GEN + "COM2_RADIO_FRACT_INC",
        "COM_KHZ_DN": GEN + "COM2_RADIO_FRACT_DEC",
        "NAV_MHZ_UP": GEN + "NAV2_RADIO_WHOLE_INC",
        "NAV_MHZ_DN": GEN + "NAV2_RADIO_WHOLE_DEC",
        "NAV_KHZ_UP": GEN + "NAV2_RADIO_FRACT_INC",
        "NAV_KHZ_DN": GEN + "NAV2_RADIO_FRACT_DEC",
    },
}
RADIO_UNMAPPED = {               # both units
    "FREQ_PUSH": "the FREQ knob's mode is the panel's: each mode sends buttons of its own",
}
# the one ADF receiver, from both units: the knob tunes the active frequency, ADF ⇆ swaps it with the standby
ADF = {
    "ADF_SWAP": GEN + "ADF1 Swap Freq",
    "ADF_100_UP": GEN + "ADF_100_INC",
    "ADF_100_DN": GEN + "ADF_100_DEC",
    "ADF_1_UP": GEN + "ADF_1_INC",
    "ADF_1_DN": GEN + "ADF_1_DEC",
    "ADF_10_UP": GEN + "ADF_10_INC",
    "ADF_10_DN": GEN + "ADF_10_DEC",
}
# the transponder (device 1): squawk, digit 1 is the thousands
SQUAWK = {
    "SQK_D1_UP": GEN + "XPNDR_1000_INC",
    "SQK_D1_DN": GEN + "XPNDR_1000_DEC",
    "SQK_D2_UP": GEN + "XPNDR_100_INC",
    "SQK_D2_DN": GEN + "XPNDR_100_DEC",
    "SQK_D3_UP": GEN + "XPNDR_10_INC",
    "SQK_D3_DN": GEN + "XPNDR_10_DEC",
    "SQK_D4_UP": GEN + "XPNDR_1_INC",
    "SQK_D4_DN": GEN + "XPNDR_1_DEC",
    "IDENT": GEN + "TransponderIDT",
    "VFR": "Microsoft.Cessna 172.C_172_XPNDR_VFR",         # squawk 1200, in any aircraft
}
SQUAWK_UNMAPPED = {
    "XPDR_MODE": "no HubHop preset steps the transponder mode",
}
# the cockpit lighting (device 1)
LIGHTS = {
    "CABIN_LT": GEN + "TOGGLE_CABIN_LIGHTS",
}
_DIMMERS = "the dimmers differ by aircraft: no HubHop preset steps them in every aircraft with this avionics"
LIGHTS_UNMAPPED = dict.fromkeys(("PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN"), _DIMMERS)
# the RANGE knob (device 1): its tilts and push pan the map and work its pointer
PAN = ("PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT", "PTR", "S_PAN_UP", "S_PAN_DN", "S_PAN_LEFT", "S_PAN_RIGHT",
       "S_PTR")
RANGE_KNOB = ("RANGE_CW", "RANGE_CCW", "S_RANGE_CW", "S_RANGE_CCW", *PAN)

# ---------------- the KAP 140 cockpit around a navigator (device 1) ----------------
KAP140 = {
    # autopilot keys
    "AP": KAP + "Push_AP",
    "ALT": KAP + "Push_ALT",
    "HDG": KAP + "Push_HDG",
    "NAV": KAP + "Push_NAV",
    "UP": KAP + "Push_UP",
    "APR": KAP + "Push_APR",
    "DN": KAP + "Push_DN",
    # shifted keys
    "ARM": KAP + "Push_ARM",
    "S_UP": KAP + "Push_UP",
    "BC": KAP + "Push_REV",
    "S_DN": KAP + "Push_DN",
    # ALT/HDG knob: the KAP 140's altitude knob (inner 100 ft, outer 1000 ft) and the heading bug, which the push
    # syncs to the heading as on the G1000; with SHIFT the course of NAV 1 and the altimeter
    "ALT_100_UP": KAP + "Knob_Inner_INC",
    "ALT_100_DN": KAP + "Knob_Inner_DEC",
    "ALT_1000_UP": KAP + "Knob_Outer_INC",
    "ALT_1000_DN": KAP + "Knob_Outer_DEC",
    "HDG_1_UP": GEN + "HEADING_BUG_INC",
    "HDG_1_DN": GEN + "HEADING_BUG_DEC",
    "HDG_10_UP": GEN + "AS1000_PFD_HEADING_FAST_INC",      # 5°, the sim's HEADING_BUG_SET: no 10° preset
    "HDG_10_DN": GEN + "AS1000_PFD_HEADING_FAST_DEC",
    "HDG_SYNC": GEN + "AS1000_PFD_HEADING_SYNC",           # the sim's HEADING_BUG_SET too
    "CRS_1_UP": GEN + "VOR1_OBI_INC",
    "CRS_1_DN": GEN + "VOR1_OBI_DEC",
    "CRS_10_UP": GEN + "VOR1_OBI_FAST_INC",
    "CRS_10_DN": GEN + "VOR1_OBI_FAST_DEC",
    "BARO_UP": GEN + "KOHLSMAN_INC",
    "BARO_DN": GEN + "KOHLSMAN_DEC",
    "BARO_STD": GEN + "BAROMETRIC STD PRESSURE",
}
_VS = "the KAP 140 has no VS key: it engages in VS, and UP and DN set the rate"
_FLC = "the KAP 140 has no FLC mode"
_VNV = "the KAP 140 has no VNAV mode"
KAP140_UNMAPPED = {
    "TEST": "the KAP 140 tests itself at power-up: it has no TEST key",
    "FD": "the KAP 140 has no flight director",
    "YD": "the KAP 140 has no yaw damper",
    "VS": _VS,
    "S_VS": _VS,
    "FLC": _FLC,
    "S_FLC": _FLC,
    "VNV": _VNV,
    "S_VNV": _VNV,
    "LVL": "the KAP 140 has no level mode",
    "HALF_BANK": "the KAP 140 has no low-bank mode",
    "GPSS": "the KAP 140 has no GPSS key: NAV follows the CDI, on GPS or VLOC",
    "CRS_CTR": "the CDI's course knob has no centring push",
}
# the audio panel (KMA 28 and the like): MIC selects the pilot's transmitter
AUDIO = {
    "MIC1": GEN + "Transmit_Com1",
    "COM1": GEN + "COM1 RECEIVE TOGGLE",
    "MIC2": GEN + "Transmit_Com2",
    "COM2": GEN + "COM2 RECEIVE TOGGLE",
    "ADF_AUDIO": GEN + "RADIO_ADF_IDENT_TOGGLE",
    "NAV1_AUDIO": GEN + "RADIO_VOR1_IDENT_TOGGLE",
    "DME_AUDIO": GEN + "RADIO_DME1_IDENT_TOGGLE",
    "NAV2_AUDIO": GEN + "RADIO_VOR2_IDENT_TOGGLE",
}
# everything on device 1 but the units and the RANGE knob
KAP140_COCKPIT = {**KAP140, **AUDIO, **SQUAWK, **LIGHTS}
KAP140_COCKPIT_UNMAPPED = {**KAP140_UNMAPPED, **SQUAWK_UNMAPPED, **LIGHTS_UNMAPPED}
