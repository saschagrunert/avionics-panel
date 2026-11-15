"""Host tests for panel.py: run pytest from the repository root."""
import buttonmap as BM
import panel as P

REPORTS = {d: bytearray(BM.SIZE[d] // 8) for d in (1, 2)}


def down(panel, dev):
    """the names of the buttons a panel has pressed on a device, read from the report code.py would send"""
    report = REPORTS[dev]
    panel.fill_report(dev, report)
    return {BM.DEVICE[dev][8 * i + b] for i, byte in enumerate(report) if byte for b in range(8) if byte >> b & 1}


class Sim:
    def __init__(self, solo=False):
        self.p, self.t, self.seen, self.log = P.Panel(solo), 0, [], []
        self.prev = {1: set(), 2: set()}

    def down(self, dev):
        return down(self.p, dev)

    def run(self, ms):
        """advance time, record every button press edge as (device, name) in seen, and as (ms, device, name) in
        log, the presses of one ms in the order of their button numbers"""
        for _ in range(ms):
            self.t += 1
            self.p.tick(self.t)
            for d in (1, 2):
                now = self.down(d)
                for name in sorted(now - self.prev[d], key=BM.BUTTON[d].get):
                    self.seen.append((d, name))
                    self.log.append((self.t, d, name))
                self.prev[d] = now

    def key(self, name, ms=60):
        self.p.key(name, True, self.t); self.run(ms); self.p.key(name, False, self.t); self.run(ms)

    def turn(self, ring, steps, every=200):
        for _ in range(abs(steps)):
            self.p.turn(ring, 1 if steps > 0 else -1, self.t); self.run(every)

    def take(self):
        s, self.seen = self.seen, []
        return s


def test_shift_one_shot():
    s = Sim()
    s.key("AP"); assert s.take() == [(1, "AP")]
    s.key("SHIFT"); assert s.p.shift_active(s.t)
    s.key("AP"); assert s.take() == [(1, "TEST")] and not s.p.shift_active(s.t)
    s.key("AP"); assert s.take() == [(1, "AP")]
    s.key("SHIFT"); s.key("VS"); assert s.take() == [(1, "S_VS")]      # no amber legend: own shifted button
    s.key("SHIFT"); s.key("SHIFT"); s.key("AP"); assert s.take() == [(1, "AP")]   # second tap cancels
    s.key("SHIFT"); s.run(P.ARM_MS + 100); assert not s.p.shift_active(s.t); s.key("AP"); assert s.take() == [(1, "AP")]
    s.key("SHIFT"); s.turn("FREQ_INNER", 1); s.take()                   # squawk set, light still on
    s.key("SHIFT"); s.key("VFR"); assert s.take() == [(1, "IDENT")]       # one tap arms SHIFT for the key


def test_vfr_key_after_a_squawk_entry():
    # VFR is the plain function: right after a squawk entry (the knob still holds SHIFT) the key sends VFR;
    # to ident, tap SHIFT first
    s = Sim()
    s.key("SHIFT"); s.turn("FREQ_OUTER", 1); s.take()
    s.key("VFR"); assert s.take() == [(1, "VFR")]
    s.key("SHIFT"); s.turn("FREQ_INNER", 1); s.take()
    s.key("SHIFT"); s.key("VFR"); assert s.take() == [(1, "IDENT")]


def test_knob_keeps_shift():
    s = Sim()
    s.key("SHIFT")
    s.turn("FREQ_INNER", 2, every=500); s.turn("FREQ_OUTER", 1, every=500)   # both rings, for a whole squawk code
    s.turn("FREQ_INNER", 1, every=500)
    assert [n for _, n in s.take()] == ["SQK_D1_UP", "SQK_D1_UP", "SQK_D2_UP"]
    assert s.p.shift_active(s.t)
    s.run(P.SESSION_MS); assert not s.p.shift_active(s.t)
    s.turn("FREQ_OUTER", 1); assert s.take() == [(1, "COM_MHZ_UP")]
    s.key("SHIFT"); s.turn("ALTHDG_INNER", 1); s.key("AP")              # a key after a knob session: normal
    assert [n for _, n in s.take()] == ["CRS_1_UP", "AP"]


def test_a_pause_between_squawk_digits_stays_in_the_entry():
    # the code read off a clearance between two digits: 4 s after the inner ring, the outer ring moves on to the
    # next digit, and 4 s after that the inner ring sets it. Still the squawk, not COM: the session outlasts
    # the pause
    s = Sim()
    s.key("SHIFT")
    s.p.turn("FREQ_INNER", 1, s.t); s.run(4000)
    s.p.turn("FREQ_OUTER", 1, s.t); s.run(4000)
    s.p.turn("FREQ_INNER", 1, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["SQK_D1_UP", "SQK_D2_UP"] and s.p.shift_active(s.t)


def test_a_knob_session_ends_session_ms_after_its_last_detent():
    # longer than a tap's ARM_MS; each detent starts it over, one read at SESSION_MS - 1 is still shifted,
    # one at SESSION_MS plain, and the light goes out then
    s = Sim()
    s.key("SHIFT"); s.p.turn("ALTHDG_OUTER", 1, s.t)
    s.run(P.ARM_MS); assert s.p.shift_active(s.t)
    s.run(P.SESSION_MS - P.ARM_MS - 1); assert s.p.shift_active(s.t)
    s.p.turn("ALTHDG_OUTER", 1, s.t); s.run(P.SESSION_MS - 1)
    assert s.p.shift_active(s.t) and s.p.shift_level(s.t) != P.LIGHT_OFF
    s.run(1); assert not s.p.shift_active(s.t) and s.p.shift_level(s.t) == P.LIGHT_OFF
    s.p.turn("ALTHDG_OUTER", 1, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["BARO_UP", "BARO_UP", "ALT_100_UP"]


def test_an_armed_shift_ends_arm_ms_after_the_tap():
    # a stray tap does not linger as a knob session does: with no input, the key read at ARM_MS - 1 is
    # shifted, the one at ARM_MS plain, and the light goes out then
    for wait, sent in ((P.ARM_MS - 1, "IDENT"), (P.ARM_MS, "VFR")):
        s = Sim()
        s.p.key("SHIFT", True, s.t); s.run(30); s.p.key("SHIFT", False, s.t); s.run(wait - 30)
        assert (s.p.shift_level(s.t) != P.LIGHT_OFF) == (wait < P.ARM_MS), wait
        s.key("VFR"); assert s.take() == [(1, sent)], wait


def light_trace(s, end):
    """(ms left, light level, SHIFT applies) every ms until shortly after SHIFT drops at `end`"""
    out = []
    while s.t < end + 50:
        s.run(1)
        out.append((end - s.t, s.p.shift_level(s.t), s.p.shift_active(s.t)))
    return out


def check_pulse(trace, warn=P.SHIFT_WARN_MS, pulse=P.SHIFT_PULSE_MS):
    full, dim = P.LIGHT_FULL, P.LIGHT_DIM
    assert all(v == full for left, v, _ in trace if left > warn)                # steady until the warning
    assert [v for left, v, _ in trace if left == warn] == [dim]                 # which starts dim, on time
    last = [v for left, v, _ in trace if 0 < left <= warn]
    assert last.count(dim) == warn // 2                                         # half of it dim
    assert sum(a != b for a, b in zip(last, last[1:])) == warn // pulse - 1     # one change per phase
    assert all(v == full for left, v, _ in trace if 0 < left <= pulse)          # last phase bright
    assert all(v != P.LIGHT_OFF for _, v, on in trace if on)                    # never dark while SHIFT applies
    assert all(v == P.LIGHT_OFF and not on for left, v, on in trace if left <= 0)   # off once it dropped


def test_shift_light_pulses_before_a_knob_drops_it():
    s = Sim()
    s.key("SHIFT"); s.p.turn("FREQ_OUTER", 1, s.t)       # a knob session: drops SESSION_MS after this detent
    check_pulse(light_trace(s, s.t + P.SESSION_MS))


def test_a_tap_in_a_knob_session_arms_for_arm_ms_from_the_tap():
    # SHIFT tapped 500 ms after a squawk entry: armed for the next key, ARM_MS from the tap with its warning,
    # not the rest of the knob's session; then the FREQ inner ring tunes COM again
    s = Sim()
    s.key("SHIFT"); s.turn("FREQ_INNER", 1); s.run(500)
    s.p.key("SHIFT", True, s.t); tapped = s.t
    check_pulse(light_trace(s, tapped + P.ARM_MS))
    s.take(); s.turn("FREQ_INNER", 1)
    assert s.take() == [(1, "COM_KHZ_UP")]


def test_shift_light_pulses_before_an_armed_shift_drops():
    s = Sim()
    s.p.key("SHIFT", True, s.t)                          # armed, no key follows: drops ARM_MS after the press
    check_pulse(light_trace(s, s.t + P.ARM_MS))


def test_shift_light_pulses_before_a_released_push_drops_it():
    # a shifted push held past SESSION_MS, then let go: the session's SESSION_MS from the release, with its
    # warning, as after a detent
    s = Sim()
    s.key("SHIFT"); s.p.key("ALTHDG_PUSH", True, s.t); s.run(P.SESSION_MS + 1000)
    s.p.key("ALTHDG_PUSH", False, s.t); released = s.t
    s.run(P.BOUNCE_MS + 1)                               # the release is applied: no more extension
    end = s.p.shift_until
    assert released + P.SESSION_MS <= end <= released + P.BOUNCE_MS + P.SESSION_MS
    check_pulse(light_trace(s, end))


def test_pulse_follows_other_timings(monkeypatch):
    monkeypatch.setattr(P, "SHIFT_PULSE_MS", 100)        # 5 dim/bright pairs instead of 4
    s = Sim()
    s.p.key("SHIFT", True, s.t)
    check_pulse(light_trace(s, s.t + P.ARM_MS), pulse=100)


def test_light_is_off_once_shift_runs_out_even_before_tick():
    s = Sim()
    end = s.t + P.ARM_MS
    s.key("SHIFT")
    assert s.p.shift_level(end - 1) == P.LIGHT_FULL      # still applies: last phase bright
    assert s.p.shift_level(end) == P.LIGHT_OFF and s.p.shift_level(end + 5) == P.LIGHT_OFF


def test_inputs_read_after_shift_ran_out_are_plain():
    # inputs read after the end of SHIFT before a tick() has seen it, in a pass that did not wait for the host
    # (no stalled()): plain, as the light shows from then on
    s = Sim()
    s.key("SHIFT"); s.p.turn("FREQ_OUTER", 1, s.t)
    s.t += P.SESSION_MS + 30                             # stalled: time passed, no tick() ran
    s.turn("FREQ_OUTER", 1)                              # a late detent: plain, and no new session
    assert s.take() == [(1, "COM_MHZ_UP")] and not s.p.shift_active(s.t)
    s.p.key("SHIFT", True, s.t)
    s.t += P.ARM_MS + 30
    s.key("AP")                                          # a late key: plain
    assert s.take() == [(1, "AP")]


def test_shift_never_applies_while_dark():
    # code.py sets dark while USB is down and the lights are off: an armed SHIFT ends, a knob's session too,
    # a SHIFT tap does nothing, and nothing of it comes back when the lights do. UNIT stays as it is
    s = Sim()
    s.key("SHIFT"); s.key("HOME"); assert s.p.unit_light
    for arm in (lambda: s.key("SHIFT"), lambda: (s.key("SHIFT"), s.turn("ALTHDG_OUTER", 1), s.take())):
        arm()
        assert s.p.shift_level(s.t) == P.LIGHT_FULL
        s.p.dark = True
        assert s.p.shift_level(s.t) == P.LIGHT_OFF and not s.p.shift_active(s.t)
        s.key("SHIFT"); assert s.p.shift_level(s.t) == P.LIGHT_OFF
        s.key("AP"); s.turn("ALTHDG_OUTER", 1); s.key("SHIFT"); s.key("HOME")
        assert s.take() == [(1, "AP"), (1, "ALT_100_UP"), (2, "HOME")]
        s.p.dark = False
        s.run(1); assert s.p.shift_level(s.t) == P.LIGHT_OFF and s.p.unit_light
        s.key("AP"); s.turn("ALTHDG_OUTER", 1)
        assert s.take() == [(1, "AP"), (1, "ALT_100_UP")]


def test_a_shifted_hold_stops_while_dark():
    # a shifted tilt held while the lights go dark: its S_PAN steps stop with SHIFT, and its release sends
    # nothing; a shifted centre push held through it still sends S_PTR, as it was pressed
    s = Sim()
    hold_shifted_tilt(s); s.take()
    s.p.dark = True
    rest = light_and_edges(s, 2000)
    assert all(level == P.LIGHT_OFF for level, _ in rest) and not any(names for _, names in rest[P.PRESS_MS:])
    s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(500)
    assert s.take() == []
    s = Sim()
    s.key("SHIFT"); s.p.key("RANGE_COM", True, s.t); s.run(100)
    s.p.dark = True
    s.run(500); s.p.key("RANGE_COM", False, s.t); s.run(200)
    assert s.take() == [(1, "S_PTR")]


def test_acceleration():
    s = Sim()
    s.turn("ALTHDG_OUTER", 3, every=200); assert {n for _, n in s.take()} == {"ALT_100_UP"}
    s.turn("ALTHDG_OUTER", -4, every=30); s.run(1000)                    # fast spin: first detent slow, rest coarse
    names = [n for _, n in s.take()]
    assert len(names) == 4, names
    assert names[0] == "ALT_100_DN" and set(names[1:]) == {"ALT_1000_DN"}, names
    s.turn("FMS_INNER", 5, every=30); s.run(1000)                        # no acceleration on the FMS knob
    assert [n for _, n in s.take()] == ["FMS_INNER_CW"] * 5


def test_alt_hdg_knob_with_shift_sets_baro_and_crs():
    # with SHIFT the outer ring is BARO, one step per detent however fast the turn, and the inner ring is CRS:
    # 1 degree, or 10 degrees on a fast turn. The push is STD, and both rings and the push are one session
    s = Sim()
    s.key("SHIFT")
    s.turn("ALTHDG_OUTER", 2); s.turn("ALTHDG_INNER", -1); s.key("ALTHDG_PUSH")
    assert s.take() == [(1, "BARO_UP"), (1, "BARO_UP"), (1, "CRS_1_DN"), (1, "BARO_STD")]
    s.turn("ALTHDG_OUTER", -3, every=P.FAST_MS // 2); s.run(500)
    assert [n for _, n in s.take()] == ["BARO_DN"] * 3
    s.turn("ALTHDG_INNER", 3, every=P.FAST_MS // 2); s.run(500)
    assert [n for _, n in s.take()] == ["CRS_1_UP", "CRS_10_UP", "CRS_10_UP"]
    s.run(P.SESSION_MS)
    s.turn("ALTHDG_OUTER", 1); s.turn("ALTHDG_INNER", 1)                  # the session ran out: ALT and HDG
    assert s.take() == [(1, "ALT_100_UP"), (1, "HDG_1_UP")]


def test_the_step_tables_name_buttons():
    # turn() takes its buttons from tables made at import, so a detent builds no strings: each names a button,
    # with an up and a down step per function
    assert P.STEP_UP.keys() == P.STEP_DN.keys()
    assert all({P.STEP_UP[f], P.STEP_DN[f]} <= set(BM.BUTTON[1]) for f in P.STEP_UP)
    assert {P.KNOB[n] for n in P.RINGS + P.PUSHES} == {"ALTHDG", "FREQ", "FMS", "RANGE"}


def test_a_turn_of_no_detents_does_nothing():
    # code.py only passes on a ring that moved, so turn() never gets 0 on the board. If it does, that is no
    # detent: nothing is sent, and an armed SHIFT stays for the next key
    s = Sim()
    s.key("SHIFT"); s.p.turn("FREQ_INNER", 0, s.t); s.run(200)
    assert s.take() == []
    s.key("AP"); assert s.take() == [(1, "TEST")]


def test_fms_knob_with_shift_dims_the_lights():
    s = Sim()
    s.turn("FMS_OUTER", 1); assert s.take() == [(1, "FMS_OUTER_CW")]
    s.key("SHIFT")
    s.turn("FMS_OUTER", 2); s.turn("FMS_INNER", -1); s.key("FMS_PUSH")   # one session: both rings and push
    assert s.take() == [(1, "PANEL_LT_UP"), (1, "PANEL_LT_UP"), (1, "FLOOD_LT_DN"), (1, "CABIN_LT")]
    s.turn("FMS_OUTER", 2, every=30); s.run(200)                          # fast turn: still one step each
    assert s.take() == [(1, "PANEL_LT_UP"), (1, "PANEL_LT_UP")]
    s.run(P.SESSION_MS)
    s.key("SHIFT"); s.key("HOME")                                         # unit 2: lighting stays on device 1
    s.key("SHIFT"); s.turn("FMS_INNER", 1); s.key("FMS_PUSH")
    assert s.take() == [(1, "FLOOD_LT_UP"), (1, "CABIN_LT")]
    s.run(P.SESSION_MS)
    s.turn("FMS_INNER", 1); s.key("FMS_PUSH")                             # plain FMS knob follows the unit
    assert s.take() == [(2, "FMS_INNER_CW"), (2, "FMS_CRSR")]


def test_unit_and_freq_modes():
    s = Sim()
    s.key("COM_SWAP"); assert s.take() == [(1, "COM_SWAP")]
    s.key("HOME"); assert not s.p.unit_light and s.take() == [(1, "HOME")]   # plain HOME: the GTN key
    s.key("SHIFT"); s.key("HOME"); assert s.p.unit_light and s.take() == []
    s.key("HOME"); assert s.p.unit_light and s.take() == [(2, "HOME")]
    s.key("COM_SWAP"); s.key("AP"); assert s.take() == [(2, "COM_SWAP"), (1, "AP")]
    s.key("FREQ_PUSH"); assert s.take() == [(2, "FREQ_PUSH")]
    s.turn("FREQ_INNER", 1); assert s.take() == [(2, "NAV_KHZ_UP")]
    s.key("FREQ_PUSH"); s.turn("FREQ_INNER", -1); assert s.take() == [(2, "FREQ_PUSH"), (2, "ADF_1_DN")]
    s.key("SHIFT"); s.key("HOME"); assert not s.p.unit_light
    s.key("SHIFT"); s.key("FREQ_PUSH"); assert s.take() == [(1, "XPDR_MODE")]
    s.run(P.SESSION_MS); s.turn("FREQ_OUTER", 1); assert s.take() == [(1, "ADF_100_UP")]   # the mode stayed
    s.key("FREQ_PUSH"); s.turn("FREQ_OUTER", 1); assert s.take() == [(1, "FREQ_PUSH"), (1, "COM_MHZ_UP")]


def test_freq_mode_survives_a_long_pause():
    # the mode is sticky: only the push changes it, however long the knob is left alone
    s = Sim()
    s.key("FREQ_PUSH"); s.take()
    s.run(20000)                                         # long after the push
    s.turn("FREQ_INNER", 1)
    assert s.take() == [(1, "NAV_KHZ_UP")]


def test_holding_the_freq_push_returns_it_to_com():
    # from every mode, and in the keyboard mode too: the press cycles as before and is held as before, and once
    # held FREQ_HOLD_MS the knob tunes COM; a shorter push only cycles
    for solo in (False, True):
        for start in range(len(P.FREQ_MODES)):
            for held, mode in ((P.FREQ_HOLD_MS - 1, (start + 1) % 3), (P.FREQ_HOLD_MS, 0), (5000, 0)):
                s = Sim(solo)
                for _ in range(start):
                    s.key("FREQ_PUSH")
                s.take()
                s.p.key("FREQ_PUSH", True, s.t); s.run(held)
                assert s.p.freq_mode == mode and s.down(1) == {"FREQ_PUSH"}, (solo, start, held)
                s.p.key("FREQ_PUSH", False, s.t); s.run(500)
                s.turn("FREQ_INNER", 1)
                assert s.take() == [(1, "FREQ_PUSH"), (1, P.FREQ_MODES[mode][1] + "_UP")], (solo, start, held)


def test_a_freq_push_released_in_time_is_short_while_its_release_waits_out_the_bounce():
    # the hold counts until the scan of the release, not until it is applied BOUNCE_MS later; a bounce in
    # between does not start the hold again
    for release, mode in ((P.FREQ_HOLD_MS - 1, 1), (P.FREQ_HOLD_MS, 0)):
        s = Sim()
        s.p.key("FREQ_PUSH", True, s.t); s.run(release)
        s.p.key("FREQ_PUSH", False, s.t); s.run(P.BOUNCE_MS + 10)
        assert s.p.freq_mode == mode, release
    s = Sim()
    s.p.key("FREQ_PUSH", True, s.t); s.run(500)
    s.p.key("FREQ_PUSH", False, s.t); s.run(10); s.p.key("FREQ_PUSH", True, s.t)   # a bounce: still held
    s.run(P.FREQ_HOLD_MS - 510)
    assert s.p.freq_mode == 0 and s.take() == [(1, "FREQ_PUSH")]


def test_another_push_released_under_a_held_freq_push_keeps_its_hold():
    s = Sim()
    s.p.key("FREQ_PUSH", True, s.t); s.run(100)
    s.key("ALTHDG_PUSH", 100)
    s.run(P.FREQ_HOLD_MS)
    assert s.p.freq_mode == 0


def test_a_shifted_freq_push_held_stays_xpdr_mode_and_keeps_the_mode():
    s = Sim()
    s.key("FREQ_PUSH"); s.take()                                         # NAV
    s.key("SHIFT"); s.p.key("FREQ_PUSH", True, s.t); s.run(2000)
    s.turn("FREQ_INNER", 1); s.p.key("FREQ_PUSH", False, s.t); s.run(P.SESSION_MS + 100)
    assert s.p.freq_mode == 1 and s.take() == [(1, "XPDR_MODE"), (1, "SQK_D1_UP")]
    s.turn("FREQ_INNER", 1); assert s.take() == [(1, "NAV_KHZ_UP")]


def test_a_freq_turn_ends_the_hold():
    # a push held while the FREQ knob turns changes no radio under the hand: the turn tunes the mode the push
    # stepped to, and the hold no longer returns to COM
    s = Sim()
    s.p.key("FREQ_PUSH", True, s.t); s.run(P.FREQ_HOLD_MS - 20)          # NAV
    s.p.turn("FREQ_INNER", 8, s.t); s.run(2000)                           # NAV steps, no COM at 1 s
    s.p.turn("FREQ_INNER", -1, s.t)
    s.p.key("FREQ_PUSH", False, s.t); s.run(2000)
    assert s.take() == [(1, "FREQ_PUSH")] + [(1, "NAV_KHZ_UP")] * 8 + [(1, "NAV_KHZ_DN")]


def test_a_hold_read_late_with_its_turn_still_returns_to_com():
    # after a wait for the host the loop reads a long hold and the turn after it at once: the hold counts first,
    # so the turn tunes COM
    s = Sim()
    s.t = 4000
    s.p.key("FREQ_PUSH", True, s.t, at=2000)                               # NAV, held 1.5 s by the scans
    s.p.key("FREQ_PUSH", False, s.t, at=3500)
    s.p.turn("FREQ_INNER", 1, s.t); s.run(500)
    assert s.p.freq_mode == 0 and (1, "COM_KHZ_UP") in s.take()


def test_a_hold_read_late_returns_to_com():
    # after a wait for the host the loop reads a long hold at once, and then only ticks, or reads the next press:
    # the hold counts before its release ends the push
    for then in ("tick", "press"):
        s = Sim()
        s.t = 4000
        s.p.key("FREQ_PUSH", True, s.t, at=2000)                           # NAV, held 1.5 s by the scans
        s.p.key("FREQ_PUSH", False, s.t, at=3500)
        if then == "press":
            s.p.key("FREQ_PUSH", True, s.t, at=3990)                       # a new push from COM: NAV, not ADF
            assert s.p.freq_mode == 1
        else:
            s.p.tick(s.t)
            assert s.p.freq_mode == 0


def test_a_hold_counts_before_a_release_after_a_keypad_overflow():
    # code.py lets go of every key after a keypad overflow, at once: a push held long enough returns to COM first
    s = Sim()
    s.p.key("FREQ_PUSH", True, s.t)                                        # NAV
    s.t += P.FREQ_HOLD_MS + 500                                            # a wait for the host: no tick
    s.p.release("FREQ_PUSH", s.t)
    assert s.p.freq_mode == 0


def test_a_freq_hold_runs_from_the_scan_of_its_press():
    # a press the loop reads late (after a wait for the host) is held from its scan, as its release is: held
    # 1.5 s by the scans, it returns to COM, though the loop read it only 0.5 s before the release
    s = Sim()
    s.t = 3000
    s.p.key("FREQ_PUSH", True, s.t, at=s.t - 1000); s.run(500)            # scanned at 2000, read at 3000: NAV
    s.p.key("FREQ_PUSH", False, s.t); s.run(100)                           # released at 3500
    assert s.p.freq_mode == 0


def squawk(s):
    """SHIFT, then one detent of the FREQ inner ring: a new squawk entry, on digit 1"""
    s.key("SHIFT"); s.turn("FREQ_INNER", 1)


def test_squawk_entry_of_a_whole_code():
    # 4521 from 0000: the outer ring moves on to the next digit and sends nothing, the inner ring steps the
    # selected digit once per detent
    s = Sim()
    s.key("SHIFT")
    for n in (4, 5, 2, 1):
        s.turn("FREQ_INNER", n); s.turn("FREQ_OUTER", 1)
    assert [n for _, n in s.take()] == ["SQK_D1_UP"] * 4 + ["SQK_D2_UP"] * 5 + ["SQK_D3_UP"] * 2 + ["SQK_D4_UP"]
    s.turn("FREQ_OUTER", -2); s.turn("FREQ_INNER", -1)   # back to digit 2, and down
    assert s.take() == [(1, "SQK_D2_DN")] and s.p.shift_active(s.t)


def test_squawk_digit_stops_at_both_ends():
    s = Sim()
    s.key("SHIFT")
    s.turn("FREQ_OUTER", -3); s.turn("FREQ_INNER", 1)    # already on digit 1: no wrap to digit 4
    s.turn("FREQ_OUTER", 6); s.turn("FREQ_INNER", 1)     # past digit 4: stays there
    s.p.turn("FREQ_OUTER", -9, s.t); s.turn("FREQ_INNER", 1)   # several detents in one read stop at the end too
    s.p.turn("FREQ_OUTER", 2, s.t); s.turn("FREQ_INNER", 1)
    assert [n for _, n in s.take()] == ["SQK_D1_UP", "SQK_D4_UP", "SQK_D1_UP", "SQK_D3_UP"]


def test_squawk_starts_at_digit_1_in_a_new_session():
    # a session that ran out, one ended by a key, and SHIFT armed again while the knob still keeps it
    s = Sim()
    squawk(s); s.turn("FREQ_OUTER", 2); s.turn("FREQ_INNER", 1)
    s.run(P.SESSION_MS); assert not s.p.shift_active(s.t)
    squawk(s); s.turn("FREQ_OUTER", 1); s.turn("FREQ_INNER", 1)
    s.key("AP")
    squawk(s); s.turn("FREQ_OUTER", 3); s.turn("FREQ_INNER", 1)
    s.key("SHIFT"); assert s.p.shift_active(s.t)
    s.turn("FREQ_INNER", 1)
    assert [n for _, n in s.take()] == ["SQK_D1_UP", "SQK_D3_UP", "SQK_D1_UP", "SQK_D2_UP", "AP",
                                        "SQK_D1_UP", "SQK_D4_UP", "SQK_D1_UP"]


def test_squawk_digit_stays_when_shift_is_tapped_under_a_held_push():
    # digit 3 selected, the FREQ push held, SHIFT tapped: the held push keeps the session under the armed
    # SHIFT, so the next inner detent is still in it, on digit 3
    s = Sim()
    s.p.key("SHIFT", True, s.t); s.run(60); s.p.key("SHIFT", False, s.t); s.run(140)
    s.turn("FREQ_OUTER", 2, every=10); s.run(280)
    s.p.key("FREQ_PUSH", True, s.t); s.run(200)
    s.p.key("SHIFT", True, s.t); s.run(60); s.p.key("SHIFT", False, s.t); s.run(240)
    s.turn("FREQ_INNER", 1, every=500)
    s.p.key("FREQ_PUSH", False, s.t); s.run(200)
    assert [n for _, n in s.take()] == ["XPDR_MODE", "SQK_D3_UP"]


def test_squawk_push_keeps_the_selected_digit():
    s = Sim()
    s.key("SHIFT"); s.turn("FREQ_OUTER", 1); s.key("FREQ_PUSH"); s.turn("FREQ_INNER", 1)
    s.p.key("FREQ_PUSH", True, s.t); s.run(100); s.turn("FREQ_OUTER", 1); s.turn("FREQ_INNER", 1)   # push held
    s.p.key("FREQ_PUSH", False, s.t); s.turn("FREQ_INNER", -1)
    assert [n for _, n in s.take()] == ["XPDR_MODE", "SQK_D2_UP", "XPDR_MODE", "SQK_D3_UP", "SQK_D3_DN"]
    s.run(P.SESSION_MS); s.turn("FREQ_INNER", 1)
    assert s.take() == [(1, "COM_KHZ_UP")]               # the shifted pushes left the mode alone


def test_squawk_fast_spin_only_steps_the_selected_digit():
    # however fast the inner ring turns, also with several detents in one read: one step per detent, and at
    # most MAX_QUEUE of them
    s = Sim()
    s.key("SHIFT"); s.turn("FREQ_OUTER", 1)
    s.turn("FREQ_INNER", 4, every=10); s.p.turn("FREQ_INNER", 3, s.t); s.run(1500)
    assert [n for _, n in s.take()] == ["SQK_D2_UP"] * 7
    s.turn("FREQ_INNER", -12, every=10); s.run(1500)
    assert [n for _, n in s.take()] == ["SQK_D2_DN"] * P.MAX_QUEUE


def test_squawk_steps_queued_for_a_digit_are_kept_when_the_next_one_is_selected():
    # the inner ring spun, the next digit selected while steps are still queued: they finish on their digit,
    # also when the inner ring then turns the other way (a reversal on one digit still stops at once), and
    # the new digit's steps follow them, as far as the MAX_QUEUE waiting leave room
    s = Sim()
    s.key("SHIFT")
    s.turn("FREQ_INNER", 5, every=10); s.turn("FREQ_OUTER", 1, every=10)
    s.turn("FREQ_INNER", -1, every=10); s.run(1500)
    assert [n for _, n in s.take()] == ["SQK_D1_UP"] * 5 + ["SQK_D2_DN"]
    s.turn("FREQ_INNER", 5, every=10); s.turn("FREQ_INNER", -1, every=10); s.run(1500)
    assert [n for _, n in s.take()] == ["SQK_D2_UP", "SQK_D2_DN"]
    s.turn("FREQ_INNER", 12, every=10); s.turn("FREQ_OUTER", 1, every=10)
    s.turn("FREQ_INNER", 12, every=10); s.run(1500)
    names = [n for _, n in s.take()]
    d3 = names.count("SQK_D3_UP")
    assert names == ["SQK_D2_UP"] * P.MAX_QUEUE + ["SQK_D3_UP"] * d3 and 0 < d3 < P.MAX_QUEUE


def test_adf_inner_ring_accelerates():
    # in ADF mode the inner ring steps 1 kHz, or 10 kHz on a fast turn
    s = Sim()
    s.key("FREQ_PUSH"); s.key("FREQ_PUSH"); s.take()
    s.turn("FREQ_OUTER", 3, every=P.FAST_MS // 2); s.run(500)            # the outer ring: one step per detent
    assert [n for _, n in s.take()] == ["ADF_100_UP"] * 3
    s.turn("FREQ_INNER", 2, every=P.FAST_MS // 2); s.run(500)
    assert [n for _, n in s.take()] == ["ADF_1_UP", "ADF_10_UP"]


def test_com_nav_rings_do_not_accelerate():
    # COM and NAV: both rings send one step per detent, however fast the turn (only ADF's inner ring accelerates)
    for pushes, names in ((0, ("COM_MHZ_UP", "COM_KHZ_UP")), (1, ("NAV_MHZ_UP", "NAV_KHZ_UP"))):
        for ring, name in zip(("FREQ_OUTER", "FREQ_INNER"), names):
            s = Sim()
            for _ in range(pushes):
                s.key("FREQ_PUSH")
            s.take()
            s.turn(ring, 3, every=P.FAST_MS // 2); s.run(500)
            assert [n for _, n in s.take()] == [name] * 3, (ring, name)


def test_range():
    s = Sim()
    s.p.key("RANGE_COM", True, s.t); s.run(100); s.p.key("RANGE_COM", False, s.t); s.run(100)
    assert s.take() == [(1, "PTR")]                                      # centre push
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(700)
    s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(200)
    names = [n for _, n in s.take()]
    assert names and set(names) == {"PAN_UP"} and len(names) >= 3, names   # tilt repeats, no PTR
    for lead in (10, 150):                               # slow tilt: com closes well before the direction
        s.p.key("RANGE_COM", True, s.t); s.run(lead); s.p.key("RANGE_D", True, s.t); s.run(100)
        s.p.key("RANGE_D", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(100)
        assert [n for _, n in s.take()] == ["PAN_RIGHT"], lead
    s.p.key("RANGE_COM", True, s.t); s.run(800); s.p.key("RANGE_COM", False, s.t); s.run(100)
    assert s.take() == [(1, "PTR")]                                      # long centre push: one PTR on release
    for key, way in (("RANGE_B", "LEFT"), ("RANGE_C", "DN")):
        s.p.key("RANGE_COM", True, s.t); s.p.key(key, True, s.t); s.run(100)
        s.p.key(key, False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(100)
        s.key("SHIFT")
        s.p.key("RANGE_COM", True, s.t); s.p.key(key, True, s.t); s.run(100)
        s.p.key(key, False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(P.SESSION_MS + 100)
        assert [n for _, n in s.take()] == ["PAN_" + way, "S_PAN_" + way], key
    s.turn("RANGE", -2); assert [n for _, n in s.take()] == ["RANGE_CCW", "RANGE_CCW"]
    s.key("SHIFT"); s.turn("RANGE", 1); assert s.take() == [(1, "S_RANGE_CW")]
    s.key("SHIFT"); s.turn("RANGE", -1); assert s.take() == [(1, "S_RANGE_CCW")]


def test_centre_press_without_a_direction_sends_ptr_on_release():
    # nothing while the centre is held (a direction may still close); PTR once the release is no bounce
    s = Sim()
    s.p.key("RANGE_COM", True, s.t); s.run(500); assert s.take() == []
    s.p.key("RANGE_COM", False, s.t); s.run(P.BOUNCE_MS - 1); assert s.take() == []
    s.run(1); assert s.take() == [(1, "PTR")]
    s.run(500); assert s.take() == []


def test_unit_toggled_while_a_unit_key_is_held():
    # CDI goes down in unit 1, UNIT changes under it: it stays on device 1 until its release, and the next
    # press is on device 2
    s = Sim()
    s.p.key("CDI", True, s.t); s.run(100)
    tap(s, "SHIFT"); tap(s, "HOME"); assert s.p.unit_light
    s.run(500)
    assert s.down(1) == {"CDI"} and s.down(2) == set()
    s.p.key("CDI", False, s.t); s.run(100)
    assert s.down(1) == set() and s.take() == [(1, "CDI")]
    s.key("CDI"); assert s.take() == [(2, "CDI")]


def test_unit_toggled_while_detents_are_queued():
    # six quick FMS detents in unit 1, UNIT changed while most are still queued: all six go to device 1,
    # the next ones to device 2
    s = Sim()
    s.turn("FMS_INNER", 6, every=10)
    tap(s, "SHIFT"); tap(s, "HOME"); assert s.p.unit_light
    assert s.take() == [(1, "FMS_INNER_CW")] * 2         # more to go
    s.turn("FMS_INNER", 2, every=10); s.run(1000)
    assert sorted(s.take()) == [(1, "FMS_INNER_CW")] * 4 + [(2, "FMS_INNER_CW")] * 2


STEP_MS = P.PRESS_MS + P.GAP_MS


def spaced(log):
    """Whether each press in log starts PRESS_MS or more after the one before it, and STEP_MS or more after the
    last press of its own button"""
    prev, last = None, {}
    for t, d, n in log:
        if (prev is not None and t - prev < P.PRESS_MS) or ((d, n) in last and t - last[(d, n)] < STEP_MS):
            return False
        prev = last[(d, n)] = t
    return True


def test_everything_goes_out_in_the_order_it_came():
    # three quick FMS inner detents, ENT, an outer detent and the push, all faster than they go out
    s = Sim()
    s.turn("FMS_INNER", 3, every=10); tap(s, "ENT"); s.turn("FMS_OUTER", 1, every=10); tap(s, "FMS_PUSH")
    s.run(1000)
    assert [n for _, _, n in s.log] == ["FMS_INNER_CW"] * 3 + ["ENT", "FMS_OUTER_CW", "FMS_CRSR"]
    assert spaced(s.log)


def test_a_key_with_nothing_ahead_goes_out_at_once():
    s = Sim()
    s.p.key("AP", True, s.t); s.run(1)
    assert s.take() == [(1, "AP")]


def test_a_key_waits_for_a_step_still_shown():
    # a detent 19 ms before the key: the key goes down once the step was shown for PRESS_MS
    s = Sim()
    s.p.turn("FMS_INNER", 1, s.t); s.run(20)
    s.p.key("AP", True, s.t); s.run(100)
    assert [n for _, _, n in s.log] == ["FMS_INNER_CW", "AP"] and spaced(s.log)


def test_a_step_waits_for_a_key_before_it():
    # COM ⇆ and a kHz detent 25 ms later; ENT twice, the second waiting for its own gap, and a detent 30 ms
    # after it: the detent goes out last both times
    s = Sim()
    s.p.key("COM_SWAP", True, s.t); s.run(25); s.p.turn("FREQ_INNER", 1, s.t); s.run(300)
    assert [n for _, _, n in s.log] == ["COM_SWAP", "COM_KHZ_UP"] and spaced(s.log)
    s = Sim()
    tap(s, "ENT"); s.p.key("ENT", True, s.t); s.run(30); s.p.turn("FMS_INNER", 1, s.t); s.run(300)
    assert [n for _, _, n in s.log] == ["ENT", "ENT", "FMS_INNER_CW"] and spaced(s.log)


def test_a_held_key_or_tilt_repeats_in_turn_with_the_steps():
    # UP or a tilt pressed and held while FMS steps are queued: its first step follows them, and a detent
    # turned during the hold goes out between two of its steps, in the order they came, and nothing follows
    # its release
    for keys, button in ((("UP",), "UP"), (("RANGE_COM", "RANGE_A"), "PAN_UP")):
        s = Sim()
        s.turn("FMS_INNER", 4, every=10)
        for k in keys:
            s.p.key(k, True, s.t)
        s.run(800); s.turn("FMS_OUTER", 1, every=10); s.run(800)
        let_go = s.t
        for k in keys:
            s.p.key(k, False, s.t)
        s.run(1000)
        names = [n for _, _, n in s.log]
        assert names[:5] == ["FMS_INNER_CW"] * 4 + [button] and names.count("FMS_OUTER_CW") == 1, keys
        outer = names.index("FMS_OUTER_CW")
        assert 5 < outer < len(names) - 1 and set(names[5:outer] + names[outer + 1:]) == {button}, keys
        starts = [t for t, _, n in s.log if n == button]
        assert spaced(s.log), keys
        assert starts[-1] < let_go + P.BOUNCE_MS, keys


def test_a_key_held_behind_steps_keeps_its_unit_and_is_shown_from_its_turn():
    # CDI pressed in unit 1 behind queued steps and held while UNIT changes: it goes out after the steps, on
    # device 1, and stays down from its turn until it is let go
    s = Sim()
    s.turn("FMS_INNER", 4, every=10)
    s.p.key("CDI", True, s.t); s.run(100)
    tap(s, "SHIFT"); tap(s, "HOME"); assert s.p.unit_light
    s.run(500); assert s.down(1) == {"CDI"}
    s.p.key("CDI", False, s.t); s.run(P.BOUNCE_MS - 1); assert s.down(1) == {"CDI"}
    s.run(1); assert s.down(1) == set()
    s.key("CDI")
    assert s.take() == [(1, "FMS_INNER_CW")] * 4 + [(1, "CDI"), (2, "CDI")]


def test_shift_tapped_behind_steps_arms_the_next_key_at_once():
    # the light comes on at the tap, the key goes out shifted after the steps, and the light is off at its press
    s = Sim()
    s.turn("FMS_INNER", 4, every=10); tap(s, "SHIFT")
    assert s.p.shift_level(s.t) == P.LIGHT_FULL
    tap(s, "VFR"); assert s.p.shift_level(s.t) == P.LIGHT_OFF
    s.run(1000)
    assert s.take() == [(1, "FMS_INNER_CW")] * 4 + [(1, "IDENT")]


def test_a_key_ends_a_session_at_its_press_while_its_steps_still_go_out():
    # AP pressed while squawk steps are still queued: the session and the light end at the press, the queued
    # steps still go out as squawk steps, and AP, plain, follows them
    s = Sim()
    s.key("SHIFT"); s.turn("FREQ_INNER", 6, every=10)
    tap(s, "AP"); assert s.p.shift_level(s.t) == P.LIGHT_OFF and not s.p.shift_active(s.t)
    s.turn("FREQ_INNER", 1, every=10); s.run(1000)
    assert [n for _, n in s.take()] == ["SQK_D1_UP"] * 6 + ["AP", "COM_KHZ_UP"]


def test_at_most_max_queue_steps_wait():
    # 12 detents in one read keep MAX_QUEUE; once the first is on its way, a detent of the other ring fits in
    s = Sim()
    s.p.turn("FMS_INNER", 12, s.t); s.run(5); s.turn("FMS_OUTER", 1, every=5); s.run(2000)
    assert [n for _, n in s.take()] == ["FMS_INNER_CW"] * P.MAX_QUEUE + ["FMS_OUTER_CW"]
    s.run(2000); assert s.take() == []                   # the four dropped detents never come


def test_a_button_gets_at_most_max_queue_presses_with_the_one_still_shown():
    # 12 detents in one read: MAX_QUEUE presses of the ring's button with nothing shown, one less while its last
    # press is still down or in its gap, so the last one ends its gap within MAX_QUEUE steps
    for before in (None, 1, P.PRESS_MS + 1):
        s = Sim()
        if before is not None:
            s.p.turn("FMS_INNER", 1, s.t); s.run(before); s.take()
            assert s.down(1) == ({"FMS_INNER_CW"} if before == 1 else set())
        s.p.turn("FMS_INNER", 12, s.t); s.run(3000)
        assert len(s.take()) == (P.MAX_QUEUE if before is None else P.MAX_QUEUE - 1)


def test_a_key_behind_a_full_queue_is_kept_and_waits_less_than_a_second():
    # three rings flicked, then AP; and CLR tapped 12 times behind them: MAX_QUEUE of those, in their turn
    s = Sim()
    for ring in ("FMS_INNER", "FMS_OUTER", "FREQ_INNER"):
        s.turn(ring, 15, every=20)
    pressed = s.t
    tap(s, "AP")
    for _ in range(12):
        s.p.key("CLR", True, s.t); s.run(P.BOUNCE_MS + 1); s.p.key("CLR", False, s.t); s.run(P.BOUNCE_MS + 1)
    s.run(2000)
    names = [n for _, _, n in s.log]
    assert names[-1 - P.MAX_QUEUE:] == ["AP"] + ["CLR"] * P.MAX_QUEUE and spaced(s.log)
    assert [t for t, _, n in s.log if n == "AP"][0] - pressed < P.MAX_QUEUE * STEP_MS


def test_reversing_keeps_the_steps_a_key_or_another_ring_followed():
    # FMS inner spun, ENT (or the outer ring), then the inner ring back: the steps before ENT are the
    # character it confirms, so they stay and the step back follows ENT. Turned back right away, the knob
    # still stops at once
    for between in ("ENT", "FMS_OUTER"):
        s = Sim()
        s.turn("FMS_INNER", 6, every=10)
        if between == "ENT":
            tap(s, "ENT")
        else:
            s.turn("FMS_OUTER", 1, every=10)
        s.turn("FMS_INNER", -1, every=10); s.run(1500)
        sent = "ENT" if between == "ENT" else "FMS_OUTER_CW"
        assert [n for _, n in s.take()] == ["FMS_INNER_CW"] * 6 + [sent, "FMS_INNER_CCW"], between
    s = Sim()
    s.turn("FMS_INNER", 6, every=10); tap(s, "ENT"); s.turn("FMS_INNER", 3, every=10)
    s.turn("FMS_INNER", -1, every=10); s.run(1500)
    assert [n for _, n in s.take()] == ["FMS_INNER_CW"] * 6 + ["ENT", "FMS_INNER_CCW"]


def test_reversing_in_another_function_keeps_the_steps_of_the_one_before():
    # a step back only stops the function the ring still has. ALT spun, SHIFT, and the ring one detent back, now
    # BARO; COM kHz spun, UNIT, and one back for COM 2: SHIFT and UNIT send no button, but the steps queued
    # before them all go out
    s = Sim()
    s.turn("ALTHDG_OUTER", 8, every=10); tap(s, "SHIFT"); s.turn("ALTHDG_OUTER", -1, every=10); s.run(1500)
    assert [n for _, n in s.take()] == ["ALT_100_UP"] + ["ALT_1000_UP"] * 7 + ["BARO_DN"]
    s = Sim()
    s.turn("FREQ_INNER", 6, every=10); tap(s, "SHIFT"); tap(s, "HOME")
    s.turn("FREQ_INNER", -1, every=10); s.run(1500)
    assert s.take() == [(1, "COM_KHZ_UP")] * 6 + [(2, "COM_KHZ_DN")]


def test_steps_kept_stay_when_the_ring_turns_back():
    # code.py keeps the steps queued before it waited for a host: a turn back after that queues behind them
    s = Sim()
    s.p.turn("ALTHDG_OUTER", 1, s.t); s.p.keep_steps(); s.p.turn("ALTHDG_OUTER", -1, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_100_UP", "ALT_100_DN"]
    # also when the ring goes on the same way first, to the same button: the turn back drops only the steps
    # queued since, not the kept ones (keep_steps after a wait, a SHIFT tap and its cancel)
    for between in ("wait", "two taps"):
        s = Sim()
        s.p.turn("FMS_OUTER", 5, s.t); s.run(5)
        if between == "wait":
            s.p.keep_steps()
        else:
            tap(s, "SHIFT"); tap(s, "SHIFT")
        s.p.turn("FMS_OUTER", 1, s.t); s.run(5); s.p.turn("FMS_OUTER", -1, s.t); s.run(2000)
        assert [n for _, n in s.take()] == ["FMS_OUTER_CW"] * 5 + ["FMS_OUTER_CCW"], between
    # ALT spun, UNIT toggled (which ALT ignores), on the same way, then back: the 1000 ft steps all go out
    s = Sim()
    s.turn("ALTHDG_OUTER", 8, every=10); tap(s, "SHIFT"); tap(s, "HOME")
    s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(5); s.p.turn("ALTHDG_OUTER", -1, s.t); s.run(2000)
    sent = [n for _, n in s.take()]
    assert sent[-1] == "ALT_100_DN" and sent.count("ALT_1000_UP") == 7, sent
    # a squawk digit's steps stay when the selection comes back to it and its ring goes on and back
    s = Sim()
    tap(s, "SHIFT"); s.p.turn("FREQ_INNER", 5, s.t); s.run(5)
    s.p.turn("FREQ_OUTER", 1, s.t); s.run(5); s.p.turn("FREQ_OUTER", -1, s.t); s.run(5)
    s.p.turn("FREQ_INNER", 1, s.t); s.run(5); s.p.turn("FREQ_INNER", -1, s.t); s.run(2000)
    assert [n for _, n in s.take()] == ["SQK_D1_UP"] * 5 + ["SQK_D1_DN"]


def test_fill_report_sets_a_bit_per_pressed_button_and_clears_the_rest():
    s = Sim()
    s.p.key("ENT", True, s.t); s.p.key("AP", True, s.t); s.run(P.PRESS_MS + 5)
    tap(s, "SHIFT"); tap(s, "HOME"); s.p.key("ENT", False, s.t); s.run(200); s.p.key("ENT", True, s.t); s.run(5)
    for dev, want in ((1, {BM.BUTTON[1]["AP"]}), (2, {BM.BUTTON[2]["ENT"]})):
        report = bytearray(b"\xff" * (BM.SIZE[dev] // 8))
        s.p.fill_report(dev, report)
        assert {b for b in range(BM.SIZE[dev]) if report[b >> 3] >> (b & 7) & 1} == want == s.p.buttons(dev)


def test_reversing_forgets_steps_that_never_went_out():
    # ALT spun behind FMS steps and turned back before any of its steps went out: only the step back is sent
    s = Sim()
    s.turn("FMS_INNER", 4, every=10); s.turn("ALTHDG_OUTER", 3, every=10); s.turn("ALTHDG_OUTER", -1, every=10)
    s.run(1000)
    assert [n for _, n in s.take()] == ["FMS_INNER_CW"] * 4 + ["ALT_100_DN"]
    s.run(1000); assert s.take() == []


def test_a_medium_speed_turn_mixes_in_coarse_steps():
    # HDG detents 61 to 112 ms apart: the first ones fine; while a fine step still waits, a detent takes the
    # coarse step, so each detent is one step and the last one goes out with the hand. Slower than the fine
    # steps go out, every detent stays fine
    for every in (61, 70, 100):
        s = Sim()
        s.turn("ALTHDG_INNER", 30, every=every); last = s.t - every; s.run(1000)
        names = [n for _, n in s.take()]
        assert len(names) == 30 and names[:2] == ["HDG_1_UP"] * 2 and "HDG_10_UP" in names, every
        assert set(names) == {"HDG_1_UP", "HDG_10_UP"} and s.log[-1][0] - last < STEP_MS, every
    s = Sim()
    s.turn("ALTHDG_INNER", 30, every=STEP_MS + 1); s.run(1000)
    assert [n for _, n in s.take()] == ["HDG_1_UP"] * 30


def test_a_slow_turn_behind_another_rings_steps_stays_fine():
    # ALT and HDG turned slowly right after a quick FMS scroll: their fine steps wait behind the FMS steps,
    # but the hand turns slower than steps go out, so every detent stays fine and none is lost
    for ring, detents, fine in (("ALTHDG_OUTER", 8, "ALT_100_UP"), ("ALTHDG_INNER", 4, "HDG_1_UP")):
        s = Sim()
        s.turn("FMS_INNER", 15, every=20); s.turn(ring, detents, every=150); s.run(2000)
        assert [n for _, n in s.take() if n != "FMS_INNER_CW"] == [fine] * detents, ring


def held_presses(keys, button, pass_ms, ms=15000):
    """keys held for ms and then let go, with one tick() every pass_ms: the ms each press of button started at,
    and the ms of the release"""
    p, t, starts, was, let_go = P.Panel(), 0, [], False, None
    for k in keys:
        p.key(k, True, t)
    while t < ms + 3000:
        t += pass_ms
        if let_go is None and t >= ms:
            let_go = t
            for k in reversed(keys):
                p.key(k, False, t)
        p.tick(t)
        now = button in down(p, 1)
        if now and not was:
            starts.append(t)
        was = now
    return starts, let_go


def test_a_hold_stops_with_its_release_at_any_pass_time():
    # a loop pass of 5, 8 or 12 ms stretches every press and gap to whole passes, so a step can take longer
    # than a repeat: the hold steps as fast as the steps go through, and no press starts after the release
    for pass_ms in (1, 5, 8, 12):
        for keys, button, every in ((("RANGE_COM", "RANGE_A"), "PAN_UP", P.PAN_MS), (("UP",), "UP", P.REPEAT_MS)):
            starts, let_go = held_presses(keys, button, pass_ms)
            # a step: press and gap, each rounded up to whole passes, and one pass until the next press
            step = (-(-P.PRESS_MS // pass_ms) - (-P.GAP_MS // pass_ms) + 1) * pass_ms
            period = max(every, step) + pass_ms            # a repeat due between two passes waits for the next
            assert starts[-1] < let_go, (pass_ms, button, [t - let_go for t in starts if t >= let_go])
            assert all(b - a < period for a, b in zip(starts[1:], starts[2:] + [let_go])), (pass_ms, button)


def test_fast_tilt_closes_direction_and_com_in_one_scan():
    # a quick tilt closes its direction and "com" within one keypad scan: the keypad reports them in the same
    # pass, the direction before "com" (code.py's scan order, tests/test_pins.py), and releases them the same way
    s = Sim()
    s.p.key("RANGE_A", True, s.t); s.p.key("RANGE_COM", True, s.t); s.run(100)
    s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(200)
    assert s.take() == [(1, "PAN_UP")]                                  # no PTR


def test_tilt_first_repeat_after_300_ms():
    s = Sim()
    t0 = s.t
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t)
    trace = pressed_trace(s, 600)
    starts = [t for t in sorted(trace) if "PAN_UP" in trace[t] and "PAN_UP" not in trace.get(t - 1, ())]
    assert starts[:3] == [t0 + 1, t0 + P.PAN_DELAY_MS, t0 + P.PAN_DELAY_MS + P.PAN_MS]


def test_up_dn_repeat():
    s = Sim()
    s.p.key("DN", True, s.t); s.run(1000); s.p.key("DN", False, s.t); s.run(300)
    n = len(s.take())
    assert 4 <= n <= 7, n                    # 1 at once, then from 400 ms about 8 per second


def test_shifted_up_dn_are_held_not_repeated():
    # S_UP and S_DN stay down as long as the key, as other keys do, so a profile can tell a tap from a hold; the
    # keyboard mode repeats them as before
    for key, button in (("UP", "S_UP"), ("DN", "S_DN")):
        s = Sim()
        s.key("SHIFT"); s.take()
        s.p.key(key, True, s.t); s.run(P.ARM_MS + 1000)              # past SHIFT's time out: still down, once
        assert s.take() == [(1, button)] and button in s.down(1)
        s.p.key(key, False, s.t); s.run(100)
        assert button not in s.down(1) and not s.take()
        s.p.key(key, True, s.t); s.run(1000); s.p.key(key, False, s.t); s.run(100)
        assert len([n for _, n in s.take()]) > 3                # without SHIFT again: it repeats
    s = Sim(solo=True)                                          # as a keyboard it repeats with SHIFT too
    s.key("SHIFT"); s.take()
    s.p.key("UP", True, s.t); s.run(1000); s.p.key("UP", False, s.t); s.run(100)
    assert len(s.take()) > 3


def test_repeats_due_together_queue_in_a_fixed_order():
    # UP and DN held together repeat in the same ms: they queue in the same order whichever went down first.
    # CircuitPython's dicts keep no insertion order, so on the board an order by insertion would differ
    logs = []
    for first, second in (("UP", "DN"), ("DN", "UP")):
        s = Sim()
        s.p.key(first, True, s.t); s.p.key(second, True, s.t); s.run(1000)
        logs.append([(t, n) for t, _, n in s.log if t >= P.REPEAT_DELAY_MS])
    assert logs[0] == logs[1] and len(logs[0]) >= 4 and [n for _, n in logs[0][:2]] == ["DN", "UP"]   # by name


def pressed_trace(s, ms, dev=1):
    """{ms: set of button names pressed on dev} for the next ms milliseconds"""
    out = {}
    for _ in range(ms):
        s.run(1)
        out[s.t] = s.down(dev)
    return out


# MobiFlight polls the joysticks from a 20 ms System.Timers.Timer; Windows' 15.6 ms clock makes that about
# every 31 ms. It sees snapshots, so a detent only counts if a poll lands in its press and another in its gap.
POLL_MS = 31.25
# The host fetches the reports every 8 ms (bInterval 8), one IN endpoint for both joysticks: with a report still
# pending and both devices changing in one pass, an edge waits up to three frames.
HID_FRAME_MS = 8


def mobiflight_counts(on):
    """on: {ms: button pressed?}. The presses MobiFlight counts, for every phase of its poll, with every press
    edge or every release edge three HID frames late (shortening the press or the gap)"""
    late, counts = 3 * HID_FRAME_MS, set()
    for edges in ("press", "release"):
        # a pulse [a, b) arrives as [a + late, b) or as [a, b + late) (press and gap are longer than late)
        if edges == "press":
            pc = {t: on[t] and on.get(t - late, False) for t in on}
        else:
            pc = {t: on[t] or on.get(t - late, False) for t in on}
        for phase in range(32):
            polls = [t for t in sorted(pc) if (t - phase) % POLL_MS < 1]
            seen = [pc[t] for t in polls]
            counts.add(sum(b and not a for a, b in zip([False] + seen, seen)))
    return counts


def test_detent_pulses_survive_mobiflight_polling():
    # a quick spin of the FMS knob (one step per detent): whatever the phase of the poll, MobiFlight counts
    # every queued detent, and the run-on after the spin stays below 0.9 s. That holds even when every press
    # edge, or every release edge, reaches the PC three HID frames late, shortening the press or the gap
    s, trace = Sim(), {}
    for _ in range(12):                                    # 12 detents in 60 ms: MAX_QUEUE of them are kept
        s.p.turn("FMS_INNER", 1, s.t)
        trace.update(pressed_trace(s, 5))
    trace.update(pressed_trace(s, 1500))
    on = {t: "FMS_INNER_CW" in trace[t] for t in trace}
    assert max(t for t in on if on[t]) < 900
    assert mobiflight_counts(on) == {P.MAX_QUEUE}


def key_trace(s, presses, name, button=None, dev=1, after=500):
    """presses: (down ms, up ms) from now, of key or push `name`. {ms: `button` (default: name) pressed?}"""
    t0, out = s.t, {}
    events = sorted([(t0 + a, True) for a, _ in presses] + [(t0 + b, False) for _, b in presses])
    for t, pressed in events:
        while s.t < t:
            s.run(1)
            out[s.t] = (button or name) in s.down(dev)
        s.p.key(name, pressed, s.t)
    for _ in range(after):
        s.run(1)
        out[s.t] = (button or name) in s.down(dev)
    return out


# A release waits BOUNCE_MS for a bounce: the Sim's key() comes after the tick of its ms, so a release that used
# to show in the next tick now shows BOUNCE_MS - 1 ticks later than that
LATE = P.BOUNCE_MS - 1


def runs(on):
    """(first ms, length) of each run of pressed ms"""
    out, start = [], None
    for t in sorted(on):
        if on[t] and start is None:
            start = t
        elif not on[t] and start is not None:
            out.append((start, t - start)); start = None
    return out


def test_quick_tap_is_held_long_enough_for_mobiflight():
    # a 10 ms tap: the keypad reports it, the PC sees it for PRESS_MS, so every poll phase counts it
    s = Sim()
    on = key_trace(s, [(0, 10)], "AP")
    assert [n for _, n in runs(on)] == [P.PRESS_MS] and mobiflight_counts(on) == {1}


def test_long_press_is_released_after_the_bounce_window():
    s = Sim()
    on = key_trace(s, [(0, 300)], "AP")
    assert [n for _, n in runs(on)] == [300 + LATE]


def test_fast_double_tap_stays_two_presses():
    # CLR twice, or a flip-flop: 15 ms taps 35 ms apart, faster than a finger, but past BOUNCE_MS. The second
    # press waits until the first was shown for PRESS_MS and released for GAP_MS, and MobiFlight counts both in
    # every phase
    assert P.BOUNCE_MS < 35
    s = Sim()
    on = key_trace(s, [(0, 15), (50, 65)], "CLR")
    (a, n1), (b, n2) = runs(on)
    assert n1 == n2 == P.PRESS_MS and b - (a + n1) == P.GAP_MS
    assert mobiflight_counts(on) == {2}


def test_fast_triple_tap_stays_three_presses():
    s = Sim()
    on = key_trace(s, [(0, 10), (45, 55), (90, 100)], "CLR")
    assert [n for _, n in runs(on)] == [P.PRESS_MS] * 3 and mobiflight_counts(on) == {3}


def test_quick_tap_then_a_held_press_stays_two_presses():
    # the second press comes while the first is still shown and is then held: the first ends after PRESS_MS,
    # the second follows the gap and stays down until its release
    s = Sim()
    t0 = s.t
    on = key_trace(s, [(0, 15), (50, 400)], "AP")
    assert runs(on) == [(t0 + 1, P.PRESS_MS), (t0 + 1 + P.PRESS_MS + P.GAP_MS, 400 - P.PRESS_MS - P.GAP_MS + LATE)]


def test_presses_still_to_show_are_capped():
    # 20 presses, each just past BOUNCE_MS after the last (faster than a finger, and than the PC is shown them):
    # once MAX_QUEUE are owed, counting the one on its way, the rest are dropped, so the run-on stays bounded
    s = Sim()
    every = P.BOUNCE_MS + 1
    t0 = s.t
    on = key_trace(s, [(every * i, every * i + 1) for i in range(20)], "AP", after=2000)
    started = [a for a, _ in runs(on) if a <= t0 + every * 19]       # shown by the last press
    assert len(runs(on)) == len(started) + P.MAX_QUEUE - 1 < 20


def test_second_press_held_waits_for_the_gap_then_stays_held():
    # released after a long press and pressed again BOUNCE_MS later, then held: the release goes out with the
    # new press, which is down again after GAP_MS, and held until its release
    s = Sim()
    t0 = s.t
    on = key_trace(s, [(0, 200), (200 + P.BOUNCE_MS, 600)], "AP")
    second = t0 + 200 + P.BOUNCE_MS + P.GAP_MS
    assert runs(on) == [(t0 + 1, 200 + LATE), (second, 600 - 200 - P.GAP_MS)]   # first tick at t0 + 1


def test_fast_double_push_stays_two_presses():
    # pushes follow the same rule: two quick pushes of the FREQ knob step the mode twice, to ADF, and send
    # FREQ_PUSH twice
    s = Sim()
    on = key_trace(s, [(0, 15), (50, 65)], "FREQ_PUSH")
    assert len(runs(on)) == 2 and mobiflight_counts(on) == {2}
    s.take(); s.turn("FREQ_OUTER", 1); assert s.take() == [(1, "ADF_100_UP")]
    on = key_trace(s, [(0, 15), (50, 65)], "ALTHDG_PUSH", "HDG_SYNC")
    assert len(runs(on)) == 2 and mobiflight_counts(on) == {2}


def test_a_quick_tap_of_another_key_waits_for_the_press_only():
    # the gap is per button: AP right after VS goes down once VS was shown for PRESS_MS, in VS's gap
    s = Sim()
    s.p.key("VS", True, s.t); s.run(10); s.p.key("VS", False, s.t)
    s.p.key("AP", True, s.t); s.run(P.PRESS_MS)
    assert [n for _, n in s.take()] == ["VS", "AP"] and s.log[1][0] - s.log[0][0] == P.PRESS_MS


def test_a_key_goes_down_at_once_again_after_its_gap():
    # a fast double tap, and a third press well after its gap: nothing is owed any more, so it shows at once
    s = Sim()
    key_trace(s, [(0, 10), (50, 60)], "AP")
    s.take(); s.p.key("AP", True, s.t); s.run(1)
    assert s.take() == [(1, "AP")]


def test_two_keys_tapped_together_go_out_one_after_the_other():
    # VS and AP down and up in the same passes: VS first, AP once VS was shown for PRESS_MS (in VS's gap), each
    # pressed for PRESS_MS. Once both gaps are over both are forgotten, so a new press goes down at once
    s = Sim()
    s.p.key("VS", True, s.t); s.p.key("AP", True, s.t)
    trace = pressed_trace(s, 10)
    s.p.key("VS", False, s.t); s.p.key("AP", False, s.t)
    trace.update(pressed_trace(s, 2 * P.PRESS_MS + P.GAP_MS - 10))
    assert [n for t in sorted(trace) for n in trace[t]] == ["VS"] * P.PRESS_MS + ["AP"] * P.PRESS_MS
    s.run(1)
    s.take()
    s.p.key("VS", True, s.t); s.run(1)
    assert s.take() == [(1, "VS")]


# A switch that bounces for longer than a keypad scan: code.py passes on every change it scans
def test_bounce_right_after_the_press_is_one_press():
    # pressed, open again 3 ms later, closed 3 ms after that (as after a stalled pass, which reads several scans
    # at once): one press, as long as a tap, and its later release changes nothing
    s = Sim()
    t0 = s.t
    on = key_trace(s, [(0, 3), (6, 100)], "AP")
    assert runs(on) == [(t0 + 1, 100 + LATE)] and mobiflight_counts(on) == {1}


def test_chatter_one_scan_apart_is_one_press():
    # opens and closes every 22 ms (one scan, picked up late) for a while, then held: one press, held from the
    # first press to the last release, never a second press to toggle AP off again
    s = Sim()
    t0 = s.t
    on = key_trace(s, [(0, 22), (44, 66), (88, 110), (132, 300)], "AP")
    assert runs(on) == [(t0 + 1, 300 + LATE)] and mobiflight_counts(on) == {1}


def hold_trace(events, ms, shifted=False):
    """A fresh panel (SHIFT tapped first if shifted), then events (ms from now, key, pressed): per ms the light
    level and the buttons pressed on both devices"""
    s = Sim()
    if shifted:
        s.key("SHIFT")
    t0, out = s.t, []
    for _ in range(ms):
        for at, name, down in events:
            if s.t - t0 == at:
                s.p.key(name, down, s.t)
        s.run(1)
        out.append((s.p.shift_level(s.t), s.down(1), s.down(2)))
    return out


def presses(trace, dev, name):
    """the presses of a button in a hold_trace"""
    on = [name in entry[dev] for entry in trace]             # entry: (level, device 1, device 2)
    return sum(now and not before for before, now in zip([False] + on, on))


def dropout(key, at, events):
    """events with key open for one scan (KEY_SCAN_MS) from ms at"""
    return sorted(events + [(at, key, False), (at + P.KEY_SCAN_MS, key, True)], key=lambda e: e[0])


def test_chatter_keeps_an_up_hold():
    # UP held 2 s, with a one-scan dropout right after the press: the same steps as a clean hold, the repeats
    # included, not one step as for a short tap
    clean = [(0, "UP", True), (2000, "UP", False)]
    trace = hold_trace(clean, 2600)
    assert presses(trace, 1, "UP") == 1 + len(range(P.REPEAT_DELAY_MS, 2000, P.REPEAT_MS))
    assert hold_trace(dropout("UP", 20, clean), 2600) == trace


def test_chatter_delays_a_repeat_but_does_not_lose_it():
    # the dropout comes as a repeat is due: the repeat waits for the bounce to end, and the count stays. The
    # repeats after it keep their cadence, so a hold let go after one of them was due sends it too, as a clean
    # hold of the same length does. Only the first of them waits for the delayed step (press and gap) to go
    # through, which started `late` after its time: the holds here are let go after that
    clean = [(0, "UP", True), (2000, "UP", False)]
    due = P.REPEAT_DELAY_MS + 2 * P.REPEAT_MS
    trace = hold_trace(dropout("UP", due - 5, clean), 2600)
    assert presses(trace, 1, "UP") == presses(hold_trace(clean, 2600), 1, "UP")
    late = P.KEY_SCAN_MS - 5 + 1                           # the dropout ends, and the next pass sends the repeat
    # the pass that sends the next repeat, in ms after its time: the one after the delayed step is through
    through = late + P.PRESS_MS + P.GAP_MS + 1 - P.REPEAT_MS
    for n in (1, 2):                                       # let go n repeats after the delayed one, and later
        for after in range(through, 3 * P.REPEAT_MS, 5):
            clean = [(0, "UP", True), (due + n * P.REPEAT_MS + after, "UP", False)]
            ms = clean[-1][0] + 400
            assert presses(hold_trace(dropout("UP", due - 5, clean), ms), 1, "UP") == \
                presses(hold_trace(clean, ms), 1, "UP"), (n, after)


# UP held from 0 ms repeats at REPEAT_DELAY_MS and every REPEAT_MS from there: the first repeat due after 1 s
NEXT_REPEAT = next(t for t in range(P.REPEAT_DELAY_MS, 2000, P.REPEAT_MS) if t > 1000)


def test_a_stalled_pass_sends_one_late_repeat():
    # a loop pass stalls while UP is held, past two or more repeats: one repeat for the time missed, then the
    # usual cadence from there, not a burst of the missed ones. The late one goes out a pass after the stall,
    # once the step the stall cut into is through. Past one repeat only, the next one keeps its time and
    # follows as soon as the late step is through
    for late, n in ((P.REPEAT_MS - 2, 2), (P.REPEAT_MS, 1), (2000, 1)):
        s = Sim()
        s.p.key("UP", True, s.t); s.run(1000); s.take()
        s.t = NEXT_REPEAT + late - 1                       # stalled: time passed, no tick() ran
        s.run(P.REPEAT_MS - 1); s.p.key("UP", False, s.t); s.run(1000)
        assert s.take() == [(1, "UP")] * n, late


def test_a_wait_for_the_host_delays_the_repeats_with_the_press():
    # UP pressed, and the send of its press waits 300 ms for the host (code.py then calls stalled()): the PC gets
    # the press 300 ms late, and the first repeat still REPEAT_DELAY_MS after it, then every REPEAT_MS; a tilt
    # the same
    for key, button, delay, every in (("UP", "UP", P.REPEAT_DELAY_MS, P.REPEAT_MS),
                                      ("RANGE_A", "PAN_UP", P.PAN_DELAY_MS, P.PAN_MS)):
        s = Sim()
        s.p.key(key, True, s.t); s.run(1)
        s.t += 300                                         # the wait: no tick() ran
        s.p.stalled(300)
        s.run(1000)
        times = [t for t, _, name in s.log if name == button]          # pressed at 0, the wait added 300
        assert times[1] == 300 + delay and times[2] - times[1] == every, key


def test_a_wait_for_the_host_moves_the_end_of_shift():
    # SHIFT armed, and the loop waits for the host past its ARM_MS: the light stayed lit during the wait, so a
    # key read after it goes out shifted, and SHIFT ends that much later; the same for a knob's session
    s = Sim()
    s.p.key("SHIFT", True, s.t); s.run(P.ARM_MS - 100)
    s.t += 300
    s.p.stalled(300)
    assert s.p.shift_active(s.t) and s.p.shift_level(s.t) != P.LIGHT_OFF
    s.key("VFR"); assert s.take() == [(1, "IDENT")]
    s.p.key("SHIFT", True, s.t); s.run(P.ARM_MS - 1); s.p.stalled(5)
    assert s.p.shift_active(s.t + 5) and not s.p.shift_active(s.t + 6)
    s.take(); s.p.turn("FMS_OUTER", 1, s.t); s.run(P.SESSION_MS - 1); s.p.stalled(5)
    assert s.p.shift_active(s.t + 5) and not s.p.shift_active(s.t + 6)


def test_the_cadence_restarts_at_a_long_stall():
    # after a stall past several repeats, the next repeat is due exactly REPEAT_MS after the late one (sent in
    # the second pass after the stall): held a millisecond less sends only the late one, held to that tick
    # sends the next one too
    for held, n in ((P.REPEAT_MS - 1, 1), (P.REPEAT_MS, 2)):
        s = Sim()
        s.p.key("UP", True, s.t); s.run(1000); s.take()
        s.t = NEXT_REPEAT + 2049                          # stalled, not a whole number of repeats: no tick() ran
        s.run(2 + held); s.p.key("UP", False, s.t); s.run(1000)
        assert s.take() == [(1, "UP")] * n, held


def test_release_just_before_a_repeat_sends_no_extra_step():
    # the release waits BOUNCE_MS for a bounce; a repeat due in that time is not sent
    for key, button, delay in (("UP", "UP", P.REPEAT_DELAY_MS), ("RANGE_A", "PAN_UP", P.PAN_DELAY_MS)):
        events = [(0, key, True), (delay - P.BOUNCE_MS // 2, key, False)]
        assert presses(hold_trace(events, 1000), 1, button) == 1, key


def test_chatter_keeps_a_tilt_repeating():
    # a RANGE tilt held 1.5 s, the direction switch dropping out for a scan twice: it pans as a clean tilt
    clean = [(0, "RANGE_COM", True), (0, "RANGE_A", True), (1500, "RANGE_A", False), (1500, "RANGE_COM", False)]
    trace = hold_trace(clean, 2000)
    assert presses(trace, 1, "PAN_UP") > 8 and presses(trace, 1, "PTR") == 0
    assert hold_trace(dropout("RANGE_A", 900, dropout("RANGE_A", 100, clean)), 2000) == trace


def test_chatter_keeps_a_shifted_push_shifted():
    # SHIFT, then the FMS push held past SESSION_MS with a one-scan dropout after 1 s: SHIFT stays with the knob
    # until SESSION_MS after the release, as for a clean push (docs/using/controls.md), and the push sends one
    # CABIN_LT
    held = P.SESSION_MS + 1000
    clean = [(0, "FMS_PUSH", True), (held, "FMS_PUSH", False)]
    trace = hold_trace(clean, held + P.SESSION_MS + 500, shifted=True)
    assert all(level == P.LIGHT_FULL for level, _, _ in trace[:held + P.SESSION_MS - P.SHIFT_WARN_MS])
    assert trace[-1][0] == P.LIGHT_OFF and presses(trace, 1, "CABIN_LT") == 1
    assert hold_trace(dropout("FMS_PUSH", 1000, clean), held + P.SESSION_MS + 500, shifted=True) == trace


def test_bounce_window_counts_from_the_scans():
    # the keypad scanned the release and the new press one scan apart, but a pass that waited for the host picked
    # the press up 17 ms late, 37 ms after the release: still a bounce, by the scan times code.py passes on
    s = Sim()
    t0 = s.t
    s.p.key("AP", True, s.t); s.run(100)
    s.p.key("AP", False, s.t)
    s.t += P.KEY_SCAN_MS + 17                              # the next pass: no tick() in between
    s.p.key("AP", True, s.t, s.t - 17)
    s.run(200); s.p.key("AP", False, s.t); s.run(200)
    assert s.take() == [(1, "AP")] and s.t == t0 + 100 + P.KEY_SCAN_MS + 17 + 400
    s.p.key("AP", True, s.t); s.run(100)                   # the same 37 ms by the scan times: a new press
    s.p.key("AP", False, s.t)
    s.t += 37
    s.p.key("AP", True, s.t, s.t)
    s.run(200); s.p.key("AP", False, s.t); s.run(200)
    assert s.take() == [(1, "AP"), (1, "AP")]


def test_key_works_normally_after_a_bounce():
    # a bounce, then the key released and later pressed and released normally: both presses and both releases
    # reach the PC, nothing stays held (AP stuck down would block the autopilot key)
    s = Sim()
    on = key_trace(s, [(0, 5), (25, 60), (300, 400)], "AP")
    assert len(runs(on)) == 2 and not on[s.t]
    on = key_trace(s, [(0, 100), (120, 200)], "AP")          # and another bounce after it
    assert len(runs(on)) == 1 and not on[s.t]


def test_release_is_applied_at_once_when_no_bounce():
    # code.py lets go of every key after a keypad overflow: that release goes out at once, and a press right
    # after it is a new press, not a bounce
    s = Sim()
    s.p.key("AP", True, s.t); s.run(100)
    s.p.release("AP", s.t); s.run(1)
    assert s.down(1) == set()
    s.p.key("AP", True, s.t); s.run(200); s.p.key("AP", False, s.t); s.run(200)
    assert s.take() == [(1, "AP"), (1, "AP")]


def test_release_bounce_of_a_long_press_is_not_a_press():
    s = Sim()
    on = key_trace(s, [(0, 300), (322, 330)], "AP")
    assert [n for _, n in runs(on)] == [330 + LATE]


def test_double_tap_80_ms_apart_stays_two_presses():
    s = Sim()
    on = key_trace(s, [(0, 15), (95, 110)], "CLR")
    assert len(runs(on)) == 2 and mobiflight_counts(on) == {2}


def test_bounce_does_not_change_state_twice():
    # a bounce on the SHIFT key does not cancel it, one on a shifted key sends no plain press after the shifted
    # one, one on HOME in SHIFT does not switch UNIT back, one on the FREQ push steps the mode once
    s = Sim()
    key_trace(s, [(0, 5), (25, 60)], "SHIFT")
    assert s.p.shift_active(s.t)
    key_trace(s, [(0, 5), (25, 60)], "AP")
    assert [n for _, n in s.take()] == ["TEST"]
    key_trace(s, [(0, 60)], "SHIFT")
    key_trace(s, [(0, 5), (25, 60)], "HOME")
    assert s.p.unit_light
    key_trace(s, [(0, 5), (25, 60)], "FREQ_PUSH")
    s.turn("FREQ_INNER", 1)
    assert s.take() == [(2, "FREQ_PUSH"), (2, "NAV_KHZ_UP")]


def test_bounce_does_not_repeat_a_step():
    # UP and a RANGE tilt send one step per press, then repeat: a bounce sends no second step, and the centre
    # push sends one PTR
    s = Sim()
    key_trace(s, [(0, 5), (25, 60)], "UP")
    key_trace(s, [(0, 5), (25, 60)], "RANGE_A")
    key_trace(s, [(0, 5), (25, 60)], "RANGE_COM")
    assert [n for _, n in s.take()] == ["UP", "PAN_UP", "PTR"]


def test_bounce_window_boundary():
    # a press BOUNCE_MS after the release is a new press, one just before it is a bounce. Also when one pass
    # (after a stall) reads both: the RANGE centre push, released and pushed again, sends PTR for each push
    for gap, n in ((P.BOUNCE_MS, 2), (P.BOUNCE_MS - 1, 1)):
        s = Sim()
        on = key_trace(s, [(0, 10), (10 + gap, 20 + gap)], "CLR")
        assert len(runs(on)) == n
        s.p.key("RANGE_COM", True, s.t); s.run(100)
        s.t += 100                                         # stalled: both scans come in the next pass
        s.p.key("RANGE_COM", False, s.t, s.t - 60); s.p.key("RANGE_COM", True, s.t, s.t - 60 + gap)
        s.run(100); s.p.key("RANGE_COM", False, s.t); s.run(300)
        assert [name for _, name in s.take()] == ["CLR"] * n + ["PTR"] * n


def test_the_timing_follows_the_poll_the_frames_and_the_scan():
    # press and gap outlast MobiFlight's poll after an edge came three 8 ms HID frames late (a 50 ms gap can
    # arrive as 26 ms, shorter than the 31.25 ms poll); the bounce window is a scan and a half; the warning is
    # whole dim and bright pairs and shorter than SHIFT, which shows steady first
    assert P.HID_FRAME_MS == HID_FRAME_MS and P.POLL_MS >= POLL_MS
    assert P.PRESS_MS == P.GAP_MS == P.POLL_MS + 3 * HID_FRAME_MS
    assert P.BOUNCE_MS * 2 == P.KEY_SCAN_MS * 3
    assert P.SHIFT_WARN_MS % (2 * P.SHIFT_PULSE_MS) == 0 and 0 < P.SHIFT_WARN_MS < min(P.ARM_MS, P.SESSION_MS)
    assert (P.ARM_MS, P.SESSION_MS) == (3000, 5000)        # as the docs give them


def test_reversing_a_knob_drops_the_queued_steps():
    # ten quick detents clockwise, then one back: the knob stops at once, it does not run on clockwise first
    s = Sim()
    s.turn("FMS_INNER", 10, every=10); s.take()
    s.turn("FMS_INNER", -1); s.run(1000)
    assert s.take() == [(1, "FMS_INNER_CCW")]
    s.turn("ALTHDG_OUTER", 6, every=10); s.take()           # slow and coarse steps of one ring both go
    s.turn("ALTHDG_OUTER", -1); s.run(1000)
    assert s.take() == [(1, "ALT_100_DN")]
    s.turn("FMS_INNER", 6, every=10); s.turn("FMS_OUTER", -3, every=10); s.take()   # other rings keep theirs
    s.run(1000)
    assert {n for _, n in s.take()} == {"FMS_INNER_CW", "FMS_OUTER_CCW"}


def test_reversing_drops_slow_and_coarse_steps_of_one_turn():
    # two slow detents (the second still queued), then fast ones, which would go out as a second fine step and
    # two coarse ones: the reversal drops the queued slow step too, not only the coarse ones queued last
    for back, rest in ((0, ["ALT_100_UP"] + ["ALT_1000_UP"] * 2), (-1, ["ALT_100_DN"])):
        s = Sim()
        for gap in (P.FAST_MS + 5, 5, 5, 5):
            s.p.turn("ALTHDG_OUTER", 1, s.t); s.run(gap)
        assert s.take() == [(1, "ALT_100_UP")]
        s.p.turn("ALTHDG_OUTER", back, s.t); s.run(1000)
        assert [n for _, n in s.take()] == rest


def test_reversing_lets_the_running_pulse_finish():
    s = Sim()
    s.turn("FMS_INNER", 5, every=5)                         # the first pulse is pressed now
    s.p.turn("FMS_INNER", -1, s.t)
    trace = pressed_trace(s, 300)
    cw = [t for t in sorted(trace) if "FMS_INNER_CW" in trace[t]]
    assert cw and cw == list(range(cw[0], cw[-1] + 1)) and len(cw) < P.PRESS_MS   # the rest of that press only


def test_two_slow_detents_after_a_stall_stay_slow():
    # the loop stalled (a USB send waited): two detents read at once say nothing about the speed. As in
    # code.py, a pass reads the encoders before its tick(): the detents come 1 ms after the last tick
    s = Sim()
    s.run(100)
    s.t += 1; s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_1000_UP"] * 2   # no stall: two in one read is fast
    s.t += 2000                                              # stalled: time passed, no tick() ran
    s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_100_UP"] * 2
    s.t += P.FAST_MS + 1                                     # a pass just longer than FAST_MS is a stall too
    s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_100_UP"] * 2
    s.t += P.FAST_MS                                         # one of FAST_MS is not
    s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_1000_UP"] * 2


def test_two_slow_detents_read_in_the_first_pass_stay_slow():
    # code.py's first pass reads the encoders before the first tick(), after the start (in keyboard mode its
    # 0.9 s blink): the detents turned meanwhile say nothing about the speed, as after a stall
    s = Sim()
    s.t = 900
    s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_100_UP"] * 2
    s.p.turn("ALTHDG_OUTER", 1, s.t); s.run(P.FAST_MS - 1)  # from then on, as ever: a detent close behind is fast
    s.p.turn("ALTHDG_OUTER", 1, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_100_UP", "ALT_1000_UP"]


def light_and_edges(s, ms):
    """per ms: (light level, button names newly pressed on device 1)"""
    out = []
    for _ in range(ms):
        n = len(s.seen)
        s.run(1)
        out.append((s.p.shift_level(s.t), [name for _, name in s.seen[n:]]))
    return out


def test_shifted_tilt_held_keeps_the_light():
    # a shifted pan held longer than SESSION_MS: the light stays on while S_PAN repeats, then the usual
    # SESSION_MS
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t)
    held = light_and_edges(s, P.SESSION_MS + 2000)
    assert all(level == P.LIGHT_FULL for level, _ in held)
    assert sum(names.count("S_PAN_UP") for _, names in held) > 30
    s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t)
    assert s.p.shift_active(s.t + P.SESSION_MS - 1) and not s.p.shift_active(s.t + P.SESSION_MS)
    after = light_and_edges(s, P.SESSION_MS + 100)
    assert all(names == [] for _, names in after)            # no PTR, no more pan
    assert after[-1][0] == P.LIGHT_OFF


def test_shifted_centre_push_held_stays_shifted():
    # SHIFT, then the RANGE centre held past SESSION_MS: the light stays on, and the release sends S_PTR
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t)
    assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, P.SESSION_MS + 1000))
    s.p.key("RANGE_COM", False, s.t); s.run(200)
    assert s.take() == [(1, "S_PTR")]


def test_centre_push_is_shifted_as_at_its_press():
    # SHIFT is decided when the centre goes down, as the light showed then
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t); s.run(100)
    s.turn("FMS_OUTER", 1); assert not s.p.shift_active(s.t)   # another knob ends SHIFT while the centre is held
    s.p.key("RANGE_COM", False, s.t); s.run(200)
    assert s.take() == [(1, "FMS_OUTER_CW"), (1, "S_PTR")]
    s.p.key("RANGE_COM", True, s.t); s.run(100)
    s.key("SHIFT")                                           # tapped while an unshifted centre is held
    s.p.key("RANGE_COM", False, s.t); s.run(200)
    assert s.take() == [(1, "PTR")]
    s.key("AP"); assert s.take() == [(1, "TEST")]            # the tap still arms the next key


def test_held_shifted_tilt_survives_a_stalled_pass():
    # one loop pass stalls for longer than SESSION_MS while a shifted tilt is held: the session goes on
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(500)
    s.t += P.SESSION_MS + 500                                # stalled: time passed, no tick() ran
    held = light_and_edges(s, 1000)
    assert all(level == P.LIGHT_FULL for level, _ in held)
    assert sum(names.count("S_PAN_UP") for _, names in held) >= 5
    s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(200)
    assert s.p.shift_active(s.t)


def test_held_shifted_push_survives_a_stalled_pass():
    # the same when the stalled pass first reads an input: the release, then a turn of the same knob. Also for a
    # release after a keypad overflow, which code.py applies at once
    for overflow in (False, True):
        s = Sim()
        s.key("SHIFT"); s.take()
        s.p.key("ALTHDG_PUSH", True, s.t); s.run(100)
        s.t += P.SESSION_MS + 500                            # stalled: time passed, no tick() ran
        if overflow:
            s.p.release("ALTHDG_PUSH", s.t)
        else:
            s.p.key("ALTHDG_PUSH", False, s.t)
        assert s.p.shift_active(s.t + P.SESSION_MS - 1) and not s.p.shift_active(s.t + P.SESSION_MS)
        s.turn("ALTHDG_INNER", 1)
        assert s.take() == [(1, "BARO_STD"), (1, "CRS_1_UP")]


def test_shifted_push_held_keeps_the_light():
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("ALTHDG_PUSH", True, s.t)
    assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, P.SESSION_MS + 1000))
    assert s.take() == [(1, "BARO_STD")]
    s.p.key("ALTHDG_PUSH", False, s.t)
    s.run(P.SESSION_MS - 100); assert s.p.shift_active(s.t)
    s.run(200); assert not s.p.shift_active(s.t)


def test_shift_taps_keep_a_held_shifted_tilt():
    # SHIFT tapped once or twice during a held shifted pan: S_PAN goes on and the light stays on until the
    # release; one tap arms the next key for 3 s (test_an_armed_shift_runs_out_under_a_held_push), a second tap
    # cancels only that
    for taps, key in ((1, "TEST"), (2, "AP")):
        s = Sim()
        s.key("SHIFT"); s.take()
        s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(1500)
        for _ in range(taps):
            s.p.key("SHIFT", True, s.t); s.run(30); s.p.key("SHIFT", False, s.t); s.run(30)
        held = light_and_edges(s, P.ARM_MS - 1000)
        assert all(level == P.LIGHT_FULL for level, _ in held)
        assert sum(names.count("S_PAN_UP") for _, names in held) > 15
        s.take(); s.key("AP")                                       # within the tap's 3 s, the tilt still held
        assert [n for _, n in s.take() if not n.startswith("S_PAN")] == [key]
        s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(200)
        assert s.p.shift_active(s.t)


def test_an_armed_shift_runs_out_under_a_held_push():
    # a tap during a held shifted push arms the next key for ARM_MS, as without the push: VFR sends IDENT within
    # them and VFR after them, while the push still keeps its session and the light until SESSION_MS after its
    # release
    for wait, key in ((1000, "IDENT"), (P.ARM_MS + 100, "VFR")):
        s = Sim()
        s.key("SHIFT"); s.p.key("FREQ_PUSH", True, s.t); s.run(200)
        tap(s, "SHIFT"); s.run(wait)
        assert s.p.shift_level(s.t) == P.LIGHT_FULL
        s.take(); s.key("VFR"); assert s.take() == [(1, key)], wait
        assert s.p.shift == "FREQ"
        s.p.key("FREQ_PUSH", False, s.t); s.run(P.SESSION_MS - 100); assert s.p.shift_active(s.t)
        s.run(200); assert not s.p.shift_active(s.t)
    # a stalled loop pass moves the arm's end with the session's
    s = Sim()
    s.key("SHIFT"); s.p.key("FREQ_PUSH", True, s.t); s.run(200); tap(s, "SHIFT")
    s.p.stalled(5000); s.t += 5000; s.run(1000)
    s.take(); s.key("VFR"); assert s.take() == [(1, "IDENT")]


def test_shift_taps_keep_a_held_shifted_push():
    for taps in (1, 2):
        s = Sim()
        s.key("SHIFT"); s.take()
        s.p.key("ALTHDG_PUSH", True, s.t); s.run(1500)
        for _ in range(taps):
            s.p.key("SHIFT", True, s.t); s.run(30); s.p.key("SHIFT", False, s.t); s.run(30)
        assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, P.SESSION_MS + 1000))
        assert s.take() == [(1, "BARO_STD")]
        s.p.key("ALTHDG_PUSH", False, s.t); s.run(P.SESSION_MS - 100); assert s.p.shift_active(s.t)
        s.run(200); assert not s.p.shift_active(s.t)


def test_a_tap_just_before_the_release_arms_for_arm_ms_from_the_tap():
    # the arm ends ARM_MS after the tap, the key read at ARM_MS - 1 is shifted and the one at ARM_MS plain; the
    # released push's session goes on until SESSION_MS after the release (applied within its BOUNCE_MS)
    for wait, sent in ((P.ARM_MS - 1, "IDENT"), (P.ARM_MS, "VFR"), (None, None)):
        s = Sim()
        s.key("SHIFT"); s.p.key("ALTHDG_PUSH", True, s.t); s.run(P.SESSION_MS + 1000)
        s.p.key("SHIFT", True, s.t); tapped = s.t; s.run(30); s.p.key("SHIFT", False, s.t); s.run(30)
        s.p.key("ALTHDG_PUSH", False, s.t); released = s.t
        s.take()
        if wait is not None:
            s.run(tapped + wait - s.t); assert s.p.shift_active(s.t), wait
            s.key("VFR"); assert s.take() == [(1, sent)], wait
            continue
        s.run(P.BOUNCE_MS + 1)
        end = s.p.shift_until
        assert released + P.SESSION_MS <= end <= released + P.BOUNCE_MS + P.SESSION_MS
        s.run(end - 1 - s.t); assert s.p.shift_active(s.t) and s.p.shift == "ALTHDG"
        s.run(1); assert not s.p.shift_active(s.t)


def tap(s, name):
    s.p.key(name, True, s.t); s.run(30); s.p.key(name, False, s.t); s.run(30)


def hold_shifted_tilt(s):
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(1000)


def test_keys_keep_a_held_shifted_tilt():
    # no key ends the session a held tilt keeps: a plain key, a key that a SHIFT tap armed, SHIFT taps. S_PAN
    # and the light go on until the release, then the usual SESSION_MS
    for keys, sent in ((["AP"], ["AP"]), (["SHIFT", "VFR"], ["IDENT"]),
                       (["SHIFT", "VFR", "SHIFT", "SHIFT", "AP"], ["IDENT", "AP"])):
        s = Sim()
        hold_shifted_tilt(s)
        for k in keys:
            tap(s, k)
        held = light_and_edges(s, P.SESSION_MS + 1000)
        assert all(level == P.LIGHT_FULL for level, _ in held), keys
        assert sum(names.count("S_PAN_UP") for _, names in held) > 30, keys
        assert [n for _, n in s.take() if n != "S_PAN_UP"] == sent, keys
        s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t)
        s.run(P.SESSION_MS - 100); assert s.p.shift_active(s.t), keys
        s.run(200); assert not s.p.shift_active(s.t), keys


def test_armed_key_keeps_a_held_shifted_push():
    s = Sim()
    s.key("SHIFT"); s.p.key("ALTHDG_PUSH", True, s.t); s.run(500)
    tap(s, "SHIFT"); tap(s, "VFR")
    assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, P.SESSION_MS + 1000))
    s.turn("ALTHDG_INNER", 1)                                # still the shifted session: CRS
    assert s.take() == [(1, "BARO_STD"), (1, "IDENT"), (1, "CRS_1_UP")]


def test_second_tap_cancels_shift_unless_a_control_is_held():
    # the held push is let go between the two taps: the second tap cancels SHIFT. The same right after a
    # squawk entry: the first tap arms SHIFT, the second ends the knob's session too
    s = Sim()
    s.key("SHIFT"); s.p.key("ALTHDG_PUSH", True, s.t); s.run(500)
    tap(s, "SHIFT")
    s.p.key("ALTHDG_PUSH", False, s.t); s.run(100); assert s.p.shift_active(s.t)
    tap(s, "SHIFT"); assert s.p.shift_level(s.t) == P.LIGHT_OFF
    s.turn("ALTHDG_INNER", 1)
    assert s.take() == [(1, "BARO_STD"), (1, "HDG_1_UP")]
    s.key("SHIFT"); s.turn("FREQ_INNER", 1)
    tap(s, "SHIFT"); tap(s, "SHIFT"); assert s.p.shift_level(s.t) == P.LIGHT_OFF
    s.turn("FREQ_INNER", 1)
    assert s.take() == [(1, "SQK_D1_UP"), (1, "COM_KHZ_UP")]


def test_a_plain_push_held_does_not_keep_shift():
    # only a push made in a shifted session keeps it: SHIFT and a turn while a plain push is held end the
    # session SESSION_MS after the detent, push still held
    s = Sim()
    s.p.key("ALTHDG_PUSH", True, s.t); s.run(100)
    s.key("SHIFT"); s.turn("ALTHDG_INNER", 1, every=1)
    s.run(P.SESSION_MS - 100); assert s.p.shift_active(s.t)
    s.run(100); assert not s.p.shift_active(s.t)
    assert s.take() == [(1, "HDG_SYNC"), (1, "CRS_1_UP")]


def test_shifted_repeat_stops_when_another_knob_takes_shift():
    # SHIFT tapped during a shifted pan, then the FMS knob turned: the arming goes to the FMS knob (lighting),
    # which ends the RANGE session. The light stays on for the FMS knob, but the tilt stops sending S_PAN
    s = Sim()
    hold_shifted_tilt(s)
    tap(s, "SHIFT")
    s.turn("FMS_OUTER", 1, every=P.PRESS_MS)              # the step follows the pan step on its way
    assert s.take()[-1] == (1, "PANEL_LT_UP")
    rest = light_and_edges(s, 4000)
    assert all(level != P.LIGHT_OFF for level, _ in rest[:2500])
    assert not any("S_PAN_UP" in names for _, names in rest)


def test_shifted_repeat_stops_when_shift_is_armed_after_its_session_ended():
    # in one loop pass another knob's push ends the RANGE session and SHIFT is tapped: the light is on for
    # the armed SHIFT, which no longer belongs to the tilt, so S_PAN stops
    s = Sim()
    hold_shifted_tilt(s)
    s.p.key("FMS_PUSH", True, s.t); s.p.key("SHIFT", True, s.t)
    rest = light_and_edges(s, 2000)
    assert rest[0][0] == P.LIGHT_FULL and not any("S_PAN_UP" in names for _, names in rest)


def test_shifted_repeat_stops_when_another_control_ends_shift():
    # the other hand turns the FMS knob during a shifted pan: SHIFT ends, the light goes dark, and the
    # held tilt stops sending S_PAN (lit means shifted)
    s = Sim()
    s.key("SHIFT")
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(1000)
    s.turn("FMS_OUTER", 1, every=1); s.take()
    rest = light_and_edges(s, 2000)
    assert all(level == P.LIGHT_OFF and "S_PAN_UP" not in names for level, names in rest)


def go_dark(s):
    s.p.dark = True; s.run(100); s.p.dark = False


def test_a_control_held_from_an_ended_session_keeps_no_later_one():
    # a shifted push or tilt still held when another knob or USB going down ends its session keeps no later
    # session of its knob: SHIFT and a turn start a new one, which ends SESSION_MS after the detent as without it
    for held, ring in ((("FREQ_PUSH",), "FREQ_INNER"), (("RANGE_COM", "RANGE_A"), "RANGE")):
        for end in (lambda s: s.turn("FMS_OUTER", 1), go_dark):
            s = Sim()
            s.key("SHIFT")
            for name in held:
                s.p.key(name, True, s.t)
            s.run(200)
            end(s); assert not s.p.shift_active(s.t)
            s.key("SHIFT"); s.turn(ring, 1, every=1)
            s.run(P.SESSION_MS - 100); assert s.p.shift_active(s.t), held
            s.run(100); assert not s.p.shift_active(s.t), held
            s.take(); s.turn(ring, 1)
            assert s.take() == [(1, "COM_KHZ_UP" if ring == "FREQ_INNER" else "RANGE_CW")]
            for name in held:
                s.p.key(name, False, s.t)
            s.run(200)
            assert s.take() == []                        # no more S_PAN, and no PTR after a tilt


def test_solo_presses_one_button_at_a_time():
    # the keyboard mode's panel: a detent while a key is held goes out once the key is up (at its turn without
    # solo), and pressed() names the one button down
    for solo in (False, True):
        s = Sim(solo)
        assert s.p.pressed() is None
        s.p.key("AP", True, s.t); s.run(10)
        assert s.p.pressed() == (1, BM.BUTTON[1]["AP"])
        s.p.turn("ALTHDG_OUTER", 1, s.t); s.run(300)
        assert s.take() == ([(1, "AP")] if solo else [(1, "AP"), (1, "ALT_100_UP")])
        s.p.key("AP", False, s.t); s.run(300)
        released = s.t - 300 + P.BOUNCE_MS
        assert s.take() == ([(1, "ALT_100_UP")] if solo else [])
        assert not solo or s.log[-1] == (released, 1, "ALT_100_UP")     # in the same pass as AP's release
        assert s.p.pressed() is None


def test_solo_keeps_the_order_and_the_spacing():
    # a turn with a key in between: the same presses, in the same order and 112 ms apart, with or without solo
    logs = []
    for solo in (False, True):
        s = Sim(solo)
        s.turn("FREQ_INNER", 3, every=20); s.key("COM_SWAP", 20); s.turn("FREQ_INNER", 2, every=20); s.run(1000)
        logs.append(s.log)
    assert logs[0] == logs[1] and [n for _, _, n in logs[0]] == ["COM_KHZ_UP"] * 3 + ["COM_SWAP"] + ["COM_KHZ_UP"] * 2


def test_counts():
    assert len(BM.DEVICE[1]) == 117 and len(BM.DEVICE[2]) == 39
    assert BM.DEVICE[1][-5:] == BM.LIGHTING                          # lighting is the tail of device 1
    assert BM.BUTTON[1]["VFR"] == 16 and BM.BUTTON[1]["IDENT"] == 33  # the key's plain and shifted function
    for name in sum(BM.MATRIX, ()):
        assert name in ("SHIFT", "RANGE_A", "RANGE_B", "RANGE_C", "RANGE_D", "RANGE_COM", "ALTHDG_PUSH",
                        "FMS_PUSH") or name in BM.BUTTON[1], name

# Button numbers as of the first build (rev 1): the MobiFlight configs of every user depend on them. New
# buttons may only be appended; to change this list on purpose, everyone's mappings have to change too.
FROZEN = {
    1: (
        "AP", "ALT", "HDG", "FD", "VS", "NAV", "UP", "FLC", "APR", "DN", "VNV", "LVL", "MIC1", "COM1",
        "MIC2", "COM2", "VFR", "TEST", "ARM", "CRS_CTR", "YD", "S_VS", "GPSS", "S_UP", "S_FLC", "BC",
        "S_DN", "S_VNV", "HALF_BANK", "ADF_AUDIO", "NAV1_AUDIO", "DME_AUDIO", "NAV2_AUDIO", "IDENT",
        "ALT_100_UP", "ALT_100_DN", "ALT_1000_UP", "ALT_1000_DN", "HDG_1_UP", "HDG_1_DN", "HDG_10_UP",
        "HDG_10_DN", "HDG_SYNC", "CRS_1_UP", "CRS_1_DN", "CRS_10_UP", "CRS_10_DN", "BARO_UP", "BARO_DN",
        "BARO_STD", "RANGE_CW", "RANGE_CCW", "PAN_UP", "PAN_DN", "PAN_LEFT", "PAN_RIGHT", "PTR",
        "S_RANGE_CW", "S_RANGE_CCW", "S_PAN_UP", "S_PAN_DN", "S_PAN_LEFT", "S_PAN_RIGHT", "S_PTR",
        "SQK_D2_UP", "SQK_D2_DN", "SQK_D1_UP", "SQK_D1_DN", "SQK_D4_UP", "SQK_D4_DN", "SQK_D3_UP",
        "SQK_D3_DN", "XPDR_MODE", "CDI", "COM_SWAP", "NAV_SWAP", "HOME", "FPL", "DIRECT", "MENU", "PROC",
        "CLR", "ENT", "OBS", "COM_121_5", "ADF_SWAP", "VNAV", "MSG", "NRST", "TERR", "MAP", "S_ENT",
        "FMS_OUTER_CW", "FMS_OUTER_CCW", "FMS_INNER_CW", "FMS_INNER_CCW", "FMS_CRSR", "COM_MHZ_UP",
        "COM_MHZ_DN", "COM_KHZ_UP", "COM_KHZ_DN", "NAV_MHZ_UP", "NAV_MHZ_DN", "NAV_KHZ_UP", "NAV_KHZ_DN",
        "ADF_100_UP", "ADF_100_DN", "ADF_1_UP", "ADF_1_DN", "ADF_10_UP", "ADF_10_DN", "FREQ_PUSH",
        "PANEL_LT_UP", "PANEL_LT_DN", "FLOOD_LT_UP", "FLOOD_LT_DN", "CABIN_LT"
    ),
    2: (
        "CDI", "COM_SWAP", "NAV_SWAP", "HOME", "FPL", "DIRECT", "MENU", "PROC", "CLR", "ENT", "OBS",
        "COM_121_5", "ADF_SWAP", "VNAV", "MSG", "NRST", "TERR", "MAP", "S_ENT", "FMS_OUTER_CW",
        "FMS_OUTER_CCW", "FMS_INNER_CW", "FMS_INNER_CCW", "FMS_CRSR", "COM_MHZ_UP", "COM_MHZ_DN",
        "COM_KHZ_UP", "COM_KHZ_DN", "NAV_MHZ_UP", "NAV_MHZ_DN", "NAV_KHZ_UP", "NAV_KHZ_DN", "ADF_100_UP",
        "ADF_100_DN", "ADF_1_UP", "ADF_1_DN", "ADF_10_UP", "ADF_10_DN", "FREQ_PUSH"
    ),
}


def test_button_numbers_are_frozen():
    for dev, names in FROZEN.items():
        assert tuple(BM.DEVICE[dev][:len(names)]) == names, f"device {dev}: a button number moved"


# ---------------- the FREQ light ----------------
def flash_at(p, t):
    """whether the FREQ light shows a flash of its count at t: lit, inside the count's flashes"""
    start, n = p.flash
    return 0 <= t - start < n * P.FLASH_EVERY_MS and p.freq_lit(t)


def flashes(p, t0, ms=1500):
    """ms from t0 to the start of each flash of the FREQ light's counts"""
    out, was = [], False
    for t in range(t0, t0 + ms):
        flash = flash_at(p, t)
        if flash and not was:
            out.append(t - t0)
        was = flash
    return out


EVERY = P.FLASH_EVERY_MS


def watch(s, ms, lit):
    """runs s ms, appending the FREQ light's flash state of each ms to lit (as code.py reads it, pass by pass)"""
    for _ in range(ms):
        s.run(1)
        lit.append(flash_at(s.p, s.t))


def starts(lit):
    """the indices where a flash starts in lit"""
    return [i for i, on in enumerate(lit) if on and (i == 0 or not lit[i - 1])]


def test_a_freq_push_counts_its_new_mode():
    # NAV twice, ADF three times, COM once: short flashes, FLASH_EVERY_MS apart; ADF's after a dark pause, as
    # NAV's light was on
    s = Sim()
    for mode, n, wait in ((1, 2, 0), (2, 3, P.FLASH_PAUSE_MS), (0, 1, 0)):
        t0 = s.t
        s.key("FREQ_PUSH")
        assert s.p.freq_mode == mode and flashes(s.p, t0) == [wait + i * EVERY for i in range(n)]
        s.run(1500)                                                    # (ADF's blink then in its dark half)
    t0 = s.t
    assert flashes(s.p, t0) == []                                      # done: the light shows the mode again


def test_a_flash_is_short():
    # on a dark light, COM before the push; NAV's light only after a pause from the last flash
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0)
    back = EVERY + P.FLASH_MS + P.FLASH_PAUSE_MS
    lit = [s.p.freq_lit(t) for t in range(t0, t0 + back + 1)]
    assert lit[:P.FLASH_MS] == [True] * P.FLASH_MS and not any(lit[P.FLASH_MS:EVERY])
    assert lit[EVERY:EVERY + P.FLASH_MS] == [True] * P.FLASH_MS and not any(lit[EVERY + P.FLASH_MS:back])
    assert lit[back] and not s.p.freq_lit(t0 - 1)


def test_the_freq_light_shows_the_mode():
    # off COM, on NAV, ADF a slow blink that starts dark once its count is over; a count still to come (a squawk
    # digit's, while its ring rests) keeps the light dark
    s = Sim()
    assert not any(s.p.freq_lit(s.t + ms) for ms in range(3000))
    s.key("FREQ_PUSH"); s.run(1000)
    assert all(s.p.freq_lit(s.t + ms) for ms in range(3000))
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0); s.p.key("FREQ_PUSH", False, t0 + 1)   # ADF: 3 flashes, after a pause
    back = t0 + P.FLASH_PAUSE_MS + 2 * EVERY + P.FLASH_MS + P.FLASH_PAUSE_MS
    half = P.FREQ_BLINK_MS // 2
    assert [s.p.freq_lit(t) for t in (back - 1, back, back + half - 1, back + half, back + 2 * half - 1)] == [
        False, False, False, True, True]
    assert not s.p.freq_lit(back + 2 * half) and s.p.freq_lit(back + 3 * half)
    s.run(3000)
    s.key("SHIFT")
    t0 = s.t
    s.p.turn("FREQ_OUTER", 1, t0)                                          # digit 2, counted after its rest
    assert not any(s.p.freq_lit(t) for t in range(t0, t0 + P.SQUAWK_REST_MS))
    s.run(5000)
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)  # COM
    s.run(1000)
    assert s.p.freq_mode == 0 and not any(s.p.freq_lit(s.t + ms) for ms in range(3000))


PAUSE = P.FLASH_MS + P.FLASH_PAUSE_MS        # from a flash's start to the next count's first


def double_push(gap):
    """the starts of the FREQ light's flashes (lit[i]: the light at i + 1 ms) for two FREQ pushes gap ms apart"""
    s, lit = Sim(), []
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)   # NAV: 2, cut short by the next push
    watch(s, gap, lit)
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)   # ADF: 3, after a pause
    watch(s, 1500, lit)
    assert s.p.freq_mode == 2
    return starts(lit)


def test_a_new_count_waits_for_a_pause():
    # a second push while the first count runs: the first stops where it is, and the latest mode is counted after
    # a pause clearly longer than the gaps inside a count, so the two never read as one number
    assert double_push(100) == [0, PAUSE - 1, PAUSE - 1 + EVERY, PAUSE - 1 + 2 * EVERY]       # in a gap
    assert double_push(40) == [0, PAUSE - 1, PAUSE - 1 + EVERY, PAUSE - 1 + 2 * EVERY]        # in a flash
    late = EVERY + PAUSE - 1                                                                  # in the second
    assert double_push(210) == [0, EVERY - 1, late, late + EVERY, late + 2 * EVERY]
    assert P.FLASH_PAUSE_MS > 2 * (EVERY - P.FLASH_MS)


def test_a_count_after_one_just_over_waits_too():
    s, lit = Sim(), []
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)
    watch(s, EVERY + P.FLASH_MS + 10, lit)                             # NAV's two flashes, just over
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)
    watch(s, 1500, lit)
    assert starts(lit) == [0, EVERY - 1, EVERY + PAUSE - 1, EVERY + PAUSE - 1 + EVERY, EVERY + PAUSE - 1 + 2 * EVERY]


def test_a_bounce_does_not_restart_a_count():
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0)
    s.p.key("FREQ_PUSH", False, t0 + 5)                                # bounces within BOUNCE_MS
    s.p.key("FREQ_PUSH", True, t0 + 10)
    s.p.key("FREQ_PUSH", False, t0 + 100)
    s.run(1)
    assert s.p.freq_mode == 1 and s.p.flash == (t0, 2)


def test_a_hold_read_late_counts_com_once():
    # after a wait for the host the loop reads a long hold at once: NAV's count is due the same ms and never shown,
    # so the light counts COM alone, at once
    s = Sim()
    s.t = 4000
    s.p.key("FREQ_PUSH", True, s.t, at=2000)
    s.p.key("FREQ_PUSH", False, s.t, at=3500)
    s.p.tick(s.t)
    assert s.p.freq_mode == 0 and flashes(s.p, s.t) == [0]


def test_a_wait_for_the_host_moves_the_count():
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0)
    s.p.stalled(500)
    assert flashes(s.p, t0, 1500) == [500, 500 + EVERY]


def test_a_unit_change_keeps_a_count():
    # SHIFT, HOME in NAV's second flash: the white light shows unit 2 at once, the green one counts on
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0); s.p.key("FREQ_PUSH", False, t0 + 1)   # NAV: flashes at 0 and EVERY
    s.run(100)
    s.p.key("SHIFT", True, s.t); s.run(40); s.p.key("SHIFT", False, s.t)
    s.run(EVERY + 5 - (s.t - t0))
    s.p.key("HOME", True, s.t)                                             # UNIT, in the second flash
    assert s.p.unit_light and s.p.flash == (t0, 2) and flash_at(s.p, s.t)


def test_a_third_push_comes_in_place_of_the_count_still_to_come():
    # three pushes 100 ms apart: the third's count (COM) takes the place of the second's, which waits for its pause,
    # and keeps its start: one flash after the pause, never NAV's or ADF's number
    s = Sim()
    t0 = s.t
    for at in (0, 100, 200):
        s.p.key("FREQ_PUSH", True, t0 + at); s.p.key("FREQ_PUSH", False, t0 + at + 1)
    assert s.p.freq_mode == 0 and s.p.flash == (t0 + PAUSE, 1) and flashes(s.p, t0 + 201) == [PAUSE - 201]


def test_a_key_keeps_a_freq_count_still_to_come():
    # COM ⇆ in the pause before ADF's count: only a squawk digit's count is dropped by a key
    s = Sim()
    t0 = s.t
    for at in (0, 100):
        s.p.key("FREQ_PUSH", True, t0 + at); s.p.key("FREQ_PUSH", False, t0 + at + 1)
    s.p.key("COM_SWAP", True, t0 + 150)
    assert s.p.flash == (t0 + PAUSE, 3)


def test_a_key_does_not_cut_a_squawk_count_under_way():
    # a key in the flashes of a digit already counted ends the entry, but the count shown goes on
    s = Sim()
    s.key("SHIFT")
    t0 = s.t
    s.p.turn("FREQ_OUTER", 2, t0)                                          # digit 3, counted after its rest
    s.p.key("AP", True, t0 + P.SQUAWK_REST_MS + 10)
    assert s.p.flash == (t0 + P.SQUAWK_REST_MS, 3)


def test_a_hold_that_runs_out_while_dark_shows_no_count():
    # USB drops for the pass in which the hold returns to COM: its count is never shown, also once USB is back
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0)
    s.run(P.FREQ_HOLD_MS - 1)
    s.p.dark = True
    s.run(1)                                                               # the hold runs out
    s.p.dark = False
    assert s.p.freq_mode == 0 and s.p.flash[1] == 0 and flashes(s.p, s.t) == []


def test_a_freq_hold_counts_com():
    # the push counts its mode at once; held, the return to COM counts one when the hold runs out, after a dark
    # pause: NAV's light was on
    s, lit = Sim(), []
    s.p.key("FREQ_PUSH", True, s.t)
    watch(s, P.FREQ_HOLD_MS + 900, lit)
    assert s.p.freq_mode == 0 and starts(lit) == [0, EVERY - 1, P.FREQ_HOLD_MS + P.FLASH_PAUSE_MS - 1]   # (lit[i]:
                                                                                                      # i + 1 ms)


def test_a_shifted_freq_push_counts_nothing():
    # XPDR mode: the FREQ mode stays, and the light says nothing about it
    s = Sim()
    s.key("SHIFT")
    t0 = s.t
    s.key("FREQ_PUSH")
    assert s.p.freq_mode == 0 and flashes(s.p, t0) == []


def test_the_squawk_outer_ring_counts_its_digit():
    # the digit it selects, once the ring rests, also when it finds the ring at an end
    s = Sim()
    s.key("SHIFT")
    rest = P.SQUAWK_REST_MS
    for steps, digit in ((1, 2), (1, 3), (1, 4), (1, 4), (-3, 1), (-1, 1)):
        t0 = s.t
        s.p.turn("FREQ_OUTER", steps, t0)
        assert s.p.digit == digit and flashes(s.p, t0, 1500) == [rest + i * EVERY for i in range(digit)], digit
        s.run(1500)
    t0 = s.t
    s.turn("FREQ_INNER", 1)                                            # the inner ring sets the digit: no count
    assert flashes(s.p, t0) == []


def test_a_squawk_spin_counts_the_last_digit_once():
    # detents 100 ms apart, 1 to 4: no flash while the ring turns, then four, once
    s = Sim()
    s.key("SHIFT")
    t0 = s.t
    for i in range(3):
        s.p.turn("FREQ_OUTER", 1, t0 + 100 * i)
    assert s.p.digit == 4 and flashes(s.p, t0, 2000) == [200 + P.SQUAWK_REST_MS + i * EVERY for i in range(4)]


def test_from_nav_a_count_shows_on_a_dark_light():
    # NAV's light goes dark for ADF's count, a pause before its first flash, so that flash stands on its own
    s = Sim()
    s.key("FREQ_PUSH"); s.run(1000)
    t0 = s.t
    nav = s.p.freq_lit(t0)
    s.p.key("FREQ_PUSH", True, t0)
    first = t0 + P.FLASH_PAUSE_MS
    assert nav and [s.p.freq_lit(t) for t in (t0, first - 1, first, first + P.FLASH_MS - 1, first + P.FLASH_MS)] == [
        False, False, True, True, False]


def light(s, ms):
    """runs s ms, the FREQ light of each ms as code.py reads it, pass by pass (the first: the ms after now)"""
    out = []
    for _ in range(ms):
        s.run(1)
        out.append(s.p.freq_lit(s.t))
    return out


def lit_runs(lit):
    """(index, length) of every stretch the light is on in lit"""
    out = []
    for i, on in enumerate(lit):
        if on and (i == 0 or not lit[i - 1]):
            out.append([i, 0])
        if on:
            out[-1][1] += 1
    return [tuple(r) for r in out]


def test_a_quick_second_push_keeps_the_pause_after_navs_light():
    # NAV's light on, then two pushes 120 ms apart: COM's count takes the place of ADF's, still to come, and its
    # flash still waits FLASH_PAUSE_MS after NAV's light went dark, so it never reads as a gap inside a count
    s = Sim()
    s.key("FREQ_PUSH"); s.run(1000)
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0)
    lit = light(s, 40)
    s.p.key("FREQ_PUSH", False, s.t)
    lit += light(s, 80)
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)
    lit += light(s, 1500)
    assert s.p.freq_mode == 0 and lit_runs(lit) == [(P.FLASH_PAUSE_MS - 1, P.FLASH_MS)]


def test_a_push_in_adfs_dark_half_keeps_the_pause_after_its_lit_half():
    # ADF's blink, a push 50 ms after a lit half ended: COM's flash comes FLASH_PAUSE_MS after that lit half
    s = Sim()
    s.p.freq_mode = 2
    s.run(2 * P.FREQ_BLINK_MS + 50)
    t0 = s.t
    assert s.p.freq_lit(t0 - 51) and not s.p.freq_lit(t0 - 50) and not s.p.freq_lit(t0 - 1)
    s.p.key("FREQ_PUSH", True, t0); s.p.key("FREQ_PUSH", False, t0 + 1)
    lit = light(s, 1000)
    assert s.p.freq_mode == 0 and lit_runs(lit) == [(P.FLASH_PAUSE_MS - 51, P.FLASH_MS)]


def test_a_squawk_count_waits_the_pause_after_navs_light():
    # NAV's light on, SHIFT, the outer ring to digit 2: dark FLASH_PAUSE_MS (more than the ring's rest), two
    # flashes, the pause, NAV's light again
    s = Sim()
    s.key("FREQ_PUSH"); s.run(1000)
    s.key("SHIFT")
    t0 = s.t
    s.p.turn("FREQ_OUTER", 1, t0)
    lit = light(s, 1500)
    first = P.FLASH_PAUSE_MS - 1
    back = first + P.FLASH_EVERY_MS + P.FLASH_MS + P.FLASH_PAUSE_MS
    assert lit_runs(lit) == [(first, P.FLASH_MS), (first + P.FLASH_EVERY_MS, P.FLASH_MS), (back, 1500 - back)]


def test_a_push_soon_after_navs_light_came_on_keeps_it_on():
    # COM, a push, a second push 700 ms later, just after NAV's light came on: it stays on LIT_MIN_MS, so it never
    # reads as a flash between NAV's count and ADF's, then dark FLASH_PAUSE_MS and ADF's three flashes
    s = Sim()
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)
    lit = light(s, 700)
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)
    lit += light(s, 2000)
    nav = EVERY + PAUSE - 1
    first = nav + P.LIT_MIN_MS + P.FLASH_PAUSE_MS
    runs = [(0, P.FLASH_MS - 1), (EVERY - 1, P.FLASH_MS), (nav, P.LIT_MIN_MS)]   # (lit[i]: i + 1 ms)
    assert s.p.freq_mode == 2 and lit_runs(lit)[:6] == runs + [(first + i * EVERY, P.FLASH_MS) for i in range(3)]
    assert P.FLASH_MS < P.FLASH_EVERY_MS < P.LIT_MIN_MS <= P.FREQ_BLINK_MS // 2


def mode_and_flashes(s, ms, out):
    """runs s ms, appending the FREQ light of each ms to out, as (lit, a flash of a count)"""
    for _ in range(ms):
        s.run(1)
        out.append((s.p.freq_lit(s.t), flash_at(s.p, s.t)))
    return out


def no_short_mode(seen, first=True):
    """whether the mode, in seen (mode_and_flashes), is lit LIT_MIN_MS at least each time (one still on at the end
    aside, and one already on at the start unless first)"""
    runs = lit_runs([lit for lit, _ in seen])
    return all(n >= P.LIT_MIN_MS for i, n in runs
               if i + n < len(seen) and (first or i) and not any(f for _, f in seen[i:i + n]))


def test_the_mode_is_never_lit_for_less_than_its_minimum():
    # whenever a count comes, the mode's light that it darkens was on LIT_MIN_MS at least: a second push any gap
    # after the first, a squawk detent any time after NAV's count, a push in any phase of ADF's blink, and a push
    # any time after USB came back
    def push(s):
        s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)

    def digit(s):
        s.p.key("SHIFT", True, s.t); s.p.key("SHIFT", False, s.t + 1); s.p.turn("FREQ_OUTER", 1, s.t)

    for gap in range(0, 1500, 9):
        for then in (push, digit):
            s, seen = Sim(), []
            push(s)
            mode_and_flashes(s, gap, seen)
            then(s)
            assert no_short_mode(mode_and_flashes(s, 1700, seen)), (gap, then.__name__)
    for phase in range(0, P.FREQ_BLINK_MS, 9):
        s, seen = Sim(), []
        s.p.freq_mode = 2
        mode_and_flashes(s, 2 * P.FREQ_BLINK_MS + phase, seen)
        push(s)
        assert no_short_mode(mode_and_flashes(s, 1700, seen)) and s.p.freq_mode == 0, phase
    for gap in range(0, 2 * P.LIT_MIN_MS, 9):
        s, seen = Sim(), []
        s.p.freq_mode, s.p.dark = 1, True
        s.run(50)
        s.p.dark = False
        mode_and_flashes(s, gap, seen)
        push(s)
        assert no_short_mode(mode_and_flashes(s, 1700, seen)) and s.p.freq_mode == 2, gap
    for phase in range(0, P.FREQ_BLINK_MS, 9):           # ADF, USB back in any phase of the blink
        s, seen = Sim(), []
        s.p.freq_mode = 2
        s.run(P.FREQ_BLINK_MS + phase)
        s.p.dark = True; s.run(50); s.p.dark = False
        assert no_short_mode(mode_and_flashes(s, 2 * P.FREQ_BLINK_MS, seen)), phase
    for mode in (1, 2):                                  # NAV or ADF, a digit's count dropped by a key any time
        for gap in range(0, 2 * P.FREQ_BLINK_MS, 9):     # after the digit, then a push
            s, seen = Sim(), []
            s.p.freq_mode = mode
            s.run(2 * P.FREQ_BLINK_MS + gap % P.FREQ_BLINK_MS)
            digit(s)                                     # (recorded from here: the light may be on already)
            mode_and_flashes(s, gap % (P.SQUAWK_REST_MS + 50), seen)
            s.p.key("AP", True, s.t); s.p.key("AP", False, s.t + 1)
            mode_and_flashes(s, 2 + gap // 9 % 400, seen)   # (Sim applies a key after the ms's light was read,
            push(s)                                         # code.py before: 1 ms after the drop is no case)
            assert no_short_mode(mode_and_flashes(s, 2000, seen), first=False), (mode, gap)


def test_no_count_while_dark():
    # the lights are off while USB is down: a push then counts nothing, neither then nor once the host is back
    s = Sim()
    s.p.dark = True
    t0 = s.t
    s.key("FREQ_PUSH")
    s.p.dark = False
    assert s.p.freq_mode == 1 and flashes(s.p, t0) == []


def test_a_count_under_way_ends_while_dark():
    # USB drops during a count: nothing of it resumes when the host is back
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0); s.p.key("FREQ_PUSH", False, t0 + 1)   # NAV: 2
    s.run(30)
    s.p.dark = True
    s.run(20)
    s.p.dark = False
    assert s.p.flash[1] == 0 and flashes(s.p, s.t) == []


def test_a_push_at_a_flash_boundary_pauses_after_the_flash_shown():
    # at start + FLASH_EVERY_MS the next flash is not shown yet: the pause runs from the one before
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0); s.p.key("FREQ_PUSH", False, t0 + 1)   # NAV: 2, from t0
    s.t = t0 + EVERY
    s.p.key("FREQ_PUSH", True, s.t); s.p.key("FREQ_PUSH", False, s.t + 1)  # ADF
    assert s.p.flash == (t0 + PAUSE, 3)


def squawk_rest(*then):
    """SHIFT, the outer ring to digit 3, then `then` (Sim calls) within its rest: the flashes from the turn on"""
    s = Sim()
    s.key("SHIFT")
    t0 = s.t
    s.p.turn("FREQ_OUTER", 2, t0)
    for step in then:
        step(s)
    return s, flashes(s.p, t0, 2000)


def test_a_squawk_count_still_to_come_goes_with_its_entry():
    # the entry ends (a key, a SHIFT tap starting a new one, a cancel, another knob) before the ring rested: the
    # digit it selected is not counted, as it no longer is the one the inner ring sets
    for then in ((lambda s: s.key("AP", 20),),
                 (lambda s: s.key("SHIFT", 20),),
                 (lambda s: s.key("SHIFT", 20), lambda s: s.key("SHIFT", 20)),
                 (lambda s: s.turn("ALTHDG_OUTER", 1),),
                 (lambda s: s.key("FMS_PUSH", 20),)):
        s, seen = squawk_rest(*then)
        assert seen == [], then
    s, seen = squawk_rest(lambda s: s.key("SHIFT", 20), lambda s: s.turn("FREQ_INNER", 1))
    assert s.take()[-1:] == [(1, "SQK_D1_UP")] and seen == []                   # the new entry, on digit 1
    s, seen = squawk_rest(lambda s: s.turn("FREQ_INNER", 1))                    # the same entry: counted
    assert seen == [P.SQUAWK_REST_MS + i * EVERY for i in range(3)]


def test_a_freq_push_after_a_squawk_entry_counts_from_its_press():
    # a plain push once a key ended the entry: its count does not wait for the dropped squawk rest
    s = Sim()
    s.key("SHIFT")
    s.p.turn("FREQ_OUTER", 2, s.t)
    s.key("AP", 20)
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0)
    assert s.p.flash == (t0, 2)


def test_a_dropped_squawk_count_keeps_the_pause_after_the_count_before():
    # NAV's count, then a squawk digit put back behind it and dropped by a key: ADF still waits for the pause after
    # NAV's last flash, so the two counts do not read as five
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0); s.p.key("FREQ_PUSH", False, t0 + 1)   # NAV: flashes at t0, t0 + 200
    s.p.key("SHIFT", True, t0 + 270); s.p.key("SHIFT", False, t0 + 280)
    s.p.turn("FREQ_OUTER", 1, t0 + 290)                                  # digit 2, after the pause
    s.p.key("AP", True, t0 + 320)                                          # ends the entry: the digit is dropped
    s.p.key("FREQ_PUSH", True, t0 + 350)                                   # ADF
    assert s.p.flash == (t0 + EVERY + PAUSE, 3)


def test_a_key_read_as_the_squawk_count_is_due_drops_it():
    # a key read in the pass the digit's count is due: code.py has not shown it yet, so the ended entry's digit is
    # not shown at all
    s = Sim()
    s.key("SHIFT")
    t0 = s.t
    s.p.turn("FREQ_OUTER", 1, t0)                                          # digit 2, due at its rest's end
    s.p.key("AP", True, t0 + P.SQUAWK_REST_MS)
    assert s.p.flash[1] == 0


def test_a_squawk_count_arriving_during_a_freq_count_waits_for_a_pause():
    # NAV's count runs when the squawk ring rests: it is cut where it is, and the digit follows after a pause
    s = Sim()
    t0 = s.t
    s.p.key("FREQ_PUSH", True, t0); s.p.key("FREQ_PUSH", False, t0 + 1)   # NAV: 2, from t0
    s.p.key("SHIFT", True, t0 + 100); s.p.key("SHIFT", False, t0 + 110)
    s.p.turn("FREQ_OUTER", 1, t0 + 120)                                  # digit 2, in NAV's first gap
    assert s.p.flash == (t0 + PAUSE, 2)                                  # (not at its rest's end, t0 + 420)
