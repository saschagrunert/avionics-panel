"""Garmin GFC 500 with the Working Title G3X Touch, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md), as in the CubCrafters XCub and NX Cub (one G3X Touch, a
GMC 507) and the Draco X (PFD and MFD). Unit 1 is the G3X Touch of index 1 (the PFD, or the only display) with
COM 1 / NAV 1, unit 2 the one of index 2 (the MFD) with COM 2 / NAV 2. What the profile does differently from the
real units is in docs/using/mapping.md#gfc-500-and-g3x-touch.

Sources, in Working Title's msfs-avionics-mirror for MSFS 2024 (SU5): the G3X Touch's H events (docs "G3X Touch H
Event List"; case-sensitive, UiInteractionMapper.ts) and the code that takes them (src/workingtitle-instruments-
g3x-touch, src/garminsdk, src/sdk). The G3X Touch builds the GFC 500 from Garmin's autopilot (GarminAutopilot,
GarminAPStateManager), which takes the sim's key events, so the autopilot keys send what the G3X's own AFCS page
sends (MFD/Views/AfcsControlsView/AfcsControlsView.tsx) and the knobs what its PFD knobs send
(GduDisplay/Gdu460/PfdInstruments/Gdu460PfdInstrumentsView.tsx). Key events and simulation variables as in the
MSFS 2024 SDK. The radios, ADF, transponder, audio panel and cabin light are the parts the tables share (parts.py).
"""
from mobiflight.families import parts
from mobiflight.families.rpn import h, k, turn

NAME = "GFC 500 and G3X Touch"


def _gdu(index):
    """The bezel of the G3X Touch (GDU 460) of this index: D→, MENU, BACK as CLR, NRST and the right-hand dual
    knob, which works the MFD pane in split screen"""
    p = f"AS3X_Touch_{index}_"
    return {
        "DIRECT": h(p + "DirectTo_Push"),
        "MENU": h(p + "Menu_Push"),
        "CLR": h(p + "Back_Push"),
        "NRST": h(p + "NRST_Push"),
        "FMS_OUTER_CW": h(p + "Knob_Outer_R_INC"),
        "FMS_OUTER_CCW": h(p + "Knob_Outer_R_DEC"),
        "FMS_INNER_CW": h(p + "Knob_Inner_R_INC"),
        "FMS_INNER_CCW": h(p + "Knob_Inner_R_DEC"),
        "FMS_CRSR": h(p + "Knob_Inner_R_PUSH"),
    }


def _nav(code):
    """The code for the NAV radio the CDI shows, # for its number. With an autopilot the G3X keeps GPS DRIVES NAV1
    and AUTOPILOT NAV SELECTED on its CDI (ActiveNavSourceManager.ts)."""
    return f"(A:AUTOPILOT NAV SELECTED, Number) 2 == if{{ {code.replace('#', '2')} }} els{{ {code.replace('#', '1')} }}"


def _cdi(gps, nav):
    """The code for what the CDI shows: gps for the G3X's GPS, nav for a NAV radio"""
    return f"(A:GPS DRIVES NAV1, Bool) if{{ {gps} }} els{{ {_nav(nav)} }}"


# the one CDI, which the key switches between GPS and NAV 1 while the G3X flies its own flight plan
# (ActiveNavSourceManager.ts), and the GPS's OBS mode, from both units
_CDI = {"CDI": k("TOGGLE_GPS_DRIVES_NAV1"), "OBS": k("GPS_OBS")}
# the GMC 507's nose up/down wheel sets the reference of the active vertical mode, as the G3X's own AFCS page does:
# VS, then IAS (nose up slows it), then pitch; Working Title's directors set these A: flags
# (APVSDirector.ts, APFLCDirector.ts, APPitchDirector.ts)
_WHEEL = ("(A:AUTOPILOT VERTICAL HOLD, Bool) if{{ (>K:AP_VS_VAR_{0}) }} els{{ (A:AUTOPILOT FLIGHT LEVEL CHANGE, Bool) "
          "if{{ (>K:AP_SPD_VAR_{1}) }} els{{ (A:AUTOPILOT PITCH HOLD, Bool) if{{ (>K:AP_PITCH_REF_INC_{2}) }} }} }}")
_NOSE_UP = _WHEEL.format("INC", "DEC", "UP")
_NOSE_DN = _WHEEL.format("DEC", "INC", "DN")
_VS = k("AP_VS_HOLD")
_IAS = k("FLIGHT_LEVEL_CHANGE")
_VNV = h("AS1000_VNAV_TOGGLE")                      # GarminAPStateManager.ts toggles VNAV on this H event
# CRS CTR: the course to the VOR, or the localizer's, on the NAV the CDI shows, as the G3X's Course knob push sets it
_CENTRE = ("(A:NAV HAS LOCALIZER:#, Bool) if{ (A:NAV LOCALIZER:#, degrees) near dnor (>K:VOR#_SET) } "
           "els{ (A:NAV HAS NAV:#, Bool) if{ (A:NAV RADIAL:#, degrees) 180 + near dnor (>K:VOR#_SET) } }")

_AFCS = {
    # autopilot keys
    "AP": k("AP_MASTER"),
    "ALT": k("AP_ALT_HOLD"),
    "HDG": k("AP_HDG_HOLD"),
    # the GMC 507's FD key does nothing while the autopilot is engaged
    "FD": "(A:AUTOPILOT MASTER, Bool) ! if{ (>K:TOGGLE_FLIGHT_DIRECTOR) }",
    "VS": _VS,
    "NAV": k("AP_NAV1_HOLD"),
    "UP": _NOSE_UP,
    "FLC": _IAS,
    "APR": k("AP_APR_HOLD"),
    "DN": _NOSE_DN,
    "VNV": _VNV,
    "LVL": parts.LEVEL,
    # shifted keys
    "CRS_CTR": f"(A:GPS DRIVES NAV1, Bool) ! if{{ {_nav(_CENTRE)} }}",
    "YD": k("YAW_DAMPER_TOGGLE"),
    "S_VS": _VS,
    "S_UP": _NOSE_UP,
    "S_FLC": _IAS,
    "S_DN": _NOSE_DN,
    "S_VNV": _VNV,
    # ALT/HDG knob: the selected altitude, 100 ft for a value up to 999 and 1000 ft above (AltitudeSelectManager.ts,
    # GarminAutopilot.ts), and the heading bug, whose push syncs it to the heading as the G3X's knob does; with SHIFT
    # the course of what the CDI shows and the altimeter of index 1, the G3X's (GduDefsConfig.ts)
    "ALT_100_UP": k("AP_ALT_VAR_INC"),
    "ALT_100_DN": k("AP_ALT_VAR_DEC"),
    "ALT_1000_UP": k("AP_ALT_VAR_INC", 1000),
    "ALT_1000_DN": k("AP_ALT_VAR_DEC", 1000),
    "HDG_1_UP": k("HEADING_BUG_INC"),
    "HDG_1_DN": k("HEADING_BUG_DEC"),
    **parts.HEADING_FAST,
    "HDG_SYNC": parts.SYNC,
    # the G3X's GPS follows the sim's GPS OBS (use-sim-obs by default: FmsConfig.ts, GarminObsLNavModule.ts)
    "CRS_1_UP": _cdi(k("GPS_OBS_INC"), k("VOR#_OBI_INC")),
    "CRS_1_DN": _cdi(k("GPS_OBS_DEC"), k("VOR#_OBI_DEC")),
    "CRS_10_UP": _cdi(turn("GPS OBS VALUE", "GPS_OBS_SET", 10), turn("NAV OBS:#", "VOR#_SET", 10)),
    "CRS_10_DN": _cdi(turn("GPS OBS VALUE", "GPS_OBS_SET", -10), turn("NAV OBS:#", "VOR#_SET", -10)),
    "BARO_UP": k("KOHLSMAN_INC", 1),
    "BARO_DN": k("KOHLSMAN_DEC", 1),
    "BARO_STD": k("BAROMETRIC_STD_PRESSURE", 1),
}

_TOUCH = "a touchscreen function of the G3X Touch: its bezel has only D→, MENU, BACK (CLR), NRST and the knobs"
_UNIT_UNMAPPED = {
    "HOME": "the G3X Touch has no HOME key: free for your own mapping (docs/using/compatibility.md)",
    "PROC": "the G3X Touch is VFR only: it loads no procedures",
    **dict.fromkeys(("FPL", "ENT", "S_ENT", "VNAV", "MSG", "TERR", "MAP"), _TOUCH),
    **parts.RADIO_UNMAPPED,
}

DEVICE = {
    1: {
        **_AFCS,
        **parts.AUDIO,
        **parts.SQUAWK,
        **parts.LIGHTS,
        # unit 1: the G3X Touch of index 1, radio 1
        **_gdu(1),
        **_CDI,
        **parts.RADIO[1],
        **parts.ADF,
    },
    2: {**_gdu(2), **_CDI, **parts.RADIO[2], **parts.ADF},
}
UNMAPPED = {
    1: {
        "TEST": "the GFC 500 tests itself at power-up: it has no TEST key",
        "ARM": "the GFC 500 has no ARM key",
        "GPSS": "the GFC 500 flies GPS steering in NAV mode",
        "BC": "the GFC 500 has no BC key",
        "HALF_BANK": "the GFC 500 has no low-bank key",
        **dict.fromkeys(parts.RANGE_KNOB, "the G3X Touch zooms its map with the inner FMS knob on the map page and "
                                          "pans it on the touchscreen"),
        **parts.SQUAWK_UNMAPPED,
        **_UNIT_UNMAPPED,
        **parts.LIGHTS_UNMAPPED,
    },
    2: _UNIT_UNMAPPED,
}
