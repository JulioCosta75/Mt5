@echo off
REM ============================================================
REM  Start Atlas as a normal app (tray launcher — no Windows services).
REM  Phase 1 entry point. Prefer this over start_atlas.bat / NSSM.
REM ============================================================
setlocal EnableExtensions
title Atlas

call "%~dp0_detect_env.bat"
if errorlevel 1 (
    echo [ERROR] Environment detection failed.
    pause
    exit /b 1
)

if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%" >nul 2>nul
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%" >nul 2>nul

set "LAUNCHER=%SCRIPTS_DIR%atlas_launcher.py"
if not exist "%LAUNCHER%" (
    echo [ERROR] Missing launcher: %LAUNCHER%
    pause
    exit /b 1
)

REM Prefer pythonw.exe so no console window stays open with the tray icon.
set "PYW="
for %%I in ("%PYTHON%") do set "PY_DIR=%%~dpI"
if exist "%PY_DIR%pythonw.exe" set "PYW=%PY_DIR%pythonw.exe"

echo Starting Atlas tray launcher ...
echo   Root   : %ATLAS_ROOT%
echo   Python : %PYTHON%
echo   Tip    : look for the Atlas icon in the system tray. Right-click to Quit.
echo.

if defined PYW (
    start "Atlas" "%PYW%" "%LAUNCHER%" --root "%ATLAS_ROOT%"
) else (
    start "Atlas" "%PYTHON%" "%LAUNCHER%" --root "%ATLAS_ROOT%"
)

endlocal
exit /b 0
