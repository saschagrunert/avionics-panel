# Controls

What each key and knob does, and why it sits where it is. Button numbers for mapping are in
[firmware/BUTTONS.md](../firmware/BUTTONS.md).

## Principles

- Designed for one-handed use: the other hand is on the HOTAS. Every function works with one hand.
- Each knob sits next to its key group: ALT · HDG beside the autopilot keys, the frequency knob
  beside the radio keys, FMS beside the FMS keys.
- The left side does the autopilot work and the right side does radios and navigation. Two exceptions
  keep the knob columns symmetric: the map's RANGE knob sits under ALT/HDG, and CRS and BARO share the
  ALT/HDG knob behind SHIFT.
- White legends are primary functions, amber legends are SHIFT functions. All caps are black. Two
  lights: amber whenever SHIFT applies (pulsing in its last second), white while unit 2 is selected.
- Everything behind SHIFT can wait until the autopilot flies, apart from IDENT (SHIFT, VFR). If both
  hands are needed, LVL first.

## SHIFT

SHIFT is tapped, never held. For keys it is one-shot; a knob keeps it while in use:

- Tap SHIFT: the amber light next to it comes on. The next key press uses the amber function, then
  the panel returns to normal and the light goes off.
- A knob turned or pushed after SHIFT stays shifted while you keep using it, including moving between
  its outer and inner ring (for a whole squawk code), and returns to normal 3 s after the last detent.
  1 s was too short to move from one ring to the other or glance at the code.
- Tapping SHIFT again cancels it. It also cancels itself after 3 s without input. During the last second
  the amber light pulses between bright and dim, so a knob never drops back to its plain function
  unannounced in the middle of a turn (Reddit feedback). It never goes dark while SHIFT still applies:
  lit, even dim, means shifted; dark means plain. While a knob still keeps SHIFT (light on after a squawk
  entry), a tap arms SHIFT for the next key instead, so SHIFT, VFR gives IDENT with one tap. The VFR key
  alone sends VFR, even right after a squawk entry: VFR is the plain function because squawking VFR is
  the common case in VFR flying; to ident, tap SHIFT first.
- Keys and knobs without an amber legend still send their own shifted button. The planned default profiles
  map it to the same function as the plain control, so a stray SHIFT before DN or ENT does no harm,
  and the slot stays free for personal mappings. The FMS knob is the exception: with SHIFT it works the
  cockpit lighting, so a stray SHIFT before it changes a light level or toggles the cabin light instead
  of paging. The amber light shows it, and turning back, or pushing again, undoes it. After dimming, the
  knob stays on the lighting for 3 s like any shifted knob: wait for the amber light to go out before
  paging.
- The cap has a small raised bar near its front edge, so it can be found without looking.
  UP (bar at the back edge) and DN (bar at the front edge) are told apart the same way.
- It sits in the centre of the bottom row: shortest average travel to both sides.

## HOTAS

Not on the panel, mapped to the HOTAS instead, as in the real aircraft, where they sit on the yoke,
stick or throttle: GA (throttle), AP disconnect, CWS (control wheel steering) and elevator trim
(stick). The GFC 700 and the KFC 150 both have CWS; it lets you hand-fly briefly without disengaging
the autopilot.

## Workflows

Takeoff: turn ALT (outer ring, left knob) to the cleared altitude, push the knob (HDG SYNC), press
HDG and FLC, hold UP or DN to the climb speed. After takeoff: SHIFT, FD (YD, where installed), then AP.
Descent: set the new altitude, press VS, hold DN to -500 to -1000 ft/min; ALT captures.
Tuning: push the frequency knob to choose COM, NAV or ADF, turn outer (MHz) and inner (kHz), then press
COM ⇆ or NAV ⇆ (SHIFT, NAV ⇆ for the ADF). SHIFT, HOME (UNIT) first for COM 2 / NAV 2.
Squawk: SHIFT, then turn the frequency knob (outer: first two digits, inner: last two). Ident: SHIFT, VFR
(IDENT).

## Knobs

| Position | Part | Turn | Push | With SHIFT |
| --- | --- | --- | --- | --- |
| Left top | dual encoder, Ø22 / Ø13 knobs | outer ALT, inner HDG | HDG SYNC | outer CRS, inner BARO, push STD |
| Left bottom | multi-control: turn, tilt 4 ways, push | RANGE | map pointer | own buttons, free for personal mappings |
| Right top | dual encoder, Ø22 / Ø13 knobs | frequency: outer MHz, inner kHz (ADF: outer 100s, inner 1s) | cycles the knob through COM, NAV and ADF standby frequency (ADF only in aircraft that have one; COM/NAV is C/V on the GNS 430) | squawk code, push XPDR mode |
| Right bottom | dual encoder, Ø24 / Ø13 knobs, the largest knob as on the G1000 | outer page group, inner page | cursor | lighting: outer panel lights, inner glareshield flood, push cabin light |

On the left knob the push sits on the inner HDG knob, so pushing the heading knob syncs the heading,
as on the G1000. ALT gets the bigger outer ring: it changes most per flight and is easier to spin.
Rule: the push acts on what the inner knob sets. Unshifted the inner knob is HDG (push SYNC); shifted
it is BARO (push STD, kept on purpose for transition altitudes in Europe), so CRS goes on the outer ring.
Reddit feedback asked for CRS and BARO on their own knob, as on the G1000 bezel. Kept behind SHIFT on
purpose: a knob stays shifted while it is turned (both rings, 3 s after the last detent), so setting BARO
or a course is one tap and then turning, and a fourth dual knob would make the panel wider.
Outer rings have a coarse knurl, inner knobs a fine one.
Knob legends follow one pattern, in one type size per colour (white 1.55 mm, amber 1.5 mm): what the
rings do, outer ring first, then PUSH and what the push does; where one word covers both rings, it stands
for both (FREQ, SQUAWK, FMS). The legends: ALT · HDG · PUSH SYNC, CRS · BARO · PUSH STD, RANGE · PUSH PTR
(the four arrows already say pan), FREQ · PUSH COM/NAV/ADF, SQUAWK · PUSH XPDR, FMS · PUSH CRSR (as
Garmin prints it) and PANEL · FLOOD · PUSH CABIN for the cockpit lighting. The texts and the angle each
legend is turned towards the user live in `mech/stack.py`: 15°, RANGE 35°, and FMS only 5°, so the long
lighting line keeps about 3 mm off the plate edge. The FREQ legend ends about 5.5 mm above the FMS knob;
a longer one would run behind it. The arrow pointing away from you is hidden behind the RANGE knob when
seated; the other three are enough.
The cockpit lighting (Reddit feedback) sits behind SHIFT on the FMS knob instead of on knobs of its own:
it is set once or twice per flight, a knob keeps SHIFT while it turns, so dimming is one tap and then
turning, and more knobs would break the symmetric layout. The lighting buttons stay on the first
joystick whatever unit is selected.
Acceleration (firmware): a slow turn makes the fine step, a fast turn the coarse step.

| Function | Slow | Fast |
| --- | --- | --- |
| ALT | 100 ft | 1,000 ft |
| HDG, CRS | 1° | 10° |
| Squawk, per ring | last digit of the pair | first digit of the pair |
| ADF, inner ring | 1 kHz | 10 kHz |

COM, NAV, BARO, the FMS knob and RANGE have no acceleration: frequencies already have a coarse outer
ring, and pages, characters and zoom steps must move exactly one per detent. The dimmers move one step
per detent too; the profile sets the step size.
UP and DN are keys, as on the G1000. They auto-repeat while held (first repeat after 400 ms,
then about 8 steps per second), so -1000 ft/min takes about 1.4 s.
Knob legends are engraved on the side facing the keys; the near side of a rear knob is hidden behind
the front knob when seated.

## Keys (label, shift legend in parentheses)

Autopilot, columns are engage / vertical / lateral. VS and FLC sit next to UP and DN, as on the
G1000 where they are directly above NOSE UP and NOSE DN. LVL is in the corner, away from DN; the
corner position marks it, so it has a normal black cap. FD is the plain key and YD sits behind SHIFT
(Reddit feedback): the GFC 500/700 and the KFC autopilots have a flight director, while many GA
aircraft have no yaw damper, and where one is installed it is switched once per flight.

| | | |
| --- | --- | --- |
| AP (TEST) | ALT (ARM) | HDG (CRS CTR) |
| FD (YD) | VS | NAV (GPSS) |
| UP | FLC | APR (BC) |
| DN | VNV | LVL (½ BANK) |

One engraved frame surrounds all keys and single lines split it into AUTOPILOT, AUDIO, RADIO and FMS
(separate frames read as a double rule between AUTOPILOT and AUDIO).

Shift legends are 1.7 mm tall, centred 1.6 mm below their cap: clear of the key-hole edge, and the
next row's caps don't hide them down to about 40° eye height (a desk is around 42°, plus the 6° wedge).

Audio and radio, split by an engraved line. AUDIO (left half) selects what you talk on (MIC) and
listen to (COM; with SHIFT NAV 1, NAV 2, ADF, DME for station identifiers). It does not tune anything.
RADIO (right half) holds the CDI key, the transponder key and the flip-flops next to the frequency
knob:

| | | | |
| --- | --- | --- | --- |
| MIC 1 (ADF) | COM 1 (NAV 1) | CDI (OBS) | COM ⇆ (121.5) |
| MIC 2 (DME) | COM 2 (NAV 2) | VFR (IDENT) | NAV ⇆ (ADF ⇆) |

121.5 tunes the emergency frequency, like holding the COM flip-flop for two seconds on Garmin units.
ADF ⇆ is the ADF flip-flop (FRQ on the KR 87). MIC 1 (ADF) is different: it only listens to the ADF.
CRS CTR centres the course needle on the active VOR, like pushing the CRS knob on the G1000 and G3X.
DME (Reddit feedback, replaced MKR) listens to a separate DME such as the KN 62. A DME paired with a VOR
or ILS already sends its ident on the NAV audio, and the marker lights show on the PFD without audio.

FMS, D→ / MENU / CLR / ENT next to the FMS knob as on the G1000:

| | | | |
| --- | --- | --- | --- |
| HOME (UNIT) | FPL (VNAV) | D→ (MSG) | MENU (NRST) |
| SHIFT, light below | PROC (TERR) | CLR (MAP) | ENT |

MAP returns to the default map page, like holding CLR on the G1000 and GNS 530/430.

28 keys. UNIT (SHIFT, HOME) switches between unit 1 and unit 2 for the FMS keys and knob (GTN or GNS 530
/ second unit) and for the radio the frequency knob and flip-flops tune (COM 1 / NAV 1 or COM 2 / NAV 2).
On the G1000 UNIT selects radio 2 only and the FMS keys always drive the MFD: the PFD and MFD share the
radios, so coupling them would tune COM 2 while editing on the PFD (the planned G1000 profile maps it
that way). A white light next to the amber UNIT legend is on while unit 2 is selected. There is no
automatic return to unit 1, because a timeout would interrupt long flight plan edits.
