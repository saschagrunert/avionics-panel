"""The quick-reference card of a profile: one page of HTML, to print on A4 in landscape, with what every control of
the panel sets in that profile, plain, with SHIFT and in unit 2 (docs/using/mapping.md#quick-reference-cards).

The keys come in the order of the panel and under their legends (mech/stack.py's KEY_LEGENDS), the knobs' rings and
pushes under the words of KNOB_LEGENDS. A mapped button shows what its code sets, as MobiFlight lists the item
(profile.label()); an unmapped one shows "nothing" and the number of its reason (the family's UNMAPPED), listed under
the keys. The page is self-contained (no scripts, fonts or pictures from elsewhere) and depends on the profile alone,
so the same tables make the same bytes.
"""
import functools
import html
import os

from mobiflight import profile

BM = profile.BM


def key_name(legend):
    """A cap's legend (mech/stack.py's KEY_LEGENDS) -> its button name, as sim.key_name gives it (not in
    buttonmap.py, which the panel loads: code it never runs still costs RAM there; test_card.py keeps the two alike)"""
    return {"D→": "DIRECT"}.get(legend, legend.replace(" ⇆", "_SWAP").replace(" ", ""))


@functools.cache
def stack():
    """mech/stack.py, read when a card is made: the profiles themselves do without it"""
    return profile._load("_mobiflight_stack", os.path.join(profile.HERE, "..", "mech", "stack.py"))


TURN = "↻ / ↺"                   # a pair of buttons: clockwise / counter-clockwise
FREQ_HOLD = "1 s"                # a plain FREQ push held this long returns the knob to COM (firmware/panel.py)


def words(legend):
    """A knob legend's words: its rings, outer first, then its push"""
    return legend.split(" · ")


def knobs():
    """[(title, amber title or None, [(shifted, row title, [button, ...]), ...])], in the panel's order: ALT/HDG and
    RANGE on the left, FREQ and FMS on the right. A row of two buttons is a ring turned both ways or a tilt both
    ways, in the order its title gives."""
    alt, hdg, sync = words(stack().KNOB_LEGENDS["ALTHDG"][0])
    baro, crs, std = words(stack().KNOB_LEGENDS["ALTHDG"][1])
    rng, ptr = words(stack().KNOB_LEGENDS["RANGE"][0])
    freq, mode = words(stack().KNOB_LEGENDS["FREQ"][0])
    squawk, xpdr = words(stack().KNOB_LEGENDS["FREQ"][1])
    fms, crsr = words(stack().KNOB_LEGENDS["FMS"][0])
    panel, flood, cabin = words(stack().KNOB_LEGENDS["FMS"][1])
    tilt = [("tilt ▲ / ▼", ["PAN_UP", "PAN_DN"]), ("tilt ◀ / ▶", ["PAN_LEFT", "PAN_RIGHT"])]
    ranges = [(f"{rng} {TURN}", ["RANGE_CW", "RANGE_CCW"]), *tilt, (ptr, ["PTR"])]
    return [
        (f"{alt}/{hdg}", f"{baro}/{crs}", [
            (False, f"{alt}, outer {TURN}", BM.turn("ALT_100")),
            (False, f"{alt}, quick turn {TURN}", BM.turn("ALT_1000")),
            (False, f"{hdg}, inner {TURN}", BM.turn("HDG_1")), (False, f"{hdg}, quick turn {TURN}", BM.turn("HDG_10")),
            (False, sync, ["HDG_SYNC"]),
            (True, f"{baro}, outer {TURN}", BM.turn("BARO")), (True, f"{crs}, inner {TURN}", BM.turn("CRS_1")),
            (True, f"{crs}, quick turn {TURN}", BM.turn("CRS_10")), (True, std, ["BARO_STD"])]),
        (rng, None, [(False, title, names) for title, names in ranges]
         + [(True, title, [f"S_{n}" for n in names]) for title, names in ranges]),
        (freq, squawk, [
            (False, f"COM, outer {TURN}", BM.turn("COM_MHZ")), (False, f"COM, inner {TURN}", BM.turn("COM_KHZ")),
            (False, f"NAV, outer {TURN}", BM.turn("NAV_MHZ")), (False, f"NAV, inner {TURN}", BM.turn("NAV_KHZ")),
            (False, f"ADF, outer {TURN}", BM.turn("ADF_100")), (False, f"ADF, inner {TURN}", BM.turn("ADF_1")),
            (False, f"ADF, quick turn {TURN}", BM.turn("ADF_10")),
            (False, f"{mode} (green light: off COM, on NAV, blinks ADF); held {FREQ_HOLD}: back to COM",
             ["FREQ_PUSH"]),
            *((True, f"{squawk} digit {d}, inner {TURN}", BM.turn(f"SQK_D{d}")) for d in (1, 2, 3, 4)),
            (True, xpdr, ["XPDR_MODE"])]),
        (fms, f"{panel}/{flood}", [
            (False, f"outer {TURN}", ["FMS_OUTER_CW", "FMS_OUTER_CCW"]),
            (False, f"inner {TURN}", ["FMS_INNER_CW", "FMS_INNER_CCW"]), (False, crsr, ["FMS_CRSR"]),
            (True, f"{panel}, outer {TURN}", BM.turn("PANEL_LT")),
            (True, f"{flood}, inner {TURN}", BM.turn("FLOOD_LT")),
            (True, cabin, ["CABIN_LT"])]),
    ]


def caps():
    """[[(legend, amber legend, button, its button with SHIFT), ...] per row]: the keys as the panel has them; SHIFT
    sends no button, HOME with SHIFT is UNIT (firmware state)"""
    out = []
    for row in stack().KEY_LEGENDS:
        out.append([])
        for legend, amber in row:
            name = key_name(legend)
            shifted = None if name in ("SHIFT", "HOME") else BM.shifted(name)
            out[-1].append((legend, amber, None if name == "SHIFT" else name, shifted))
    return out


class Card:
    """What a profile's buttons set, as HTML, and the reasons of its unmapped ones, numbered as they come"""

    def __init__(self, family):
        self.family, self.reasons = family, {}

    def one(self, device, button):
        """(HTML, whether the button is unmapped)"""
        entry = self.family.DEVICE[device].get(button)
        if entry is None:
            reason = self.family.UNMAPPED[device][button]
            number = self.reasons.setdefault(reason, len(self.reasons) + 1)
            return f'<span class="off">nothing<sup>{number}</sup></span>', True
        acts = profile.actions(entry)
        if "onLongRelease" not in acts:
            press, release = (profile.label(acts[a]) if a in acts else "" for a in ("onPress", "onRelease"))
            if press and release and press != release:                     # what a release undoes, apart
                return html.escape(f"{press}; release: {release}"), False
            return html.escape(profile.label(" ".join(acts.values()))), False
        # sent on a release after a tap, or after a hold instead
        parts = [*([profile.label(acts["onPress"])] if "onPress" in acts else []),
                 *([f"tap: {profile.label(acts['onRelease'])}"] if "onRelease" in acts else []),
                 f"hold: {profile.label(acts['onLongRelease'])}"]
        return html.escape("; ".join(parts)), False

    def value(self, device, buttons):
        """What these buttons set on this device, joined by " / ", or one "nothing" for buttons unmapped alike"""
        out = [self.one(device, b) for b in buttons]
        if all(off for _, off in out) and len(set(out)) == 1:
            return out[0][0]
        return " / ".join(text for text, _ in out)

    def codes(self, device, buttons):
        """What these buttons send on this device: their codes, or the reasons they send nothing"""
        table, unmapped = self.family.DEVICE[device], self.family.UNMAPPED[device]
        return [profile.actions(table[b]) if b in table else unmapped[b] for b in buttons]

    def lines(self, buttons):
        """[(device, HTML)]: device 1's, and device 2's (unit 2) where these buttons are on device 2 too, "the same"
        where they send the same codes (labels leave out the numbers, as a GTN's unit in its events)"""
        first = self.value(1, buttons)
        if not all(b in BM.BUTTON[2] for b in buttons):
            return [(1, first)]
        if self.codes(2, buttons) == self.codes(1, buttons):
            return [(1, first), (2, "the same")]
        return [(1, first), (2, self.value(2, buttons))]


def row(card, title, buttons, shifted):
    tag = f'<b class="{"amber" if shifted else "plain"}">{html.escape(title)}</b>'
    out = []
    for device, text in card.lines(buttons):
        head = tag if device == 1 else '<b class="unit">unit 2</b>'
        out.append(f"<tr><th>{head}</th><td>{text}</td></tr>")
    return "<tbody>" + "".join(out) + "</tbody>"


def page(family, key, version=None):
    """The card of a profile (families.FAMILIES[key]) as a page of HTML, with the commit of the files in its title as
    the profile's name has it (version: the command line passes --stamp, profile.VERSION unless given; None for
    none)"""
    card, cells = Card(family), []
    for keyrow in caps():
        for legend, amber, plain, shifted in keyrow:
            if plain is None:
                body = ('<tbody><tr><th><b class="plain">SHIFT</b></th><td>tap, then a key or knob: its amber '
                        'function (amber light); SHIFT, HOME: UNIT, unit 1 or 2 (white light)</td></tr></tbody>')
            elif shifted is None:
                body = "\n".join([row(card, legend, [plain], False),
                                  f'<tbody><tr><th><b class="amber">{html.escape(amber)}</b></th><td>unit 1 or 2, in '
                                  'the panel</td></tr></tbody>'])
            else:
                body = "\n".join([row(card, legend, [plain], False),
                                  row(card, amber or "SHIFT", [shifted], True)])
            cells.append(f'<div class="key"><table>\n{body}\n</table></div>')
    blocks = []
    for title, amber, rows in knobs():
        head = html.escape(title) + (f' <span class="amber">{html.escape(amber)}</span>' if amber else "")
        body = "\n".join(row(card, t if not s or amber else f"SHIFT, {t}", b, s) for s, t, b in rows)
        blocks.append(f'<div class="knob"><h3>{head} knob</h3><table>\n{body}\n</table></div>')
    notes = "\n".join(f'<li value="{n}">{html.escape(r)}</li>' for r, n in card.reasons.items())
    name = html.escape(family.NAME)
    version = html.escape(version) if version else ""
    stamp = f' <span class="version">({version})</span>' if version else ""
    title_stamp = f" ({version})" if version else ""                                # the printout's header, the PDF
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Avionics Panel: {name}{title_stamp}</title>
<style>
@page {{ size: A4 landscape; margin: 7mm; }}
:root {{ --ink: #1b1b1b; --soft: #6b6b6b; --line: #c9c9c9; --amber: #a35f00; --paper: #ffffff; }}
* {{ box-sizing: border-box; }}
html {{ background: var(--paper); color: var(--ink); color-scheme: light; }}
body {{ margin: 0 auto; width: 283mm; padding: 0; font: 6pt/1.2 "Barlow Semi Condensed", "Roboto Condensed",
  "Arial Narrow", "Liberation Sans Narrow", Arial, sans-serif; -webkit-print-color-adjust: exact;
  print-color-adjust: exact; }}
header {{ display: flex; justify-content: space-between; align-items: baseline; gap: 4mm;
  border-bottom: 0.4mm solid var(--ink); margin-bottom: 1.5mm; }}
h1 {{ font-size: 11pt; margin: 0; white-space: nowrap; }}
.version {{ font-size: 7pt; font-weight: normal; color: var(--soft); }}
header p {{ margin: 0; color: var(--soft); text-align: right; }}
h3 {{ font-size: 7pt; margin: 0 0 0.4mm; }}
.keys {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 1mm; }}
/* a knob to a column, each as wide as its rows need: the FMS knob's lighting lists the most in the Bonanza */
.knobs {{ display: grid; grid-template-columns: minmax(0, 0.68fr) minmax(0, 0.85fr) minmax(0, 1.05fr) minmax(0, 1.42fr);
  column-gap: 3mm; margin-top: 1.5mm; }}
.key {{ border: 0.25mm solid var(--line); border-radius: 1.2mm; padding: 0.8mm 1mm; }}
.knob + .knob {{ border-left: 0.25mm solid var(--line); padding-left: 1.5mm; }}
tbody, tr {{ break-inside: avoid; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ text-align: left; vertical-align: top; padding: 0.1mm 0; overflow-wrap: anywhere; }}
th {{ font-weight: normal; white-space: nowrap; padding-right: 1mm; width: 1%; }}
.amber {{ color: var(--amber); }}
.unit {{ color: var(--soft); font-weight: normal; }}
.off {{ color: var(--soft); font-style: italic; }}
ol {{ columns: 3; column-gap: 4mm; margin: 1mm 0 0; padding-left: 3mm; color: var(--soft); }}
footer {{ margin-top: 1mm; border-top: 0.25mm solid var(--line); }}
footer p {{ margin: 0.6mm 0 0; font-weight: bold; }}
</style>
</head>
<body>
<header>
<h1>Avionics Panel: {name}{stamp}</h1>
<p>What each control sets in the MobiFlight profile {html.escape(profile.filename(key))}, as MobiFlight lists the
events and variables. <b class="amber">Amber</b>: with SHIFT. Unit 2: after SHIFT, HOME. A row named for two ways
(↻ / ↺, ▲ / ▼, ◀ / ▶) lists what each sets in that order, A / B; tap / hold: what a key sets let go at once, or held
first. In squawk mode the outer ring picks the digit and sends nothing.</p>
</header>
<section class="keys">
{chr(10).join(cells)}
</section>
<section class="knobs">
{chr(10).join(blocks)}
</section>
<footer>
<p>Why a control does nothing in this profile:</p>
<ol>
{notes}
</ol>
</footer>
</body>
</html>
"""
