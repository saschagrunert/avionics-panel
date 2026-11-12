Avionics Panel simulator for Windows

The panel's firmware, run on this PC: click its keys and turn its knobs in the browser, and MobiFlight sees
two joysticks, as with the panel. Use it to fly with the panel's controls and to set up MobiFlight before
the hardware exists.

1. Install vJoy 2.2.2.0 (vJoySetup_v2.2.2.0_Win10_Win11.exe) from
   https://github.com/BrunnerInnovation/vJoy/releases/tag/v2.2.2.0
2. Right-click vjoy-setup.bat, Run as administrator. It makes vJoy devices 1 and 2 the panel's joysticks
   (128 and 64 buttons) and replaces whatever these two devices were before. Once is enough.
3. Double-click start.bat. A command window opens, then the panel opens in the browser. Keep the window
   open while you fly; close it to end the simulator.
4. In MobiFlight, bind the buttons of the two "vJoy Device" joysticks: device 1 has 128 buttons, device 2
   has 64. firmware\BUTTONS.md lists what each button is. In MSFS, leave these two joysticks unbound.

If Windows blocks the batch files, delete this folder, right-click the downloaded zip, Properties, tick
Unblock, OK, and extract it again.

A profile bound to the vJoy devices has to be bound to the real panel again later: MobiFlight tells
joysticks apart by an ID Windows gives each one.

More: https://github.com/saschagrunert/avionics-panel/blob/main/docs/using/simulator.md
