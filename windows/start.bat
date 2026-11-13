@echo off
rem The panel in the browser, feeding vJoy devices 1 and 2. Closing this window ends it.
rem Arguments go on to the simulator: start.bat --host 0.0.0.0 serves the page to a tablet on the network.
pushd "%~dp0"
if not exist python\python.exe (
  echo Extract the whole zip first: right-click it, Extract All, then run start.bat from the extracted folder.
  pause
  exit /b 1
)
python\python.exe -m sim.page --vjoy --open %*
pause
