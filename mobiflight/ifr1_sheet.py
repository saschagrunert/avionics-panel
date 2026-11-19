"""The IFR-1's cheat sheet of a profile as a drawing (ifr1_card.page(words=True)): the IFR-1 in the middle, to scale
from a photo of the device, and round it a box of plain words for each mode key, each key, the knob and ⇆, with a
leader line from the box to its control. The words are the cheat sheet's (ifr1_card.Grid); this module lays them
out.

Where the boxes go: the knob, ⇆ and the left column of mode keys but COM1 (NAV1, FMS1, AP) on the left; COM1, COM2 and
NAV2 above; the four keys on the right (D→, MENU, CLR, ENT) with FMS2 and XPDR on the right; the six keys of the bottom
row below. Inside the device a line runs from its control to the edge in the gaps between the keys and round the knob
and the blue legends (ROUTES, in mm); outside it goes on straight to its box, the boxes of a side in the order their
lines leave the device, so no two lines cross. Sheet.boxes and Sheet.leads keep what was drawn, for the tests.
"""
import html
from html.parser import HTMLParser

from mobiflight import ifr1, ifr1_card
from mobiflight.sheet import width

# ---------------- the device, in mm from its top left corner (y down), measured on Octavi's top-down photo ----------
# (octavi.net/ifr-1) with its width taken as 110: the device is 112 x 74 mm, so the drawing is 2 % small throughout
BODY = (110.0, 73.2, 3.3)                         # width, height, corner radius
MODE_COLS = (54.75, 71.7)                         # the mode keys' columns, COM1's first
RIGHT_COL = 97.1                                  # D→, MENU, CLR, ENT
ROWS = (9.8, 21.7, 33.6, 45.5)                    # the rows of the mode keys and the keys on the right
KEY = (13.7, 7.1)                                 # a key's width and height
BOTTOM_COLS = (12.6, 29.5, 46.5, 63.4, 80.3, 97.2)
BOTTOM_ROW, BOTTOM_KEY = 62.2, (14.2, 5.6)
KNOB = (20.6, 17.5, 9.5, 7.3)                     # centre, outer ring's radius, inner ring's
SWAP = (21.1, 39.4, 13.5, 6.9)                    # ⇆: centre, width, height
LED = (63.3, 27.3, 1.7)
DIVIDER = (84.4, 6.6, 48.7)                       # the groove left of the keys on the right: x, from y, to y
GLOSS = ((0, 46.6), (37.5, 46.6), (45.5, 54.0), (110, 54.0))   # the glossy band's upper edge, left to right
MODE_GRID = (("COM1", "COM2"), ("NAV1", "NAV2"), ("FMS1", "FMS2"), ("AP", "XPDR"))
RIGHT_KEYS = ("DCT", "MENU", "CLR", "ENT")
LEGENDS = {"DCT": "-D→", "MENU": "MENU", "CLR": "CLR", "ENT": "ENT"}
BLUE_OVER = {"COM1": "HDG", "COM2": "BARO", "NAV1": "CRS1", "NAV2": "CRS2", "XPDR": "MODE"}
BOTTOM = (("AP", "CDI"), ("HDG", "OBS"), ("NAV", "MSG"), ("APR", "FPL"), ("ALT", "VNAV"), ("VS", "PROC"))


def _mode_key(mode):
    r = next(i for i, row in enumerate(MODE_GRID) if mode in row)
    return MODE_COLS[MODE_GRID[r].index(mode)], ROWS[r]


def _edges(cx, cy, w=KEY[0], h=KEY[1]):
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def routes():
    """{callout: (side, [(x, y) mm])}: each control's line inside the device, from its control to the device's edge,
    in the gaps between the keys, round the knob and ⇆ and clear of the blue legends"""
    w, h, _ = BODY
    out = {"KNOB": ("left", [(KNOB[0] - KNOB[2], KNOB[1]), (0, KNOB[1])]),
           "SWAP": ("left", [(SWAP[0] - SWAP[2] / 2, SWAP[1]), (0, SWAP[1])])}
    left = _edges(*_mode_key("NAV1"))[0]
    below_knob = (KNOB[1] + KNOB[2] + SWAP[1] - SWAP[3] / 2) / 2          # between the knob and ⇆
    out["NAV1"] = ("left", [(left, ROWS[1]), (left - 2.6, ROWS[1]), (left - 2.6, below_knob), (0, below_knob)])
    out["FMS1"] = ("left", [(left, ROWS[2]), (0, ROWS[2])])
    out["AP"] = ("left", [(left, ROWS[3]), (0, ROWS[3])])
    # above: up beside the blue legend, COM1's left of HDG, COM2's right of BARO, NAV2's right of its column
    out["COM1"] = ("top", [(left + 1.5, ROWS[0] - KEY[1] / 2), (left + 1.5, 0)])
    right = _edges(*_mode_key("COM2"))[2]
    out["COM2"] = ("top", [(right - 1.6, ROWS[0] - KEY[1] / 2), (right - 1.6, 0)])
    out["NAV2"] = ("top", [(right, ROWS[1]), (right + 2.9, ROWS[1]), (right + 2.9, 0)])
    # right: the keys straight out, FMS2 and XPDR down the gap left of the groove and out under CLR and ENT
    key_right = RIGHT_COL + KEY[0] / 2
    for key, y in zip(RIGHT_KEYS, ROWS, strict=True):
        out[key] = ("right", [(key_right, y), (w, y)])
    under_clr = (ROWS[2] + ROWS[3]) / 2
    out["FMS2"] = ("right", [(right, ROWS[2]), (right + 2.4, ROWS[2]), (right + 2.4, under_clr), (w, under_clr)])
    under_ent = (ROWS[3] + KEY[1] / 2 + GLOSS[-1][1]) / 2
    out["XPDR"] = ("right", [(right, ROWS[3]), (right + 3.9, ROWS[3]), (right + 3.9, under_ent), (w, under_ent)])
    # below: down from each key beside the white legend under it
    for (white, _), x in zip(BOTTOM, BOTTOM_COLS, strict=True):
        out[f"B_{white}"] = ("bottom", [(x - 5.6, BOTTOM_ROW + BOTTOM_KEY[1] / 2), (x - 5.6, h)])
    return out


ROUTES = routes()
SIDES = {side: [c for c, (s, _) in ROUTES.items() if s == side] for side in ("left", "top", "right", "bottom")}
# a side's boxes in the order their lines leave the device: down the left and right, along the top and bottom
for _side, _axis in (("left", 1), ("right", 1), ("top", 0), ("bottom", 0)):
    SIDES[_side].sort(key=lambda c, a=_axis: ROUTES[c][1][-1][a])


# ---------------- the page, in SVG units (px): A4 landscape, 297 mm wide ----------------
W = 1600
S = 5.2                              # px per mm on the device
FONT = "Arial, 'Liberation Sans', Helvetica, sans-serif"
INK, MUTED, BLUE, LINE = "#16181b", "#7a7f87", "#2f7fc1", "#5b6b85"
TEXT_PX, TITLE_PX, LINE_H, PAD = 11.5, 12.5, 14, 6
MARGIN, GAP, STUB = 16, 8, 14        # the page's margin, between boxes, a line's first piece outside the device
TOP_BOX = 186                        # a box's width above the device
TITLE_BOTTOM = 30                    # the legend line ends here (the page's header has the title)
SLACK = 8                            # px a line keeps free in its box, for a font wider than Arial
SUPER = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


class _Cell(HTMLParser):
    """A cell of ifr1_card.Grid (a little HTML) as runs of (text, style): "ink", "muted" (<i>), "off" (nothing)"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.runs, self.stack = [], ["ink"]

    def handle_starttag(self, tag, attrs):
        self.stack.append("off" if tag == "span" else "sup" if tag == "sup" else "muted")

    def handle_endtag(self, tag):
        self.stack.pop()

    def handle_data(self, data):
        style = self.stack[-1]
        if style == "sup":
            data, style = data.translate(SUPER), "off"
        self.runs.append((data, style))


def runs(cell):
    parser = _Cell()
    parser.feed(cell)
    return parser.runs


def wrap(row_runs, room):
    """runs in lines that fit room px wide, each line runs; a word keeps its style"""
    words = []
    for text, style in row_runs:
        parts = text.split(" ")
        for i, part in enumerate(parts):
            if i and words:
                words.append((" ", style))
            if part:
                words.append((part, style))
    lines, line, used = [], [], 0.0
    for word, style in words:
        w = width(word, TEXT_PX)
        if word == " ":
            if line:
                line.append((word, style))
                used += w
            continue
        if line and used + w > room:
            while line and line[-1][0] == " ":
                used -= width(line.pop()[0], TEXT_PX)
            lines.append(line)
            line, used = [], 0.0
        line.append((word, style))
        used += w
    return [*lines, line] if line else lines


def boxes_of(ifr1_profile):
    """{callout: (title, [(label, cell HTML, label colour)])}, and the Grid that numbered the reasons: what each
    box says, from the cheat sheet's cells (ifr1_card.Grid with words)"""
    grid = ifr1_card.Grid(ifr1_profile, words=True)
    family = ifr1.FAMILIES[ifr1_profile.KEY]
    shifted_titles = dict(ifr1_card.MODES)
    out = {"KNOB": ("Knob", [
        ("rings, push", "by the mode: each mode key's box. The push shifts COM1, COM2, NAV1, NAV2 and XPDR to the "
                        "blue legend over their key, and back", INK)]),
        "SWAP": ("⇆", [
            ("", "by the mode: each mode key's box. In FMS1, FMS2, AP and XPDR, held while turning a ring (press ⇆ "
                 "first, then turn): the ring does what follows <i>⇆ held</i>, and ⇆ sends nothing; otherwise a tap "
                 f"sends its tap, a hold of over {ifr1.profile.LONG_MS / 1000:g} s its hold, on its release; in COM1 "
                 f"and COM2 a hold of {ifr1.TALK_MS / 1000:g} s sends at once, with nothing on the release", INK)])}

    def mode_rows(mode, colour):
        outer = grid.knob([f"Button_{mode}_OI", f"Button_{mode}_OD"])
        inner = grid.knob([f"Button_{mode}_II", f"Button_{mode}_ID"])
        rows = [("rings", outer, colour)] if outer == inner else [("outer", outer, colour), ("inner", inner, colour)]
        return [*rows, ("push", grid.push(mode), colour), ("⇆", grid.key(f"Button_{mode}_TOG"), colour)]

    for row in MODE_GRID:
        for mode in row:
            title = mode
            if mode in ("FMS1", "FMS2"):
                unit = ifr1_profile.UNITS[int(mode[-1]) - 1]
                title = f"{mode}: {ifr1_card.unit_name(family, unit)}"
            rows = mode_rows(mode, INK)
            if mode in ifr1.SHIFTED:
                rows.append((shifted_titles[f"{mode}^"], None, BLUE))
                rows += mode_rows(f"{mode}^", BLUE)
            out[mode] = (title, rows)
    for key in RIGHT_KEYS:
        out[key] = (LEGENDS[key], [("FMS1", grid.key(f"Button_FMS1_{key}"), INK),
                                   ("FMS2", grid.key(f"Button_FMS2_{key}"), INK)])
    for white, blue in BOTTOM:
        out[f"B_{white}"] = (f"{white} / {blue}", [
            ("other modes", grid.key(f"Button_AP_{white}"), INK),
            (f"FMS1 {blue}", grid.key(f"Button_FMS1_{blue}"), BLUE),
            (f"FMS2 {blue}", grid.key(f"Button_FMS2_{blue}"), BLUE)])
    return out, grid


class Sheet:
    def __init__(self, ifr1_profile):
        self.p = ifr1_profile
        self.texts, self.grid = boxes_of(ifr1_profile)
        self.out, self.boxes, self.leads = [], {}, {}
        self.x0 = (W - BODY[0] * S) / 2
        self.y0 = 0.0

    def P(self, x, y):
        """a device point (mm, y down) on the page"""
        return self.x0 + x * S, self.y0 + y * S

    # ---------------- drawing ----------------
    def text(self, x, y, s, px=TEXT_PX, fill=INK, weight="normal", anchor="start"):
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{px}" font-weight="{weight}" fill="{fill}" '
                        f'text-anchor="{anchor}">{html.escape(s)}</text>')

    def lines(self, callout, room):
        """a box's lines: [(runs, weight, size)]"""
        title, rows = self.texts[callout]
        out = [([(title, "title")], "bold", TITLE_PX)]
        for label, cell, colour in rows:
            if cell is None:                                   # a shifted mode's title
                out.append(([(label, "blue")], "bold", TITLE_PX))
                continue
            head = [(f"{label}: ", "blue" if colour == BLUE else "label")] if label else []
            for line in wrap(head + runs(cell), room - SLACK):
                out.append((line, "normal", TEXT_PX))
        return out

    def box(self, callout, x, top, w, lines):
        h = len(lines) * LINE_H + 2 * PAD - 2
        self.boxes[callout] = (x, top, w, h)
        self.out.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="#ffffff" '
                        'stroke="#c3c8cf"/>')
        fills = {"title": INK, "blue": BLUE, "label": INK, "ink": INK, "muted": MUTED, "off": MUTED}
        for i, (line, weight, px) in enumerate(lines):
            merged = []                                        # one span for each run of a style
            for text, style in line:
                if merged and merged[-1][1] == style:
                    merged[-1] = (merged[-1][0] + text, style)
                else:
                    merged.append((text, style))
            spans = "".join(
                f'<tspan fill="{fills[style]}"'
                f'{" font-weight=" + chr(34) + "bold" + chr(34) if style in ("label",) else ""}'
                f'{" font-style=" + chr(34) + "italic" + chr(34) if style == "off" else ""}>'
                f'{html.escape(text)}</tspan>' for text, style in merged)
            self.out.append(f'<text x="{x + PAD:.1f}" y="{top + PAD + 10 + i * LINE_H:.1f}" font-size="{px}" '
                            f'font-weight="{weight}">{spans}</text>')
        return h

    @staticmethod
    def height(lines):
        return len(lines) * LINE_H + 2 * PAD - 2

    def lead(self, callout, points):
        self.leads[callout] = points
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        self.out.append(f'<polyline points="{d}" fill="none" stroke="#ffffff" stroke-width="4" '
                        'stroke-linejoin="round" stroke-opacity="0.85"/>')
        self.out.append(f'<polyline points="{d}" fill="none" stroke="{LINE}" stroke-width="1.4" '
                        'stroke-linejoin="round"/>')
        x, y = points[-1]
        self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{LINE}"/>')

    def key(self, cx, cy, w, h, legend, size=13, fill="#d4d5d8", lamp=False):
        x, y = self.P(cx - w / 2, cy - h / 2)
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w * S:.1f}" height="{h * S:.1f}" rx="7" '
                        'fill="#202225" stroke="#000" stroke-width="1.5"/>')
        if lamp:                                               # the bottom row's light bar
            lx, ly = self.P(cx - w * 0.355, cy - 0.55)
            self.out.append(f'<rect x="{lx:.1f}" y="{ly:.1f}" width="{w * 0.71 * S:.1f}" height="{1.1 * S:.1f}" '
                            'rx="2.3" fill="#d9dadc"/>')
        elif legend:
            self.text(*self.P(cx, cy + 1.6), legend, size, fill, "bold", "middle")

    def device(self):
        w, h, r = BODY
        x, y = self.P(0, 0)
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w * S:.1f}" height="{h * S:.1f}" rx="{r * S:.1f}" '
                        'fill="#2b2d31"/>')
        gloss = [*GLOSS, (w, h), (0, h)]
        d = " ".join(f"{px:.1f},{py:.1f}" for px, py in (self.P(*p) for p in gloss))
        self.out.append(f'<clipPath id="body"><rect x="{x:.1f}" y="{y:.1f}" width="{w * S:.1f}" '
                        f'height="{h * S:.1f}" rx="{r * S:.1f}"/></clipPath>')
        self.out.append(f'<polygon points="{d}" fill="#45484e" clip-path="url(#body)"/>')
        gx, gy0 = self.P(DIVIDER[0], DIVIDER[1])
        _, gy1 = self.P(DIVIDER[0], DIVIDER[2])
        self.out.append(f'<line x1="{gx:.1f}" y1="{gy0:.1f}" x2="{gx:.1f}" y2="{gy1:.1f}" stroke="#16171a" '
                        'stroke-width="8" stroke-linecap="round"/>')
        lx, ly = self.P(LED[0], LED[1])
        self.out.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{LED[2] * S:.1f}" fill="#141518"/>')
        kx, ky = self.P(KNOB[0], KNOB[1])
        for radius, fill in ((KNOB[2], "#1b1c1f"), (KNOB[3], "#2f3135")):
            self.out.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="{radius * S:.1f}" fill="{fill}" stroke="#000" '
                            'stroke-width="1.5"/>')
        self.key(*SWAP, "")
        # ⇆'s legend as the device prints it: one arrow, both heads filled (a font's ↔ draws too small)
        cx, cy, half, head, tip, shaft = SWAP[0], SWAP[1] + 0.2, 3.3, 1.5, 1.05, 0.28
        arrow = [(cx - half, cy), (cx - half + head, cy - tip), (cx - half + head, cy - shaft),
                 (cx + half - head, cy - shaft), (cx + half - head, cy - tip), (cx + half, cy),
                 (cx + half - head, cy + tip), (cx + half - head, cy + shaft), (cx - half + head, cy + shaft),
                 (cx - half + head, cy + tip)]
        d = " ".join(f"{px:.1f},{py:.1f}" for px, py in (self.P(*p) for p in arrow))
        self.out.append(f'<polygon points="{d}" fill="#c9cbcf"/>')
        for mode in (m for row in MODE_GRID for m in row):
            cx, cy = _mode_key(mode)
            self.key(cx, cy, *KEY, mode)
            if mode in BLUE_OVER:
                self.text(*self.P(cx, cy - KEY[1] / 2 - 1.3), BLUE_OVER[mode], 10.5, "#6fa8dc", "bold", "middle")
        for key, cy in zip(RIGHT_KEYS, ROWS, strict=True):
            self.key(RIGHT_COL, cy, *KEY, LEGENDS[key])
        for (white, blue), cx in zip(BOTTOM, BOTTOM_COLS, strict=True):
            self.key(cx, BOTTOM_ROW, *BOTTOM_KEY, "", lamp=True)
            self.text(*self.P(cx, BOTTOM_ROW - BOTTOM_KEY[1] / 2 - 1.3), blue, 10.5, "#6fa8dc", "bold", "middle")
            self.text(*self.P(cx, BOTTOM_ROW + BOTTOM_KEY[1] / 2 + 4.6), white, 14, "#ffffff", "bold", "middle")

    # ---------------- layout ----------------
    @staticmethod
    def stack(tops, heights, lo, hi):
        """tops as near the wanted ones as boxes of these heights allow, in order, GAP apart, within lo and hi"""
        out = []
        for top in tops:
            out.append(max(top, lo, out[-1] + heights[len(out) - 1] + GAP if out else lo))
        over = out[-1] + heights[-1] - hi if out else 0
        if over > 0:                                           # push back up from the bottom
            out[-1] -= over
            for i in range(len(out) - 2, -1, -1):
                out[i] = min(out[i], out[i + 1] - GAP - heights[i])
        return out

    def svg(self):
        side_w = self.x0 - MARGIN - 2 * STUB - 24
        top_lines = {c: self.lines(c, TOP_BOX - 2 * PAD) for c in SIDES["top"]}
        top_h = max(self.height(lines) for lines in top_lines.values())
        self.y0 = TITLE_BOTTOM + top_h + 2 * STUB + 26
        bottom_w = (W - 2 * MARGIN - 5 * GAP) / 6
        bottom_lines = {c: self.lines(c, bottom_w - 2 * PAD) for c in SIDES["bottom"]}
        bottom_top = self.y0 + BODY[1] * S + 2 * STUB + 26
        self.device()
        # above: the boxes side by side over the device, each over its line where the others leave room
        span = len(SIDES["top"]) * TOP_BOX + (len(SIDES["top"]) - 1) * GAP
        left = self.P(BODY[0] / 2, 0)[0] - span / 2
        for i, callout in enumerate(SIDES["top"]):
            bx = left + i * (TOP_BOX + GAP)
            bottom = TITLE_BOTTOM + top_h
            h = self.height(top_lines[callout])
            self.box(callout, bx, bottom - h, TOP_BOX, top_lines[callout])
            points = [self.P(*p) for p in ROUTES[callout][1]]
            ex, ey = points[-1]
            ax = min(max(ex, bx + 12), bx + TOP_BOX - 12)
            self.lead(callout, [(ax, bottom), (ax, ey - STUB - 10), (ex, ey - STUB), *reversed(points)])
        # left and right: stacked from the top of the page to the bottom band, each as near its line's height
        for side in ("left", "right"):
            calls = SIDES[side]
            lines = {c: self.lines(c, side_w - 2 * PAD) for c in calls}
            heights = [self.height(lines[c]) for c in calls]
            exits = [self.P(*ROUTES[c][1][-1])[1] for c in calls]
            tops = self.stack([e - h / 2 for e, h in zip(exits, heights, strict=True)], heights, TITLE_BOTTOM,
                              bottom_top - 26)
            bx = MARGIN if side == "left" else W - MARGIN - side_w
            for callout, top, h in zip(calls, tops, heights, strict=True):
                self.box(callout, bx, top, side_w, lines[callout])
                points = [self.P(*p) for p in ROUTES[callout][1]]
                ex, ey = points[-1]
                sign = -1 if side == "left" else 1
                ay = min(max(ey, top + 12), top + h - 12)
                edge = bx + side_w if side == "left" else bx
                self.lead(callout, [(edge, ay), (ex + sign * STUB, ey), *reversed(points)])
        # below: a row of boxes across the page, each line straight down from its key into the band under the side
        # boxes (which end 26 px over the row) and across it to its box, so it passes no other box
        bottom_h = max(self.height(lines) for lines in bottom_lines.values())
        band = bottom_top - 20
        for i, callout in enumerate(SIDES["bottom"]):
            bx = MARGIN + i * (bottom_w + GAP)
            self.box(callout, bx, bottom_top, bottom_w, bottom_lines[callout])
            points = [self.P(*p) for p in ROUTES[callout][1]]
            ex, ey = points[-1]
            ax = min(max(ex, bx + 12), bx + bottom_w - 12)
            self.lead(callout, [(ax, bottom_top), (ex, band), *reversed(points)])
        height = bottom_top + bottom_h + MARGIN
        head = [f'<text x="{W / 2:.1f}" y="18" font-size="12" fill="{MUTED}" text-anchor="middle">'
                f'{html.escape(INTRO)}</text>']
        body = "\n".join(head + self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height:.0f}" font-family="{FONT}">\n'
                f'<rect width="{W}" height="{height:.0f}" fill="#f6f7f9"/>\n{body}\n</svg>\n')


INTRO = ("Blue: the shifted mode (knob push) and the FMS functions of the bottom row.  A ring: clockwise / "
         "counter-clockwise where they differ.  \"nothing\": the profile sends nothing for it, for the reason below.")


def plain(ifr1_profile):
    """{callout: [row as plain text]}: what each box says, its title first, a row "label: text" (for the tests)"""
    texts, _ = boxes_of(ifr1_profile)
    out = {}
    for callout, (title, rows) in texts.items():
        out[callout] = [title] + [label if cell is None else
                                  (f"{label}: " if label else "") + "".join(t for t, _ in runs(cell))
                                  for label, cell, _ in rows]
    return out


def svg(ifr1_profile):
    """the drawing of a profile's cheat sheet, and the Grid that numbered its reasons (for the notes under it)"""
    sheet = Sheet(ifr1_profile)
    return sheet.svg(), sheet.grid
