@echo off
REM ============================================================
REM  _detect_env.bat  --  shared helper (CALLed by other scripts)
REM ------------------------------------------------------------
REM  Resolves every path + tool Atlas needs and works for BOTH
REM  supported layouts:
REM
REM    1) Production install (built with Atlas_Setup.exe):
REM         {app}\backend  {app}\bridge  {app}\frontend_build
REM         {app}\python\python.exe   {app}\nssm.exe
REM
REM    2) Fresh git clone (developer / manual install):
REM         <repo>\backend  <repo>\mt5-bridge  <repo>\frontend\build
REM         system Python   <repo>\installer\nssm.exe (bundled)
REM
REM  Exports to the CALLER:
REM    ATLAS_ROOT INSTALLER_DIR SCRIPTS_DIR BACKEND_DIR BRIDGE_DIR
REM    FRONTEND_BUILD DATA_DIR LOGS_DIR NSSM PYTHON PY_MODE
REM
REM  Returns errorlevel 1 when a hard requirement is missing.
REM  NOTE: intentionally NO setlocal so variables reach the caller.
REM ============================================================

set "SCRIPTS_DIR=%~dp0"
for %%I in ("%SCRIPTS_DIR%..") do set "INSTALLER_DIR=%%~fI"

REM ---- Layout detection --------------------------------------
set "PRODUCTION_LAYOUT="
if exist "%INSTALLER_DIR%\backend\server.py" set "PRODUCTION_LAYOUT=1"

if defined PRODUCTION_LAYOUT (
    set "ATLAS_ROOT=%INSTALLER_DIR%"
) else (
    for %%I in ("%INSTALLER_DIR%\..") do set "ATLAS_ROOT=%%~fI"
)

if defined PRODUCTION_LAYOUT (
    set "BACKEND_DIR=%INSTALLER_DIR%\backend"
    set "BRIDGE_DIR=%INSTALLER_DIR%\bridge"
    set "FRONTEND_BUILD=%INSTALLER_DIR%\frontend_build"
) else (
    set "BACKEND_DIR=%ATLAS_ROOT%\backend"
    set "BRIDGE_DIR=%ATLAS_ROOT%\mt5-bridge"
    set "FRONTEND_BUILD=%ATLAS_ROOT%\frontend\build"
)

set "DATA_DIR=%ATLAS_ROOT%\data"
set "LOGS_DIR=%ATLAS_ROOT%\logs"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%" >nul 2>nul
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%" >nul 2>nul

REM ---- Locate NSSM (bundled first, download as last resort) ---
set "NSSM="
if exist "%INSTALLER_DIR%\nssm.exe"  set "NSSM=%INSTALLER_DIR%\nssm.exe"
if not defined NSSM if exist "%ATLAS_ROOT%\nssm.exe"  set "NSSM=%ATLAS_ROOT%\nssm.exe"
if not defined NSSM if exist "%SCRIPTS_DIR%nssm.exe"  set "NSSM=%SCRIPTS_DIR%nssm.exe"
if not defined NSSM (
    echo [setup] nssm.exe not found locally - downloading NSSM 2.24 ...
    call :download_nssm
    if exist "%INSTALLER_DIR%\nssm.exe" set "NSSM=%INSTALLER_DIR%\nssm.exe"
)
if not defined NSSM (
    echo [ERROR] Could not locate or download nssm.exe.
    echo         Please drop a Windows nssm.exe ^(64-bit^) at:
    echo         %INSTALLER_DIR%\nssm.exe
    exit /b 1
)

REM ---- Locate Python -----------------------------------------
REM  Prefer a bundled embedded runtime; otherwise use the system
REM  Python (resolved to an ABSOLUTE python.exe so it also works
REM  when the service runs under the LocalSystem account).
set "PYTHON="
set "PY_MODE="
if exist "%ATLAS_ROOT%\python\python.exe"     ( set "PYTHON=%ATLAS_ROOT%\python\python.exe" & set "PY_MODE=embedded" )
if not defined PYTHON if exist "%INSTALLER_DIR%\python\python.exe" ( set "PYTHON=%INSTALLER_DIR%\python\python.exe" & set "PY_MODE=embedded" )
if not defined PYTHON (
    for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYTHON=%%P"
    if defined PYTHON set "PY_MODE=system"
)
if not defined PYTHON (
    for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PYTHON=%%P"
    if defined PYTHON set "PY_MODE=system"
)
if not defined PYTHON (
    echo [ERROR] No Python interpreter found on this machine.
    echo         Install Python 3.10 - 3.12 from
    echo         https://www.python.org/downloads/windows/
    echo         and tick "Add python.exe to PATH", then re-run.
    exit /b 1
)

goto :detect_done

REM ------------------------------------------------------------
:download_nssm
set "_NSSM_ZIP=%TEMP%\atlas_nssm.zip"
set "_NSSM_TMP=%TEMP%\atlas_nssm_tmp"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%_NSSM_ZIP%' -UseBasicParsing } catch { exit 1 }" || goto :eof
if exist "%_NSSM_TMP%" rmdir /S /Q "%_NSSM_TMP%" >nul 2>nul
powershell -NoProfile -Command "Expand-Archive -Force '%_NSSM_ZIP%' '%_NSSM_TMP%'" || goto :eof
copy /Y "%_NSSM_TMP%\nssm-2.24\win64\nssm.exe" "%INSTALLER_DIR%\nssm.exe" >nul 2>nul
rmdir /S /Q "%_NSSM_TMP%" >nul 2>nul
del "%_NSSM_ZIP%" >nul 2>nul
goto :eof

REM ------------------------------------------------------------
:detect_done
exit /b 0
