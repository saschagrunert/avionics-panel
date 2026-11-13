"""The workflows and controls of docs/using/controls.md as a pilot uses them, on the simulated panel (sim/). Each
test asserts the buttons MobiFlight sees (polling the joysticks every 31.25 ms), by their BUTTONS.md names, and
that nothing is left pressed at the end. Each runs in keyboard mode too: there the sim must see the shortcuts
(keys.py) of the same functions typed, in the same order, and no key left down."""
import os
import re
import sys
from functools import partial

import pytest

from sim import PATTERN_MS, Sim, canonical

CONTROLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs/using/controls.md")
JOYSTICKS = Sim                        # the joystick mode's Sim, also while a test runs in keyboard mode


@pytest.fixture(autouse=True, params=["joysticks", "keyboard"])
def mode(request, monkeypatch):
    if request.param == "keyboard":
        monkeypatch.setattr(sys.modules[__name__], "Sim", partial(JOYSTICKS, keyboard=True))


def seen(sim, same=True):
    """What MobiFlight saw go down on device 1 and device 2, once it sees nothing held any more. In keyboard mode
    the same scenario also runs with the joysticks, whose presses it returns, after checking that the keyboard
    typed their shortcuts in the same order (a shared shortcut by the function it stands for) and let go. Not
    same: the keyboard's own functions instead (where the loop pass times, which the keyboard's extra report per
    step shifts, decide between a fine and a coarse step)."""
    if sim.keyboard and not same:
        assert sim.reports(1)[-1][1] == bytes(8)
        return tuple([n for _, d, n in sim.typed() if d == device] for device in (1, 2))
    if sim.keyboard:
        joysticks = JOYSTICKS()
        joysticks.script = {ms - PATTERN_MS: actions for ms, actions in sim.script.items()}
        joysticks.now = sim.now - PATTERN_MS
        order = sorted((ms, d, n) for d in (1, 2) for ms, n in joysticks.polled(d))
        assert [(d, n) for _, d, n in sim.typed()] == [canonical(d, n) for _, d, n in order]
        assert sim.reports(1)[-1][1] == bytes(8)
        return seen(joysticks)
    assert sim.held(1) == [] and sim.held(2) == []
    return sim.presses(1), sim.presses(2)


def taps(sim, *keys):
    for key in keys:
        sim.tap(key)


# ---------------- Workflows ----------------
def test_takeoff():
    # turn ALT to the cleared altitude, push the knob (HDG SYNC), press HDG and FLC, hold UP to the climb speed
    sim = Sim()
    sim.turn("ALTHDG_OUTER", 5)
    taps(sim, "ALTHDG_PUSH", "HDG", "FLC")
    sim.press("UP")
    sim.wait(1000)                     # a step at once, the first repeat after 400 ms, then about 8 per second
    sim.release("UP")
    sim.wait(500)
    assert seen(sim) == (["ALT_100_UP"] * 5 + ["HDG_SYNC", "HDG", "FLC"] + ["UP"] * 6, [])


def test_after_takeoff():
    # SHIFT, FD (YD), then AP
    sim = Sim()
    taps(sim, "SHIFT", "FD", "AP")
    assert seen(sim) == (["YD", "AP"], [])


def test_descent():
    # set the new altitude, press VS, hold DN: -1000 ft/min (10 steps) takes about 1.4 s
    sim = Sim()
    sim.turn("ALTHDG_OUTER", -3)
    sim.tap("VS")
    sim.press("DN")
    sim.wait(1500)
    sim.release("DN")
    sim.wait(500)
    assert seen(sim) == (["ALT_100_DN"] * 3 + ["VS"] + ["DN"] * 10, [])


def test_tune_com1():
    # turn outer (MHz) and inner (kHz), then press COM ⇆; the knob starts at COM
    sim = Sim()
    sim.turn("FREQ_OUTER", 2)
    sim.turn("FREQ_INNER", -3)
    sim.tap("COM_SWAP")
    assert seen(sim) == (["COM_MHZ_UP"] * 2 + ["COM_KHZ_DN"] * 3 + ["COM_SWAP"], [])


def test_com_swap_waits_for_the_khz_steps():
    # COM kHz spun six detents in 240 ms, COM ⇆ 100 ms later while steps are still on their way: the swap comes
    # after the last of them, so the frequency it makes active is the one dialled
    sim = Sim()
    sim.turn("FREQ_INNER", 6, every=40)
    sim.wait(100)
    sim.tap("COM_SWAP")
    sim.wait(500)
    assert seen(sim) == (["COM_KHZ_UP"] * 6 + ["COM_SWAP"], [])


def test_tune_nav1():
    # push the FREQ knob for NAV, turn, NAV ⇆
    sim = Sim()
    sim.tap("FREQ_PUSH")
    sim.turn("FREQ_OUTER", 1)
    sim.turn("FREQ_INNER", 2)
    sim.tap("NAV_SWAP")
    assert seen(sim) == (["FREQ_PUSH", "NAV_MHZ_UP"] + ["NAV_KHZ_UP"] * 2 + ["NAV_SWAP"], [])


def test_tune_adf():
    # push twice for ADF: outer 100s, inner 1s (10s when fast), then SHIFT, NAV ⇆ (ADF ⇆)
    sim = Sim()
    taps(sim, "FREQ_PUSH", "FREQ_PUSH")
    sim.turn("FREQ_OUTER", 1)
    sim.turn("FREQ_INNER", 1)
    sim.turn("FREQ_INNER", 3, every=30)
    taps(sim, "SHIFT", "NAV_SWAP")
    assert seen(sim) == (["FREQ_PUSH"] * 2 + ["ADF_100_UP"] + ["ADF_1_UP"] * 2 + ["ADF_10_UP"] * 2 + ["ADF_SWAP"], [])


def test_tune_com2():
    # SHIFT, HOME (UNIT) first for COM 2: the white light comes on, the knob and flip-flop move to device 2
    sim = Sim()
    taps(sim, "SHIFT", "HOME")
    sim.turn("FREQ_INNER", 2)
    sim.tap("COM_SWAP")
    assert seen(sim) == ([], ["COM_KHZ_UP"] * 2 + ["COM_SWAP"])
    assert sim.light("UNIT")[-1][1] > 0


def test_tune_nav2():
    # in unit 2 the FREQ push, the turns and NAV ⇆ go to device 2
    sim = Sim()
    taps(sim, "SHIFT", "HOME", "FREQ_PUSH")
    sim.turn("FREQ_OUTER", -1)
    sim.turn("FREQ_INNER", 1)
    sim.tap("NAV_SWAP")
    assert seen(sim) == ([], ["FREQ_PUSH", "NAV_MHZ_DN", "NAV_KHZ_UP", "NAV_SWAP"])


def test_freq_mode_cycles_and_stays():
    # the push cycles COM, NAV, ADF and back to COM; the mode stays through keys, SHIFT, a squawk entry and a
    # long pause, until the next push
    sim = Sim()
    taps(sim, "FREQ_PUSH", "FREQ_PUSH", "FREQ_PUSH")
    sim.turn("FREQ_INNER", 1)
    sim.tap("FREQ_PUSH")
    taps(sim, "AP", "SHIFT", "SHIFT", "SHIFT")
    sim.turn("FREQ_INNER", 1)
    sim.wait(10_000)
    sim.turn("FREQ_INNER", 1)
    assert seen(sim) == (["FREQ_PUSH"] * 3 + ["COM_KHZ_UP", "FREQ_PUSH", "AP", "SQK_D1_UP", "NAV_KHZ_UP"], [])


def test_squawk():
    # 1200 to 7000: tap SHIFT, the inner ring sets the first digit, one detent of the outer ring moves to the
    # next. 3 s after the last detent the light goes out and the knob tunes again.
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("FREQ_INNER", 6)
    sim.turn("FREQ_OUTER", 1)
    sim.turn("FREQ_INNER", -2)
    last = sim.now - 150                   # the last detent
    sim.wait(3500)
    sim.turn("FREQ_INNER", 1)
    sim.wait(500)
    assert seen(sim) == (["SQK_D1_UP"] * 6 + ["SQK_D2_DN"] * 2 + ["COM_KHZ_UP"], [])
    off, duty = sim.light("SHIFT")[-1]
    assert duty == 0 and last + 3000 <= off <= last + 3000 + sim.pass_ms


def test_squawk_digits():
    # every shifted session starts at the first digit; the outer ring moves on clockwise, back counter-clockwise,
    # and stops at the first and the fourth
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("FREQ_OUTER", 2)
    sim.turn("FREQ_INNER", 1)
    sim.wait(3500)                         # the session ends
    sim.tap("SHIFT")
    sim.turn("FREQ_OUTER", -1)
    sim.turn("FREQ_INNER", 1)
    sim.turn("FREQ_OUTER", 5)
    sim.turn("FREQ_INNER", 1)
    sim.turn("FREQ_OUTER", -1)
    sim.turn("FREQ_INNER", -1)
    assert seen(sim) == (["SQK_D3_UP", "SQK_D1_UP", "SQK_D4_UP", "SQK_D3_DN"], [])


def test_xpdr_mode():
    # SHIFT, FREQ push: XPDR mode
    sim = Sim()
    taps(sim, "SHIFT", "FREQ_PUSH")
    assert seen(sim) == (["XPDR_MODE"], [])


def test_ident_after_a_squawk_entry():
    # SHIFT, VFR (IDENT) with one tap while the knob still keeps SHIFT; VFR alone stays VFR
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("FREQ_INNER", 1)
    taps(sim, "SHIFT", "VFR", "VFR")
    assert seen(sim) == (["SQK_D1_UP", "IDENT", "VFR"], [])


# ---------------- SHIFT ----------------
def test_shift_tapped_again_cancels():
    sim = Sim()
    taps(sim, "SHIFT", "SHIFT", "AP")
    assert seen(sim) == (["AP"], [])


def test_shift_times_out_with_a_pulsing_light():
    # armed SHIFT cancels itself 3 s after the tap; the light pulses between bright and dim in the last second
    sim = Sim()
    sim.tap("SHIFT")
    sim.wait(3000)
    sim.tap("AP")
    assert seen(sim) == (["AP"], [])
    (_, off), (on, full), *pulse, (end, last) = sim.light("SHIFT")
    assert off == last == 0 and 3000 <= end - on <= 3000 + sim.pass_ms
    assert [d for _, d in pulse] == [full // 4, full] * 4
    assert all(end - 1000 - sim.pass_ms <= t < end for t, _ in pulse)


def test_a_key_ends_a_knob_session_and_is_sent_plain():
    # a key pressed while a knob keeps SHIFT is sent plain, and the knob is plain afterwards
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("ALTHDG_OUTER", 1)
    sim.tap("AP")
    sim.turn("ALTHDG_OUTER", 1)
    assert seen(sim) == (["BARO_UP", "AP", "ALT_100_UP"], [])


def test_another_knob_ends_a_knob_session():
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("ALTHDG_OUTER", 1)
    sim.turn("FREQ_INNER", 1)
    sim.turn("ALTHDG_OUTER", 1)
    assert seen(sim) == (["BARO_UP", "COM_KHZ_UP", "ALT_100_UP"], [])


def test_a_held_shifted_push_keeps_shift():
    # a shifted push held longer than 3 s keeps SHIFT, also through a plain key; the 3 s start at its release
    sim = Sim()
    sim.tap("SHIFT")
    sim.press("ALTHDG_PUSH")
    sim.wait(2000)
    sim.tap("AP")
    sim.wait(2000)
    sim.release("ALTHDG_PUSH")
    sim.wait(2500)
    sim.turn("ALTHDG_OUTER", 1)
    assert seen(sim) == (["BARO_STD", "AP", "BARO_UP"], [])


def test_a_held_shifted_tilt_keeps_shift():
    # a shifted pan held for 4 s goes on shifted throughout: at once, after 300 ms, then every 120 ms
    sim = Sim()
    sim.tap("SHIFT")
    sim.tilt("LEFT", hold=4000)
    assert seen(sim) == (["S_PAN_LEFT"] * (1 + len(range(300, 4000, 120))), [])


def test_shifted_keys():
    # each key with SHIFT sends its amber legend from controls.md's key tables, a key without one S_<key>
    # (HOME, UNIT, has a test of its own)
    legend = {"½ BANK": "HALF_BANK", "ADF": "ADF_AUDIO", "NAV 1": "NAV1_AUDIO", "NAV 2": "NAV2_AUDIO",
              "DME": "DME_AUDIO", "121.5": "COM_121_5", "ADF ⇆": "ADF_SWAP"}
    with open(CONTROLS) as f:
        text = f.read().split("\n## Keys")[1].split("\n## ")[0]
    cells = [c.strip() for line in text.splitlines() if line.startswith("| ") and "---" not in line
             for c in line.strip("|").split("|") if c.strip() and not c.strip().startswith("SHIFT")]
    sim, expected = Sim(), []
    for cell in cells:
        label, amber = re.fullmatch(r"(.+?)(?: \((.+)\))?", cell).groups()
        key = label.replace(" ⇆", "_SWAP").replace("D→", "DIRECT").replace(" ", "")
        if key != "HOME":
            taps(sim, "SHIFT", key)
            expected.append(legend.get(amber, amber.replace(" ", "_")) if amber else "S_" + key)
    assert len(expected) == 26 and seen(sim) == (expected, [])


# ---------------- Knobs ----------------
def test_alt_and_hdg_accelerate():
    # the first detent of a turn makes the fine step, detents within 60 ms after it the coarse one
    sim = Sim()
    sim.turn("ALTHDG_OUTER", 4, every=40)
    sim.wait(1000)
    sim.turn("ALTHDG_INNER", 2)
    sim.turn("ALTHDG_INNER", -4, every=40)
    sim.wait(1000)
    assert seen(sim) == (["ALT_100_UP"] + ["ALT_1000_UP"] * 3 + ["HDG_1_UP"] * 2 + ["HDG_1_DN"] + ["HDG_10_DN"] * 3,
                         [])


def test_a_flick_makes_both_detents_coarse():
    # two detents in one pass of the loop
    sim = Sim()
    sim.turn("ALTHDG_OUTER", 2, every=0)
    sim.wait(500)
    assert seen(sim) == (["ALT_1000_UP"] * 2, [])


def test_baro_and_std():
    # SHIFT, the outer ring sets BARO; the push, still shifted, sets standard
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("ALTHDG_OUTER", 3)
    sim.tap("ALTHDG_PUSH")
    assert seen(sim) == (["BARO_UP"] * 3 + ["BARO_STD"], [])


def test_crs_and_crs_ctr():
    # SHIFT, the inner knob sets CRS, fast in 10° steps; CRS CTR is SHIFT, HDG, one tap while the knob keeps SHIFT
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("ALTHDG_INNER", 2)
    sim.turn("ALTHDG_INNER", 3, every=40)
    sim.wait(500)
    taps(sim, "SHIFT", "HDG")
    assert seen(sim) == (["CRS_1_UP"] * 3 + ["CRS_10_UP"] * 2 + ["CRS_CTR"], [])


def test_unit():
    # SHIFT, HOME switches to unit 2 and back: the FMS keys go to device 2 meanwhile, AP stays on device 1
    sim = Sim()
    taps(sim, "SHIFT", "HOME", "DIRECT", "AP", "SHIFT", "HOME", "DIRECT")
    assert seen(sim) == (["AP", "DIRECT"], ["DIRECT"])
    assert [duty > 0 for _, duty in sim.light("UNIT")] == [False, True, False]


def test_cdi_and_obs_follow_unit():
    sim = Sim()
    taps(sim, "CDI", "SHIFT", "HOME", "CDI", "SHIFT", "CDI")
    assert seen(sim) == (["CDI"], ["CDI", "OBS"])


def test_fms_knob():
    # outer ring page group, inner ring page, push cursor; in unit 2 all on device 2
    sim = Sim()
    sim.turn("FMS_OUTER", 1)
    sim.turn("FMS_INNER", -1)
    sim.tap("FMS_PUSH")
    taps(sim, "SHIFT", "HOME")
    sim.turn("FMS_OUTER", -1)
    sim.turn("FMS_INNER", 1)
    sim.tap("FMS_PUSH")
    assert seen(sim) == (["FMS_OUTER_CW", "FMS_INNER_CCW", "FMS_CRSR"], ["FMS_OUTER_CCW", "FMS_INNER_CW", "FMS_CRSR"])


def test_ent_waits_for_the_fms_steps():
    # a character dialled with five quick detents of the inner ring, ENT 150 ms later, then the next character:
    # ENT confirms the finished entry, and the next steps follow it
    sim = Sim()
    sim.turn("FMS_INNER", 5, every=30)
    sim.wait(150)
    sim.tap("ENT")
    sim.turn("FMS_INNER", 2, every=30)
    sim.wait(500)
    assert seen(sim) == (["FMS_INNER_CW"] * 5 + ["ENT"] + ["FMS_INNER_CW"] * 2, [])


def test_the_outer_ring_waits_for_the_inner_one():
    # four quick detents of the inner ring finish the character before one of the outer ring moves the cursor
    sim = Sim()
    sim.turn("FMS_INNER", 4, every=30)
    sim.turn("FMS_OUTER", 1, every=30)
    sim.wait(1000)
    assert seen(sim) == (["FMS_INNER_CW"] * 4 + ["FMS_OUTER_CW"], [])


def test_a_medium_speed_turn_stops_with_the_hand():
    # HDG turned 30 detents at 75 ms each: too slow for the coarse step by time, faster than fine steps go out
    # (112 ms each). Every detent arrives as one step, fine or coarse, and the last one is released within
    # 180 ms of the last detent: nothing is lost and the knob does not run on
    sim = Sim()
    sim.turn("ALTHDG_INNER", 30, every=75)
    last = sim.now - 75
    sim.wait(1500)
    names = seen(sim, same=False)[0]
    assert len(names) == 30 and names[0] == "HDG_1_UP" and set(names) == {"HDG_1_UP", "HDG_10_UP"}
    assert max(t for t, names in sim.buttons(1) if not names) <= last + 180


def test_fast_fms_spin_keeps_every_detent():
    # one page per detent, no acceleration: 8 detents in 160 ms reach the PC as 8 steps
    sim = Sim()
    sim.turn("FMS_INNER", 8, every=20)
    sim.wait(1000)
    assert seen(sim) == (["FMS_INNER_CW"] * 8, [])


def test_turning_back_stops_the_knob_at_once():
    # a fast spin queues detents; turning the other way drops the ones not sent yet (firmware.md): turned back
    # 180 ms after the first detent, while the second step is on its way
    sim = Sim()
    sim.turn("FMS_INNER", 6, every=20)
    sim.wait(60)
    sim.turn("FMS_INNER", -1)
    sim.wait(1000)
    assert seen(sim) == (["FMS_INNER_CW"] * 2 + ["FMS_INNER_CCW"], [])


def test_turning_back_in_another_function_keeps_the_steps_of_the_one_before():
    # ALT spun eight detents, SHIFT, and the same ring one detent back, now BARO, while ALT steps still wait: a
    # step back only stops its own function, so all eight ALT steps reach the PC. The same across a UNIT change:
    # COM 1's six kHz steps stay when the ring then turns back for COM 2
    sim = Sim()
    sim.turn("ALTHDG_OUTER", 8, every=40)
    sim.tap("SHIFT", then=50)
    sim.turn("ALTHDG_OUTER", -1)
    sim.wait(1500)
    assert seen(sim) == (["ALT_100_UP"] + ["ALT_1000_UP"] * 7 + ["BARO_DN"], [])
    sim = Sim()
    sim.turn("FREQ_INNER", 6, every=40)
    sim.tap("SHIFT", then=50)
    sim.tap("HOME", then=50)
    sim.turn("FREQ_INNER", -2)
    sim.wait(1500)
    assert seen(sim) == (["COM_KHZ_UP"] * 6, ["COM_KHZ_DN"] * 2)


@pytest.mark.parametrize("offset", range(0, 20, 3))
def test_shift_and_a_key_within_one_scan(offset):
    # SHIFT and, 5 ms later, FD (YD), then AP; SHIFT and HOME (UNIT) the same way. Whether or not one 19.5 ms key
    # scan reads both presses, SHIFT comes first: YD, not FD with SHIFT left armed for AP; UNIT, not the HOME page
    sim = Sim()
    sim.wait(offset)
    for key in ("FD", "HOME"):
        sim.press("SHIFT")
        sim.wait(5)
        sim.press(key)
        sim.wait(100)
        sim.release("SHIFT")
        sim.release(key)
        sim.wait(300)
        sim.tap("AP")
    assert seen(sim) == (["YD", "AP", "AP"], [])
    assert [duty > 0 for _, duty in sim.light("UNIT")] == [False, True]


def test_cockpit_lighting():
    # SHIFT, FMS knob: outer panel lights, inner flood, push cabin light; on device 1 in either unit (mapping.md)
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("FMS_OUTER", 2)
    sim.turn("FMS_INNER", -1)
    sim.tap("FMS_PUSH")
    taps(sim, "SHIFT", "HOME", "SHIFT")
    sim.turn("FMS_INNER", 1)
    assert seen(sim) == (["PANEL_LT_UP"] * 2 + ["FLOOD_LT_DN", "CABIN_LT", "FLOOD_LT_UP"], [])


def test_a_fast_double_tap_stays_two_presses():
    # CLR twice as fast as a finger can (firmware.md)
    sim = Sim()
    for _ in range(2):
        sim.tap("CLR", hold=40, then=60)
    sim.wait(300)
    assert seen(sim) == (["CLR", "CLR"], [])


def test_range_pan_pointer_and_zoom():
    # a tilt held pans at once, after 300 ms, then every 120 ms; the push is the pointer; turning zooms
    sim = Sim()
    sim.tilt("LEFT", hold=700)
    sim.tap("RANGE_COM")
    sim.turn("RANGE", -2)
    sim.turn("RANGE", 1)
    assert seen(sim) == (["PAN_LEFT"] * 5 + ["PTR"] + ["RANGE_CCW"] * 2 + ["RANGE_CW"], [])


def test_a_slow_tilt_sends_no_pointer():
    # on a slow tilt the centre closes before the direction: a pan, no PTR
    sim = Sim()
    sim.press("RANGE_COM")
    sim.wait(60)
    sim.press("RANGE_A")
    sim.wait(100)
    sim.release("RANGE_A")
    sim.release("RANGE_COM")
    sim.wait(300)
    assert seen(sim) == (["PAN_UP"], [])


def test_shifted_range_buttons():
    # the RANGE knob with SHIFT sends buttons of its own, free for own mappings
    sim = Sim()
    sim.tap("SHIFT")
    sim.turn("RANGE", 1)
    sim.tap("RANGE_COM")
    sim.tilt("DN")
    assert seen(sim) == (["S_RANGE_CW", "S_PTR", "S_PAN_DN"], [])
