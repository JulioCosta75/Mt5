@echo off
REM ============================================================
REM  Stop Atlas tray launcher + child processes (no Windows services).
REM ============================================================
setlocal EnableExtensions
call "%~dp0_detect_env.bat" >nul 2>nul

echo Stopping Atlas ...

REM 1) If the launcher left a lock file with its PID, kill that tree.
if exist "%DATA_DIR%\atlas_launcher.lock" (
  for /f "usebackq delims=" %%P in ("%DATA_DIR%\atlas_launcher.lock") do (
    if not "%%P"=="" taskkill /PID %%P /T /F >nul 2>nul
  )
  del /F /Q "%DATA_DIR%\atlas_launcher.lock" >nul 2>nul
)

REM 2) Kill Atlas embeddable interpreters by MODULES *basename* only.
REM    Full path in MODULES matches 0 processes (confirmed on Windows).
if exist "%ATLAS_ROOT%\python\python311.dll" (
  taskkill /F /FI "IMAGENAME eq python.exe" /FI "MODULES eq python311.dll" >nul 2>nul
  taskkill /F /FI "IMAGENAME eq pythonw.exe" /FI "MODULES eq python311.dll" >nul 2>nul
)

REM 3) Legacy cleanup: if old NSSM services still exist from a prior install, stop them.
sc query AtlasBackend >nul 2>nul && net stop AtlasBackend >nul 2>nul
sc query AtlasBridge  >nul 2>nul && net stop AtlasBridge  >nul 2>nul

echo Atlas stopped.
timeout /t 1 >nul
endlocal
exit /b 0
