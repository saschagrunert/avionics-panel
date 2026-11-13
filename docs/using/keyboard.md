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
reported to tell apart from the left ones; its menu may show both sides alike.

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
modifiers, or the key alone. The sim's defaults sit on many of those. MSFS 2024 keeps two keyboard presets,
General and Airplanes (its SDK). Their defaults take the F-keys alone and with Ctrl or Shift (the cameras,
Shift with an F-key, are in General), and binding guides, which are unofficial, name Insert alone as the drone
camera. A list of the Keyboard 2020 presets, unofficial too, has more: Home and Page Up alone, the right Ctrl
with the arrows, and Alt with Up and Down. So before binding:

1. In the controls menu, select the keyboard and copy both of its presets, General and Airplanes. Every
   keyboard uses these presets, yours included, so the panel's shortcuts and a real keyboard's meet there.
2. In each copy, use Search by input on F1 to F12, Insert, Home, Page Up and Page Down, and clear what each
   does alone or with one modifier. Your keyboard loses them too.
3. With the Keyboard 2020 presets, also clear the right Ctrl with the arrows, and Alt+Up and Alt+Down: these
   are the panel's shortcuts for TEST, ARM, CRS CTR, COM 121.5, HOME and VFR.

Then bind each function your aircraft has: search the action, select a free binding and press the panel's
control, or turn its knob one detent. Set what the control needs before you select the binding, since a FREQ
push sends a shortcut of its own: for a unit 2 function select unit 2 (SHIFT, HOME), for a NAV or ADF function
push FREQ to that mode. A fast step (ALT 1000 ft, HDG and CRS 10°, ADF 10 kHz) always comes after a slow one:
turn two detents quickly and check that the menu shows the F-key KEYS.md gives before you confirm. Where it
does not, type the shortcut on a keyboard instead, with the right Ctrl and right Shift where KEYS.md says
Right, since the menu may show both sides alike. Binding every function takes an hour or more, longer on a
console; bind the ones you use.

Last, go through the rows of [KEYS.md](../../firmware/KEYS.md) you left unbound. Where the Contains column
names a function you bound, bind that row too, to its own action or to one that does nothing in your aircraft
(for a name after "unit 2:", with unit 2 selected). The row's shortcut holds that function's, so left unbound
it could fire that function: this guards against the fallback the reports describe. An action takes two
inputs, a primary and a secondary one (MSFS 2024 SDK), so every two rows guarded this way need a harmless
action of their own, and 62 of the 117 rows name something under Contains.

## Xbox and PS5

Plug the panel into the console's USB port and bind as above.

- Reports from both consoles say the sim may ignore the keyboard while a mouse or its receiver is plugged in.
  If it does, unplug the mouse, start the sim, plug the panel in at the main menu, then plug the mouse back
  in.
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
   different actions; the menu may show both alike. Send each: each should fire its own action alone. If the
   second binding replaces the first, or one fires both, the sim does not tell the sides apart.
3. In the same copy, bind FD (Right Ctrl+F5) and CDI (Right Ctrl+Right Shift+Alt+F5) to two different actions
   and check that the menu took all three modifiers of CDI. Then send CDI ten times: its action must fire
   every time, and FD's never. If the menu drops a modifier, three at once do not work, and 16 shortcuts use
   three (CDI, COM ⇆ and NAV ⇆, FPL, D→, MENU, PROC, CLR, two of the squawk digits, and unit 2's COM MHz
   steps). If FD's action fires too, the sim fires every bound part of a shortcut, and binding the rows under
   Contains does not guard against it.
4. Turn the ALT/HDG outer ring ten detents fast, and check that Windows shows no Sticky Keys prompt: many knob
   shortcuts hold the right Shift.

On a console the same checks need the panel itself.

## Limits

- Whether MSFS and the consoles tell the right Ctrl and Shift from the left ones, take three modifiers at
  once, take a press of about 48 ms and fall back to shorter bindings is known from forum reports only, or
  not at all. Most shortcuts use the right Ctrl or Shift: where the sides are not told apart, the 114
  shortcuts become 78, and 54 of the 114 functions share theirs with another.
- Two functions that share a shortcut, sent one right after the other (RANGE turned, SHIFT, and RANGE turned
  on while its steps still wait), leave its key up for one report, 8 ms, where two presses of one function
  leave it up for at least 56 ms. A host that reads the keyboard less often than every 8 ms may take them for
  one press; this has not been tried on a host.
- A knob that is bumped likely wakes a sleeping PC: Windows lets a keyboard wake the computer unless that is
  turned off for the device (Device Manager, Power Management).
- On the PC the shortcuts reach the sim only while its window is in front; another program in front gets them
  instead, where they act as that program's own shortcuts (Ctrl+F5 reloads a browser page).
- On Windows, holding a key whose shortcut has the right Shift for 8 s brings up the Filter Keys prompt; its
  keyboard shortcut can be turned off in Windows' accessibility settings.
