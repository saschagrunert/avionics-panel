"""JLCPCB BOM + CPL (pick and place) for the rev 1 board."""
import csv
from collections import OrderedDict
import board as B

B.build()
FOOT = {"1N4148W": "SOD-123", "RP2040": "LQFN-56 7x7", "TYPE-C-31-M-12": "USB-C 16P", "W25Q16JVSNIQ": "SOIC-8 150mil",
        "ABM8-272-T3 12MHz": "3225 4-pad", "XC6206P332MR": "SOT-23"}
# JLCPCB gets the bottom side only (Economic assembly); the top-side through-hole parts go to THT-LCSC.csv.
SMD = [p for p in B.PARTS if p[6] == "bottom"]
groups = OrderedDict()
for ref, value, lcsc, x, y, rot, side in SMD:
    groups.setdefault((value, lcsc), []).append(ref)
with open("avionics-panel-rev1-BOM.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"])
    for (value, lcsc), refs in groups.items():
        w.writerow([value, ",".join(refs), FOOT.get(value, "0603"), lcsc, len(refs)])
with open("avionics-panel-rev1-CPL.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for ref, value, lcsc, x, y, rot, side in SMD:
        w.writerow([ref, f"{x:.3f}mm", f"{B.H - y:.3f}mm", "Top" if side == "top" else "Bottom", rot % 360])
# Through-hole parts on the top side, for hand soldering (Economic assembly does the SMD side only).
# One panel, plus spares where a part is cheap or easy to damage. Upload to LCSC's BOM tool.
SPARE = {"1-1825910-4": 2, "XL-302UYC": 4, "XL-302UWC": 4}
tht = OrderedDict()
for ref, value, lcsc, x, y, rot, side in B.PARTS:
    if side == "top":
        tht.setdefault((value, lcsc), []).append(ref)
with open("avionics-panel-rev1-THT-LCSC.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["LCSC Part Number", "Quantity", "Manufacturer Part", "Designator"])
    for (value, lcsc), refs in tht.items():
        w.writerow([lcsc, len(refs) + SPARE.get(value, 0), value, ",".join(refs)])
print(len(SMD), "SMD parts,", len(groups), "BOM lines;", sum(len(r) for r in tht.values()), "through-hole parts for hand soldering")
for (value, lcsc), refs in groups.items():
    print(f"  {len(refs):3d} x {value:20s} {lcsc}")
