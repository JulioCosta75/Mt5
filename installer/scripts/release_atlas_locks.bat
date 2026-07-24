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
cd /d "%SCRIPTS_DIR%"
for %%I in ("%SCRIPTS_DIR%..") do set "ATLAS_ROOT=%%~fI"

call "%SCRIPTS_DIR%_detect_env.bat" >nul 2>nul
if not defined ATLAS_ROOT for %%I in ("%SCRIPTS_DIR%..") do set "ATLAS_ROOT=%%~fI"
if not defined NSSM if exist "%ATLAS_ROOT%\nssm.exe" set "NSSM=%ATLAS_ROOT%\nssm.exe"

echo Releasing Atlas file locks under %ATLAS_ROOT% ...

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

REM ---- 3) Kill Atlas-bundled python.exe (embedded runtime) ------------------
if exist "%ATLAS_ROOT%\python\python.exe" (
    taskkill /F /FI "IMAGENAME eq python.exe" /FI "MODULES eq %ATLAS_ROOT%\python\python311.dll" >nul 2>nul
    taskkill /F /FI "IMAGENAME eq python.exe" /FI "MODULES eq %ATLAS_ROOT%\python\python312.dll" >nul 2>nul
)

REM ---- 4) Kill ANY process whose image path is under {app} ------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ATLAS_ROOT%';" ^
  "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |" ^
  "Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase) } |" ^
  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM ---- 5) Kill processes bound to Atlas backend/bridge ports ---------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "foreach ($port in 8001,8002) {" ^
  "  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |" ^
  "  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" ^
  "}"

REM ---- 6) Kill uvicorn workers (embedded OR system Python via AppDirectory) -
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ATLAS_ROOT%';" ^
  "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |" ^
  "Where-Object { $_.CommandLine -and $_.CommandLine -match 'uvicorn' -and ($_.CommandLine -match 'server:app' -or $_.CommandLine -match 'bridge_server:app') -and ($_.CommandLine -like ('*' + $root + '*') -or $_.ExecutablePath -like ($root + '*')) } |" ^
  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM ---- 7) Kill detached cmd.exe wrappers (apply_restart / install helpers) --
REM      These often inherit CWD={app}\backend from the AtlasBackend service
REM      while the executable is System32\cmd.exe — missed by step 4.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = '%ATLAS_ROOT%';" ^
  "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |" ^
  "Where-Object { $_.CommandLine -and ($_.CommandLine -like ('*' + $root + '*') -or $_.CommandLine -match 'apply_restart\.bat' -or $_.CommandLine -match 'release_atlas_locks\.bat') } |" ^
  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM ---- 8) Wait for handles to drain -----------------------------------------
timeout /t 2 /nobreak >nul

REM ---- 9) Verify backend directory is releasable ----------------------------
set "LOCK_PROBE=%ATLAS_ROOT%\backend\.atlas_lock_probe"
if exist "%ATLAS_ROOT%\backend" (
    echo.>"%LOCK_PROBE%" 2>nul
    if exist "%LOCK_PROBE%" (
        del /f /q "%LOCK_PROBE%" >nul 2>nul
        echo Backend directory lock probe: OK
    ) else (
        echo [WARN] Backend directory may still be locked.
        echo        Run: scripts\diagnose_atlas_locks.bat
        endlocal
        exit /b 1
    )
)

echo Atlas locks released.
endlocal
exit /b 0
