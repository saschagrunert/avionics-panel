"""Bendix/King KFC 150 with the KAS 297B altitude selector in Black Square's aircraft, in MSFS 2024: what each
button does there (docs/using/controls.md, docs/using/compatibility.md), as in the Black Square Bonanza. Unit 1 is
the first navigator (a GNS 530 or GTN 750) with COM 1 / NAV 1, unit 2 the second (a GNS 430 or GTN 650) with COM 2 /
NAV 2. What the profile does differently from the real units is in docs/using/mapping.md#kfc-150-black-square.

Sources: the Black Square Bonanza Professional User Guide (2025), "Hardware Inputs & Outputs". The KFC 150's keys
are the simulator's autopilot key events ("Instrument Events"), its TEST the L: variable of its self-test, the KAS
297B's knob and keys H: events of its own, the dimmers L: variables. Black Square names its navigators' inputs by
instance ("Avionics Variables & Events"): the GNS as AS530_1_ and AS430_1_, which the profile sends as the
template's AS530_ and AS430_ as the GNS profile does (the GNS takes both: BaseInstrument.DecomposeEventFromPrefix
strips the instrument's ID or its template's name, and the guide's own CDI row names AS530_CDI_Push), TDS's GTNXi as
L: variables (TDSGTNXI750U1_, and TDSGTNXI650U1_ for the GTN 650, by analogy with the guide's "replace GTN750 with
GTN650", which it gives for pms50's names, and as Black Square loads the 650 as unit 1, gtn.py), pms50's GTN as H:
events (GTN750_, GTN650_). A key sends the inputs of all three, as each navigator takes only its own, so one profile
drives whichever the aircraft has. The guide lists no event for FD or for the KFC 150's UP/DN rocker: FD is the
simulator's flight director key event, and the rocker steps the reference of the mode as the guide describes it
(below); YD is the simulator's yaw damper event, for an aircraft that has one. The GNS's D→ is Working Title's
DirectTo_Push, as the GNS profile sends it: the guide's DRCT_Push is not among the events the GNS takes
(InteractionEvent.ts), and its RNG keys, which the guide does not list, are Working Title's too. The radios, ADF,
transponder codes, audio panel, cabin light and the knobs round the autopilot are the parts the tables share
(parts.py).
"""
from mobiflight.families import parts
from mobiflight.families.rpn import h, k, lset

NAME = "KFC 150 (Black Square)"


def _held(variable):
    """A TDS key as Black Square reads it: 1 while down, 0 when let go (a key left at 1 shows as stuck)"""
    return {"press": lset(variable, 1), "release": lset(variable, 0)}


def _key(gns, tds, pms):
    """A key of the GNS (an H: event), the TDS GTN (a held L: variable) and the pms50 GTN (an H: event); None for a
    navigator without it"""
    held = _held(tds) if tds else {}
    press = " ".join(code for code in (gns and h(gns), held.get("press"), pms and h(pms)) if code)
    return {"press": press, "release": held["release"]} if held else press


def _turn(gns, tds, pms):
    """A knob detent of the GNS, the TDS GTN (its L: variable set to 1, which Black Square sets back) and the pms50
    GTN"""
    return " ".join((h(gns), lset(tds, 1), h(pms)))


def _unit(gns, gtn):
    """The FMS keys and knob of the navigators of a unit: the GNS by its prefix ("AS530_"), the GTN by its model
    ("750", "650")"""
    tds, pms = f"TDSGTNXI{gtn}U1_", f"GTN{gtn}_"
    return {
        "OBS": h(gns + "OBS_Push"),
        "FPL": h(gns + "FPL_Push"),
        "DIRECT": _key(gns + "DirectTo_Push", tds + "DTOKey", pms + "DirectToPush"),
        "MENU": h(gns + "MENU_Push"),
        "PROC": h(gns + "PROC_Push"),
        "CLR": h(gns + "CLR_Push"),
        "ENT": h(gns + "ENT_Push"),
        "S_ENT": h(gns + "ENT_Push"),
        "MSG": h(gns + "MSG_Push"),
        "MAP": h(gns + "CLR_Push_Long"),                      # hold CLR
        "HOME": _key(None, tds + "HomeKey", pms + "HomePush"),
        "FMS_OUTER_CW": _turn(gns + "RightLargeKnob_Right", tds + "RKnobOuterInc", pms + "KnobLargeInc"),
        "FMS_OUTER_CCW": _turn(gns + "RightLargeKnob_Left", tds + "RKnobOuterDec", pms + "KnobLargeDec"),
        "FMS_INNER_CW": _turn(gns + "RightSmallKnob_Right", tds + "RKnobInnerInc", pms + "KnobSmallInc"),
        "FMS_INNER_CCW": _turn(gns + "RightSmallKnob_Left", tds + "RKnobInnerDec", pms + "KnobSmallDec"),
        "FMS_CRSR": _key(gns + "RightSmallKnob_Push", tds + "RKnobCRSR", pms + "KnobPush"),
    }


# UP and DN: the KFC 150's rocker, which steps the altitude held by 100 ft in ALT, the pitch held by 1° in pitch
# mode (the guide's KFC 150 section) and the rate in VS (its KAS 297B section); the simulator's key events for each
_ROCKER = ("(A:AUTOPILOT ALTITUDE LOCK, Bool) if{{ 100 (>K:AP_ALT_VAR_{0}) }} els{{ (A:AUTOPILOT VERTICAL HOLD, Bool) "
           "if{{ (>K:AP_VS_VAR_{0}) }} els{{ (A:AUTOPILOT PITCH HOLD, Bool) if{{ (>K:AP_PITCH_REF_INC_{1}) }} }} }}")
_UP, _DN = _ROCKER.format("INC", "UP"), _ROCKER.format("DEC", "DN")
_VS = h("kas297b_VsButton")


def _dimmer(variable, step):
    """A dimmer's L: variable (0 to 100) a step up or down, 20 detents end to end"""
    sign, limit = ("+", "100 min") if step > 0 else ("-", "0 max")
    return f"(L:{variable}, Number) {abs(step)} {sign} {limit} (>L:{variable})"


_KFC150 = {
    # autopilot keys: AP ENG, the modes, TEST (the self-test's counter, as the guide sets it) and the KAS 297B's
    # VS ENG and ALT ARM
    "AP": k("AP_MASTER"),
    "TEST": lset("var_AutopilotStartupCounter", 20),
    "ALT": k("AP_ALT_HOLD"),
    "ARM": h("kas297b_ArmButton"),
    "HDG": k("AP_PANEL_HEADING_HOLD"),
    "FD": k("TOGGLE_FLIGHT_DIRECTOR"),
    "YD": k("YAW_DAMPER_TOGGLE"),
    "NAV": k("AP_NAV1_HOLD"),
    "APR": k("AP_APR_HOLD"),
    "BC": k("AP_BC_HOLD"),
    "VS": _VS,
    "S_VS": _VS,
    "UP": _UP,
    "S_UP": _UP,
    "DN": _DN,
    "S_DN": _DN,
    # ALT/HDG knob: the KAS 297B's knob (inner 100 ft, outer 1000 ft; the rate instead while it is pulled), the
    # heading bug, the course and the altimeter
    "ALT_100_UP": h("kas297b_100_INC"),
    "ALT_100_DN": h("kas297b_100_DEC"),
    "ALT_1000_UP": h("kas297b_1000_INC"),
    "ALT_1000_DN": h("kas297b_1000_DEC"),
    **parts.NAV1_KNOBS,
}

# RANGE: the GNS 530's RNG key, as in the GNS profile; clockwise zooms out
_RANGE = {"RANGE_CW": h("AS530_RNG_Dezoom"), "RANGE_CCW": h("AS530_RNG_Zoom")}

# SHIFT, RANGE: the GTN 750's volume knob (TDS's, then pms50's), as in the GTN profile, and TDS's volume push,
# which the guide does not list: its L: variable as TDS's own HubHop presets set it (pms50 has none)
_VOLUME = {
    "S_RANGE_CW": f"{lset('TDSGTNXI750U1_LKnobInc', 1)} {h('GTN750_VolInc')}",
    "S_RANGE_CCW": f"{lset('TDSGTNXI750U1_LKnobDec', 1)} {h('GTN750_VolDec')}",
    "S_PTR": _held("TDSGTNXI750U1_LKnobCRSR"),
}

_LIGHTS = {
    # the instrument lights and the glareshield flood lights (the guide's dimmers), and the cabin light
    "PANEL_LT_UP": _dimmer("var_FlightInstrumentsLightingKnob", 5),
    "PANEL_LT_DN": _dimmer("var_FlightInstrumentsLightingKnob", -5),
    "FLOOD_LT_UP": _dimmer("var_GlareshieldLightingKnob", 5),
    "FLOOD_LT_DN": _dimmer("var_GlareshieldLightingKnob", -5),
    **parts.LIGHTS,
}

# the KAS 297B's mode: XPDR mode presses the GTX 327's ALT or STBY key (its H: events), by the mode the simulator
# keeps: standby or off goes to ALT, any other mode to standby
_SQUAWK = {
    **parts.SQUAWK,
    "XPDR_MODE": "(A:TRANSPONDER STATE:1, Enum) 1 > if{ (>H:TRANSPONDER_Push_STBY) } els{ (>H:TRANSPONDER_Push_ALT) }",
}

_UNIT_UNMAPPED = {
    "NRST": "neither the GNS nor the GTN has a NRST key: the GNS's nearest pages are a page group, the GTN's on its "
            "touchscreen",
    "TERR": "neither the GNS nor the GTN has a TERR key",
    **parts.RADIO_UNMAPPED,
}

DEVICE = {
    1: {
        **_KFC150,
        **parts.AUDIO,
        **_SQUAWK,
        **_LIGHTS,
        **_RANGE,
        **_VOLUME,
        # unit 1: the GNS 530 or GTN 750, radio 1; CDI is the guide's GPS/VLOC event (the GNS 530's CDI key)
        **_unit("AS530_", "750"),
        "CDI": k("TOGGLE_GPS_DRIVES_NAV1"),
        "VNAV": h("AS530_VNAV_Push"),
        **parts.RADIO[1],
        **parts.ADF,
    },
    2: {**_unit("AS430_", "650"), "CDI": h("AS430_CDI_Push"), **parts.RADIO[2], **parts.ADF},
}
_NO_PAN = "the GNS has no joystick, and the GTN pans its map on its touchscreen"
UNMAPPED = {
    1: {
        "FLC": "the KFC 150 has no FLC mode",
        "S_FLC": "the KFC 150 has no FLC mode",
        "VNV": "the KFC 150 has no VNAV mode",
        "S_VNV": "the KFC 150 has no VNAV mode",
        "LVL": "the KFC 150 has no level mode",
        "HALF_BANK": "the KFC 150 has no low-bank mode",
        "GPSS": "the KFC 150 has no GPSS key: NAV follows the HSI, on GPS or VLOC",
        **dict.fromkeys((b for b in parts.PAN if b != "S_PTR"), _NO_PAN),
        **_UNIT_UNMAPPED,
    },
    2: {**_UNIT_UNMAPPED, "VNAV": "the GNS 430 has no VNAV key, and the GTN none at all"},
}
