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

profile.bat writes a MobiFlight profile bound to your joysticks, the panel's or the vJoy devices, with the
Python in this folder. Double-click it for the steps, or run profile.bat --family g1000 --from guids.mfproj
from a command prompt in this folder. profile.bat --cards cards.zip writes a printable card and cheat
sheet of every profile, and profile.bat --joystick-definition avionics-panel.joystick.json the file that names the panel's
buttons in MobiFlight.

This zip's build, the date and short hash of its commit, is in firmware\version.py. The page shows it in
its last line at the bottom left, and a profile from profile.bat has it in its name.

To try the page without vJoy, open a command prompt in this folder (type cmd in Explorer's address bar,
Enter) and run python\python.exe -m sim.page --open. MobiFlight then sees no joysticks.

For a tablet beside the PC, run start.bat --host 0.0.0.0 from a command prompt in this folder. Then, once,
right-click firewall.bat and choose Run as administrator: it lets the simulator through Windows' firewall on
private networks, from this PC's own subnet (not over a VPN or a guest network), whatever was chosen when
Windows asked.

To see what each button does in one of the generated profiles, run start.bat --family g1000 from a
command prompt in this folder (or gns, gtn, g3x, black-square-bonanza, cows-da40, carenado-c182t): one more
line at the bottom left of the page names what the button pressed last does there, or "nothing" and why. It
shows joystick buttons, so the keyboard mode has none.

The panel's keyboard mode, for MSFS without MobiFlight, runs too, without vJoy: see Keyboard mode on the
page linked below.

More: https://github.com/saschagrunert/avionics-panel/blob/main/docs/using/simulator.md
