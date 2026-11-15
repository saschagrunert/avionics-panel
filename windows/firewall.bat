@echo off
rem Lets a tablet on the network open the page (start.bat --host 0.0.0.0): allows incoming connections to this
rem folder's python.exe on private networks only, from their own subnet (no VPN or routed network further
rem away). Needs administrator rights: right-click this file, Run as administrator. Run it again after moving
rem the folder.
setlocal
set "PYTHON=%~dp0python\python.exe"
set "RULE=Avionics Panel simulator"
if not exist "%PYTHON%" goto extract
fltmc >nul 2>&1 || goto admin
rem First the rules from before: the ones Windows made for this python.exe when it asked, which block it on the
rem networks not ticked there (a block wins over every allow), and this file's, also for a folder moved since.
netsh advfirewall firewall delete rule name=all program="%PYTHON%" >nul 2>&1
netsh advfirewall firewall delete rule name="%RULE%" >nul 2>&1
netsh advfirewall firewall add rule name="%RULE%" dir=in action=allow program="%PYTHON%" protocol=TCP profile=private remoteip=localsubnet >nul || goto failed
echo The simulator may now take connections from this PC's subnet on private networks. This PC's networks:
powershell -NoProfile -Command "Get-NetConnectionProfile | Format-Table Name, InterfaceAlias, NetworkCategory -AutoSize"
echo On a network marked Public or DomainAuthenticated the tablet cannot connect. For your own network marked
echo Public: in Settings, Network ^& internet, open it and choose Private network.
pause
exit /b 0
:extract
echo Extract the whole zip first: right-click it, Extract All, then run firewall.bat from the extracted folder.
goto failed
:admin
echo This needs administrator rights: right-click firewall.bat, Run as administrator.
:failed
echo The firewall was not changed.
pause
exit /b 1
