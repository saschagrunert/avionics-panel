"""The rows several parts share: {button: code} rows, and {button: reason} for the buttons a part leaves unmapped,
joined into the parts' DEVICE and UNMAPPED dicts (part.py); and the parts round the KAP 140, its autopilot and the
Bendix/King cockpit.

The radios, ADF, transponder, audio panel and the instruments around a Bendix/King autopilot take the simulator's
own key events (the MSFS 2024 SDK's Key Events) and, for the transponder's mode, its simulation variable, which act
the same in every aircraft and whatever unit shows them; the KAP 140 takes the H: events of the one MSFS ships, the
ones its instrument (KAP140.js) handles. Garmin's autopilot, as Working Title's G1000 NXi and G3X Touch build it,
takes the simulator's autopilot key events (GARMIN_SHARED).
"""
import re

from mobiflight.families.part import GPS_DISTANCE, part
from mobiflight.families.rpn import h, k, turn

VFR = "7000"                     # the squawk the VFR key sets (EASA), unless a profile is made with another (--vfr)


def transmit(com):
    """MIC: the pilot and copilot transmit on COM 1 or 2 (the SDK's PILOT_TRANSMITTER_SET and
    COPILOT_TRANSMITTER_SET take 0 for COM 1, 1 for COM 2), and listen to it, as an audio panel's MIC key selects
    that radio's audio too (Garmin's GMA 1347)"""
    return (f"{com - 1} (>K:PILOT_TRANSMITTER_SET) {com - 1} (>K:COPILOT_TRANSMITTER_SET) "
            f"1 (>K:COM{com}_RECEIVE_SELECT)")


def receive(com):
    """COM: listen to COM 1 or 2, or stop (the SDK's COMn_RECEIVE_SELECT, set to the opposite of COM RECEIVE EX1),
    but never stop listening to the radio transmitted on (COM TRANSMIT), whose audio an audio panel always plays"""
    return f"(A:COM RECEIVE EX1:{com}, bool) ! (A:COM TRANSMIT:{com}, bool) or (>K:COM{com}_RECEIVE_SELECT)"


# The squawk: TRANSPONDER CODE:1 read as a number is its four digits as a decimal one (1200), and XPNDR_SET takes the
# code in the simulator's unit Bco16, a digit in each hex digit (0x1200), keeping three bits of each (MSFS DevSupport
# "Faulty unit for SimVar TRANSPONDER CODE"). Code works with the digits; squawk() packs them itself (BCO16). The
# simulator does not convert them for an L: variable set as a number and read as Bco16: in flight that sent 7000 as it
# is, 0x1B58, which the transponder took as 1350 (0x1B58 with three bits of each hex digit).
#
# VFR toggles the VFR code: from another code it keeps that code in L:AvionicsPanel_Squawk (its digits), squawks the
# VFR code and selects ALT (alt: the code that selects it); on the VFR code it squawks the code kept, once, as a GTX
# 327's VFR key does, and leaves the mode as it is. The VFR code goes to register 0 at the start, so it stands in the
# code once (docs/using/mapping.md: change it there). L:AvionicsPanel_Squawk_Kept says a code is kept (0000 is a code
# too).
ALT = "4 (>A:TRANSPONDER STATE:1, Enum)"         # the simulator's mode ALT (XPDR_MODE below)
CODE = "(A:TRANSPONDER CODE:1, number)"          # the squawk's digits, 1200 for 1200
_KEPT, _KEEPS = "AvionicsPanel_Squawk", "AvionicsPanel_Squawk_Kept"
# the digits on the stack (1200) packed a digit to a hex digit (0x1200), register 5 holding them meanwhile
BCO16 = "s5 1000 / flr 4096 * l5 100 / flr 10 % 256 * + l5 10 / flr 10 % 16 * + l5 10 % +"


def squawk(digits=""):
    """XPNDR_SET of a code's digits as a decimal number (an RPN value, "" for the top of the stack), in Bco16"""
    return " ".join(filter(None, (digits, BCO16, k("XPNDR_SET"))))


def vfr(code=VFR, alt=ALT):
    """VFR: toggle this code, four digits of 0 to 7, in any aircraft (above); alt selects ALT"""
    if not re.fullmatch("[0-7]{4}", str(code)):
        raise ValueError(f"not a squawk code (four digits, each 0 to 7): {code!r}")
    return (f"{int(code)} sp0 {CODE} l0 == if{{ (L:{_KEEPS}, Bool) if{{ {squawk(f'(L:{_KEPT}, Number)')} "
            f"0 (>L:{_KEEPS}) }} els{{ {alt} }} }} "
            f"els{{ {CODE} (>L:{_KEPT}) 1 (>L:{_KEEPS}) {squawk('l0')} {alt} }}")


_SQUAWK_ENTRY = re.compile(re.escape(vfr("7777", "@ALT@")).replace("7777", "[0-7]{1,4}", 1)
                           .replace("@ALT@", "(?P<alt>.+)", 1).replace("@ALT@", "(?P=alt)"))


def vfr_toggle(entry):
    """A table entry as the VFR toggle vfr() makes, the row --vfr replaces: its match, whose "alt" is the code that
    selects ALT, or None"""
    return _SQUAWK_ENTRY.fullmatch(entry) if isinstance(entry, str) else None


# ---------------- the simulator's radios, tuned directly ----------------
# COM 1 / NAV 1 from unit 1 and COM 2 / NAV 2 from unit 2, whichever unit or tuning box shows them; 121.5 tunes
# the unit's COM radio to 121.5 MHz, as holding a COM flip-flop does (COM_RADIO_SET_HZ takes Hz)
RADIO = {
    1: {
        "COM_SWAP": k("COM1_RADIO_SWAP"),
        "COM_121_5": k("COM_RADIO_SET_HZ", 121500000),
        "NAV_SWAP": k("NAV1_RADIO_SWAP"),
        "COM_MHZ_UP": k("COM_RADIO_WHOLE_INC"),
        "COM_MHZ_DN": k("COM_RADIO_WHOLE_DEC"),
        "COM_KHZ_UP": k("COM_RADIO_FRACT_INC"),
        "COM_KHZ_DN": k("COM_RADIO_FRACT_DEC"),
        "NAV_MHZ_UP": k("NAV1_RADIO_WHOLE_INC"),
        "NAV_MHZ_DN": k("NAV1_RADIO_WHOLE_DEC"),
        "NAV_KHZ_UP": k("NAV1_RADIO_FRACT_INC"),
        "NAV_KHZ_DN": k("NAV1_RADIO_FRACT_DEC"),
    },
    2: {
        "COM_SWAP": k("COM2_RADIO_SWAP"),
        "COM_121_5": k("COM2_RADIO_SET_HZ", 121500000),
        "NAV_SWAP": k("NAV2_RADIO_SWAP"),
        "COM_MHZ_UP": k("COM2_RADIO_WHOLE_INC"),
        "COM_MHZ_DN": k("COM2_RADIO_WHOLE_DEC"),
        "COM_KHZ_UP": k("COM2_RADIO_FRACT_INC"),
        "COM_KHZ_DN": k("COM2_RADIO_FRACT_DEC"),
        "NAV_MHZ_UP": k("NAV2_RADIO_WHOLE_INC"),
        "NAV_MHZ_DN": k("NAV2_RADIO_WHOLE_DEC"),
        "NAV_KHZ_UP": k("NAV2_RADIO_FRACT_INC"),
        "NAV_KHZ_DN": k("NAV2_RADIO_FRACT_DEC"),
    },
}
RADIO_UNMAPPED = {               # both units
    "FREQ_PUSH": "the FREQ knob's mode is the panel's: each mode sends buttons of its own",
}
# the one ADF receiver, from both units: the knob tunes the active frequency, ADF ⇆ swaps it with the standby
ADF = {
    "ADF_SWAP": k("ADF1_RADIO_SWAP"),
    "ADF_100_UP": k("ADF_100_INC"),
    "ADF_100_DN": k("ADF_100_DEC"),
    "ADF_1_UP": k("ADF_1_INC"),
    "ADF_1_DN": k("ADF_1_DEC"),
    "ADF_10_UP": k("ADF_10_INC"),
    "ADF_10_DN": k("ADF_10_DEC"),
}
# the transponder (device 1): squawk, digit 1 is the thousands. XPDR mode switches between standby and ALT through
# the simulator's TRANSPONDER STATE:1 (the SDK: settable, 0 off, 1 standby, 2 test, 3 on, 4 ALT, 5 ground), which
# holds the mode of Working Title's units (XPDR.ts) and of the KT 76, whose knob sets it and turns with it
# (ASOBO_Transponder_Knob_Setting_Template in the SDK's Asobo\Transponder\Transponder.xml, with this statement):
# standby or off goes to ALT, any other mode to standby. A code entered with the squawk digits forgets the code VFR
# kept, so VFR on the VFR code never returns to an old one
FORGET_SQUAWK = f"0 (>L:{_KEEPS})"
SQUAWK = {
    **{f"SQK_D{d}_{way}": f"{k(f'XPNDR_{step}_{event}')} {FORGET_SQUAWK}"
       for d, step in ((1, 1000), (2, 100), (3, 10), (4, 1)) for way, event in (("UP", "INC"), ("DN", "DEC"))},
    "IDENT": k("XPNDR_IDENT_ON"),
    "VFR": vfr(),
    "XPDR_MODE": "(A:TRANSPONDER STATE:1, Enum) 1 > if{ 1 } els{ 4 } (>A:TRANSPONDER STATE:1, Enum)",
}
# the cockpit lighting (device 1): TOGGLE_CABIN_LIGHTS sent without the circuit the SDK lets it name, assumed to
# toggle the aircraft's cabin lights as a whole
LIGHTS = {
    "CABIN_LT": k("TOGGLE_CABIN_LIGHTS"),
}


def dimmer(read, writes, step, switches=()):
    """A dimmer a step up or down, from 0 to 100 (20 detents end to end): read, the variable it steps (RPN, as
    "(L:name, Number)" or "(B:NAME)"), set in register 0 and written to every one of writes (as "L:name" or
    "B:NAME_Set"), and the lights' switches on above 0 and off at 0"""
    sign, limit = ("+", "100 min") if step > 0 else ("-", "0 max")
    return " ".join([f"{read} {abs(step)} {sign} {limit} sp0", *(f"l0 (>{w})" for w in writes),
                     *(f"l0 0 > (>{s})" for s in switches)])


def toggle(read, writes, on=1):
    """A light pushed on or off: read, its state (RPN), and every one of writes set to on or 0 as it goes"""
    return " ".join([f"{read} 0 > ! {on} * sp0", *(f"l0 (>{w})" for w in writes)])


_DIMMERS = "the dimmers differ by aircraft: their key events take the aircraft's own circuit or potentiometer"
LIGHTS_UNMAPPED = dict.fromkeys(("PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN"), _DIMMERS)
# the RANGE knob (device 1): its tilts and push pan the map and work its pointer
PAN = ("PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT", "PTR", "S_PAN_UP", "S_PAN_DN", "S_PAN_LEFT", "S_PAN_RIGHT",
       "S_PTR")
RANGE_KNOB = ("RANGE_CW", "RANGE_CCW", "S_RANGE_CW", "S_RANGE_CCW", *PAN)

# ---------------- the heading bug, the course of NAV 1, the autopilot's level mode ----------------
# the heading bug of slot 1 and the heading indicator of index 1 (Working Title's APPublisher.ts and Ahrs.ts read
# both by index)
HEADING_VAR, COURSE = "AUTOPILOT HEADING LOCK DIR:1", "NAV OBS:1"
# the fast step of the heading bug, 10° (docs/using/controls.md#knobs)
HEADING_FAST = {
    "HDG_10_UP": turn(HEADING_VAR, "HEADING_BUG_SET", 10),
    "HDG_10_DN": turn(HEADING_VAR, "HEADING_BUG_SET", -10),
}
SYNC = "(A:HEADING INDICATOR:1, degrees) near dnor (>K:HEADING_BUG_SET)"         # the bug to the heading shown
# the ALT/HDG knob's heading: the heading bug, whose push syncs it to the heading, in every autopilot part
HEADING = {"HDG_1_UP": k("HEADING_BUG_INC"), "HDG_1_DN": k("HEADING_BUG_DEC"), **HEADING_FAST, "HDG_SYNC": SYNC}


def nav(code):
    """The code for the NAV radio the CDI shows, # for its number, by AUTOPILOT NAV SELECTED, which the G3X Touch
    keeps on its CDI with an autopilot (its ActiveNavSourceManager.ts)"""
    return f"(A:AUTOPILOT NAV SELECTED, Number) 2 == if{{ {code.replace('#', '2')} }} els{{ {code.replace('#', '1')} }}"


def cdi(gps, radio):
    """The code for what the G3X Touch's CDI shows: gps for its GPS, radio for a NAV radio (# for its number)"""
    return f"(A:GPS DRIVES NAV1, Bool) if{{ {gps} }} els{{ {nav(radio)} }}"


def course_fast(shows):
    """The fast step of the course, 10°, on what the CDI shows, by shows(gps, radio) (cdi() or the G1000's): the
    GPS's OBS course, which Working Title's units take from the simulator's (LNavObsManager.ts,
    GarminObsLNavModule.ts), or the course of the NAV radio"""
    return {
        "CRS_10_UP": shows(turn("GPS OBS VALUE", "GPS_OBS_SET", 10), turn("NAV OBS:#", "VOR#_SET", 10)),
        "CRS_10_DN": shows(turn("GPS OBS VALUE", "GPS_OBS_SET", -10), turn("NAV OBS:#", "VOR#_SET", -10)),
    }
# LVL engages the autopilot in level lateral and vertical modes, as the GMC 507's and GFC 700's LVL keys; Garmin's
# autopilot takes both leveler events (GarminAPStateManager.ts)
LEVEL = "(>K:AP_WING_LEVELER_ON) (>K:AP_PITCH_LEVELER_ON) (>K:AUTOPILOT_ON)"
# CRS CTR on NAV radio #: the course to the VOR (its radial + 180°) or the localizer's, in whole degrees, as the
# G3X's Course knob push sets it; nothing without a signal
CENTRE = ("(A:NAV HAS LOCALIZER:#, Bool) if{ (A:NAV LOCALIZER:#, degrees) near dnor (>K:VOR#_SET) } "
          "els{ (A:NAV HAS NAV:#, Bool) if{ (A:NAV RADIAL:#, degrees) 180 + near dnor (>K:VOR#_SET) } }")

# ---------------- the rows Working Title's G1000 NXi and G3X Touch share ----------------
# Working Title builds the GFC 700 of the G1000 NXi and the GFC 500 of the G3X Touch from Garmin's autopilot
# (GarminAPStateManager.ts, GarminAPConfig.ts in garminsdk), which takes the simulator's autopilot key events, as the
# G3X's own AFCS page sends them (MFD/Views/AfcsControlsView/AfcsControlsView.tsx), and toggles VNAV on an H: event
_VS_KEY = k("AP_VS_HOLD")
_FLC_KEY = k("FLIGHT_LEVEL_CHANGE")
_VNV_KEY = h("AS1000_VNAV_TOGGLE")


def reference(vs, pitch, alt=None, flc=None):
    """UP or DN: the code that steps the reference of the active vertical mode, by the simulator's A: flags of the
    modes, which Working Title's directors set (APVSDirector.ts, APFLCDirector.ts, APPitchDirector.ts): alt in ALT
    hold, vs in VS, flc in FLC and pitch in pitch mode, the first of them that is on; nothing in another mode or in
    one without a code"""
    modes = (("AUTOPILOT ALTITUDE LOCK", alt), ("AUTOPILOT VERTICAL HOLD", vs), ("AUTOPILOT FLIGHT LEVEL CHANGE", flc),
             ("AUTOPILOT PITCH HOLD", pitch))
    out = ""
    for flag, code in reversed([mode for mode in modes if mode[1]]):
        out = f"(A:{flag}, Bool) if{{ {code} }}" + (f" els{{ {out} }}" if out else "")
    return out


# the GMC 507's nose up/down wheel and the GFC 700's NOSE UP and NOSE DN keys set the reference of the active
# vertical mode, as the G3X's AFCS page does: VS, then IAS (nose up slows it), then pitch
_NOSE_UP = reference(k("AP_VS_VAR_INC"), k("AP_PITCH_REF_INC_UP"), flc=k("AP_SPD_VAR_DEC"))
_NOSE_DN = reference(k("AP_VS_VAR_DEC"), k("AP_PITCH_REF_INC_DN"), flc=k("AP_SPD_VAR_INC"))
# the autopilot keys, the yaw damper and the ALT/HDG knob
GARMIN_SHARED = {
    # autopilot keys
    "AP": k("AP_MASTER"),
    "ALT": k("AP_ALT_HOLD"),
    "HDG": k("AP_HDG_HOLD"),
    # Garmin's FD key does nothing while the autopilot is engaged
    "FD": "(A:AUTOPILOT MASTER, Bool) ! if{ (>K:TOGGLE_FLIGHT_DIRECTOR) }",
    "VS": _VS_KEY,
    "NAV": k("AP_NAV1_HOLD"),
    "UP": _NOSE_UP,
    "FLC": _FLC_KEY,
    "APR": k("AP_APR_HOLD"),
    "DN": _NOSE_DN,
    "VNV": _VNV_KEY,
    "LVL": LEVEL,
    # shifted keys
    "YD": k("YAW_DAMPER_TOGGLE"),
    "S_VS": _VS_KEY,
    "S_UP": _NOSE_UP,
    "S_FLC": _FLC_KEY,
    "S_DN": _NOSE_DN,
    "S_VNV": _VNV_KEY,
    # ALT/HDG knob: the selected altitude, 100 ft for a value up to 999 and 1000 ft above (AltitudeSelectManager.ts,
    # GarminAutopilot.ts), and the heading bug, whose push syncs it to the heading
    "ALT_100_UP": k("AP_ALT_VAR_INC"),
    "ALT_100_DN": k("AP_ALT_VAR_DEC"),
    "ALT_1000_UP": k("AP_ALT_VAR_INC", 1000),
    "ALT_1000_DN": k("AP_ALT_VAR_DEC", 1000),
    **HEADING,
}
STD = {"BARO_STD": k("BAROMETRIC_STD_PRESSURE", 1)}         # the altimeter of index 1
# STD toggled, for an altimeter that BAROMETRIC_STD_PRESSURE only ever sets to STD: from another setting it keeps
# that setting in L:AvionicsPanel_Baro (millibars) and sets STD; on STD it sets the setting kept with KOHLSMAN_SET
# (millibars * 16), once. STD is 1013.25 hPa, and 29.92 inHg reads 1013.21: within 0.1 hPa of 1013.23 takes both and
# leaves out a QNH of 1013 hPa, 29.91 or 29.93 inHg, where a press sets STD. KOHLSMAN_SET goes without the
# altimeter's index, as KOHLSMAN_INC and _DEC do: the SDK does not say in which order RPN gives an event two
# parameters. A turn of the BARO ring forgets the setting kept (NAV1_KNOBS), so a press never returns to an old one
# (the IFR-1's Bonanza profile keeps the setting the same way, but sets its second altimeter by index: ifr1.py)
BARO, KEPT_BARO = "(A:KOHLSMAN SETTING MB:1, millibars)", "AvionicsPanel_Baro"
AT_STD = "1013.23 - abs 0.1 <"                 # of a setting in millibars: 1 on STD
FORGET_BARO = f"0 (>L:{KEPT_BARO})"
STD_TOGGLE = {"BARO_STD": (
    f"{BARO} {AT_STD} if{{ (L:{KEPT_BARO}, Number) 0 > if{{ (L:{KEPT_BARO}, Number) 16 * near "
    f"{k('KOHLSMAN_SET')} {FORGET_BARO} }} }} els{{ {BARO} (>L:{KEPT_BARO}) {STD['BARO_STD']} }}")}

# ---------------- the instruments round a Bendix/King autopilot (device 1) ----------------
# with SHIFT, the course of NAV 1 and the altimeter (KOHLSMAN_INC and _DEC without an index, as the SDK's Key Events
# list them; STD names the first altimeter, and pressed again returns to the setting before: STD_TOGGLE), as the
# simulator's key events; CRS CTR centres the course of NAV 1
NAV1_KNOBS = {
    "CRS_CTR": CENTRE.replace("#", "1"),
    "CRS_1_UP": k("VOR1_OBI_INC"),
    "CRS_1_DN": k("VOR1_OBI_DEC"),
    "CRS_10_UP": turn(COURSE, "VOR1_SET", 10),
    "CRS_10_DN": turn(COURSE, "VOR1_SET", -10),
    "BARO_UP": f"{k('KOHLSMAN_INC')} {FORGET_BARO}",
    "BARO_DN": f"{k('KOHLSMAN_DEC')} {FORGET_BARO}",
    **STD_TOGGLE,
}

# ---------------- VNV without VNAV: the descent calculator ----------------
# For an autopilot without VNAV (the KAP 140, the KFC 150), VNV works out once per press the vertical speed that
# reaches the selected altitude at the navigator's active waypoint: Δ / (distance / ground speed in minutes). Δ is the
# selected altitude (AUTOPILOT ALTITUDE LOCK VAR:1, the slot the sim's SimPlane.js names the selected one, which
# KAP140.js leaves alone in ALT hold, where it holds its altitude in slot 2) less the altimeter's (INDICATED
# ALTITUDE); the ground speed is the aircraft's own (GROUND VELOCITY), whatever the navigator. It descends only: these
# autopilots hold a climb rate with no care for the airspeed. It rounds the rate to 100 ft/min, keeps its size between
# 300 and 1500 ft/min and sets it with the SDK's AP_VS_VAR_SET_ENGLISH, after the autopilot's code that enters VS
# (before) or before the one that engages it (after), so the autopilot flies VS at that rate: the KAP 140 takes the
# present vertical speed as it enters VS, and the KAS 297B's VS ENG takes the rate it shows. It does nothing without a
# distance, at 30 knots or less (below which TDS's GTNXi and Working Title's VNAV work out no times or rates either)
# or unless the selected altitude is more than 100 ft below. The distance is the first above 0 of distances (RPN
# reads, in nautical miles), which the navigators declare: TDS's GTNXi's (gtn.py), or the simulator's GPS WP DISTANCE,
# which Working Title's GNS and G1000 NXi write from their own LNAV (GpsSynchronizer.ts in
# microsoft/msfs-avionics-mirror's sdk/autopilot, run by the GNS's MainScreen.tsx and the NXi's WTG1000_MFD.tsx);
# Working Title publishes no L: variable of its own for it. A profile joined from parts reads its navigators' (the
# autopilot part's VNV, part.compose), the part alone every navigator's (families/__init__.py). A required rate
# (required: an RPN read in ft/min, 0 for none, as the G1000 NXi gives one, g1000.py) goes first when it is a descent
# of 300 ft/min or more; a smaller one, as for a constraint far ahead, gives way to the rate worked out. VNV and
# SHIFT, VNV are the same: the key has no amber legend, so a stray SHIFT changes nothing.
_SIZE = "100 / near 100 * 300 max 1500 min"          # a rate's size, rounded to 100 ft/min and clamped
_SET_VS = k("AP_VS_VAR_SET_ENGLISH")
_SELECTED = "(A:AUTOPILOT ALTITUDE LOCK VAR:1, feet)"


def _set(rate, before, after):
    """rate (RPN, a size in ft/min) set as a descent, between the autopilot's codes before and after"""
    return " ".join(filter(None, (before, f"{rate} {_SIZE} neg {_SET_VS}", after)))


def descent(before="", after="", distances=(GPS_DISTANCE,), required=None):
    """VNV's code: the vertical speed to the selected altitude at the active waypoint, by registers 0 (Δ, ft),
    1 (the distance, nm), 2 (the ground speed, kt) and 3 (the rate, ft/min)"""
    first, *rest = distances
    return " ".join([
        f"{first} sp1", *(f"l1 0 > ! if{{ {d} sp1 }}" for d in rest),
        f"{_SELECTED} (A:INDICATED ALTITUDE, feet) - sp0 (A:GROUND VELOCITY, knots) sp2",
        f"{required or 0} sp3 l3 neg 300 < if{{ 0 sp3 l1 0 > l2 30 > and if{{ l0 l2 * l1 60 * / sp3 }} }}",
        f"l3 0 < l0 neg 100 > and if{{ {_set('l3 abs', before, after)} }}",
    ])


# ---------------- the KAP 140 and the instruments round it (device 1) ----------------
# the KAP 140 flies VS whenever it is engaged without ALT: VNV leaves ALT hold as its ALT key does, which the sim's
# KAP140.js turns into AP_PANEL_VS_ON with the autopilot engaged. VNV sends that event itself, ahead of the rate: an
# H: event runs in the gauge after the code's K: events, so its VS would take the present vertical speed after the
# rate. The rate it holds is assumed to be the simulator's, which AP_VS_VAR_SET_ENGLISH sets. Behind Working Title's
# G1000 NXi or GNS, their autopilot state manager takes AP_PANEL_VS_ON and enters VS a frame later, its VS director
# then writing the present vertical speed over the rate (GarminAPStateManager.ts, APVSDirector.ts in
# microsoft/msfs-avionics-mirror): VNV sets the rate again as the key is let go (to check in the sim:
# docs/using/mapping.md).
KAP140_VS = "(A:AUTOPILOT MASTER, Bool) (A:AUTOPILOT ALTITUDE LOCK, Bool) and if{ 0 (>K:AP_PANEL_VS_ON) }"


def KAP140_VNV(**kwargs):    # noqa: N802 (named as the other autopilots' VNV)
    """VNV's entry, of the distances and required rate (part.compose): VS and the rate pressed, the rate again let go"""
    return {"press": descent(before=KAP140_VS, **kwargs), "release": descent(**kwargs)}


KAP140 = {
    # autopilot keys
    "AP": h("KAP140_Push_AP"),
    "ALT": h("KAP140_Push_ALT"),
    "HDG": h("KAP140_Push_HDG"),
    "NAV": h("KAP140_Push_NAV"),
    "UP": h("KAP140_Push_UP"),
    "APR": h("KAP140_Push_APR"),
    "DN": h("KAP140_Push_DN"),
    # VS, which the KAP 140 has no key for: leaves ALT hold for VS, as its ALT key does (KAP140_VS); SHIFT does the same
    "VS": KAP140_VS,
    "S_VS": KAP140_VS,
    # shifted keys
    "S_UP": h("KAP140_Push_UP"),
    "BC": h("KAP140_Push_REV"),
    "S_DN": h("KAP140_Push_DN"),
    # ALT/HDG knob: the KAP 140's altitude knob (inner 100 ft, outer 1000 ft) and the heading bug
    "ALT_100_UP": h("KAP140_Knob_Inner_INC"),
    "ALT_100_DN": h("KAP140_Knob_Inner_DEC"),
    "ALT_1000_UP": h("KAP140_Knob_Outer_INC"),
    "ALT_1000_DN": h("KAP140_Knob_Outer_DEC"),
    **HEADING,
}
_FLC = "the KAP 140 has no FLC mode"
KAP140_UNMAPPED = {
    "TEST": "the KAP 140 tests itself at power-up: it has no TEST key",
    "ARM": "the sim's KAP 140 does nothing on ARM: its KAP140.js handles KAP140_Push_ARM with an empty case",
    "FD": "the KAP 140 has no flight director",
    "YD": "the KAP 140 has no yaw damper",
    "FLC": _FLC,
    "S_FLC": _FLC,
    "LVL": "the KAP 140 has no level mode",
    "HALF_BANK": "the KAP 140 has no low-bank mode",
    "GPSS": "the KAP 140 has no GPSS key: NAV follows the CDI, on GPS or VLOC",
}
# the audio panel (KMA 28, GMA 1347 and the like): MIC selects the transmitter, COM the receivers
AUDIO = {
    "MIC1": transmit(1),
    "COM1": receive(1),
    "MIC2": transmit(2),
    "COM2": receive(2),
    "ADF_AUDIO": k("RADIO_ADF_IDENT_TOGGLE"),
    "NAV1_AUDIO": k("RADIO_VOR1_IDENT_TOGGLE"),
    "DME_AUDIO": k("RADIO_DME1_IDENT_TOGGLE"),
    "NAV2_AUDIO": k("RADIO_VOR2_IDENT_TOGGLE"),
}


def cockpit(key, name, knobs):
    """A cockpit part: the ALT/HDG knob with SHIFT (knobs), the audio panel, transponder and lighting, and the
    radios and ADF of both units (an aircraft's own lights go over it in its profile: compose(rows=))"""
    device = {1: {**knobs, **AUDIO, **SQUAWK, **LIGHTS, **RADIO[1], **ADF}, 2: {**RADIO[2], **ADF}}
    unmapped = {1: {**LIGHTS_UNMAPPED, **RADIO_UNMAPPED}, 2: dict(RADIO_UNMAPPED)}
    return part(key, name, "cockpit", device, unmapped)


# the autopilot and cockpit parts round the KAP 140, as in the Cessna 172 Skyhawk Classic and Carenado's C182T; VNV
# and SHIFT, VNV are the descent calculator, of the distances the part reads alone (part.alone) or in a profile
# (part.compose)
KAP140_AUTOPILOT = part("kap140", "KAP 140", "autopilot", {1: KAP140}, {1: KAP140_UNMAPPED}, VNV=KAP140_VNV)
BENDIX_KING = cockpit("bendix-king", "Bendix/King", NAV1_KNOBS)
