"""Host tests for panel.py: python3 test_panel.py"""
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
    s.key("SHIFT"); s.key("HOME"); assert s.p.unit_light and s.take() == []
    s.key("COM_SWAP"); s.key("AP"); assert s.take() == [(2, "COM_SWAP"), (1, "AP")]
    s.key("FREQ_PUSH"); assert s.p.freq_mode_name == "NAV" and s.take() == [(2, "FREQ_PUSH")]
    s.turn("FREQ_INNER", 1); assert s.take() == [(2, "NAV_KHZ_UP")]
    s.key("FREQ_PUSH"); s.turn("FREQ_INNER", -1); assert s.take() == [(2, "FREQ_PUSH"), (2, "ADF_1_DN")]
    s.run(10100); assert s.p.freq_mode_name == "COM"                    # back to COM after 10 s
    s.key("SHIFT"); s.key("HOME"); assert not s.p.unit_light
    s.key("SHIFT"); s.key("FREQ_PUSH"); assert s.take() == [(1, "XPDR_MODE")] and s.p.freq_mode_name == "COM"


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


def test_up_dn_repeat():
    s = Sim()
    s.p.key("DN", True, s.t); s.run(1000); s.p.key("DN", False, s.t); s.run(300)
    n = len(s.take())
    assert 4 <= n <= 7, n                    # 1 at once, then from 400 ms about 8 per second


def test_counts():
    assert len(BM.DEVICE[1]) == 122 and len(BM.DEVICE[2]) == 44
    assert BM.DEVICE[1][-5:] == BM.LIGHTING                          # added at the end: no number moved
    assert BM.BUTTON[1]["IDENT"] == 16 and BM.BUTTON[1]["VFR"] == 33  # swapped on the key, not in number
    for name in sum(BM.MATRIX, ()):
        assert name in ("SHIFT", "RANGE_A", "RANGE_B", "RANGE_C", "RANGE_D", "RANGE_COM", "ALTHDG_PUSH",
                        "FMS_PUSH") or name in BM.BUTTON[1], name


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
