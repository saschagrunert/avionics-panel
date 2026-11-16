"""Panel logic of the Avionics Panel rev 1: plain Python, no hardware access, testable on the PC.

code.py feeds it key events, encoder detents and the time in milliseconds, and sends the buttons it
reports. All state (SHIFT, UNIT, frequency mode) lives here and comes out as fixed joystick buttons,
so MobiFlight mappings never need variables or preconditions. See docs/using/controls.md (SHIFT,
Knobs) and docs/architecture/firmware.md.
"""
import buttonmap as BM

ARM_MS = 3000            # a SHIFT tap arms the next key this long: a stray tap does not linger
SESSION_MS = 5000        # a shifted knob returns to normal this long after its last detent (or a held push or
                         # tilt's release): room to read a clearance between two squawk digits
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
LOCK_MS = 1000           # SHIFT held this long locks it: every key and knob shifted until a SHIFT tap
LOCK_BLINK_MS = 500      # while locked the amber light blinks dim and bright this long each, never dark
TAP_GAP_MS = 2 * BOUNCE_MS                # 60: a finger lifts and comes back no sooner (a press sooner is chatter)
PRESS_MS = POLL_MS + LATE_MS              # 56: one knob detent = a button held this long, a key or push at least ...
GAP_MS = PRESS_MS                         # ... then released this long before its next one: about 9 steps a second
MAX_QUEUE = 8            # presses waiting, all rings and keys together, beyond which a detent or repeat is
                         # dropped; and presses per button, the one the PC is being shown (down or in its gap)
                         # included: a fast spin runs on, and a key waits behind it, for at most about
                         # 8 x 112 = 896 ms
REPEAT_DELAY_MS = 400    # UP / DN: first repeat ...
REPEAT_MS = 125          # ... then about 8 per second
PAN_DELAY_MS = 300       # RANGE tilt: first repeat ...
PAN_MS = 120             # ... then this often (both: no faster than the steps go through, see tick())
FREQ_HOLD_MS = 1000      # a plain FREQ push held this long returns the knob to COM
# The green FREQ light shows the FREQ knob's mode: off COM, on NAV, a slow blink ADF. It also counts what it tells,
# in n short flashes on a dark light, the mode back after a pause: after a FREQ push its new mode (1 COM, 2 NAV,
# 3 ADF, also when a hold returns to COM) and for the squawk's outer ring its digit (1 to 4). Short enough to read
# as blips, not as the mode. A new count takes the old one's place, after a pause clearly longer than the gaps
# inside a count, so two never run together into a wrong number; the mode shows again after the same pause, and
# a count's first flash waits it after the mode's light, so the light being on never runs into a flash.
FREQ_BLINK_MS = 1000     # ADF: dark, then lit, half of this each, dark first after a count
FLASH_MS = 60            # each flash ...
FLASH_EVERY_MS = 200     # ... starts this long after the one before: 3 flashes take 460 ms
FLASH_PAUSE_MS = 2 * FLASH_EVERY_MS   # from a count's last flash shown to the first of the next
LIT_MIN_MS = 300         # once the mode shows lit, a count darkens it no sooner: five flashes long and more than
                         # FLASH_EVERY_MS, so a lit stretch cut short never reads as a flash of the count after it
SQUAWK_REST_MS = 300     # the squawk digit is counted once its ring has rested this long: a spin shows only the last
# RANGE tilt switches -> pan direction: a tilt away closes A, left B, towards the user C, right D (Alps drawing)
PAN_DIRS = {"RANGE_A": "UP", "RANGE_B": "LEFT", "RANGE_C": "DN", "RANGE_D": "RIGHT"}
# The sources that repeat while held, in a fixed order: repeats due in the same pass queue in it (the second one
# may find the queue full), and CircuitPython's dicts keep no insertion order
REPEAT_SOURCES = tuple(sorted(BM.REPEAT_KEYS + tuple(PAN_DIRS)))
# The FREQ knob's modes, in the order its push cycles them: the outer ring's step, the inner ring's and the inner
# ring's coarse step
FREQ_MODES = (("COM_MHZ", "COM_KHZ", None), ("NAV_MHZ", "NAV_KHZ", None), ("ADF_100", "ADF_1", "ADF_10"))
SQUAWK = (None, "SQK_D1", "SQK_D2", "SQK_D3", "SQK_D4")   # the shifted FREQ inner ring's function, by digit
RINGS = ("ALTHDG_OUTER", "ALTHDG_INNER", "FREQ_OUTER", "FREQ_INNER", "FMS_OUTER", "FMS_INNER", "RANGE")
PUSHES = ("ALTHDG_PUSH", "FMS_PUSH", "FREQ_PUSH")
# Made once, so a detent or push builds no strings (a fast spin then leaves less for the collector, whose pauses
# would hold steps up): each ring's and push's knob, and each step function's buttons, the up or clockwise step
# and the down or counter-clockwise one
KNOB = {n: n.split("_")[0] for n in RINGS + PUSHES}


def _steps():
    up, dn = {}, {}
    ups = ("ALT_100", "ALT_1000", "HDG_1", "HDG_10", "CRS_1", "CRS_10", "BARO", "PANEL_LT", "FLOOD_LT")
    for f in ups + SQUAWK[1:] + tuple(f for mode in FREQ_MODES for f in mode if f):
        up[f], dn[f] = f + "_UP", f + "_DN"
    for f in ("FMS_OUTER", "FMS_INNER", "RANGE", "S_RANGE"):
        up[f], dn[f] = f + "_CW", f + "_CCW"
    return up, dn


STEP_UP, STEP_DN = _steps()


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
        self.arm_until = 0           # a tap's "any" ends then, also while a held control keeps SHIFT on
        self.locked = False          # SHIFT locked by a hold: every key and knob shifted, until a SHIFT tap
        self.locked_at = 0           # ms the lock began: the blink's phase
        self.shift_down = None       # scan ms of the SHIFT press still down, until its release is applied, while
                                     # nothing else was used: it may lock, and a lock it made can still be undone
        self.lock_open = False       # the lock came from the SHIFT press still down: other input takes it back
        self.used_up = False         # input scanned after SHIFT's release, still pending: modifier use if that
                                     # release turns out a bounce
        self.lock_left = None        # scan ms of the release that ended the locking press: chatter after it
        self.unit = 1
        self.freq_mode = 0           # index into FREQ_MODES: kept until the FREQ push changes it
        self.freq_since = None       # ms of the press of a plain FREQ push held, until FREQ_HOLD_MS set COM
        self.digit = 1               # squawk digit (1 to 4) the shifted FREQ inner ring steps
        self.flash = (0, 0)          # the FREQ light's count: (ms of its first flash, flashes)
        self.flash_squawk = False    # it is a squawk digit's: dropped while still to come if the entry ends
        self.flash_free = 0          # no count starts before: FLASH_PAUSE_MS after the last flash shown
        self.lit_at = -FLASH_PAUSE_MS - 1   # nor before FLASH_PAUSE_MS after this: the last ms the light showed
                                            # its mode lit (NAV, ADF's lit half) when a count was due, or keeps it
                                            # lit to make LIT_MIN_MS (_saw_lit)
        self.held = {}               # source -> (device, button) held while the source is held
        self.pending = {}            # key or push -> scan ms of its release, not applied for BOUNCE_MS
        self.shown = {}              # (device, button) -> [down?, ms of its last edge, presses owed]: every
                                     # button the PC sees down, in its gap or still owed a press
        self.order = []              # the owed presses (shown keys), in the order they came: steps and keys
        self.order_ms = 0            # the head of order waits until then: PRESS_MS after the last press sent
        self.repeat = {}             # source -> [(device, button), next_ms, every_ms]
        self.last_detent = {}        # ring -> (ms, direction)
        self.ring_keys = {}          # ring -> {shown key: presses its detents queued there since its last
                                     # reversal or keep_steps()}
        self.session = 0             # number of the latest shifted knob session: a new one starts at 1 more
        self.sessions = {}           # source -> number of the shifted session a held push or tilt was pressed
                                     # in: it keeps that session, and no later one of its knob, while held
        self.last_tick = None        # ms of the last tick(): the previous loop pass
        self.range_dirs = set()
        self.range_tilted = False    # a direction closed during this RANGE "com" press

    # ---------------- helpers ----------------
    def _btn(self, dev, name):
        return dev, BM.BUTTON[dev][name]

    def _owe(self, k, n=1):
        """n more presses of button k, behind everything already in order; at most MAX_QUEUE with the one on
        its way, down or in its gap (so the last ends its gap within MAX_QUEUE steps). Returns how many it
        queued."""
        e = self.shown.get(k)
        if e is None:
            e = self.shown[k] = [False, None, 0]
        added = 0
        while added < n and e[2] + (e[1] is not None) < MAX_QUEUE:
            e[2] += 1
            self.order.append(k)
            added += 1
        return added

    def _hold(self, src, k):
        """A key or push goes down: holds k while src is held, and owes the PC one more press of k"""
        self.held[src] = k
        self._owe(k)

    def _queue(self, k, n=1):
        """n detents or repeats of button k, while fewer than MAX_QUEUE presses wait in order, keys included, so
        nothing waits behind them for long. Keys, pushes and the first step of a hold are never dropped for that
        (_owe)."""
        return self._owe(k, min(n, MAX_QUEUE - len(self.order)))

    def _reverse(self, ring):
        """The ring turned the other way: drop the detents it still has queued in the old direction, so the knob
        stops at once. Only those at the end of order: a key or another ring queued after them came later, and
        the PC must see them first (ENT confirms the character dialled before it). And only as many as the ring
        queued since keep_steps(): the same button's steps from before stay. A pulse already on the way
        finishes, the PC has seen its press."""
        keys = self.ring_keys.pop(ring, None)
        if keys is None:
            return
        while self.order and keys.get(self.order[-1], 0):
            k = self.order.pop()
            keys[k] -= 1
            self.shown[k][2] -= 1

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
        self.arm_until += ms
        self.locked_at += ms
        self.flash = (self.flash[0] + ms, self.flash[1])   # the count, as the light stayed during the wait
        self.flash_free += ms
        self.lit_at += ms

    def shift_active(self, t):
        """Whether SHIFT applies at time t, the one place that decides it: inputs, tick() and the light agree,
        so a detent read after SHIFT ran out is plain, also before tick() has seen that, and cannot revive the
        session. Never while dark: the light is off then, and dark means plain. Always while locked."""
        return not self.dark and (self.locked or self.shift is not None and t < self.shift_until)

    def _expire(self, t, scan=None):
        """Ends SHIFT once it ran out. A tap's armed SHIFT ends ARM_MS after the tap, also while a shifted push
        or tilt is held: SHIFT then goes back to that control's session. A shifted push or tilt still held keeps
        its session, its SESSION_MS start at its release: extended first, so a loop pass that stalled that long
        doesn't end it under the hand. SHIFT held LOCK_MS alone locks it, judged at scan, the scan time of the
        event being read (key() reads them in scan order, so SHIFT was down until then at least), else at t;
        _used() takes it back while the press is still down. Dark ends the lock. Under the lock a knob's session
        has no time limit: the light cannot warn of its end, so only a key, a SHIFT tap or another knob ends it."""
        if self.dark:
            self.locked, self.lock_open, self.shift_down = False, False, None
        elif (self.shift_down is not None and not self.locked
              and self.pending.get("SHIFT", t if scan is None else scan) - self.shift_down >= LOCK_MS):
            self.locked, self.locked_at, self.lock_open = True, t, True      # (a release waiting out BOUNCE_MS
            if self.shift == "any":                                          # ends the hold at its scan)
                self.shift, self.under = self.under, None                    # the lock replaces the arm
        if self.shift == "any" and t >= self.arm_until:
            self.shift, self.under = self.under, None
        if self._held_session() is not None:
            self.shift_until = t + SESSION_MS
        if not self.shift_active(t):                       # (never while locked: no time limit)
            self.shift = self.under = None

    def _used(self, t, scan=None):
        """A key, push or tilt scanned at scan, or a detent (no scan): with SHIFT still down SHIFT is a modifier,
        so its press locks not, and a lock it made goes back to the arm of a tap, which this input takes: it
        goes out shifted. Still down: its release not applied yet, and this input scanned before that release; a
        detent has no scan time, so one read before SHIFT's release is applied (BOUNCE_MS after its scan) counts.
        A key, push or tilt scanned at or after the release counts only if the release turns out a bounce
        (used_up, key()): SHIFT was down throughout then."""
        if self.shift_down is None:
            return
        if scan is not None and self.pending.get("SHIFT", scan + 1) <= scan:
            self.used_up = True
            return
        self.shift_down = None
        if self.lock_open:
            held = self._held_session()
            self.locked = self.lock_open = False
            self.shift, self.under, self.shift_until = "any", held, t + ARM_MS
            self.arm_until = self.shift_until

    def _kept(self):
        """The knob whose session SHIFT is: the armed "any" keeps the one a held control was in."""
        return self.under if self.shift == "any" else self.shift

    def _held_session(self):
        """The knob whose session a shifted push or tilt still held keeps, or None. Keys never end that
        session, SHIFT taps and the key a tap armed included; another knob does (_knob_shift), and so does
        dark. A release still waiting out BOUNCE_MS counts as held: it may be a bounce
        (docs/architecture/firmware.md)."""
        knob = self._kept()
        return knob if knob is not None and _has_value(self.sessions, self.session) else None

    def _in_session(self, src):
        """Whether src is a push or tilt held in the shifted session that goes on now"""
        return self.sessions.get(src) == self.session and self._kept() is not None

    def _knob_shift(self, knob, t):
        """SHIFT for a knob action: armed SHIFT, the lock or this knob's own shifted session. Starts/extends it."""
        if self.locked and self.shift != knob:             # locked: any knob is shifted, a new session as after a
            self._drop_squawk(t)                           # tap
            self.shift, self.under = "any", None
        if self.shift == "any" and self.under != knob:     # not the session a held push of this knob keeps:
            self.digit = 1                                 # a new one, the squawk entry starts at digit 1, and
            self.session += 1                              # a control held from an ended one keeps it not
        if self.shift == "any" or self.shift == knob:
            self.shift, self.under = knob, None
            self.shift_until = t + SESSION_MS
            return True
        self.shift = self.under = None   # another knob ends this session, also one a held push or tilt keeps
        self._drop_squawk(t)             # (a squawk digit's count is the FREQ session's: a SHIFT tap dropped it)
        return False

    def shift_level(self, t):
        """Level of the amber light at time t: LIGHT_FULL while SHIFT applies, pulsing between LIGHT_DIM and
        LIGHT_FULL during its last SHIFT_WARN_MS (while locked it blinks LIGHT_DIM and LIGHT_FULL, LOCK_BLINK_MS
        each, starting dim), so a knob never drops back to its plain function
        unannounced in the middle of a turn. Never LIGHT_OFF while SHIFT applies, and LIGHT_OFF from the
        moment SHIFT runs out, whether or not tick() has seen that yet. An int, no float: code.py calls
        this every millisecond."""
        if not self.shift_active(t):
            return LIGHT_OFF
        if self.locked:                                    # starts dim, so the lock shows at once
            return LIGHT_DIM if ((t - self.locked_at) // LOCK_BLINK_MS) % 2 == 0 else LIGHT_FULL
        left = self.shift_until - t
        if left > SHIFT_WARN_MS:
            return LIGHT_FULL
        return LIGHT_FULL if ((left - 1) // SHIFT_PULSE_MS) % 2 == 0 else LIGHT_DIM

    @property
    def unit_light(self):
        """Whether the unit is 2, as the UNIT light shows it"""
        return self.unit == 2

    def _mode_from(self):
        """Where the light shows its mode again after the last count: FLASH_PAUSE_MS after its last flash (ADF's
        blink counts from there), and not in the pause of one cut short or dropped (flash_free)"""
        start, n = self.flash
        base = start + ((n - 1) * FLASH_EVERY_MS + FLASH_MS + FLASH_PAUSE_MS if n else 0)
        return base, max(base, self.flash_free)

    def freq_lit(self, t):
        """The FREQ light at time t: off COM, on NAV, ADF's slow blink. While a count is still to come, and from
        its start until the mode shows again (_mode_from), the light shows the count's flashes on a dark light
        instead; ADF's blink starts dark after it. A mode lit when a count came stays lit until lit_at, to make
        LIT_MIN_MS. Ints alone, no float: code.py calls this every millisecond."""
        if self.lit_at - LIT_MIN_MS < t <= self.lit_at:  # (the lit stretch that ends at lit_at is that long)
            return True
        base, shown = self._mode_from()
        if t < shown:
            since, n = t - self.flash[0], self.flash[1]
            return 0 <= since < n * FLASH_EVERY_MS and since % FLASH_EVERY_MS < FLASH_MS
        if self.freq_mode == 2:
            return (t - base) % FREQ_BLINK_MS >= FREQ_BLINK_MS // 2
        return self.freq_mode == 1

    def _saw_lit(self, t):
        """Before a change that makes a count at t: keeps in lit_at the last ms before t that the light showed its
        mode lit (NAV, ADF's lit half; a count's own flashes keep their pause by flash_free), so that the count's
        first flash waits FLASH_PAUSE_MS after it, also when a later count takes its place or the mode changes. A
        mode lit now stays lit until LIT_MIN_MS after it came on: lit_at is then the last ms of that."""
        base, shown = self._mode_from()
        u = t - 1
        if u < shown or self.freq_mode == 0:
            return
        on = shown                                         # the ms it came on: NAV when the mode shows again
        if self.freq_mode == 2:
            phase = (u - base) % FREQ_BLINK_MS
            if phase < FREQ_BLINK_MS // 2:                 # dark half: the lit half before it, if there was one
                if u - phase - 1 >= shown:
                    self.lit_at = u - phase - 1
                return
            on = max(u - phase + FREQ_BLINK_MS // 2, shown)   # ADF since its lit half began
        self.lit_at = max(u, on + LIT_MIN_MS - 1)          # (never earlier than the one kept: time goes on)

    def _drop_squawk(self, t):
        """The squawk entry ended or starts anew: a digit's count still to come would tell a digit no longer
        selected"""
        if self.flash_squawk and self.flash[0] >= t:      # (one due this very ms is not shown yet: _count)
            self.flash = (t + 1, 0)                        # the mode shows again from the next ms, ADF dark first
        self.flash_squawk = False

    def _count(self, n, t, squawk=False):
        """The FREQ light counts n, from t, the time now, on (a squawk digit once its ring has rested). It takes
        the place of a count still to come (also one due this very ms, which code.py has not shown yet: a late
        read's press and its hold), and starts FLASH_PAUSE_MS after the last flash shown of one under way or just
        over (cut short where it is), and FLASH_PAUSE_MS after the light last showed its mode lit (lit_at, which
        the caller brings up to date first: _saw_lit), dark meanwhile, so its first flash stands apart. tick()
        clears one made while dark: the light is off."""
        self.flash_squawk = squawk
        start, old = self.flash
        at = max(t + SQUAWK_REST_MS if squawk else t, self.flash_free,   # (kept when a squawk count is dropped)
                 self.lit_at + 1 + FLASH_PAUSE_MS)
        if old and t > start:                              # (one still to come: this one comes instead, at was
                                                           # already at or past its start)
            last = min((t - start - 1) // FLASH_EVERY_MS, old - 1)   # (one starting now is not shown yet)
            self.flash_free = start + last * FLASH_EVERY_MS + FLASH_MS + FLASH_PAUSE_MS
            at = max(at, self.flash_free)
        self.flash = (at, n)

    # ---------------- inputs ----------------
    def key(self, name, pressed, t, at=None):
        """A key or push went down or up; at: the ms the keypad scanned it (default t), for BOUNCE_MS. A release
        waits in self.pending until tick() applies it BOUNCE_MS after its scan; a new press of the same key
        before that was a bounce and ends the wait, so a run of bounces is one press, held throughout."""
        if at is None:
            at = t
        if not pressed:
            self.pending[name] = at
            self._expire(t, at)
            return
        self._expire(t, at)
        self._freq_hold(t, at)                             # a FREQ hold read late, as long as this event's scan
                                                           # finds it, before its release is applied
        last = self.pending.pop(name, None)
        if last is not None:
            if at - last < BOUNCE_MS:                      # a bounce: the press goes on
                if name == "SHIFT" and self.used_up:       # input in the gap: SHIFT was a modifier after all.
                    self.used_up, self.shift_down = False, None   # A lock it made ends, to plain: that input
                    if self.lock_open:                     # already went out shifted
                        self.locked = self.lock_open = False
                        self.shift, self.under = self._held_session(), None
                return
            self._apply(name, False, t, last)              # the release was real, tick() hasn't seen it yet
        self._apply(name, True, t, at)

    def release(self, name, t):
        """A release that is no bounce (code.py lets go of every key after a keypad overflow): applied at once,
        and a press right after it is a new press. A FREQ push held long enough counts before it; a SHIFT hold
        does not lock, whichever key this is: after an overflow its end is not known. The keypad then reports a
        key still down as a new press, so a SHIFT held through one unlocks (more than code.py's MAX_EVENTS left
        unread: not in use)."""
        self.shift_down, self.lock_open = None, False
        self._expire(t)
        self._freq_hold(t)
        self._apply(name, False, t)

    def _apply(self, name, pressed, t, at=None):
        """A press or release applied at t; at: its scan (default t), where a FREQ or SHIFT hold starts and the
        locking press ends"""
        if at is None:
            at = t
        if pressed:
            self.keep_steps()
            if name != "SHIFT":
                self._used(t, at)
        if name.startswith("RANGE_"):
            return self._range_key(name, pressed, t)
        if name in PUSHES:
            return self._push(name, pressed, t, at)
        if not pressed:
            self.held.pop(name, None)
            self.repeat.pop(name, None)
            if name == "SHIFT":
                if self.lock_open:
                    self.lock_left = at
                self.shift_down, self.lock_open, self.used_up = None, False, False
            return
        self._drop_squawk(t)                             # a key or SHIFT tap ends the squawk entry, or starts anew
        held = self._held_session()
        if name == "SHIFT":
            if self.locked:                              # a tap ends the lock, to plain, and starts no hold; not
                if self.lock_left is None or at - self.lock_left >= TAP_GAP_MS:   # chatter right after the
                    self.locked, self.shift, self.under = False, held, None     # locking press let go
                return
            self.shift_down = at                         # a hold may lock: from the scan. One held since the start
                                                         # (update mode) never gets here: the keypad reports no press
            if self.shift == "any":                      # a second tap cancels SHIFT, except for a held control
                self.shift, self.under = held, None
            else:                                        # also while a knob still keeps SHIFT: arm for the next key
                self.shift, self.under, self.shift_until = "any", held, t + ARM_MS
                self.arm_until = self.shift_until
            return
        shifted = self.locked or self.shift == "any"
        self.shift, self.under = held, None              # a key ends a knob's session, unless a control holds it
        if name == "HOME" and shifted:                    # UNIT: firmware state, white light
            self.unit = 2 if self.unit == 1 else 1
            return
        k = self._btn(self.unit if name in BM.UNIT_KEYS else 1, BM.shifted(name) if shifted else name)
        # with SHIFT, as joysticks, UP and DN are held as other keys, so a mapping tells a tap from a hold; as a
        # keyboard (solo), which has no hold of its own, they repeat their shortcut as without SHIFT
        if name in BM.REPEAT_KEYS and (self.solo or not shifted):
            self._owe(k)
            self.repeat[name] = [k, t + REPEAT_DELAY_MS, REPEAT_MS]
        else:
            self._hold(name, k)

    def _push(self, name, pressed, t, at):
        if not pressed:
            self.held.pop(name, None)
            self.sessions.pop(name, None)
            if name == "FREQ_PUSH":
                self.freq_since = None
            return
        knob = KNOB[name]                                  # ALTHDG, FMS, FREQ
        shifted = self._knob_shift(knob, t)
        if shifted:
            self.sessions[name] = self.session
        if name == "ALTHDG_PUSH":
            k = self._btn(1, "BARO_STD" if shifted else "HDG_SYNC")
        elif name == "FMS_PUSH":
            k = self._btn(1, "CABIN_LT") if shifted else self._btn(self.unit, "FMS_CRSR")
        elif shifted:
            k = self._btn(1, "XPDR_MODE")
        else:                                              # FREQ push: next mode at once, COM once held long
            self._saw_lit(t)
            self.freq_mode = (self.freq_mode + 1) % len(FREQ_MODES)
            self.freq_since = at                           # a FREQ hold runs from the scan, as its release does
            self._count(self.freq_mode + 1, t)
            k = self._btn(self.unit, "FREQ_PUSH")
        self._hold(name, k)

    def turn(self, ring, steps, t):
        """ring: ALTHDG_OUTER, ALTHDG_INNER, FREQ_OUTER, FREQ_INNER, FMS_OUTER, FMS_INNER or RANGE.
        steps: detents, positive clockwise."""
        self._expire(t)
        if not steps:
            return
        self._used(t)
        up = steps > 0
        last = self.last_detent.get(ring)
        if last is not None and last[1] != up:
            self._reverse(ring)
        # fast: 2+ detents in one read, or the previous detent on this ring and direction was recent. After a
        # stalled loop pass, or in the first one (code.py's start may take a while), 2+ detents in one read say
        # nothing about the speed: only the previous detent counts.
        stalled = self.last_tick is None or t - self.last_tick > FAST_MS
        since = t - last[0] if last is not None and last[1] == up else None    # ms since this turn's last detent
        fast = (abs(steps) > 1 and not stalled) or (since is not None and since < FAST_MS)
        self.last_detent[ring] = (t, up)
        knob = KNOB[ring]
        if knob == "FREQ":                                  # a turn ends a FREQ hold: no change of radio under it,
            self._freq_hold(t)                              # unless the hold was long already (a late read)
            self.freq_since = None
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
                # counted once the ring rests, also at an end: the light shows where it stopped
                self._saw_lit(t)
                self._count(digit, t, squawk=True)
                return
            slow = SQUAWK[self.digit]
        elif knob == "FMS" and shifted:                     # lighting: device 1 in every unit, one step per detent
            slow = "PANEL_LT" if ring == "FMS_OUTER" else "FLOOD_LT"
        elif knob == "FREQ":
            dev = self.unit
            outer, slow, quick = FREQ_MODES[self.freq_mode]
            if ring == "FREQ_OUTER":
                slow, quick = outer, None
        else:                                               # FMS, RANGE: exactly one step per detent
            dev = self.unit if knob == "FMS" else 1
            slow = "S_RANGE" if shifted else ring           # shifted: only RANGE gets here
        names = STEP_UP if up else STEP_DN
        # Turned faster than its steps go out, a knob with a coarse step takes it while a fine step still waits:
        # the two buttons share the turn, so the knob stops with the hand. Fine steps that only wait behind other
        # buttons don't count: a slow turn stays fine.
        lagging = since is not None and since < PRESS_MS + GAP_MS
        if quick and (fast or (lagging and self.shown.get(self._btn(dev, names[slow]), (0, 0, 0))[2])):
            slow = quick
        keys = self.ring_keys.get(ring)
        if keys is None:
            keys = self.ring_keys[ring] = {}
        k = self._btn(dev, names[slow])
        keys[k] = keys.get(k, 0) + self._queue(k, abs(steps))

    def _range_key(self, name, pressed, t):
        """A tilt closes its direction and "com"; the centre push closes "com" alone. "com" can close well
        before the direction on a slow tilt, so PTR is sent on release, and only if no direction closed. SHIFT is
        decided at the press, as for a push: S_PTR or PTR as the light showed when the centre went down."""
        shifted = name in self.sessions                    # the release: was it pressed in a shifted session?
        if not pressed:
            self.sessions.pop(name, None)
        elif self._knob_shift("RANGE", t):                 # "com" too
            self.sessions[name] = self.session
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
        self._expire(t)                                    # extends a session held by a push or tilt, locks a hold
        self.last_tick = t
        self._freq_hold(t)                                 # before a pending release ends the push: read late,
        if self.pending:                                   # a long hold still counts
            for name in list(self.pending):                # a copy: applying a release ends its entry
                if t - self.pending[name] >= BOUNCE_MS:
                    self._apply(name, False, t, self.pending.pop(name))
        if self.repeat and not self.dark:                  # no repeats for a host that is away: they would wake
            self._repeat(t)                                # it; one missed comes once it is back
        self._show(t)
        if self.order and t >= self.order_ms:
            self._next(t)
        if self.dark:     # the light is off: no count made now or under way shows when USB is back (code.py ticks
            self.flash, self.flash_squawk = (t + 1, 0), False   # before it shows the lights); the mode shows from
            self.flash_free, self.lit_at = t + 1, -FLASH_PAUSE_MS - 1   # the next ms, LIT_MIN_MS counts from there

    def _freq_hold(self, t, scan=None):
        """A plain FREQ push held FREQ_HOLD_MS returns the knob to COM. A release still waiting out BOUNCE_MS
        counts as held until its scan: the push is long if it was down that long before it. Else it counts as
        held until scan, the scan of the event read now (key() passes it: a pass that waited for the host reads
        seconds of events at once, in scan order, and a release scanned after this event is not read yet), or
        until t."""
        until = self.pending.get("FREQ_PUSH", t if scan is None else scan)
        if self.freq_since is not None and until - self.freq_since >= FREQ_HOLD_MS:
            self._saw_lit(t)
            self.freq_mode, self.freq_since = 0, None      # (no FREQ step is queued: a turn ended the hold)
            self._count(1, t)

    def _repeat(self, t):
        for src in REPEAT_SOURCES:
            r = self.repeat.get(src)
            if r is None:
                continue
            if src in self.sessions and not self._in_session(src):
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
