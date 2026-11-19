"""The quick-reference cards (mobiflight/card.py): every control of the panel on each profile's card, once, under
the panel's legends, with what its buttons set or the reason they set nothing; a self-contained page of one A4
sheet in landscape; and the zip of the cards, the same bytes each time."""
import html
import os
import re
import zipfile
from html.parser import HTMLParser

import buttonmap as BM
import panel as P
import pytest

from mobiflight import __main__ as cli
from mobiflight import card, cards, ifr1, ifr1_card, profile, sheet, sheet_text
from mobiflight.families import FAMILIES

FAMILY = pytest.mark.parametrize("key", sorted(FAMILIES))


@pytest.fixture(autouse=True)
def unstamped(monkeypatch):
    # the command line's default stamp is the commit of firmware/version.py, which git archive fills in: none, as
    # in a git checkout, so the cards read the same in an archive too
    monkeypatch.setattr(profile, "VERSION", None)


def rows():
    """[(shifted, title, [button, ...])] of every key and knob as the card has them"""
    out = []
    for keyrow in card.caps():
        for legend, amber, plain, shifted in keyrow:
            if plain:
                out.append((False, legend, [plain]))
            if shifted:
                out.append((True, amber or "SHIFT", [shifted]))
    for _, _, knob in card.knobs():
        out += knob
    return out


def test_the_card_has_every_button_once():
    # the keys and the knobs' rows together are device 1's buttons, each once; device 2's are among them, as
    # unit 2's lines
    buttons = [b for _, _, names in rows() for b in names]
    assert sorted(buttons) == sorted(BM.DEVICE[1])
    assert set(BM.DEVICE[2]) <= set(buttons)


def test_mapping_md_links_the_web_card_of_every_profile():
    # the Pages workflow puts the cards at cards/ beside the view
    with open(os.path.join(profile.HERE, "..", "docs", "using", "mapping.md"), encoding="utf-8") as f:
        text = f.read()
    for key in FAMILIES:
        url = f"https://saschagrunert.de/avionics-panel/cards/avionics-panel-{key}-card.html"
        assert f"[card-{key}]: {url}\n" in text and f"][card-{key}]" in text, key


def test_the_cards_name_the_keys_as_the_simulator_does():
    import sim

    legends = [label for row in card.stack().KEY_LEGENDS for label, _ in row]
    assert [card.key_name(label) for label in legends] == [sim.key_name(label) for label in legends]


def test_the_card_uses_the_panels_legends():
    # the keys in the panel's order, by their caps' legends and their amber legends; the knobs by their legends'
    # words (SHIFT sends nothing of its own, and HOME with SHIFT is UNIT)
    keys = card.caps()
    assert [[legend for legend, _, _, _ in row] for row in keys] == [[c for c, _ in r]
                                                                     for r in card.stack().KEY_LEGENDS]
    for row in keys:
        for legend, _, plain, shifted in row:
            if legend in ("SHIFT", "HOME"):
                assert shifted is None and (plain is None) == (legend == "SHIFT"), legend
                continue
            assert plain in BM.BUTTON[1] and shifted == BM.shifted(plain), legend
    titles = " ".join([title for _, title, _ in rows()] + [f"{t} {a}" for t, a, _ in card.knobs()])
    words = set()
    for legends in card.stack().KNOB_LEGENDS.values():
        for legend in filter(None, legends):
            words |= set(card.words(legend))
            for word in card.words(legend):
                assert word in titles, word
    # each knob's title and amber title are its legends' ring words, none typed on their own
    for title, amber, _ in card.knobs():
        for part in filter(None, (*title.split("/"), *(amber or "").split("/"))):
            assert part in words, part


# Each knob row's head and buttons, written out here rather than taken from card.knobs(): a row that names one ring
# or push and lists another's buttons fails. A ring's two ways: _UP/_DN, or _CW/_CCW, or for a tilt as titled.
TURN = ("_UP", "_DN")
KNOB_ROWS = {
    "ALT, outer": ("ALT_100", TURN), "ALT, quick turn": ("ALT_1000", TURN), "HDG, inner": ("HDG_1", TURN),
    "HDG, quick turn": ("HDG_10", TURN), "PUSH SYNC": ("HDG_SYNC", ("",)), "BARO, outer": ("BARO", TURN),
    "CRS, inner": ("CRS_1", TURN), "CRS, quick turn": ("CRS_10", TURN), "PUSH STD": ("BARO_STD", ("",)),
    "RANGE ↻": ("RANGE", ("_CW", "_CCW")), "tilt ▲": ("PAN", TURN), "tilt ◀": ("PAN", ("_LEFT", "_RIGHT")),
    "PUSH PTR": ("PTR", ("",)), "COM, outer": ("COM_MHZ", TURN), "COM, inner": ("COM_KHZ", TURN),
    "NAV, outer": ("NAV_MHZ", TURN), "NAV, inner": ("NAV_KHZ", TURN), "ADF, outer": ("ADF_100", TURN),
    "ADF, inner": ("ADF_1", TURN), "ADF, quick turn": ("ADF_10", TURN), "PUSH COM/NAV/ADF": ("FREQ_PUSH", ("",)),
    **{f"SQUAWK digit {d}": (f"SQK_D{d}", TURN) for d in range(1, 5)}, "PUSH XPDR": ("XPDR_MODE", ("",)),
    "outer ↻": ("FMS_OUTER", ("_CW", "_CCW")), "inner ↻": ("FMS_INNER", ("_CW", "_CCW")),
    "PUSH CRSR": ("FMS_CRSR", ("",)), "PANEL, outer": ("PANEL_LT", TURN), "FLOOD, inner": ("FLOOD_LT", TURN),
    "PUSH CABIN": ("CABIN_LT", ("",)),
}
SAME_TITLE_SHIFTED = ("RANGE", "PAN", "PTR")   # RANGE's rows keep their titles with SHIFT: their buttons get S_


def test_each_row_names_its_own_buttons():
    # the keys' rows by the caps' legends (stack.KEY_LEGENDS, not card.caps()), plain and amber; the knobs' rows
    # by KNOB_ROWS
    expected = []
    for row in card.stack().KEY_LEGENDS:
        for name in (card.key_name(legend) for legend, _ in row):
            if name != "SHIFT":
                expected.append((False, [name]))
            if name not in ("SHIFT", "HOME"):
                expected.append((True, [BM.shifted(name)]))
    got = rows()
    assert [(s, b) for s, _, b in got[:len(expected)]] == expected
    for shifted, title, buttons in got[len(expected):]:
        stem, ways = next(KNOB_ROWS[h] for h in KNOB_ROWS if title.startswith(h))
        prefix = "S_" if shifted and stem in SAME_TITLE_SHIFTED else ""
        assert buttons == [prefix + stem + way for way in ways], (title, buttons)


@FAMILY
def test_each_row_shows_its_own_buttons(key):
    # row by row, in the card's order: the legend in its head, and in its line what its own buttons set (each
    # label of their codes) or "nothing"; unit 2's line "the same" or what device 2's buttons set. So a row that
    # showed another key's or ring's buttons fails, not only a label missing from the whole page.
    family = FAMILIES[key]
    bodies = [b for b in re.findall(r"<tbody>(.*?)</tbody>", card.page(family, key), re.S)
              if "tap, then a key or knob" not in b and "unit 1 or 2, in the panel" not in b]
    expected = rows()
    assert len(bodies) == len(expected)
    for body, (_, title, buttons) in zip(bodies, expected, strict=True):
        lines = [(html.unescape(re.sub(r"<[^>]+>", "", th)), html.unescape(td))
                 for th, td in re.findall(r"<tr><th>(.*?)</th><td>(.*?)</td></tr>", body)]
        assert title in lines[0][0], (title, lines)
        devices = (1, 2) if all(b in BM.BUTTON[2] for b in buttons) else (1,)
        assert len(lines) == len(devices), (title, lines)
        for device, (_, text) in zip(devices, lines, strict=True):
            if device == 2 and text == "the same":
                sends = [[profile.actions(family.DEVICE[d][b]) if b in family.DEVICE[d] else family.UNMAPPED[d][b]
                          for b in buttons] for d in (1, 2)]
                assert sends[0] == sends[1], (title, buttons)
                continue
            for button in buttons:
                entry = family.DEVICE[device].get(button)
                if entry is None:
                    assert "nothing" in text, (device, button, text)
                for code in profile.actions(entry).values() if entry is not None else ():
                    assert profile.label(code) in text, (device, button, text)


def test_the_freq_push_row_says_a_hold_returns_to_com():
    # the push sends FREQ_PUSH, which no profile maps: the panel's own hold to COM is all it does but cycle; the
    # times the card and the cheat sheets name are the firmware's
    assert f"{P.FREQ_HOLD_MS // 1000} s" == card.FREQ_HOLD and f"{P.LOCK_MS // 1000} s" == card.LOCK
    assert f"held alone {card.LOCK}: locked" in card.page(FAMILIES["g1000"], "g1000")
    assert f"held {card.LOCK}: locked" in sheet_text.SHIFT
    assert sheet_text.RADIOS["FREQ_PUSH"].endswith(f"held {card.FREQ_HOLD}: COM")
    assert f"held {card.FREQ_HOLD}: COM" in card.page(FAMILIES["g1000"], "g1000")


def test_a_row_of_two_buttons_is_a_turn_or_a_tilt_both_ways():
    # the first button clockwise, up or left, the second the other way, as the title's arrows give them
    for _, title, names in rows():
        if len(names) == 2:
            first, second = names
            assert re.search(r"_(UP|CW|LEFT)$", first) and re.search(r"_(DN|CCW|RIGHT)$", second), names
            assert first.rsplit("_", 1)[0] == second.rsplit("_", 1)[0], names
            assert ("◀ / ▶" in title) == first.endswith("_LEFT") and ("▲ / ▼" in title) == first.startswith(
                ("PAN_UP", "S_PAN_UP")), title


class Page(HTMLParser):
    """The tags of a page, checked to close in order, and its text"""
    VOID = {"meta", "br"}

    def __init__(self):
        super().__init__()
        self.open, self.tags, self.text = [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag not in self.VOID:
            self.open.append(tag)

    def handle_endtag(self, tag):
        assert self.open.pop() == tag

    def handle_data(self, data):
        self.text.append(data)


def parse(text):
    page = Page()
    page.feed(text)
    page.close()
    assert not page.open
    return page


@FAMILY
def test_the_card_says_what_each_button_sets(key):
    # each mapped button by what it sets, as MobiFlight lists it; each unmapped one by its reason, numbered
    family = FAMILIES[key]
    text = card.page(family, key)
    found = " ".join(parse(text).text)
    for device in (1, 2):
        for button, entry in family.DEVICE[device].items():
            for code in profile.actions(entry).values():             # (tap and hold apart)
                assert profile.label(code) and profile.label(code) in found, (device, button)
        for reason in family.UNMAPPED[device].values():
            assert f">{html.escape(reason)}</li>" in text, reason
    notes = re.findall(r'<li value="([0-9]+)">', text)
    assert notes == [str(n) for n in range(1, len(notes) + 1)]
    used = {int(n) for n in re.findall(r"nothing<sup>([0-9]+)</sup>", text)}
    assert used == set(range(1, len(notes) + 1))
    assert f"<title>Avionics Panel: {html.escape(family.NAME)}, card</title>" in text
    assert f"avionics-panel-{key}.mfproj" in text


def test_unit_2_shows_device_2s_buttons():
    # CLR in the G1000 profile: the MFD's in unit 1, the PFD's in unit 2; COM ⇆ the radio of its unit; a control
    # that sets the same in both units says so
    c = card.Card(FAMILIES["g1000"])
    assert c.lines(["CLR"]) == [(1, "AS1000_MFD_CLR"), (2, "AS1000_PFD_CLR")]
    assert c.lines(["COM_SWAP"]) == [(1, "COM1_RADIO_SWAP"), (2, "COM2_RADIO_SWAP")]
    assert c.lines(["ADF_1_UP", "ADF_1_DN"]) == [(1, "ADF_1_INC / ADF_1_DEC"), (2, "the same")]
    assert c.lines(["AP"]) == [(1, "AP_MASTER")]
    assert c.lines(["TEST"]) == [(1, '<span class="off">nothing<sup>1</sup></span>')]
    assert c.lines(["PANEL_LT_UP", "PANEL_LT_DN"]) == [(1, '<span class="off">nothing<sup>2</sup></span>')]
    assert c.lines(["GPSS", "TEST"]) == [(1, '<span class="off">nothing<sup>3</sup></span> / '
                                             '<span class="off">nothing<sup>1</sup></span>')]
    # HOME in the GTN profile: the same event, but for the unit's GTN by its number, so not "the same"
    assert card.Card(FAMILIES["gtn"]).lines(["HOME"]) == [(1, "GPS_MENU_BUTTON"), (2, "GPS_MENU_BUTTON")]


def test_a_key_tapped_or_held_says_which():
    # SHIFT, UP in the Bonanza: the EDM 800's left button, tapped or held
    assert card.Card(FAMILIES["black-square-bonanza"]).one(1, "S_UP") == (
        "tap: bksq_JpiButton_1_L_Short; hold: bksq_JpiButton_1_L_Long", False)


def test_a_key_pressed_and_released_says_what_the_release_does():
    # TEST in the Bonanza: the press starts the KFC 150's test (and the MD41's lamp test), the release lets go of
    # the lamp test
    family = FAMILIES["black-square-bonanza"]
    acts = profile.actions(family.DEVICE[1]["TEST"])
    assert card.Card(family).one(1, "TEST") == (
        f"{profile.label(acts['onPress'])}; release: {profile.label(acts['onRelease'])}", False)


def test_the_title_names_the_commit():
    # as the profile's name does: none in a git checkout
    family = FAMILIES["g1000"]
    plain, stamped = card.page(family, "g1000", None), card.page(family, "g1000", "2026-11-14, abc1234")
    assert "<h1>Avionics Panel: G1000 NXi</h1>" in plain and "<title>Avionics Panel: G1000 NXi, card</title>" in plain
    assert '<h1>Avionics Panel: G1000 NXi <span class="version">(2026-11-14, abc1234)</span></h1>' in stamped
    assert "<title>Avionics Panel: G1000 NXi, card (2026-11-14, abc1234)</title>" in stamped     # the printout's header


@FAMILY
def test_the_card_is_one_self_contained_page(key):
    # no scripts, styles, fonts or pictures from elsewhere, a light page, A4 in landscape
    text = card.page(FAMILIES[key], key)
    page = parse(text)
    assert {tag for tag, _ in page.tags} <= {"html", "head", "meta", "title", "style", "body", "header", "h1", "p",
                                            "b", "section", "div", "table", "tbody", "tr", "th", "td", "span",
                                            "sup", "h3", "footer", "ol", "li"}
    assert not re.search(r"https?:|url\(|@import|src=|href=", text)
    assert "@page { size: A4 landscape;" in text and "color-scheme: light" in text
    assert "prefers-color-scheme" not in text and text.startswith("<!doctype html>")
    assert "\u2014" not in text and "\u2013" not in text       # no dashes, as in the docs


def test_the_command_writes_the_cards_of_every_profile(tmp_path):
    out, again = tmp_path / "cards.zip", tmp_path / "again.zip"
    cli.main(["--cards", str(out)])
    cli.main(["--cards", str(again)])
    assert out.read_bytes() == again.read_bytes()                 # the same profiles make the same zip
    with zipfile.ZipFile(out) as z:
        # each profile's card, then its cheat sheet (mobiflight/sheet.py), then the IFR-1's (mobiflight/ifr1_card.py),
        # then the index of them all, the profiles in one order
        assert z.namelist() == [name for key in sorted(FAMILIES) for name in cards.files(key)] + ["index.html"]
        assert z.read("index.html").decode() == cards.index(dict(sorted(FAMILIES.items())))
        for key, family in FAMILIES.items():
            panel_card, panel_sheet, one_card, one_sheet = cards.files(key)
            assert z.read(panel_card).decode() == card.page(family, key), key
            assert z.read(panel_sheet).decode() == sheet.svg(key, sheet.TITLES[key]), key
            one = ifr1.build(key)
            assert z.read(one_card).decode() == ifr1_card.page(one), key
            assert z.read(one_sheet).decode() == ifr1_card.page(one, words=True), key
        assert {info.date_time for info in z.infolist()} == {cli.STAMP}
        assert {info.external_attr >> 16 for info in z.infolist()} == {0o644}


def test_the_index_links_every_page_and_project_of_every_profile():
    page = cards.index(FAMILIES, "v1")
    for key, family in FAMILIES.items():
        assert html.escape(family.NAME) in page, key
        for name in cards.files(key):
            assert f'href="{name}"' in page, name
        for project in (profile.filename(key), ifr1.filename(key)):     # the latest build's
            assert f'href="{cards.REPO}/releases/download/rolling/{project}"' in page, project
    assert "<title>Avionics Panel: cards and cheat sheets (v1)</title>" in page and "(v1)" not in cards.index(FAMILIES)
    parse(page)                                                 # every tag closed in order
    assert "\u2014" not in page and "\u2013" not in page
    # the way back to the view and the docs it names, which exist, and link the page on Pages
    assert f'<a href="{cards.VIEW}">3D view</a>' in page
    for doc in ("mapping.md", "ifr1.md"):
        assert f'href="{cards.REPO}/blob/main/docs/using/{doc}"' in page
        with open(os.path.join(profile.HERE, "..", "docs", "using", doc), encoding="utf-8") as f:
            assert f"]: {cards.VIEW}cards/\n" in f.read(), doc


def test_a_releases_index_links_its_own_projects_and_docs(tmp_path):
    # the zip a tagged release carries: its projects and its docs, not the latest build's
    out = tmp_path / "cards.zip"
    cli.main(["--cards", str(out), "--tag", "v1.0"])
    with zipfile.ZipFile(out) as z:
        page = z.read("index.html").decode()
    assert f"{cards.REPO}/releases/download/v1.0/{ifr1.filename('g1000')}" in page and "/rolling/" not in page
    assert f"{cards.REPO}/blob/v1.0/docs/using/ifr1.md" in page and "/blob/main/" not in page
    assert "the MobiFlight project of\nthe release v1.0." in page
    with pytest.raises(SystemExit):
        cli.main(["--family", "g1000", "--tag", "v1.0"])         # for the cards alone
    # a tag with characters a URL or HTML takes otherwise, as git allows them, reaches the links quoted and the page
    # escaped
    page = cards.index(FAMILIES, tag='v1#&"')
    assert f"{cards.REPO}/releases/download/v1%23%26%22/" in page and f"{cards.REPO}/blob/v1%23%26%22/docs/" in page
    assert 'v1#&"' not in page and "the release v1#&amp;&quot;." in page


def test_the_cards_take_the_stamp_as_the_profiles(tmp_path):
    out = tmp_path / "cards.zip"
    cli.main(["--cards", str(out), "--stamp", "test1"])
    with zipfile.ZipFile(out) as z:
        assert z.read("avionics-panel-g1000-card.html").decode() == card.page(FAMILIES["g1000"], "g1000", "test1")
        assert ">G1000 NXi (test1)</text>" in z.read("avionics-panel-g1000-sheet.svg").decode()


def test_a_failed_write_leaves_no_cards(tmp_path, monkeypatch):
    # as a project that fails to write: no zip with some cards
    def fail(family, key, version):
        if key == "gns":
            raise ValueError("no card")
        return "card"
    monkeypatch.setattr(card, "page", fail)
    with pytest.raises(SystemExit):
        cli.main(["--cards", str(tmp_path / "cards.zip")])
    assert not os.listdir(tmp_path)


def test_any_failure_leaves_a_file_there_as_it_was(tmp_path, monkeypatch):
    # an error of any kind while the cards are made (a table without a button, say): the zip there stays, and no
    # new file is left
    out = tmp_path / "cards.zip"
    out.write_bytes(b"old")

    def fail(family, key, version):
        raise KeyError("FREQ_PUSH")
    monkeypatch.setattr(card, "page", fail)
    with pytest.raises(KeyError):
        cli.main(["--cards", str(out)])
    assert os.listdir(tmp_path) == ["cards.zip"] and out.read_bytes() == b"old"


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="a read-only file is writable on Windows' terms here, and for root")
def test_a_read_only_file_there_is_refused_and_kept(tmp_path):
    out = tmp_path / "cards.zip"
    out.write_bytes(b"old")
    out.chmod(0o444)
    with pytest.raises(SystemExit):
        cli.main(["--cards", str(out)])
    assert os.listdir(tmp_path) == ["cards.zip"] and out.read_bytes() == b"old"


@pytest.mark.parametrize("args", [
    ["--cards", "x.zip", "--cockpit", "g1000"],
    ["--cards", "x.zip", "-o", "y.html"],
    ["--cards", "x.zip", "--vfr", "1200"],
    ["--cards", "x.zip", "--serials", "JS-x", "JS-y"],
    ["--cards", "x.zip", "--family", "g1000"],
    ["--cards", "missing/x.zip"],
])
def test_command_line_errors_with_cards(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cli.main(args)
    assert not os.listdir(tmp_path)


# ---------------- printed ----------------
CALL_MS = 60_000                 # a browser call that takes longer fails


@pytest.fixture(scope="module")
def pdf_pages(tmp_path_factory):
    """The pages a card prints on, A4 landscape by its own @page, in headless Chromium (Playwright, as
    tests/test_simjs.py), as found and with Arial for its condensed fonts, as on a PC that has none"""
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        missing("no Playwright for Python")
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(timeout=CALL_MS)
    except Error as e:
        playwright.stop()
        missing(f"Playwright for Python has no Chromium: {str(e).splitlines()[0]}")
    page, folder = browser.new_page(), tmp_path_factory.mktemp("cards")
    page.set_default_timeout(CALL_MS)                    # a hung Chromium fails the test, not the suite

    def pages(name, text, font=None):
        path = folder / name
        path.write_text(text, encoding="utf-8")
        page.goto(path.as_uri())
        if font:
            page.add_style_tag(content=f"body {{ font-family: {font} !important; }}")
        return len(re.findall(rb"/Type\s*/Page[^s]", page.pdf(prefer_css_page_size=True)))
    yield pages
    browser.close()
    playwright.stop()


def missing(why):
    """as tests/test_simjs.py's: a skip without a browser, a failure where the shell must have one"""
    if os.environ.get("REQUIRE_BROWSER"):
        pytest.fail(f"{why}, and REQUIRE_BROWSER is set")
    pytest.skip(why)


@pytest.mark.parametrize("key", sorted(FAMILIES))
def test_every_card_prints_on_one_page(pdf_pages, key):
    # the panel's card and the IFR-1's card and cheat sheet, in their condensed fonts and in Arial: a long label or
    # a profile of much text (the Bonanza's) must not spill onto a second page
    panel_card, _, ifr1_card_name, ifr1_sheet = cards.files(key)
    one = ifr1.build(key)
    for name, text in ((panel_card, card.page(FAMILIES[key], key, "v")), (ifr1_card_name, ifr1_card.page(one, "v")),
                       (ifr1_sheet, ifr1_card.page(one, "v", words=True))):
        for font in (None, "Arial"):
            assert pdf_pages(name, text, font) == 1, (name, font)
