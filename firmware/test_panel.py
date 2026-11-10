"""Host tests for panel.py: run pytest from the repository root."""
import buttonmap as BM
import panel as P


class Sim:
    def __init__(self):
        self.p, self.t, self.seen = P.Panel(), 0, []
        self.prev = {1: set(), 2: set()}
        self.names = {d: {v: k for k, v in BM.BUTTON[d].items()} for d in (1, 2)}

    def run(self, ms):
        """advance time, record every button press edge as (device, name)"""
        names = self.names
        for _ in range(ms):
            self.t += 1
            self.p.tick(self.t)
            for d in (1, 2):
                now = self.p.buttons(d)
                for b in sorted(now - self.prev[d]):
                    self.seen.append((d, names[d][b]))
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
    s.key("SHIFT"); s.run(3100); assert not s.p.shift_active(s.t); s.key("AP"); assert s.take() == [(1, "AP")]
    s.key("SHIFT"); s.turn("FREQ_OUTER", 1); s.take()                   # squawk set, light still on
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
    s.turn("FREQ_OUTER", 2, every=500); s.turn("FREQ_INNER", 1, every=500)   # whole squawk code
    assert [n for _, n in s.take()] == ["SQK_D2_UP", "SQK_D2_UP", "SQK_D4_UP"]
    assert s.p.shift_active(s.t)
    s.run(3000); assert not s.p.shift_active(s.t)
    s.turn("FREQ_OUTER", 1); assert s.take() == [(1, "COM_MHZ_UP")]
    s.key("SHIFT"); s.turn("ALTHDG_INNER", 1); s.key("AP")              # a key after a knob session: normal
    assert [n for _, n in s.take()] == ["BARO_UP", "AP"]


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
    s.key("SHIFT"); s.turn("FREQ_OUTER", 1)              # a knob session: drops 3000 ms after this detent
    check_pulse(light_trace(s, s.p.shift_until))


def test_shift_light_pulses_before_an_armed_shift_drops():
    s = Sim()
    s.key("SHIFT")                                       # armed, no key follows: drops 3000 ms after the tap
    check_pulse(light_trace(s, s.p.shift_until))


def test_pulse_follows_other_timings(monkeypatch):
    monkeypatch.setattr(P, "SHIFT_PULSE_MS", 100)        # 5 dim/bright pairs instead of 4
    s = Sim()
    s.key("SHIFT")
    check_pulse(light_trace(s, s.p.shift_until), pulse=100)


def test_pulse_timing_rules():
    assert P.pulse_timing_ok(1000, 125, 3000) and P.pulse_timing_ok(1000, 100, 3000)
    assert not P.pulse_timing_ok(1000, 150, 3000)       # would start with a bright partial phase
    assert not P.pulse_timing_ok(3000, 125, 3000)       # would pulse for the whole SHIFT


def test_bad_timing_raises(monkeypatch):
    import pytest
    monkeypatch.setattr(P, "SHIFT_PULSE_MS", 150)
    with pytest.raises(ValueError):
        P.check_timing()


def test_light_is_off_once_shift_runs_out_even_before_tick():
    s = Sim()
    s.key("SHIFT")
    end = s.p.shift_until
    assert s.p.shift_level(end - 1) == P.LIGHT_FULL      # still applies: last phase bright
    assert s.p.shift_level(end) == P.LIGHT_OFF and s.p.shift_level(end + 5) == P.LIGHT_OFF


def test_inputs_after_a_stall_follow_the_dark_light():
    # the loop stalls past the end of SHIFT: no tick() ran, but inputs must be plain, as the light says
    s = Sim()
    s.key("SHIFT"); s.turn("FREQ_OUTER", 1); s.take()
    s.t = s.p.shift_until + 30                           # stalled: time passed, no tick() ran
    s.turn("FREQ_OUTER", 1)                              # a late detent: plain, and no new 3 s session
    assert s.take() == [(1, "COM_MHZ_UP")] and not s.p.shift_active(s.t)
    s.key("SHIFT")
    s.t = s.p.shift_until + 30
    s.key("AP")                                          # a late key: plain
    assert s.take() == [(1, "AP")]


def test_acceleration():
    s = Sim()
    s.turn("ALTHDG_OUTER", 3, every=200); assert {n for _, n in s.take()} == {"ALT_100_UP"}
    s.turn("ALTHDG_OUTER", -4, every=30); s.run(1000)                    # fast spin: first detent slow, rest coarse
    names = [n for _, n in s.take()]
    assert len(names) == 4, names
    assert names[0] == "ALT_100_DN" and set(names[1:]) == {"ALT_1000_DN"}, names
    s.turn("FMS_INNER", 5, every=30); s.run(1000)                        # no acceleration on the FMS knob
    assert [n for _, n in s.take()] == ["FMS_INNER_CW"] * 5


def test_fms_knob_with_shift_dims_the_lights():
    s = Sim()
    s.turn("FMS_OUTER", 1); assert s.take() == [(1, "FMS_OUTER_CW")]
    s.key("SHIFT")
    s.turn("FMS_OUTER", 2); s.turn("FMS_INNER", -1); s.key("FMS_PUSH")   # one session: both rings and push
    assert s.take() == [(1, "PANEL_LT_UP"), (1, "PANEL_LT_UP"), (1, "FLOOD_LT_DN"), (1, "CABIN_LT")]
    s.turn("FMS_OUTER", 2, every=30); s.run(200)                          # fast turn: still one step each
    assert s.take() == [(1, "PANEL_LT_UP"), (1, "PANEL_LT_UP")]
    s.run(3000)
    s.key("SHIFT"); s.key("HOME")                                         # unit 2: lighting stays on device 1
    s.key("SHIFT"); s.turn("FMS_INNER", 1); s.key("FMS_PUSH")
    assert s.take() == [(1, "FLOOD_LT_UP"), (1, "CABIN_LT")]
    s.run(3000)
    s.turn("FMS_INNER", 1); s.key("FMS_PUSH")                             # plain FMS knob follows the unit
    assert s.take() == [(2, "FMS_INNER_CW"), (2, "FMS_CRSR")]


def test_unit_and_freq_modes():
    s = Sim()
    s.key("COM_SWAP"); assert s.take() == [(1, "COM_SWAP")]
    s.key("HOME"); assert not s.p.unit_light and s.take() == [(1, "HOME")]   # plain HOME: the GTN key
    s.key("SHIFT"); s.key("HOME"); assert s.p.unit_light and s.take() == []
    s.key("HOME"); assert s.p.unit_light and s.take() == [(2, "HOME")]
    s.key("COM_SWAP"); s.key("AP"); assert s.take() == [(2, "COM_SWAP"), (1, "AP")]
    s.key("FREQ_PUSH"); assert s.p.freq_mode_name == "NAV" and s.take() == [(2, "FREQ_PUSH")]
    s.turn("FREQ_INNER", 1); assert s.take() == [(2, "NAV_KHZ_UP")]
    s.key("FREQ_PUSH"); s.turn("FREQ_INNER", -1); assert s.take() == [(2, "FREQ_PUSH"), (2, "ADF_1_DN")]
    s.run(10100); assert s.p.freq_mode_name == "COM"                    # back to COM after 10 s
    s.key("SHIFT"); s.key("HOME"); assert not s.p.unit_light
    s.key("SHIFT"); s.key("FREQ_PUSH"); assert s.take() == [(1, "XPDR_MODE")] and s.p.freq_mode_name == "COM"


def test_freq_push_restarts_the_mode_timeout():
    # a turn, then the push long after it: the 10 s count from the push, not from the turn
    p = P.Panel()
    p.turn("FREQ_INNER", 1, 0); p.tick(0)
    p.key("FREQ_PUSH", True, 20000); p.tick(20001)
    assert p.freq_mode_name == "NAV"
    p.key("FREQ_PUSH", False, 20050)
    p.tick(20000 + P.FREQ_RESET_MS - 1); assert p.freq_mode_name == "NAV"
    p.tick(20000 + P.FREQ_RESET_MS); assert p.freq_mode_name == "COM"


def test_freq_turns_keep_the_mode():
    # turns keep NAV well past 10 s from the push; COM comes back 10 s after the last turn
    s = Sim()
    s.key("FREQ_PUSH"); s.take()
    s.turn("FREQ_INNER", 4, every=4000)
    assert [n for _, n in s.take()] == ["NAV_KHZ_UP"] * 4
    last = s.t - 4000
    s.run(last + P.FREQ_RESET_MS - 1 - s.t); assert s.p.freq_mode_name == "NAV"
    s.run(1); assert s.p.freq_mode_name == "COM"


def test_adf_inner_ring_accelerates():
    # in ADF mode the inner ring steps 1 kHz, or 10 kHz on a fast turn
    s = Sim()
    s.key("FREQ_PUSH"); s.key("FREQ_PUSH"); s.take()
    assert s.p.freq_mode_name == "ADF"
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
    s.turn("RANGE", -2); assert [n for _, n in s.take()] == ["RANGE_CCW", "RANGE_CCW"]
    s.key("SHIFT"); s.turn("RANGE", 1); assert s.take() == [(1, "S_RANGE_CW")]
    s.key("SHIFT"); s.turn("RANGE", -1); assert s.take() == [(1, "S_RANGE_CCW")]


def test_fast_tilt_closes_direction_and_com_in_one_scan():
    # a quick tilt closes its direction and "com" within one 20 ms keypad scan: the keypad reports them in
    # the same pass, the direction (RANGE_A, key 28) before "com" (key 32), and releases them the same way
    names = sum(BM.MATRIX, ())
    assert names.index("RANGE_A") < names.index("RANGE_COM")
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


def pressed_trace(s, ms, dev=1):
    """{ms: set of button names pressed on dev} for the next ms milliseconds"""
    out = {}
    for _ in range(ms):
        s.run(1)
        out[s.t] = {s.names[dev][b] for b in s.p.buttons(dev)}
    return out


# MobiFlight polls the joysticks from a 20 ms System.Timers.Timer; Windows' 15.6 ms clock makes that about
# every 31 ms. It sees snapshots, so a detent only counts if a poll lands in its press and another in its gap.
POLL_MS = 31.25
# The host fetches the reports every 8 ms (bInterval 8), one IN endpoint for both joysticks: with a report still
# pending and both devices changing in one pass, an edge waits up to three frames.
HID_FRAME_MS = 8


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
    late = 3 * HID_FRAME_MS
    for edges in ("press", "release"):
        # a pulse [a, b) arrives as [a + late, b) or as [a, b + late) (press and gap are longer than late)
        if edges == "press":
            pc = {t: on[t] and on.get(t - late, False) for t in on}
        else:
            pc = {t: on[t] or on.get(t - late, False) for t in on}
        for phase in range(32):
            polls = [t for t in sorted(pc) if (t - phase) % POLL_MS < 1]
            seen = [pc[t] for t in polls]
            presses = sum(b and not a for a, b in zip([False] + seen, seen))
            assert presses == P.MAX_QUEUE, (edges, phase)


def test_timing_rules_keep_repeats_from_piling_up(monkeypatch):
    # a step (press and gap) may be as long as the UP / DN repeat and the tilt repeat, each, but not longer
    import pytest
    P.check_timing()
    step = P.PRESS_MS + P.GAP_MS
    for name in ("REPEAT_MS", "PAN_MS"):
        with monkeypatch.context() as m:
            m.setattr(P, name, step)
            P.check_timing()
            m.setattr(P, name, step - 1)
            with pytest.raises(ValueError):
                P.check_timing()


def test_timing_rules_keep_press_and_gap_above_a_poll(monkeypatch):
    # an edge can reach the PC three 8 ms HID frames late (the joysticks share the endpoint): press and gap must
    # still outlast MobiFlight's poll then. A 50 ms gap can arrive as 26 ms, shorter than the 31.25 ms poll
    import pytest
    assert P.HID_FRAME_MS == HID_FRAME_MS
    least = P.POLL_MS + 3 * HID_FRAME_MS
    for name in ("PRESS_MS", "GAP_MS"):
        with monkeypatch.context() as m:
            m.setattr(P, name, least)
            P.check_timing()
            m.setattr(P, name, least - 1)
            with pytest.raises(ValueError):
                P.check_timing()


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
    # two slow detents (the second still queued), then fast ones: the reversal drops the queued slow step
    # too, not only the coarse ones queued last
    s = Sim()
    for gap in (P.FAST_MS + 5, 5, 5, 5):
        s.p.turn("ALTHDG_OUTER", 1, s.t); s.run(gap)
    assert s.take() == [(1, "ALT_100_UP"), (1, "ALT_1000_UP")]
    assert s.p.queue[s.p._btn(1, "ALT_100_UP")] == 2 and s.p.queue[s.p._btn(1, "ALT_1000_UP")] == 2
    s.p.turn("ALTHDG_OUTER", -1, s.t); s.run(1000)
    assert s.take() == [(1, "ALT_100_DN")]


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


def light_and_edges(s, ms):
    """per ms: (light level, button names newly pressed on device 1)"""
    out = []
    for _ in range(ms):
        n = len(s.seen)
        s.run(1)
        out.append((s.p.shift_level(s.t), [name for _, name in s.seen[n:]]))
    return out


def test_shifted_tilt_held_keeps_the_light():
    # a shifted pan held longer than 3 s: the light stays on while S_PAN repeats, then the usual 3 s
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t)
    held = light_and_edges(s, 5000)
    assert all(level == P.LIGHT_FULL for level, _ in held)
    assert sum(names.count("S_PAN_UP") for _, names in held) > 30
    s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t)
    assert s.p.shift_until == s.t + P.SHIFT_MS
    after = light_and_edges(s, 3100)
    assert all(names == [] for _, names in after)            # no PTR, no more pan
    assert after[-1][0] == P.LIGHT_OFF


def test_shifted_centre_push_held_stays_shifted():
    # SHIFT, then the RANGE centre held for 4 s: the light stays on, and the release sends S_PTR
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t)
    assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, 4000))
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
    # one loop pass stalls for longer than SHIFT_MS while a shifted tilt is held: the session goes on
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(500)
    s.t += P.SHIFT_MS + 500                                  # stalled: time passed, no tick() ran
    held = light_and_edges(s, 1000)
    assert all(level == P.LIGHT_FULL for level, _ in held)
    assert sum(names.count("S_PAN_UP") for _, names in held) >= 5
    s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(200)
    assert s.p.shift_active(s.t)


def test_held_shifted_push_survives_a_stalled_pass():
    # the same when the stalled pass first reads an input: the release, then a turn of the same knob
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("ALTHDG_PUSH", True, s.t); s.run(100)
    s.t += P.SHIFT_MS + 500                                  # stalled: time passed, no tick() ran
    s.p.key("ALTHDG_PUSH", False, s.t)
    assert s.p.shift_active(s.t) and s.p.shift_until == s.t + P.SHIFT_MS
    s.turn("ALTHDG_INNER", 1)
    assert s.take() == [(1, "BARO_STD"), (1, "BARO_UP")]


def test_shifted_push_held_keeps_the_light():
    s = Sim()
    s.key("SHIFT"); s.take()
    s.p.key("ALTHDG_PUSH", True, s.t)
    assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, 4000))
    assert s.take() == [(1, "BARO_STD")]
    s.p.key("ALTHDG_PUSH", False, s.t)
    s.run(3100); assert not s.p.shift_active(s.t)


def test_shift_taps_keep_a_held_shifted_tilt():
    # SHIFT tapped once or twice during a held shifted pan: S_PAN goes on and the light stays on until the
    # release; one tap arms the next key, a second tap cancels only that
    for taps, key in ((1, "TEST"), (2, "AP")):
        s = Sim()
        s.key("SHIFT"); s.take()
        s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(1500)
        for _ in range(taps):
            s.p.key("SHIFT", True, s.t); s.run(30); s.p.key("SHIFT", False, s.t); s.run(30)
        held = light_and_edges(s, 4000)
        assert all(level == P.LIGHT_FULL for level, _ in held)
        assert sum(names.count("S_PAN_UP") for _, names in held) > 30
        s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t); s.run(200)
        assert s.p.shift_active(s.t)
        s.take(); s.key("AP"); assert s.take() == [(1, key)]


def test_shift_taps_keep_a_held_shifted_push():
    for taps in (1, 2):
        s = Sim()
        s.key("SHIFT"); s.take()
        s.p.key("ALTHDG_PUSH", True, s.t); s.run(1500)
        for _ in range(taps):
            s.p.key("SHIFT", True, s.t); s.run(30); s.p.key("SHIFT", False, s.t); s.run(30)
        assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, 4000))
        assert s.take() == [(1, "BARO_STD")]
        s.p.key("ALTHDG_PUSH", False, s.t); s.run(2900); assert s.p.shift_active(s.t)
        s.run(200); assert not s.p.shift_active(s.t)


def tap(s, name):
    s.p.key(name, True, s.t); s.run(30); s.p.key(name, False, s.t); s.run(30)


def hold_shifted_tilt(s):
    s.key("SHIFT"); s.take()
    s.p.key("RANGE_COM", True, s.t); s.p.key("RANGE_A", True, s.t); s.run(1000)


def test_keys_keep_a_held_shifted_tilt():
    # no key ends the session a held tilt keeps: a plain key, a key that a SHIFT tap armed, SHIFT taps. S_PAN
    # and the light go on until the release, then the usual 3 s
    for keys, sent in ((["AP"], ["AP"]), (["SHIFT", "VFR"], ["IDENT"]),
                       (["SHIFT", "VFR", "SHIFT", "SHIFT", "AP"], ["IDENT", "AP"])):
        s = Sim()
        hold_shifted_tilt(s)
        for k in keys:
            tap(s, k)
        held = light_and_edges(s, 4000)
        assert all(level == P.LIGHT_FULL for level, _ in held), keys
        assert sum(names.count("S_PAN_UP") for _, names in held) > 30, keys
        assert [n for _, n in s.take() if n != "S_PAN_UP"] == sent, keys
        s.p.key("RANGE_A", False, s.t); s.p.key("RANGE_COM", False, s.t)
        s.run(2900); assert s.p.shift_active(s.t), keys
        s.run(200); assert not s.p.shift_active(s.t), keys


def test_armed_key_keeps_a_held_shifted_push():
    s = Sim()
    s.key("SHIFT"); s.p.key("ALTHDG_PUSH", True, s.t); s.run(500)
    tap(s, "SHIFT"); tap(s, "VFR")
    assert all(level == P.LIGHT_FULL for level, _ in light_and_edges(s, 4000))
    s.turn("ALTHDG_INNER", 1)                                # still the shifted session: BARO
    assert s.take() == [(1, "BARO_STD"), (1, "IDENT"), (1, "BARO_UP")]


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
    s.key("SHIFT"); s.turn("FREQ_OUTER", 1)
    tap(s, "SHIFT"); tap(s, "SHIFT"); assert s.p.shift_level(s.t) == P.LIGHT_OFF
    s.turn("FREQ_OUTER", 1)
    assert s.take() == [(1, "SQK_D2_UP"), (1, "COM_MHZ_UP")]


def test_a_plain_push_held_does_not_keep_shift():
    # only a push made in a shifted session keeps it: SHIFT and a turn while a plain push is held end the
    # session 3 s after the detent, push still held
    s = Sim()
    s.p.key("ALTHDG_PUSH", True, s.t); s.run(100)
    s.key("SHIFT"); s.turn("ALTHDG_INNER", 1, every=1)
    s.run(P.SHIFT_MS - 100); assert s.p.shift_active(s.t)
    s.run(100); assert not s.p.shift_active(s.t)
    assert s.take() == [(1, "HDG_SYNC"), (1, "BARO_UP")]


def test_shifted_repeat_stops_when_another_knob_takes_shift():
    # SHIFT tapped during a shifted pan, then the FMS knob turned: the arming goes to the FMS knob (lighting),
    # which ends the RANGE session. The light stays on for the FMS knob, but the tilt stops sending S_PAN
    s = Sim()
    hold_shifted_tilt(s)
    tap(s, "SHIFT")
    s.turn("FMS_OUTER", 1, every=1)
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

