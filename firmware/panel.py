"""Panel logic of the Avionics Panel rev 1: plain Python, no hardware access, testable on the PC.

code.py feeds it key events, encoder detents and the time in milliseconds, and sends the buttons it
reports. All state (SHIFT, UNIT, frequency mode) lives here and comes out as fixed joystick buttons,
so MobiFlight mappings never need variables or preconditions. See docs/using/controls.md (SHIFT,
Knobs) and docs/architecture/firmware.md.
"""
import buttonmap as BM

SHIFT_MS = 3000          # SHIFT cancels itself, and a shifted knob returns to normal, after this
SHIFT_PULSE_MS = 125     # before SHIFT drops out the amber light pulses, dim and bright this long each (4 Hz) ...
SHIFT_WARN_MS = 8 * SHIFT_PULSE_MS   # ... for this long: whole pairs, so it starts dim and ends bright
LIGHT_OFF, LIGHT_DIM, LIGHT_FULL = 0, 1, 2   # levels of the amber light; code.py maps them to PWM duties
FAST_MS = 60             # detents closer than this (same ring, same direction) take the coarse step
# Every press and every gap must outlast a MobiFlight poll after losing three HID frames, and the bounce window
# must take a bounce one key scan long, with half a scan to spare (docs/architecture/firmware.md, Knob steps and
# Keys and switch bounce).
POLL_MS = 32             # MobiFlight's poll, 31.25 ms rounded up
HID_FRAME_MS = 8         # the host's report interval
LATE_MS = 3 * HID_FRAME_MS                # 24: an edge may reach the PC this late: three frames
KEY_SCAN_MS = 20         # code.py's keypad scan interval: 20 ticks of 1/1024 s, 19.5 ms
BOUNCE_MS = KEY_SCAN_MS * 3 // 2          # 30: a press this soon after its own release (scan times) is a bounce
PRESS_MS = POLL_MS + LATE_MS              # 56: one knob detent = a button held this long, a key or push at least ...
GAP_MS = PRESS_MS                         # ... then released this long before its next one: about 9 steps a second
MAX_QUEUE = 8            # detents waiting, all rings together, and presses owed per button: a fast spin runs
                         # on, and a key waits behind it, for at most about 8 x 112 = 896 ms
REPEAT_DELAY_MS = 400    # UP / DN: first repeat ...
REPEAT_MS = 125          # ... then about 8 per second
PAN_DELAY_MS = 300       # RANGE tilt: first repeat ...
PAN_MS = 120             # ... then this often (both: no faster than the steps go through, see tick())
# RANGE tilt switches -> pan direction: a tilt away closes A, left B, towards the user C, right D (Alps drawing)
PAN_DIRS = {"RANGE_A": "UP", "RANGE_B": "LEFT", "RANGE_C": "DN", "RANGE_D": "RIGHT"}
# The sources that repeat while held, in a fixed order: repeats due in the same pass queue in it (the second one
# may find the queue full), and CircuitPython's dicts keep no insertion order
REPEAT_SOURCES = tuple(sorted(BM.REPEAT_KEYS + tuple(PAN_DIRS)))
# The FREQ knob's modes, in the order its push cycles them: the outer ring's step, the inner ring's and the inner
# ring's coarse step
FREQ_MODES = (("COM_MHZ", "COM_KHZ", None), ("NAV_MHZ", "NAV_KHZ", None), ("ADF_100", "ADF_1", "ADF_10"))


def _has_value(d, value):
    """value in d.values(), without making the view: tick() asks in every pass"""
    for k in d:
        if d[k] == value:
            return True
    return False


class Panel:
    def __init__(self, solo=False):
        """solo: one button down at a time, for the keyboard mode (keys.py): a press waits until no other button
        is down, so each shortcut goes down with its own modifiers and no other key held"""
        self.solo = solo
        self.dark = False            # code.py sets it while USB is down and the lights are off: SHIFT never
                                     # applies, and a held key or tilt does not repeat
        self.shift = None            # None, "any" (armed by the SHIFT key) or the knob that keeps it
        self.under = None            # with "any": the knob whose held push or tilt keeps its session under it
        self.shift_until = 0
        self.unit = 1
        self.freq_mode = 0           # index into FREQ_MODES: kept until the FREQ push changes it
        self.digit = 1               # squawk digit (1 to 4) the shifted FREQ inner ring steps
        self.held = {}               # source -> (device, button) held while the source is held
        self.pending = {}            # key or push -> scan ms of its release, not applied for BOUNCE_MS
        self.shown = {}              # (device, button) -> [down?, ms of its last edge, presses owed]: every
                                     # button the PC sees down, in its gap or still owed a press
        self.order = []              # the owed presses (shown keys), in the order they came: steps and keys
        self.order_ms = 0            # the head of order waits until then: PRESS_MS after the last press sent
        self.repeat = {}             # source -> [(device, button), next_ms, every_ms]
        self.last_detent = {}        # ring -> (ms, direction)
        self.ring_keys = {}          # ring -> shown keys its detents went to since its last reversal
        self.sessions = {}           # source -> knob: a push or tilt held in that knob's shifted session
        self.last_tick = None        # ms of the last tick(): the previous loop pass
        self.range_dirs = set()
        self.range_tilted = False    # a direction closed during this RANGE "com" press

    # ---------------- helpers ----------------
    def _btn(self, dev, name):
        return dev, BM.BUTTON[dev][name]

    def _owe(self, k, n=1):
        """n more presses of button k, behind everything already in order; at most MAX_QUEUE with the one on
        its way"""
        e = self.shown.get(k)
        if e is None:
            e = self.shown[k] = [False, None, 0]
        while n > 0 and e[2] + (e[1] is not None) < MAX_QUEUE:
            e[2] += 1
            self.order.append(k)
            n -= 1
        return k

    def _hold(self, src, k):
        """A key or push goes down: holds k while src is held, and owes the PC one more press of k"""
        self.held[src] = k
        self._owe(k)

    def _queue(self, k, n=1):
        """n detents or repeats of button k, while fewer than MAX_QUEUE presses wait in order, so nothing waits
        behind them for long. Keys, pushes and the first step of a hold are never dropped (_owe)."""
        return self._owe(k, min(n, MAX_QUEUE - len(self.order)))

    def _reverse(self, ring):
        """The ring turned the other way: drop the detents it still has queued in the old direction, so the knob
        stops at once. Only those at the end of order: a key or another ring queued after them came later, and
        the PC must see them first (ENT confirms the character dialled before it). A pulse already on the way
        finishes, the PC has seen its press."""
        keys = self.ring_keys.pop(ring, ())
        while self.order and self.order[-1] in keys:
            self.shown[self.order.pop()][2] -= 1

    def keep_steps(self):
        """The steps queued so far stay: a ring that turns back later no longer drops them. For where something
        came between that ends a turn: a key or push, which may have changed what the ring does (SHIFT, UNIT,
        the FREQ push), and code.py's wait for a host, in which no step could go out."""
        self.ring_keys.clear()

    def stalled(self, ms):
        """The loop waited ms for the host (code.py: a send that waited, a request to resume), so a report
        reached the PC later than the LATE_MS that PRESS_MS and GAP_MS allow for. Every press and gap the PC is
        being shown starts that much later, so one that begins with that report or after it still outlasts a
        poll for the PC, and the next press keeps its distance; the next repeat of a held key or tilt keeps its
        delay. The end of SHIFT moves as well: the light stayed as it was during the wait, and a key pressed
        then goes out as it showed."""
        for k in self.shown:
            if self.shown[k][1] is not None:
                self.shown[k][1] += ms
        for src in self.repeat:
            self.repeat[src][1] += ms
        self.order_ms += ms
        self.shift_until += ms

    def shift_active(self, t):
        """Whether SHIFT applies at time t, the one place that decides it: inputs, tick() and the light agree,
        so a detent read after SHIFT ran out is plain, also before tick() has seen that, and cannot revive the
        session. Never while dark: the light is off then, and dark means plain."""
        return not self.dark and self.shift is not None and t < self.shift_until

    def _expire(self, t):
        """Ends SHIFT once it ran out. A shifted push or tilt still held keeps its session, the 3 s start at its
        release: extended first, so a loop pass that stalled for 3 s or more doesn't end it under the hand."""
        if self._held_session() is not None:
            self.shift_until = t + SHIFT_MS
        if not self.shift_active(t):
            self.shift = self.under = None

    def _kept(self):
        """The knob whose session SHIFT is: the armed "any" keeps the one a held control was in."""
        return self.under if self.shift == "any" else self.shift

    def _held_session(self):
        """The knob whose session a shifted push or tilt still held keeps, or None. Keys never end that
        session, SHIFT taps and the key a tap armed included; another knob does (_knob_shift). A release still
        waiting out BOUNCE_MS counts as held: it may be a bounce (docs/architecture/firmware.md)."""
        knob = self._kept()
        return knob if _has_value(self.sessions, knob) else None

    def _knob_shift(self, knob, t):
        """SHIFT for a knob action: armed SHIFT or this knob's own shifted session. Starts/extends it."""
        if self.shift == "any" and self.under != knob:     # not the session a held push of this knob keeps:
            self.digit = 1                                 # a new one, the squawk entry starts at digit 1
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

    # ---------------- inputs ----------------
    def key(self, name, pressed, t, at=None):
        """A key or push went down or up; at: the ms the keypad scanned it (default t), for BOUNCE_MS. A release
        waits in self.pending until tick() applies it BOUNCE_MS after its scan; a new press of the same key
        before that was a bounce and ends the wait, so a run of bounces is one press, held throughout."""
        self._expire(t)
        if at is None:
            at = t
        if not pressed:
            self.pending[name] = at
            return
        last = self.pending.pop(name, None)
        if last is not None:
            if at - last < BOUNCE_MS:
                return                                     # a bounce: the press goes on
            self._apply(name, False, t)                    # the release was real, tick() hasn't seen it yet
        self._apply(name, True, t)

    def release(self, name, t):
        """A release that is no bounce (code.py lets go of every key after a keypad overflow): applied at once,
        and a press right after it is a new press."""
        self._expire(t)
        self._apply(name, False, t)

    def _apply(self, name, pressed, t):
        if pressed:
            self.keep_steps()
        if name.startswith("RANGE_"):
            return self._range_key(name, pressed, t)
        if name in ("ALTHDG_PUSH", "FMS_PUSH", "FREQ_PUSH"):
            return self._push(name, pressed, t)
        if not pressed:
            self.held.pop(name, None)
            self.repeat.pop(name, None)
            return
        held = self._held_session()
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
        k = self._btn(self.unit if name in BM.UNIT_KEYS else 1, BM.shifted(name) if shifted else name)
        if name in BM.REPEAT_KEYS:
            self._owe(k)
            self.repeat[name] = [k, t + REPEAT_DELAY_MS, REPEAT_MS]
        else:
            self._hold(name, k)

    def _push(self, name, pressed, t):
        if not pressed:
            self.held.pop(name, None)
            self.sessions.pop(name, None)
            return
        knob = name[:-5]                                   # ALTHDG, FMS, FREQ
        shifted = self._knob_shift(knob, t)
        if shifted:
            self.sessions[name] = knob
        if name == "ALTHDG_PUSH":
            k = self._btn(1, "BARO_STD" if shifted else "HDG_SYNC")
        elif name == "FMS_PUSH":
            k = self._btn(1, "CABIN_LT") if shifted else self._btn(self.unit, "FMS_CRSR")
        elif shifted:
            k = self._btn(1, "XPDR_MODE")
        else:                                              # FREQ push: next mode
            self.freq_mode = (self.freq_mode + 1) % len(FREQ_MODES)
            k = self._btn(self.unit, "FREQ_PUSH")
        self._hold(name, k)

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
        since = t - last[0] if last is not None and last[1] == up else None    # ms since this turn's last detent
        fast = (abs(steps) > 1 and not stalled) or (since is not None and since < FAST_MS)
        self.last_detent[ring] = (t, up)
        knob = ring.split("_")[0]
        shifted = self._knob_shift(knob, t)
        dev, slow, quick = 1, None, None
        if ring == "ALTHDG_OUTER":
            slow, quick = ("BARO", None) if shifted else ("ALT_100", "ALT_1000")
        elif ring == "ALTHDG_INNER":
            slow, quick = ("CRS_1", "CRS_10") if shifted else ("HDG_1", "HDG_10")
        elif knob == "FREQ" and shifted:                    # squawk: one digit, one step per detent
            if ring == "FREQ_OUTER":                        # selects the digit, stops at 1 and 4, sends nothing
                digit = min(max(self.digit + steps, 1), 4)
                if digit != self.digit:
                    self.digit = digit
                    # The inner ring's queued steps stay with their digit: its next reversal lets them finish
                    # there, also after the selection has come back to that digit before they are sent.
                    self.ring_keys.pop("FREQ_INNER", None)
                return
            slow = "SQK_D" + str(self.digit)
        elif knob == "FMS" and shifted:                     # lighting: device 1 in every unit, one step per detent
            slow = "PANEL_LT" if ring == "FMS_OUTER" else "FLOOD_LT"
        elif knob == "FREQ":
            dev = self.unit
            outer, slow, quick = FREQ_MODES[self.freq_mode]
            if ring == "FREQ_OUTER":
                slow, quick = outer, None
        else:                                               # FMS, RANGE: exactly one step per detent
            dev = self.unit if knob == "FMS" else 1
            name = ("S_" if shifted else "") + ring + ("_CW" if up else "_CCW")   # shifted: only RANGE gets here
        if slow:
            way = "_UP" if up else "_DN"
            # Turned faster than its steps go out, a knob with a coarse step takes it while a fine step still
            # waits: the two buttons share the turn, so the knob stops with the hand. Fine steps that only wait
            # behind other buttons don't count: a slow turn stays fine.
            lagging = since is not None and since < PRESS_MS + GAP_MS
            if quick and (fast or (lagging and self.shown.get(self._btn(dev, slow + way), (0, 0, 0))[2])):
                slow = quick
            name = slow + way
        keys = self.ring_keys.get(ring)
        if keys is None:
            keys = self.ring_keys[ring] = set()
        keys.add(self._queue(self._btn(dev, name), abs(steps)))

    def _range_key(self, name, pressed, t):
        """A tilt closes its direction and "com"; the centre push closes "com" alone. "com" can close well
        before the direction on a slow tilt, so PTR is sent on release, and only if no direction closed. SHIFT is
        decided at the press, as for a push: S_PTR or PTR as the light showed when the centre went down."""
        shifted = name in self.sessions                    # the release: was it pressed in a shifted session?
        if not pressed:
            self.sessions.pop(name, None)
        elif self._knob_shift("RANGE", t):                 # "com" too
            self.sessions[name] = "RANGE"
        if name == "RANGE_COM":
            if pressed:
                self.range_tilted = bool(self.range_dirs)
            else:
                if not self.range_tilted:                  # set while a direction is closed, too
                    self._owe(self._btn(1, "S_PTR" if shifted else "PTR"))
                self.range_tilted = False
            return
        if pressed:
            self.range_dirs.add(name)
            self.range_tilted = True
            k = self._btn(1, ("S_PAN_" if name in self.sessions else "PAN_") + PAN_DIRS[name])
            self._owe(k)
            self.repeat[name] = [k, t + PAN_DELAY_MS, PAN_MS]
        else:
            self.range_dirs.discard(name)
            self.repeat.pop(name, None)

    # ---------------- time ----------------
    def tick(self, t):
        self._expire(t)                                    # extends a session held by a push or tilt
        self.last_tick = t
        if self.pending:
            for name in list(self.pending):                # a copy: applying a release ends its entry
                if t - self.pending[name] >= BOUNCE_MS:
                    del self.pending[name]
                    self._apply(name, False, t)
        if self.repeat and not self.dark:                  # no repeats for a host that is away: they would wake
            self._repeat(t)                                # it; one missed comes once it is back
        self._show(t)
        if self.order and t >= self.order_ms:
            self._next(t)

    def _repeat(self, t):
        for src in REPEAT_SOURCES:
            r = self.repeat.get(src)
            if r is None:
                continue
            if src in self.sessions and self._kept() != self.sessions[src]:
                del self.repeat[src]                       # its shifted session ended, maybe for another knob: stop
                continue
            if src in self.pending:                        # released, maybe: a repeat due now waits for a bounce
                continue
            # A repeat waits until the last step of its button is through (press and gap), so at any pass time a
            # hold sends nothing after its release but its step in order or on the way. Held back by that, a
            # bounce or a slow pass: keep the cadence, but send a missed repeat once, not in a burst
            k, due, every = r
            if t >= due and k not in self.shown:
                self._queue(k)
                r[1] = due + every if t - due < every else t + every

    def _next(self, t):
        """Presses the head of order PRESS_MS after the last press it sent, so MobiFlight has seen that one first
        (another button may go down in its gap), and once the head's own last press and gap are over; solo, also
        once no button is down (a held key holds the next one back)."""
        e = self.shown[self.order[0]]
        down, since, owed = e
        if down or (since is not None and t - since < GAP_MS) or (self.solo and self.pressed() is not None):
            return
        self.order.pop(0)
        e[0], e[1], e[2] = True, t, owed - 1
        self.order_ms = t + PRESS_MS

    def _show(self, t):
        """Releases a press once it was down PRESS_MS and its source let go (at once with another press owed:
        a fast double tap), and forgets a button once its gap is over and nothing is owed"""
        if not self.shown:                                 # nothing pressed lately: skip the work below
            return
        done = None                                        # a list only when an entry goes (no copy per tick)
        for k in self.shown:                               # no items() or values() view left on the heap per tick
            e = self.shown[k]
            down, since, owed = e
            if down:
                if t - since >= PRESS_MS and (owed or not _has_value(self.held, k)):
                    e[0], e[1] = False, t
            elif not owed and (since is None or t - since >= GAP_MS):
                if done is None:
                    done = [k]
                else:
                    done.append(k)
        if done:
            for k in done:
                del self.shown[k]

    def buttons(self, dev):
        """Button numbers currently pressed on one device (for tests on the PC: code.py uses fill_report)"""
        return {b for (d, b), e in self.shown.items() if d == dev and e[0]}

    def pressed(self):
        """A (device, button) pressed now, or None; solo keeps it to one (no set or view: called every pass)"""
        for k in self.shown:
            if self.shown[k][0]:
                return k
        return None

    def fill_report(self, dev, report):
        """One device's HID report, in place: a bit per button, set while it is pressed (no set or view: code.py
        calls this for both devices in every pass)"""
        for i in range(len(report)):
            report[i] = 0
        for k in self.shown:
            if k[0] == dev and self.shown[k][0]:
                report[k[1] >> 3] |= 1 << (k[1] & 7)
