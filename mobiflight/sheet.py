"""The cheat sheet of a profile: one SVG with the panel drawn in the middle, to scale from the 3D view's geometry
(viewer/geometry.js) with the legends of mech/stack.py, and a box of plain words for each column of keys and each
knob, with a leader line to every control (docs/using/aircraft/). The words, written by hand, are in sheet_text.SHEETS;
"does nothing" where the profile maps nothing.

Keys: a box above the panel for each column's two upper keys and one below for its two lower keys. A box's lines run
in lanes between the boxes and the panel, ordered so no two lines cross. The outer row's line comes straight onto its
key (below the panel beside the amber legend under the key, which it would cross); the inner row's runs along the
gap beside its column and in from the side, the right side unless a light sits in that gap. Knobs: a box beside the
panel for each, its line to the knob's rim. The page is self-contained, and the same texts and geometry make the same
bytes. Sheet.boxes and Sheet.leads keep what was drawn, for tests/test_sheet.py.
"""
import html
import json
import math
import os
import re

from mobiflight import card, profile
from mobiflight.sheet_text import SHEETS, SHIFT

HERE = os.path.dirname(os.path.abspath(__file__))
GEOMETRY = os.path.join(HERE, "..", "viewer", "geometry.js")
OUT = os.path.join(HERE, "..", "docs", "using", "aircraft")

BM = profile.BM

# the knobs' rows: (id, title, shifted, buttons), the panel's left knobs first
KNOBS = {
    "ALTHDG": ("ALT / HDG", [
        ("ALT_KNOB", "outer", False, [*BM.turn("ALT_100"), *BM.turn("ALT_1000")]),
        ("HDG_KNOB", "inner", False, [*BM.turn("HDG_1"), *BM.turn("HDG_10")]),
        ("SYNC", "push", False, ["HDG_SYNC"]),
        ("BARO", "outer", True, BM.turn("BARO")),
        ("CRS", "inner", True, [*BM.turn("CRS_1"), *BM.turn("CRS_10")]),
        ("STD", "push", True, ["BARO_STD"])]),
    "RANGE": ("RANGE", [
        ("RANGE", "turn", False, ["RANGE_CW", "RANGE_CCW"]),
        ("PAN_UD", "tilt up/down", False, ["PAN_UP", "PAN_DN"]),
        ("PAN_LR", "tilt left/right", False, ["PAN_LEFT", "PAN_RIGHT"]),
        ("PTR", "push", False, ["PTR"]),
        ("S_RANGE", "turn", True, ["S_RANGE_CW", "S_RANGE_CCW"]),
        ("S_PAN_UD", "tilt up/down", True, ["S_PAN_UP", "S_PAN_DN"]),
        ("S_PAN_LR", "tilt left/right", True, ["S_PAN_LEFT", "S_PAN_RIGHT"]),
        ("S_PTR", "push", True, ["S_PTR"])]),
    "FREQ": ("FREQ", [
        ("FREQ_OUTER", "outer", False, [*BM.turn("COM_MHZ"), *BM.turn("NAV_MHZ"), *BM.turn("ADF_100")]),
        ("FREQ_INNER", "inner", False, [*BM.turn("COM_KHZ"), *BM.turn("NAV_KHZ"), *BM.turn("ADF_1"),
                                        *BM.turn("ADF_10")]),
        ("FREQ_PUSH", "push", False, []),
        ("SQUAWK", "rings", True, [b for d in (1, 2, 3, 4) for b in BM.turn(f"SQK_D{d}")]),
        ("XPDR", "push", True, ["XPDR_MODE"])]),
    "FMS": ("FMS", [
        ("FMS_OUTER", "outer", False, ["FMS_OUTER_CW", "FMS_OUTER_CCW"]),
        ("FMS_INNER", "inner", False, ["FMS_INNER_CW", "FMS_INNER_CCW"]),
        ("CRSR", "push", False, ["FMS_CRSR"]),
        ("PANEL", "outer", True, BM.turn("PANEL_LT")),
        ("FLOOD", "inner", True, BM.turn("FLOOD_LT")),
        ("CABIN", "push", True, ["CABIN_LT"])]),
}
# the panel's own: no button, or one whose meaning the firmware gives (the FREQ knob's mode)
PANEL_ONLY = {"FREQ_PUSH"}


def controls():
    """{id: buttons}: every key's button and shifted button (card.caps(): SHIFT and UNIT send none), every knob
    row"""
    out = {}
    for keyrow in card.caps():
        for _, _, plain, shifted in keyrow:
            out.update({name: [name] for name in (plain, shifted) if name})
    rows = {cid: buttons for _, knob_rows in KNOBS.values() for cid, _, _, buttons in knob_rows}
    assert not set(rows) & set(out), sorted(set(rows) & set(out))        # a knob row's id is no key's
    return {**out, **rows}


CONTROLS = controls()


def geometry():
    with open(GEOMETRY, encoding="utf-8") as f:
        text = f.read()
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


# ---------------- layout, in SVG units (px): A4 landscape, 297 mm wide ----------------
W, H = 1600, 1000
PAGE_MM = 297
S = 5.6                          # px per mm on the panel
OVH = 2.5                        # the plate's overhang round the board, mm
FONT = "Arial, 'Liberation Sans', Helvetica, sans-serif"
INK, MUTED, AMBER, LINE = "#16181b", "#7a7f87", "#a86f00", "#5b6b85"
TEXT_PX, LABEL_PX, LINE_H = 11.5, 12, 14
BOX_W, BOX_GAP, PAD = 128, 4, 6
SLACK = 8                        # px a line keeps free in its box, for a font wider than Arial
SIDE_W = 300
TITLE_BOTTOM = 70                # the title and the line under it end here
LANES = 72, 58                   # px between the key boxes and the panel: above it, below it
UNITS = re.compile(r"(\d) (s|%|ft|kHz|MHz)(?!\w)|\b(COM|NAV) (\d)")    # kept on one line: "5 %", "COM 2"


def width(text, px):
    """the rough width of a text in Arial at px"""
    w = 0.0
    for ch in text:
        w += (0.28 if ch in " \u00a0" else 0.67 if ch.isupper() else 0.56 if ch.isdigit() else
              0.3 if ch in ".,;:'!|()-/" else 0.5)
    return w * px


def wrap(text, px, room):
    """text in lines that fit room px wide; a number keeps its unit ("1 s", "5 %") and a radio its number"""
    lines, line = [], ""
    for word in UNITS.sub(lambda m: "\u00a0".join(g for g in m.groups() if g), text).split(" "):
        trial = f"{line} {word}".strip()
        if line and width(trial, px) > room:
            lines.append(line)
            line = word
        else:
            line = trial
    return [*lines, line]


def crosses(a, b):
    """whether two polylines of horizontal and vertical segments cross: a vertical one through a horizontal one"""
    def segments(points):
        return list(zip(points, points[1:], strict=False))
    for p, q in segments(a):
        for r, s in segments(b):
            for (v0, v1), (h0, h1) in (((p, q), (r, s)), ((r, s), (p, q))):
                if v0[0] == v1[0] and h0[1] == h1[1] and v0[1] != v1[1] and h0[0] != h1[0]:
                    x, y = v0[0], h0[1]
                    if (min(h0[0], h1[0]) < x < max(h0[0], h1[0])
                            and min(v0[1], v1[1]) < y < max(v0[1], v1[1])):
                        return True
    return False


class Sheet:
    def __init__(self, key):
        self.key = key
        self.texts, self.unit2 = SHEETS[key]
        self.g = geometry()
        self.out, self.boxes, self.leads = [], [], []
        plate_w, plate_h = (self.g["board"]["w"] + 2 * OVH) * S, (self.g["board"]["h"] + 2 * OVH) * S
        self.x0, self.y0 = (W - plate_w) / 2, (H - plate_h) / 2 + 10
        self.plate = (plate_w, plate_h)

    def P(self, x, y):
        """a board point (mm, y down) on the page"""
        return self.x0 + (x + OVH) * S, self.y0 + (y + OVH) * S

    def text(self, x, y, s, px=TEXT_PX, fill=INK, weight="normal", anchor="start"):
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{px}" font-weight="{weight}" fill="{fill}" '
                        f'text-anchor="{anchor}">{html.escape(s)}</text>')

    def entries(self, entries, room):
        """[(label, shifted, text or None)] as lines: [(text, fill, weight)]"""
        lines = []
        for label, shifted, text in entries:
            lines.append((("⇧ " if shifted else "") + label, AMBER if shifted else INK, "bold"))
            if text is None:
                lines.append(("does nothing", MUTED, "normal"))
            else:
                lines += [(line, INK, "normal") for line in wrap(text, TEXT_PX, room - SLACK)]
        return lines

    def box(self, x, y, w, lines, grow_up=False):
        """a box of lines at x, its top at y (its bottom, growing up); its (top, bottom)"""
        h = len(lines) * LINE_H + 2 * PAD - 2
        top = y - h if grow_up else y
        self.boxes.append((x, top, w, h))
        self.out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{w}" height="{h}" rx="6" fill="#ffffff" '
                        f'stroke="#c3c8cf"/>')
        for i, (s, fill, weight) in enumerate(lines):
            self.text(x + PAD, top + PAD + 10 + i * LINE_H, s, LABEL_PX if weight == "bold" else TEXT_PX, fill,
                      weight)
        return top, top + h

    def lead(self, points):
        self.leads.append(points)
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        self.out.append(f'<polyline points="{d}" fill="none" stroke="{LINE}" stroke-width="1.3"/>')
        x, y = points[-1]
        self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{LINE}"/>')

    # ---------------- the panel ----------------
    def panel(self):
        g, (pw, ph) = self.g, self.plate
        self.out.append(f'<rect x="{self.x0:.1f}" y="{self.y0:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
                        f'rx="{(g["board"]["corner_r"] + OVH) * S:.1f}" fill="#2d2f33"/>')
        cw, ch = (v * S for v in g["keys"]["cap"][:2])
        for r, row in enumerate(card.caps()):
            for c, (legend, amber, _, _) in enumerate(row):
                x, y = self.P(g["keys"]["cols"][c], g["keys"]["rows"][r])
                self.out.append(f'<rect x="{x - cw / 2:.1f}" y="{y - ch / 2:.1f}" width="{cw:.1f}" height="{ch:.1f}" '
                                'rx="4" fill="#111214" stroke="#000"/>')
                self.text(x, y + 4.5, legend, 12.5, "#f2a900" if legend == "SHIFT" else "#ffffff", "bold", "middle")
                if amber:
                    self.text(x, y + ch / 2 + 11, amber, 9, "#f2a900", "bold", "middle")
        for name, light in g["lights"].items():
            x, y = self.P(light["x"], light["y"])
            colour = {"SHIFT": "#f2a900", "UNIT": "#ffffff", "FREQ": "#7cd33c"}[name]
            self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{light["d"] / 2 * S:.1f}" fill="{colour}" '
                            'fill-opacity="0.85"/>')
        for name, knob in g["knobs"].items():
            x, y = self.P(knob["x"], knob["y"])
            if name == "RANGE":
                rk = g["range_knob"]
                self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rk["skirt_d"] / 2 * S:.1f}" fill="#1c1d20"/>')
                self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rk["d"] / 2 * S:.1f}" fill="#27282c" '
                                'stroke="#000"/>')
                # the pan arrows as triangles, not glyphs: ▲▼◀▶ have emoji forms that viewers may pick
                arm = (rk["skirt_d"] / 2 + 3) * S
                for ux, uy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    tip, base, half = arm + 5, arm - 3, 4.5
                    pts = [(ux * tip, uy * tip), (ux * base - uy * half, uy * base + ux * half),
                           (ux * base + uy * half, uy * base - ux * half)]
                    d = " ".join(f"{x + px:.1f},{y + py:.1f}" for px, py in pts)
                    self.out.append(f'<polygon points="{d}" fill="#d8dadd"/>')
            else:
                for part, fill in (("outer_knob", "#1c1d20"), ("inner_knob", "#27282c")):
                    self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{g[part]["d"] / 2 * S:.1f}" '
                                    f'fill="{fill}" stroke="#000"/>')
            self.text(x, y + 4, KNOBS[name][0], 11, "#ffffff", "bold", "middle")

    # ---------------- the callouts ----------------
    def light_in_gap(self, gx, y0, y1):
        """whether a light lies on the vertical from y0 to y1 at gx"""
        for light in self.g["lights"].values():
            lx, ly = self.P(light["x"], light["y"])
            if abs(lx - gx) < light["d"] / 2 * S + 3 and min(y0, y1) < ly < max(y0, y1):
                return True
        return False

    def key_lines(self, band, starts, depth, anchor_y, step):
        """{(column, which): polyline} of a band, with these lane depths"""
        g, cols = self.g, self.g["keys"]["cols"]
        cw, ch = (v * S for v in g["keys"]["cap"][:2])
        outer, inner = (0, 1) if band == "top" else (3, 2)
        edge, sign = (self.y0, 1) if band == "top" else (self.y0 + self.plate[1], -1)
        out = {}
        for c, bx, kx in starts:
            _, ky_in = self.P(cols[c], g["keys"]["rows"][inner])
            # the inner line along the gap right of its column, or left of it where a light sits in that gap
            gx = kx + (self.P(cols[c + 1], 0)[0] - kx) / 2 if c + 1 < len(cols) else kx + cw / 2 + 6
            side = 1
            if self.light_in_gap(gx, edge, ky_in):
                gx, side = kx - cw / 2 - 7, -1
            # the line on the side its key is reached from leaves the box on that side
            for which, r, dx in (("outer", outer, -10 * side), ("inner", inner, 10 * side)):
                lane = edge - sign * (8 + step * depth[(c, which)])
                _, ky = self.P(cols[c], g["keys"]["rows"][r])
                start = [(bx + dx, anchor_y[c]), (bx + dx, lane)]
                if which == "outer":
                    # below the panel the amber legend sits under the key: come in beside it
                    ex = kx if band == "top" else kx - cw / 2 + 4
                    out[(c, which)] = [*start, (ex, lane), (ex, ky - sign * ch / 2)]
                else:
                    out[(c, which)] = [*start, (gx, lane), (gx, ky), (kx + side * cw / 2, ky)]
        return out

    def key_boxes(self):
        caps, cols = card.caps(), self.g["keys"]["cols"]
        n = len(cols)
        bx0 = (W - n * BOX_W - (n - 1) * BOX_GAP) / 2
        for band, (outer, inner) in (("top", (0, 1)), ("bottom", (3, 2))):
            starts = [(c, bx0 + c * (BOX_W + BOX_GAP) + BOX_W / 2, self.P(cols[c], 0)[0]) for c in range(n)]
            # lanes: the lines that travel furthest nearest the panel, each side of the middle on its own
            depth = {}
            for side in ([s for s in starts if s[1] < s[2]], [s for s in starts if s[1] >= s[2]]):
                for level, (c, bx, kx) in enumerate(sorted(side, key=lambda s: -abs(s[1] - s[2]))):
                    first, second = ("outer", "inner") if bx < kx else ("inner", "outer")
                    depth[(c, first)], depth[(c, second)] = 2 * level, 2 * level + 1
            room = LANES[band != "top"]
            limit = self.y0 - room if band == "top" else self.y0 + self.plate[1] + room
            step = min(6.0, (room - 14) / max(1, max(depth.values())))
            anchor_y = {}
            for c, bx, _ in starts:
                entries = []
                for r in sorted((outer, inner)):                          # in the panel's order, top to bottom
                    legend, amber, plain, shifted = caps[r][c]
                    if plain is None:                                     # SHIFT
                        entries.append(("SHIFT", False, SHIFT))
                        continue
                    entries.append((legend, False, self.texts[plain]))
                    if shifted:
                        same = self.texts[shifted] == self.texts[plain] and self.texts[plain] is not None
                        entries.append((amber or legend, True, "the same" if same else self.texts[shifted]))
                    elif plain == "HOME":
                        entries.append(("UNIT", True, "unit 1 or 2 (white light); " + self.unit2))
                lines = self.entries(entries, BOX_W - 2 * PAD)
                top, bottom = self.box(bx - BOX_W / 2, limit, BOX_W, lines, grow_up=band == "top")
                anchor_y[c] = bottom if band == "top" else top
            # a column's two lines swap lanes where they would cross (an inner line coming in from the left)
            for _ in range(2 * n):
                leads = self.key_lines(band, starts, depth, anchor_y, step)
                pair = next(((a, b) for a in leads for b in leads if a < b and crosses(leads[a], leads[b])), None)
                if pair is None:
                    break
                (ca, _), (cb, _) = pair
                if ca != cb:
                    raise ValueError(f"{band}: the lines of columns {ca} and {cb} cross")
                depth[(ca, "outer")], depth[(ca, "inner")] = depth[(ca, "inner")], depth[(ca, "outer")]
            else:
                raise ValueError(f"{band}: no order of the lanes keeps the lines apart")
            for points in leads.values():
                self.lead(points)

    def knob_boxes(self):
        g = self.g
        sides = {"ALTHDG": ("left", "top"), "RANGE": ("left", "bottom"), "FREQ": ("right", "top"),
                 "FMS": ("right", "bottom")}
        for name, (side, half) in sides.items():
            title, rows = KNOBS[name]
            entries = [(f"{title}, {t}" if not s else t, s, self.texts[cid]) for cid, t, s, _ in rows]
            lines = self.entries(entries, SIDE_W - 2 * PAD)
            x = 14 if side == "left" else W - 14 - SIDE_W
            kx, ky = self.P(g["knobs"][name]["x"], g["knobs"][name]["y"])
            r = (g["range_knob"]["skirt_d"] if name == "RANGE" else g["outer_knob"]["d"]) / 2 * S
            # to the rim, up and out at 35°: clear of the RANGE knob's pan arrows, left, right, up and down
            dx, dy = r * math.cos(math.radians(35)), -r * math.sin(math.radians(35))
            tx, ty = (kx - dx if side == "left" else kx + dx), ky + dy
            h = len(lines) * LINE_H + 2 * PAD - 2
            top = max(TITLE_BOTTOM + 8, ty - h + 40) if half == "top" else min(H - 20 - h, ty - 40)
            self.box(x, top, SIDE_W, lines)
            self.lead([(x + SIDE_W if side == "left" else x, ty), (tx, ty)])

    def svg(self, title):
        self.out, self.boxes, self.leads = [], [], []
        self.panel()
        self.key_boxes()
        self.knob_boxes()
        self.text(W / 2, 40, title, 26, INK, "bold", "middle")
        self.text(W / 2, 62, "⇧ = after a tap on SHIFT (amber light).  Unit 2: SHIFT, HOME (white light).  "
                             '"does nothing": this profile sends nothing for it.', 12, MUTED, anchor="middle")
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_MM}mm" height="{PAGE_MM * H / W:g}mm" '
                f'viewBox="0 0 {W} {H}" font-family="{FONT}">\n<rect width="{W}" height="{H}" fill="#f6f7f9"/>\n'
                f'{body}\n</svg>\n')


def svg(key, title):
    """the cheat sheet of a profile (sheet_text.SHEETS[key]) as SVG"""
    return Sheet(key).svg(title)


TITLES = {
    "g1000": "G1000 NXi",
    "g3x": "GFC 500 and G3X Touch",
    "gns": "GNS 530/430 with the KAP 140",
    "gtn": "TDS GTN 750Xi and 650Xi with the KAP 140",
    "black-square-bonanza": "Black Square Bonanza",
    "cows-da40": "COWS DA40",
    "carenado-c182t": "Carenado C182T",
}


def write(out_dir=OUT):
    """every profile's sheet as <key>.svg in out_dir, made if need be: [paths]"""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for key in sorted(SHEETS):
        path = os.path.join(out_dir, f"{key}.svg")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg(key, TITLES[key]))
        paths.append(path)
    return paths
