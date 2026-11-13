"""Schematic of the rev 1 board, drawn from the netlist in board.py -> avionics-panel-rev1-schematic.pdf.

The board has no hand-drawn schematic: board.py places the pads and gives every pad its net, and the
router and the checks work from that. This script draws the same netlist as four A3 sheets. Every net on
the drawing is looked up from a pad, nothing is typed in twice, and the script checks at the end that
every pad of the netlist shows up exactly with its net (pins without a net get a no-connect cross).
Skipped as duplicates: the RP2040's fan-out and via pads (U1.F*, U1.V*; the two SWD
pads U1.F24 / U1.F25 are drawn as test points) and the vias the USB lines land on (R_DP.E, R_DM.E). Skipped as no
part's pins: the fiducials (FID.*).
Pin names come from the datasheets (RP2040 table 2, W25Q16JV, XC6206, USB-C, SRV05-4, PEC11D, RKJXT).
"""
import math
import re

import matplotlib

matplotlib.use("Agg")
import board as B
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Polygon, Rectangle, Wedge


def netlist(pads):
    """(ref, pin) -> net for every pad of the board"""
    out = {}
    for p in pads:
        ref, _, pin = p.name.partition(".")
        out[(ref, pin)] = p.net
    return out


PADS = B.build()
NET = netlist(PADS)
PART = {r: (v, lcsc) for r, v, lcsc, *_ in B.PARTS}
REFS = sorted({r for r, _ in NET})
POWER = {"GND", "3V3", "1V1", "VBUS", "VBUS_F"}
SHOWN = set()                       # (ref, pin, net) of every pin on the drawing
PAPER = (420.0, 297.0)              # A3 landscape, mm
ZOOM = 1.4                          # one drawing unit is 1.4 mm on paper: all coordinates below are in units
W, H = PAPER[0] / ZOOM, PAPER[1] / ZOOM
WIRE, INK, PIN_C = "#1f4e8c", "#1b1b1b", "#7a1f1f"
SHEETS = ("USB-C and power", "RP2040, flash, crystal", "Key matrix", "Knobs and lights")

# Pin names typed from the datasheets (the netlist only knows numbers): RP2040 datasheet section 1.4.3 and
# figure 3 (pinout, QFN-56), Winbond W25Q16JV datasheet section 3.1 (SOIC-8 208 mil / 150 mil pin names),
# USB Type-C specification release 2.x table 3-4 (receptacle pin assignments).
RP2040_PINS = {1: "IOVDD", 10: "IOVDD", 19: "TESTEN", 20: "XIN", 21: "XOUT", 22: "IOVDD", 23: "DVDD",
               24: "SWCLK", 25: "SWD", 26: "RUN", 33: "IOVDD", 42: "IOVDD", 43: "ADC_AVDD", 44: "VREG_VIN",
               45: "VREG_VOUT", 46: "USB_DM", 47: "USB_DP", 48: "USB_VDD", 49: "IOVDD", 50: "DVDD",
               51: "QSPI_SD3", 52: "QSPI_SCLK", 53: "QSPI_SD0", 54: "QSPI_SD2", 55: "QSPI_SD1", 56: "QSPI_SS"}
GPIO_PIN = dict(zip(range(30), [*range(2, 10), *range(11, 19), *range(27, 33), *range(34, 42)], strict=True))
for _g, _n in GPIO_PIN.items():
    RP2040_PINS[_n] = f"GPIO{_g}" + (f"/ADC{_g - 26}" if _g >= 26 else "")
FLASH_PINS = {"1": "/CS", "2": "DO (IO1)", "3": "/WP (IO2)", "4": "GND", "5": "DI (IO0)", "6": "CLK",
              "7": "/HOLD (IO3)", "8": "VCC"}
USBC_PINS = {"A4B9": "VBUS", "B4A9": "VBUS", "A6": "D+", "B6": "D+", "A7": "D-", "B7": "D-", "A5": "CC1",
             "B5": "CC2", "A8": "SBU1", "B8": "SBU2", "A1B12": "GND", "B1A12": "GND"}


def spare_gpios():
    """GPIO nets that reach only the RP2040 (its pin and fan-out pad): the unused pins"""
    refs = {}
    for (ref, _pin), n in NET.items():
        if n:
            refs.setdefault(n, set()).add(ref)
    return sorted((n for n, r in refs.items() if n.startswith("GP") and r == {"U1"}), key=lambda n: int(n[2:]))


def skipped(ref, pin):
    return (ref == "FID"                                    # the fiducials: copper dots, no part and no net
            or (ref in ("R_DP", "R_DM") and pin == "E")      # where the USB lines land
            or (ref == "U1" and re.fullmatch(r"[FV]\d+", pin) is not None and pin not in ("F24", "F25")))


def pins_of(ref):
    return [pin for r, pin in NET if r == ref and not skipped(r, pin)]


def net(ref, pin):
    return NET[(ref, pin)]


DIRS = {"l": (-1, 0), "r": (1, 0), "u": (0, 1), "d": (0, -1)}


class Sheet:
    def __init__(self, pdf, n):
        self.pdf, self.n = pdf, n
        self.fig = plt.figure(figsize=(PAPER[0] / 25.4, PAPER[1] / 25.4))
        ax = self.ax = self.fig.add_axes((0, 0, 1, 1))
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.axis("off")
        ax.add_patch(Rectangle((4, 4), W - 8, H - 8, fill=False, lw=0.8, ec=INK))
        x0, y0 = W - 104, 4
        ax.add_patch(Rectangle((x0, y0), 100, 21, fill=False, lw=0.8, ec=INK))
        for y in (y0 + 7, y0 + 14):
            self.line((x0, y), (x0 + 100, y), wire=False)
        self.text(x0 + 2, y0 + 17.5, "Avionics Panel rev 1, schematic", 10, weight="bold")
        self.text(x0 + 2, y0 + 10.5, f"Sheet {n} of {len(SHEETS)}: {SHEETS[n - 1]}", 9)
        self.text(x0 + 2, y0 + 3.5, "Drawn from the netlist of pcb/board.py (make_schematic.py)", 7)

    # ---- primitives ----
    def line(self, *pts, wire=True, lw=None, ls="-"):
        xs, ys = zip(*pts, strict=True)
        self.ax.plot(xs, ys, color=WIRE if wire else INK, lw=lw or (0.9 if wire else 0.8), ls=ls,
                     solid_capstyle="round")

    def text(self, x, y, s, size=6.0, ha="left", va="center", rot=0, weight="normal", color=INK, box=None):
        self.ax.text(x, y, s, fontsize=size, ha=ha, va=va, rotation=rot, weight=weight, color=color,
                     bbox=box, family="DejaVu Sans")

    def dot(self, x, y):
        self.ax.add_patch(Circle((x, y), 0.55, color=WIRE, zorder=3))

    def wire(self, pts, pins=(), check=None):
        """a drawn connection; all pins on it (and `check`, a pin standing for the net) share one net"""
        nets = {net(*p) for p in pins} | ({net(*check)} if check else set())
        if len(nets) != 1:
            raise ValueError(f"a wire joins pins of several nets: {pins} {nets}")
        for p in pins:
            SHOWN.add((*p, net(*p)))
        self.line(*pts)

    def label(self, x, y, name, d, stub=3.0):
        """net label or power symbol for net `name` at the end of a stub leaving (x, y) towards d"""
        dx, dy = DIRS[d]
        ex, ey = x + dx * stub, y + dy * stub
        if stub:
            self.line((x, y), (ex, ey))
        if name == "GND":                                 # the bars face away from the pin
            if d == "u":
                self.line((ex, ey), (ex, ey + 1.5)); ey += 1.5
                dx, dy = 0, -1
            for k, w in enumerate((3.0, 2.0, 1.0)):
                cx, cy = ex + dx * k * 0.7, ey + dy * k * 0.7
                self.line((cx - dy * w / 2, cy - dx * w / 2), (cx + dy * w / 2, cy + dx * w / 2), wire=False, lw=1.0)
        elif name in POWER:                               # rails: bar across the stub, name beyond it
            if d in "ud":
                self.line((ex - 1.8, ey), (ex + 1.8, ey), wire=False, lw=1.1)
                self.text(ex, ey + 1.0 * dy, name, 7, ha="center", va="bottom" if dy > 0 else "top",
                          weight="bold")
            else:
                self.line((ex, ey - 1.8), (ex, ey + 1.8), wire=False, lw=1.1)
                self.text(ex + 1.0 * dx, ey, name, 7, ha="left" if dx > 0 else "right", weight="bold")
        else:
            box = dict(boxstyle="square,pad=0.18", fc="#eef3fa", ec=WIRE, lw=0.5)
            if d in "lr":
                self.text(ex + 0.6 * dx, ey, name, 6.8, ha="left" if dx > 0 else "right", box=box)
            else:
                self.text(ex, ey + 0.6 * dy, name, 6.8, ha="center", va="bottom" if dy > 0 else "top", rot=90,
                          box=box)

    def end(self, x, y, ref, pin, d, stub=3.0, pads=None):
        """terminates a pin: net label, power symbol or no-connect cross; records the pin(s)"""
        group = pads or [pin]
        nets = {net(ref, p) for p in group}
        if len(nets) != 1:
            raise ValueError(f"{ref}: pins {group} drawn as one are on several nets {nets}")
        n = nets.pop()
        for p in group:
            SHOWN.add((ref, p, n))
        if n is None:
            self.line((x - 1, y - 1), (x + 1, y + 1), wire=False, lw=1.0)
            self.line((x - 1, y + 1), (x + 1, y - 1), wire=False, lw=1.0)
        else:
            self.label(x, y, n, d, stub)

    # ---- symbols ----
    def ic(self, ref, x0, top, w, left=(), right=(), bottom=(), pitch=3.3, wired=(), title=None, names=None):
        """box with pins; entries are (pin or [pads], name) or None for a gap. Returns pin -> end point."""
        rows = max(len(left), len(right))
        h = pitch * (rows + 1)
        self.ax.add_patch(Rectangle((x0, top - h), w, h, fill=True, fc="#fbf7ef", ec=INK, lw=0.9))
        self.text(x0, top + 1.5, ref, 8.5, weight="bold")
        value, lcsc = PART.get(ref, ("", ""))
        self.text(x0, top - h - 1.5, title or f"{value} ({lcsc})", 6.8, va="top")
        pos = {}

        def pin_line(entry, px, py, dx, dy, ha):
            pads = entry[0] if isinstance(entry[0], list) else [entry[0]]
            key = entry[0] if isinstance(entry[0], str) else entry[2]
            ex, ey = px + 5 * dx, py + 5 * dy
            self.line((px, py), (ex, ey), wire=False)
            num = ",".join(re.sub(r"([AB]\d+)(?=[AB])", r"\1,", p) for p in pads) if len(entry) < 3 else entry[2]
            if dx:
                self.text(px + 2.5 * dx, py + 0.5, num, 5.2, ha="center", va="bottom", color=PIN_C)
                self.text(px - 1.0 * dx, py, entry[1], 6.2, ha=ha)
            else:
                self.text(px + 0.6, py + 2.5 * dy, num, 5.2, va="center", color=PIN_C)
                self.text(px, py - 1.0 * dy, entry[1], 6.2, ha="center", va="bottom", rot=90)
            pos[key] = (ex, ey)
            if key not in wired:
                self.end(ex, ey, ref, pads[0], "l" if dx < 0 else "r" if dx > 0 else "d", pads=pads)

        for i, e in enumerate(left):
            if e:
                pin_line(e, x0, top - pitch * (i + 1), -1, 0, "left")
        for i, e in enumerate(right):
            if e:
                pin_line(e, x0 + w, top - pitch * (i + 1), 1, 0, "right")
        for i, e in enumerate(bottom):
            if e:
                pin_line(e, x0 + w / 2 + pitch * (i - (len(bottom) - 1) / 2), top - h, 0, -1, "center")
        return pos

    def two(self, ref, x, y, d, pins=("1", "2"), length=10.0, text_side=1, show_lcsc=True):
        """two-pin part from (x, y) towards d: pins[0] at the start. Returns pin -> end point."""
        dx, dy = DIRS[d]
        a, b = (x, y), (x + dx * length, y + dy * length)
        mx, my = x + dx * length / 2, y + dy * length / 2
        kind = "LED" if ref.startswith("LED") else "JP" if ref.startswith("JP") else ref[0]
        px, py = -dy, dx                                     # perpendicular

        def pt(t, s):                                        # along / across the part, from its middle
            return mx + dx * t + px * s, my + dy * t + py * s

        if kind == "R":
            self.line(a, pt(-2.5, 0), wire=False); self.line(pt(2.5, 0), b, wire=False)
            self.ax.add_patch(Polygon([pt(-2.5, -0.9), pt(2.5, -0.9), pt(2.5, 0.9), pt(-2.5, 0.9)], closed=True,
                                      fill=False, ec=INK, lw=0.9))
        elif kind == "C":
            self.line(a, pt(-0.5, 0), wire=False); self.line(pt(0.5, 0), b, wire=False)
            for t in (-0.5, 0.5):
                self.line(pt(t, -1.8), pt(t, 1.8), wire=False, lw=1.2)
        elif kind in ("D", "LED"):                           # anode = pins[0] side, arrow towards the cathode
            self.line(a, pt(-1.5, 0), wire=False); self.line(pt(1.5, 0), b, wire=False)
            self.ax.add_patch(Polygon([pt(-1.5, -1.5), pt(-1.5, 1.5), pt(1.5, 0)], closed=True, fill=True,
                                      fc="white", ec=INK, lw=0.9))
            self.line(pt(1.5, -1.5), pt(1.5, 1.5), wire=False, lw=1.0)
            if kind == "LED":
                for t in (-0.6, 0.6):
                    self.ax.annotate("", xy=pt(t + 1.2, 3.6), xytext=pt(t, 2.0),
                                     arrowprops=dict(arrowstyle="-|>", lw=0.6, color=INK, mutation_scale=5))
        elif kind == "F":                                     # fuse: a box with the wire running through it
            self.line(a, b, wire=False)
            self.ax.add_patch(Polygon([pt(-2.5, -0.9), pt(2.5, -0.9), pt(2.5, 0.9), pt(-2.5, 0.9)], closed=True,
                                      fill=False, ec=INK, lw=0.9))
        elif kind == "JP":                                    # solder jumper, open: two half-round pads
            self.line(a, pt(-1.8, 0), wire=False); self.line(pt(1.8, 0), b, wire=False)
            ang = math.degrees(math.atan2(dy, dx))
            self.ax.add_patch(Wedge(pt(-0.4, 0), 1.4, ang + 90, ang + 270, fc=INK, ec=INK, lw=0.6))
            self.ax.add_patch(Wedge(pt(0.4, 0), 1.4, ang - 90, ang + 90, fc=INK, ec=INK, lw=0.6))
        value, lcsc = PART.get(ref, ("", ""))
        val = value + (f" {lcsc}" if show_lcsc else "")
        if d in "ud":
            tx = mx + 2.6 * text_side
            ha = "left" if text_side > 0 else "right"
            self.text(tx, my + 1.2, ref, 6.6, ha=ha, weight="bold")
            self.text(tx, my - 1.2, val, 5.8, ha=ha)
        elif text_side > 0:
            self.text(mx, my + 4.6, ref, 6.6, ha="center", va="bottom", weight="bold")
            self.text(mx, my + 2.0, val, 5.8, ha="center", va="bottom")
        else:
            self.text(mx, my - 2.0, ref, 6.6, ha="center", va="top", weight="bold")
            self.text(mx, my - 4.6, val, 5.8, ha="center", va="top")
        return {pins[0]: a, pins[1]: b}

    def switch(self, x, y, h=9.0):
        """push switch drawn downwards from (x, y): terminals at the top and at the bottom (returned)"""
        y1, y2 = y - 2.5, y - h + 2.5
        self.line((x, y), (x, y1), wire=False); self.line((x, y2), (x, y - h), wire=False)
        for yy in (y1, y2):
            self.ax.add_patch(Circle((x, yy), 0.45, fill=False, ec=INK, lw=0.8))
        self.line((x + 1.6, y1 + 0.6), (x + 1.6, y2 - 0.6), wire=False, lw=1.0)       # contact bar
        self.line((x + 1.6, (y1 + y2) / 2), (x + 3.4, (y1 + y2) / 2), wire=False)      # plunger
        self.line((x + 3.4, (y1 + y2) / 2 - 1.0), (x + 3.4, (y1 + y2) / 2 + 1.0), wire=False)
        return (x, y - h)

    def note(self, x, y, lines, size=7.0):
        for i, s in enumerate(lines):
            self.text(x, y - i * 3.6, s, size, va="top")

    def heading(self, x, y, s):
        self.text(x, y, s, 8.5, weight="bold")

    def save(self):
        self.pdf.savefig(self.fig)
        plt.close(self.fig)


# ---------------- sheet 1: USB-C and power ----------------
def sheet_power(s):
    order = ["A4B9", "B4A9", "A6", "B6", "A7", "B7", "A5", "B5", "A8", "B8", "A1B12", "B1A12"]
    shell = sorted(p for p in pins_of("J1") if p.startswith("SH"))
    if set(order) | set(shell) != set(pins_of("J1")):
        raise ValueError(f"J1's pins are not the ones drawn: {pins_of('J1')}")
    right = [(p, USBC_PINS[p]) for p in order] + [(shell, "SHIELD", "SH")]
    s.heading(20, 200, "USB-C (device): 5.1k pull-downs on CC1 and CC2, the D+ and D- pairs joined on the board,"
              " so either plug orientation works")
    pos = s.ic("J1", 24, 186, 20, right=right, pitch=6.0, wired={"A6", "B6", "A7", "B7", "A5", "B5"},
               title=f"{PART['J1'][0]} USB-C receptacle ({PART['J1'][1]})")
    # the ESD array in line on both lines (in on pins 6 / 4, out on 1 / 3), its VCC clamp on VBUS_F, behind the fuse
    lines = ((("A6", "B6"), "R_DP"), (("A7", "B7"), "R_DM"))
    ins = [next(p for p in ("4", "6") if net("U4", p) == net("J1", pa)) for (pa, _pb), _r in lines]
    outs = [next(p for p in ("1", "3") if net("U4", p) == net("J1", pa)) for (pa, _pb), _r in lines]
    io = {"1": "I/O1", "3": "I/O2", "4": "I/O3", "6": "I/O4"}         # SRV05-4 datasheet pin names
    u4 = s.ic("U4", 90, 171, 18, left=[(ins[0], io[ins[0]]), ("5", "VCC"), (ins[1], io[ins[1]])],
              right=[(outs[0], io[outs[0]]), ("2", "GND"), (outs[1], io[outs[1]])], pitch=6.0,
              wired=set(ins + outs), title=f"{PART['U4'][0]} ESD array ({PART['U4'][1]})")
    for ((pa, pb), r), pi, po in zip(lines, ins, outs, strict=True):
        (xa, ya), (xb, yb) = pos[pa], pos[pb]
        ym = (ya + yb) / 2
        s.wire([(xa, ya), (56, ya), (56, yb), (xb, yb)], [("J1", pa), ("J1", pb)])
        s.wire([(56, ym), u4[pi]], [("U4", pi)], check=("J1", pa))
        s.dot(56, ym)
        s.text(57, ym + 0.6, net("J1", pa), 5.6, color=WIRE, va="bottom")
        rp = s.two(r, u4[po][0] + 5, u4[po][1], "r", pins=("2", "1"))
        s.wire([u4[po], rp["2"]], [("U4", po), (r, "2")])
        s.end(*rp["1"], r, "1", "r")
    r = s.two("R_IN", 84, 184, "r")                 # the damping resistor and the fuse, VBUS (J1) to VBUS_F
    s.end(*r["1"], "R_IN", "1", "l")
    f = s.two("F1", 102, 184, "r")
    s.wire([r["2"], f["1"]], [("R_IN", "2"), ("F1", "1")])
    s.end(*f["2"], "F1", "2", "r")
    for pin in ("A5", "B5"):
        x, y = pos[pin]
        r = next(r for r in REFS if r.startswith("R_CC") and net(r, "1") == net("J1", pin))
        rp = s.two(r, 66, y, "r", text_side=-1 if pin == "B5" else 1)
        s.wire([(x, y), rp["1"]], [("J1", pin), (r, "1")])
        s.text(57, y + 0.6, net("J1", pin), 5.6, color=WIRE, va="bottom")
        s.end(*rp["2"], r, "2", "r")

    s.heading(140, 192, "3.3 V regulator")         # below the USB-C heading, which runs past x 140
    s.ic("U3", 172, 182, 22, left=[("3", "VIN")], right=[("2", "VOUT")], bottom=[("1", "VSS")], pitch=7.0)
    for ref, x in (("C_IN", 148), ("C_OUT0", 228)):
        top = next(p for p in ("1", "2") if net(ref, p) != "GND")
        bot = "1" if top == "2" else "2"
        p = s.two(ref, x, 176, "d", pins=(top, bot))
        s.end(*p[top], ref, top, "u")
        s.end(*p[bot], ref, bot, "d")

    # rail decoupling, found in the netlist: every two-pin capacitor between a rail and GND
    s.heading(20, 90, "Decoupling, placed at the RP2040 and the flash; the 3V3 and GND inner planes connect them")
    caps = [r for r in REFS if r.startswith("C_") and r not in ("C_IN", "C_OUT0")
            and set(pins_of(r)) == {"1", "2"} and "GND" in (net(r, "1"), net(r, "2"))
            and {net(r, "1"), net(r, "2")} - {"GND"} <= {"3V3", "1V1"}]

    def rail(r):
        return net(r, "1") if net(r, "1") != "GND" else net(r, "2")

    for i, ref in enumerate(sorted(caps, key=lambda r: (rail(r) != "3V3", r))):
        top = "1" if net(ref, "1") != "GND" else "2"
        bot = "2" if top == "1" else "1"
        p = s.two(ref, 26 + i * 20, 74, "d", pins=(top, bot))
        s.end(*p[top], ref, top, "u")
        s.end(*p[bot], ref, bot, "d")
    s.note(20, 46, ["C_IO1, C_IO10, C_IO22, C_IO49: one at each IOVDD pin but 33 (C_IO49 also USB_VDD); C_D2 (1 uF):",
                    "IOVDD 42, ADC_AVDD and VREG_VIN. C_D1, C_D3, C_BULK: on the 3V3 plane, shared by IOVDD 33. C_FL:",
                    "flash VCC. C_1V0 to C_1V2: DVDD and VREG_VOUT (the RP2040's internal 1.1 V core regulator).",
                    "U4 takes D+ and D- through two channels each. R_IN (1 ohm) damps the hot-plug ringing on C_IN",
                    "and gives way first on a short on VBUS_F (U4's clamp included); F1 (0.5 A PTC) covers slow",
                    "overloads."])


# ---------------- sheet 2: RP2040, flash, crystal ----------------
def sheet_mcu(s):
    u1 = {p for p in pins_of("U1") if p.isdigit()}
    if u1 != {str(i) for i in range(1, 57)}:
        raise ValueError(f"U1's pins are not 1 to 56: {sorted(u1)}")
    by_name = {}
    for n, name in RP2040_PINS.items():
        by_name.setdefault(name, []).append(n)
    left_names = ["IOVDD", "DVDD", "VREG_VIN", "VREG_VOUT", "USB_VDD", "ADC_AVDD", None, "RUN", "TESTEN", None,
                  "XIN", "XOUT", None, "SWCLK", "SWD", None, "USB_DP", "USB_DM", None, "QSPI_SS", "QSPI_SCLK",
                  "QSPI_SD0", "QSPI_SD1", "QSPI_SD2", "QSPI_SD3"]
    left = []
    for name in left_names:
        left += [(str(n), name) for n in sorted(by_name[name])] if name else [None]
    left += [None, ("EP", "GND (pad)", "57")]
    right = [(str(GPIO_PIN[g]), RP2040_PINS[GPIO_PIN[g]]) for g in range(30)]
    if {e[0] for e in left + right if e} != u1 | {"EP"}:
        raise ValueError("the RP2040 symbol does not show every pin once")
    s.heading(20, 200, "RP2040, chip-down minimal design (Raspberry Pi, Hardware design with RP2040)")
    s.ic("U1", 62, 192, 34, left=left, right=right, pitch=3.6)

    s.heading(166, 200, "Flash and USB boot")
    s.ic("U2", 188, 190, 26, left=[(p, FLASH_PINS[p]) for p in "1234"],
         right=[(p, FLASH_PINS[p]) for p in "8765"], pitch=4.5,
         title=f"{PART['U2'][0]} 16 Mbit QSPI flash ({PART['U2'][1]})")
    rb = s.two("R_BOOT", 194, 150, "d")
    s.end(*rb["1"], "R_BOOT", "1", "u")
    jp = s.two("JP_BOOT", 194, 136, "d", show_lcsc=False)
    s.wire([rb["2"], jp["1"]], [("R_BOOT", "2"), ("JP_BOOT", "1")])
    s.text(193, 138, net("R_BOOT", "2"), 5.6, color=WIRE, ha="right")
    s.end(*jp["2"], "JP_BOOT", "2", "d")
    s.note(212, 146, ["JP_BOOT: bridge pads under a hole in the", "body floor. Bridged while plugging in USB,",
                      "chip select low starts the USB bootloader."])

    s.heading(166, 120, "12 MHz crystal")
    y, xa, xb = 104, 186, 202                     # Y1.3 (XIN side) and Y1.1 (XOUT side) terminals
    for xx in (192.5, 195.5):
        s.line((xx, y - 2.2), (xx, y + 2.2), wire=False, lw=1.1)
    s.ax.add_patch(Rectangle((193.2, y - 1.6), 1.6, 3.2, fill=False, ec=INK, lw=0.9))
    s.line((xa, y), (192.5, y), wire=False); s.line((195.5, y), (xb, y), wire=False)
    s.ax.add_patch(Rectangle((190, y - 4.5), 8, 9, fill=False, ec=INK, lw=0.6, ls="--"))
    s.text(190, y + 9.5, "Y1", 8.5, weight="bold")
    s.text(176, y + 6.0, f"{PART['Y1'][0]} ({PART['Y1'][1]})", 6.2)
    for pin, xx in (("2", 192.5), ("4", 195.5)):
        s.line((xx, y - 4.5), (xx, y - 7), wire=False)
        s.text(xx + 0.4, y - 5.8, pin, 5.2, color=PIN_C)
        s.end(xx, y - 7, "Y1", pin, "d", stub=1.0)
    s.text(xa + 0.4, y + 0.6, "3", 5.2, color=PIN_C, va="bottom")
    s.text(xb - 1.6, y + 0.6, "1", 5.2, color=PIN_C, va="bottom")
    def load_cap(n):
        """the load capacitor on net n: (ref, its pin on n, its GND pin)"""
        ref = next(r for r in ("C_X1", "C_X2") if n in (net(r, "1"), net(r, "2")))
        return (ref, "1", "2") if net(ref, "1") == n else (ref, "2", "1")
    cx1, p1, g1 = load_cap(net("Y1", "3"))
    cx2, p2, g2 = load_cap(net("Y1", "1"))
    s.wire([(xa, y), (178, y)], [("Y1", "3")])
    c = s.two(cx1, 178, y, "d", pins=(p1, g1), text_side=-1)
    s.wire([(178, y), c[p1]], [(cx1, p1)], check=("Y1", "3")); s.dot(178, y)
    s.end(*c[g1], cx1, g1, "d")
    s.wire([(178, y), (172, y)], [], check=("Y1", "3"))
    s.label(172, y, net("Y1", "3"), "l", stub=0)
    c = s.two(cx2, 210, y, "d", pins=(p2, g2))
    s.wire([(xb, y), (210, y)], [("Y1", "1"), (cx2, p2)]); s.dot(210, y)
    s.end(*c[g2], cx2, g2, "d")
    r = s.two("R_X", 210, y, "r", pins=("1", "2"))
    s.wire([(210, y), r["1"]], [("R_X", "1")], check=("Y1", "1"))
    s.text(203, y + 0.6, net("Y1", "1"), 5.6, color=WIRE, va="bottom")
    s.end(*r["2"], "R_X", "2", "r")

    s.heading(166, 74, "SWD debug pads (exposed copper, bottom side)")
    for i, pin in enumerate(("F24", "F25")):
        x, yy = 196, 66 - i * 7
        s.ax.add_patch(Circle((x, yy), 1.0, fill=False, ec=INK, lw=0.9))
        s.end(x - 1.0, yy, "U1", pin, "l", stub=5)
        s.text(x + 2.5, yy, f"U1.{pin}", 6.8, weight="bold")
    s.note(166, 48, [
        f"RUN (pin 26) is tied to {net('U1', '26')}: the probe resets over SWD.",
        f"TESTEN (pin 19) goes to {net('U1', '19')} at the exposed pad.",
        *(f"GPIO{n[2:]} ({n}) is the spare: a fan-out pad, no load." for n in spare_gpios()),
        "GND for an SWD probe: the USB-C shell.",
    ])


# ---------------- sheet 3: key matrix ----------------
def sheet_matrix(s):
    rows, cols = B.ROW_GP, B.COL_GP
    cells = []                                           # (row, col, switch ref, row pins, key pin, nc pins, diode)
    for d in REFS:
        if set(pins_of(d)) != {"A", "K"} or net(d, "A") not in cols:
            continue
        kn = net(d, "K")
        (sref, kpin), = [(r, p) for (r, p), nn in NET.items() if nn == kn and r != d and not skipped(r, p)]
        rpins = [p for p in pins_of(sref) if net(sref, p) in rows]
        rnets = {net(sref, p) for p in rpins}
        if len(rnets) != 1:
            raise ValueError(f"{sref}: row pins {rpins} are on several nets {rnets}")
        nc = [p for p in pins_of(sref) if net(sref, p) is None] if sref.startswith("K") else []
        cells.append((rows.index(rnets.pop()), cols.index(net(d, "A")), sref, rpins, kpin, nc, d))
    if len({(r, c) for r, c, *_ in cells}) != len(cells):
        raise ValueError("two switches on one crosspoint")
    x0, pitch_x, y0, pitch_y = 68, 34, 180, 30
    xl, xr = 24, x0 + pitch_x * (len(cols) - 1) + 6
    yb = y0 - pitch_y * (len(rows) - 1) - 20
    s.heading(20, 200, "Key matrix: rows driven, columns read through the diodes "
                       "(anodes on the columns: keypad.KeyMatrix(columns_to_anodes=True)), columns pulled up")
    for r, rn in enumerate(rows):
        y = y0 - pitch_y * r
        s.line((xl, y), (xr, y))
        s.label(xl, y, rn, "l", stub=0)
        s.text(xl + 1, y + 0.8, f"row {r}", 5.8, va="bottom", color=WIRE)
    pullups = []
    for c, cn in enumerate(cols):
        x = x0 + pitch_x * c
        s.line((x, y0 + 10), (x, yb))
        s.label(x, y0 + 10, cn, "u", stub=0)
        s.text(x + 1.0, y0 + 6, f"col {c}", 5.8, color=WIRE)
        pu, = [r for r in REFS if r.startswith("R_PU") and net(r, "1") == cn]   # pull-up to 3V3, pin 1 on the column
        pullups.append(pu)
        p = s.two(pu, x, yb, "d", pins=("1", "2"), length=8, show_lcsc=False)
        s.wire([(x, yb), p["1"]], [(pu, "1")])
        s.end(*p["2"], pu, "2", "d", stub=2.0)
    for r, c, sref, rpins, kpin, nc, d in cells:
        xc, y = x0 + pitch_x * c, y0 - pitch_y * r
        x = xc - 26
        s.dot(x, y)
        s.wire([(x, y), (x, y - 2)], [(sref, p) for p in rpins])
        bx, by = s.switch(x, y - 2, h=10)
        s.text(x - 0.8, y - 2.6, "+".join(rpins), 5.0, ha="right", color=PIN_C)
        s.text(x - 0.8, by + 0.6, kpin, 5.0, ha="right", color=PIN_C)
        for p in nc:                                     # the unused pin of the switch's second contact pair
            s.end(x - 4.0, by + 2.4, sref, p, "l", stub=0)
            s.text(x - 4.0, by + 3.6, p, 5.0, ha="center", color=PIN_C)
        dp = s.two(d, xc - 6, by - 4, "l", pins=("A", "K"), length=10, text_side=-1, show_lcsc=False)
        s.wire([(bx, by), (bx, by - 4), dp["K"]], [(sref, kpin), (d, "K")])
        s.wire([dp["A"], (xc, by - 4)], [(d, "A")], check=(d, "A"))
        s.dot(xc, by - 4)
        if re.fullmatch(r"K\d\d", sref):
            legend = B.KEY_LABELS[int(sref[1])][int(sref[2])]
        else:
            legend = f"{sref.replace('ENC_', '')} {kpin if sref == 'RANGE' else 'push'}"
        s.text(x + 4.5, y - 5.0, legend, 7.2, weight="bold")
        s.text(x + 4.5, y - 8.4, sref, 6.0)
    keys = [r for r in REFS if re.fullmatch(r"K\d\d", r)]
    diodes = [c[6] for c in cells]
    s.note(20, 25, [
        f"{len(keys)} keys {PART[keys[0]][0]} ({PART[keys[0]][1]}): A and B are one contact, C and D the other;",
        f"C is unused. {len(diodes)} diodes {PART[diodes[0]][0]} ({PART[diodes[0]][1]}), one per switch.",
        "Row 4: the RANGE tilt switches A to D and com (centre push = com alone, decoded in firmware),",
        "and the ALT/HDG and FMS knob pushes.",
        f"{PART[pullups[0]][0]} column pull-ups ({PART[pullups[0]][1]}): the RP2040's own (50 to 80k) are too slow.",
    ], size=6.6)


# ---------------- sheet 4: knobs and lights ----------------
def sheet_knobs(s):
    s.heading(20, 200, "Dual encoders, 30 detents / 15 pulses with push; the firmware reads ring 1 as the outer and "
                       "ring 2 as the inner knob")
    encs = sorted((r for r in REFS if r.startswith("ENC_")), key=lambda r: next(p[3:5] for p in B.PARTS if p[0] == r))
    for i, ref in enumerate(encs):
        if set(pins_of(ref)) != {"A", "B", "C", "A2", "B2", "C2", "D", "E", "MP-1", "MP1"}:
            raise ValueError(f"{ref}'s pins are not the ones drawn: {pins_of(ref)}")
        left = [("A", "A"), ("C", "C"), ("B", "B"), None, ("A2", "A'"), ("C2", "C'"), ("B2", "B'")]
        x0 = 36 + i * 92
        s.ic(ref, x0, 186, 30, left=left, right=[("D", "push"), ("E", "push"), None, (["MP-1", "MP1"], "lugs", "MP")],
             pitch=4.5,
             title=f"{PART[ref][0]} ({PART[ref][1]})")
        s.text(x0 + 15, 186 - 4.5 * 2, "ring 1", 6.2, ha="center", color=PIN_C)
        s.text(x0 + 15, 186 - 4.5 * 6, "ring 2", 6.2, ha="center", color=PIN_C)
        diode = [d for d, *_ in B.DIODES if NET.get((d, "K")) in (net(ref, "D"), net(ref, "E"))]
        how = (f"push: key matrix through {diode[0]} (sheet 3)" if diode else
               f"push: direct, {net(ref, 'E')} to {net(ref, 'D')}")
        s.text(x0, 186 - 4.5 * 8 - 9, how, 6.4, va="top")

    s.heading(20, 120, "RANGE: turn, 4-way tilt, push")
    pins = set(pins_of("RANGE"))
    enc = [("ENCA", "encoder A"), ("ECOM", "encoder com"), ("ENCB", "encoder B")]
    sw = [("PUSH", "switch common"), None, ("A", "tilt A"), ("B", "tilt B"), ("C", "tilt C"), ("D", "tilt D"),
          ("COM", "any tilt / push")]
    rest = sorted(pins - {e[0] for e in enc + sw if e})
    s.ic("RANGE", 46, 108, 34, left=enc + [None] + [(p, "frame") for p in rest], right=sw, pitch=4.5,
         title=f"{PART['RANGE'][0]} ({PART['RANGE'][1]})")
    s.note(20, 64, ["The tilt and push switches sit in key matrix row 4 (sheet 3)."])

    s.heading(170, 120, "Lights (light pipes in the front plate)")
    for i, led in enumerate(r for r in REFS if r.startswith("LED_")):
        y = 104 - i * 22
        res = next(r for r in REFS if r.startswith("R_") and net(r, "2") == net(led, "A"))
        rp = s.two(res, 192, y, "r")
        s.end(*rp["1"], res, "1", "l")
        lp = s.two(led, 212, y, "r", pins=("A", "K"), text_side=-1)
        s.wire([rp["2"], lp["A"]], [(res, "2"), (led, "A")])
        if net(led, "K") == "GND":
            s.end(*lp["K"], led, "K", "r")
            continue
        # switched on the low side: the FET's drain on the cathode, its gate on the GPIO with a pull-down
        q = next(r for r in REFS if r.startswith("Q_") and net(r, "3") == net(led, "K"))
        qp = s.ic(q, 236, y + 4.5, 12, left=[("3", "D")], right=[("2", "S"), ("1", "G")], pitch=4.5,
                  wired=("3", "1"))
        s.wire([lp["K"], qp["3"]], [(led, "K"), (q, "3")])
        gx, gy = qp["1"]
        pd = next(r for r in REFS if r.startswith("R_") and r.endswith("_PD") and net(r, "2") == net(q, "1"))
        pp = s.two(pd, gx + 6, gy, "d", pins=("2", "1"))
        s.wire([(gx, gy), pp["2"]], [(q, "1"), (pd, "2")])
        s.dot(*pp["2"])
        s.label(*pp["2"], net(q, "1"), "r", stub=6.0)
        s.end(*pp["1"], pd, "1", "d")
    # GP25's series resistor to the FREQ outer ring's B line (pcb/board.py add_gp25_resistor)
    rp = s.two("R_GP25", 250, 104, "r")
    s.end(*rp["1"], "R_GP25", "1", "l")
    s.end(*rp["2"], "R_GP25", "2", "r")
    s.note(236, 97, ["GP25 is CircuitPython's status LED on the Pico build:", "1k limits it into a closed contact."],
           size=6.0)


def main():
    with PdfPages("avionics-panel-rev1-schematic.pdf", metadata={"CreationDate": None}) as pdf:
        for n, draw in enumerate((sheet_power, sheet_mcu, sheet_matrix, sheet_knobs), start=1):
            s = Sheet(pdf, n)
            draw(s)
            s.save()
    want = {(r, p, n) for (r, p), n in NET.items() if not skipped(r, p)}
    missing, extra = want - SHOWN, SHOWN - want
    if missing or extra:
        raise SystemExit(f"schematic differs from the netlist: missing {sorted(missing)}, extra {sorted(extra)}")
    print(f"schematic: {len(SHEETS)} sheets, {len(want)} pins of {len({r for r, _, _ in want})} parts, "
          "all with their netlist nets")


if __name__ == "__main__":
    main()
