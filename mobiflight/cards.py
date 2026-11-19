"""The cards zip (python3 -m mobiflight --cards): the file names of each profile's quick-reference card and cheat
sheet, the panel's (card.py, sheet.py) and the IFR-1's (ifr1_card.py), and the index of them all with each profile's
projects, which the zip holds and the Pages workflow puts at cards/ beside the 3D view
(docs/using/mapping.md#quick-reference-cards).
"""
import html

from mobiflight import card, ifr1, profile

REPO = "https://github.com/saschagrunert/avionics-panel"
# the 3D view on Pages, absolute, as the page opened from the zip has no view beside it
VIEW = "https://saschagrunert.de/avionics-panel/"


def release(tag=None):
    """Where a release's files are: the release tag's, or the latest build's (rolling)"""
    return f"{REPO}/releases/download/{tag or 'rolling'}/"


def docs(tag=None):
    """Where the docs on using the panel are: as of the release tag, or on main"""
    return f"{REPO}/blob/{tag or 'main'}/docs/using/"


def files(key):
    """The file names of a profile's pages in the cards zip and at cards/ of the 3D view: (the panel's card, its cheat
    sheet, the IFR-1's card, its cheat sheet)"""
    return (f"avionics-panel-{key}-card.html", f"avionics-panel-{key}-sheet.svg",
            f"avionics-panel-ifr1-{key}-card.html", f"avionics-panel-ifr1-{key}-sheet.html")


def index(families, version=None, tag=None):
    """The index of the cards zip and of cards/ beside the 3D view, as a page of HTML: for each profile of families
    ({key: family}, in their order) its cheat sheets and cards, for the panel and for the IFR-1, and its projects of
    the release tag, or of the latest build (version: as card.page()'s)"""
    files_at, docs_at, rows = release(tag), docs(tag), []
    for key, family in families.items():
        panel_card, panel_sheet, ifr1_card, ifr1_sheet = files(key)
        rows.append(f'<tr><th>{html.escape(family.NAME)}</th>'
                    f'<td data-head="Panel"><a href="{panel_sheet}">cheat sheet</a> · '
                    f'<a href="{panel_card}">card</a> · <a href="{files_at}{profile.filename(key)}">project</a></td>'
                    f'<td data-head="Octavi IFR-1"><a href="{ifr1_sheet}">cheat sheet</a> · '
                    f'<a href="{ifr1_card}">card</a> · <a href="{files_at}{ifr1.filename(key)}">project</a></td></tr>')
    stamp, title_stamp = card.stamps(version)
    body = "\n".join(rows)
    of = f"the release {html.escape(tag)}" if tag else "the latest build"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Avionics Panel: cards and cheat sheets{title_stamp}</title>
<style>
:root {{ --ink: #1b1b1b; --soft: #6b6b6b; --line: #c9c9c9; --link: #0b57d0; --paper: #ffffff; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --ink: #e6e6e6; --soft: #a0a0a0; --line: #3a3a3a; --link: #8ab4f8; --paper: #1b1c1e; }} }}
* {{ box-sizing: border-box; }}
html {{ background: var(--paper); color: var(--ink); color-scheme: light dark; }}
body {{ margin: 0 auto; max-width: 52rem; padding: 1.5rem 1rem; font: 1rem/1.5 system-ui, sans-serif; }}
h1 {{ font-size: 1.4rem; margin: 0 0 0.5rem; }}
.version {{ font-size: 0.9rem; font-weight: normal; color: var(--soft); }}
p {{ margin: 0 0 1rem; color: var(--soft); }}
a {{ color: var(--link); }}
table {{ border-collapse: collapse; width: 100%; }}
nav {{ margin-top: 1rem; }}
th, td {{ text-align: left; vertical-align: top; padding: 0.5rem 0.75rem 0.5rem 0;
  border-bottom: 1px solid var(--line); }}
thead th {{ border-bottom: 2px solid var(--ink); }}
@media (max-width: 560px) {{ tr {{ display: block; padding: 0.5rem 0; border-bottom: 1px solid var(--line); }}
  thead {{ display: none; }} th, td {{ display: block; border: 0; padding: 0.1rem 0; }}
  td::before {{ content: attr(data-head) ": "; color: var(--soft); }} }}
</style>
</head>
<body>
<h1>Avionics Panel: cards and cheat sheets{stamp}</h1>
<p>For each profile, for the panel and for the Octavi IFR-1: the cheat sheet (what each control does, in plain
words), the card (every event and variable a control sends, as MobiFlight lists them) and the MobiFlight project of
{of}. Open a cheat sheet or card and print it on A4 in landscape. From the zip, extract it first: the pages link each
other, and a page opened inside the zip comes alone.</p>
<table>
<thead><tr><th>Profile</th><th>Panel</th><th>Octavi IFR-1</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
<nav><a href="{VIEW}">3D view</a> · <a href="{docs_at}mapping.md">Profiles</a> ·
<a href="{docs_at}ifr1.md">Octavi IFR-1</a></nav>
</body>
</html>
"""
