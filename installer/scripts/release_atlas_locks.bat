@echo off
REM ============================================================
REM  release_atlas_locks.bat
REM ------------------------------------------------------------
REM  Stops Atlas Windows services and terminates any process still
REM  holding files under {app}.  Must run BEFORE Inno Setup deletes
REM  installation files (PrepareToInstall on upgrade, InitializeUninstall
REM  on uninstall).  Safe to run multiple times.
REM ============================================================
setlocal

set "SCRIPTS_DIR=%~dp0"
for %%I in ("%SCRIPTS_DIR%..") do set "ATLAS_ROOT=%%~fI"

call "%SCRIPTS_DIR%_detect_env.bat" >nul 2>nul
if not defined ATLAS_ROOT for %%I in ("%SCRIPTS_DIR%..") do set "ATLAS_ROOT=%%~fI"
if not defined NSSM if exist "%ATLAS_ROOT%\nssm.exe" set "NSSM=%ATLAS_ROOT%\nssm.exe"

echo Releasing Atlas file locks ...

REM ---- 1) Stop via Service Control Manager --------------------------------
net stop AtlasBackend >nul 2>nul
net stop AtlasBridge  >nul 2>nul
timeout /t 2 /nobreak >nul

REM ---- 2) Stop + remove NSSM service wrappers -------------------------------
if defined NSSM (
    "%NSSM%" stop AtlasBackend >nul 2>nul
    "%NSSM%" stop AtlasBridge  >nul 2>nul
    timeout /t 1 /nobreak >nul
    "%NSSM%" remove AtlasBackend confirm >nul 2>nul
    "%NSSM%" remove AtlasBridge  confirm >nul 2>nul
) else (
    sc delete AtlasBackend >nul 2>nul
    sc delete AtlasBridge  >nul 2>nul
)

REM ---- 3) Kill Atlas-bundled python.exe (uvicorn backend + bridge) ----------
if exist "%ATLAS_ROOT%\python\python311.dll" (
    taskkill /F /FI "IMAGENAME eq python.exe" /FI "MODULES eq %ATLAS_ROOT%\python\python311.dll" >nul 2>nul
)

REM ---- 4) Kill any remaining process whose image path is under {app} --------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ATLAS_ROOT%';" ^
  "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |" ^
  "Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase) } |" ^
  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM Give the OS a moment to release file handles.
timeout /t 2 /nobreak >nul
echo Atlas locks released.
endlocal
exit /b 0
