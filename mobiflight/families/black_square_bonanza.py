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
variables (TDSGTNXI750U1_), and PMS50's GTN as H: events (GTN750_, GTN650_; PMS50 names a GTN 650 on COM 2 GTN650_2_, so
unit 2 sends both, UNIT2_NAVIGATORS). TDS's GTNXi takes its own key events too, in any aircraft (its manual's
"Interfacing with Hardware", gtn.py), as a project the Bonanza is flown with drives it; the profile sends those, which
also cover the volume push the guide does not list, with the GTN 650's values as TDS's unit 1 and unit 2, as the guide
gives no unit for it. PMS50's GTN takes its volume push and contextual keys by PMS50's own list of events (gtn.py).
TDS's are the simulator's legacy GPS key events, which other avionics may take as well: Working Title's GNS does not
(none of them is in its source or the Garmin SDK's), and that Black Square's KLN 90B and PMS50's GTN do not either is
assumed. A control sends the inputs of every navigator its unit may hold, as each takes only its own and no two
selections share a navigator's own input, so one profile drives whichever the tablet selected. Two controls send the
simulator's events instead, which every selection follows: CDI (TOGGLE_GPS_DRIVES_NAV1) and TERR (GPS_OBS); the RANGE
tilt sends the COM volume (the GNS part's, the radio's) beside the GTNs' volume. The guide lists no event for FD or for
the KFC 150's UP/DN rocker: FD is the simulator's flight director key event, and the rocker steps the reference of the
mode as the guide describes it (below); YD is the simulator's yaw damper event, for an aircraft that has one. The GNS's
D→ is Working Title's DirectTo_Push, as the GNS profile sends it: the guide's DRCT_Push is not among the events the GNS
takes (InteractionEvent.ts), and its RNG keys, which the guide does not list, are Working Title's too. The EDM 800's
left button is taken to be STEP and its right LEAN FIND, as on the real unit; the guide does not say.

The profile (PROFILE) joins the KFC 150 part (AUTOPILOT, also offered alone), the Bendix/King cockpit (parts.py) and in
each unit the navigator parts the tablet may put there (gns.py, gtn.py and the KLN 90B here, part.joined), with the
Bonanza's own rows over them (part.compose).
"""

from mobiflight.families import gns, gtn, parts
from mobiflight.families.part import compose, distances, joined, navigator, part
from mobiflight.families.rpn import bezel, h, k, lset

NAME = "Black Square Bonanza"


def _toggle(variable):
    """A switch's L: variable flipped (Boolean)"""
    return f"(L:{variable}, Bool) ! (>L:{variable})"


# ---------------- the KFC 150 and KAS 297B ----------------
# UP and DN: the KFC 150's rocker, which steps the altitude held by 100 ft in ALT, the pitch held by 1° in pitch
# mode (the guide's KFC 150 section) and the rate in VS (its KAS 297B section); the simulator's key events for each.
# AP_ALT_VAR_INC and _DEC name no slot, taken to be the first, which VNV reads as the KAS 297B's selected altitude
# (parts.descent): which of the two the first slot holds in ALT is for the sim to show (docs/using/mapping.md, VNV
# without VNAV), as neither the guide nor the SDK says
_UP = parts.reference(k("AP_VS_VAR_INC"), k("AP_PITCH_REF_INC_UP"), alt=k("AP_ALT_VAR_INC", 100))
_DN = parts.reference(k("AP_VS_VAR_DEC"), k("AP_PITCH_REF_INC_DN"), alt=k("AP_ALT_VAR_DEC", 100))
_VS = h("kas297b_VsButton")
# VNV: the descent calculator (parts.descent), with VS ENG pressed after the rate is set, while the autopilot is
# engaged, not in VS and not on a glideslope (a press there would leave it): the guide says VS ENG takes the rate the
# KAS 297B shows, which shows a rate set from outside for 2 s, and arms the altitude's capture when that rate leads
# towards it; with the autopilot off VS ENG would set the flight director's mode instead. The guide also says the KAS
# 297B keeps its older behaviour for the native AP_VS_VAR_SET_ENGLISH. The distance is first the KNS 81's RNAV DME
# output (an output the guide lists) while the HSI's source switch is on RNAV, then TDS's GTNXi's and the simulator's
# GPS WP DISTANCE, as the navigators the tablet may choose give them; the guide names none for the KLN 90B, which is
# assumed to write GPS WP DISTANCE, if anything
_VS_ENG = (f"(A:AUTOPILOT MASTER, Bool) (A:AUTOPILOT VERTICAL HOLD, Bool) ! and (A:AUTOPILOT GLIDESLOPE ACTIVE, Bool) "
           f"! and if{{ {_VS} }}")
_RNAV_DISTANCE = "(L:var_rnavDrivesHsi, Bool) (L:var_RNAV_DME, Number) *"


def KFC150_VNV(**kwargs):    # noqa: N802 (named as the other autopilots' VNV)
    """VNV's code, of the distances and required rate (part.compose): the rate, then VS ENG, on press alone, as the
    panel sent it when VNV worked in flight. Not the KAP 140's second step (parts.KAP140_VNV): the IFR-1's VNV, which
    set the rate again on release, AP_VS_VAR_SET_ENGLISH sent to the KAS 297B just after VS ENG (the guide: it keeps
    its older behaviour for that event), or sent it from onHold alone, never worked"""
    return parts.descent(after=_VS_ENG, **kwargs)


_NO_FLC = "the KFC 150 has no FLC mode"

# the KFC 150 and KAS 297B as an autopilot part, also for Black Square's aircraft with other avionics: AP ENG, the
# modes and the KAS 297B's VS ENG and ALT ARM, the ALT/HDG knob, SHIFT, UP and SHIFT, DN as the rocker (a stray
# SHIFT does no harm), TEST the self-test's counter, as the guide sets it, and VNV and SHIFT, VNV the descent
# calculator without the Bonanza's KNS 81, which another aircraft lacks (of the distances the part reads alone,
# part.alone, or in a profile, part.compose). FD and the self-test only with the autopilot off, as Garmin's FD
# (parts.GARMIN_SHARED): a press in flight must not take the flight director away from it or test it.
_OFF = "(A:AUTOPILOT MASTER, Bool) !"
SELF_TEST = f"{_OFF} if{{ {lset('var_AutopilotStartupCounter', 20)} }}"
AUTOPILOT = part("kfc150", "KFC 150 (Black Square)", "autopilot", {1: {
    "AP": k("AP_MASTER"),
    "TEST": SELF_TEST,
    "ALT": k("AP_ALT_HOLD"),
    "ARM": h("kas297b_ArmButton"),
    "HDG": k("AP_PANEL_HEADING_HOLD"),
    "FD": f"{_OFF} if{{ {k('TOGGLE_FLIGHT_DIRECTOR')} }}",
    "YD": k("YAW_DAMPER_TOGGLE"),
    "NAV": k("AP_NAV1_HOLD"),
    "APR": k("AP_APR_HOLD"),
    "BC": k("AP_BC_HOLD"),
    "VS": _VS,
    "S_VS": _VS,
    "UP": _UP,
    "DN": _DN,
    "S_UP": _UP,
    "S_DN": _DN,
    # ALT/HDG knob: the KAS 297B's knob (inner 100 ft, outer 1000 ft; the rate instead while it is pulled), the
    # heading bug (the course and the altimeter, with SHIFT, are the cockpit's)
    "ALT_100_UP": h("kas297b_100_INC"),
    "ALT_100_DN": h("kas297b_100_DEC"),
    "ALT_1000_UP": h("kas297b_1000_INC"),
    "ALT_1000_DN": h("kas297b_1000_DEC"),
    **parts.HEADING,
}}, {1: {
    "FLC": _NO_FLC,
    "HALF_BANK": "the KFC 150 has no low-bank mode",
    "S_FLC": _NO_FLC,
    "LVL": "the KFC 150 has no level mode",
    "GPSS": "the KFC 150 has no GPSS key: NAV follows the HSI, on GPS or VLOC",
}}, VNV=KFC150_VNV)


def _edm(button):
    """A button of the EDM 800 engine monitor ("L" or "R"): a tap is its short press, a hold its long one (the
    firmware holds S_UP and S_DN as long as the key)"""
    return {"release": h(f"bksq_JpiButton_1_{button}_Short"), "long": h(f"bksq_JpiButton_1_{button}_Long")}


# the Bonanza's own keys round the autopilot: TEST also holds the MD41's lamp test as long as the key (with the
# autopilot engaged too, as it tests lamps alone), SHIFT, UP and SHIFT, DN are the EDM 800's left (STEP) and right
# (LEAN FIND) buttons, GPSS the HSI's source switch below it (NAV 1 or RNAV, the KNS 81), LVL the KDI 572R's selector
# (one position on, and from the last round to the first), SHIFT, FLC and SHIFT, VNV the KR 87's ADF (antenna) and BFO
# keys (VNV, which reads the KNS 81 first: _VNV, below the units)
_AROUND_AUTOPILOT = {
    "TEST": {"press": f"{SELF_TEST} {lset('var_md41Test', 1)}",
             "release": lset("var_md41Test", 0)},
    "S_UP": _edm("L"),
    "S_DN": _edm("R"),
    "GPSS": _toggle("var_rnavDrivesHsi"),
    "LVL": "(L:var_dmeMode, Number) 1 + 5 % (>L:var_dmeMode)",
    "S_FLC": h("adf_AntAdf"),
    "S_VNV": h("adf_bfo"),
}


# ---------------- the navigators the tablet may put in each unit ----------------
def kln90b():
    """Black Square's KLN 90B in unit 1, by its H: events (KLN90B_): D→, CLR, ENT and MSG, MENU as its ALT key, the
    FMS knob as its right knob and the FMS push as its right CRSR; on the RANGE knob its left side: the turn its left
    inner knob, the tilt left and right its left outer knob, the push its left CRSR"""
    rows = bezel("KLN90B_", {
        "DIRECT": "DCT_Push",
        "MENU": "ALT_Push",
        "CLR": "CLR_Push",
        "ENT": "ENT_Push",
        "S_ENT": "ENT_Push",
        "MSG": "MSG_Push",
        "FMS_OUTER_CW": "RightLargeKnob_Right",
        "FMS_OUTER_CCW": "RightLargeKnob_Left",
        "FMS_INNER_CW": "RightSmallKnob_Right",
        "FMS_INNER_CCW": "RightSmallKnob_Left",
        "FMS_CRSR": "RightCursor_Toggle",
        "RANGE_CW": "LeftSmallKnob_Right",
        "RANGE_CCW": "LeftSmallKnob_Left",
        "PTR": "LeftCursor_Toggle",
        "PAN_LEFT": "LeftLargeKnob_Left",
        "PAN_RIGHT": "LeftLargeKnob_Right",
    })
    unmapped = {
        **dict.fromkeys(("CDI", "OBS", "HOME", "FPL", "PROC", "VNAV", "NRST", "TERR", "MAP"),
                        "the KLN 90B has no such key (the MD41 beside it has VLOC/GPS, APR ARM and OBS: the "
                        "Bonanza's CDI, NRST and TERR)"),
        **dict.fromkeys(("PAN_UP", "PAN_DN"), "the KLN 90B's left outer knob is on the tilt left and right"),
    }
    return navigator("kln90b", "KLN 90B", rows, unmapped, 1)


# Unit 1, the primary selection: the GNS 530, TDS's GTN 750Xi (its unit 1), PMS50's GTN 750 or the KLN 90B with the
# MD41 beside it: its VLOC/GPS key is CDI's event (the guide's GPS/VLOC event, the GNS 530's CDI key too), its APR
# ARM key on NRST and its OBS key, the simulator's GPS OBS toggle, on TERR (not on OBS: the GNS's OBS key sets the
# mode itself, and a toggle beside it would undo it)
UNIT1_NAVIGATORS = (gns.navigator("530", 1), gtn.tds("750", 1, 1), gtn.pms50("750", 1), kln90b())
UNIT1 = joined("black-square-bonanza", "Black Square Bonanza's primary", *UNIT1_NAVIGATORS, rows={
    "CDI": k("TOGGLE_GPS_DRIVES_NAV1"),
    "NRST": h("KLN90B_ApprArm_Push"),
    "TERR": k("GPS_OBS")})
# Unit 2, the secondary selection: the GNS 430, TDS's GTN 650Xi (its unit 1 or 2, as the guide gives no unit for it
# and only one GTN 650 is ever fitted) or PMS50's GTN 650
UNIT2_NAVIGATORS = (gns.navigator("430", 2), gtn.tds("650", 1, 2), gtn.tds("650", 2, 2),
                    gtn.pms50("650", 2, also=("GTN650_",)))
UNIT2 = joined("black-square-bonanza", "Black Square Bonanza's secondary", *UNIT2_NAVIGATORS, reasons={
                   "NRST": "neither the GNS nor the GTN has a NRST key: the GNS's nearest pages are a page group, the "
                           "GTN's on its touchscreen",
                   "TERR": "neither the GNS nor the GTN has a TERR key",
                   "VNAV": "the GNS 430 has no VNAV key, and the GTN none at all"})
# the Bonanza's VNV: its KNS 81 first, then the distances of the navigators the tablet may choose, as compose()
# orders them (part.distances)
_VNV = KFC150_VNV(distances=(_RNAV_DISTANCE, *distances(UNIT1, UNIT2)))


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
    "MIC1": f"{parts.transmit(1)} {lset('var_PilotTransmitSelector', 0)}",
    "MIC2": f"{parts.transmit(2)} {lset('var_PilotTransmitSelector', 1)}",
}

# the KR 87: the FREQ knob's ADF mode tunes it, ADF ⇆ is its FRQ key
_ADF = {"ADF_SWAP": h("adf_frqTransfert")}

# the GTX 327's mode: XPDR mode presses its ALT or STBY key (its H: events), by the mode the simulator keeps:
# standby or off goes to ALT, any other mode to standby; VFR presses its ALT key as it squawks the VFR code
_SQUAWK = {
    "XPDR_MODE": "(A:TRANSPONDER STATE:1, Enum) 1 > if{ (>H:TRANSPONDER_Push_STBY) } els{ (>H:TRANSPONDER_Push_ALT) }",
    "VFR": parts.vfr(alt=h("TRANSPONDER_Push_ALT")),
}

# the two altimeters, set together from the setting of the left-hand one (the BARO knob with SHIFT, its push STD):
# KOHLSMAN_SET (millibars * 16) without an index for the left-hand one, as the other profiles set theirs, and with
# index 2 for the right-hand one, as (>K:2:KOHLSMAN_SET) takes it below the setting, as FlyByWire's, Salty's and
# Working Title's MobiFlight presets send it (the order and the index still to check in the aircraft:
# docs/using/mapping.md), so a wrong order costs the right-hand one alone. A turn steps the left-hand one's setting
# by 0.01 inHg, the US Bonanza's unit (KOHLSMAN_INC and _DEC step in the sim's: in hPa a whole hPa every third
# detent or so), and forgets the setting STD kept; STD and the setting before as parts.STD_TOGGLE, on both.
_SET_BOTH_BARO = "16 * near sp0 l0 (>K:KOHLSMAN_SET) 2 l0 (>K:2:KOHLSMAN_SET)"
_STD_BOTH_BARO = "1 (>K:BAROMETRIC_STD_PRESSURE) 2 (>K:BAROMETRIC_STD_PRESSURE)"
_KEPT = f"(L:{parts.KEPT_BARO}, Number)"


def _baro_step(operator):
    return f"{parts.BARO} 0.3386389 / near 1 {operator} 0.3386389 * {_SET_BOTH_BARO} {parts.FORGET_BARO}"


_BOTH_ALTIMETERS = {
    "BARO_UP": _baro_step("+"),
    "BARO_DN": _baro_step("-"),
    "BARO_STD": (f"{parts.BARO} {parts.AT_STD} if{{ {_KEPT} 0 > if{{ {_KEPT} {_SET_BOTH_BARO} {parts.FORGET_BARO} }} "
                 f"els{{ {_STD_BOTH_BARO} }} }} els{{ {lset(parts.KEPT_BARO, parts.BARO)} {_STD_BOTH_BARO} }}"),
}

# the profile: the KFC 150, the Bendix/King cockpit (its radios, ADF tuning, transponder codes and the knobs round
# the autopilot) and the navigators of both units, with the Bonanza's own rows over them
PROFILE = compose(NAME, AUTOPILOT, parts.BENDIX_KING, UNIT1, UNIT2, rows={
    1: {**_AROUND_AUTOPILOT, "VNV": _VNV, **_LIGHTS, **_RADAR, **_AUDIO, **_SQUAWK, **_ADF, **_BOTH_ALTIMETERS},
    2: _ADF,
})
