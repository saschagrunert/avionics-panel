"""G1000 NXi (Working Title) with the GFC 700 and GMA 1347, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md). What the profile does differently from the real G1000 is in
docs/using/mapping.md#g1000-nxi.

Every row is an input Working Title's G1000 NXi takes, by its source (src/workingtitle-instruments-g1000 and
src/garminsdk in microsoft/msfs-avionics-mirror, MSFS 2024 SU5). Its autopilot is Garmin's, built as the G3X
Touch's (GarminAPStateManager.ts, WTG1000_MFD.tsx), so the autopilot keys and the ALT/HDG knob are the simulator's
key events the two share (parts.GARMIN_SHARED). The PFD's CRS and BARO knobs, the MFD's RANGE knob, FMS keys, FMS
knob and joystick are the H: events the NXi takes for them (CourseKnobInputHandler.ts, Altimeter.tsx,
MFDViewService.ts); it takes no H: event for a long press of CLR. The CDI and OBS are the simulator's key events
the NXi follows (ActiveNavSourceManager.ts, LNavObsManager.ts); the radios, ADF, transponder and audio panel are
the parts the tables share (parts.py). The keys without an amber legend and the RANGE knob send the plain function
with SHIFT too, so a stray SHIFT does no harm (docs/using/mapping.md#two-joysticks).
"""
from mobiflight.families import parts
from mobiflight.families.rpn import h, k

NAME = "G1000 NXi"

# what the CDI shows, as the NXi's PFD keeps it in L:PFD_CDI_Source on every change and at start (HSI.tsx): 3 for
# GPS, 1 or 2 for NAV 1 or NAV 2. AUTOPILOT NAV SELECTED would not do: the NXi may start its CDI on NAV 1 without
# writing it (NavProcessor.ts, initCdi).
_SOURCE = "(L:PFD_CDI_Source, Number)"


def _shows(gps, radio):
    """The code for what the CDI shows: gps for the GPS, radio for a NAV radio (# for its number)"""
    return (f"{_SOURCE} 3 == if{{ {gps} }} "
            f"els{{ {_SOURCE} 2 == if{{ {radio.replace('#', '2')} }} els{{ {radio.replace('#', '1')} }} }}")


# the CDI softkey's cycle, GPS, NAV 1, NAV 2, GPS: the NXi selects a NAV radio on AP_NAV_SELECT_SET and GPS on
# TOGGLE_GPS_DRIVES_NAV1, which alone would never select NAV 2 (ActiveNavSourceManager.ts, NavProcessor.ts)
_NAV1, _NAV2, _GPS = k("AP_NAV_SELECT_SET", 1), k("AP_NAV_SELECT_SET", 2), k("TOGGLE_GPS_DRIVES_NAV1")
_CDI = f"{_SOURCE} 3 == if{{ {_NAV1} }} els{{ {_SOURCE} 1 == if{{ {_NAV2} }} els{{ {_GPS} }} }}"

_UNIT = {
    "CDI": _CDI,
    # the OBS softkey's mode: the NXi follows the sim's GPS OBS (LNavObsManager.ts, GarminObsLNavModule.ts)
    "OBS": k("GPS_OBS"),
    "FPL": h("AS1000_MFD_FPL_Push"),
    "DIRECT": h("AS1000_MFD_DIRECTTO"),
    "MENU": h("AS1000_MFD_MENU_Push"),
    "PROC": h("AS1000_MFD_PROC_Push"),
    "CLR": h("AS1000_MFD_CLR"),
    "ENT": h("AS1000_MFD_ENT_Push"),
    "S_ENT": h("AS1000_MFD_ENT_Push"),
    "FMS_OUTER_CW": h("AS1000_MFD_FMS_Lower_INC"),
    "FMS_OUTER_CCW": h("AS1000_MFD_FMS_Lower_DEC"),
    "FMS_INNER_CW": h("AS1000_MFD_FMS_Upper_INC"),
    "FMS_INNER_CCW": h("AS1000_MFD_FMS_Upper_DEC"),
    "FMS_CRSR": h("AS1000_MFD_FMS_Upper_PUSH"),
    **parts.ADF,
}
_UNIT_UNMAPPED = {
    "HOME": "the G1000 has no HOME key: free for your own mapping (docs/using/compatibility.md)",
    "VNAV": "the G1000 has no VNAV key: the autopilot's VNV key is the panel's VNV",
    "MSG": "softkeys are positional: a fixed softkey is ALERTS only at the PFD's top level",
    "NRST": "softkeys are positional: a fixed softkey is NRST only at the PFD's top level",
    "TERR": "the G1000 has no TERR key: the terrain page is in the MFD's map pages (FMS knob)",
    "MAP": "the G1000 NXi takes no long CLR press from outside: Working Title's source handles no H: event for it",
    **parts.RADIO_UNMAPPED,
}

_DEVICE1 = {
    # the autopilot keys, NOSE UP and NOSE DN, the yaw damper, the ALT/HDG knob and STD (parts.py), with BC
    **parts.GARMIN_SHARED,
    "BC": k("AP_BC_HOLD"),
    # the PFD's CRS knob and its push (CourseKnobInputHandler.ts): the course of the GPS's OBS or of the NAV radio
    # the CDI shows, and its push centres it; and its BARO knob (Altimeter.tsx)
    "CRS_CTR": h("AS1000_PFD_CRS_PUSH"),
    "CRS_1_UP": h("AS1000_PFD_CRS_INC"),
    "CRS_1_DN": h("AS1000_PFD_CRS_DEC"),
    **parts.course_fast(_shows),
    "BARO_UP": h("AS1000_PFD_BARO_INC"),
    "BARO_DN": h("AS1000_PFD_BARO_DEC"),
    # audio (GMA 1347): the simulator's audio panel
    **parts.AUDIO,
    # RANGE knob and joystick, on the MFD; clockwise zooms out, as on the G1000: RANGE_INC steps the map to its next
    # range (MFDNavMapPage.tsx)
    "RANGE_CW": h("AS1000_MFD_RANGE_INC"),
    "RANGE_CCW": h("AS1000_MFD_RANGE_DEC"),
    "PAN_UP": h("AS1000_MFD_JOYSTICK_UP"),
    "PAN_DN": h("AS1000_MFD_JOYSTICK_DOWN"),
    "PAN_LEFT": h("AS1000_MFD_JOYSTICK_LEFT"),
    "PAN_RIGHT": h("AS1000_MFD_JOYSTICK_RIGHT"),
    "PTR": h("AS1000_MFD_JOYSTICK_PUSH"),
    "S_RANGE_CW": h("AS1000_MFD_RANGE_INC"),
    "S_RANGE_CCW": h("AS1000_MFD_RANGE_DEC"),
    "S_PAN_UP": h("AS1000_MFD_JOYSTICK_UP"),
    "S_PAN_DN": h("AS1000_MFD_JOYSTICK_DOWN"),
    "S_PAN_LEFT": h("AS1000_MFD_JOYSTICK_LEFT"),
    "S_PAN_RIGHT": h("AS1000_MFD_JOYSTICK_RIGHT"),
    "S_PTR": h("AS1000_MFD_JOYSTICK_PUSH"),
    **parts.SQUAWK,
    # unit 1: radio 1
    **_UNIT,
    **parts.RADIO[1],
    **parts.LIGHTS,
}

_DEVICE2 = {**_UNIT, **parts.RADIO[2]}

DEVICE = {1: _DEVICE1, 2: _DEVICE2}
UNMAPPED = {
    1: {
        "TEST": "the GFC 700 has no TEST key",
        "ARM": "the GFC 700 has no ARM key",
        "GPSS": "the GFC 700 flies GPS steering in NAV mode",
        "HALF_BANK": "no G1000 NXi aircraft in MSFS has a low-bank key",
        **_UNIT_UNMAPPED,
        **parts.LIGHTS_UNMAPPED,
    },
    2: _UNIT_UNMAPPED,
}
