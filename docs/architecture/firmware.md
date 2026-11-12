# Firmware

CircuitPython 9.2.9 on the panel's RP2040, in [firmware/](../../firmware/). Installing it is in
[Bring-up](../building/bring-up.md), mapping its buttons in [Mapping](../using/mapping.md).

```mermaid
flowchart LR
  matrix["Key matrix: 28 keys, RANGE switches,<br>ALT/HDG and FMS pushes<br>(keypad.KeyMatrix, every 20 ms)"]
  push["FREQ push<br>(keypad.Keys)"]
  rings["7 encoder rings<br>(rotaryio, one PIO state machine each)"]
  panel["panel.py: SHIFT, UNIT, frequency mode,<br>acceleration, repeats, bounce, pulse queue"]
  lights["SHIFT and UNIT lights<br>(pwmio)"]
  dev1["Joystick device 1<br>128 buttons"]
  dev2["Joystick device 2<br>64 buttons, unit 2"]
  pc["MobiFlight"]
  kbd["Keyboard mode instead:<br>one keyboard, a shortcut per button<br>(keys.py)"]
  sim["The sim's controls menu"]
  matrix --> panel
  push --> panel
  rings --> panel
  panel --> lights
  panel --> dev1 --> pc
  panel --> dev2 --> pc
  panel -.-> kbd -.-> sim
```

`code.py` reads the hardware and feeds key events, encoder detents and the time to `panel.py`, which holds all
the logic, has no hardware access and runs on the PC in the tests. `boot.py` sets up the two joysticks, which
share one USB HID (human interface device) interface with two report IDs, and hides the drive and console in
normal use. `buttonmap.py` numbers the buttons, and `make_buttons.py` (PC only) writes
[BUTTONS.md](../../firmware/BUTTONS.md). In the [keyboard mode](#keyboard-mode) `boot.py` sets up a keyboard
instead, and `keys.py` turns the buttons into shortcuts; `make_keys.py` writes
[KEYS.md](../../firmware/KEYS.md).

## State

Every state lives in the firmware and is sent as fixed joystick buttons, so mappings never need variables or
preconditions and cannot get out of sync with the panel (except with a GNS or GTN together with an ADF,
[Mapping](../using/mapping.md#per-avionics)):

- SHIFT: one-shot for keys, kept through a knob session ([Controls](../using/controls.md#shift)). Shifted
  functions are their own buttons.
- UNIT: the firmware keeps the state and drives the white light; what moves to device 2 is in
  [Mapping](../using/mapping.md#two-joysticks). Button numbers are frozen; a snapshot test in
  `firmware/test_panel.py` checks it.
- FREQ knob: the push cycles COM, NAV, ADF, and each mode sends its own turn buttons. The mode stays
  until the next push.
- Knob acceleration ([table](../using/controls.md#knobs)), UP / DN auto-repeat and the pan tilt repeat rate
  are done in the firmware.
- Squawk with SHIFT: the outer ring selects the digit (1 to 4; it stops at both ends and sends no button), the
  inner ring steps the selected digit, one step per detent, on that digit's own up and down buttons. A new
  shifted session starts at digit 1; a shifted FREQ push still held keeps its session and the digit.
- RANGE: a tilt closes its direction switch and "com"; on a slow tilt "com" can close well before the
  direction. So the centre push (PTR) is sent on release, and only if no direction closed during the press. A
  tilt repeats, first after 300 ms, then about every 120 ms.

## Knob steps

Knob detents are button pulses: 56 ms pressed, 56 ms released, so 112 ms per step of one button (about 9
steps per second). Press and gap both have to outlast a MobiFlight poll, or two detents merge into one:

- MobiFlight polls joysticks from a 20 ms timer, which Windows' 15.6 ms clock stretches to about 31 ms, and
  only sees the state at each poll.
- The PC fetches reports every 8 ms (the HID endpoint's interval), and both joysticks share that endpoint.
  With a report still waiting from the previous loop pass and both devices changing in the current one, an
  edge can arrive up to three frames (24 ms) late.

So `check_timing` in [panel.py](../../firmware/panel.py) keeps press and gap at 56 ms at least: a poll,
rounded up to 32 ms, plus three frames.

Everything goes out in the order it came, knob steps, keys and pushes alike, one new press at most every
56 ms. MobiFlight has seen each press before the next one starts, which may be in its gap; a second press of
the same button also waits for its own gap. So COM ⇆ after a quick turn swaps the frequency that was dialled,
and ENT confirms the whole character. A key with nothing ahead of it goes out at once, and two keys pressed
together go out 56 ms apart.

What the queue does:

- At most 8 detents wait, all rings together, and a detent beyond that is dropped. Keys, pushes and the first
  step of UP, DN or a tilt are never dropped (up to 8 owed presses per button). So a key waits for at most
  about 0.9 s.
- A key or push held while it waits goes down at its turn and stays down until it is let go. Let go before
  its turn, it reaches the PC as a 56 ms tap.
- A repeat of a held UP, DN or tilt waits until the last step of its button is through, so a step longer than
  the repeat interval (120 ms tilt, 125 ms UP / DN) slows the repeats down and nothing queues up.
- Acceleration: ALT, HDG, CRS and the ADF inner ring have a fine and a coarse step. A detent takes the coarse
  step within 60 ms of the previous one, and so do two detents read in one loop pass.
- With detents less than 112 ms apart, such a knob also takes the coarse step while a fine step of it still
  waits. The two buttons then share the turn, and the last step goes out within about 0.2 s of the
  hand. A fine step that only waits behind other rings does not count, so a slow turn stays fine.
- A spin faster than its steps go out can lose detents beyond the 8 waiting and runs on for up to about
  0.9 s. That holds for knobs with one step per detent (FMS, COM, NAV, the ADF outer ring, BARO, squawk, the
  dimmers, RANGE), and for the coarse step faster than about 16 detents per second.
- Turning the other way drops the steps of that ring at the end of the queue, so the knob stops at once.
  Steps that a key or another ring followed stay, since what followed builds on them (ENT confirms the
  character they dialled).

The [first-board check](../building/bring-up.md#first-board) measures whether MobiFlight counts every detent.

## Keys and switch bounce

Keys and pushes follow the same rule as the knobs: a quick tap stays pressed for at least 56 ms, and a new
press of the same button waits until that button has been released for 56 ms. MobiFlight then sees every tap,
and a fast double tap (CLR twice, a flip-flop) stays two presses. A longer press is sent as long as it is held
(and 30 ms more, see below); right after a quick tap of the same button it starts up to 112 ms late, once the
tap and its gap are over, and it waits its turn behind anything still queued ([Knob steps](#knob-steps)).

The keys are scanned every 20 ms and a press is passed on at the first scan that reads it (no added delay). A
key already held when the firmware starts is ignored until it is pressed again. A switch that bounces for
longer than a scan shows up as a release and a new press one scan later, which the 56 ms minimum press would
turn into two presses (AP on and straight off again). So a release of a key or push waits 30 ms: a new press
of it in that time was a bounce, and the press goes on as if never released. A switch that chatters while held
stays one press throughout: UP and a tilt keep repeating (a repeat due in those 30 ms waits for them, the ones
after it keep their time), and a shifted push or tilt keeps SHIFT.

- The 30 ms count from the scans that read the release and the press (`keypad.Event.timestamp`), not from the
  loop pass that picks them up, so a pass that waits for the PC cannot stretch a bounce past them.
  CircuitPython 9.2 scans the keys from its 1/1024 s tick interrupt, so the two scans of such a bounce are
  about 20 ms apart, more when code that runs with interrupts off holds the second one up: `check_timing`
  keeps the 30 ms at least one and a half scans, half a scan to spare. A finger lifts and comes back in no
  less than about 60 ms, so a real double tap stays two presses.
- The cost: every release reaches the PC 30 ms late. A held key, UP / DN repeat or tilt stops 30 ms later (no
  extra step), the 3 s of a shifted push or tilt start 30 ms after it is let go, and the RANGE centre push
  sends PTR 30 ms after its release. In those 30 ms the push or tilt still counts as held (the release may
  still turn out a bounce), so a key or a second SHIFT tap does not end its SHIFT session; the light stays on
  and shows it. Presses, the SHIFT one-shot and UNIT act on the press and get no bounce delay.
- After a keypad overflow, `code.py` releases a key whose release was lost at once, without the wait. Raising
  the keypad's `debounce_threshold` instead would delay every press and release by a scan (20 ms) and the
  recovery after a lost event too.

## Errors

If `code.py` raises, in its main loop or while it starts (a missing file, no joysticks or keyboard from
`boot.py`, a pin), it releases every button or key (the PC keeps the last report otherwise, so a key could stay
held), prints the traceback, waits 2 s and restarts itself, also when printing fails (a `MemoryError` may
leave no room to format it). The pause lets Ctrl-C on the serial console stop even a crash loop at the REPL
(CircuitPython's interactive prompt). There is no watchdog: every wait in the loop is bounded, and a watchdog
reset would drop the joysticks off USB and run `boot.py` again.

## USB

Reports are only sent while the host has the panel mounted and not suspended. A host that enumerates the panel
but never reads it (Linux, while no program has the joystick open) makes each send wait 2 s and fail. Both
joysticks share one USB interface, so they fail alike and share one back-off: after a failed send neither
device tries for 1 s, then 2, 4 and up to 8 s, so a loop pass never stalls for more than about 2 s, and in the
end the loop stalls for 2 s of every 10.

Input while the host has suspended the panel (a host that autosuspends idle HID devices, such as Linux with
`power/control` at `auto`) asks the host to resume. CircuitPython has no call for that: a report sent while
suspended waits 2 s, then sends the request, and the input waits up to 0.5 s more for the host to come back.
So the first input reaches the PC about 2 s late, still held for its full 56 ms (in keyboard mode, as every
short press there, a frame less); knob turns from before the request go before keys pressed during it. The
request is joystick 1's last report, in keyboard mode the keyboard's. A host that refuses, or no host at all,
stalls the loop for about 2.5 s per request, with a back-off like a failed send's; the back-off ends when the
host comes back by itself. Whether a sleeping PC wakes is the PC's setting ("Allow this device to wake the
computer" in Windows' Device Manager, `power/wakeup` on Linux).

In update mode (SHIFT held at plug-in) the panel is a composite device with the drive and the console, and the
joysticks move to another interface number: Windows may then see them as new controllers
([Mapping](../using/mapping.md#update-mode-and-guids)).

## Keyboard mode

[keys.py](../../firmware/keys.py) holds what the [keyboard mode](../using/keyboard.md) adds: the stored mode,
the keyboard's descriptor, the shortcut of every button and the report. `panel.py` is the same in both modes,
but for one rule.

- The mode is one byte of `microcontroller.nvm`, the 4 KB of flash that CircuitPython's RP2040 builds keep
  between the firmware and CIRCUITPY (`CIRCUITPY_INTERNAL_NVM_SIZE`), so it survives power cycles, new files
  and a new UF2; `flash_nuke.uf2` erases it. 0x4B is the keyboard, any other value (a blank flash reads 0xFF)
  the joysticks. `boot.py` reads HOME (amber legend UNIT; row GP5, in SHIFT's column GP6) the way it reads
  SHIFT, and while it is held stores the other mode: switching to the keyboard writes one byte, switching back
  erases and rewrites the 4 KB sector. `code.py` reads the byte itself and imports `keys.py` only in keyboard
  mode, so the joysticks keep its RAM, then looks for the device that mode needs.
- USB: one keyboard and no joysticks, under the same names: HID 1.11's boot keyboard (appendix E.6), without
  report ID, 8 bytes (the modifiers, a reserved byte, six keys of which the panel uses one), keys 0 to 101.
  The interface declares the boot protocol (`usb_hid.enable(boot_device=1)`), for hosts that take only a boot
  keyboard. A host that switches to the boot protocol, if it does so before `code.py` starts, gets
  CircuitPython's own boot keyboard in `usb_hid.devices`, with the same 8 bytes, so `code.py` sends the same
  reports. In update mode the console and the drive come first, and CircuitPython takes a boot device only on
  USB interface 0 (it starts in safe mode otherwise), so there the keyboard declares no boot protocol.
- The shortcuts: F1 to F12, Insert, Home, Page Up, Page Down and the arrows, with left Ctrl, Shift and Alt and
  right Ctrl and Shift. `keys.GROUPS` lists them with what each group leaves out and why; `keys.FIRST` names
  the functions the sim may have no action for, which get shortcuts whose parts do nothing in flight. With
  SHIFT, a key without an amber legend sends its plain shortcut, and in unit 2 only COM and NAV have their own
  (not COM 121.5). 114 shortcuts, frozen by `firmware/test_keys.py`; `keys.UNIT2` leaves 8 free for new
  functions of device 1, and 2 more are free after unit 2's.
- One shortcut at a time: `Panel(solo=True)` presses a button only while no other one is down, so a held key
  holds back what follows. The queue, its order, its spacing and the acceleration stay the same
  ([Knob steps](#knob-steps)). A shortcut is a combination of keys: two at once would be another one.
- The report: `keys.Keyboard` turns the pressed button into its shortcut, a step per loop pass. The modifiers
  go down alone, then the key; on release the key goes up first, then the modifiers. So the host never sees a
  key with modifiers other than its own, and a shortcut that follows at once swaps the modifiers in a report
  of its own. `send_report` waits until the host has taken the report before, so each step reaches it, a
  frame apart: the key goes down a frame after its modifiers and is down about one frame less than
  `PRESS_MS`.
- Each time it starts, before its loop, `code.py` lights SHIFT and UNIT by turns, 150 ms each, three times,
  also while USB is down (at plug-in the host may not have mounted the panel yet), so the mode shows on a
  charger too. Then the loop sets both lights, dark while USB is down ([Lights](#lights)). Keys and knobs used
  meanwhile go out after it.

## Lights

`code.py` drives the SHIFT and UNIT lights with PWM at `LED_DUTY` = 0x4800 and 0x5500 (about 28 and 33 % of
full), the amber one dimmed to a quarter for its pulse in SHIFT's last second. Both stay dark while USB is not
connected (the PC asleep, booting or off, a charger, a host that has suspended the panel); the panel runs on.
In keyboard mode they first take turns at each start ([Keyboard mode](#keyboard-mode)). It sets the drive
strength of their pads (GP12, GP15) to 12 mA, which the SHIFT light's series resistor needs (GP15 only switches
the UNIT light's transistor, [Electronics](electronics.md#lights)), by writing the RP2040's pad registers
through `memorymap` (CircuitPython has no call for it); should that fail, it prints "LED drive strength not
set" and the SHIFT light stays dimmer at the 4 mA default.

## Pins

Seven `rotaryio` encoders use 7 of the RP2040's 8 PIO state machines; the Pico bench creates all seven too.
GP25, the FREQ outer encoder's B line, is the Pico CircuitPython build's status LED, driven high at 12 mA in
blinks in the first second after power-up, after `code.py` stops with an error and in safe mode; a 1 k
resistor in series on the board limits the current into a closed contact to 3.3 mA, `boot.py` sets the LED's
brightness to 0 so that later blinks drive the pin low, and while `code.py` runs the pin belongs to
`rotaryio`. A custom board definition would avoid it, and the spare GP14 cannot be routed in its place. The
pins are in `code.py` and the [GPIO map](electronics.md#gpio-map).

## Code and tests

Run `pytest` from the repository root for the host tests:

| Test | Checks |
| --- | --- |
| `firmware/test_panel.py` | `panel.py` |
| `firmware/test_code.py` | `code.py`, on the simulator's stand-in hardware, in both modes |
| `firmware/test_boot.py` | `boot.py`, on the simulator's stand-in hardware: USB, the drive, the stored mode |
| `firmware/test_keys.py` | `keys.py`: the stored mode, the descriptor, a shortcut per button, the report |
| `tests/test_sim.py` | The simulator itself: what it refuses, its errors, and its stand-ins against CircuitPython's (report length, suspend, key scans, event queue, clocks) |
| `tests/test_workflows.py` | The [workflows](../using/controls.md#workflows), keys and knobs, on the simulator, in both modes |
| `tests/test_live.py` | The simulator in real time: actions, reports, the lights, a reload after an error |
| `tests/test_descriptor.py` | `boot.py`'s report descriptors, parsed, and the simulator's reports read with them |
| `tests/test_uhid.py` | The simulator as a Linux HID device: descriptor, name and IDs, a key press, the keyboard |
| `tests/test_page.py` | The panel page's server: actions, its event stream, an error, a page that goes |
| `tests/test_vjoy.py` | The vJoy output: its struct, every button of both devices, its calls into a stand-in DLL |
| `tests/test_sendinput.py` | The keystroke output: its structs, the keystrokes of the keyboard's reports, a stand-in DLL |
| `tests/test_windows_zip.py` | The simulator's zip for Windows: layout, `._pth`, the simulator run from it |
| `tests/test_pins.py` | Every pin `code.py` uses, against the nets in `pcb/board.py` |
| `tests/test_mpy_cross.py` | Every board file, compiled with the board's compiler |
| `tests/test_mobiflight.py` | The [MobiFlight profiles](../using/mapping.md#generated-profiles): tables and their codes, project format, workflows |

The simulator in [sim/](../../sim/) runs the unchanged `boot.py` and `code.py` on stand-ins for the hardware
modules, on virtual time: the keypads scan every 20/1024 s (19.5 ms), a loop pass takes 3 ms, and the PC takes
a report at its poll of the shared endpoint every 8 ms; seconds of flying take milliseconds. It does not
reproduce CircuitPython's speed, memory or USB stack; the other differences are listed in
[sim/hardware.py](../../sim/hardware.py). `tests/test_workflows.py` uses it as a pilot would (tap
SHIFT, turn the FREQ inner ring) and checks the buttons MobiFlight sees at its 31.25 ms polls, by their names,
and that none stays pressed. With the firmware's own tests, a firmware change that breaks a documented
workflow fails the build. Each workflow runs in keyboard mode too (`Sim(keyboard=True)`), where the sim must
see the same functions typed, in the same order: `sim.typed()` reads them from the keyboard's reports and fails
on a key that goes down with modifiers other than its own or beside another key.

The compiler is CircuitPython 9.2's own `mpy-cross`, so it rejects the syntax the board rejects. It checks
syntax only: a module or argument the board's build lacks shows up on the bench. It is not in nixpkgs:
[nix/mpy-cross.nix](../../nix/mpy-cross.nix) fetches Adafruit's 9.2.9 build for Linux x86-64 and ARM64, pinned
by its hash, and the firmware shell puts it on the PATH and sets `REQUIRE_MPY_CROSS=1`, which makes a missing
compiler fail its tests. On other systems the shell prints a notice and those tests skip.

### The simulator in real time

[sim/live.py](../../sim/live.py) runs `code.py` on the same stand-ins in a thread of its own, paced to the
wall clock. Any thread queues the simulator's actions by the firmware's input names (`act("tap", "AP")`,
`act("turn", "FREQ_INNER", 3)`), each after the ones before it: press, release and a turn with no spacing
(`act("turn", "FREQ_INNER", 3, 0)`) run at once, while a tap, a tilt and a turn with its default spacing take
their time. A switch changes no sooner than 50 ms after its last change, on the panel's clock, as with a
finger: a quicker click would fall between two key scans. Every report the PC takes goes to an output function
as the device (1 or 2) and the report bytes, report ID first (in keyboard mode the keyboard's 8 bytes, as
device 1); `light()` reads a light's duty. An error in the loop goes as on the board: `code.py` releases every
button, waits 2 s and reloads, on the same board.

[sim/uhid.py](../../sim/uhid.py) makes it a HID device on Linux through `/dev/uhid`: one device with the
report descriptor `boot.py` builds (both report IDs), the name `DIY Avionics Panel` and the IDs 239A:80F4. It
reads actions from stdin, one per line, and needs write access to `/dev/uhid` (root, or a udev rule):

```sh
sudo python3 -m sim.uhid   # then type, for example:
tap AP
turn FREQ_INNER 3
tilt UP 500
lights
```

`hid-recorder` or a `/dev/hidrawN` node shows every report. Linux's input layer makes one input device of
both joysticks and maps only the first 80 buttons of device 1, so `evtest` sees part of it, as with the panel
([Linux](../using/mapping.md#linux)). `python3 -m sim.uhid --keyboard` makes the keyboard of the keyboard
mode instead, which the desktop takes like any keyboard. The USB layer (enumeration, interfaces, the drive in
update mode) is not simulated. `tests/test_uhid.py` runs where `/dev/uhid` and the new hidraw node are
accessible and skips elsewhere, CI included: the hosted runners' kernel has `uhid` only in an extra modules
package. `REQUIRE_UHID=1` turns the skips into failures. Without a kernel, `tests/test_descriptor.py` parses
the descriptors with the parser of [hid-tools](https://gitlab.freedesktop.org/libevdev/hid-tools) (the
firmware shell provides it on Linux) and reads the simulator's reports with them.

### The panel page

[sim/page.py](../../sim/page.py) runs the simulator in real time and serves the 3D view with the panel
playable in it. It needs Python 3.10 or newer and nothing else. From the repository root:

```sh
python3 -m sim.page        # then open the URL it prints, http://127.0.0.1:8000/?sim
```

How the page is played (keys, knobs, pushes, touch, the RANGE tilt, the lights) and how a tablet opens it are
in [The page](../using/simulator.md#the-page). `--port N` changes the port (8000), `--host 0.0.0.0` serves
the page to the network, and `--open` opens it in the default browser once it is served. A page that goes,
also one that drops off the network, lets go of what it holds within a few seconds. `--uhid` also feeds the
uhid device above, so programs on Linux see the joysticks, and `--vjoy` the vJoy devices below; without them
the reports go only to the page. `--keyboard` runs the keyboard mode, and `--sendinput` then types its
shortcuts on Windows ([below](#keystrokes-on-windows)). The API is described in `sim/page.py`. Opened without
`?sim`, as on GitHub Pages, the viewer stays the plain 3D view.

### vJoy on Windows

[sim/vjoy.py](../../sim/vjoy.py) feeds vJoy 2.2.2.0 through its `vJoyInterface.dll` with `ctypes`: report ID
4 goes to vJoy device 1 and ID 5 to device 2, each report as one `UpdateVJD`, so MobiFlight never reads half
a report. Its struct mirrors `JOYSTICK_POSITION_V3` of vJoy's `SDK/inc/public.h` at the tag `v2.2.2.0`
(124 bytes; pyvjoy's is an older, shorter one). It acquires both devices at the start, after checking that
they exist with enough buttons and that no other program owns them. At the end it lets go of every button and
of the devices: after Ctrl-C, and through a console handler also on Ctrl-Break and when the window closes,
where Python runs no `finally`. A kill from Task Manager leaves the last buttons down until the next start,
whose first reports clear them. `python -m sim.vjoy` reads actions from stdin like `sim.uhid`, and
`python -m sim.page --vjoy` feeds vJoy from the page. `tests/test_vjoy.py` checks it on Linux against the
header's layout, `boot.py`'s descriptor, BUTTONS.md and stand-ins for the DLL and the console; the DLL itself
and MobiFlight are tested on Windows.

### Keystrokes on Windows

[sim/sendinput.py](../../sim/sendinput.py) types the keyboard mode's shortcuts on Windows, through user32's
`SendInput` with `ctypes`: each report becomes the key presses and releases it differs by from the one
before, by their scan codes (Microsoft's table of HID usages and scan codes), so a game that reads scan codes
takes them as a keyboard's. Windows gives them to the window in front, so the page is played from another
device ([Simulator](../using/simulator.md#keyboard-mode)). At the end it lets go of every key, through a
console handler as vJoy's also on Ctrl-Break and when the window closes, and sends nothing after that. Windows
takes no keystrokes while a UAC prompt or the lock screen is up: a report it does not take in full ends the
run with an error, and the end lets go of that report's keys too, and of every modifier.
`tests/test_sendinput.py` checks its structs against `winuser.h`'s 64-bit layout and its keystrokes against
a stand-in for `user32.dll`; Windows and the sim are tested on Windows.

[windows/make_zip.py](../../windows/make_zip.py) builds the zip the [Simulator](../using/simulator.md) page
describes, on Linux: Python's embeddable package for Windows (amd64, pinned by version and SHA-256), whose
`._pth` file gets the zip's folder, with `firmware/`, `sim/`, `viewer/` and the batch files in `windows/`.
The `windows` workflow builds it for every pull request and push to main, keeps it as an artifact of the run
and attaches it to every published release. Pushes to main also replace the zip of the `rolling` pre-release,
which the Simulator page links, so it is from a recent commit on main, which the release names.
