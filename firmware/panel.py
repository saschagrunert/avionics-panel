"""Panel logic of the Avionics Panel rev 1: plain Python, no hardware access, testable on the PC.

code.py feeds it key events, encoder detents and the time in milliseconds, and sends the buttons it
reports. All state (SHIFT, UNIT, frequency mode) lives here and comes out as fixed joystick buttons,
so MobiFlight mappings never need variables or preconditions. See docs/controls.md (SHIFT, Knobs)
and docs/firmware.md.
"""
import buttonmap as BM

SHIFT_MS = 3000          # SHIFT cancels itself, and a shifted knob returns to normal, after this
FREQ_RESET_MS = 10000    # frequency knob back to COM after this long without a turn
FAST_MS = 60             # detents closer than this (same ring, same direction) take the coarse step
PRESS_MS = 40            # one knob detent = a button held this long ...
GAP_MS = 25              # ... then released this long before the next one
MAX_QUEUE = 12           # queued detents per button (fast spins)
REPEAT_DELAY_MS = 400    # UP / DN: first repeat ...
REPEAT_MS = 125          # ... then about 8 per second
PAN_DELAY_MS = 300       # RANGE tilt: first repeat ...
PAN_MS = 120             # ... then this often
# RANGE tilt switches -> pan direction. Check on the first board and swap here if a direction is off.
PAN_DIRS = {"RANGE_A": "UP", "RANGE_B": "LEFT", "RANGE_C": "DOWN", "RANGE_D": "RIGHT"}
FREQ_MODES = ("COM", "NAV", "ADF")


class Panel:
    def __init__(self):
        self.shift = None            # None, "any" (armed by the SHIFT key) or the knob that keeps it
        self.shift_until = 0
        self.unit = 1
        self.freq_mode = 0
        self.freq_last = 0
        self.held = {}               # source -> (device, button) held while the source is held
        self.repeat = {}             # source -> [device, button, next_ms]
        self.queue = {}              # (device, button) -> queued detents
        self.pulse = {}              # (device, button) -> (down?, until_ms)
        self.last_detent = {}        # ring -> (ms, direction)
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

    def _knob_shift(self, knob, t):
        """SHIFT for a knob action: armed SHIFT or this knob's own shifted session. Starts/extends it."""
        if self.shift == "any" or self.shift == knob:
            self.shift = knob
            self.shift_until = t + SHIFT_MS
            return True
        self.shift = None            # any other action ends another knob's session
        return False

    @property
    def shift_light(self):
        return self.shift is not None

    @property
    def unit_light(self):
        return self.unit == 2

    @property
    def freq_mode_name(self):
        return FREQ_MODES[self.freq_mode]

    # ---------------- inputs ----------------
    def key(self, name, pressed, t):
        if name.startswith("RANGE_"):
            return self._range_key(name, pressed, t)
        if name in ("ALTHDG_PUSH", "FMS_PUSH", "FREQ_PUSH"):
            return self._push(name, pressed, t)
        if not pressed:
            self.held.pop(name, None)
            self.repeat.pop(name, None)
            return
        if name == "SHIFT":
            if self.shift == "any":                      # second tap cancels
                self.shift = None
            else:                                        # also while a knob still keeps SHIFT: arm for the next key
                self.shift, self.shift_until = "any", t + SHIFT_MS
            return
        shifted = self.shift == "any"
        self.shift = None
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
            return
        knob = name[:-5]                                   # ALTHDG, FMS, FREQ
        shifted = self._knob_shift(knob, t)
        if name == "ALTHDG_PUSH":
            self.held[name] = self._btn(1, "BARO_STD" if shifted else "HDG_SYNC")
        elif name == "FMS_PUSH":
            self.held[name] = self._btn(self._unit_dev(), "S_FMS_CRSR" if shifted else "FMS_CRSR")
        elif shifted:
            self.held[name] = self._btn(1, "XPDR_MODE")
        else:                                              # FREQ push: next mode, and C/V for GNS / GTN
            self.freq_mode = (self.freq_mode + 1) % len(FREQ_MODES)
            self.freq_last = t
            self.held[name] = self._btn(self._unit_dev(), "FREQ_PUSH")

    def turn(self, ring, steps, t):
        """ring: ALTHDG_OUTER, ALTHDG_INNER, FREQ_OUTER, FREQ_INNER, FMS_OUTER, FMS_INNER or RANGE.
        steps: detents, positive clockwise."""
        if not steps:
            return
        up = steps > 0
        last = self.last_detent.get(ring)
        # fast: 2+ detents in one read, or the previous detent on this ring and direction was recent
        fast = abs(steps) > 1 or (last is not None and last[1] == up and t - last[0] < FAST_MS)
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
            name = ("S_" if shifted else "") + ring + ("_CW" if up else "_CCW")
            self._queue(dev, name, abs(steps))
            return
        base = quick if (fast and quick) else slow
        self._queue(dev, base + ("_UP" if up else "_DN"), abs(steps))

    def _range_key(self, name, pressed, t):
        """A tilt closes its direction and "com"; the centre push closes "com" alone. "com" can close well
        before the direction on a slow tilt, so PTR is sent on release, and only if no direction closed."""
        if name == "RANGE_COM":
            if pressed:
                self.range_com, self.range_tilted = True, bool(self.range_dirs)
            else:
                if not self.range_tilted and not self.range_dirs:
                    self._queue(1, "S_PTR" if self._knob_shift("RANGE", t) else "PTR")
                self.range_com, self.range_tilted = False, False
            return
        if pressed:
            self.range_dirs.add(name)
            self.range_tilted = True
            button = ("S_PAN_" if self._knob_shift("RANGE", t) else "PAN_") + PAN_DIRS[name]
            self._queue(1, button)
            self.repeat[name] = [1, button, t + PAN_DELAY_MS, PAN_MS]
        else:
            self.range_dirs.discard(name)
            self.repeat.pop(name, None)

    # ---------------- time ----------------
    def tick(self, t):
        if self.shift is not None and t >= self.shift_until:
            self.shift = None
        if self.freq_mode and t - self.freq_last >= FREQ_RESET_MS:
            self.freq_mode = 0
        for r in self.repeat.values():
            dev, button, nxt, every = r
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
