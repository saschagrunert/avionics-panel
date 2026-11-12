"""MobiFlight profiles for the panel, one per avionics family (docs/using/mapping.md#generated-profiles).
Standard library only.

- families/: one table per avionics family, each button name of firmware/buttonmap.py -> HubHop preset names.
- hubhop.py: downloads HubHop's preset database and looks the presets up in it.
- profile.py: writes the MobiFlight 11 project (.mfproj) for both joysticks.

The repository holds only the presets' names. Their codes and IDs come from HubHop's database at generation
time: HubHop's presets are HubHop's data, written by its authors, and not covered by this repository's licence.
"""
