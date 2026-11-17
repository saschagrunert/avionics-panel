"""Garmin GFC 500 with the Working Title G3X Touch, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md), as in the CubCrafters XCub and NX Cub (one G3X Touch, a
GMC 507) and the Draco X (PFD and MFD). Unit 1 is the G3X Touch of index 1 (the PFD, or the only display) with
COM 1 / NAV 1, unit 2 the one of index 2 (the MFD) with COM 2 / NAV 2. What the profile does differently from the
real units is in docs/using/mapping.md#gfc-500-and-g3x-touch.

Sources, in Working Title's msfs-avionics-mirror for MSFS 2024 (SU5): the G3X Touch's H events (docs "G3X Touch H
Event List"; case-sensitive, UiInteractionMapper.ts) and the code that takes them (src/workingtitle-instruments-
g3x-touch, src/garminsdk, src/sdk). The G3X Touch builds the GFC 500 from Garmin's autopilot (GarminAutopilot,
GarminAPStateManager), which takes the sim's key events, so the autopilot keys send what the G3X's own AFCS page
sends (MFD/Views/AfcsControlsView/AfcsControlsView.tsx, parts.GARMIN_SHARED) and the knobs what its PFD knobs send
(GduDisplay/Gdu460/PfdInstruments/Gdu460PfdInstrumentsView.tsx). Key events and simulation variables as in the
MSFS 2024 SDK. The radios, ADF, transponder, audio panel and cabin light are the parts the tables share (parts.py).
"""
from mobiflight.families import parts
from mobiflight.families.part import part
from mobiflight.families.rpn import bezel, k


def _gdu(index):
    """The bezel of the G3X Touch (GDU 460) of this index: D→, MENU, BACK as CLR, NRST and the right-hand dual
    knob, which works the MFD pane in split screen"""
    return bezel(f"AS3X_Touch_{index}_", {
        "DIRECT": "DirectTo_Push",
        "MENU": "Menu_Push",
        "CLR": "Back_Push",
        "NRST": "NRST_Push",
        "FMS_OUTER_CW": "Knob_Outer_R_INC",
        "FMS_OUTER_CCW": "Knob_Outer_R_DEC",
        "FMS_INNER_CW": "Knob_Inner_R_INC",
        "FMS_INNER_CCW": "Knob_Inner_R_DEC",
        "FMS_CRSR": "Knob_Inner_R_PUSH",
    })


# the one CDI, which the key switches between GPS and NAV 1 while the G3X flies its own flight plan
# (ActiveNavSourceManager.ts), and the GPS's OBS mode, from both units
_CDI = {"CDI": k("TOGGLE_GPS_DRIVES_NAV1"), "OBS": k("GPS_OBS")}

# the GFC 500: the autopilot keys, the GMC 507's wheel as UP and DN, the yaw damper and the ALT/HDG knob, whose push
# syncs the heading bug as the G3X's knob does (parts.py)
AUTOPILOT = part("gfc500", "GFC 500", "autopilot", {1: parts.GARMIN_SHARED}, {1: {
    "TEST": "the GFC 500 tests itself at power-up: it has no TEST key",
    "ARM": "the GFC 500 has no ARM key",
    "GPSS": "the GFC 500 flies GPS steering in NAV mode",
    "BC": "the GFC 500 has no BC key",
    "HALF_BANK": "the GFC 500 has no low-bank key",
}})

# the cockpit: CRS CTR, the course to the VOR, or the localizer's, on the NAV the CDI shows, as the G3X's Course
# knob push sets it; with SHIFT the course of what the CDI shows and the altimeter of index 1, the G3X's
# (GduDefsConfig.ts), and STD, which only sets STD: Working Title's G3X is taken to keep STD as a mode of its own,
# as the G1000 NXi does (g1000.py), which KOHLSMAN_SET would not leave, so the push does not toggle it as
# parts.STD_TOGGLE does; the G3X's GPS follows the sim's GPS OBS (use-sim-obs by default: FmsConfig.ts,
# GarminObsLNavModule.ts). KOHLSMAN_INC and _DEC with the altimeter's index, as the G3X's own knob sends them
# (Gdu460PfdInstrumentsView.tsx), though the SDK's Key Events list no parameter for them. The radios, ADF,
# transponder and audio panel are the sim's own, on its data bar (parts.py).
COCKPIT = parts.cockpit("g3x", "G3X Touch", {
    "CRS_CTR": f"(A:GPS DRIVES NAV1, Bool) ! if{{ {parts.nav(parts.CENTRE)} }}",
    "CRS_1_UP": parts.cdi(k("GPS_OBS_INC"), k("VOR#_OBI_INC")),
    "CRS_1_DN": parts.cdi(k("GPS_OBS_DEC"), k("VOR#_OBI_DEC")),
    **parts.course_fast(parts.cdi),
    "BARO_UP": k("KOHLSMAN_INC", 1),
    "BARO_DN": k("KOHLSMAN_DEC", 1),
    **parts.STD,
})

_TOUCH = "a touchscreen function of the G3X Touch: its bezel has only D→, MENU, BACK (CLR), NRST and the knobs"
_TOUCH_KEYS = ("FPL", "ENT", "S_ENT", "VNAV", "MSG", "TERR", "MAP")
# what the G3X Touch has on its touchscreen only (docs/using/compatibility.md)
TOUCHSCREEN = (*_TOUCH_KEYS, *parts.RANGE_KNOB)
_UNIT_UNMAPPED = {
    "HOME": "the G3X Touch has no HOME key: free for your own mapping (docs/using/compatibility.md)",
    "PROC": "the G3X Touch is VFR only: it loads no procedures",
    **dict.fromkeys(_TOUCH_KEYS, _TOUCH),
}

# the navigator: unit 1 the G3X Touch of index 1, unit 2 the one of index 2, each with its bezel and the one CDI
NAVIGATOR = part("g3x", "G3X Touch", "navigator", {1: {**_gdu(1), **_CDI}, 2: {**_gdu(2), **_CDI}}, {
    1: {**dict.fromkeys(parts.RANGE_KNOB, "the G3X Touch zooms its map with the inner FMS knob on the map page and "
                                          "pans it on the touchscreen"),
        **_UNIT_UNMAPPED},
    2: _UNIT_UNMAPPED,
})
