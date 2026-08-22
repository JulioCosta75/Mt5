@echo off
REM Open the Sr. Atlas dashboard with a safe fallback chain:
REM   1) OS default http:// handler
REM   2) Microsoft Edge (ships with supported Windows)
REM   3) Native message with the URL (never leave only a bare OS dialog)
setlocal EnableExtensions
set "URL=http://localhost:8001/"
set "HINT=Atlas is running. Open http://localhost:8001 in your browser to view the dashboard."

REM 1) Default handler — PowerShell Start-Process raises when no app is associated
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Start-Process -FilePath '%URL%'; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 exit /b 0

REM 2) Edge (x86 path first, then Program Files — covers typical and ARM/64 layouts)
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

REM 3) Branded hint — do not leave only the unbranded Windows "needs a new app" dialog
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('%HINT%','Sr. Atlas',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null" >nul 2>&1
if errorlevel 1 (
  msg * "%HINT%" 2>nul
)
exit /b 0
