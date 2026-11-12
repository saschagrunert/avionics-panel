"""G1000 NXi (Working Title) with the GFC 700 and GMA 1347, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md) as HubHop presets. What the profile does differently
from the real G1000 is in docs/using/mapping.md#g1000-nxi.

Presets in this order of preference: HubHop's MSFS 2024 G1000 input events (B:AS1000_*, "G1000 (2024)"), the
simulator's own key events (K:), which act the same in every aircraft, Working Title's G1000 NXi presets
(audio panel) and the G1000 H: events. Only the first group is marked for MSFS 2024 in HubHop. The radios, ADF
and transponder are the K: parts the tables share (parts.py). The keys without an amber legend and the RANGE
knob send the plain function with SHIFT too, so a stray SHIFT does no harm
(docs/using/mapping.md#two-joysticks).
"""
from mobiflight.families import parts

NAME = "G1000 NXi"

B = "Microsoft.G1000 (2024)."              # MSFS 2024 input events
GEN = parts.GEN
WT = "Working Title.G1000 NXi."

_UNIT = {
    "CDI": GEN + "TOGGLE_GPS_DRIVES_NAV1",
    "FPL": GEN + "AS1000_MFD_FPL_Push",
    "DIRECT": GEN + "AS1000_MFD_DIRECTTO",
    "MENU": GEN + "AS1000_MFD_MENU_Push",
    "PROC": GEN + "AS1000_MFD_PROC_Push",
    "CLR": GEN + "AS1000_MFD_CLR",
    "ENT": GEN + "AS1000_MFD_ENT_Push",
    "MAP": GEN + "AS1000_MFD_CLR_Long",                    # hold CLR
    "S_ENT": GEN + "AS1000_MFD_ENT_Push",
    "FMS_OUTER_CW": GEN + "AS1000_MFD_FMS_Lower_INC",
    "FMS_OUTER_CCW": GEN + "AS1000_MFD_FMS_Lower_DEC",
    "FMS_INNER_CW": GEN + "AS1000_MFD_FMS_Upper_INC",
    "FMS_INNER_CCW": GEN + "AS1000_MFD_FMS_Upper_DEC",
    "FMS_CRSR": GEN + "AS1000_MFD_FMS_Upper_PUSH",
    **parts.ADF,
}
_UNIT_UNMAPPED = {
    "HOME": "the G1000 has no HOME key: free for your own mapping (docs/using/compatibility.md)",
    "OBS": "softkeys are positional: a fixed softkey is OBS only at the PFD's top level",
    "VNAV": "the G1000 has no VNAV key (HubHop's AS1000_VNAV_TOGGLE switches VNAV on and off, not a page)",
    "MSG": "softkeys are positional: a fixed softkey is ALERTS only at the PFD's top level",
    "NRST": "softkeys are positional: a fixed softkey is NRST only at the PFD's top level",
    "TERR": "the G1000 has no TERR key: the terrain page is in the MFD's map pages (FMS knob)",
    **parts.RADIO_UNMAPPED,
}

_DEVICE1 = {
    # autopilot keys
    "AP": B + "AP - Toggle",
    "ALT": B + "ALT - Toggle",
    "HDG": B + "HDG - Toggle",
    "FD": B + "FD - Toggle",
    "VS": B + "VS - Toggle",
    "NAV": B + "NAV - Toggle",
    "UP": B + "Vertical speed up - Push",                 # NOSE UP
    "FLC": B + "FLC - Toggle",
    "APR": B + "APP - Toggle",
    "DN": B + "Vertical speed down - Push",               # NOSE DN
    "VNV": B + "VNV - Toggle",
    "LVL": GEN + "AP_WING_LEVELER",
    # audio (GMA 1347)
    "MIC1": WT + "Mid COM1 Mic Button Push",
    "COM1": WT + "Mid COM1 Button Push",
    "MIC2": WT + "Mid COM2 Mic Button Push",
    "COM2": WT + "Mid COM2 Button Push",
    # shifted keys
    "CRS_CTR": B + "CRS - Direct push",
    "YD": GEN + "YAW_DAMPER_TOGGLE",
    "S_VS": B + "VS - Toggle",
    "S_UP": B + "Vertical speed up - Push",
    "S_FLC": B + "FLC - Toggle",
    "BC": B + "BC - Toggle",
    "S_DN": B + "Vertical speed down - Push",
    "S_VNV": B + "VNV - Toggle",
    "ADF_AUDIO": WT + "Mid ADF Push",
    "NAV1_AUDIO": WT + "Mid NAV1 Push",
    "DME_AUDIO": WT + "Mid DME Push",
    "NAV2_AUDIO": WT + "Mid NAV 2 Push",
    # ALT/HDG knob: the G1000's ALT knob (inner 100 ft, outer 1000 ft) and HDG knob; with SHIFT CRS/BARO
    "ALT_100_UP": B + "ALT - Inner inc",
    "ALT_100_DN": B + "ALT - Inner dec",
    "ALT_1000_UP": B + "ALT - Outer inc",
    "ALT_1000_DN": B + "ALT - Outer dec",
    "HDG_1_UP": B + "HDG - Inc",
    "HDG_1_DN": B + "HDG - Dec",
    "HDG_10_UP": GEN + "AS1000_PFD_HEADING_FAST_INC",      # 5°: no 10° preset
    "HDG_10_DN": GEN + "AS1000_PFD_HEADING_FAST_DEC",
    "HDG_SYNC": B + "HDG - Sync push",
    "CRS_1_UP": B + "CRS - Inc",
    "CRS_1_DN": B + "CRS - Dec",
    "CRS_10_UP": B + "CRS - Inc",                         # 1°: no faster course preset
    "CRS_10_DN": B + "CRS - Dec",
    "BARO_UP": B + "BARO - Inc",
    "BARO_DN": B + "BARO - Dec",
    "BARO_STD": GEN + "BAROMETRIC STD PRESSURE",
    # RANGE knob and joystick, on the MFD; clockwise zooms out, as on the G1000
    "RANGE_CW": B + "MFD RANGE ZOOM - Inc",
    "RANGE_CCW": B + "MFD RANGE ZOOM - Dec",
    "PAN_UP": GEN + "AS1000_MFD_JOYSTICK_UP",
    "PAN_DN": GEN + "AS1000_MFD_JOYSTICK_DOWN",
    "PAN_LEFT": GEN + "AS1000_MFD_JOYSTICK_LEFT",
    "PAN_RIGHT": GEN + "AS1000_MFD_JOYSTICK_RIGHT",
    "PTR": GEN + "AS1000_MFD_JOYSTICK_PUSH",
    "S_RANGE_CW": B + "MFD RANGE ZOOM - Inc",
    "S_RANGE_CCW": B + "MFD RANGE ZOOM - Dec",
    "S_PAN_UP": GEN + "AS1000_MFD_JOYSTICK_UP",
    "S_PAN_DN": GEN + "AS1000_MFD_JOYSTICK_DOWN",
    "S_PAN_LEFT": GEN + "AS1000_MFD_JOYSTICK_LEFT",
    "S_PAN_RIGHT": GEN + "AS1000_MFD_JOYSTICK_RIGHT",
    "S_PTR": GEN + "AS1000_MFD_JOYSTICK_PUSH",
    **parts.SQUAWK,
    # unit 1: radio 1
    **_UNIT,
    **parts.RADIO[1],
    "COM_121_5": GEN + "AS1000_PFD_COM_Switch_Long",       # hold COM ⇆
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
    2: {
        **_UNIT_UNMAPPED,
        "COM_121_5": "no HubHop preset tunes COM 2 to 121.5 (the G1000's long COM ⇆ press acts on the COM in "
                     "the tuning box)",
    },
}
