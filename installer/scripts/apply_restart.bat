@echo off
REM ============================================================
REM  apply_restart.bat  --  restart Atlas services so freshly
REM  saved MT5 credentials (written by the dashboard) take effect.
REM  Launched detached by the backend; safe to restart the backend
REM  itself because this runs in its own process.
REM ============================================================
setlocal

REM Never inherit AtlasBackend's AppDirectory (backend\) as CWD — that
REM leaves an empty backend folder locked after services stop.
cd /d "%~dp0"

REM Give the backend a moment to finish sending its HTTP response.
timeout /t 2 >nul

call "%~dp0_detect_env.bat" >nul 2>nul
if not defined NSSM (
    for %%I in ("%~dp0..\nssm.exe") do set "NSSM=%%~fI"
)

if defined NSSM (
    "%NSSM%" restart AtlasBridge  >nul 2>nul
    "%NSSM%" restart AtlasBackend >nul 2>nul
) else (
    net stop  AtlasBridge  >nul 2>nul
    net stop  AtlasBackend >nul 2>nul
    net start AtlasBridge  >nul 2>nul
    net start AtlasBackend >nul 2>nul
)

endlocal
exit /b 0
