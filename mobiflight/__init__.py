"""MobiFlight profiles for the panel, one per avionics family (docs/using/mapping.md#generated-profiles).
Standard library only.

- families/: one table per avionics family, each button name of firmware/buttonmap.py -> MobiFlight calculator
  code, joined from the parts the families share (parts.py), written with the statements of rpn.py.
- profile.py: writes the MobiFlight 11 project (.mfproj) for both joysticks.
"""
