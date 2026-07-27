@echo off
REM ============================================================
REM  Removes the Atlas Windows services.
REM ============================================================
setlocal

call "%~dp0_detect_env.bat" >nul 2>nul
if not defined NSSM (
    for %%I in ("%~dp0..\nssm.exe") do set "NSSM=%%~fI"
)

"%NSSM%" stop   AtlasBackend >nul 2>nul
"%NSSM%" remove AtlasBackend confirm
"%NSSM%" stop   AtlasBridge  >nul 2>nul
"%NSSM%" remove AtlasBridge  confirm
echo Atlas services removed.
endlocal
