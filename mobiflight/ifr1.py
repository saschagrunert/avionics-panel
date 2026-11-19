"""The Octavi IFR-1's MobiFlight profiles, made from the panel's (docs/using/ifr1.md): for every profile of
families.FAMILIES, a project for the IFR-1 that sends what the panel's buttons send in that profile.

MobiFlight reads the IFR-1 itself (src/MobiFlightConnector/MobiFlight/Joysticks/Octavi/ in its repository at 11.3.1:
OctaviHandler.cs, Octavi.cs, and Joysticks/octavi/octavi.joystick.json). The device keeps one of eight modes, which its
mode keys select, and reports it with every input; MobiFlight turns each input into one of 96 named buttons (BUTTONS) by
that mode and a shift of its own, which the knob push toggles in COM1, COM2, NAV1, NAV2 and XPDR and every change of
mode ends (sending Button_UNSHIFT_SW). Its keys send a press and a release, and (MobiFlight 11.2 on) a release after a
hold (onLongRelease) and a hold while still down (onHold), each after a delay of the item's; a knob sends one press per
detent and nothing else. Its six AP lights each take 0 or 1 (LEDS): MobiFlight shifts the value into the lights' byte as
it is, so a 2 would light the next light too.

Every IFR-1 button sends what a panel button sends in the profile (uses(): Panel sources, by the table TABLE), with
these rules over it:

- ⇆ in FMS1, FMS2, AP and XPDR is a modifier of its mode's knob (MODIFIED): pressed, it sets the mode's L: variable;
  a detent while it is held sends the knob's held code; let go without a detent between, it sends its tap, however
  long it was held; then it clears the variable. It has no hold: a detent that comes with its press goes out without
  it, and ⇆ let go would send the hold (AP_VS_HOLD). The state lives in L: variables of the IFR-1's own (STATE), as the
  panel keeps its own, so the two devices can fly together.
- A key with a hold (an amber function of AMBER of its panel key, HOLDS, MODE's cabin light, the profile's EXTRA, or VNV
  on the AP knob's push) sends its hold at once when held HOLD_MS, while still down, and its plain function on a tap, on
  its release; every other key sends on press as the panel's does, a key of TDS's GTN its key-up on release. ⇆ in COM1
  and COM2 sends its hold, the panel's COM 1 or COM 2 audio, when let go after HOLD_MS, and a longer one, its MIC 1 or
  MIC 2 (TALK), at once after TALK_MS. A hold of two steps (the KAP 140's VNV) sends its first at once and its second
  when let go after it.
- MobiFlight sends a release to the button of the mode the IFR-1 is in by then, and Button_UNSHIFT_SW on every change
  of mode and on leaving shift. That button lets go of every ⇆ and every key with a hold (clear()), so one let go,
  or still held, after a change of mode sends nothing, and a GTN key sends its key-up only from the button that sent
  its key-down. Button_SHIFT_SW, on entering shift, lets go of ⇆ in the modes with a shift (clear(shifting=True)),
  whose release reaches the shifted button, so a hold of COM1 or COM2 sends nothing in HDG or BARO.
- A panel button the profile leaves unmapped leaves the IFR-1's unmapped too, with the profile's reason.

The layers: the AP rings set the selected altitude 1000 ft (outer) and 100 ft (inner), with ⇆ held the inner ring the
panel's UP and DN and the outer ring AP_COARSE of them at once (a Times source); XPDR's rings the squawk two digits
each, with ⇆ held the panel and flood dimmers; MODE (XPDR shifted) the transponder's mode, ALT one way and standby the
other (transponder_mode()), its ⇆ the VFR code. In every profile ⇆ held in NAV1 and NAV2 is the panel's NAV 1 and NAV 2
audio, in CRS1 the simulator's marker audio event, in CRS2 the panel's DME audio and in BARO the simulator's pitot heat
event (HOLDS); with ⇆ held in FMS1 and FMS2, TDS's GTN's outer ring is its volume, and its MENU, CLR and ENT, without ⇆,
the volume up, down and push (tds_gtn()). Per profile, EXTRA puts IFR-1 uses of their own over the panel's (Plus and Own
sources): in the Black Square Bonanza TDS's GTN volume beside the GNS's, KLN 90B's and PMS50's keys of FMS1, each
navigator's range or volume on the outer ring with ⇆ held, the HSI's course with the heading bug, GPSS on NAV held, and
the cockpit's self-test, EDM 800, DME selector, oxygen, tip tanks, prop heat, fuel pump and air conditioner on keys of
FMS2 (bonanza_extra()); in the COWS DA40 and the C182T their fuel pump, and the NG DA40's fuel transfer pump, on keys of
FMS2 held (da40_extra(), c182t_extra()).

New code, which no panel button sends (Own sources): the squawk's digits in pairs (squawk_pair), NAV 2's course
(NAV2_COURSE), the transponder's mode one way (transponder_mode()), the modifier (held(), knob()), the marker audio and
pitot heat (HOLDS), the buttons that let go of the held keys (clear()) and the aircraft's own codes of EXTRA. project()
writes the project.
"""
import re
import uuid
from collections import namedtuple
from types import SimpleNamespace

from mobiflight import profile
from mobiflight.families import FAMILIES, black_square_bonanza, parts
from mobiflight.families.rpn import k, lset, turn

BM = profile.BM

# ---------------- the device, as MobiFlight 11.3.1 names it ----------------
NAME = "IFR1"                    # its DirectInput instance name, which MobiFlight binds a project's controller by
# the serial Octavi's registry fix gives it (Octavi_GUID_fix.reg); MobiFlight 11's auto binder binds the project to
# the one IFR-1 connected whatever its own (ControllerAutoBinder.cs), so the fix is not needed
SERIAL = "JS-096db160-8ba2-11ed-8002-444553540000"
MODES = ("COM1", "COM2", "NAV1", "NAV2", "FMS1", "FMS2", "AP", "XPDR")
SHIFTED = ("COM1", "COM2", "NAV1", "NAV2", "XPDR")    # the modes with a shift (octavi.joystick.json's Inputs)
KNOB = ("OI", "OD", "II", "ID")                       # outer ↻, outer ↺, inner ↻, inner ↺
FMS_KEYS = ("DCT", "MENU", "CLR", "ENT", "CDI", "OBS", "MSG", "FPL", "VNAV", "PROC")
AP_ROW = ("AP", "HDG", "NAV", "APR", "ALT", "VS")     # the bottom row, outside FMS1 and FMS2
# the AP lights, by their labels, which an output names as its Pin (Joystick.SetOutputDeviceState matches the label);
# octavi.joystick.json's seventh, "Auto Blink Context", is MobiFlight's own: it writes its shift there
LIGHTS = ("AP Master", "AP HDG", "AP NAV", "AP APR", "AP ALT", "AP VS")


def buttons():
    """The 96 buttons in MobiFlight's order, as OctaviHandler's constructor makes them: SHIFT_SW and UNSHIFT_SW; then
    each mode and each shifted mode (COM1^ and so on): its knob and ⇆ (TOG), its push (CRSR) where it has no shift,
    FMS1's and FMS2's keys, AP's bottom row; the bottom row, already made, for every other mode"""
    out = ["Button_SHIFT_SW", "Button_UNSHIFT_SW"]
    for name in (*MODES, *(f"{m}^" for m in SHIFTED)):
        out += [f"Button_{name}_{ring}" for ring in (*KNOB, "TOG")]
        if name.rstrip("^") not in SHIFTED:
            out.append(f"Button_{name}_CRSR")
        if name in ("FMS1", "FMS2"):
            out += [f"Button_{name}_{key}" for key in FMS_KEYS]
        if name == "AP":
            out += [f"Button_AP_{key}" for key in AP_ROW]
    return tuple(out)


BUTTONS = buttons()

# ---------------- the sources ----------------
Panel = namedtuple("Panel", "device button")   # a panel button: what it sends in the profile
Own = namedtuple("Own", "name code")           # code no panel button sends, and what it does
Plus = namedtuple("Plus", "panel own")         # a panel button and an Own after it, on one event (at once)
Times = namedtuple("Times", "panel count")     # a panel button sent count times on one event (at once)


# the prefix of the IFR-1's own L: variables, short as Button_UNSHIFT_SW names one per key with a hold in a message of
# 1024 bytes (clear())
STATE = "AvPanelIFR1_"


def _var(name, turned=False):
    return f"{STATE}{name}{'_Turned' if turned else ''}"


MODIFIED = ("FMS1", "FMS2", "AP", "XPDR")      # the modes whose ⇆ is a modifier of their knob


def _down(key):
    """the L: variable that keeps a key down (entry()), named by its mode and key alone, as clear() lets go of each by
    name in one message, "^" of a shifted mode spelt out (an L: variable's name takes letters, digits and _): a release
    that MobiFlight delivers to another mode, the one the user changed to with the key held, sends nothing there. A
    key with a hold keeps it so, and a key of TDS's GTN, so its key-up goes only where its key-down went."""
    return f"{STATE}{key.replace('^', '_Shifted')}"


def clear(keys, shifting=False):
    """Button_UNSHIFT_SW, which MobiFlight sends on every change of mode and on leaving shift: every modifier and each
    of keys (the profile's keys with a hold, by their mode and key) let go, so the release of a ⇆ or key pressed in
    the mode left sends nothing in the new one (held(), entry()). Only the profile's own keys, as the code must fit
    MobiFlight's message (tests/test_ifr1.py). shifting: Button_SHIFT_SW, which MobiFlight sends on entering shift,
    where only ⇆ of the modes with a shift (SHIFTED) changes button: it lets go of those alone, so the longer hold
    MobiFlight sends while ⇆ is still down (TALK_MS) sends nothing in the shifted mode."""
    if shifting:
        return Own("lets go of ⇆ in the modes with a shift",
                   " ".join([*(lset(_var(m), 0) for m in MODIFIED if m in SHIFTED),
                             *(lset(_down(key), 0) for key in keys if mode(f"Button_{key}") in SHIFTED)]))
    return Own("lets go of ⇆ and the held keys of every mode",
               " ".join([*(lset(_var(m), 0) for m in MODIFIED), *(lset(_down(key), 0) for key in keys)]))


# the squawk two digits at a time: the code is TRANSPONDER CODE:1 in BCD16 (its digits as hex, as parts.vfr reads it),
# which XPNDR_SET takes back whole, so no carry of the sim's digit events matters
_CODE = "(A:TRANSPONDER CODE:1, Bcd16)"


def squawk_pair(first, step):
    """A detent on the first two digits of the squawk (first) or the last two, as one octal number 00 to 77 stepped
    up or down (step 1 or -1) and round from 77 to 00 and back, as the panel's digits go round; the other two kept.
    Register 0 holds the pair as BCD (0x00 to 0x77), 1 the pair stepped as a number 0 to 63. A code set this way
    forgets the one VFR kept, as the panel's digits do (parts.SQUAWK)."""
    up = 1 if step > 0 else 63                     # -1 modulo 64
    if first:
        pair, rest, place = f"{_CODE} 256 / flr", f"{_CODE} 256 %", " 256 *"
    else:
        pair, rest, place = f"{_CODE} 256 %", f"{_CODE} 256 / flr 256 *", ""
    return (f"{pair} sp0 l0 16 / flr 8 * l0 16 % + {up} + 64 % sp1 "
            f"l1 8 / flr 16 * l1 8 % +{place} {rest} + {k('XPNDR_SET')} {parts.FORGET_SQUAWK}")


# NAV 2's course (CRS2), from the statements the panel sets NAV 1's with (parts.NAV1_KNOBS, parts.CENTRE), NAV 2 for
# NAV 1: the sim's own events, which the G1000 NXi and the Bonanza's NAV 2 indicator are taken to follow
NAV2_COURSE = {
    "OI": Own("NAV 2 course 10°", turn("NAV OBS:2", "VOR2_SET", 10)),
    "OD": Own("NAV 2 course 10°", turn("NAV OBS:2", "VOR2_SET", -10)),
    "II": Own("NAV 2 course 1°", k("VOR2_OBI_INC")),
    "ID": Own("NAV 2 course 1°", k("VOR2_OBI_DEC")),
    "TOG": Own("NAV 2 course to the VOR or LOC", parts.CENTRE.replace("#", "2")),
}
SQUAWK_PAIRS = {
    "OI": Own("first two squawk digits", squawk_pair(True, 1)),
    "OD": Own("first two squawk digits", squawk_pair(True, -1)),
    "II": Own("last two squawk digits", squawk_pair(False, 1)),
    "ID": Own("last two squawk digits", squawk_pair(False, -1)),
}
# ⇆ held where it sends nothing else in every profile: the panel's audio of the station tuned in NAV1 and NAV2, to hear
# its ident, and of the DME in CRS2; the simulator's own events, which an aircraft may ignore, for the marker audio in
# CRS1, for an approach, and pitot heat in BARO, of the pitot-static system the altimeter reads (1, as Black Square's
# guide sends it)
HOLDS = {
    "Button_NAV1_TOG": Panel(1, "NAV1_AUDIO"),
    "Button_NAV2_TOG": Panel(1, "NAV2_AUDIO"),
    "Button_NAV1^_TOG": Own("marker audio on or off", k("MARKER_SOUND_TOGGLE")),
    "Button_NAV2^_TOG": Panel(1, "DME_AUDIO"),
    "Button_COM2^_TOG": Own("pitot heat on or off", k("PITOT_HEAT_TOGGLE", 1)),
}

# the amber functions a held key sends (the panel's legends under the key, buttonmap.shifted): BC on APR, ARM on ALT
# and, in FMS1 and FMS2, MAP on CLR, NRST on MENU and TERR on PROC. AP keeps its press (disengaging cannot wait for the
# release) and NAV too; TEST and GPSS have no key of their own (the Bonanza's go on keys held, bonanza_extra()). The COM
# flip-flop's amber 121.5 gives way to the panel's COM 1 and COM 2 audio and, held longer, its MIC 1 and MIC 2 (TALK),
# as choosing the radios to listen to and talk on matters more in flight and the IFR-1 has no audio panel.
AMBER = ("BC", "ARM", "MAP", "NRST", "TERR")
TALK = {1: "MIC1", 2: "MIC2"}                  # ⇆ held TALK_MS in COM1 and COM2: talk on that radio
# a hold: a key held HOLD_MS sends its hold at once, while still down (onHold), and nothing when let go (but the
# second step of a hold of two, the KAP 140's VNV, entry()); ⇆ of COM1 and COM2, whose onHold is TALK, and a modifier
# ⇆ tell a hold from a tap when let go (onLongRelease) after as long. Twice the 0.35 s of the panel's keys: a hold
# that switches something off unseen (a radio's audio, pitot heat, a pump) must not come from a press a little slow.
HOLD_MS = 700
# why a ⇆ with neither a tap nor a ring that uses it held sends nothing, where its sources give no reason (none of
# them is a panel button the profile leaves unmapped)
NO_USE = "⇆ has nothing to do in this mode: no tap, and its rings take nothing with it held"
TALK_MS = 2000


def _knob(device, *names):
    return {ring: {"turn": Panel(device, name)} for ring, name in zip(KNOB, names, strict=True)}


# the modes whose rings and ⇆ are panel buttons alone: {mode: {ring: {use: source}}}
TABLE = {
    "COM1": {**_knob(1, "COM_MHZ_UP", "COM_MHZ_DN", "COM_KHZ_UP", "COM_KHZ_DN"), "TOG": {"key": Panel(1, "COM_SWAP")}},
    "COM2": {**_knob(2, "COM_MHZ_UP", "COM_MHZ_DN", "COM_KHZ_UP", "COM_KHZ_DN"), "TOG": {"key": Panel(2, "COM_SWAP")}},
    "NAV1": {**_knob(1, "NAV_MHZ_UP", "NAV_MHZ_DN", "NAV_KHZ_UP", "NAV_KHZ_DN"), "TOG": {"key": Panel(1, "NAV_SWAP")}},
    "NAV2": {**_knob(2, "NAV_MHZ_UP", "NAV_MHZ_DN", "NAV_KHZ_UP", "NAV_KHZ_DN"), "TOG": {"key": Panel(2, "NAV_SWAP")}},
    # HDG: the heading bug, 10° on the outer ring (the panel's quick turn), 1° on the inner; ⇆ syncs it
    "COM1^": {**_knob(1, "HDG_10_UP", "HDG_10_DN", "HDG_1_UP", "HDG_1_DN"), "TOG": {"key": Panel(1, "HDG_SYNC")}},
    # BARO: the altimeter setting on either ring; ⇆ STD, and pressed again the setting before where the panel does so
    "COM2^": {**_knob(1, "BARO_UP", "BARO_DN", "BARO_UP", "BARO_DN"), "TOG": {"key": Panel(1, "BARO_STD")}},
    # CRS1: the panel's course, which follows the CDI where the cockpit's does (the G1000 NXi's CRS knob); ⇆ CRS CTR
    "NAV1^": {**_knob(1, "CRS_10_UP", "CRS_10_DN", "CRS_1_UP", "CRS_1_DN"), "TOG": {"key": Panel(1, "CRS_CTR")}},
    "NAV2^": {ring: {"turn" if ring in KNOB else "key": own} for ring, own in NAV2_COURSE.items()},
    # MODE, the transponder's, as the IFR-1's legend has it: either ring clockwise ALT, counter-clockwise standby
    # (transponder_mode()); ⇆ the VFR code, held the cabin light
    "XPDR^": {"TOG": {"key": Panel(1, "VFR"), "hold": Panel(1, "CABIN_LT")}},
}
FMS = {"DCT": "DIRECT", "MENU": "MENU", "CLR": "CLR", "ENT": "ENT", "CDI": "CDI", "OBS": "OBS", "MSG": "MSG",
       "FPL": "FPL", "VNAV": "VNAV", "PROC": "PROC", "CRSR": "FMS_CRSR"}
FMS_KNOB = dict(zip(KNOB, ("FMS_OUTER_CW", "FMS_OUTER_CCW", "FMS_INNER_CW", "FMS_INNER_CCW"), strict=True))
MAP = dict(zip(KNOB, ("RANGE_CW", "RANGE_CCW", "RANGE_CW", "RANGE_CCW"), strict=True))   # clockwise zooms out

# per autopilot part (a profile's PARTS): the VS key held in the bottom row, a panel button, None for nothing. ⇆ in AP
# only modifies its rings, with no tap or hold: a detent that comes with its press goes out without it
# (docs/using/ifr1.md), and ⇆ let go would then send its tap, as FLC, which switches FLC off when it is the mode
AP_VS_HOLD = {"gfc700": "FLC", "gfc500": "FLC", "kfc150": "FD", "kap140": None}
# steps of the panel's UP and DN a detent of the AP outer ring sends with ⇆ held: 500 ft/min in VS (100 ft/min a step),
# 5 kt in FLC, five pitch steps, five altitude steps in ALT hold (the KAP 140's, or the Bonanza's 100 ft each); a quick
# change of the reference, as the inner ring trims it
AP_COARSE = 5
# per navigator part: the panel's units of FMS1 and FMS2 where they are not 1 and 2. The G1000 NXi's unit 1 is its MFD
# (with the panel's COM 1, the radios sharing a knob); the IFR-1 has modes for its radios, so FMS1 is the PFD, as the
# G1000 numbers its displays.
FMS_UNITS = {"navigator-g1000": (2, 1)}
# TDS's GTN in a unit of its own (a navigator part gtn750-tds1 and the like): the outer ring with ⇆ held is its volume
# knob (the panel's tilt up and down, (↻, ↺)), as the GTN's inner knob is its range; and MENU, CLR and ENT, which it
# takes only on its touchscreen, its volume up and down and its push (the panel's RANGE tilt and push: squelch with COM
# selected, ident with NAV). The Bonanza's tablet selections do the same in bonanza_extra().
TDS_HELD_OUTER = ("PAN_UP", "PAN_DN")
TDS_KEYS = {"MENU": ("PAN_UP", "up"), "CLR": ("PAN_DN", "down"), "ENT": ("PTR", None)}


def tds_gtn(family, unit):
    """The name of TDS's GTN in a unit of the profile ("GTN 750"), None for another navigator"""
    part = next((p for p in family.PIECES if p.KIND == "navigator" and (unit,) == p.UNITS
                 and p.KEY.startswith("gtn") and "-tds" in p.KEY), None)
    return part and f"GTN {part.KEY[3:6]}"


def transponder_mode(family, alt):
    """A detent of a MODE ring: the panel's XPDR MODE, which switches between standby and ALT, only from standby or
    off (alt) or only from ALT or on (not alt), so each way takes the transponder one way however far it turns"""
    code = family.DEVICE[1].get("XPDR_MODE")
    if code is None:
        return Panel(1, "XPDR_MODE")                  # its reason
    test = "(A:TRANSPONDER STATE:1, Enum) 1 >" + (" !" if alt else "")
    return Own("transponder ALT" if alt else "transponder standby", f"{test} if{{ {tapped(code)} }}")


def _part(family, kind):
    """The key of the profile's part of this kind (its PARTS, as "autopilot-kap140" -> "kap140")"""
    return next(p.KEY for p in family.PIECES if kind == p.KIND)


def fms_units(family):
    """(FMS1's unit, FMS2's unit) in the profile"""
    return next((units for p, units in FMS_UNITS.items() if p in family.PARTS), (1, 2))


def amber(device, button):
    """A key's use: the panel key, and held its amber function where that is one of AMBER"""
    shifted = BM.shifted(button)
    return {"key": Panel(device, button), **({"hold": Panel(device, shifted)} if shifted in AMBER else {})}


def uses(key):
    """{IFR-1 button: {use: source}} for the profile of this key. A use is "turn" (a detent), "held" (a detent with
    ⇆ held), "key" (a key's press, or its tap where it has a hold), "hold" (a key held HOLD_MS, sent while still
    down; for ⇆ of COM1 and COM2 sent when let go after HOLD_MS), "long_hold" (⇆ of COM1 and COM2 held TALK_MS, sent
    at once, its release then sending nothing), "tap" (⇆ as a modifier, let go at once); a source is a Panel button,
    an Own code, a Plus of both, a Panel button Times over, or None for nothing."""
    family = FAMILIES[key]
    autopilot = _part(family, "autopilot")
    out = {f"Button_{name}_{ring}": dict(use) for name, rings in TABLE.items() for ring, use in rings.items()}
    for button, source in HOLDS.items():
        out[button]["hold"] = source
    for com, talk in TALK.items():
        out[f"Button_COM{com}_TOG"] = {"key": Panel(com, "COM_SWAP"), "hold": Panel(1, f"COM{com}"),
                                       "long_hold": Panel(1, talk)}
    for ring, alt in zip(KNOB, (True, False, True, False), strict=True):
        out[f"Button_XPDR^_{ring}"] = {"turn": transponder_mode(family, alt)}
    # AP: the selected altitude 1000 ft on the outer ring and 100 ft on the inner, as the selectors the profiles drive
    # have them; with ⇆ held the inner ring is the panel's UP and DN (the rate or speed), the outer ring AP_COARSE of
    # them at once; the push VNV, held, as a push comes easily with a turn of the rings
    for ring, button in zip(KNOB, ("ALT_1000_UP", "ALT_1000_DN", "ALT_100_UP", "ALT_100_DN"), strict=True):
        out[f"Button_AP_{ring}"] = {"turn": Panel(1, button)}
    out["Button_AP_OI"]["held"] = Times(Panel(1, "UP"), AP_COARSE)
    out["Button_AP_OD"]["held"] = Times(Panel(1, "DN"), AP_COARSE)
    out["Button_AP_II"]["held"] = Panel(1, "UP")
    out["Button_AP_ID"]["held"] = Panel(1, "DN")
    out["Button_AP_CRSR"] = {"key": None, "hold": Panel(1, "VNV")}
    out["Button_AP_TOG"] = {"tap": None, "hold": None}
    for name in AP_ROW:
        out[f"Button_AP_{name}"] = amber(1, name) if name in ("APR", "ALT") else {"key": Panel(1, name)}
    if hold := AP_VS_HOLD[autopilot]:
        out["Button_AP_VS"]["hold"] = Panel(1, hold)
    # FMS1 and FMS2: the unit's keys and knob, with ⇆ held its map's range; ⇆ tapped the unit's HOME
    for name, unit in zip(("FMS1", "FMS2"), fms_units(family), strict=True):
        shift = "S_" if unit == 2 else ""          # a unit's map: unit 2's is on device 1 with SHIFT (part.place)
        gtn = tds_gtn(family, unit)
        held = {**MAP, **(dict(zip(KNOB[:2], TDS_HELD_OUTER, strict=True)) if gtn else {})}
        for ring, button in FMS_KNOB.items():
            out[f"Button_{name}_{ring}"] = {"turn": Panel(unit, button), "held": Panel(1, shift + held[ring])}
        for ifr1_key, button in FMS.items():
            out[f"Button_{name}_{ifr1_key}"] = amber(unit, button)
        for ifr1_key, (button, way) in TDS_KEYS.items() if gtn else ():
            code = family.DEVICE[1].get(shift + button)
            out[f"Button_{name}_{ifr1_key}"]["key"] = (Own(f"{gtn} volume {way}", code) if way and code else
                                                       Panel(1, shift + button))
        out[f"Button_{name}_TOG"] = {"tap": Panel(unit, "HOME"), "hold": None}
        if "navigator-g1000" in family.PARTS and autopilot == "gfc700":
            # the G1000 NXi's VNAV is its GFC 700's VNV, as the IFR-1's VNAV key reads, not the panel's amber VNAV,
            # which there is the MFD's Detail softkey (the C182T's KAP 140 has no VNAV: its VNV is a calculator)
            out[f"Button_{name}_VNAV"] = {"key": Panel(1, "VNV")}
    # XPDR: two digits a ring, with ⇆ held the panel dimmer on the outer ring and the flood dimmer on the inner; ⇆
    # tapped IDENT
    for ring, own in SQUAWK_PAIRS.items():
        out[f"Button_XPDR_{ring}"] = {"turn": own}
    for ring, button in zip(KNOB, ("PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN"), strict=True):
        out[f"Button_XPDR_{ring}"]["held"] = Panel(1, button)
    out["Button_XPDR_TOG"] = {"tap": Panel(1, "IDENT"), "hold": None}
    out["Button_UNSHIFT_SW"] = {"key": None}      # clear(), of the keys with a hold the profile has (build())
    out["Button_SHIFT_SW"] = {"key": None}        # clear(shifting=True), likewise
    for (button, use), source in EXTRA.get(key, dict)().items():
        out[button][use] = source
    assert set(out) == set(BUTTONS), sorted(set(out) ^ set(BUTTONS))
    return {button: out[button] for button in BUTTONS}


def tapped(entry):
    """A table entry sent at once, as a tap: its press code, then its release code (a key held as long as the panel's,
    as TDS's GTN keys); None stays None"""
    if entry is None or isinstance(entry, str):
        return entry
    if "long" in entry:
        raise ValueError(f"an entry that tells a tap from a hold cannot go out at once: {entry!r}")
    return " ".join(filter(None, (entry.get("press"), entry.get("release"))))


# ---------------- the Black Square Bonanza's own uses ----------------
def _codes(navigators, button, kind):
    """What the navigators of a kind (a part of their key: "gtn" TDS's and PMS50's GTN, "-tds" TDS's alone, "gns" the
    GNS) among a unit's send for a panel button of their map, joined, each at once (tapped()): "" where none takes it"""
    return " ".join(tapped(n.DEVICE[1][button]) for n in navigators if kind in n.KEY and button in n.DEVICE[1])


# the KFC 150's self-test (its TEST, the guide's counter), only with the autopilot off: a test in flight would disturb
# the engaged autopilot
_SELF_TEST = black_square_bonanza.SELF_TEST
# the HSI's course (NAV 1's, the yellow arrow, as the panel's CRS sets it) to the heading, as HDG_SYNC sets the bug
_COURSE_SYNC = "(A:HEADING INDICATOR:1, degrees) near dnor (>K:VOR1_SET)"
# the oxygen flow valve (L:var_oxygenOn, 0 to 100): shut where open at all, else fully open
_OXYGEN = "(L:var_oxygenOn, Number) 0 > ! 100 * (>L:var_oxygenOn)"
# the two tip tank transfer pumps' switches, together: both off where either runs, else both on, so a hold after one
# was switched in the cockpit stops both
_TIP_TANKS = ("(L:TipTankTransferSwitch_L, Bool) (L:TipTankTransferSwitch_R, Bool) or ! sp0 "
              "l0 (>L:TipTankTransferSwitch_L) l0 (>L:TipTankTransferSwitch_R)")
# the fuel boost pump (L:var_FUEL_Switch_Pump_1: 0 off, 1 low, 2 high): one position on, from high round to off, as
# the project the Bonanza is flown with steps it
_FUEL_PUMP = "(L:var_FUEL_Switch_Pump_1, Number) 1 + 3 % (>L:var_FUEL_Switch_Pump_1)"
# prop heat, by the simulator's input event, as the project the Bonanza is flown with switches it
_PROP_HEAT = "1 (>B:DEICE_Propeller_1_Toggle)"
# the air conditioner and its blower (L:var_airConditioningBlowerSwitch 2, high, with it, else 0), together
_AIR_CONDITIONER = ("(L:var_AirConditionerSwitch, Bool) ! sp0 l0 (>L:var_AirConditionerSwitch) "
                    "l0 2 * (>L:var_airConditioningBlowerSwitch)")


def bonanza_extra():
    """{(IFR-1 button, use): source} over the panel's, for the Black Square Bonanza (EXTRA). TDS's GTN takes none of the
    keys MENU, CLR and ENT of FMS1 (PMS50's takes them as its MENU, BACK and ENTER with its Premium version, gtn.py), so
    each also sends TDS's volume up, down and its push (squelch with COM selected, ident with NAV); only TDS's GTN takes
    those (families/black_square_bonanza.py). FMS2's CLR and ENT are the EDM 800's (below), and its volume is the outer
    ring's with ⇆ held, the volume keys being seldom used. The outer ring with ⇆ held is the GNS's map range, as the
    inner ring is, and the GTN's volume knob (TDS's and PMS50's, as TDS_HELD_OUTER has it for TDS's GTN), and in FMS1
    the KLN 90B's left outer knob: the panel's RANGE knob sends the COM volume beside each GTN's, which the GNS takes,
    so the outer ring sends each navigator's own. ⇆ in HDG also sets the HSI's course (NAV 1's, its yellow arrow) to the
    heading, as it sets the heading bug.

    The cockpit's functions go on keys of FMS1 and FMS2, none on a ⇆ that also modifies its ring, which has no hold
    (AP_VS_HOLD). NAV held is the HSI's NAV 1 / RNAV switch (GPSS), as the panel's amber NAV; in FMS2, VNAV is the DME
    selector (the GNS 430 has no VNAV key), CLR and ENT the EDM 800's STEP and LEAN FIND, its left and right buttons
    side by side, its short presses on a tap, as they are pressed often (the GNS 430's CLR and ENT, each with PMS50's,
    held instead; MAP, CLR's amber, gives way), and held, MENU the KFC 150's self-test with the autopilot off, MSG the
    oxygen flow valve, FPL both tip tank transfer pumps, OBS prop heat, CDI the fuel boost pump and VNAV the air
    conditioner, from the guide's "Hardware Inputs & Outputs" and the project the Bonanza is flown with. Those keys then
    send their tap on release, their hold at once (HOLD_MS). The fuel selector stays the cockpit's: a tank is chosen
    seldom, and a held key should not choose one by mistake."""
    units = {1: ("GTN 750", "", black_square_bonanza.UNIT1_NAVIGATORS),
             2: ("GTN 650", "S_", black_square_bonanza.UNIT2_NAVIGATORS)}
    out = {}
    gtn, shift, navigators = units[1]
    for ifr1_key, button, words in (("MENU", "PAN_UP", "volume up"), ("CLR", "PAN_DN", "volume down"),
                                    ("ENT", "PTR", "volume push: squelch, or ident with NAV")):
        code = _codes(navigators, shift + button, "-tds")
        out[f"Button_FMS1_{ifr1_key}", "key"] = Plus(Panel(1, ifr1_key), Own(f"TDS {gtn} {words}", code))
    for ring, kln, way, volume in (("OI", "PAN_RIGHT", "CW", "UP"), ("OD", "PAN_LEFT", "CCW", "DN")):
        for mode, unit in (("FMS1", 1), ("FMS2", 2)):
            gtn, shift, navigators = units[unit]
            gns = f"GNS {('530', '430')[unit - 1]}"
            code = (f"{_codes(navigators, f'{shift}RANGE_{way}', 'gns')} "
                    f"{_codes(navigators, f'{shift}PAN_{volume}', 'gtn')}")
            own = Own(f"{gns} map range; {gtn} volume", code)
            out[f"Button_{mode}_{ring}", "held"] = Plus(Panel(1, kln), own) if unit == 1 else own
    edm = {side: FAMILIES["black-square-bonanza"].DEVICE[1][f"S_{way}"]["release"]
           for side, way in (("L", "UP"), ("R", "DN"))}                # the EDM 800's buttons, a short press
    out.update({
        ("Button_COM1^_TOG", "key"): Plus(Panel(1, "HDG_SYNC"), Own("HSI course to the heading", _COURSE_SYNC)),
        ("Button_AP_NAV", "hold"): Panel(1, "GPSS"),
        ("Button_FMS2_VNAV", "key"): Panel(1, "LVL"),
        ("Button_FMS2_VNAV", "hold"): Own("air conditioner and blower on or off", _AIR_CONDITIONER),
        ("Button_FMS2_CLR", "key"): Own("EDM 800 STEP", edm["L"]),
        ("Button_FMS2_CLR", "hold"): Panel(2, "CLR"),
        ("Button_FMS2_ENT", "key"): Own("EDM 800 LEAN FIND", edm["R"]),
        ("Button_FMS2_ENT", "hold"): Panel(2, "ENT"),
        ("Button_FMS2_MENU", "hold"): Own("KFC 150 self-test, autopilot off only", _SELF_TEST),
        ("Button_FMS2_MSG", "hold"): Own("oxygen on or off", _OXYGEN),
        ("Button_FMS2_FPL", "hold"): Own("tip tank pumps: both off if either runs, else both on", _TIP_TANKS),
        ("Button_FMS2_OBS", "hold"): Own("prop heat on or off", _PROP_HEAT),
        ("Button_FMS2_CDI", "hold"): Own("fuel boost pump: off → low → high → off", _FUEL_PUMP),
    })
    return out


# ---------------- the COWS DA40's and Carenado C182T's own uses ----------------
# the electric fuel pump, by the simulator's input event, as the projects these aircraft are flown with switch it
_ELECTRIC_PUMP = Own("electric fuel pump on or off", "(B:FUEL_PUMP_1) ! (>B:FUEL_PUMP_1_Set)")


def da40_extra():
    """{(IFR-1 button, use): source} over the panel's, for the COWS DA40 (EXTRA): FMS2's keys held, which the G1000
    NXi's MFD leaves free, as the project the DA40 is flown with sets them: CDI the electric fuel pump, FPL the NG's
    auxiliary fuel transfer pump (L:XFER_SWITCH, which the XLS ignores), as FPL held is the Bonanza's tip tank pumps.
    Those keys then send their tap on release, their hold at once (HOLD_MS). The fuel selector stays the cockpit's
    (bonanza_extra()); the DA40 has no oxygen, tip tanks or prop heat."""
    return {
        ("Button_FMS2_CDI", "hold"): _ELECTRIC_PUMP,
        ("Button_FMS2_FPL", "hold"): Own("NG fuel transfer pump on or off", "(L:XFER_SWITCH, Bool) ! (>L:XFER_SWITCH)"),
    }


def c182t_extra():
    """{(IFR-1 button, use): source} over the panel's, for Carenado's C182T (EXTRA): CDI held in FMS2, which the G1000
    NXi's MFD leaves free, the electric fuel pump, as the project the C182T is flown with switches it; CDI then sends
    its tap on release, its hold at once (HOLD_MS)"""
    return {("Button_FMS2_CDI", "hold"): _ELECTRIC_PUMP}


# per profile: the IFR-1's uses over the panel's, as a function of no arguments (uses())
EXTRA = {"black-square-bonanza": bonanza_extra, "cows-da40": da40_extra, "carenado-c182t": c182t_extra}


_OF_A_MODE = re.compile(rf"Button_([A-Z0-9]+\^?)_({'|'.join((*KNOB, 'TOG', 'CRSR', *FMS_KEYS))})")


def mode(button):
    """The mode an IFR-1 button belongs to, shifted ones with ^ ("Button_COM1^_OI" -> "COM1^"), None for the bottom
    row and SHIFT_SW and UNSHIFT_SW, which every mode shares"""
    match = _OF_A_MODE.fullmatch(button)
    return match[1] if match else None


def is_modifier(button):
    """Whether a button is ⇆ of a mode whose knob it modifies (MODIFIED)"""
    return button.endswith("_TOG") and mode(button) in MODIFIED


def is_ring(button):
    """Whether a button is a detent of a ring"""
    return button.rsplit("_", 1)[1] in KNOB


def held(name, tap):
    """⇆ of the mode name as a modifier: pressed, it sets its L: variable (_var()) and clears its _Turned; let go, it
    sends tap (None: nothing) unless a detent came between or the mode changed since the press (clear() let go of it),
    however long it was held, then clears the modifier. It has no hold (AP_VS_HOLD). Its long release is its release,
    so a slow tap counts and the ring leaves its held layer whatever MobiFlight sends on a release after a hold."""
    on, turned = _var(name), _var(name, True)
    release = f"(L:{on}, Bool) (L:{turned}, Bool) ! and if{{ {tap} }} {lset(on, 0)}" if tap else lset(on, 0)
    return {"press": f"{lset(on, 1)} {lset(turned, 0)}", "release": release, "long": release}


def knob(name, turn_code, held_code=None):
    """A detent of the knob of the mode name, whose ⇆ is a modifier: turn_code, or held_code while ⇆ is held. Without
    held_code (no use with ⇆ held, or one the profile leaves unmapped) it sends turn_code whether ⇆ is held or not.
    Every detent marks the knob turned, so ⇆ let go sends nothing; a detent that sends nothing at all is None."""
    on, turned = f"(L:{_var(name)}, Bool)", _var(name, True)
    if held_code and turn_code:
        code = f"{on} if{{ {held_code} }} els{{ {turn_code} }}"
    elif held_code:
        code = f"{on} if{{ {held_code} }}"
    else:
        code = turn_code
    return f"{code} {lset(turned, 1)}" if code else None


# ---------------- the lights ----------------
_FLAGS = dict(zip(LIGHTS, ("AUTOPILOT MASTER", "AUTOPILOT HEADING LOCK", "AUTOPILOT NAV1 LOCK",
                           "AUTOPILOT APPROACH HOLD", "AUTOPILOT ALTITUDE LOCK", "AUTOPILOT VERTICAL HOLD"),
                  strict=True))
_FLAG = {light: f"(A:{flag}, Bool)" for light, flag in _FLAGS.items()}
_APR_OR_BC = f"{_FLAG['AP APR']} (A:AUTOPILOT BACKCOURSE HOLD, Bool) or"
_GARMIN = dict(_FLAG)
# what each light shows, by the autopilot part: the sim's autopilot flags, which Garmin's autopilot (Working Title's
# directors), the KAP 140 (the sim's KAP140.js) and Black Square's KFC 150 (its keys are the sim's autopilot events)
# are taken to keep, to check on the device (docs/using/ifr1.md). The KAP 140 has no flight director, so its mode
# lights go with the autopilot; the KAP 140's and KFC 150's APR light shows BC too, as their APR annunciator does with
# REV and BC. Each read is 0 or 1 (a flag, and, or).
LEDS = {
    "gfc700": _GARMIN,
    "gfc500": _GARMIN,
    "kap140": {"AP Master": _FLAG["AP Master"],
               **{light: f"{_FLAG['AP Master']} {read} and"
                  for light, read in {**_FLAG, "AP APR": _APR_OR_BC}.items() if light != "AP Master"}},
    "kfc150": {**_FLAG, "AP APR": _APR_OR_BC},
}


READS = re.compile(r"\(A:([^),]+)")              # the variables a light reads


# ---------------- a profile ----------------
Use = namedtuple("Use", "source entry reason")   # a source, what it sends in the profile (None: nothing) and why not


def resolve(table, family, source):
    """A source's Use in the profile, whose DEVICE tables are table (profile.tables())"""
    if source is None:
        return Use(None, None, None)
    if isinstance(source, Own):
        return Use(source, source.code, None)
    if isinstance(source, Plus):
        panel = resolve(table, family, source.panel)
        code = " ".join(filter(None, (tapped(panel.entry), source.own.code)))
        return Use(source, code or None, None if code else panel.reason)
    if isinstance(source, Times):
        panel = resolve(table, family, source.panel)
        code = panel.entry and repeated(tapped(panel.entry), source.count)
        return Use(source, code or None, None if code else panel.reason)
    if source.button in table[source.device]:
        return Use(source, table[source.device][source.button], None)
    return Use(source, None, family.UNMAPPED[source.device][source.button])


_TOKEN = re.compile(r"\([^)]*\)|\S+")                     # a code's tokens: a variable read or set, or a word
_REPEATABLE = re.compile(r"\(>[KH]:[^\d)][^)]*\)")         # an event of one value or none (not K:2:)
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def repeated(code, count):
    """A code that sends each run of its events count times where it sends it once, a run whole, so a press and its
    release stay in order: its tests (the autopilot's mode) run once, and it stays short enough for MobiFlight's
    message, where the whole code count times would not. Only for a code of the UP and DN keys' shape: events, each
    of no value or a number just before it, in blocks of if{, els{ and }, each if{ after one read, its test. Anything
    else could set a variable once for count events or leave an event's computed value to its first send alone, so it
    raises ValueError."""
    tokens = _TOKEN.findall(code)
    out, run = [], []
    for token, after in zip(tokens, [*tokens[1:], None], strict=True):
        if _REPEATABLE.fullmatch(token) or (_NUMBER.fullmatch(token) and after and _REPEATABLE.fullmatch(after)):
            run.append(token)
            continue
        if not (token in ("if{", "els{", "}") or (token.startswith("(") and token[1] != ">" and after == "if{")):
            raise ValueError(f"a code that is not events in tests cannot repeat ({token!r}): {code!r}")
        out += run * count + [token]
        run = []
    return " ".join(out + run * count)


def holds(used):
    """A key's (tap, hold, longer hold) codes, each sent at once (tapped()), from its Uses; a longer hold takes the
    place of a hold that sends nothing or only the tap (TALK where a profile leaves the radio's audio unmapped)"""
    plain, hold, longer = (tapped(used[use].entry) if use in used else None for use in ("key", "hold", "long_hold"))
    if longer is not None and (hold is None or hold == plain):
        hold, longer = longer, None
    return plain, (hold if hold != plain else None), longer


def entry(button, used):
    """The table entry of an IFR-1 button from its Uses ({use: Use}), or None where it sends nothing"""
    sent = {use: u.entry for use, u in used.items()}
    name = mode(button)
    if is_modifier(button):
        if sent.get("hold") is not None:
            raise ValueError(f"{button}: a modifier has no hold, as a detent that comes with its press would send it")
        return held(name, tapped(sent.get("tap")))
    if is_ring(button):
        turn_code = tapped(sent.get("turn"))
        return knob(name, turn_code, tapped(sent.get("held"))) if name in MODIFIED else turn_code
    plain, hold, longer = holds(used)
    if hold is not None:          # a tap on its release, a hold at once, each only if the key went down here
        down = _down(button.removeprefix("Button_"))

        def end(code):
            return f"(L:{down}, Bool) if{{ {code} }} {lset(down, 0)}" if code else lset(down, 0)
        two = used["hold"].entry if "hold" in used else None
        if longer is None and isinstance(two, dict) and set(two) == {"press", "release"}:
            # a hold of two steps (the KAP 140's VNV: VS and the rate, then the rate again a frame later, once the
            # autopilot is in VS): the first at once, the second as the key is let go after it, on any release
            # (MobiFlight may take a release just past HOLD_MS for a long one before its hold's timer fired: with no
            # long release a release is a release), its flag let go on a change of mode as the key's (clear())
            again = f"{down}_Again"
            return {"press": lset(down, 1),
                    "release": f"{end(plain)} (L:{again}, Bool) if{{ {two['release']} }} {lset(again, 0)}",
                    "hold": f"(L:{down}, Bool) if{{ {two['press']} {lset(again, 1)} }} {lset(down, 0)}"}
        if longer is None:
            return {"press": lset(down, 1), "release": end(plain), "hold": end(hold)}
        # ⇆ of COM1 and COM2: the hold when let go after HOLD_MS, the longer hold at once after TALK_MS
        return {"press": lset(down, 1), "release": end(plain), "long": end(hold), "hold": end(longer)}
    plain = sent.get("key")
    if isinstance(plain, dict) and "release" in plain and "long" not in plain:
        # a key held as long as the panel's (TDS's GTN): its key-up only from the button that sent its key-down, so a
        # release MobiFlight delivers to another mode reaches no other unit. clear() leaves the flag alone: the button's
        # next press and release let go of what a key-up lost on a change of mode left down.
        down = _down(button.removeprefix("Button_"))
        return {**plain, "press": " ".join(filter(None, (lset(down, 1), plain.get("press")))),
                "release": f"(L:{down}, Bool) if{{ {plain['release']} }} {lset(down, 0)}"}
    return plain


def build(key, vfr=None):
    """The IFR-1 profile of a panel profile (FAMILIES[key]): KEY, NAME (the panel's), USES ({button: {use: Use}}),
    DEVICE ({button: entry}), UNMAPPED ({button: reason}, every other button, with the reason of its first use the
    profile leaves unmapped), LEDS ({light: read}) and UNITS (FMS1's and FMS2's panel units). vfr: the VFR code ⇆
    in MODE squawks (profile.tables())."""
    family = FAMILIES[key]
    table = profile.tables(family, vfr)
    device, unmapped, used_by, held_keys = {}, {}, {}, []
    for button, sources in uses(key).items():
        used = {use: resolve(table, family, source) for use, source in sources.items()}
        used_by[button] = used
        sent = entry(button, used)
        if is_modifier(button) and sent and used["tap"].entry is None and not any(
                used_by[f"Button_{mode(button)}_{ring}"].get("held", Use(None, None, None)).entry for ring in KNOB):
            sent = None                     # a ⇆ with no tap whose rings have no use with it held (the G3X's FMS)
            for ring in KNOB:               # whose rings then mark no turn for it
                ring_button = f"Button_{mode(button)}_{ring}"
                if ring_button in device:
                    device[ring_button] = device[ring_button].removesuffix(f" {lset(_var(mode(button), True), 1)}")
        key_name = button.removeprefix("Button_")
        if isinstance(sent, dict) and sent.get("press") == lset(_down(key_name), 1):     # a key with a hold
            held_keys.append(key_name)
            if f"{_down(key_name)}_Again" in sent.get("hold", ""):                     # and a second step
                held_keys.append(f"{key_name}_Again")
        if sent is not None:
            device[button] = sent
        elif button not in ("Button_SHIFT_SW", "Button_UNSHIFT_SW"):
            unmapped[button] = next((u.reason for u in used.values() if u.reason), NO_USE)
    for button, let_go in (("Button_SHIFT_SW", clear(held_keys, shifting=True)),
                           ("Button_UNSHIFT_SW", clear(held_keys))):
        used_by[button] = {"key": Use(let_go, let_go.code, None)}
        device[button] = let_go.code
    device = {button: device[button] for button in BUTTONS if button in device}
    return SimpleNamespace(KEY=key, NAME=family.NAME, USES=used_by, DEVICE=device, UNMAPPED=unmapped,
                           LEDS=dict(LEDS[_part(family, "autopilot")]), UNITS=fms_units(family))


def filename(key):
    """An IFR-1 project's file name, by its panel profile's key"""
    return f"avionics-panel-ifr1-{key}.mfproj"


def item_label(ifr1_profile, button, acts):
    """What an item is named by in MobiFlight's list: as the panel's (profile.label()), without the IFR-1's own state
    variables, which every key with a hold and every modifier sets; the buttons that let go of them by what they do"""
    if button.endswith("SHIFT_SW"):
        return ifr1_profile.USES[button]["key"].source.name
    return ", ".join(name for name in profile.label(" ".join(acts.values())).split(", ")
                     if not name.startswith(STATE)) or "modifier of the rings"       # ⇆ with no tap of its own


def project(ifr1_profile, stamp=None):
    """The project of an IFR-1 profile (ifr1.build()) as a dict: an InputConfigItem for each of its buttons, by the
    name MobiFlight gives it (Device {"Type": "Button", "Name": "Button_COM1_OI"}), and an OutputConfigItem for each AP
    light, its read as custom code (SimConnectValue VarType 2, CODE) to the light by its label (Device {"Type":
    "Output", "Pin": "AP HDG"}), as MobiFlight 11.3.1 writes a joystick's light (OutputConfigItem.cs,
    OutputConfig/Output.cs; its own IFR-1 sample, Samples/Test Autoshift.mfproj). Every item names the IFR-1 as its
    controller, which MobiFlight 11 binds to the one connected (SERIAL). stamp: as profile.build()'s."""
    controller = {"Name": NAME, "Serial": SERIAL}
    title = f"{profile.NAME} for the IFR-1: {ifr1_profile.NAME}"
    items = []
    for button in BUTTONS:
        if button not in ifr1_profile.DEVICE:
            continue
        acts = profile.actions(ifr1_profile.DEVICE[button])
        items.append({
            "GUID": str(uuid.uuid5(profile.ITEMS, f"ifr1/{ifr1_profile.NAME}/{button}")),
            "Active": True,
            "Name": f"{button.removeprefix('Button_')}: {item_label(ifr1_profile, button, acts)}",
            "Type": "InputConfigItem",
            "Controller": controller,
            "Device": {"Type": "Button", "Name": button},
            # a key with a hold when let go and one at once (⇆ of COM1 and COM2) holds longer for the second (entry())
            "button": profile.button_config(
                acts, long_delay=HOLD_MS, hold_delay=TALK_MS if {"onLongRelease", "onHold"} <= set(acts) else HOLD_MS),
        })
    for light in LIGHTS:
        read = ifr1_profile.LEDS[light]
        items.append({
            "GUID": str(uuid.uuid5(profile.ITEMS, f"ifr1/{ifr1_profile.NAME}/{light}")),
            "Active": True,
            "Name": f"{light} light: {', '.join(dict.fromkeys(READS.findall(read)))}",
            "Type": "OutputConfigItem",
            "Controller": controller,
            "Source": {"Type": "SimConnectSource", "SimConnectValue": {"UUID": "", "Value": read, "VarType": 2}},
            "TestValue": {"type": 1, "Float64": 1.0},
            "Device": {"Name": light, "Pin": light, "Brightness": 255, "PwmMode": False, "Type": "Output"},
            "DeviceType": "Output",
            "DeviceName": light,
        })
    return profile.project(f"{title}{f' ({stamp})' if stamp else ''}", title, items)
