"""The IFR-1's quick-reference card and cheat sheet of a profile (ifr1.py, docs/using/ifr1.md): one page of HTML each,
to print on A4 in landscape, the card as a grid of the IFR-1's modes and controls, the cheat sheet as the IFR-1 drawn
with a box of words for each control (ifr1_sheet.py, from this module's Grid). The card lists what each control sets, as
MobiFlight lists the item (profile.label(), as the panel's card.py); the cheat sheet says what it does in a few words,
the panel's cheat sheet words (sheet_text.SHEETS) for the panel button it sends, words of its own for the rings the
IFR-1 turns otherwise than the panel (words_of()), and an Own code's name for code no panel button sends. Both mark a
control that sends nothing with "nothing" and the number of its reason, listed below. Both pages are self-contained
and depend on the profile alone, so the same tables make the same bytes.
"""
import html

from mobiflight import card, ifr1, profile, sheet
from mobiflight.families import FAMILIES, every_part
from mobiflight.sheet_text import SHEETS

# the modes as rows: (MobiFlight's name, title), the shifted ones by the legend under their mode key
MODES = (("COM1", "COM1"), ("COM2", "COM2"), ("NAV1", "NAV1"), ("NAV2", "NAV2"), ("FMS1", "FMS1"), ("FMS2", "FMS2"),
         ("AP", "AP"), ("XPDR", "XPDR"), ("COM1^", "HDG (COM1 shifted)"), ("COM2^", "BARO (COM2 shifted)"),
         ("NAV1^", "CRS1 (NAV1 shifted)"), ("NAV2^", "CRS2 (NAV2 shifted)"), ("XPDR^", "lights (XPDR shifted)"))
# the keys as rows: (title, FMS1's and FMS2's key, the bottom row's key in the other modes)
KEYS = (("DCT", "DCT", None), ("MENU", "MENU", None), ("CLR", "CLR", None), ("ENT", "ENT", None),
        ("AP / CDI", "CDI", "AP"), ("HDG / OBS", "OBS", "HDG"), ("NAV / MSG", "MSG", "NAV"),
        ("APR / FPL", "FPL", "APR"), ("ALT / VNAV", "VNAV", "ALT"), ("VS / PROC", "PROC", "VS"))
TURN = "↻ / ↺"
# the units of the navigators of both units, and of the Bonanza's tablet selections, by name (the navigators of one
# unit by their part's NAME)
UNIT_NAMES = {"navigator-g1000": {1: "MFD", 2: "PFD"}, "navigator-g3x": {1: "PFD", 2: "MFD"},
              "navigator-black-square-bonanza-unit1": {1: "primary: GNS 530, GTN 750 or KLN 90B"},
              "navigator-black-square-bonanza-unit2": {2: "secondary: GNS 430 or GTN 650"}}
# the panel's words for a key of both units that name unit 1's navigators, for unit 2 (FMS2 or FMS1)
UNIT2_WORDS = {"black-square-bonanza": {"CDI": "GNS 430 CDI: GPS or VLOC", "MENU": "MENU"}}
# the course of the IFR-1's CRS1, by the cockpit part
COURSE = {"g1000": "course of the CDI (PFD CRS knob)", "g3x": "course of the CDI", "bendix-king": "NAV 1 course"}


def unit_name(family, unit):
    """What a unit of the profile is ("PFD", "GNS 430")"""
    for part in family.PARTS:
        if part in UNIT_NAMES and unit in UNIT_NAMES[part]:
            return UNIT_NAMES[part][unit]
    return next(every_part()[p].NAME for p in family.PARTS if p.startswith("navigator-") and p.endswith(f"-unit{unit}"))


def _radio(device, kind):
    return {f"{kind}_MHZ_UP": f"{kind} {device} MHz", f"{kind}_KHZ_UP": f"{kind} {device} kHz",
            f"{kind}_SWAP": f"{kind} {device} flip-flop"}


def words_of(key):
    """{(device, panel button): words} for the IFR-1's rows of this profile: the panel's cheat sheet words of the
    control the button belongs to (sheet.CONTROLS), the rings the IFR-1 turns otherwise than the panel by its own
    words; a ring's own words under its _UP name stand for its _DN too"""
    texts, _ = SHEETS[key]
    family = ifr1.FAMILIES[key]
    course = COURSE[ifr1._part(family, "cockpit")]
    out = {}
    for control, buttons in sheet.CONTROLS.items():
        for button in buttons:
            out[1, button] = out[2, button] = texts.get(control)
    for button, text in UNIT2_WORDS.get(key, {}).items():
        out[2, button] = text
    own = {
        **{(d, b): w for d in (1, 2) for kind in ("COM", "NAV") for b, w in _radio(d, kind).items()},
        (1, "HDG_10_UP"): "heading bug 10°", (1, "HDG_1_UP"): "heading bug 1°",
        (1, "CRS_10_UP"): f"{course} 10°", (1, "CRS_1_UP"): f"{course} 1°",
        (1, "ALT_100_UP"): "selected altitude 100 ft", (1, "ALT_1000_UP"): "1000 ft",
        (1, "PANEL_LT_UP"): texts["PANEL"], (1, "FLOOD_LT_UP"): texts["FLOOD"],
    }
    for (device, button), text in own.items():
        out[device, button] = text
        if button.endswith("_UP"):                           # the other way, in the same words
            out[device, button.removesuffix("_UP") + "_DN"] = text
    return out


class Grid:
    """The grid of a profile's IFR-1 controls; text(uses) gives a cell's text as HTML from the Uses of its buttons
    (one per way: ↻ then ↺), the reasons of what sends nothing numbered as they come"""

    def __init__(self, ifr1_profile, words=False):
        self.p, self.reasons = ifr1_profile, {}
        self.words = words_of(ifr1_profile.KEY) if words else None

    def nothing(self, reason):
        number = self.reasons.setdefault(reason, len(self.reasons) + 1)
        return f'<span class="off">nothing<sup>{number}</sup></span>'

    def say(self, use, at_once=False):
        """What one Use sends, as HTML: its words or its label, or nothing with its reason; at_once: as the IFR-1
        sends it on one event (ifr1.tapped()), a key's press and release together"""
        if use.entry is None:
            return self.nothing(use.reason) if use.reason else None
        if self.words is not None:
            if isinstance(use.source, ifr1.Own):
                return html.escape(use.source.name)
            if isinstance(use.source, ifr1.Plus):                 # the panel's words, then the IFR-1's own
                device, button = use.source.panel
                sent = button in FAMILIES[self.p.KEY].DEVICE[device]  # the panel's words only where it sends
                panel = self.words[device, button] if sent else None
                return html.escape("; ".join(filter(None, (panel, use.source.own.name))))
            text = self.words[use.source.device, use.source.button]
            assert text, (self.p.KEY, use.source)      # a mapped control has words (tests/test_ifr1.py)
            return html.escape(text)
        if at_once:
            return html.escape(profile.label(ifr1.tapped(use.entry)))
        acts = profile.actions(use.entry)
        if set(acts) == {"onPress", "onRelease"}:
            press, release = (profile.label(acts[a]) for a in ("onPress", "onRelease"))
            if press != release:
                return html.escape(f"{press}; release: {release}")
        return html.escape(profile.label(" ".join(acts.values())))

    def ways(self, used, use, mapped=False):
        """The texts of one use of a pair of buttons (↻, ↺) joined, one text where both say the same; None where
        neither has the use (mapped: neither sends anything for it)"""
        texts = [self.say(u[use], at_once=True) if use in u and (u[use].entry or not mapped) else None for u in used]
        if not any(texts):
            return None
        if len(set(texts)) == 1:
            return texts[0]
        return " / ".join(t or "nothing" for t in texts)

    def knob(self, buttons):
        """A ring's cell: its turn, and with ⇆ held what it sends instead"""
        used = [self.p.USES[b] for b in buttons]
        if all(b in self.p.UNMAPPED for b in buttons) and len({self.p.UNMAPPED[b] for b in buttons}) == 1:
            return self.nothing(self.p.UNMAPPED[buttons[0]])
        parts = [self.ways(used, "turn") or "nothing"]
        if (held := self.ways(used, "held", mapped=True)) is not None:      # unmapped: the ring turns as without
            parts.append(f"<i>⇆ held:</i> {held}")
        if (once := self.ways(used, "once", mapped=True)) is not None:
            parts.append(f"<i>⇆ held, first detent:</i> {once}")
        return "; ".join(parts)

    def key(self, button):
        """A key's cell: its press, or its tap and its hold"""
        if button in self.p.UNMAPPED:
            return self.nothing(self.p.UNMAPPED[button])
        used = self.p.USES[button]
        if "tap" in used:                                    # ⇆ as a modifier
            tap, hold = self.say(used["tap"], at_once=True), self.say(used["hold"], at_once=True)
            parts = [f"<i>tap:</i> {tap}" if tap else None, f"<i>hold:</i> {hold}" if hold else None]
            return "; ".join(p for p in parts if p) or '<span class="off">only held while turning a ring</span>'
        key, hold = used["key"], used.get("hold")
        if mic := used.get("long_hold"):
            return (f"<i>tap:</i> {self.say(key, at_once=True)}; <i>hold:</i> {self.say(hold, at_once=True)}; "
                    f"<i>hold {ifr1.TALK_MS / 1000:g} s:</i> {self.say(mic, at_once=True)}")
        if hold is not None and hold.entry is not None and hold.entry != key.entry:
            tap = self.say(key, at_once=True) if key.entry is not None else None
            return "; ".join(p for p in (f"<i>tap:</i> {tap}" if tap else None,
                                         f"<i>hold:</i> {self.say(hold, at_once=True)}") if p)
        return self.say(key)

    def push(self, mode):
        """The knob push: CRSR, or MobiFlight's shift in a mode that has one"""
        if mode.rstrip("^") in ifr1.SHIFTED:
            return "shift: back to " + mode.rstrip("^") if mode.endswith("^") else "shift: " + dict(MODES)[mode + "^"]
        return self.key(f"Button_{mode}_CRSR")

    def modes(self):
        """The modes' rows, as HTML"""
        rows = []
        for mode, title in MODES:
            if mode in ("FMS1", "FMS2"):
                unit = self.p.UNITS[int(mode[-1]) - 1]
                title = f"{title}: {unit_name(ifr1.FAMILIES[self.p.KEY], unit)}"
            cells = [self.knob([f"Button_{mode}_OI", f"Button_{mode}_OD"]),
                     self.knob([f"Button_{mode}_II", f"Button_{mode}_ID"]),
                     self.push(mode), self.key(f"Button_{mode}_TOG")]
            rows.append(f"<tr><th>{html.escape(title)}</th>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        return "\n".join(rows)

    def keys(self):
        """The keys' rows, as HTML: in FMS1, in FMS2, and in every other mode"""
        rows = []
        for title, fms, other in KEYS:
            cells = [self.key(f"Button_FMS1_{fms}"), self.key(f"Button_FMS2_{fms}"),
                     self.key(f"Button_AP_{other}") if other else '<span class="off">only in FMS1 and FMS2</span>']
            rows.append(f"<tr><th>{html.escape(title)}</th>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        return "\n".join(rows)


STYLE = """@page { size: A4 landscape; margin: 7mm; }
:root { --ink: #1b1b1b; --soft: #6b6b6b; --line: #c9c9c9; --paper: #ffffff; }
* { box-sizing: border-box; }
html { background: var(--paper); color: var(--ink); color-scheme: light; }
body { margin: 0 auto; width: 283mm; padding: 0; font: 6.5pt/1.25 "Barlow Semi Condensed", "Roboto Condensed",
  "Arial Narrow", "Liberation Sans Narrow", Arial, sans-serif; -webkit-print-color-adjust: exact;
  print-color-adjust: exact; }
header { display: flex; justify-content: space-between; align-items: baseline; gap: 4mm;
  border-bottom: 0.4mm solid var(--ink); margin-bottom: 1.5mm; }
h1 { font-size: 11pt; margin: 0; white-space: nowrap; }
h2 { font-size: 7.5pt; margin: 1.5mm 0 0.5mm; }
.version { font-size: 7pt; font-weight: normal; color: var(--soft); }
header p { margin: 0; color: var(--soft); text-align: right; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
th, td { text-align: left; vertical-align: top; padding: 0.4mm 1mm; border-bottom: 0.25mm solid var(--line);
  overflow-wrap: anywhere; }
thead th { font-weight: bold; border-bottom: 0.4mm solid var(--ink); }
tbody th { font-weight: bold; }
col.head { width: 24mm; }
tr { break-inside: avoid; }
.off { color: var(--soft); font-style: italic; }
i { color: var(--soft); }
ol { columns: 2; column-gap: 4mm; margin: 1mm 0 0; padding-left: 3mm; color: var(--soft); }
footer { margin-top: 1mm; }
footer p { margin: 0.6mm 0 0; font-weight: bold; }
figure { margin: 0; }
figure svg { display: block; width: 100%; height: auto; max-height: 172mm; }
"""


def page(ifr1_profile, version=None, words=False):
    """The IFR-1's card (words False) or cheat sheet (words True) of a profile, as a page of HTML, with the commit of
    the files in its title (version: as card.page's). The card is a grid of the modes and keys; the cheat sheet the
    IFR-1 drawn with a box of words for each control (ifr1_sheet.py). Both list why a control does nothing below."""
    from mobiflight import ifr1_sheet  # imports this module's Grid
    if words:
        drawing, grid = ifr1_sheet.svg(ifr1_profile)
        body = f'<figure>\n{drawing}</figure>\n'
    else:
        grid = Grid(ifr1_profile)
        modes, keys = grid.modes(), grid.keys()
        body = f"""<h2>Modes</h2>
<table>
<colgroup><col class="head"><col><col><col><col></colgroup>
<thead><tr><th>Mode</th><th>Outer ring {TURN}</th><th>Inner ring {TURN}</th><th>Knob push</th><th>⇆</th></tr></thead>
<tbody>
{modes}
</tbody>
</table>
<h2>Keys</h2>
<table>
<colgroup><col class="head"><col><col><col></colgroup>
<thead><tr><th>Key</th><th>FMS1</th><th>FMS2</th><th>Every other mode</th></tr></thead>
<tbody>
{keys}
</tbody>
</table>
"""
    notes = "\n".join(f'<li value="{n}">{html.escape(r)}</li>' for r, n in grid.reasons.items())
    footer = (f"<footer>\n<p>Why a control does nothing in this profile:</p>\n<ol>\n{notes}\n</ol>\n</footer>\n"
              if notes else "")
    what = "cheat sheet" if words else "card"
    name = html.escape(ifr1_profile.NAME)
    stamp, title_stamp = card.stamps(version)
    intro = ("What each control of the IFR-1 does with the MobiFlight profile "
             if words else "What each control of the IFR-1 sets with the MobiFlight profile ")
    intro += (f"{ifr1.filename(ifr1_profile.KEY)}{'' if words else ', as MobiFlight lists the events and variables'}"
              ". A ring lists clockwise / counter-clockwise where they differ. ⇆ in FMS1, FMS2, AP and XPDR: held "
              "while turning a ring, the ring does what follows \"⇆ held\", and ⇆ sends nothing on its release "
              "(press ⇆ first, then turn); otherwise a tap sends its tap, a hold of over "
              f"{profile.LONG_MS / 1000:g} s its hold, on release. A key with a hold sends its tap on release too.")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Avionics Panel for the IFR-1: {name}, {what}{title_stamp}</title>
<style>
{STYLE}</style>
</head>
<body>
<header>
<h1>IFR-1: {name}{stamp}</h1>
<p>{html.escape(intro)}</p>
</header>
{body}{footer}</body>
</html>
"""
