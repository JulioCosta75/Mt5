@echo off
REM Open the Sr. Atlas dashboard via Microsoft Edge directly (URL as argument).
REM Do NOT use the OS default http handler / Start-Process on the bare URL:
REM fresh Windows (incl. Sandbox) often shows an unbranded "needs a new app"
REM dialog even when Edge is registered as ProgId — first-run shell verbs are
REM unreliable. Launching msedge.exe with the URL works on those machines.
REM
REM Order: Edge (ProgramFiles(x86) then ProgramFiles) → branded native message.
setlocal EnableExtensions
set "URL=http://localhost:8001/"
set "HINT=Atlas is running. Open http://localhost:8001 in your browser to view the dashboard."

set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
  set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
  set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
)
if defined EDGE (
  start "" "%EDGE%" "%URL%"
  if not errorlevel 1 exit /b 0
)

REM Edge not found / failed — branded hint (never leave only an unbranded OS dialog)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('%HINT%','Sr. Atlas',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null" >nul 2>&1
if errorlevel 1 (
  msg * "%HINT%" 2>nul
)
exit /b 0
