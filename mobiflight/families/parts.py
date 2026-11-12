"""The parts several family tables share: {button: code} rows, and {button: reason} for the buttons a part leaves
unmapped, joined into a table's DEVICE and UNMAPPED dicts (__init__.py).

The radios, ADF, transponder, audio panel and the instruments around the KAP 140 take the simulator's own key
events (the MSFS 2024 SDK's Key Events), which act the same in every aircraft and whatever unit shows them; the
KAP 140 takes the H: events of the one MSFS ships, the ones its instrument (KAP140.js) handles.
"""
from mobiflight.families.rpn import h, k, turn


def transmit(com):
    """MIC: the pilot and copilot transmit on COM 1 or 2 (the SDK's PILOT_TRANSMITTER_SET and
    COPILOT_TRANSMITTER_SET take 0 for COM 1, 1 for COM 2)"""
    return f"{com - 1} (>K:PILOT_TRANSMITTER_SET) {com - 1} (>K:COPILOT_TRANSMITTER_SET)"


def receive(com):
    """COM: listen to COM 1 or 2, or stop (the SDK's COMn_RECEIVE_SELECT, set to the opposite of COM RECEIVE EX1)"""
    return f"(A:COM RECEIVE EX1:{com}, bool) ! (>K:COM{com}_RECEIVE_SELECT)"


# ---------------- the simulator's radios, tuned directly ----------------
# COM 1 / NAV 1 from unit 1 and COM 2 / NAV 2 from unit 2, whichever unit or tuning box shows them; 121.5 tunes
# the unit's COM radio to 121.5 MHz, as holding a COM flip-flop does (COM_RADIO_SET_HZ takes Hz)
RADIO = {
    1: {
        "COM_SWAP": k("COM1_RADIO_SWAP"),
        "COM_121_5": k("COM_RADIO_SET_HZ", 121500000),
        "NAV_SWAP": k("NAV1_RADIO_SWAP"),
        "COM_MHZ_UP": k("COM_RADIO_WHOLE_INC"),
        "COM_MHZ_DN": k("COM_RADIO_WHOLE_DEC"),
        "COM_KHZ_UP": k("COM_RADIO_FRACT_INC"),
        "COM_KHZ_DN": k("COM_RADIO_FRACT_DEC"),
        "NAV_MHZ_UP": k("NAV1_RADIO_WHOLE_INC"),
        "NAV_MHZ_DN": k("NAV1_RADIO_WHOLE_DEC"),
        "NAV_KHZ_UP": k("NAV1_RADIO_FRACT_INC"),
        "NAV_KHZ_DN": k("NAV1_RADIO_FRACT_DEC"),
    },
    2: {
        "COM_SWAP": k("COM2_RADIO_SWAP"),
        "COM_121_5": k("COM2_RADIO_SET_HZ", 121500000),
        "NAV_SWAP": k("NAV2_RADIO_SWAP"),
        "COM_MHZ_UP": k("COM2_RADIO_WHOLE_INC"),
        "COM_MHZ_DN": k("COM2_RADIO_WHOLE_DEC"),
        "COM_KHZ_UP": k("COM2_RADIO_FRACT_INC"),
        "COM_KHZ_DN": k("COM2_RADIO_FRACT_DEC"),
        "NAV_MHZ_UP": k("NAV2_RADIO_WHOLE_INC"),
        "NAV_MHZ_DN": k("NAV2_RADIO_WHOLE_DEC"),
        "NAV_KHZ_UP": k("NAV2_RADIO_FRACT_INC"),
        "NAV_KHZ_DN": k("NAV2_RADIO_FRACT_DEC"),
    },
}
RADIO_UNMAPPED = {               # both units
    "FREQ_PUSH": "the FREQ knob's mode is the panel's: each mode sends buttons of its own",
}
# the one ADF receiver, from both units: the knob tunes the active frequency, ADF ⇆ swaps it with the standby
ADF = {
    "ADF_SWAP": k("ADF1_RADIO_SWAP"),
    "ADF_100_UP": k("ADF_100_INC"),
    "ADF_100_DN": k("ADF_100_DEC"),
    "ADF_1_UP": k("ADF_1_INC"),
    "ADF_1_DN": k("ADF_1_DEC"),
    "ADF_10_UP": k("ADF_10_INC"),
    "ADF_10_DN": k("ADF_10_DEC"),
}
# the transponder (device 1): squawk, digit 1 is the thousands
SQUAWK = {
    "SQK_D1_UP": k("XPNDR_1000_INC"),
    "SQK_D1_DN": k("XPNDR_1000_DEC"),
    "SQK_D2_UP": k("XPNDR_100_INC"),
    "SQK_D2_DN": k("XPNDR_100_DEC"),
    "SQK_D3_UP": k("XPNDR_10_INC"),
    "SQK_D3_DN": k("XPNDR_10_DEC"),
    "SQK_D4_UP": k("XPNDR_1_INC"),
    "SQK_D4_DN": k("XPNDR_1_DEC"),
    "IDENT": k("XPNDR_IDENT_ON"),
    "VFR": k("XPNDR_SET", "0x1200"),          # squawk 1200, in any aircraft: XPNDR_SET takes BCO16
}
SQUAWK_UNMAPPED = {
    "XPDR_MODE": "the simulator has no key event that steps the transponder mode",
}
# the cockpit lighting (device 1)
LIGHTS = {
    "CABIN_LT": k("TOGGLE_CABIN_LIGHTS"),
}
_DIMMERS = "the dimmers differ by aircraft: their key events take the aircraft's own circuit or potentiometer"
LIGHTS_UNMAPPED = dict.fromkeys(("PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN"), _DIMMERS)
# the RANGE knob (device 1): its tilts and push pan the map and work its pointer
PAN = ("PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT", "PTR", "S_PAN_UP", "S_PAN_DN", "S_PAN_LEFT", "S_PAN_RIGHT",
       "S_PTR")
RANGE_KNOB = ("RANGE_CW", "RANGE_CCW", "S_RANGE_CW", "S_RANGE_CCW", *PAN)

# ---------------- the heading bug, the course of NAV 1, the autopilot's level mode ----------------
# the heading bug of slot 1 and the heading indicator of index 1 (Working Title's APPublisher.ts and Ahrs.ts read
# both by index)
HEADING, COURSE = "AUTOPILOT HEADING LOCK DIR:1", "NAV OBS:1"
# the fast step of the heading bug, 10° (docs/using/controls.md#knobs)
HEADING_FAST = {
    "HDG_10_UP": turn(HEADING, "HEADING_BUG_SET", 10),
    "HDG_10_DN": turn(HEADING, "HEADING_BUG_SET", -10),
}
SYNC = "(A:HEADING INDICATOR:1, degrees) near dnor (>K:HEADING_BUG_SET)"         # the bug to the heading shown
# LVL engages the autopilot in level lateral and vertical modes, as the GMC 507's and GFC 700's LVL keys; Garmin's
# autopilot takes both leveler events (GarminAPStateManager.ts)
LEVEL = "(>K:AP_WING_LEVELER_ON) (>K:AP_PITCH_LEVELER_ON) (>K:AUTOPILOT_ON)"

# ---------------- the KAP 140 cockpit around a navigator (device 1) ----------------
KAP140 = {
    # autopilot keys
    "AP": h("KAP140_Push_AP"),
    "ALT": h("KAP140_Push_ALT"),
    "HDG": h("KAP140_Push_HDG"),
    "NAV": h("KAP140_Push_NAV"),
    "UP": h("KAP140_Push_UP"),
    "APR": h("KAP140_Push_APR"),
    "DN": h("KAP140_Push_DN"),
    # shifted keys
    "S_UP": h("KAP140_Push_UP"),
    "BC": h("KAP140_Push_REV"),
    "S_DN": h("KAP140_Push_DN"),
    # ALT/HDG knob: the KAP 140's altitude knob (inner 100 ft, outer 1000 ft) and the heading bug, which the push
    # syncs to the heading as on the G1000; with SHIFT the course of NAV 1 and the altimeter
    "ALT_100_UP": h("KAP140_Knob_Inner_INC"),
    "ALT_100_DN": h("KAP140_Knob_Inner_DEC"),
    "ALT_1000_UP": h("KAP140_Knob_Outer_INC"),
    "ALT_1000_DN": h("KAP140_Knob_Outer_DEC"),
    "HDG_1_UP": k("HEADING_BUG_INC"),
    "HDG_1_DN": k("HEADING_BUG_DEC"),
    **HEADING_FAST,
    "HDG_SYNC": SYNC,
    "CRS_1_UP": k("VOR1_OBI_INC"),
    "CRS_1_DN": k("VOR1_OBI_DEC"),
    "CRS_10_UP": turn(COURSE, "VOR1_SET", 10),
    "CRS_10_DN": turn(COURSE, "VOR1_SET", -10),
    "BARO_UP": k("KOHLSMAN_INC"),
    "BARO_DN": k("KOHLSMAN_DEC"),
    "BARO_STD": k("BAROMETRIC_STD_PRESSURE"),
}
_VS = "the KAP 140 has no VS key: it engages in VS, and UP and DN set the rate"
_FLC = "the KAP 140 has no FLC mode"
_VNV = "the KAP 140 has no VNAV mode"
KAP140_UNMAPPED = {
    "TEST": "the KAP 140 tests itself at power-up: it has no TEST key",
    "ARM": "the sim's KAP 140 does nothing on ARM (KAP140.js)",
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
# the audio panel (KMA 28, GMA 1347 and the like): MIC selects the transmitter, COM the receivers
AUDIO = {
    "MIC1": transmit(1),
    "COM1": receive(1),
    "MIC2": transmit(2),
    "COM2": receive(2),
    "ADF_AUDIO": k("RADIO_ADF_IDENT_TOGGLE"),
    "NAV1_AUDIO": k("RADIO_VOR1_IDENT_TOGGLE"),
    "DME_AUDIO": k("RADIO_DME1_IDENT_TOGGLE"),
    "NAV2_AUDIO": k("RADIO_VOR2_IDENT_TOGGLE"),
}
# everything on device 1 but the units and the RANGE knob
KAP140_COCKPIT = {**KAP140, **AUDIO, **SQUAWK, **LIGHTS}
KAP140_COCKPIT_UNMAPPED = {**KAP140_UNMAPPED, **SQUAWK_UNMAPPED, **LIGHTS_UNMAPPED}
