# Keyboard mode

For MSFS on Xbox and PS5, and on the PC without MobiFlight: in keyboard mode the panel is one USB keyboard
instead of the two joysticks, and its functions send keyboard shortcuts, which you bind once in the sim's own
controls menu. The joysticks stay the default mode and the one for MobiFlight ([Mapping](mapping.md)).

It has not been tried in MSFS or on a console yet: see [Limits](#limits), and
[The first test](#the-first-test) for what to try first.

## Switching the mode

Hold the HOME key (amber legend UNIT) alone while plugging the panel in, and for about 2 s more. The panel
switches between the joysticks and the keyboard and keeps that mode from then on, also through firmware
updates. Switch back the same way.

- In keyboard mode the SHIFT and UNIT lights take turns three times every time the panel starts or restarts.
- In joystick mode they stay dark.
- SHIFT held while plugging in keeps the drive and the console for an update in either mode
  ([Bring-up](../building/bring-up.md#normal-and-update-mode)). Holding both switches the mode as well.

## The shortcuts

[KEYS.md](../../firmware/KEYS.md) lists the shortcut of each function, and the one it sends in unit 2 where
that differs. They are F1 to F12, Insert, Home, Page Up, Page Down and the arrow keys with Ctrl, Shift and
Alt: keys that mean the same on every keyboard layout. Most use the right Ctrl or Shift, which MSFS is
reported to tell apart from the left ones, although its menu names both sides alike.

- With SHIFT, the keys without an amber legend (VS, UP, FLC, DN, VNV, ENT) and the RANGE knob send their plain
  shortcut.
- In unit 2 the COM and NAV functions (frequencies, flip-flops), except COM 121.5, send shortcuts of their
  own; everything else sends unit 1's. The sim's controls have one set of FMS keys, the G1000's.
- A knob detent, a step of a held UP or DN, a pan step of a RANGE tilt and the RANGE push (PTR) are short
  presses of their shortcut; a key or push holds its shortcut as long as it is held.
- One shortcut goes out at a time. A key held down holds back what follows, knob steps included, until it is
  let go.

## Binding

Which action a function stands for per aircraft is in [Compatibility](compatibility.md). The sim's controls
have actions for the autopilot, radios, transponder, lights and the G1000; most GTN and GNS keys have none.

Forum reports say MSFS 2024 can fire a shorter binding when a shortcut has none: the same key with fewer
modifiers, or the key alone. Its default airplane preset binds F1 to F12, Ctrl+F1 to Ctrl+F12 and Shift+F1 to
Shift+F11 (cameras), so before binding:

1. In the controls menu, select the keyboard and copy its airplane preset. Every keyboard uses this preset,
   yours included, so the panel's shortcuts and a real keyboard's meet there.
2. In the copy, clear F1 to F12 alone, Ctrl+F1 to Ctrl+F12 and Shift+F1 to Shift+F11. Your keyboard loses them
   too.

Then bind each function your aircraft has: search the action, select a free binding and press the panel's
control, or turn its knob one detent. Set what the control needs before you select the binding, since a FREQ
push sends a shortcut of its own: for a unit 2 function select unit 2 (SHIFT, HOME), for a NAV or ADF function
push FREQ to that mode. A fast step (ALT 1000 ft, HDG and CRS 10°, ADF 10 kHz) always comes after a slow one:
turn two detents quickly and check that the menu shows the F-key KEYS.md gives before you confirm. Where it
does not, type the shortcut on a keyboard instead, with the right Ctrl and right Shift where KEYS.md says
Right, since the menu names both sides alike. Binding every function takes about an hour; bind the ones you
use.

Last, go through the rows of [KEYS.md](../../firmware/KEYS.md) you left unbound. Where the Contains column
names a function you bound, bind that row too, to its own action or to one that does nothing in your aircraft
(for a name after "unit 2:", with unit 2 selected). The row's shortcut holds that function's, so left unbound
it could fire that function: this guards against the fallback the reports describe.

## Xbox and PS5

Plug the panel into the console's USB port and bind as above.

- Both consoles have been reported to miss a keyboard plugged in before a mouse or its receiver: plug the
  mouse in first, then the panel.
- PS5: reports say its keyboard bindings are unreliable.

## The first test

What to try first, on a PC with MSFS 2024: the [simulator](simulator.md#keyboard-mode) sends the panel's
shortcuts to the sim with Windows' SendInput, the right Ctrl and Shift included, before the panel exists.

1. In the default preset, send FMS_OUTER_CW (Right Ctrl+Shift+F5: the FMS knob's outer ring one detent
   clockwise), which has no binding there, and see whether what F5, Shift+F5 or Ctrl+F5 does in that preset
   happens. If it does, the sim falls back to shorter bindings (Ctrl+F5 also means it does not tell the sides
   apart).
2. In a copy of the preset, bind FMS_OUTER_CW and NAV_KHZ_DN (Ctrl+Right Shift+F5: the FREQ inner knob one
   detent counter-clockwise, after one FREQ push for the NAV mode made before you select the binding) to two
   different actions; the menu shows both as Ctrl+Shift+F5. Send each: each should fire its own action alone.
   If the second binding replaces the first, or one fires both, the sim does not tell the sides apart.

On a console the same two checks need the panel itself.

## Limits

- Tested on the simulator only. Whether MSFS and the consoles tell the right Ctrl and Shift from the left
  ones, take a press of about 48 ms and fall back to shorter bindings is known from forum reports only. Most
  shortcuts use the right Ctrl or Shift: where the sides are not told apart, the 114 shortcuts become 78, and
  54 of the 114 functions share theirs with another.
- On the PC the shortcuts reach the sim only while its window is in front; another program in front gets them
  instead, where they act as that program's own shortcuts (Ctrl+F5 reloads a browser page).
- On Windows, holding a key whose shortcut has the right Shift for 8 s brings up the Filter Keys prompt; its
  keyboard shortcut can be turned off in Windows' accessibility settings.
