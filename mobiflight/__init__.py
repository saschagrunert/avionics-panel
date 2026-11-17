"""MobiFlight profiles for the panel, one per avionics family or aircraft, and its avionics parts
(docs/using/mapping.md#generated-profiles). Standard library only.

- families/: the avionics parts (autopilots, cockpits, navigators; part.py), each a table of button names of
  firmware/buttonmap.py -> MobiFlight calculator code written with the statements of rpn.py, and the profiles
  joined from them or written for an aircraft.
- profile.py: writes the project (.mfproj) of MobiFlight 11.2 and newer for both joysticks.
- ifr1.py: the same profiles for the Octavi IFR-1 (MobiFlight 11.3 and newer), from the panel's tables, and
  ifr1_card.py their cards and cheat sheets.
"""
