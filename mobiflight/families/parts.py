"""The parts several family tables share: {button: code} rows, and {button: reason} for the buttons a part leaves
unmapped, joined into a table's DEVICE and UNMAPPED dicts (__init__.py).

The radios, ADF, transponder, audio panel and the instruments around a Bendix/King autopilot take the simulator's
own key events (the MSFS 2024 SDK's Key Events) and, for the transponder's mode, its simulation variable, which act
the same in every aircraft and whatever unit shows them; the KAP 140 takes the H: events of the one MSFS ships, the
ones its instrument (KAP140.js) handles. Garmin's autopilot, as Working Title's G1000 NXi and G3X Touch build it,
takes the simulator's autopilot key events (GARMIN_SHARED).
"""
import re

from mobiflight.families.rpn import h, k, turn

VFR = "7000"                     # the squawk the VFR key sets (EASA), unless a profile is made with another (--vfr)


def transmit(com):
    """MIC: the pilot and copilot transmit on COM 1 or 2 (the SDK's PILOT_TRANSMITTER_SET and
    COPILOT_TRANSMITTER_SET take 0 for COM 1, 1 for COM 2)"""
    return f"{com - 1} (>K:PILOT_TRANSMITTER_SET) {com - 1} (>K:COPILOT_TRANSMITTER_SET)"


def receive(com):
    """COM: listen to COM 1 or 2, or stop (the SDK's COMn_RECEIVE_SELECT, set to the opposite of COM RECEIVE EX1)"""
    return f"(A:COM RECEIVE EX1:{com}, bool) ! (>K:COM{com}_RECEIVE_SELECT)"


def vfr(code=VFR):
    """VFR: squawk this code, four digits of 0 to 7, in any aircraft (XPNDR_SET takes BCO16: the digits as hex)"""
    if not re.fullmatch("[0-7]{4}", str(code)):
        raise ValueError(f"not a squawk code (four digits, each 0 to 7): {code!r}")
    return k("XPNDR_SET", f"0x{code}")


def is_squawk(entry):
    """Whether a table entry is a squawk code as vfr() makes one: the row --vfr replaces"""
    return isinstance(entry, str) and re.fullmatch("0x[0-7]{4} " + re.escape(k("XPNDR_SET")), entry) is not None


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
# the transponder (device 1): squawk, digit 1 is the thousands. XPDR mode switches between standby and ALT through
# the simulator's TRANSPONDER STATE:1 (the SDK: settable, 0 off, 1 standby, 2 test, 3 on, 4 ALT, 5 ground), which
# holds the mode of Working Title's units (XPDR.ts) and of the KT 76, whose knob sets it and turns with it
# (ASOBO_Transponder_Knob_Setting_Template in the SDK's Asobo\Transponder\Transponder.xml, with this statement):
# standby or off goes to ALT, any other mode to standby
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
    "VFR": vfr(),
    "XPDR_MODE": "(A:TRANSPONDER STATE:1, Enum) 1 > if{ 1 } els{ 4 } (>A:TRANSPONDER STATE:1, Enum)",
}
# the cockpit lighting (device 1): TOGGLE_CABIN_LIGHTS sent without the circuit the SDK lets it name, assumed to
# toggle the aircraft's cabin lights as a whole
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


def nav(code):
    """The code for the NAV radio the CDI shows, # for its number, by AUTOPILOT NAV SELECTED, which the G3X Touch
    keeps on its CDI with an autopilot (its ActiveNavSourceManager.ts)"""
    return f"(A:AUTOPILOT NAV SELECTED, Number) 2 == if{{ {code.replace('#', '2')} }} els{{ {code.replace('#', '1')} }}"


def cdi(gps, radio):
    """The code for what the G3X Touch's CDI shows: gps for its GPS, radio for a NAV radio (# for its number)"""
    return f"(A:GPS DRIVES NAV1, Bool) if{{ {gps} }} els{{ {nav(radio)} }}"


def course_fast(shows):
    """The fast step of the course, 10°, on what the CDI shows, by shows(gps, radio) (cdi() or the G1000's): the
    GPS's OBS course, which Working Title's units take from the simulator's (LNavObsManager.ts,
    GarminObsLNavModule.ts), or the course of the NAV radio"""
    return {
        "CRS_10_UP": shows(turn("GPS OBS VALUE", "GPS_OBS_SET", 10), turn("NAV OBS:#", "VOR#_SET", 10)),
        "CRS_10_DN": shows(turn("GPS OBS VALUE", "GPS_OBS_SET", -10), turn("NAV OBS:#", "VOR#_SET", -10)),
    }
# LVL engages the autopilot in level lateral and vertical modes, as the GMC 507's and GFC 700's LVL keys; Garmin's
# autopilot takes both leveler events (GarminAPStateManager.ts)
LEVEL = "(>K:AP_WING_LEVELER_ON) (>K:AP_PITCH_LEVELER_ON) (>K:AUTOPILOT_ON)"
# CRS CTR on NAV radio #: the course to the VOR (its radial + 180°) or the localizer's, in whole degrees, as the
# G3X's Course knob push sets it; nothing without a signal
CENTRE = ("(A:NAV HAS LOCALIZER:#, Bool) if{ (A:NAV LOCALIZER:#, degrees) near dnor (>K:VOR#_SET) } "
          "els{ (A:NAV HAS NAV:#, Bool) if{ (A:NAV RADIAL:#, degrees) 180 + near dnor (>K:VOR#_SET) } }")

# ---------------- the rows Working Title's G1000 NXi and G3X Touch share ----------------
# Working Title builds the GFC 700 of the G1000 NXi and the GFC 500 of the G3X Touch from Garmin's autopilot
# (GarminAPStateManager.ts, GarminAPConfig.ts in garminsdk), which takes the simulator's autopilot key events, as the
# G3X's own AFCS page sends them (MFD/Views/AfcsControlsView/AfcsControlsView.tsx), and toggles VNAV on an H: event
_VS_KEY = k("AP_VS_HOLD")
_FLC_KEY = k("FLIGHT_LEVEL_CHANGE")
_VNV_KEY = h("AS1000_VNAV_TOGGLE")
# the GMC 507's nose up/down wheel and the GFC 700's NOSE UP and NOSE DN keys set the reference of the active
# vertical mode, as the G3X's AFCS page does: VS, then IAS (nose up slows it), then pitch; Working Title's directors
# set these A: flags (APVSDirector.ts, APFLCDirector.ts, APPitchDirector.ts)
_WHEEL = ("(A:AUTOPILOT VERTICAL HOLD, Bool) if{{ (>K:AP_VS_VAR_{0}) }} els{{ (A:AUTOPILOT FLIGHT LEVEL CHANGE, Bool) "
          "if{{ (>K:AP_SPD_VAR_{1}) }} els{{ (A:AUTOPILOT PITCH HOLD, Bool) if{{ (>K:AP_PITCH_REF_INC_{2}) }} }} }}")
_NOSE_UP = _WHEEL.format("INC", "DEC", "UP")
_NOSE_DN = _WHEEL.format("DEC", "INC", "DN")
# the autopilot keys, the yaw damper, the ALT/HDG knob and STD
GARMIN_SHARED = {
    # autopilot keys
    "AP": k("AP_MASTER"),
    "ALT": k("AP_ALT_HOLD"),
    "HDG": k("AP_HDG_HOLD"),
    # Garmin's FD key does nothing while the autopilot is engaged
    "FD": "(A:AUTOPILOT MASTER, Bool) ! if{ (>K:TOGGLE_FLIGHT_DIRECTOR) }",
    "VS": _VS_KEY,
    "NAV": k("AP_NAV1_HOLD"),
    "UP": _NOSE_UP,
    "FLC": _FLC_KEY,
    "APR": k("AP_APR_HOLD"),
    "DN": _NOSE_DN,
    "VNV": _VNV_KEY,
    "LVL": LEVEL,
    # shifted keys
    "YD": k("YAW_DAMPER_TOGGLE"),
    "S_VS": _VS_KEY,
    "S_UP": _NOSE_UP,
    "S_FLC": _FLC_KEY,
    "S_DN": _NOSE_DN,
    "S_VNV": _VNV_KEY,
    # ALT/HDG knob: the selected altitude, 100 ft for a value up to 999 and 1000 ft above (AltitudeSelectManager.ts,
    # GarminAutopilot.ts), and the heading bug, whose push syncs it to the heading
    "ALT_100_UP": k("AP_ALT_VAR_INC"),
    "ALT_100_DN": k("AP_ALT_VAR_DEC"),
    "ALT_1000_UP": k("AP_ALT_VAR_INC", 1000),
    "ALT_1000_DN": k("AP_ALT_VAR_DEC", 1000),
    "HDG_1_UP": k("HEADING_BUG_INC"),
    "HDG_1_DN": k("HEADING_BUG_DEC"),
    **HEADING_FAST,
    "HDG_SYNC": SYNC,
    "BARO_STD": k("BAROMETRIC_STD_PRESSURE", 1),
}

# ---------------- the instruments round a Bendix/King autopilot (device 1) ----------------
# the heading bug, which the push syncs to the heading as on the G1000, and with SHIFT the course of NAV 1 and the
# altimeter (KOHLSMAN_INC and _DEC without an index, as the SDK's Key Events list them; STD names the first
# altimeter), as the simulator's key events; CRS CTR centres the course of NAV 1
NAV1_KNOBS = {
    "CRS_CTR": CENTRE.replace("#", "1"),
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
    "BARO_STD": k("BAROMETRIC_STD_PRESSURE", 1),      # the altimeter of index 1
}

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
    # ALT/HDG knob: the KAP 140's altitude knob (inner 100 ft, outer 1000 ft), the heading bug, the course and the
    # altimeter
    "ALT_100_UP": h("KAP140_Knob_Inner_INC"),
    "ALT_100_DN": h("KAP140_Knob_Inner_DEC"),
    "ALT_1000_UP": h("KAP140_Knob_Outer_INC"),
    "ALT_1000_DN": h("KAP140_Knob_Outer_DEC"),
    **NAV1_KNOBS,
}
_VS = "the KAP 140 has no VS key: it engages in VS, and UP and DN set the rate"
_FLC = "the KAP 140 has no FLC mode"
_VNV = "the KAP 140 has no VNAV mode"
KAP140_UNMAPPED = {
    "TEST": "the KAP 140 tests itself at power-up: it has no TEST key",
    "ARM": "the sim's KAP 140 does nothing on ARM: its KAP140.js handles KAP140_Push_ARM with an empty case",
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
KAP140_COCKPIT_UNMAPPED = {**KAP140_UNMAPPED, **LIGHTS_UNMAPPED}
