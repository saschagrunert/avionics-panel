"""The grid of an IFR-1 profile's controls, which its quick-reference card and cheat sheet print (ifr1_card.py,
ifr1_sheet.py): what each ring, push and key sends, as MobiFlight lists the item (profile.label()) or in a few words
(the panel's cheat sheet words, sheet_text.SHEETS, for the panel button it sends, words of its own for the rings the
IFR-1 turns otherwise than the panel, words_of(), and an Own code's name for code no panel button sends), "nothing"
and the number of its reason for a control that sends nothing; and the rules of ⇆ and of a held key both pages state.
"""
import html

from mobiflight import card, ifr1, profile, sheet
from mobiflight.families import FAMILIES
from mobiflight.sheet_text import SHEETS


def listed(names):
    """names in words, as a, b and c"""
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def hold_rules():
    """⇆ and a key with a hold, as both pages say it, from ifr1's modes and delays"""
    hold, talk = f"{ifr1.HOLD_MS / 1000:g} s", f"{ifr1.TALK_MS / 1000:g} s"
    return (f"⇆ in {listed(ifr1.MODIFIED)}, held while turning a ring (press ⇆ first, then turn): the ring does what "
            "follows \"⇆ held\", and ⇆ sends nothing; otherwise ⇆ sends its tap when let go, however long it was "
            f"held. A key with a hold sends its tap when let go, and its hold at once when held {hold}; ⇆ in COM1 "
            f"and COM2 its hold when let go after {hold}, and its {talk} hold at once.")


# the modes as rows: (MobiFlight's name, title), the shifted ones by the legend under their mode key
MODES = (("COM1", "COM1"), ("COM2", "COM2"), ("NAV1", "NAV1"), ("NAV2", "NAV2"), ("FMS1", "FMS1"), ("FMS2", "FMS2"),
         ("AP", "AP"), ("XPDR", "XPDR"), ("COM1^", "HDG (COM1 shifted)"), ("COM2^", "BARO (COM2 shifted)"),
         ("NAV1^", "CRS1 (NAV1 shifted)"), ("NAV2^", "CRS2 (NAV2 shifted)"), ("XPDR^", "MODE (XPDR shifted)"))
# the keys as rows: (title, FMS1's and FMS2's key, the bottom row's key in the other modes)
KEYS = (("DCT", "DCT", None), ("MENU", "MENU", None), ("CLR", "CLR", None), ("ENT", "ENT", None),
        ("AP / CDI", "CDI", "AP"), ("HDG / OBS", "OBS", "HDG"), ("NAV / MSG", "MSG", "NAV"),
        ("APR / FPL", "FPL", "APR"), ("ALT / VNAV", "VNAV", "ALT"), ("VS / PROC", "PROC", "VS"))
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
    return next(p.NAME for p in family.PIECES if p.KIND == "navigator" and (unit,) == p.UNITS)


def _radio(device, kind):
    return {f"{kind}_MHZ_UP": f"{kind} {device} MHz", f"{kind}_KHZ_UP": f"{kind} {device} kHz",
            f"{kind}_SWAP": f"{kind} {device} flip-flop"}


def words_of(key):
    """{(device, panel button): words} for the IFR-1's rows of this profile: the panel's cheat sheet words of the
    control the button belongs to (sheet.CONTROLS), the rings the IFR-1 turns otherwise than the panel by its own
    words; a ring's own words under its _UP name stand for its _DN too"""
    texts, _ = SHEETS[key]
    family = FAMILIES[key]
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
        (1, "ALT_100_UP"): "selected altitude 100 ft", (1, "ALT_1000_UP"): "selected altitude 1000 ft",
        (1, "PANEL_LT_UP"): texts["PANEL"], (1, "FLOOD_LT_UP"): texts["FLOOD"],
    }
    for (device, button), text in own.items():
        out[device, button] = text
        if button.endswith("_UP"):                           # the other way, in the same words
            out[device, button.removesuffix("_UP") + "_DN"] = text
    return out


class Grid(card.Reasons):
    """The grid of a profile's IFR-1 controls; knob(), key() and push() give a cell's text as HTML from the Uses of
    its buttons (a ring's one per way: ↻ then ↺), the reasons of what sends nothing numbered as they come"""

    def __init__(self, ifr1_profile, words=False):
        super().__init__()
        self.p = ifr1_profile
        self.words = words_of(ifr1_profile.KEY) if words else None

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
        return html.escape(card.describe(use.entry))

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
        return "; ".join(parts)

    def key(self, button):
        """A key's cell: its press, or its tap and its hold"""
        if button in self.p.UNMAPPED:
            return self.nothing(self.p.UNMAPPED[button])
        used = self.p.USES[button]
        if "tap" in used:                                    # ⇆ as a modifier: a tap alone (ifr1.AP_VS_HOLD)
            tap = self.say(used["tap"], at_once=True)
            return f"<i>tap:</i> {tap}" if tap else '<span class="off">only held while turning a ring</span>'
        key, hold, longer = used.get("key"), used.get("hold"), used.get("long_hold")

        def sends(u):                                        # a hold that does more than the tap
            return u is not None and u.entry is not None and (key is None or u.entry != key.entry)
        if longer is not None and not sends(hold):           # the longer hold in its place (ifr1.holds())
            hold, longer = longer, None
        if not sends(hold):
            return self.say(key)
        tap = self.say(key, at_once=True) if key is not None and key.entry is not None else None
        parts = [f"<i>tap:</i> {tap}" if tap else None, f"<i>hold:</i> {self.say(hold, at_once=True)}"]
        if sends(longer):
            parts.append(f"<i>hold {ifr1.TALK_MS / 1000:g} s:</i> {self.say(longer, at_once=True)}")
        return "; ".join(p for p in parts if p)

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
                title = f"{title}: {unit_name(FAMILIES[self.p.KEY], unit)}"
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
