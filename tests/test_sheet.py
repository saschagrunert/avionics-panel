"""The aircraft cheat sheets (mobiflight/sheet.py, docs/using/aircraft/): a sheet for every profile, its words held to
the profile's tables, and the SVGs in the docs as the tables make them."""
import math
import os
import re

import pytest

from mobiflight import sheet
from mobiflight.families import FAMILIES
from mobiflight.sheet_text import SHEETS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIRCRAFT = os.path.join(ROOT, "docs", "using", "aircraft")


def test_every_profile_has_a_sheet():
    assert set(SHEETS) == set(FAMILIES)


@pytest.mark.parametrize("key", sorted(FAMILIES))
def test_a_control_has_words_where_the_profile_maps_it(key):
    # every control of the panel has an entry; it is None ("does nothing") where the profile maps none of its
    # buttons in either unit, and words where it maps one; the panel's own (the FREQ knob's mode) always has words.
    # Whether the words are right is for the reader: sheet_text.py writes them from the tables and mapping.md
    texts, _ = SHEETS[key]
    family = FAMILIES[key]
    assert set(sheet.CONTROLS) <= set(texts), sorted(set(sheet.CONTROLS) - set(texts))
    assert not set(texts) - set(sheet.CONTROLS), sorted(set(texts) - set(sheet.CONTROLS))
    for control, buttons in sheet.CONTROLS.items():
        if control in sheet.PANEL_ONLY:
            assert texts[control], control
            continue
        mapped = any(b in family.DEVICE[device] for device in (1, 2) for b in buttons)
        assert (texts[control] is not None) == mapped, (control, texts[control])


@pytest.mark.parametrize("key", sorted(FAMILIES))
def test_a_control_of_one_unit_says_which(key):
    # a control whose buttons both units have, mapped in one unit only, does nothing in the other after SHIFT,
    # HOME: its words name the unit it works in
    texts, family = SHEETS[key][0], FAMILIES[key]
    for control, buttons in sheet.CONTROLS.items():
        both = [b for b in buttons if b in sheet.BM.BUTTON[2]]
        if not both:
            continue
        units = [u for u in (1, 2) if any(b in family.DEVICE[u] for b in both)]
        if len(units) == 1:
            assert f"unit {units[0]}" in texts[control], (control, texts[control])


@pytest.mark.parametrize("key", sorted(FAMILIES))
def test_the_sheets_in_the_docs_are_the_tables(key):
    # docs/using/aircraft/<key>.svg as sheet.svg() makes it now, and a page that shows it
    with open(os.path.join(AIRCRAFT, f"{key}.svg"), encoding="utf-8") as f:
        assert f.read() == sheet.svg(key, sheet.TITLES[key]), "run python3 -m mobiflight --sheets"
    with open(os.path.join(AIRCRAFT, f"{key}.md"), encoding="utf-8") as f:
        assert f"]({key}.svg)" in f.read()


def test_the_words_are_plain():
    # no dashes the docs do not use, and short enough for a box
    for key, (texts, unit2) in SHEETS.items():
        for control, text in [*texts.items(), ("unit 2", unit2)]:
            if text:
                assert not re.search("[–—]", text), (key, control)
                assert len(text) <= 70, (key, control, len(text))


def test_the_command_line_writes_every_sheet(tmp_path):
    from mobiflight import __main__ as cli
    cli.main(["--sheets", str(tmp_path)])
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(f"{key}.svg" for key in FAMILIES)
    with pytest.raises(SystemExit):
        cli.main(["--sheets", str(tmp_path), "--vfr", "1200"])


def segments(points):
    return list(zip(points, points[1:], strict=False))


def near(p, q, c, room):
    """whether the segment p-q passes within room of the point c"""
    (x0, y0), (x1, y1), (cx, cy) = p, q, c
    dx, dy = x1 - x0, y1 - y0
    t = max(0.0, min(1.0, ((cx - x0) * dx + (cy - y0) * dy) / ((dx * dx + dy * dy) or 1)))
    return (x0 + t * dx - cx) ** 2 + (y0 + t * dy - cy) ** 2 < room ** 2


@pytest.mark.parametrize("key", sorted(FAMILIES))
def test_the_layout_keeps_clear(key):
    # every box on the page and below the title, none over another or over the panel; no two leader lines cross,
    # and none runs over a light or the amber legend under a key
    s = sheet.Sheet(key)
    s.svg(sheet.TITLES[key])
    pw, ph = s.plate
    for i, (x, y, w, h) in enumerate(s.boxes):
        assert x >= 0 and x + w <= sheet.W and y >= sheet.TITLE_BOTTOM and y + h <= sheet.H, (key, i)
        assert x + w <= s.x0 or x >= s.x0 + pw or y + h <= s.y0 or y >= s.y0 + ph, (key, i, "over the panel")
        for j, (x2, y2, w2, h2) in enumerate(s.boxes[:i]):
            assert x + w <= x2 or x2 + w2 <= x or y + h <= y2 or y2 + h2 <= y, (key, i, j)
    for i, a in enumerate(s.leads):
        for b in s.leads[:i]:
            assert not sheet.crosses(a, b), (key, a, b)
    g = s.g
    cw, ch = (v * sheet.S for v in g["keys"]["cap"][:2])
    lights = [(s.P(v["x"], v["y"]), v["d"] / 2 * sheet.S) for v in g["lights"].values()]
    legends = [(s.P(g["keys"]["cols"][c], g["keys"]["rows"][r]), amber)
               for r, row in enumerate(sheet.card.caps()) for c, (_, amber, _, _) in enumerate(row) if amber]
    for points in s.leads:
        for p, q in segments(points):
            for c, r in lights:
                assert not near(p, q, c, r + 1), (key, points, "light")
            for (kx, ky), amber in legends:          # the legend's middle, 11 px under the key's front edge
                assert not near(p, q, (kx, ky + ch / 2 + 8), sheet.width(amber, 9) / 2 + 1), (key, points, amber)


@pytest.mark.parametrize("key", sorted(FAMILIES))
def test_every_control_gets_one_line_to_its_edge(key):
    # one leader line to each key and knob, ending on that key's edge or that knob's rim
    s = sheet.Sheet(key)
    s.svg(sheet.TITLES[key])
    g = s.g
    cw, ch = (v * sheet.S for v in g["keys"]["cap"][:2])
    keys = [s.P(x, y) for y in g["keys"]["rows"] for x in g["keys"]["cols"]]
    knobs = [(s.P(k["x"], k["y"]), (g["range_knob"]["skirt_d"] if name == "RANGE" else g["outer_knob"]["d"])
              / 2 * sheet.S) for name, k in g["knobs"].items()]
    hit = []
    for points in s.leads:
        ex, ey = points[-1]
        on_key = [i for i, (kx, ky) in enumerate(keys)
                  if abs(abs(ex - kx) - cw / 2) < 0.5 and abs(ey - ky) <= ch / 2
                  or abs(abs(ey - ky) - ch / 2) < 0.5 and abs(ex - kx) <= cw / 2]
        on_knob = [("knob", i) for i, ((kx, ky), r) in enumerate(knobs) if abs(math.hypot(ex - kx, ey - ky) - r) < 0.5]
        assert len(on_key) + len(on_knob) == 1, (key, points)
        hit += on_key + on_knob
    assert len(hit) == len(set(hit)) == len(keys) + len(knobs), key


@pytest.mark.parametrize("key", sorted(FAMILIES))
def test_the_same_is_the_same(key):
    # a shifted key shown as "the same" sends what its plain key sends, in both units
    texts, family = SHEETS[key][0], FAMILIES[key]
    for row in sheet.card.caps():
        for _, _, plain, shifted in row:
            if plain and shifted and texts[plain] is not None and texts[shifted] == texts[plain]:
                for device in (1, 2):
                    assert family.DEVICE[device].get(plain) == family.DEVICE[device].get(shifted), (plain, device)
