@echo off
REM ============================================================
REM  apply_restart.bat — restart Atlas via the tray launcher
REM  (no NSSM / Windows services). Detached by the backend after
REM  Settings "Save & Connect" writes new .env credentials.
REM ============================================================
setlocal EnableExtensions

REM Let the HTTP response finish before we recycle the backend process.
timeout /t 2 >nul

call "%~dp0stop_atlas.bat" >nul 2>nul
timeout /t 2 >nul

REM Relaunch tray app (pythonw preferred) without waiting.
call "%~dp0start_atlas_app.bat"

endlocal
exit /b 0
