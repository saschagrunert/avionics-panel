# Simulator

The simulator runs the panel's firmware on the PC and shows the panel in the browser: click its keys, turn
its knobs with the mouse wheel. On Windows the buttons go to two virtual joysticks, which MobiFlight reads
like the panel's two joysticks, with the same button numbers. Use it to fly with the panel's controls before
the hardware exists, to get used to SHIFT, UNIT and the knob modes ([Controls](controls.md)), and to try
bindings in MobiFlight. The firmware is the same as on the board, not a copy of its logic: what the simulator
sends is what the panel will send.

## Windows

The simulator is one zip with everything it needs, Python included. The virtual joysticks come from
[vJoy](https://github.com/BrunnerInnovation/vJoy), a signed driver that is installed separately.

1. Install vJoy 2.2.2.0: `vJoySetup_v2.2.2.0_Win10_Win11.exe` from its
   [release page](https://github.com/BrunnerInnovation/vJoy/releases/tag/v2.2.2.0). It is the build signed for
   Windows 10 and 11; older vJoy builds often fail to install there.
2. Download [avionics-panel-sim-windows.zip][sim-zip], built from a recent commit on main, which the
   [release][sim-release] names. Right-click it, Properties, tick Unblock, OK, or Windows warns before each
   batch file. Then right-click it, Extract All. The files are in the `avionics-panel-sim` folder inside the
   extracted one.
3. Right-click `vjoy-setup.bat` in that folder, Run as administrator. It sets up vJoy devices 1 and 2 with 128
   and 64 buttons and no axes, and replaces whatever these two devices were before. It also removes vJoy's
   force feedback registration, which all vJoy devices share: if another vJoy device uses force feedback, set
   it up again afterwards. Once is enough.
4. Double-click `start.bat`. A command window opens, then the panel opens in the default browser
   (`http://127.0.0.1:8000/?sim`). Keep the command window open while you fly: closing it ends the
   simulator, closing the browser tab does not. If something is wrong, the window says what and stays open.
5. In MobiFlight, bind the buttons of the two "vJoy Device" joysticks as for the panel: the button numbers
   are in [BUTTONS.md](../../firmware/BUTTONS.md), how to map them in [Mapping](mapping.md). If MobiFlight
   lists no vJoy Device, turn on joystick support and tick both under Extras, Settings, Peripherals.

[The page](#the-page) says how to play the panel in the browser.

## The page

The page shows the panel from above and keeps the view still:

- Keys: press with the mouse or a finger; a key stays pressed as long as you hold it.
- Knobs: the pointer's distance from the knob's middle picks the inner knob or the outer ring round it. The
  mouse wheel turns that ring, one detent per notch, so a fast spin is a fast turn, and a mouse button pushes
  the knob as long as it is down. On a touch screen, a finger moved round the knob turns the ring it touched,
  one detent per 12 degrees as on the panel. A quick tap in the middle pushes the knob; a finger that moves
  round it, even by a fraction of a detent, never does. A push held by touch is not possible; the mouse can
  hold one.
- RANGE turns and pushes like the other knobs; holding one of the four arrows round it tilts it that way.
- The SHIFT and UNIT lights follow the firmware. The lines at the bottom left say the same in words and show
  the buttons each joystick reports, by their [BUTTONS.md](../../firmware/BUTTONS.md) names; a button that
  went off stays there dimmed for a second. A firmware error shows its message; when the program stops, the
  page says it is disconnected and reconnects once it runs again.

Clicking the page takes the keyboard focus from the sim, so run the sim in a window or borderless, not in
exclusive full screen.

For a tablet in landscape beside the sim (a phone is too small), serve the page to the network. On Windows,
close the `start.bat` window, open a command prompt in the folder (type `cmd` in Explorer's address bar,
Enter) and run `python\python.exe -m sim.page --vjoy --host 0.0.0.0 --open`; on Linux, add `--host 0.0.0.0`
to the command in [Linux](#linux). Open the address it prints on the tablet, by its IP address, not a host
name. If that is
127.0.0.1 or a VPN address, use the computer's Wi-Fi address with the same port instead. Windows asks to let
Python through its firewall: allow it on private networks only. Anyone on that network can then press the
panel's keys. A page that goes, also one that drops off the network, lets go of what it holds within a few
seconds.

## What MobiFlight shows

- Two joysticks named "vJoy Device", without axes: device 1 has 128 buttons, device 2 has 64. Tell them apart
  by their button count, or with MobiFlight's input scan: a plain AP press comes from device 1.
- The button numbers are the panel's, as [BUTTONS.md](../../firmware/BUTTONS.md) lists them: AP is button 1
  of device 1 here too. vJoy's JoyMonitor shows them as well; Windows' game controller settings (`joy.cpl`)
  show only the first 32 buttons of each.
- MSFS sees the two joysticks too. Leave their bindings in the sim's controls settings empty, or its own
  bindings act on the same buttons.
- One program at a time can feed a vJoy device. A MobiFlight profile with vJoy outputs takes them from the
  simulator (or the simulator from it): use other vJoy devices for those.

## From the simulator to the panel

MobiFlight keys each joystick by its DirectInput instance GUID (the ID Windows gives each game controller),
not by its name or buttons, so bindings made on the vJoy devices do not attach to the panel. When the panel
is plugged in, MobiFlight lists the vJoy devices of the profile as missing: bind them to the panel's devices
under Extras, Controller Bindings, vJoy device 1 (128 buttons) to the panel's device 1 and device 2 to device
2, then save the profile. Every binding keeps its button number, so nothing else changes. Both of the panel's
devices are named "Avionics Panel"; [Mapping](mapping.md#two-joysticks) says how to tell them apart.

## Linux

MobiFlight and MSFS do not run on Linux, but the simulator does, from a copy of this repository with Python
3.10 or newer:

```sh
python3 -m sim.page          # the panel in the browser, http://127.0.0.1:8000/?sim
sudo python3 -m sim.page --uhid
```

With `--uhid` the reports also go to a HID device that Linux sees with the panel's own report descriptor, name
and USB IDs, so programs that read joysticks see the panel's two joysticks. It needs write access to
`/dev/uhid` (root, or a udev rule).
[The simulator in real time](../architecture/firmware.md#the-simulator-in-real-time) has the details, and
[Mapping](mapping.md#linux) what Linux makes of the two joysticks.

## Limits

- On Windows the joysticks are vJoy's, not the panel's: their name is "vJoy Device", their USB IDs and GUIDs
  are vJoy's, and the panel's [device name](mapping.md#device-name) and
  [update mode](mapping.md#update-mode-and-guids) do not come up. Only `--uhid` on Linux shows the panel's
  name and IDs, and nothing shows its USB layer.
- The firmware is the panel's, but the PC runs it on stand-ins for the hardware, so its timing is modelled: a
  key scan every 20 ms, a loop pass of 3 ms and a USB report every 8 ms, as on the board. The PC's own load
  can delay a step slightly; the board's real loop time is tested on the board.
- A mouse is not the panel: the feel of the keys and knobs, their reach and the legends' legibility are for
  the real panel to show.

[sim-zip]: https://github.com/saschagrunert/avionics-panel/releases/download/rolling/avionics-panel-sim-windows.zip
[sim-release]: https://github.com/saschagrunert/avionics-panel/releases/tag/rolling
