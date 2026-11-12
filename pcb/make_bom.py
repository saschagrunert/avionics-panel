"""JLCPCB BOM + CPL (pick and place) for the rev 1 board, in two assembly variants (docs/building/building.md):
economic: BOM.csv / CPL.csv, the bottom side only (Economic assembly, all SMD), plus THT-LCSC.csv, the
    through-hole parts from LCSC for hand soldering;
full: BOM-full.csv / CPL-full.csv, both sides (Standard assembly): the SMD bottom and the through-hole parts on
    the top, one BOM and one CPL with the side in its Layer column.
"""
import csv
import json

import board as B

B.build()


def package(ref, lcsc):
    """The BOM footprint name: ours for a bottom-side part (board.part() records it), JLC's for a top-side one."""
    if B.FOOTPRINT[ref]:
        return B.FOOTPRINT[ref]
    with open(f"footprints/{lcsc}.json") as f:
        return json.load(f)["package"]


def grouped(parts):
    """{(value, LCSC number): [ref, ...]}, in the order of the parts."""
    groups = {}
    for ref, value, lcsc, *_ in parts:
        groups.setdefault((value, lcsc), []).append(ref)
    return groups


def write_bom(fname, parts):
    groups = grouped(parts)
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"])
        for (value, lcsc), refs in groups.items():
            foot = {package(r, lcsc) for r in refs}
            if len(foot) != 1:                         # a plain raise: asserts vanish under -O
                raise ValueError(f"{value} {lcsc}: one LCSC part on several footprints {sorted(foot)}")
            w.writerow([value, ",".join(refs), foot.pop(), lcsc, len(refs)])
    return groups


def write_cpl(fname, parts):
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref, _value, _lcsc, x, y, rot, side in parts:
            ref, mx, my, layer, rot = B.cpl(ref, x, y, rot, side)
            w.writerow([ref, f"{mx:.3f}mm", f"{my:.3f}mm", layer, rot])


# Economic: JLCPCB gets the bottom side only; the top-side through-hole parts go to THT-LCSC.csv.
SMD = [p for p in B.PARTS if p[6] == "bottom"]
TOP = [p for p in B.PARTS if p[6] == "top"]
groups = write_bom("avionics-panel-rev1-BOM.csv", SMD)
write_cpl("avionics-panel-rev1-CPL.csv", SMD)
# Full: both sides, the top-side rotations in JLC's top convention (board.py docstring; check.py fits them).
full = write_bom("avionics-panel-rev1-BOM-full.csv", SMD + TOP)
write_cpl("avionics-panel-rev1-CPL-full.csv", SMD + TOP)
# Through-hole parts on the top side, for hand soldering (economic variant only). One panel, plus spares where
# a part is cheap or easy to damage. Quantity is what to order, Needed what one board takes. Upload to LCSC's BOM
# tool.
SPARE = {"1-1825910-4": 2}
with open("avionics-panel-rev1-THT-LCSC.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["LCSC Part Number", "Quantity", "Manufacturer Part", "Designator", "Needed"])
    for (value, lcsc), refs in grouped(TOP).items():
        w.writerow([lcsc, len(refs) + SPARE.get(value, 0), value, ",".join(refs), len(refs)])
print(len(SMD), "SMD parts,", len(groups), "BOM lines;", len(TOP), "through-hole parts for hand soldering;",
      f"full variant {len(SMD) + len(TOP)} parts, {len(full)} BOM lines")
for (value, lcsc), refs in full.items():
    print(f"  {len(refs):3d} x {value:20s} {lcsc}")
