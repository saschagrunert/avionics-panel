"""The rows of single aircraft that their profiles lay over their parts' (families/__init__.py): the lighting of the
COWS DA40 and of Carenado's C182T, as the projects these aircraft are flown with set it, by the simulator's input
events (B:, MSFS 2024), whose value runs from 0 to 100 for a dimmer, or is 0 or 1 for a switch as the DA40's cabin
lights, and which a _Set event sets; and the DA40's standby altimeter, set with the PFD's."""
from mobiflight.families import g1000, parts
from mobiflight.families.rpn import lset

# COWS DA40: the outer ring the panel lights, the inner ring the glareshield lights, the cabin light push the three
# cabin lights, on (1) or off as the first goes
DA40_LIGHTS = {
    "PANEL_LT_UP": parts.dimmer("(B:LIGHTING_PANEL_1)", ("B:LIGHTING_PANEL_1_Set",), 5),
    "PANEL_LT_DN": parts.dimmer("(B:LIGHTING_PANEL_1)", ("B:LIGHTING_PANEL_1_Set",), -5),
    "FLOOD_LT_UP": parts.dimmer("(B:LIGHTING_GLARESHIELD_1)", ("B:LIGHTING_GLARESHIELD_1_Set",), 5),
    "FLOOD_LT_DN": parts.dimmer("(B:LIGHTING_GLARESHIELD_1)", ("B:LIGHTING_GLARESHIELD_1_Set",), -5),
    "CABIN_LT": parts.toggle("(B:LIGHTING_CABIN_1)", tuple(f"B:LIGHTING_CABIN_{n}_Set" for n in (1, 2, 3))),
}

# Carenado C182T: one dimmer for all its panel lights on the outer ring (its first potentiometer, the panel, the
# pedestal and its second potentiometer, all alike), its two cabin lights dimmed together on the inner ring, and the
# cabin light push those full on or off, as the project the C182T is flown with sets them
_C182T_PANEL = ("B:LIGHTING_POTENTIOMETER_3_Set", "B:LIGHTING_PANEL_1_Set", "B:LIGHTING_PEDESTRAL_1_Set",
                "B:LIGHTING_POTENTIOMETER_4_Set")
_C182T_CABIN = ("B:LIGHTING_CABIN_1_Set", "B:LIGHTING_CABIN_2_Set")
C182T_LIGHTS = {
    "PANEL_LT_UP": parts.dimmer("(B:LIGHTING_POTENTIOMETER_3)", _C182T_PANEL, 5),
    "PANEL_LT_DN": parts.dimmer("(B:LIGHTING_POTENTIOMETER_3)", _C182T_PANEL, -5),
    "FLOOD_LT_UP": parts.dimmer("(B:LIGHTING_CABIN_1)", _C182T_CABIN, 5),
    "FLOOD_LT_DN": parts.dimmer("(B:LIGHTING_CABIN_1)", _C182T_CABIN, -5),
    "CABIN_LT": parts.toggle("(B:LIGHTING_CABIN_1)", _C182T_CABIN, 100),
}

# COWS DA40: the standby altimeter, set with the PFD's BARO knob and STD as the NXi sets its own (g1000.COCKPIT). It
# reads L:KOHLSMAN SETTING HG:2 (inHg), which only its own knob sets, 0.01 inHg a detent from 28 to 31.5 (the knob's
# behaviour code in the aircraft), not the sim's altimeter 2. The NXi sets its setting only with KOHLSMAN_SET from
# its JS (Altimeter.tsx), which the sim applies after the panel's code has run, so the code reads the PFD's setting
# before the H: event: the sim's altimeter 1, to 0.01 inHg as the NXi reads it. A detent steps the standby 0.01 inHg
# from there, the NXi's step with the PFD in inHg (in hPa it steps 1 hPa, and the standby is then off by up to
# 0.02 inHg, less than one hPa). The NXi steps its own copy of the setting, which follows the sim's a frame or so
# later, so in a fast spin the two may step from different values; the next detent sets the standby again.
#
# On STD a turn leaves STD for the setting before it and steps from that (onbaroKnobTurn, updateBaroStd), so on STD
# a detent steps the standby from that setting: the one kept while the standby still reads the 29.92 the panel's
# STD gave it, else the standby's own, which STD Baro in the cockpit leaves as it was. STD toggles the standby with
# the PFD: from another setting it keeps the PFD's setting, which the NXi returns to, in
# L:AvionicsPanel_Standby_Baro and sets 29.92; on STD it sets the setting kept, once (parts.STD_TOGGLE's test), and
# with none kept (STD from the cockpit, or a QNH of 29.92, which the push takes for STD) leaves the standby as it
# is. A push that misses STD Baro, from another menu of the PFD's softkeys, sets the standby all the same; the next
# detent sets it again. A detent forgets the setting kept, as the NXi leaves STD with it.
_STANDBY, _STANDBY_KEPT = "KOHLSMAN SETTING HG:2", "AvionicsPanel_Standby_Baro"
_PFD_HUNDREDTHS = "(A:KOHLSMAN SETTING HG:1, inHg) 100 * near"
_KEPT = f"(L:{_STANDBY_KEPT}, Number)"
_ON_STD_FROM = (f"(L:{_STANDBY}, Number) 100 * near sp0 l0 2992 == {_KEPT} 0 > and "
                f"if{{ {_KEPT} 100 * near }} els{{ l0 }}")


def _standby(hundredths):
    """Sets the standby to a setting in hundredths of an inHg, within its knob's 28 to 31.5"""
    return f"{hundredths} 3150 min 2800 max 100 / (>L:{_STANDBY})"


def _standby_step(button, step):
    base = f"{parts.BARO} {parts.AT_STD} if{{ {_ON_STD_FROM} }} els{{ {_PFD_HUNDREDTHS} }}"
    return f"{g1000.COCKPIT.DEVICE[1][button]} {_standby(f'{base} {step}')} {lset(_STANDBY_KEPT, 0)}"


DA40_STANDBY = {
    "BARO_UP": _standby_step("BARO_UP", "1 +"),
    "BARO_DN": _standby_step("BARO_DN", "1 -"),
    "BARO_STD": (f"{g1000.COCKPIT.DEVICE[1]['BARO_STD']} {parts.BARO} {parts.AT_STD} if{{ {_KEPT} 0 > if{{ "
                 f"{_standby(f'{_KEPT} 100 * near')} {lset(_STANDBY_KEPT, 0)} }} }} "
                 f"els{{ {lset(_STANDBY_KEPT, f'{_PFD_HUNDREDTHS} 100 /')} {_standby(2992)} }}"),
}
