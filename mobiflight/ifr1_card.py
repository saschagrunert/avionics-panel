"""The IFR-1's quick-reference card and cheat sheet of a profile (ifr1.py, docs/using/ifr1.md): one page of HTML each,
to print on A4 in landscape, the card as a grid of the IFR-1's modes and controls (ifr1_grid.Grid), the cheat sheet as
the IFR-1 drawn with a box of words for each control (ifr1_sheet.py, from the same grid with words). Both list why a
control does nothing below. Both pages are self-contained and depend on the profile alone, so the same tables make the
same bytes.
"""
import html

from mobiflight import card, ifr1, ifr1_sheet
from mobiflight.ifr1_grid import TURN, Grid, hold_rules

STYLE = """@page { size: A4 landscape; margin: 7mm; }
:root { --ink: #1b1b1b; --soft: #6b6b6b; --line: #c9c9c9; --paper: #ffffff; }
* { box-sizing: border-box; }
html { background: var(--paper); color: var(--ink); color-scheme: light; }
body { margin: 0 auto; width: 283mm; padding: 0; font: 6pt/1.2 "Barlow Semi Condensed", "Roboto Condensed",
  "Arial Narrow", "Liberation Sans Narrow", Arial, sans-serif; -webkit-print-color-adjust: exact;
  print-color-adjust: exact; }
header { display: flex; justify-content: space-between; align-items: baseline; gap: 4mm;
  border-bottom: 0.4mm solid var(--ink); margin-bottom: 1.5mm; }
h1 { font-size: 11pt; margin: 0; white-space: nowrap; }
h2 { font-size: 7.5pt; margin: 1.5mm 0 0.5mm; }
.version { font-size: 7pt; font-weight: normal; color: var(--soft); }
header p { margin: 0; color: var(--soft); text-align: right; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: 0.4mm 1mm; border-bottom: 0.25mm solid var(--line);
  overflow-wrap: anywhere; }
thead th { font-weight: bold; border-bottom: 0.4mm solid var(--ink); }
tbody th { font-weight: bold; }
col.head { width: 20mm; }
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
              f". A ring lists clockwise / counter-clockwise where they differ. {hold_rules()}")
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
