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
    for t, down in events:
        while s.t < t:
            s.run(1)
            out[s.t] = (button or name) in {s.names[dev][b] for b in s.p.buttons(dev)}
        s.p.key(name, down, s.t)
    for _ in range(after):
        s.run(1)
        out[s.t] = (button or name) in {s.names[dev][b] for b in s.p.buttons(dev)}
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
    # once MAX_QUEUE are owed the rest are dropped, as for knob detents, so the run-on stays bounded
    s = Sim()
    every = P.BOUNCE_MS + 1
    t0 = s.t
    on = key_trace(s, [(every * i, every * i + 1) for i in range(20)], "AP", after=2000)
    started = [a for a, _ in runs(on) if a <= t0 + every * 19]       # shown by the last press
    assert len(runs(on)) == len(started) + P.MAX_QUEUE < 20


def test_second_press_held_waits_for_the_gap_then_stays_held():
    # released after a long press and pressed again BOUNCE_MS later, then held: the release goes out with the
    # new press, which is down again after GAP_MS, and held until its release
    s = Sim()
    t0 = s.t
    on = key_trace(s, [(0, 200), (200 + P.BOUNCE_MS, 600)], "AP")
    second = t0 + 200 + P.BOUNCE_MS + P.GAP_MS
    assert runs(on) == [(t0 + 1, 200 + LATE), (second, 600 - 200 - P.GAP_MS)]   # first tick at t0 + 1


def test_fast_double_push_stays_two_presses():
    # pushes follow the same rule: two quick pushes of the FREQ knob step the mode twice and send two C/V
    s = Sim()
    on = key_trace(s, [(0, 15), (50, 65)], "FREQ_PUSH")
    assert len(runs(on)) == 2 and mobiflight_counts(on) == {2} and s.p.freq_mode_name == "ADF"
    on = key_trace(s, [(0, 15), (50, 65)], "ALTHDG_PUSH", "HDG_SYNC")
    assert len(runs(on)) == 2 and mobiflight_counts(on) == {2}


def test_quick_taps_of_different_keys_do_not_wait():
    # the gap is per button: AP right after VS goes down at once
    s = Sim()
    s.p.key("VS", True, s.t); s.run(10); s.p.key("VS", False, s.t)
    s.p.key("AP", True, s.t); s.run(1)
    assert {s.names[1][b] for b in s.p.buttons(1)} == {"VS", "AP"}


def test_key_state_is_forgotten_after_the_gap():
    s = Sim()
    key_trace(s, [(0, 10), (50, 60)], "AP")
    assert s.p.shown == {}


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
        out.append((s.p.shift_level(s.t), s.p.buttons(1), s.p.buttons(2)))
    return out


def presses(trace, dev, name):
    """the presses of a button in a hold_trace"""
    b = BM.BUTTON[dev][name]
    on = [b in entry[dev] for entry in trace]                # entry: (level, device 1, device 2)
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
    # repeats after it keep their cadence, so a hold let go just after one of them was due sends it too, as a
    # clean hold of the same length does
    clean = [(0, "UP", True), (2000, "UP", False)]
    due = P.REPEAT_DELAY_MS + 2 * P.REPEAT_MS
    late = hold_trace(dropout("UP", due - 5, clean), 2600)
    assert presses(late, 1, "UP") == presses(hold_trace(clean, 2600), 1, "UP")
    for n in (1, 2):                                       # let go n repeats after the delayed one, and later
        for after in range(1, 3 * P.REPEAT_MS, 5):
            clean = [(0, "UP", True), (due + n * P.REPEAT_MS + after, "UP", False)]
            ms = clean[-1][0] + 400
            assert presses(hold_trace(dropout("UP", due - 5, clean), ms), 1, "UP") == \
                presses(hold_trace(clean, ms), 1, "UP"), (n, after)


def test_a_stalled_pass_sends_one_late_repeat():
    # a loop pass stalls while UP is held, past two or more repeats: one repeat for the time missed, then the
    # usual cadence from there, not a burst of the missed ones that would run on after the release. Past one
    # repeat only, the next one keeps its time, due right after the late one
    for late, n in ((P.REPEAT_MS - 1, 2), (P.REPEAT_MS, 1), (2000, 1)):
        s = Sim()
        s.p.key("UP", True, s.t); s.run(1000); s.take()
        s.t = s.p.repeat["UP"][2] + late - 1               # stalled: time passed, no tick() ran
        s.run(P.REPEAT_MS - 1); s.p.key("UP", False, s.t); s.run(1000)
        assert s.take() == [(1, "UP")] * n, late


def test_the_cadence_restarts_at_a_long_stall():
    # after a stall past several repeats, the next repeat is due exactly REPEAT_MS after the late one: held a
    # millisecond less sends only the late one, held to that tick sends the next one too
    for held, n in ((P.REPEAT_MS - 1, 1), (P.REPEAT_MS, 2)):
        s = Sim()
        s.p.key("UP", True, s.t); s.run(1000); s.take()
        s.t = s.p.repeat["UP"][2] + 2049                  # stalled, not a whole number of repeats: no tick() ran
        s.run(1 + held); s.p.key("UP", False, s.t); s.run(1000)
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
    # SHIFT, then the FMS push held 4 s with a one-scan dropout after 1 s: SHIFT stays with the knob until 3 s
    # after the release, as for a clean push (docs/controls.md), and the push sends one CABIN_LT
    clean = [(0, "FMS_PUSH", True), (4000, "FMS_PUSH", False)]
    trace = hold_trace(clean, 7500, shifted=True)
    assert all(level == P.LIGHT_FULL for level, _, _ in trace[:4000 + P.SHIFT_MS - P.SHIFT_WARN_MS])
    assert trace[-1][0] == P.LIGHT_OFF and presses(trace, 1, "CABIN_LT") == 1
    assert hold_trace(dropout("FMS_PUSH", 1000, clean), 7500, shifted=True) == trace


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
    assert len(runs(on)) == 2 and not on[s.t] and s.p.held == {} and s.p.pending == {}
    on = key_trace(s, [(0, 100), (120, 200)], "AP")          # and another bounce after it
    assert len(runs(on)) == 1 and not on[s.t] and s.p.held == {} and s.p.pending == {}


def test_release_is_applied_at_once_when_no_bounce():
    # code.py's resync after a keypad overflow: a release it is sure of goes out at once, and a press right
    # after it is a new press, not a bounce
    s = Sim()
    s.p.key("AP", True, s.t); s.run(100)
    s.p.release("AP", s.t); s.run(1)
    assert s.p.buttons(1) == set()
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
    assert s.p.unit == 2
    key_trace(s, [(0, 5), (25, 60)], "FREQ_PUSH")
    assert s.p.freq_mode_name == "NAV" and [n for _, n in s.take()] == ["FREQ_PUSH"]


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


def test_timing_rules_keep_the_bounce_window_above_a_scan(monkeypatch):
    # a bounce one scan long must fall in the window, with half a scan to spare for a scan held off
    import pytest
    least = P.KEY_SCAN_MS * 3 // 2
    with monkeypatch.context() as m:
        m.setattr(P, "BOUNCE_MS", least)
        P.check_timing()
        m.setattr(P, "BOUNCE_MS", least - 1)
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
    s.t += P.FAST_MS + 1                                     # a pass just longer than FAST_MS is a stall too
    s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_100_UP"] * 2
    s.t += P.FAST_MS                                         # one of FAST_MS is not
    s.p.turn("ALTHDG_OUTER", 2, s.t); s.run(500)
    assert [n for _, n in s.take()] == ["ALT_1000_UP"] * 2


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
    # the same when the stalled pass first reads an input: the release, then a turn of the same knob. Also for a
    # release from code.py's resync after a keypad overflow, which is applied at once
    for resync in (False, True):
        s = Sim()
        s.key("SHIFT"); s.take()
        s.p.key("ALTHDG_PUSH", True, s.t); s.run(100)
        s.t += P.SHIFT_MS + 500                              # stalled: time passed, no tick() ran
        if resync:
            s.p.release("ALTHDG_PUSH", s.t)
        else:
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

