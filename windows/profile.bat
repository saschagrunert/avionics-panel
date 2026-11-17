@echo off
setlocal
rem A MobiFlight profile bound to the panel's joysticks, made by the zip's Python: the arguments go on to
rem python -m mobiflight (docs/using/mapping.md, Generated profiles). Without any it says how to use it.
rem The file goes to the folder the command prompt is in, or where -o says.
if not exist "%~dp0python\python.exe" (
  echo Extract the whole zip first: right-click it, Extract All, then run profile.bat from the extracted folder.
  pause
  exit /b 1
)
if not "%~1"=="" goto run
echo Writes a MobiFlight profile bound to your joysticks, so MobiFlight opens it without asking.
echo.
echo 1. In MobiFlight, start a new project and add two input configs. With the input scan, bind the first to
echo    ENT in unit 1 (device 1, Button 83) and the second to ENT in unit 2 (SHIFT, HOME, then ENT: device 2,
echo    Button 10). They need no action. Then SHIFT, HOME again for unit 1. Save it as guids.mfproj in this folder.
echo 2. Open a command prompt in this folder (type cmd in Explorer's address bar, Enter) and run, for the G1000:
echo.
echo      profile.bat --family g1000 --from guids.mfproj
echo.
echo    or for avionics parts:
echo.
echo      profile.bat --autopilot kap140 --cockpit g1000 --navigator g1000 --from guids.mfproj
echo      profile.bat --autopilot kap140 --cockpit bendix-king --unit1 gns530 --unit2 none --from guids.mfproj
echo.
echo    It writes avionics-panel-g1000.mfproj, or avionics-panel.mfproj, here; -o names another file.
echo    --vfr 1200 makes the VFR key squawk 1200 (US). Without --from the joysticks are not bound, as in the
echo    downloaded profiles.
echo 3. Open the new project in MobiFlight (File, Open).
echo.
echo profile.bat --cards cards.zip writes a printable card and cheat sheet of every profile (HTML and SVG), and
echo profile.bat --joystick-definition avionics-panel.joystick.json the file that names the panel's buttons in
echo MobiFlight (copy it into a folder of MobiFlight's Joysticks folder).
echo.
echo The profiles and the parts:
"%~dp0python\python.exe" -m mobiflight --list
set listed=%errorlevel%
echo.
echo More: https://github.com/saschagrunert/avionics-panel/blob/main/docs/using/mapping.md#generated-profiles
pause
exit /b %listed%
:run
"%~dp0python\python.exe" -m mobiflight %*
exit /b %errorlevel%
