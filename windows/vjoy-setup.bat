@echo off
rem Makes vJoy devices 1 and 2 the panel's two joysticks: 128 and 64 buttons, no axes, hats or force feedback.
rem Needs vJoy 2.2.2.0 installed and administrator rights: right-click this file, Run as administrator.
rem -f replaces a device that exists; MobiFlight may then see it as a new joystick.
setlocal
set "VJOYCONFIG=%ProgramFiles%\vJoy\x64\vJoyConfig.exe"
if not exist "%VJOYCONFIG%" goto missing
fltmc >nul 2>&1 || goto admin
"%VJOYCONFIG%" 1 -f -a -b 128
"%VJOYCONFIG%" 2 -f -a -b 64
rem -t reports both devices, so their button counts show here
"%VJOYCONFIG%" -t 1 2
echo vJoy devices 1 and 2 should show 128 and 64 buttons above; start.bat checks them too.
pause
exit /b 0
:missing
echo vJoy is not installed: %VJOYCONFIG% is missing. Install vJoy 2.2.2.0 first.
goto failed
:admin
echo This needs administrator rights: right-click vjoy-setup.bat, Run as administrator.
:failed
echo vJoy was not set up.
pause
exit /b 1
