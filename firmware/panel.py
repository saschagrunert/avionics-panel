"""Panel logic of the Avionics Panel rev 1: plain Python, no hardware access, testable on the PC.

code.py feeds it key events, encoder detents and the time in milliseconds, and sends the buttons it
reports. All state (SHIFT, UNIT, frequency mode) lives here and comes out as fixed joystick buttons,
so MobiFlight mappings never need variables or preconditions. See docs/controls.md (SHIFT, Knobs)
and docs/firmware.md.
"""
import buttonmap as BM

SHIFT_MS = 3000          # SHIFT cancels itself, and a shifted knob returns to normal, after this
SHIFT_WARN_MS = 1000     # the amber light pulses for this long before SHIFT drops out ...
SHIFT_PULSE_MS = 125     # ... dim and bright this long each (4 Hz): starts dim, ends bright
LIGHT_OFF, LIGHT_DIM, LIGHT_FULL = 0, 1, 2   # levels of the amber light; code.py maps them to PWM duties
FREQ_RESET_MS = 10000    # frequency knob back to COM after this long without a turn
FAST_MS = 60             # detents closer than this (same ring, same direction) take the coarse step
# MobiFlight polls the joysticks from a 20 ms timer that Windows' 15.6 ms clock stretches to about 31 ms, and
# reads snapshots (nothing buffered): a press and a gap must both outlast one poll, or detents merge or vanish.
PRESS_MS = 50            # one knob detent = a button held this long ...
GAP_MS = 40              # ... then released this long before the next one: 90 ms, about 11 steps per second
MAX_QUEUE = 8            # queued detents per button (fast spins): runs on for at most 8 x 90 = 720 ms
REPEAT_DELAY_MS = 400    # UP / DN: first repeat ...
REPEAT_MS = 125          # ... then about 8 per second
PAN_DELAY_MS = 300       # RANGE tilt: first repeat ...
PAN_MS = 120             # ... then this often
# RANGE tilt switches -> pan direction. Check on the first board and swap here if a direction is off.
PAN_DIRS = {"RANGE_A": "UP", "RANGE_B": "LEFT", "RANGE_C": "DN", "RANGE_D": "RIGHT"}
FREQ_MODES = ("COM", "NAV", "ADF")


def pulse_timing_ok(warn_ms, pulse_ms, shift_ms):
    """The warning must be whole dim/bright pairs, so it starts dim exactly warn_ms before the drop and its
    last phase is bright, and shorter than SHIFT itself, so a fresh SHIFT shows steady before it pulses."""
    return 0 < warn_ms < shift_ms and pulse_ms > 0 and warn_ms % (2 * pulse_ms) == 0


def check_timing():
    """Raises on timing that breaks the rules above (a plain raise: asserts vanish under -O). A held UP / DN or
    tilt must not queue repeats faster than the pulses send them, or they run on after the release."""
    if not pulse_timing_ok(SHIFT_WARN_MS, SHIFT_PULSE_MS, SHIFT_MS):
        raise ValueError("SHIFT_WARN_MS must be below SHIFT_MS and a multiple of 2 * SHIFT_PULSE_MS")
    if min(REPEAT_MS, PAN_MS) < PRESS_MS + GAP_MS:
        raise ValueError("PRESS_MS + GAP_MS must not exceed REPEAT_MS and PAN_MS")


check_timing()


class Panel:
    def __init__(self):
        self.shift = None            # None, "any" (armed by the SHIFT key) or the knob that keeps it
        self.under = None            # with "any": the knob whose held push or tilt keeps its session under it
        self.shift_until = 0
        self.unit = 1
        self.freq_mode = 0
        self.freq_last = 0
        self.held = {}               # source -> (device, button) held while the source is held
        self.repeat = {}             # source -> [device, button, next_ms]
        self.queue = {}              # (device, button) -> queued detents
        self.pulse = {}              # (device, button) -> (down?, until_ms)
        self.last_detent = {}        # ring -> (ms, direction)
        self.ring_keys = {}          # ring -> queue keys its detents went to since its last reversal
        self.holds = {}              # source -> knob: a push or tilt held in that knob's shifted session
        self.last_tick = None        # ms of the last tick(): the previous loop pass
        self.range_dirs = set()
        self.range_com = False       # RANGE "com" closed (any operation closes it)
        self.range_tilted = False    # a direction closed during this "com" press

    # ---------------- helpers ----------------
    def _btn(self, dev, name):
        return dev, BM.BUTTON[dev][name]

    def _unit_dev(self):
        return self.unit

    def _queue(self, dev, name, n=1):
        k = self._btn(dev, name)
        self.queue[k] = min(self.queue.get(k, 0) + n, MAX_QUEUE)
        return k

    def _reverse(self, ring):
        """The ring turned the other way: drop the detents it still has queued in the old direction, so the knob
        stops at once. A pulse already on the way finishes, the PC has seen its press."""
        for k in self.ring_keys.pop(ring, ()):
            if k in self.pulse:
                self.queue[k] = 1
            else:
                self.queue.pop(k, None)

    def shift_active(self, t):
        """Whether SHIFT applies at time t, the one place that decides it: inputs, tick() and the light agree,
        so a late detent after a stalled loop is plain, as the dark light says, and cannot revive the session."""
        return self.shift is not None and t < self.shift_until

    def _expire(self, t):
        """Ends SHIFT once it ran out. A shifted push or tilt still held keeps its session, the 3 s start at its
        release: extended first, so a loop pass that stalled for 3 s or more doesn't end it under the hand."""
        if self._held() is not None:
            self.shift_until = t + SHIFT_MS
        if not self.shift_active(t):
            self.shift = self.under = None

    def _kept(self):
        """The knob whose session SHIFT is: the armed "any" keeps the one a held control was in."""
        return self.under if self.shift == "any" else self.shift

    def _held(self):
        """The knob whose session a shifted push or tilt still held keeps, or None. Keys never end that
        session, SHIFT taps and the key a tap armed included; another knob does (_knob_shift)."""
        knob = self._kept()
        return knob if knob in self.holds.values() else None

    def _knob_shift(self, knob, t):
        """SHIFT for a knob action: armed SHIFT or this knob's own shifted session. Starts/extends it."""
        if self.shift == "any" or self.shift == knob:
            self.shift, self.under = knob, None
            self.shift_until = t + SHIFT_MS
            return True
        self.shift = self.under = None   # another knob ends this session, also one a held push or tilt keeps
        return False

    def shift_level(self, t):
        """Level of the amber light at time t: LIGHT_FULL while SHIFT applies, pulsing between LIGHT_DIM and
        LIGHT_FULL during its last SHIFT_WARN_MS, so a knob never drops back to its plain function
        unannounced in the middle of a turn. Never LIGHT_OFF while SHIFT applies, and LIGHT_OFF from the
        moment SHIFT runs out, whether or not tick() has seen that yet. An int, no float: code.py calls
        this every millisecond."""
        if not self.shift_active(t):
            return LIGHT_OFF
        left = self.shift_until - t
        if left > SHIFT_WARN_MS:
            return LIGHT_FULL
        return LIGHT_FULL if ((left - 1) // SHIFT_PULSE_MS) % 2 == 0 else LIGHT_DIM

    @property
    def unit_light(self):
        return self.unit == 2

    @property
    def freq_mode_name(self):
        return FREQ_MODES[self.freq_mode]

    # ---------------- inputs ----------------
    def key(self, name, pressed, t):
        self._expire(t)
        if name.startswith("RANGE_"):
            return self._range_key(name, pressed, t)
        if name in ("ALTHDG_PUSH", "FMS_PUSH", "FREQ_PUSH"):
            return self._push(name, pressed, t)
        if not pressed:
            self.held.pop(name, None)
            self.repeat.pop(name, None)
            return
        held = self._held()
        if name == "SHIFT":
            if self.shift == "any":                      # a second tap cancels SHIFT, except for a held control
                self.shift, self.under = held, None
            else:                                        # also while a knob still keeps SHIFT: arm for the next key
                self.shift, self.under, self.shift_until = "any", held, t + SHIFT_MS
            return
        shifted = self.shift == "any"
        self.shift, self.under = held, None              # a key ends a knob's session, unless a control holds it
        if name == "HOME" and shifted:                    # UNIT: firmware state, white light
            self.unit = 2 if self.unit == 1 else 1
            return
        dev = self._unit_dev() if name in BM.UNIT_KEYS else 1
        button = BM.shifted(name) if shifted else name
        if name in BM.REPEAT_KEYS:
            self._queue(dev, button)
            self.repeat[name] = [dev, button, t + REPEAT_DELAY_MS, REPEAT_MS]
        else:
            self.held[name] = self._btn(dev, button)

    def _push(self, name, pressed, t):
        if not pressed:
            self.held.pop(name, None)
            self.holds.pop(name, None)
            return
        knob = name[:-5]                                   # ALTHDG, FMS, FREQ
        shifted = self._knob_shift(knob, t)
        if shifted:
            self.holds[name] = knob
        if name == "ALTHDG_PUSH":
            self.held[name] = self._btn(1, "BARO_STD" if shifted else "HDG_SYNC")
        elif name == "FMS_PUSH":
            self.held[name] = self._btn(1, "CABIN_LT") if shifted else self._btn(self._unit_dev(), "FMS_CRSR")
        elif shifted:
            self.held[name] = self._btn(1, "XPDR_MODE")
        else:                                              # FREQ push: next mode, and C/V for GNS / GTN
            self.freq_mode = (self.freq_mode + 1) % len(FREQ_MODES)
            self.freq_last = t
            self.held[name] = self._btn(self._unit_dev(), "FREQ_PUSH")

    def turn(self, ring, steps, t):
        """ring: ALTHDG_OUTER, ALTHDG_INNER, FREQ_OUTER, FREQ_INNER, FMS_OUTER, FMS_INNER or RANGE.
        steps: detents, positive clockwise."""
        self._expire(t)
        if not steps:
            return
        up = steps > 0
        last = self.last_detent.get(ring)
        if last is not None and last[1] != up:
            self._reverse(ring)
        # fast: 2+ detents in one read, or the previous detent on this ring and direction was recent. After a
        # stalled loop pass 2+ detents in one read say nothing about the speed: only the previous detent counts.
        stalled = self.last_tick is not None and t - self.last_tick > FAST_MS
        fast = (abs(steps) > 1 and not stalled) or (last is not None and last[1] == up and t - last[0] < FAST_MS)
        self.last_detent[ring] = (t, up)
        knob = ring.split("_")[0]
        shifted = self._knob_shift(knob, t)
        dev, slow, quick = 1, None, None
        if ring == "ALTHDG_OUTER":
            slow, quick = ("CRS_1", "CRS_10") if shifted else ("ALT_100", "ALT_1000")
        elif ring == "ALTHDG_INNER":
            slow, quick = ("BARO", None) if shifted else ("HDG_1", "HDG_10")
        elif knob == "FREQ" and shifted:
            slow, quick = ("SQK_D2", "SQK_D1") if ring == "FREQ_OUTER" else ("SQK_D4", "SQK_D3")
        elif knob == "FMS" and shifted:                     # lighting: device 1 in every unit, one step per detent
            slow = "PANEL_LT" if ring == "FMS_OUTER" else "FLOOD_LT"
        elif knob == "FREQ":
            dev = self._unit_dev()
            self.freq_last = t
            mode = FREQ_MODES[self.freq_mode]
            if ring == "FREQ_OUTER":
                slow = {"COM": "COM_MHZ", "NAV": "NAV_MHZ", "ADF": "ADF_100"}[mode]
            else:
                slow = {"COM": "COM_KHZ", "NAV": "NAV_KHZ", "ADF": "ADF_1"}[mode]
                quick = "ADF_10" if mode == "ADF" else None
        else:                                               # FMS, RANGE: exactly one step per detent
            dev = self._unit_dev() if knob == "FMS" else 1
            name = ("S_" if shifted else "") + ring + ("_CW" if up else "_CCW")   # shifted: only RANGE gets here
        if slow:
            name = (quick if (fast and quick) else slow) + ("_UP" if up else "_DN")
        self.ring_keys.setdefault(ring, set()).add(self._queue(dev, name, abs(steps)))

    def _range_key(self, name, pressed, t):
        """A tilt closes its direction and "com"; the centre push closes "com" alone. "com" can close well
        before the direction on a slow tilt, so PTR is sent on release, and only if no direction closed. SHIFT is
        decided at the press, as for a push: S_PTR or PTR as the light showed when the centre went down."""
        shifted = name in self.holds                       # the release: was it pressed in a shifted session?
        if not pressed:
            self.holds.pop(name, None)
        elif self._knob_shift("RANGE", t):                 # "com" too
            self.holds[name] = "RANGE"
        if name == "RANGE_COM":
            if pressed:
                self.range_com, self.range_tilted = True, bool(self.range_dirs)
            else:
                if not self.range_tilted and not self.range_dirs:
                    self._queue(1, "S_PTR" if shifted else "PTR")
                self.range_com, self.range_tilted = False, False
            return
        if pressed:
            self.range_dirs.add(name)
            self.range_tilted = True
            button = ("S_PAN_" if name in self.holds else "PAN_") + PAN_DIRS[name]
            self._queue(1, button)
            self.repeat[name] = [1, button, t + PAN_DELAY_MS, PAN_MS]
        else:
            self.range_dirs.discard(name)
            self.repeat.pop(name, None)

    # ---------------- time ----------------
    def tick(self, t):
        self._expire(t)                                    # extends a session held by a push or tilt
        self.last_tick = t
        if self.freq_mode and t - self.freq_last >= FREQ_RESET_MS:
            self.freq_mode = 0
        for src in list(self.repeat):
            r = self.repeat[src]
            dev, button, nxt, every = r
            if src in self.holds and self._kept() != self.holds[src]:
                del self.repeat[src]                       # its shifted session ended, maybe for another knob: stop
                continue
            if t >= nxt:
                self._queue(dev, button)
                r[2] = t + every
        for k in list(self.queue):
            st = self.pulse.get(k)
            if st is None:
                self.pulse[k] = (True, t + PRESS_MS)
            elif t >= st[1]:
                if st[0]:
                    self.pulse[k] = (False, t + GAP_MS)
                else:
                    del self.pulse[k]
                    self.queue[k] -= 1
                    if self.queue[k] <= 0:
                        del self.queue[k]

    def buttons(self, dev):
        """Button numbers currently pressed on one device."""
        out = {b for d, b in self.held.values() if d == dev}
        out |= {b for (d, b), (down, _) in self.pulse.items() if d == dev and down}
        return out
