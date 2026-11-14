"""The rows of single aircraft that their profiles lay over their parts' (families/__init__.py): the lighting of the
COWS DA40 and of Carenado's C182T, as the projects these aircraft are flown with set it, by the simulator's input
events (B:, MSFS 2024), whose value runs from 0 to 100 for a dimmer, or is 0 or 1 for a switch as the DA40's cabin
lights, and which a _Set event sets."""
from mobiflight.families import parts

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
# pedestal and its second potentiometer, all alike), the cabin light push its two cabin lights, full on or off
_C182T_PANEL = ("B:LIGHTING_POTENTIOMETER_3_Set", "B:LIGHTING_PANEL_1_Set", "B:LIGHTING_PEDESTRAL_1_Set",
                "B:LIGHTING_POTENTIOMETER_4_Set")
C182T_LIGHTS = {
    "PANEL_LT_UP": parts.dimmer("(B:LIGHTING_POTENTIOMETER_3)", _C182T_PANEL, 5),
    "PANEL_LT_DN": parts.dimmer("(B:LIGHTING_POTENTIOMETER_3)", _C182T_PANEL, -5),
    "CABIN_LT": parts.toggle("(B:LIGHTING_CABIN_1)", ("B:LIGHTING_CABIN_1_Set", "B:LIGHTING_CABIN_2_Set"), 100),
}
C182T_UNMAPPED = dict.fromkeys(("FLOOD_LT_UP", "FLOOD_LT_DN"),
                               "the C182T dims all its panel lights with one knob: the outer ring")
