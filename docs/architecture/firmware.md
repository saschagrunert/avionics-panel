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
  matrix --> panel
  push --> panel
  rings --> panel
  panel --> lights
  panel --> dev1 --> pc
  panel --> dev2 --> pc
```

`code.py` reads the hardware and feeds key events, encoder detents and the time to `panel.py`, which holds all
the logic, has no hardware access and runs on the PC in the tests. `boot.py` sets up the two joysticks, which
share one USB HID (human interface device) interface with two report IDs, and hides the drive and console in
normal use. `buttonmap.py` numbers the buttons, and `make_buttons.py` (PC only) writes
[BUTTONS.md](../../firmware/BUTTONS.md).

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

If the main loop raises, `code.py` releases every button (the PC keeps the last report otherwise, so a key
could stay held), prints the traceback, waits 2 s and restarts itself, also when printing fails (a
`MemoryError` may leave no room to format it). The pause lets Ctrl-C on the serial console stop even a crash
loop at the REPL (CircuitPython's interactive prompt). There is no watchdog: every wait in the loop is
bounded, and a watchdog reset would drop the joysticks off USB and run `boot.py` again.

## USB

Reports are only sent while the host has the panel mounted and not suspended. A host that enumerates the panel
but never reads it (Linux, while no program has the joystick open) makes each send wait 2 s and fail. Both
joysticks share one USB interface, so they fail alike and share one back-off: after a failed send neither
device tries for 1 s, then 2, 4 and up to 8 s, so a loop pass never stalls for more than 2 s, and in the end
the loop stalls for 2 s of every 10.

In update mode (SHIFT held at plug-in) the panel is a composite device with the drive and the console, and the
joysticks move to another interface number: Windows may then see them as new controllers
([Mapping](../using/mapping.md#update-mode-and-guids)).

## Lights

`code.py` drives the SHIFT and UNIT lights with PWM at `LED_DUTY` = 0x4800 and 0x5500 (about 28 and 33 % of
full), the amber one dimmed to a quarter for its pulse in SHIFT's last second. It sets the drive strength of
their pads (GP12, GP15) to 12 mA, which their series resistors need ([Electronics](electronics.md#lights)), by
writing the RP2040's pad registers through `memorymap` (CircuitPython has no call for it); should that fail,
it prints "LED drive strength not set" and the lights stay dimmer at the 4 mA default.

## Pins

Seven `rotaryio` encoders use 7 of the RP2040's 8 PIO state machines; the Pico bench creates all seven too.
GP25, the FREQ outer encoder's B line, is the Pico CircuitPython build's status LED during boot and in safe
mode (harmless, limited current, and while `code.py` runs the pin belongs to `rotaryio`); a custom board
definition would avoid it, and the spare GP14 cannot be routed in its place. The pins are in `code.py` and the
[GPIO map](electronics.md#gpio-map).

## Code and tests

Run `pytest` from the repository root for the host tests:

| Test | Checks |
| --- | --- |
| `firmware/test_panel.py` | `panel.py` |
| `firmware/test_code.py` | `code.py`, on the simulator's stand-in hardware |
| `firmware/test_boot.py` | `boot.py`, on the simulator's stand-in hardware |
| `tests/test_workflows.py` | The [workflows](../using/controls.md#workflows), keys and knobs, on the simulator |
| `tests/test_live.py` | The simulator in real time: actions, reports, the lights, a reload after an error |
| `tests/test_descriptor.py` | `boot.py`'s report descriptor, parsed, and the simulator's reports read with it |
| `tests/test_uhid.py` | The simulator as a Linux HID device: descriptor, name and IDs, a key press |
| `tests/test_pins.py` | Every pin `code.py` uses, against the nets in `pcb/board.py` |
| `tests/test_mpy_cross.py` | Every board file, compiled with the board's compiler |
| `tests/test_mobiflight.py` | The [MobiFlight profiles](../using/mapping.md#generated-profiles): tables, project format, workflows |

The simulator in [sim/](../../sim/) runs the unchanged `boot.py` and `code.py` on stand-ins for the hardware
modules, on virtual time: the keypads scan every 20 ms, a loop pass takes 3 ms, and the PC takes a report at
its poll of the shared endpoint every 8 ms; seconds of flying take milliseconds. It does not reproduce
CircuitPython's speed, memory or USB stack. `tests/test_workflows.py` uses it as a pilot would (tap SHIFT,
turn the FREQ inner ring) and checks the buttons MobiFlight sees at its 31.25 ms polls, by their names, and
that none stays pressed. With the firmware's own tests, a firmware change that breaks a documented workflow
fails the build.

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
their time. Every report the PC takes goes to an output function as the device (1 or 2) and the report bytes,
report ID first; `light()` reads a light's duty. An error in the loop goes as on the board: `code.py` releases
every button, waits 2 s and reloads, on the same board.

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
([Linux](../using/mapping.md#linux)). The USB layer (enumeration, interfaces, the drive in update mode) is not
simulated. `tests/test_uhid.py` runs where `/dev/uhid` and the new hidraw node are accessible and skips
elsewhere, CI included: the hosted runners' kernel has `uhid` only in an extra modules package.
`REQUIRE_UHID=1` turns the skips into failures. Without a kernel, `tests/test_descriptor.py` parses the
descriptor with the parser of [hid-tools](https://gitlab.freedesktop.org/libevdev/hid-tools) (the firmware
shell provides it on Linux) and reads the simulator's reports with it.
