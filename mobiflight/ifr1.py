"""The Octavi IFR-1's MobiFlight profiles, made from the panel's (docs/using/ifr1.md): for every profile of
families.FAMILIES, a project for the IFR-1 that sends what the panel's buttons send in that profile.

MobiFlight reads the IFR-1 itself (src/MobiFlightConnector/MobiFlight/Joysticks/Octavi/ in its repository at 11.3.1:
OctaviHandler.cs, Octavi.cs, and Joysticks/octavi/octavi.joystick.json). The device keeps one of eight modes, which its
mode keys select, and reports it with every input; MobiFlight turns each input into one of 96 named buttons (BUTTONS)
by that mode and a shift of its own, which the knob push toggles in COM1, COM2, NAV1, NAV2 and XPDR and every change of
mode ends (sending Button_UNSHIFT_SW). Its keys send a press and a release, and from MobiFlight 11.3 a release after a
hold (onLongRelease, profile.LONG_MS); a knob sends one press per detent and nothing else. Its six AP lights each take 0
or 1 (LEDS): MobiFlight shifts the value into the lights' byte as it is, so a 2 would light the next light too.

Every IFR-1 button sends what a panel button sends in the profile (uses(): Panel sources, by the table TABLE), with
these rules over it:

- ⇆ in FMS1, FMS2, AP and XPDR is a modifier of its mode's knob (MODIFIED): pressed, it sets the mode's L: variable;
  a detent while it is held sends the knob's held code; let go without a detent between, it sends its tap, or its
  hold after a hold (profile.LONG_MS), on its release; then it clears the variable. The state lives in L: variables
  of the IFR-1's own (L:AvionicsPanel_IFR1_*), as the panel keeps its own, so the two devices can fly together.
- A key with a hold (an amber function of AMBER of its panel key, TALK, HOLDS or the profile's EXTRA) sends that when
  held and its plain function on a tap, on its release; every other key sends on press as the panel's does, a key of
  TDS's GTN its key-up on release.
- MobiFlight sends a release to the button of the mode the IFR-1 is in by then, and Button_UNSHIFT_SW on every change
  of mode and on leaving shift. That button lets go of every ⇆ and every key with a hold (clear()), so one let go
  after a change of mode sends nothing, and a GTN key sends its key-up only from the button that sent its key-down.
- A panel button the profile leaves unmapped leaves the IFR-1's unmapped too, with the profile's reason.

In every profile ⇆ held in COM1 and COM2 is the panel's MIC 1 and MIC 2 (TALK), and where it sent nothing, the panel's
NAV 1 and NAV 2 audio in NAV1 and NAV2, the simulator's marker audio event in CRS1, the panel's DME audio in CRS2 and
the simulator's pitot heat event in BARO (HOLDS); with ⇆ held in FMS1 and FMS2, a GTN's outer ring is its volume
(HELD_OUTER). Per profile, EXTRA puts IFR-1 uses of their own over the panel's (Plus and Own sources): in the Black
Square Bonanza TDS's GTN volume beside the GNS's, KLN 90B's and pms50's keys, each navigator's range or volume on the
outer ring with ⇆ held, the HSI's course with the heading bug, and the cockpit's GPSS, self-test, EDM 800, DME selector,
oxygen, tip tanks, prop heat, fuel pump and air conditioner on keys of FMS1 and FMS2 (bonanza_extra()); in the COWS DA40
and the C182T their fuel pump, and the NG DA40's fuel transfer pump, on keys of FMS2 held (da40_extra(), c182t_extra());
in the GTN profile TDS's volume and its push on MENU, CLR and ENT (gtn_extra()).

New code, which no panel button sends (Own sources): the squawk's digits in pairs (squawk_pair), NAV 2's course
(NAV2_COURSE), the modifier (held(), knob()), the KAP 140's VS key (parts.KAP140_VS, the statement VNV starts with), the
marker audio and pitot heat (HOLDS), the button that lets go of the held keys (clear()) and the aircraft's own codes of
EXTRA. project() writes the project.
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
    for mode in (*MODES, *(f"{m}^" for m in SHIFTED)):
        out += [f"Button_{mode}_{ring}" for ring in (*KNOB, "TOG")]
        if mode.rstrip("^") not in SHIFTED:
            out.append(f"Button_{mode}_CRSR")
        if mode in ("FMS1", "FMS2"):
            out += [f"Button_{mode}_{key}" for key in FMS_KEYS]
        if mode == "AP":
            out += [f"Button_AP_{key}" for key in AP_ROW]
    return tuple(out)


BUTTONS = buttons()

# ---------------- the sources ----------------
Panel = namedtuple("Panel", "device button")   # a panel button: what it sends in the profile
Own = namedtuple("Own", "name code")           # code no panel button sends, and what it does
Plus = namedtuple("Plus", "panel own")         # a panel button and an Own after it, on one event (at once)


def _var(mode, turned=False):
    return f"AvionicsPanel_IFR1_{mode}{'_Turned' if turned else ''}"


MODIFIED = ("FMS1", "FMS2", "AP", "XPDR")      # the modes whose ⇆ is a modifier of their knob


def _down(key):
    """the L: variable that keeps a key down (entry()), named by its mode and key alone, as clear() lets go of each by
    name in one message, "^" of a shifted mode spelt out (an L: variable's name takes letters, digits and _): a release
    that MobiFlight delivers to another mode, the one the user changed to with the key held, sends nothing there. A
    key with a hold keeps it so, and a key of TDS's GTN, so its key-up goes only where its key-down went."""
    return f"AvionicsPanel_IFR1_{key.replace('^', '_Shifted')}"


def clear(keys):
    """Button_UNSHIFT_SW, which MobiFlight sends on every change of mode and on leaving shift: every modifier and each
    of keys (the profile's keys with a hold, by their mode and key) let go, so the release of a ⇆ or key pressed in
    the mode left sends nothing in the new one (held(), entry()). Only the profile's own keys, as the code must fit
    MobiFlight's message (tests/test_ifr1.py)."""
    return Own("lets go of ⇆ and the held keys of every mode",
               " ".join([*(lset(_var(m), 0) for m in MODIFIED), *(lset(_down(k), 0) for k in keys)]))


# the squawk two digits at a time: the code is TRANSPONDER CODE:1 in BCD16 (its digits as hex, as parts.vfr reads it),
# which XPNDR_SET takes back whole, so no carry of the sim's digit events matters
_CODE = "(A:TRANSPONDER CODE:1, Bcd16)"


def squawk_pair(first, step):
    """A detent on the first two digits of the squawk (first) or the last two, as one octal number 00 to 77 stepped
    up or down (step 1 or -1) and round from 77 to 00 and back, as the panel's digits go round; the other two kept.
    Register 0 holds the pair as BCD (0x00 to 0x77), 1 the pair stepped as a number 0 to 63. A code set this way
    forgets the one VFR kept, as the panel's digits do (parts.SQUAWK)."""
    if step not in (1, -1):
        raise ValueError(f"a squawk pair steps by 1 or -1, not {step!r}")
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
    "OI": Own("NAV 2 course +10°", turn("NAV OBS:2", "VOR2_SET", 10)),
    "OD": Own("NAV 2 course -10°", turn("NAV OBS:2", "VOR2_SET", -10)),
    "II": Own("NAV 2 course +1°", k("VOR2_OBI_INC")),
    "ID": Own("NAV 2 course -1°", k("VOR2_OBI_DEC")),
    "TOG": Own("NAV 2 course to the VOR or LOC", parts.CENTRE.replace("#", "2")),
}
SQUAWK_PAIRS = {
    "OI": Own("first two squawk digits up", squawk_pair(True, 1)),
    "OD": Own("first two squawk digits down", squawk_pair(True, -1)),
    "II": Own("last two squawk digits up", squawk_pair(False, 1)),
    "ID": Own("last two squawk digits down", squawk_pair(False, -1)),
}
KAP140_VS = Own("VS: leaves ALT hold for VS", parts.KAP140_VS)
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
# flip-flop's amber 121.5 gives way to the panel's MIC 1 and MIC 2 (TALK), as choosing the radio to talk on matters
# more in flight and the IFR-1 has no audio panel.
AMBER = ("BC", "ARM", "MAP", "NRST", "TERR")
TALK = {1: "MIC1", 2: "MIC2"}                  # ⇆ held in COM1 and COM2: talk on that radio


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
    # the lighting: panel dimmer outer, flood dimmer inner, ⇆ the cabin light
    "XPDR^": {**_knob(1, "PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN"),
              "TOG": {"key": Panel(1, "CABIN_LT")}},
}
FMS = {"DCT": "DIRECT", "MENU": "MENU", "CLR": "CLR", "ENT": "ENT", "CDI": "CDI", "OBS": "OBS", "MSG": "MSG",
       "FPL": "FPL", "VNAV": "VNAV", "PROC": "PROC", "CRSR": "FMS_CRSR"}
FMS_KNOB = dict(zip(KNOB, ("FMS_OUTER_CW", "FMS_OUTER_CCW", "FMS_INNER_CW", "FMS_INNER_CCW"), strict=True))
MAP = dict(zip(KNOB, ("RANGE_CW", "RANGE_CCW", "RANGE_CW", "RANGE_CCW"), strict=True))   # clockwise zooms out

# per autopilot part (a profile's PARTS): ⇆ in AP, (tap, hold) of panel buttons, None for nothing
AP_TOG = {"gfc700": ("FLC", "LVL"), "gfc500": ("FLC", "LVL"), "kfc150": ("FD", "YD"), "kap140": (None, None)}
# per autopilot part: an IFR-1 key for which a panel key the autopilot leaves unmapped has a use
AP_OWN = {"kap140": {"VS": KAP140_VS}}
# per navigator part: the panel's units of FMS1 and FMS2 where they are not 1 and 2. The G1000 NXi's unit 1 is its MFD
# (with the panel's COM 1, the radios sharing a knob); the IFR-1 has modes for its radios, so FMS1 is the PFD, as the
# G1000 numbers its displays.
FMS_UNITS = {"navigator-g1000": (2, 1)}
# per profile: the outer ring with ⇆ held in a unit where it does more than repeat the inner ring's range, (↻, ↺) of
# the unit's map buttons: on a GTN its volume knob (the panel's tilt up and down), as the GTN's inner knob is its
# range; the Bonanza's in bonanza_extra()
HELD_OUTER = {"gtn": dict.fromkeys((1, 2), ("PAN_UP", "PAN_DN"))}


def _part(family, kind):
    """The key of the profile's part of this kind (its PARTS, as "autopilot-kap140" -> "kap140")"""
    return next(p.split("-", 1)[1] for p in family.PARTS if p.startswith(f"{kind}-"))


def fms_units(family):
    """(FMS1's unit, FMS2's unit) in the profile"""
    return next((units for p, units in FMS_UNITS.items() if p in family.PARTS), (1, 2))


def amber(device, button):
    """A key's use: the panel key, and held its amber function where that is one of AMBER"""
    shifted = BM.shifted(button)
    return {"key": Panel(device, button), **({"hold": Panel(device, shifted)} if shifted in AMBER else {})}


def uses(key):
    """{IFR-1 button: {use: source}} for the profile of this key. A use is "turn" (a detent), "held" (a detent with
    ⇆ held), "once" (the first detent with ⇆ held, once a hold), "key" (a key's press, or its tap where it has a
    hold), "hold" (a key held), "tap" (⇆ as a modifier, let go at once); a source is a Panel button, an Own code, a
    Plus of both, or None for nothing."""
    family = FAMILIES[key]
    autopilot = _part(family, "autopilot")
    out = {f"Button_{mode}_{ring}": dict(use) for mode, rings in TABLE.items() for ring, use in rings.items()}
    for button, source in HOLDS.items():
        out[button]["hold"] = source
    for com, talk in TALK.items():
        out[f"Button_COM{com}_TOG"] = {"key": Panel(com, "COM_SWAP"), "hold": Panel(1, talk)}
    # AP: the selected altitude 100 ft, with ⇆ held 1000 ft; the inner ring the panel's UP and DN; the push VNV
    for ring, (fine, coarse) in zip(KNOB[:2], (("ALT_100_UP", "ALT_1000_UP"), ("ALT_100_DN", "ALT_1000_DN")),
                                    strict=True):
        out[f"Button_AP_{ring}"] = {"turn": Panel(1, fine), "held": Panel(1, coarse)}
    out["Button_AP_II"] = {"turn": Panel(1, "UP")}
    out["Button_AP_ID"] = {"turn": Panel(1, "DN")}
    out["Button_AP_CRSR"] = {"key": Panel(1, "VNV")}
    tap, hold = AP_TOG[autopilot]
    out["Button_AP_TOG"] = {"tap": tap and Panel(1, tap), "hold": hold and Panel(1, hold)}
    for name in AP_ROW:
        out[f"Button_AP_{name}"] = amber(1, name) if name in ("APR", "ALT") else {"key": Panel(1, name)}
    for name, own in AP_OWN.get(autopilot, {}).items():
        out[f"Button_AP_{name}"] = {"key": own}
    # FMS1 and FMS2: the unit's keys and knob, with ⇆ held its map's range; ⇆ tapped the unit's HOME
    for mode, unit in zip(("FMS1", "FMS2"), fms_units(family), strict=True):
        shift = "S_" if unit == 2 else ""          # a unit's map: unit 2's is on device 1 with SHIFT (part.place)
        held = dict(MAP)
        for ring, button in zip(KNOB[:2], HELD_OUTER.get(key, {}).get(unit, ()), strict=False):
            held[ring] = button
        for ring, button in FMS_KNOB.items():
            out[f"Button_{mode}_{ring}"] = {"turn": Panel(unit, button), "held": Panel(1, shift + held[ring])}
        for ifr1_key, button in FMS.items():
            out[f"Button_{mode}_{ifr1_key}"] = amber(unit, button)
        out[f"Button_{mode}_TOG"] = {"tap": Panel(unit, "HOME"), "hold": None}
    # XPDR: two digits a ring; ⇆ tapped IDENT, held VFR, held and turned the mode (standby or ALT), once a hold
    for ring, own in SQUAWK_PAIRS.items():
        out[f"Button_XPDR_{ring}"] = {"turn": own, "once": Panel(1, "XPDR_MODE")}
    out["Button_XPDR_TOG"] = {"tap": Panel(1, "IDENT"), "hold": Panel(1, "VFR")}
    out["Button_UNSHIFT_SW"] = {"key": None}      # clear(), of the keys with a hold the profile has (build())
    out["Button_SHIFT_SW"] = {"key": None}
    for (button, use), source in EXTRA.get(key, dict)().items():
        out[button][use] = source
    assert set(out) == set(BUTTONS), sorted(set(out) ^ set(BUTTONS))
    return {button: out[button] for button in BUTTONS}


# the reasons of IFR-1 buttons that have no panel source
REASONS = {"Button_SHIFT_SW": "MobiFlight's own shift (the knob push in COM1, COM2, NAV1, NAV2 and XPDR): it changes "
                              "what the knob and ⇆ do, and flashes the mode key's light (firmware 1.2)"}


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
    """What the navigators of a kind (a part of their key: "gtn" TDS's and pms50's GTN, "-tds" TDS's alone, "gns" the
    GNS) among a unit's send for a panel button of their map, joined, each at once (tapped()): "" where none takes it"""
    return " ".join(tapped(n.DEVICE[1][button]) for n in navigators if kind in n.KEY and button in n.DEVICE[1])


# the KFC 150's self-test (its TEST, the guide's counter), only with the autopilot off: a test in flight would disturb
# the engaged autopilot
_SELF_TEST = f"(A:AUTOPILOT MASTER, Bool) ! if{{ {lset('var_AutopilotStartupCounter', 20)} }}"
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
    keys MENU, CLR and ENT of FMS1 or FMS2 (pms50's takes them as its MENU, BACK and ENTER, gtn.py), so each also sends
    TDS's volume up, down and its push (squelch with COM selected, ident with NAV); only TDS's GTN takes those
    (families/black_square_bonanza.py). The outer ring with ⇆ held is the GNS's map range, as the inner ring is, and
    the GTN's volume knob (TDS's and pms50's, as HELD_OUTER has it in the GTN profile), and in FMS1 the KLN 90B's left
    outer knob: the panel's RANGE knob sends the COM volume beside each GTN's, which the GNS takes, so the outer ring
    sends each navigator's own. ⇆ in HDG also sets the HSI's course (NAV 1's, its yellow arrow) to the heading, as it
    sets the heading bug.

    The cockpit's functions go on keys of FMS1 and FMS2, none on a ⇆ that also modifies its ring: a detent of the report
    ⇆ is pressed in comes first and leaves ⇆ to send its hold (docs/using/ifr1.md). CDI held in FMS1 is the HSI's NAV 1
    / RNAV switch (GPSS); in FMS2, VNAV is the DME selector (the GNS 430 has no VNAV key), MENU and PROC the EDM 800's
    STEP and LEAN FIND, its short presses on a tap, as they are pressed often (the GNS 430's MENU, with TDS's GTN 650
    volume up, and PROC, each with pms50's, held instead), and held, ENT the KFC 150's self-test with the autopilot off,
    MSG the oxygen flow valve, FPL both tip tank transfer pumps, OBS prop heat, CDI the fuel boost pump and VNAV the air
    conditioner, from the guide's "Hardware Inputs & Outputs" and the project the Bonanza is flown with. Those keys then
    send their tap on release. The fuel selector stays the cockpit's: a tank is chosen seldom, and a held key should not
    choose one by mistake."""
    units = {1: ("GTN 750", "", black_square_bonanza.UNIT1_NAVIGATORS),
             2: ("GTN 650", "S_", black_square_bonanza.UNIT2_NAVIGATORS)}
    out = {}
    for mode, unit in (("FMS1", 1), ("FMS2", 2)):
        gtn, shift, navigators = units[unit]
        for ifr1_key, button, words in (("MENU", "PAN_UP", "volume up"), ("CLR", "PAN_DN", "volume down"),
                                        ("ENT", "PTR", "volume push: squelch, or ident with NAV")):
            code = _codes(navigators, shift + button, "-tds")
            out[f"Button_{mode}_{ifr1_key}", "key"] = Plus(Panel(unit, ifr1_key), Own(f"TDS {gtn} {words}", code))
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
        ("Button_FMS1_CDI", "hold"): Panel(1, "GPSS"),
        ("Button_FMS2_VNAV", "key"): Panel(1, "LVL"),
        ("Button_FMS2_VNAV", "hold"): Own("air conditioner and blower on or off", _AIR_CONDITIONER),
        ("Button_FMS2_MENU", "hold"): out["Button_FMS2_MENU", "key"],
        ("Button_FMS2_MENU", "key"): Own("EDM 800 STEP", edm["L"]),
        ("Button_FMS2_PROC", "hold"): Panel(2, "PROC"),
        ("Button_FMS2_PROC", "key"): Own("EDM 800 LEAN FIND", edm["R"]),
        ("Button_FMS2_ENT", "hold"): Own("KFC 150 self-test, autopilot off only", _SELF_TEST),
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
    Those keys then send on their release. The fuel selector stays the cockpit's (bonanza_extra()); the DA40 has no
    oxygen, tip tanks or prop heat."""
    return {
        ("Button_FMS2_CDI", "hold"): _ELECTRIC_PUMP,
        ("Button_FMS2_FPL", "hold"): Own("NG fuel transfer pump on or off", "(L:XFER_SWITCH, Bool) ! (>L:XFER_SWITCH)"),
    }


def c182t_extra():
    """{(IFR-1 button, use): source} over the panel's, for Carenado's C182T (EXTRA): CDI held in FMS2, which the G1000
    NXi's MFD leaves free, the electric fuel pump, as the project the C182T is flown with switches it; CDI then sends
    on its release"""
    return {("Button_FMS2_CDI", "hold"): _ELECTRIC_PUMP}


def gtn_extra():
    """{(IFR-1 button, use): source} over the panel's, for TDS's GTNs (EXTRA): MENU, CLR and ENT, which TDS's GTN
    takes only on its touchscreen, its volume knob up and down and its push (squelch with COM selected, ident with
    NAV), the panel's RANGE tilt and push, as in the Bonanza (bonanza_extra())"""
    table = FAMILIES["gtn"].DEVICE[1]
    out = {}
    for mode, shift, gtn in (("FMS1", "", "GTN 750"), ("FMS2", "S_", "GTN 650")):
        for ifr1_key, button, way in (("MENU", "PAN_UP", "up"), ("CLR", "PAN_DN", "down")):   # named by its way
            out[f"Button_{mode}_{ifr1_key}", "key"] = Own(f"{gtn} volume {way}", table[shift + button])
        out[f"Button_{mode}_ENT", "key"] = Panel(1, shift + "PTR")
    return out


# per profile: the IFR-1's uses over the panel's, as a function of no arguments (uses())
EXTRA = {"black-square-bonanza": bonanza_extra, "cows-da40": da40_extra, "carenado-c182t": c182t_extra,
         "gtn": gtn_extra}


def mode(button):
    """The mode an IFR-1 button belongs to, shifted ones with ^ ("Button_COM1^_OI" -> "COM1^"), None for the bottom
    row and SHIFT_SW and UNSHIFT_SW, which every mode shares"""
    match = re.fullmatch(r"Button_([A-Z0-9]+\^?)_(OI|OD|II|ID|TOG|CRSR|DCT|MENU|CLR|ENT|CDI|OBS|MSG|FPL|VNAV|PROC)",
                         button)
    return match[1] if match else None


def held(name, tap, hold):
    """⇆ of the mode name as a modifier: pressed, it sets L:AvionicsPanel_IFR1_<name> and clears its _Turned; let go,
    it sends tap after a tap or hold after a hold (either may be None: nothing), unless a detent came between or the
    mode changed since the press (clear() let go of it), then clears the modifier. With neither, every release only
    clears it."""
    on, turned = _var(name), _var(name, True)

    def end(code):
        return f"(L:{on}, Bool) (L:{turned}, Bool) ! and if{{ {code} }} {lset(on, 0)}" if code else lset(on, 0)
    entry = {"press": f"{lset(on, 1)} {lset(turned, 0)}", "release": end(tap)}
    if tap or hold:
        entry["long"] = end(hold)
    return entry


def knob(name, turn_code, held_code=None, once=False):
    """A detent of the knob of the mode name, whose ⇆ is a modifier: turn_code, or held_code while ⇆ is held (once:
    only on the first detent of a hold). Without held_code (no use with ⇆ held, or one the profile leaves unmapped)
    it sends turn_code whether ⇆ is held or not. Every detent marks the knob turned, so ⇆ let go sends nothing; a
    detent that sends nothing at all is None."""
    on, turned = f"(L:{_var(name)}, Bool)", _var(name, True)
    if held_code and once:
        held_code = f"(L:{turned}, Bool) ! if{{ {held_code} }}"
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
    if source.button in table[source.device]:
        return Use(source, table[source.device][source.button], None)
    return Use(source, None, family.UNMAPPED[source.device][source.button])


def entry(button, used):
    """The table entry of an IFR-1 button from its Uses ({use: Use}), or None where it sends nothing"""
    sent = {use: u.entry for use, u in used.items()}
    name = mode(button)
    if button.endswith("_TOG") and name in MODIFIED:
        return held(name, tapped(sent.get("tap")), tapped(sent.get("hold")))
    if button.rsplit("_", 1)[1] in KNOB:
        turn_code = tapped(sent.get("turn"))
        if name in MODIFIED:
            once = "once" in used
            return knob(name, turn_code, tapped(sent.get("once" if once else "held")), once)
        return turn_code
    plain, hold = sent.get("key"), sent.get("hold")
    if hold is not None and hold != plain:                # a tap and a hold, on the release, if the key went down here
        down = _down(button.removeprefix("Button_"))

        def end(code):
            return f"(L:{down}, Bool) if{{ {code} }} {lset(down, 0)}" if code else lset(down, 0)
        return {"press": lset(down, 1), "release": end(tapped(plain)), "long": end(tapped(hold))}
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
    held in XPDR squawks (profile.tables())."""
    family = FAMILIES[key]
    table = profile.tables(family, vfr)
    device, unmapped, used_by, held_keys = {}, {}, {}, []
    for button, sources in uses(key).items():
        used = {use: resolve(table, family, source) for use, source in sources.items()}
        used_by[button] = used
        sent = entry(button, used)
        if isinstance(sent, dict) and "long" in sent and not (button.endswith("_TOG") and mode(button) in MODIFIED):
            held_keys.append(button.removeprefix("Button_"))
        if sent is not None:
            device[button] = sent
        elif button != "Button_UNSHIFT_SW":
            unmapped[button] = next((u.reason for u in used.values() if u.reason), None) or REASONS[button]
    let_go = clear(held_keys)
    used_by["Button_UNSHIFT_SW"] = {"key": Use(let_go, let_go.code, None)}
    device["Button_UNSHIFT_SW"] = let_go.code
    device = {button: device[button] for button in BUTTONS if button in device}
    return SimpleNamespace(KEY=key, NAME=family.NAME, USES=used_by, DEVICE=device, UNMAPPED=unmapped,
                           LEDS=dict(LEDS[_part(family, "autopilot")]), UNITS=fms_units(family))


def filename(key):
    """An IFR-1 project's file name, by its panel profile's key"""
    return f"avionics-panel-ifr1-{key}.mfproj"


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
            "Name": f"{button.removeprefix('Button_')}: {profile.label(' '.join(acts.values()))}",
            "Type": "InputConfigItem",
            "Controller": controller,
            "Device": {"Type": "Button", "Name": button},
            "button": profile.button_config(acts),
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
