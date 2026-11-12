"""G1000 NXi (Working Title) with the GFC 700 and GMA 1347, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md). What the profile does differently from the real G1000 is in
docs/using/mapping.md#g1000-nxi.

The autopilot keys, the PFD's knobs and the MFD's RANGE knob are the input events MSFS 2024's G1000 aircraft
define (B:AS1000_*, which the sim also lists for binding in the aircraft's controls: AS1000_HEADING_PFD_INC and
so on). The MFD's FMS keys, FMS knob and joystick are the H: events Working Title's G1000 NXi takes for them
(MFDViewService.ts in microsoft/msfs-avionics-mirror, MSFS 2024 SU5); it takes no H: event for a long press of
CLR. The rest is the simulator's own key events, which the NXi follows (it intercepts TOGGLE_GPS_DRIVES_NAV1 for
the CDI and BAROMETRIC_STD_PRESSURE, and its autopilot the leveler events of LVL), with the radios, ADF,
transponder and audio panel the parts the tables share (parts.py). The keys without an amber legend and the RANGE
knob send the plain function with SHIFT too, so a stray SHIFT does no harm (docs/using/mapping.md#two-joysticks).
"""
from mobiflight.families import parts
from mobiflight.families.rpn import b, h, k

NAME = "G1000 NXi"

_UNIT = {
    "CDI": k("TOGGLE_GPS_DRIVES_NAV1"),
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
    "OBS": "softkeys are positional: a fixed softkey is OBS only at the PFD's top level",
    "VNAV": "the G1000 has no VNAV key: the autopilot's VNV key is the panel's VNV",
    "MSG": "softkeys are positional: a fixed softkey is ALERTS only at the PFD's top level",
    "NRST": "softkeys are positional: a fixed softkey is NRST only at the PFD's top level",
    "TERR": "the G1000 has no TERR key: the terrain page is in the MFD's map pages (FMS knob)",
    "MAP": "the G1000 NXi takes no long CLR press from outside: Working Title's source handles no H: event for it",
    **parts.RADIO_UNMAPPED,
}

_DEVICE1 = {
    # autopilot keys
    "AP": b("AS1000_AUTOPILOT_AP_PFD_TOGGLE"),
    "ALT": b("AS1000_AUTOPILOT_ALTITUDE_PFD_TOGGLE"),
    "HDG": b("AS1000_AUTOPILOT_HEADING_PFD_TOGGLE"),
    "FD": b("AS1000_AUTOPILOT_FD_PFD_TOGGLE"),
    "VS": b("AS1000_AUTOPILOT_VERTICALSPEED_PFD_TOGGLE"),
    "NAV": b("AS1000_AUTOPILOT_NAVIGATION_PFD_TOGGLE"),
    "UP": b("AS1000_AUTOPILOT_VERTICALSPEED_UP_PFD_PUSH"),         # NOSE UP
    "FLC": b("AS1000_AUTOPILOT_FLIGHTLEVELCHANGE_PFD_TOGGLE"),
    "APR": b("AS1000_AUTOPILOT_APPROACH_PFD_TOGGLE"),
    "DN": b("AS1000_AUTOPILOT_VERTICALSPEED_DOWN_PFD_PUSH"),       # NOSE DN
    "VNV": b("AS1000_AUTOPILOT_VERTICAL_NAVIGATION_PFD_TOGGLE"),
    "LVL": parts.LEVEL,
    # audio (GMA 1347): the simulator's audio panel
    **parts.AUDIO,
    # shifted keys
    "CRS_CTR": b("AS1000_COURSE_PUSH_PFD_PUSH"),
    "YD": k("YAW_DAMPER_TOGGLE"),
    "S_VS": b("AS1000_AUTOPILOT_VERTICALSPEED_PFD_TOGGLE"),
    "S_UP": b("AS1000_AUTOPILOT_VERTICALSPEED_UP_PFD_PUSH"),
    "S_FLC": b("AS1000_AUTOPILOT_FLIGHTLEVELCHANGE_PFD_TOGGLE"),
    "BC": b("AS1000_AUTOPILOT_BACKCOURSE_PFD_TOGGLE"),
    "S_DN": b("AS1000_AUTOPILOT_VERTICALSPEED_DOWN_PFD_PUSH"),
    "S_VNV": b("AS1000_AUTOPILOT_VERTICAL_NAVIGATION_PFD_TOGGLE"),
    # ALT/HDG knob: the G1000's ALT knob (inner 100 ft, outer 1000 ft) and HDG knob; with SHIFT CRS/BARO
    "ALT_100_UP": b("AS1000_ALTITUDE_INNER_PFD_Inc", 1),
    "ALT_100_DN": b("AS1000_ALTITUDE_INNER_PFD_Dec", 1),
    "ALT_1000_UP": b("AS1000_ALTITUDE_OUTER_PFD_Inc", 1),
    "ALT_1000_DN": b("AS1000_ALTITUDE_OUTER_PFD_Dec", 1),
    "HDG_1_UP": b("AS1000_HEADING_PFD_Inc", 1),
    "HDG_1_DN": b("AS1000_HEADING_PFD_Dec", 1),
    **parts.HEADING_FAST,
    "HDG_SYNC": b("AS1000_HEADING_SYNC_PFD_PUSH"),
    "CRS_1_UP": b("AS1000_COURSE_PFD_Inc", 1),
    "CRS_1_DN": b("AS1000_COURSE_PFD_Dec", 1),
    # 1° too: a faster step would set NAV 1's course whatever the CDI follows (GPS, NAV 1 or NAV 2)
    "CRS_10_UP": b("AS1000_COURSE_PFD_Inc", 1),
    "CRS_10_DN": b("AS1000_COURSE_PFD_Dec", 1),
    "BARO_UP": b("AS1000_BARO_PFD_Inc", 1),
    "BARO_DN": b("AS1000_BARO_PFD_Dec", 1),
    "BARO_STD": k("BAROMETRIC_STD_PRESSURE"),
    # RANGE knob and joystick, on the MFD; clockwise zooms out, as on the G1000
    "RANGE_CW": b("AS1000_RANGE_ZOOM_MFD_Inc", 1),
    "RANGE_CCW": b("AS1000_RANGE_ZOOM_MFD_Dec", 1),
    "PAN_UP": h("AS1000_MFD_JOYSTICK_UP"),
    "PAN_DN": h("AS1000_MFD_JOYSTICK_DOWN"),
    "PAN_LEFT": h("AS1000_MFD_JOYSTICK_LEFT"),
    "PAN_RIGHT": h("AS1000_MFD_JOYSTICK_RIGHT"),
    "PTR": h("AS1000_MFD_JOYSTICK_PUSH"),
    "S_RANGE_CW": b("AS1000_RANGE_ZOOM_MFD_Inc", 1),
    "S_RANGE_CCW": b("AS1000_RANGE_ZOOM_MFD_Dec", 1),
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
        **parts.SQUAWK_UNMAPPED,
        **_UNIT_UNMAPPED,
        **parts.LIGHTS_UNMAPPED,
    },
    2: _UNIT_UNMAPPED,
}
