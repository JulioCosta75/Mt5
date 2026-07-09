@echo off
REM ============================================================
REM  Atlas installer — build.bat
REM  Run this on a Windows machine. Inno Setup 6 is auto-installed if missing.
REM  Produces:  dist\Atlas_Setup.exe
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ---- Build-script revision marker ------------------------------------
REM  Bump BUILD_REV whenever build.bat changes so a running VPS can prove
REM  (from its own console output) exactly which script it is executing.
REM  If you DO NOT see this banner + the [setup] auto-install lines below,
REM  you are running an OLD build.bat -> re-clone / checkout the correct branch.
set "BUILD_REV=iscc-autoinstall-r2"

echo.
echo === Atlas installer builder ===
echo === build.bat revision: %BUILD_REV% (Inno Setup 6 auto-install ENABLED) ===
echo.

REM ---- Resolve version (single source of truth: backend\VERSION) ----
set "ATLAS_VER="
if exist "..\backend\VERSION" for /f "usebackq delims=" %%V in ("..\backend\VERSION") do set "ATLAS_VER=%%V"
if not defined ATLAS_VER set "ATLAS_VER=0.3.0"
set "GITSHA="
for /f "delims=" %%G in ('git rev-parse --short HEAD 2^>nul') do set "GITSHA=%%G"
if not defined GITSHA set "GITSHA=nogit"
echo Building Atlas version %ATLAS_VER% (build %GITSHA%)
echo.

REM ---- Tooling checks ----------------------------------------
REM Inno Setup 6 (ISCC.exe): detect, and if missing, install it automatically.
REM A clean Windows VPS should be able to run build.bat with NO manual install.
set "ISCC_EXE="
call :ensure_iscc
if not defined ISCC_EXE (
    echo.
    echo [ERROR] Inno Setup 6 ^(ISCC.exe^) could not be found or installed automatically.
    echo         The automatic installer needs outbound internet access to
    echo         jrsoftware.org ^(or a working winget / choco^). If this machine is
    echo         offline or blocked, either:
    echo           - install Inno Setup 6 manually: https://jrsoftware.org/isdl.php
    echo           - or set  ISCC=C:\full\path\to\ISCC.exe  and rerun build.bat.
    exit /b 1
)
echo Using Inno Setup compiler: "%ISCC_EXE%"

where powershell >nul 2>nul || (echo [ERROR] PowerShell required. & exit /b 1)
where node       >nul 2>nul || echo [WARN] node not found - frontend pre-build will be skipped. Use prebuilt payload\frontend_build\ instead.
where yarn       >nul 2>nul || echo [INFO] yarn not found, will use npm if available.

REM ---- Folders ----
if not exist payload mkdir payload
if not exist dist    mkdir dist

REM ---- 1) Download embedded Python 3.11 ----------------------
set PYVER=3.11.9
set PYZIP=python-%PYVER%-embed-amd64.zip
if not exist payload\python\python.exe (
    echo.
    echo [1/6] Downloading Python %PYVER% embeddable...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "Invoke-WebRequest 'https://www.python.org/ftp/python/%PYVER%/%PYZIP%' -OutFile '%PYZIP%'" || exit /b 1
    if not exist payload\python mkdir payload\python
    powershell -NoProfile -Command "Expand-Archive -Force '%PYZIP%' 'payload\python'"
    del %PYZIP%
    REM Enable site-packages in embeddable Python:
    powershell -NoProfile -Command ^
      "(Get-Content payload\python\python311._pth) -replace '#import site','import site' | Set-Content payload\python\python311._pth"
    echo OK
) else (
    echo [1/6] Python %PYVER% already in payload\python\ ^(skipping download^)
)

REM ---- 2) Provision NSSM (service manager) -------------------
REM  A 64-bit nssm.exe is committed next to build.bat so the build
REM  (and a bare git clone) work offline. Fall back to download.
if not exist payload\nssm.exe (
    if exist nssm.exe (
        echo [2/6] Using bundled nssm.exe
        copy /Y nssm.exe payload\nssm.exe >nul
        echo OK
    ) else (
        echo.
        echo [2/6] Downloading NSSM 2.24...
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
          "Invoke-WebRequest 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'nssm.zip'" || exit /b 1
        powershell -NoProfile -Command "Expand-Archive -Force 'nssm.zip' 'nssm_tmp'"
        copy /Y nssm_tmp\nssm-2.24\win64\nssm.exe payload\nssm.exe
        rmdir /S /Q nssm_tmp
        del nssm.zip
        echo OK
    )
) else (
    echo [2/6] NSSM already in payload\nssm.exe ^(skipping^)
)

REM ---- 3) Copy backend + bridge sources ----------------------
echo.
echo [3/6] Staging backend + bridge sources...
if exist payload\backend rmdir /S /Q payload\backend
if exist payload\bridge  rmdir /S /Q payload\bridge
xcopy /E /I /Y ..\backend       payload\backend  >nul
xcopy /E /I /Y ..\mt5-bridge    payload\bridge   >nul
REM Exclude existing .env (user-specific); keep .env.example
if exist payload\backend\.env del payload\backend\.env
if exist payload\bridge\.env  del payload\bridge\.env
REM Drop heavy/unneeded dirs
for /d %%D in (payload\backend\__pycache__ payload\bridge\__pycache__ payload\backend\tests) do (
    if exist "%%D" rmdir /S /Q "%%D"
)
echo OK

REM ---- 3b) Stamp build_info.json (version + UTC build time + git sha) ----
echo Stamping build_info.json ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$b=[ordered]@{version='%ATLAS_VER%';build='%GITSHA%';built_at=((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'));channel='release'}; ($b|ConvertTo-Json -Compress)|Set-Content -Encoding UTF8 -NoNewline 'payload\backend\build_info.json'" || exit /b 1
echo OK

REM ---- 4) Build frontend (or use prebuilt) -------------------
echo.
echo [4/6] Building frontend ^(clean rebuild^)...
if exist payload\frontend_build rmdir /S /Q payload\frontend_build
pushd ..\frontend
if exist node_modules ( echo node_modules ok ) else ( call yarn install --frozen-lockfile || call npm ci || exit /b 1 )
REM Same-origin: dashboard is served by the backend, so no external API base.
set "REACT_APP_BACKEND_URL="
call yarn build || call npm run build || exit /b 1
popd
xcopy /E /I /Y ..\frontend\build payload\frontend_build >nul
echo OK

REM ---- 5) (MT5 setup wizard removed — configured from the Dashboard) --
if exist payload\wizard rmdir /S /Q payload\wizard

REM ---- 5) Compile Inno Setup ---------------------------------
echo.
echo [5/5] Compiling Atlas_Setup.exe...
"%ISCC_EXE%" "/DMyAppVersion=%ATLAS_VER%" atlas_setup.iss || exit /b 1

echo.
echo ============================================
echo  Build complete: dist\Atlas_Setup.exe
echo ============================================
dir /B dist\Atlas_Setup.exe
endlocal
exit /b 0

REM ============================================================
REM  Helpers
REM ============================================================

:ensure_iscc
REM Resolve ISCC_EXE. Order: explicit ISCC env > PATH > known folders >
REM registry > winget > Chocolatey > official silent download+install.
REM Verbose on purpose so a failing VPS shows exactly which step ran.
echo [setup] Locating Inno Setup 6 compiler ^(ISCC.exe^)...

REM (0) Explicit override via the ISCC environment variable.
if defined ISCC (
    if exist "%ISCC%" (
        set "ISCC_EXE=%ISCC%"
        echo [setup]   found via ISCC env: "%ISCC%"
        goto :eof
    )
)

REM (1) Already on PATH?
for /f "delims=" %%I in ('where iscc 2^>nul') do (
    set "ISCC_EXE=%%I"
    echo [setup]   found on PATH: %%I
    goto :eof
)

REM (2) Known install folders.
call :scan_known_paths
if defined ISCC_EXE ( echo [setup]   found: "%ISCC_EXE%" & goto :eof )

REM (3) Windows registry (Inno Setup 6 uninstall key -> InstallLocation).
call :scan_registry
if defined ISCC_EXE ( echo [setup]   found via registry: "%ISCC_EXE%" & goto :eof )

echo [setup] Inno Setup 6 not present - attempting automatic installation...

REM (4) winget (absent on most Windows Server SKUs; skipped if missing).
where winget >nul 2>nul
if not errorlevel 1 (
    echo [setup]   trying winget: JRSoftware.InnoSetup ...
    winget install -e --id JRSoftware.InnoSetup --scope machine --accept-source-agreements --accept-package-agreements --silent
    call :scan_known_paths
    if defined ISCC_EXE ( echo [setup]   installed via winget: "!ISCC_EXE!" & goto :eof )
    call :scan_registry
    if defined ISCC_EXE ( echo [setup]   installed via winget: "!ISCC_EXE!" & goto :eof )
) else (
    echo [setup]   winget not available - skipping.
)

REM (5) Chocolatey, if present.
where choco >nul 2>nul
if not errorlevel 1 (
    echo [setup]   trying Chocolatey: choco install innosetup ...
    choco install innosetup -y --no-progress
    call :scan_known_paths
    if defined ISCC_EXE ( echo [setup]   installed via Chocolatey: "!ISCC_EXE!" & goto :eof )
    call :scan_registry
    if defined ISCC_EXE ( echo [setup]   installed via Chocolatey: "!ISCC_EXE!" & goto :eof )
) else (
    echo [setup]   Chocolatey not available - skipping.
)

REM (6) Official silent download + install (works headless on a bare VPS).
set "_IS_EXE=%TEMP%\innosetup_latest.exe"
if exist "%_IS_EXE%" del /q "%_IS_EXE%" >nul 2>nul
echo [setup]   downloading Inno Setup 6 from jrsoftware.org ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try {[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]'Tls12,Tls11,Tls'} catch {}; try { Invoke-WebRequest 'https://jrsoftware.org/download.php/is.exe' -OutFile '%_IS_EXE%' -UseBasicParsing; exit 0 } catch { try { Invoke-WebRequest 'https://files.jrsoftware.org/is/6/innosetup-6.4.3.exe' -OutFile '%_IS_EXE%' -UseBasicParsing; exit 0 } catch { exit 1 } }"
if not exist "%_IS_EXE%" (
    echo [setup]   download failed ^(no network / blocked / TLS^).
    goto :eof
)
echo [setup]   installing Inno Setup 6 silently ^(waiting for completion^) ...
REM 'start /wait' guarantees ISCC.exe exists before we re-scan.
start "" /wait "%_IS_EXE%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /NOICONS /ALLUSERS
del "%_IS_EXE%" >nul 2>nul
call :scan_known_paths
if defined ISCC_EXE ( echo [setup]   installed via download: "%ISCC_EXE%" & goto :eof )
call :scan_registry
if defined ISCC_EXE ( echo [setup]   installed via download: "%ISCC_EXE%" & goto :eof )
echo [setup]   ISCC.exe still not found after install attempts.
goto :eof

REM ------------------------------------------------------------------
:scan_known_paths
REM Sets ISCC_EXE if ISCC.exe exists in any well-known location.
REM (These lines are intentionally NOT inside a () block so the (x86)
REM  in %ProgramFiles(x86)% cannot prematurely close a code block.)
call :check_iscc "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if defined ISCC_EXE goto :eof
call :check_iscc "%ProgramFiles%\Inno Setup 6\ISCC.exe"
if defined ISCC_EXE goto :eof
call :check_iscc "%ProgramW6432%\Inno Setup 6\ISCC.exe"
if defined ISCC_EXE goto :eof
call :check_iscc "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if defined ISCC_EXE goto :eof
call :check_iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if defined ISCC_EXE goto :eof
call :check_iscc "C:\Program Files\Inno Setup 6\ISCC.exe"
goto :eof

REM ------------------------------------------------------------------
:scan_registry
REM Reads InstallLocation from the Inno Setup 6 uninstall key (both the
REM native and WOW6432Node views, machine and per-user).
for %%K in (
    "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
    "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
    "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
) do (
    for /f "tokens=2,*" %%A in ('reg query %%K /v InstallLocation 2^>nul ^| find "InstallLocation"') do (
        call :check_iscc "%%~B\ISCC.exe"
        if defined ISCC_EXE goto :eof
    )
)
goto :eof

REM ------------------------------------------------------------------
:check_iscc
REM %1 = quoted candidate path to ISCC.exe. Sets ISCC_EXE if it exists.
if exist "%~1" set "ISCC_EXE=%~1"
goto :eof
