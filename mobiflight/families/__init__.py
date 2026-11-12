"""One table per avionics family: a module with

- NAME: the family as the project names it;
- DEVICE: {1: {button: entry}, 2: {button: entry}}, by the button names of firmware/buttonmap.py. An entry is
  a HubHop preset by its name, vendor.aircraft.label, sent on press, or {"press": name, "release": name}
  (either may be left out) for a control that needs the release too. The preset's code may be any of
  MobiFlight's (K: and H: events, B: input events, L: variables);
- UNMAPPED: {1: {button: reason}, 2: {button: reason}}, every other button of the device, with the reason it
  sends nothing in this family.

A table covers every button of the panel, so it describes one cockpit, not one unit. Build its dicts from
shared parts where cockpits share units: a table for the KAP 140 with a GNS 530/430 joins a KAP 140 part and
a GNS part, and the K: radio and squawk rows of the G1000 belong in a part of their own once a second table
uses them. HubHop names the TDS GTN presets by model and unit ("TDS Sim.GTNXi 750 1", "GTNXi 750 2",
"GTNXi 650 2"), so a GTN 750 with a 650 and two 750s are two tables, made from one part per model.

A new family is one more module here and its line in FAMILIES. `py -m mobiflight.hubhop` (`python3` on Linux
and macOS) checks that HubHop has each of its presets once.
"""
from mobiflight.families import g1000

FAMILIES = {"g1000": g1000}
