@echo off
REM Open the Sr. Atlas dashboard with a safe fallback chain:
REM   1) OS default http:// handler — ONLY if HKCU UserChoice ProgId exists
REM   2) Microsoft Edge (ships with supported Windows)
REM   3) Native message with the URL (never leave only a bare OS dialog)
REM
REM Why the registry pre-check: Start-Process / start do NOT raise when no
REM default browser is registered. Windows shows "This device needs a new app
REM to open this link" asynchronously outside PowerShell's control, so
REM try/catch never fires. Check UserChoice before attempting the default open.
setlocal EnableExtensions
set "URL=http://localhost:8001/"
set "HINT=Atlas is running. Open http://localhost:8001 in your browser to view the dashboard."

REM 1) Default handler — only when http UserChoice ProgId is present
set "HAS_DEFAULT=0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice' -ErrorAction SilentlyContinue; if ($null -eq $p -or [string]::IsNullOrWhiteSpace([string]$p.ProgId)) { exit 1 } else { exit 0 }" >nul 2>&1
if not errorlevel 1 set "HAS_DEFAULT=1"

if "%HAS_DEFAULT%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%URL%'; exit 0" >nul 2>&1
  if not errorlevel 1 exit /b 0
)

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
