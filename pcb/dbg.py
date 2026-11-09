"""Debug plot of the routed board (debug.png). Usage: python3 dbg.py [x0 x1 y0 y1] (mm, board coordinates)."""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import board as B
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

with open("routed.json") as f:
    d = json.load(f)
pads = B.build()
x0, x1, y0, y1 = [float(v) for v in sys.argv[1:5]] if len(sys.argv) > 4 else (0, B.W, 0, B.H)
fig, ax = plt.subplots(figsize=(14, 14 * (y1 - y0) / (x1 - x0) + 0.5), dpi=110)
ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect("equal")
ax.add_patch(Rectangle((0, 0), B.W, B.H, fc="#0b3d20"))
sc = 72 / 25.4 * 14 / (x1 - x0) * 110 / 72 * 0.98 * 25.4 / 1  # points per mm approx
ppm = fig.dpi * 14 / (x1 - x0) / (fig.dpi / 72)
for s in d["segments"]:
    x1_, y1_, x2_, y2_, ly, net = s[:6]; w = s[6] if len(s) > 6 else B.TRACE_W
    ax.plot([x1_, x2_], [y1_, y2_], color="#e05050" if ly == "F" else "#4aa0ff", lw=w * ppm,
            solid_capstyle="round", alpha=.85)
for v in d["vias"]:
    ax.add_patch(Circle((v[0], v[1]), (v[3] if len(v) > 3 else B.VIA_D) / 2, fc="#ccc"))
for p in pads:
    col = "#d4af37" if p.net else "#777"
    if p.net in d["failed"]:
        col = "#ff00ff"
    if p.shape == "rect":
        ax.add_patch(Rectangle((p.x - p.w / 2, p.y - p.h / 2), p.w, p.h, fc=col, alpha=.8))
    elif p.shape == "circle":
        ax.add_patch(Circle((p.x, p.y), p.w / 2, fc=col, alpha=.8))
    else:
        a, b, c, e, r = p.capsule()
        ax.plot([a, c], [b, e], color=col, lw=2 * r * ppm, solid_capstyle="round", alpha=.8)
plt.savefig("debug.png", bbox_inches="tight")
