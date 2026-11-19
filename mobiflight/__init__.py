"""MobiFlight profiles for the panel, one per avionics family or aircraft, and its avionics parts
(docs/using/mapping.md#generated-profiles). Standard library only.

- families/: the avionics parts (autopilots, cockpits, navigators; part.py), each a table of button names of
  firmware/buttonmap.py -> MobiFlight calculator code written with the statements of rpn.py, and the profiles
  joined from them or written for an aircraft.
- profile.py: writes the project (.mfproj) of MobiFlight 11.2 and newer for both joysticks, and every file the
  command line (__main__.py) writes, whole or not at all.
- card.py, sheet.py (its words in sheet_text.py) and cards.py: each profile's quick-reference card, cheat sheet and
  the index of them all; joystick.py: MobiFlight's joystick definition of the panel.
- ifr1.py: the same profiles for the Octavi IFR-1, from the panel's tables, and ifr1_grid.py, ifr1_card.py and
  ifr1_sheet.py their cards and cheat sheets.
"""
