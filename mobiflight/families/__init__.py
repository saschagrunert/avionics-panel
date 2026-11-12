"""One table per avionics family: a module with

- NAME: the family as the project names it;
- DEVICE: {1: {button: entry}, 2: {button: entry}}, by the button names of firmware/buttonmap.py. An entry is
  MobiFlight calculator code (rpn.py), sent on press, or {"press": code, "release": code} (either may be left
  out) for a control that needs the release too;
- UNMAPPED: {1: {button: reason}, 2: {button: reason}}, every other button of the device, with the reason it
  sends nothing in this family.

A table covers every button of the panel, so it describes one cockpit, not one unit; it may fit others, as the
GNS table fits KX 155/165 radios without a GNS. Tables join the parts several cockpits share (parts.py): the
simulator's radios, ADF and transponder and the KAP 140 cockpit around a navigator. Each table names the source of
its events; codes beyond a plain key or H: event say theirs where they are written.

A new family is one more module here and its line in FAMILIES.
"""
from mobiflight.families import g3x, g1000, gns, gtn

FAMILIES = {"g1000": g1000, "g3x": g3x, "gns": gns, "gtn": gtn}
