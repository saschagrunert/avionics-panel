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
from mobiflight.families.part import part
from mobiflight.families.rpn import bezel, h, k, lset

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
    return bezel(f"AS1000_{display}_", {
        "FPL": "FPL_Push",
        "DIRECT": "DIRECTTO",
        "MENU": "MENU_Push",
        "PROC": "PROC_Push",
        "CLR": "CLR",
        "ENT": "ENT_Push",
        "S_ENT": "ENT_Push",
        "FMS_OUTER_CW": "FMS_Lower_INC",
        "FMS_OUTER_CCW": "FMS_Lower_DEC",
        "FMS_INNER_CW": "FMS_Upper_INC",
        "FMS_INNER_CCW": "FMS_Upper_DEC",
        "FMS_CRSR": "FMS_Upper_PUSH",
    })


def _range(display, shift=""):
    """The RANGE knob and joystick of the MFD or the PFD; clockwise zooms out, as on the G1000: RANGE_INC steps the
    map to its next range (MFDNavMapPage.tsx, MapInset.tsx). The PFD's work its inset map, while it shows."""
    return bezel(f"AS1000_{display}_", {
        f"{shift}RANGE_CW": "RANGE_INC",
        f"{shift}RANGE_CCW": "RANGE_DEC",
        f"{shift}PAN_UP": "JOYSTICK_UP",
        f"{shift}PAN_DN": "JOYSTICK_DOWN",
        f"{shift}PAN_LEFT": "JOYSTICK_LEFT",
        f"{shift}PAN_RIGHT": "JOYSTICK_RIGHT",
        f"{shift}PTR": "JOYSTICK_PUSH",
    })


# STD: the PFD's PFD Opt and STD Baro softkeys, which toggle STD and, leaving it, return to the setting before it
# (RootMenu.ts, PFDOptMenu.ts, Altimeter.tsx); STD Baro then returns the softkeys to their top level. Not
# BAROMETRIC_STD_PRESSURE: the NXi's MFD intercepts it and passes it on to the sim (AltimeterBaroKeyEventHandler.ts),
# which sets 29.92 before the PFD's altimeter keeps the setting to return to, so STD Baro came back to 29.92 (seen in
# the COWS DA40). PFD Opt is the 4th softkey at the top level of the PFD's softkeys, where they mostly are, and STD
# Baro the 10th in PFD Opt; from another of its menus the two presses do other things (in XPDR, On and the like).
_STD = f"{h('AS1000_PFD_SOFTKEYS_4')} {h('AS1000_PFD_SOFTKEYS_10')}"

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
}

# the GFC 700: the autopilot keys, NOSE UP and NOSE DN, the yaw damper and the ALT/HDG knob (parts.py), with BC and
# ARM: the PFD's 10th softkey, Tmr/Ref at the top level of its softkeys, where the minimums are set; it opens the
# window and closes it again (RootMenu.ts, PFDViewService.ts)
AUTOPILOT = part("gfc700", "GFC 700", "autopilot",
                 {1: {**parts.GARMIN_SHARED, "BC": k("AP_BC_HOLD"), "ARM": h("AS1000_PFD_SOFTKEYS_10")}},
                 {1: {"TEST": "the GFC 700 has no TEST key",
                      "GPSS": "the GFC 700 flies GPS steering in NAV mode",
                      "HALF_BANK": "no G1000 NXi aircraft in MSFS has a low-bank key"}})

# the cockpit: the PFD's CRS knob and its push (CourseKnobInputHandler.ts), the course of the GPS's OBS or of the NAV
# radio the CDI shows, and its push centres it; its BARO knob (Altimeter.tsx) and STD; the GMA 1347 as the
# simulator's audio panel, the radios, ADF and transponder (parts.py)
COCKPIT = parts.cockpit("g1000", "G1000 NXi", {
    "CRS_CTR": h("AS1000_PFD_CRS_PUSH"),
    "CRS_1_UP": h("AS1000_PFD_CRS_INC"),
    "CRS_1_DN": h("AS1000_PFD_CRS_DEC"),
    **parts.course_fast(_shows),
    "BARO_UP": h("AS1000_PFD_BARO_INC"),
    "BARO_DN": h("AS1000_PFD_BARO_DEC"),
    "BARO_STD": _STD,
})

# the navigator: unit 1 the MFD, unit 2 the PFD, each with its FMS keys and knob; the RANGE knob and joystick on the
# MFD, with SHIFT the PFD's, on its inset map.
#
# The NXi's required vertical speed, the VSR its PFD shows, for VNV with an autopilot without VNAV (the C182T's KAP
# 140, parts.descent): Working Title's GarminVNavComputer.ts (garminsdk/autopilot/vnav) writes it to
# L:WTAP_VNAV_Required_VS (0 for none, below 0 for a descent) while the flight plan has an altitude constraint ahead.
# The NXi's MFD (WTG1000_MFD.tsx) runs that computer with its own autopilot every frame, also with a KAP 140 installed
# (G1000Autopilot.ts then only clears its FMA), so it is taken to be written there too.
NAVIGATOR = part("g1000", "G1000 NXi", "navigator",
                 {1: {**_UNIT, **_fms("MFD"), **_range("MFD"), **_range("PFD", "S_")}, 2: {**_UNIT, **_fms("PFD")}},
                 {}, DISTANCES=(parts.GPS_DISTANCE,), REQUIRED_VS="(L:WTAP_VNAV_Required_VS, feet per minute)")
