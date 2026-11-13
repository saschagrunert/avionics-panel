"""G1000 NXi (Working Title) with the GFC 700 and GMA 1347, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md). What the profile does differently from the real G1000 is in
docs/using/mapping.md#g1000-nxi.

Every row is an input Working Title's G1000 NXi takes, by its source (src/workingtitle-instruments-g1000 and
src/garminsdk in microsoft/msfs-avionics-mirror, MSFS 2024 SU5). Its autopilot is Garmin's, built as the G3X
Touch's (GarminAPStateManager.ts, WTG1000_MFD.tsx), so the autopilot keys and the ALT/HDG knob are the simulator's
key events the two share (parts.GARMIN_SHARED). The PFD's CRS and BARO knobs, the FMS keys and knobs of the MFD (unit
1) and the PFD (unit 2), the RANGE knobs and joysticks of the MFD and, with SHIFT, of the PFD, and the softkeys are the
H: events the NXi takes for them (CourseKnobInputHandler.ts, Altimeter.tsx, MFDViewService.ts, PFDViewService.ts,
MapInset.tsx, SoftKeyMenuSystem.ts); it takes no H: event for a long press of CLR. The CDI and OBS are the
simulator's key events the NXi follows (ActiveNavSourceManager.ts, LNavObsManager.ts); the radios, ADF, transponder
and audio panel are the parts the tables share (parts.py). The keys without an amber legend send the plain function
with SHIFT too, so a stray SHIFT does no harm (docs/using/mapping.md#two-joysticks).
"""
from mobiflight.families import parts
from mobiflight.families.rpn import h, k, lset

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


def _fms(display):
    """The FMS keys and the FMS knob of the MFD or the PFD ("MFD", "PFD"); ENT with SHIFT too"""
    p = f"AS1000_{display}_"
    return {
        "FPL": h(p + "FPL_Push"),
        "DIRECT": h(p + "DIRECTTO"),
        "MENU": h(p + "MENU_Push"),
        "PROC": h(p + "PROC_Push"),
        "CLR": h(p + "CLR"),
        "ENT": h(p + "ENT_Push"),
        "S_ENT": h(p + "ENT_Push"),
        "FMS_OUTER_CW": h(p + "FMS_Lower_INC"),
        "FMS_OUTER_CCW": h(p + "FMS_Lower_DEC"),
        "FMS_INNER_CW": h(p + "FMS_Upper_INC"),
        "FMS_INNER_CCW": h(p + "FMS_Upper_DEC"),
        "FMS_CRSR": h(p + "FMS_Upper_PUSH"),
    }


def _range(display, shift=""):
    """The RANGE knob and joystick of the MFD or the PFD; clockwise zooms out, as on the G1000: RANGE_INC steps the
    map to its next range (MFDNavMapPage.tsx, MapInset.tsx). The PFD's work its inset map, while it shows."""
    p = f"AS1000_{display}_"
    return {
        f"{shift}RANGE_CW": h(p + "RANGE_INC"),
        f"{shift}RANGE_CCW": h(p + "RANGE_DEC"),
        f"{shift}PAN_UP": h(p + "JOYSTICK_UP"),
        f"{shift}PAN_DN": h(p + "JOYSTICK_DOWN"),
        f"{shift}PAN_LEFT": h(p + "JOYSTICK_LEFT"),
        f"{shift}PAN_RIGHT": h(p + "JOYSTICK_RIGHT"),
        f"{shift}PTR": h(p + "JOYSTICK_PUSH"),
    }


# STD: BAROMETRIC_STD_PRESSURE only ever sets STD in the NXi (AltimeterBaroKeyEventHandler.ts), and a second one would
# store 29.92 as the setting to return to. Where the altimeter is within half a hPa of 29.92 inHg (1013.2 hPa), as in
# STD, the push presses the PFD's PFD Opt and STD Baro softkeys instead, which toggle STD and, leaving it, return to
# the setting before it (RootMenu.ts, PFDOptMenu.ts, Altimeter.tsx). PFD Opt is the 4th softkey at the top level of
# the PFD's softkeys, where they mostly are, and STD Baro the 10th in PFD Opt; from another of its menus the two
# presses do other things.
_STD = (f"(A:KOHLSMAN SETTING MB:1, millibars) 1013.2 - abs 0.5 < "
        f"if{{ {h('AS1000_PFD_SOFTKEYS_4')} {h('AS1000_PFD_SOFTKEYS_10')} }} "
        f"els{{ {k('BAROMETRIC_STD_PRESSURE', 1)} }}")

# HOME toggles the MFD's engine menu: ENGINE, its first softkey at the top level of its softkeys (MFDRootMenu.ts),
# then BACK, the 11th in the engine, lean and system menus (EngineMenu.ts, LeanMenu.ts, SystemMenu.ts). The NXi
# shows no variable for its menu, so HOME keeps which it sent last in an L: variable of its own; after the menu is
# left another way, its next press sends BACK, which on the map page toggles Charts (below), and the one after
# ENGINE again.
_ENGINE = "(L:AvionicsPanel_G1000_Engine, Bool)"
_HOME = (f"{_ENGINE} if{{ {h('AS1000_MFD_SOFTKEYS_11')} {lset('AvionicsPanel_G1000_Engine', 0)} }} "
         f"els{{ {h('AS1000_MFD_SOFTKEYS_1')} {lset('AvionicsPanel_G1000_Engine', 1)} }}")

_UNIT = {
    "CDI": _CDI,
    # the OBS softkey's mode: the NXi follows the sim's GPS OBS (LNavObsManager.ts, GarminObsLNavModule.ts)
    "OBS": k("GPS_OBS"),
    "HOME": _HOME,
    # MAP: the 11th softkey, Charts at the top level of the map page's softkeys. MFDNavMapRootMenu.ts names it, and
    # the 12th Checklist, without a handler for either, which leaves both disabled there (SoftKeyMenu.ts); in MSFS 2024
    # Charts toggles all the same, as seen in the sim, and Checklist is assumed to work as it does
    "MAP": h("AS1000_MFD_SOFTKEYS_11"),
    # TERR and VNAV: the 12th and the 10th, Checklist and Detail there, which steps through the map's four declutter
    # levels and round (MFDNavMapRootMenu.ts); MSG and NRST: the PFD's 12th and 11th, Alerts and Nearest at the top
    # level of its softkeys (RootMenu.ts; in PFD Opt the 12th does nothing and the 11th is Back: PFDOptMenu.ts). Each
    # of the PFD's opens its window, and closes it again when it shows (PFDViewService.ts).
    "TERR": h("AS1000_MFD_SOFTKEYS_12"),
    "VNAV": h("AS1000_MFD_SOFTKEYS_10"),
    "MSG": h("AS1000_PFD_SOFTKEYS_12"),
    "NRST": h("AS1000_PFD_SOFTKEYS_11"),
    **parts.ADF,
}
_UNIT_UNMAPPED = {
    **parts.RADIO_UNMAPPED,
}

_DEVICE1 = {
    # the autopilot keys, NOSE UP and NOSE DN, the yaw damper and the ALT/HDG knob (parts.py), with BC
    **parts.GARMIN_SHARED,
    "BC": k("AP_BC_HOLD"),
    # ARM: the PFD's 10th softkey, Tmr/Ref at the top level of its softkeys, where the minimums are set; it opens the
    # window and closes it again (RootMenu.ts, PFDViewService.ts)
    "ARM": h("AS1000_PFD_SOFTKEYS_10"),
    # the PFD's CRS knob and its push (CourseKnobInputHandler.ts): the course of the GPS's OBS or of the NAV radio
    # the CDI shows, and its push centres it; and its BARO knob (Altimeter.tsx)
    "CRS_CTR": h("AS1000_PFD_CRS_PUSH"),
    "CRS_1_UP": h("AS1000_PFD_CRS_INC"),
    "CRS_1_DN": h("AS1000_PFD_CRS_DEC"),
    **parts.course_fast(_shows),
    "BARO_UP": h("AS1000_PFD_BARO_INC"),
    "BARO_DN": h("AS1000_PFD_BARO_DEC"),
    "BARO_STD": _STD,
    # audio (GMA 1347): the simulator's audio panel
    **parts.AUDIO,
    # RANGE knob and joystick, on the MFD; with SHIFT the PFD's, on its inset map
    **_range("MFD"),
    **_range("PFD", "S_"),
    **parts.SQUAWK,
    # unit 1: the MFD, radio 1
    **_UNIT,
    **_fms("MFD"),
    **parts.RADIO[1],
    **parts.LIGHTS,
}

_DEVICE2 = {**_UNIT, **_fms("PFD"), **parts.RADIO[2]}   # unit 2: the PFD, radio 2

DEVICE = {1: _DEVICE1, 2: _DEVICE2}
UNMAPPED = {
    1: {
        "TEST": "the GFC 700 has no TEST key",
        "GPSS": "the GFC 700 flies GPS steering in NAV mode",
        "HALF_BANK": "no G1000 NXi aircraft in MSFS has a low-bank key",
        **_UNIT_UNMAPPED,
        **parts.LIGHTS_UNMAPPED,
    },
    2: _UNIT_UNMAPPED,
}
