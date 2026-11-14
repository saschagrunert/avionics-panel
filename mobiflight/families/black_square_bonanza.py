"""Black Square's Bonanza with the Bendix/King KFC 150 and KAS 297B, in MSFS 2024: what each button does there
(docs/using/controls.md, docs/using/compatibility.md), for every avionics selection its tablet offers. Unit 1 is the
primary selection (KX 155B, KLN 90B, GNS 530 or GTN 750) with COM 1 / NAV 1, unit 2 the secondary (KX 155B, GNS 430
or GTN 650) with COM 2 / NAV 2, and either GTN is PMS50's or TDS's. What the profile does differently from the real
units is in docs/using/mapping.md#black-square-bonanza.

Sources: the Black Square Bonanza Professional User Guide (2025), "Options Page" (the avionics selections) and "Hardware
Inputs & Outputs". The KFC 150's keys are the simulator's autopilot key events ("Instrument Events"), its TEST the L:
variable of its self-test, the KAS 297B's knob and keys, the KR 87's keys, the EDM 800's buttons and the GTX 327's keys
H: events of their own, the dimmers, their switches, the reading lights, the transmit selector, the HSI's NAV/RNAV
switch, the DME's selector and the MD41's test L: variables. Black Square names its navigators' inputs by instance
("Avionics Variables & Events"): the GNS as AS530_1_ and AS430_1_, which the profile sends as the template's AS530_ and
AS430_ as the GNS profile does (the GNS takes both: BaseInstrument.DecomposeEventFromPrefix strips the instrument's ID
or its template's name, and the guide's own CDI row names AS530_CDI_Push), the KLN 90B as KLN90B_, TDS's GTNXi as L:
variables (TDSGTNXI750U1_), and pms50's GTN as H: events (GTN750_, GTN650_). TDS's GTNXi takes its own key events too,
in any aircraft (its manual's "Interfacing with Hardware", gtn.py), as a project the Bonanza is flown with drives it;
the profile sends those, which also cover the volume push the guide does not list, with the GTN 650's values as TDS's
unit 1 and unit 2, as the guide gives no unit for it. pms50's GTN takes no volume push from outside. TDS's are the
simulator's legacy GPS key events, which other avionics may take as well: Working Title's GNS does not (none of them is
in its source or the Garmin SDK's), and that Black Square's KLN 90B and pms50's GTN do not either is assumed. A control
sends the inputs of every navigator its unit may hold, as each takes only its own and no two selections share a
navigator's own input, so one profile drives whichever the tablet selected. Three controls send the simulator's events
instead, which every selection follows: CDI (TOGGLE_GPS_DRIVES_NAV1), the RANGE tilt (the COM volume) and TERR
(GPS_OBS). The guide lists no event for FD or for the KFC 150's UP/DN rocker: FD is the simulator's flight director key
event, and the rocker steps the reference of the mode as the guide describes it (below); YD is the simulator's yaw
damper event, for an aircraft that has one. The GNS's D→ is Working Title's DirectTo_Push, as the GNS profile sends it:
the guide's DRCT_Push is not among the events the GNS takes (InteractionEvent.ts), and its RNG keys, which the guide
does not list, are Working Title's too. The EDM 800's left button is taken to be STEP and its right LEAN FIND, as on the
real unit; the guide does not say. The radios, ADF tuning, transponder codes and the knobs round the autopilot are the
parts the tables share (parts.py).
"""
from mobiflight.families import gtn, parts
from mobiflight.families.part import part
from mobiflight.families.rpn import h, k, lset

NAME = "Black Square Bonanza"
# the navigators each unit may hold: the GNS by its template's prefix, TDS's GTNXi by its values in TDS's key events
# (gtn.TDS: the GTN 750Xi as TDS's unit 1, the GTN 650Xi as its unit 1 and unit 2, as the guide gives no unit for
# it and only one GTN 650 is ever fitted), pms50's GTN by its model, and on unit 1 the KLN 90B
UNIT1 = {"gns": "AS530_", "tds": (gtn.TDS["750", 1],), "pms": "GTN750_", "kln": True}
UNIT2 = {"gns": "AS430_", "tds": (gtn.TDS["650", 1], gtn.TDS["650", 2]), "pms": "GTN650_", "kln": False}


def _codes(*codes):
    return " ".join(code for code in codes if code)


def _toggle(variable):
    """A switch's L: variable flipped (Boolean)"""
    return f"(L:{variable}, Bool) ! (>L:{variable})"


def _key(unit, gns=None, tds=None, pms=None, kln=None):
    """A key of the unit's navigators: the GNS's H: event, TDS's key event (its value + 2 when the key goes down,
    + 4 when it comes up), pms50's H: event and the KLN 90B's, each by its name after the prefix; None for a
    navigator without it"""
    press = _codes(gns and h(unit["gns"] + gns), *(tds and k(tds, v + gtn.KEY_DOWN) for v in unit["tds"]),
                   pms and h(unit["pms"] + pms), kln and unit["kln"] and h("KLN90B_" + kln))
    if not tds:
        return press
    return {"press": press, "release": _codes(*(k(tds, v + gtn.KEY_UP) for v in unit["tds"]))}


def _turn(unit, gns=None, tds=None, pms=None, kln=None):
    """A knob detent of the unit's navigators: TDS's key event with its value"""
    return _codes(gns and h(unit["gns"] + gns), *(tds and k(tds, v) for v in unit["tds"]),
                  pms and h(unit["pms"] + pms), kln and unit["kln"] and h("KLN90B_" + kln))


def _unit(unit):
    """The FMS keys and knob of the unit's navigators. The KLN 90B takes D→, CLR, ENT and MSG, MENU as its ALT key,
    the FMS knob as its right knob and the FMS push as its right CRSR"""
    return {
        "OBS": _key(unit, gns="OBS_Push"),
        "FPL": _key(unit, gns="FPL_Push"),
        "DIRECT": _key(unit, gns="DirectTo_Push", tds="GPS_DIRECTTO_BUTTON", pms="DirectToPush", kln="DCT_Push"),
        "MENU": _key(unit, gns="MENU_Push", kln="ALT_Push"),
        "PROC": _key(unit, gns="PROC_Push"),
        "CLR": _key(unit, gns="CLR_Push", kln="CLR_Push"),
        "ENT": _key(unit, gns="ENT_Push", kln="ENT_Push"),
        "S_ENT": _key(unit, gns="ENT_Push", kln="ENT_Push"),
        "MSG": _key(unit, gns="MSG_Push", kln="MSG_Push"),
        "MAP": _key(unit, gns="CLR_Push_Long"),                # hold CLR
        "HOME": _key(unit, tds="GPS_MENU_BUTTON", pms="HomePush"),
        "FMS_OUTER_CW": _turn(unit, "RightLargeKnob_Right", "GPS_GROUP_KNOB_INC", "KnobLargeInc",
                              "RightLargeKnob_Right"),
        "FMS_OUTER_CCW": _turn(unit, "RightLargeKnob_Left", "GPS_GROUP_KNOB_DEC", "KnobLargeDec",
                               "RightLargeKnob_Left"),
        "FMS_INNER_CW": _turn(unit, "RightSmallKnob_Right", "GPS_PAGE_KNOB_INC", "KnobSmallInc",
                              "RightSmallKnob_Right"),
        "FMS_INNER_CCW": _turn(unit, "RightSmallKnob_Left", "GPS_PAGE_KNOB_DEC", "KnobSmallDec",
                               "RightSmallKnob_Left"),
        "FMS_CRSR": _key(unit, gns="RightSmallKnob_Push", tds="GPS_CURSOR_BUTTON", pms="KnobPush",
                         kln="RightCursor_Toggle"),
    }


def _volume(unit, com, way):
    """A step of the unit's COM volume: the radio's (the GNS's and the KX 155B's volume knob, as the guide lists
    them) and the GTN's volume knob (TDS's GPS_BUTTON2, its value + 2 down and + 4 up)"""
    step = gtn.KEY_UP if way == "INC" else gtn.KEY_DOWN
    return _codes(*(k("GPS_BUTTON2", v + step) for v in unit["tds"]), h(f"{unit['pms']}Vol{way.title()}"),
                  k(f"COM{com}_VOLUME_{way}"))


def _range(unit, com, shift=""):
    """The RANGE knob for the unit's navigators: turned, the map's range (the GNS's RNG key, clockwise zooms out,
    and the GTN's inner knob, which zooms its map on the map page, turned the other way as in the GTN profile,
    gtn.py); tilted up and down, the unit's COM volume; pushed, TDS's GTN's volume push (squelch, GPS_BUTTON1). On
    unit 1 it also works the KLN 90B's left side: the turn its left inner knob, the tilt left and right its left
    outer knob, the push its left CRSR."""
    return {
        f"{shift}RANGE_CW": _turn(unit, "RNG_Dezoom", "GPS_PAGE_KNOB_DEC", "KnobSmallDec", "LeftSmallKnob_Right"),
        f"{shift}RANGE_CCW": _turn(unit, "RNG_Zoom", "GPS_PAGE_KNOB_INC", "KnobSmallInc", "LeftSmallKnob_Left"),
        f"{shift}PAN_UP": _volume(unit, com, "INC"),
        f"{shift}PAN_DN": _volume(unit, com, "DEC"),
        f"{shift}PTR": _key(unit, tds="GPS_BUTTON1", kln="LeftCursor_Toggle"),
        **({f"{shift}PAN_LEFT": _turn(unit, kln="LeftLargeKnob_Left"),
            f"{shift}PAN_RIGHT": _turn(unit, kln="LeftLargeKnob_Right")} if unit["kln"] else {}),
    }


# UP and DN: the KFC 150's rocker, which steps the altitude held by 100 ft in ALT, the pitch held by 1° in pitch
# mode (the guide's KFC 150 section) and the rate in VS (its KAS 297B section); the simulator's key events for each
_ROCKER = ("(A:AUTOPILOT ALTITUDE LOCK, Bool) if{{ 100 (>K:AP_ALT_VAR_{0}) }} els{{ (A:AUTOPILOT VERTICAL HOLD, Bool) "
           "if{{ (>K:AP_VS_VAR_{0}) }} els{{ (A:AUTOPILOT PITCH HOLD, Bool) if{{ (>K:AP_PITCH_REF_INC_{1}) }} }} }}")
_UP, _DN = _ROCKER.format("INC", "UP"), _ROCKER.format("DEC", "DN")
_VS = h("kas297b_VsButton")


def _edm(button):
    """A button of the EDM 800 engine monitor ("L" or "R"): a tap is its short press, a hold its long one (the
    firmware holds S_UP and S_DN as long as the key)"""
    return {"release": h(f"bksq_JpiButton_1_{button}_Short"), "long": h(f"bksq_JpiButton_1_{button}_Long")}


_KFC150 = {
    # autopilot keys: AP ENG, the modes, TEST (the self-test's counter, as the guide sets it, and the MD41's test,
    # held as long as the key) and the KAS 297B's VS ENG and ALT ARM
    "AP": k("AP_MASTER"),
    "TEST": {"press": f"{lset('var_AutopilotStartupCounter', 20)} {lset('var_md41Test', 1)}",
             "release": lset("var_md41Test", 0)},
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
    "DN": _DN,
    # SHIFT, UP and SHIFT, DN: the EDM 800's left (STEP) and right (LEAN FIND) buttons
    "S_UP": _edm("L"),
    "S_DN": _edm("R"),
    # GPSS: the HSI's source switch below it, NAV 1 or RNAV (the KNS 81)
    "GPSS": _toggle("var_rnavDrivesHsi"),
    # LVL: the KDI 572R's selector, one position on and from the last round to the first
    "LVL": "(L:var_dmeMode, Number) 1 + 5 % (>L:var_dmeMode)",
    # SHIFT, FLC and SHIFT, VNV: the KR 87's ADF (antenna) and BFO keys
    "S_FLC": h("adf_AntAdf"),
    "S_VNV": h("adf_bfo"),
    # ALT/HDG knob: the KAS 297B's knob (inner 100 ft, outer 1000 ft; the rate instead while it is pulled), the
    # heading bug (the course and the altimeter, with SHIFT, are NAV1_KNOBS, beside it in DEVICE)
    "ALT_100_UP": h("kas297b_100_INC"),
    "ALT_100_DN": h("kas297b_100_DEC"),
    "ALT_1000_UP": h("kas297b_1000_INC"),
    "ALT_1000_DN": h("kas297b_1000_DEC"),
    **parts.HEADING,
}
_KFC150_UNMAPPED = {
    "FLC": "the KFC 150 has no FLC mode",
    "VNV": "the KFC 150 has no VNAV mode",
    "HALF_BANK": "the KFC 150 has no low-bank mode",
}

# the KFC 150 and KAS 297B as an autopilot part, for Black Square's aircraft with other avionics: the keys and the
# ALT/HDG knob, with SHIFT, UP and SHIFT, DN as the rocker (a stray SHIFT does no harm) and TEST the self-test alone
AUTOPILOT = part("kfc150", "KFC 150 (Black Square)", "autopilot", {1: {
    **{b: e for b, e in _KFC150.items() if b not in ("S_UP", "S_DN", "GPSS", "LVL", "S_FLC", "S_VNV", "TEST")},
    "S_UP": _UP,
    "S_DN": _DN,
    "TEST": lset("var_AutopilotStartupCounter", 20),
}}, {1: {**_KFC150_UNMAPPED,
         "S_FLC": "the KFC 150 has no FLC mode",
         "S_VNV": "the KFC 150 has no VNAV mode",
         "LVL": "the KFC 150 has no level mode",
         "GPSS": "the KFC 150 has no GPSS key: NAV follows the HSI, on GPS or VLOC"}})


# the lighting, as a project the Bonanza is flown with sets it: the outer ring steps the instrument lights, with the
# engine instruments' and the subpanel's dimmers alike and the master panel lighting switch on above 0; the inner ring
# the glareshield flood lights, with their switch and the pilot's yoke map light; the cabin light push the six
# reading lights and the copilot's yoke map light, as the pilot's first reading light goes. The yoke map lights go by
# the guide's name (OatMapCompassLightButton_n) and by the project's (var_ in front); a name nothing reads is harmless.
_PANEL = ("L:var_FlightInstrumentsLightingKnob", "L:var_EngineInstrumentsLightingKnob", "L:var_SubpanelLightingKnob")
_FLOOD = ("L:var_GlareshieldLightingKnob",)
_FLOOD_ON = ("L:bksq_MasterGlareshieldLights", "L:OatMapCompassLightButton_1", "L:var_OatMapCompassLightButton_1")
_CABIN = (*(f"L:var_LIGHTING_Push_Cockpit_{n}" for n in range(1, 7)), "L:OatMapCompassLightButton_2",
          "L:var_OatMapCompassLightButton_2")
_LIGHTS = {
    "PANEL_LT_UP": parts.dimmer(f"({_PANEL[0]}, Number)", _PANEL, 5, ("L:bksq_MasterPanelLights",)),
    "PANEL_LT_DN": parts.dimmer(f"({_PANEL[0]}, Number)", _PANEL, -5, ("L:bksq_MasterPanelLights",)),
    "FLOOD_LT_UP": parts.dimmer(f"({_FLOOD[0]}, Number)", _FLOOD, 5, _FLOOD_ON),
    "FLOOD_LT_DN": parts.dimmer(f"({_FLOOD[0]}, Number)", _FLOOD, -5, _FLOOD_ON),
    "CABIN_LT": parts.toggle(f"({_CABIN[0]}, Bool)", _CABIN),
}

# the RDR 1150XL weather radar: SHIFT with the RANGE knob tilted left and right its range down and up (its keys' H:
# events), FLC and ½ BANK its antenna tilt down and up (L:var_RadarTilt, 0 to 100; a higher value taken as up) in steps
# of 5
_RADAR = {
    "S_PAN_LEFT": h("bksq_wradar1_radarRangeDec"),
    "S_PAN_RIGHT": h("bksq_wradar1_radarRangeInc"),
    "FLC": parts.dimmer("(L:var_RadarTilt, Number)", ("L:var_RadarTilt",), -5),
    "HALF_BANK": parts.dimmer("(L:var_RadarTilt, Number)", ("L:var_RadarTilt",), 5),
}

# MIC 1 and MIC 2: the simulator's transmitters and the pilot's transmit selector (0 COM 1, 1 COM 2)
_AUDIO = {
    **parts.AUDIO,
    "MIC1": f"{parts.transmit(1)} {lset('var_PilotTransmitSelector', 0)}",
    "MIC2": f"{parts.transmit(2)} {lset('var_PilotTransmitSelector', 1)}",
}

# the KR 87: the FREQ knob's ADF mode tunes it, ADF ⇆ is its FRQ key
_ADF = {**parts.ADF, "ADF_SWAP": h("adf_frqTransfert")}

# the KAS 297B's mode: XPDR mode presses the GTX 327's ALT or STBY key (its H: events), by the mode the simulator
# keeps: standby or off goes to ALT, any other mode to standby
_SQUAWK = {
    **parts.SQUAWK,
    "XPDR_MODE": "(A:TRANSPONDER STATE:1, Enum) 1 > if{ (>H:TRANSPONDER_Push_STBY) } els{ (>H:TRANSPONDER_Push_ALT) }",
}

# the MD41 beside the KLN 90B: its VLOC/GPS key is CDI's event, its APR ARM key on NRST and its OBS key, the
# simulator's GPS OBS toggle, on TERR (not on OBS: the GNS's OBS key sets the mode itself, and a toggle beside it
# would undo it)
_MD41 = {"NRST": h("KLN90B_ApprArm_Push"), "TERR": k("GPS_OBS")}

_UNIT_UNMAPPED = {**parts.RADIO_UNMAPPED}

DEVICE = {
    1: {
        **_KFC150,
        **parts.NAV1_KNOBS,
        **_AUDIO,
        **_SQUAWK,
        **_LIGHTS,
        **_range(UNIT1, 1),
        **_range(UNIT2, 2, "S_"),
        # unit 1: the primary navigator, radio 1; CDI is the guide's GPS/VLOC event (the GNS 530's CDI key, the
        # MD41's VLOC/GPS key)
        **_unit(UNIT1),
        **_MD41,
        "CDI": k("TOGGLE_GPS_DRIVES_NAV1"),
        "VNAV": h("AS530_VNAV_Push"),
        **parts.RADIO[1],
        **_ADF,
        **_RADAR,
    },
    2: {**_unit(UNIT2), "CDI": h("AS430_CDI_Push"), **parts.RADIO[2], **_ADF},
}
UNMAPPED = {
    1: {
        "VNV": _KFC150_UNMAPPED["VNV"],
        **_UNIT_UNMAPPED,
    },
    2: {
        "NRST": "neither the GNS nor the GTN has a NRST key: the GNS's nearest pages are a page group, the GTN's on "
                "its touchscreen",
        "TERR": "neither the GNS nor the GTN has a TERR key",
        "VNAV": "the GNS 430 has no VNAV key, and the GTN none at all",
        **_UNIT_UNMAPPED,
    },
}
