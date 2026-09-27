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
set "BUILD_REV=atlas2-free-pro-r2"

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
where node       >nul 2>nul || (echo [ERROR] Node.js is required to build the dashboard. Install Node 18+ and rerun. & exit /b 1)
where corepack   >nul 2>nul || (echo [ERROR] Corepack not found. Node.js 18+ includes Corepack. Install a current Node and rerun. & exit /b 1)

REM ---- Folders ----
if not exist payload mkdir payload
if not exist dist    mkdir dist

REM ---- 1) Download embedded Python 3.11 ----------------------
REM PowerShell Invoke-WebRequest is NOT the primary method: some Windows
REM images fail python.org with a TLS/credentials error. urllib (and curl)
REM succeed on the same URL. Never extract until the ZIP is verified.
set PYVER=3.11.9
set PYZIP=python-%PYVER%-embed-amd64.zip
set "PYURL=https://www.python.org/ftp/python/%PYVER%/%PYZIP%"
if not exist payload\python\python.exe (
    echo.
    echo [1/6] Downloading Python %PYVER% embeddable...
    echo       URL: %PYURL%
    call :download_python_zip "%PYURL%" "%PYZIP%" 5000000
    if errorlevel 1 (
        echo [ERROR] Could not download a verified Python embeddable ZIP.
        exit /b 1
    )
    if exist payload\python rmdir /S /Q payload\python
    mkdir payload\python
    call :extract_python_zip "%PYZIP%" payload\python
    if errorlevel 1 (
        echo [ERROR] Failed to extract %PYZIP%
        exit /b 1
    )
    if not exist payload\python\python.exe (
        echo [ERROR] ZIP extracted but payload\python\python.exe is missing. Refusing to continue.
        exit /b 1
    )
    del /F /Q "%PYZIP%" >nul 2>nul
    REM Enable site-packages in embeddable Python:
    powershell -NoProfile -Command ^
      "(Get-Content payload\python\python311._pth) -replace '#import site','import site' | Set-Content payload\python\python311._pth"
    echo OK
) else (
    echo [1/6] Python %PYVER% already in payload\python\ ^(skipping download^)
)

REM ---- 2) NSSM removed (Phase 2 — tray launcher, no Windows services) ----
echo [2/6] Skipping NSSM ^(Atlas runs as a tray app, not a Windows service^)
if exist payload\nssm.exe del /F /Q payload\nssm.exe >nul 2>nul
echo OK

REM ---- 3) Copy backend + bridge sources ----------------------
echo.
echo [3/6] Staging backend + bridge sources...
if exist payload\backend rmdir /S /Q payload\backend
if exist payload\bridge  rmdir /S /Q payload\bridge
REM Robocopy: code + requirements only — exclude dev junk (.venv, dbs, test logs).
robocopy ..\backend payload\backend /E /NFL /NDL /NJH /NJS /nc /ns /np ^
  /XD .venv __pycache__ .pytest_cache tests data .git ^
  /XF .env *.db *.pyc .installed
if errorlevel 8 (
    echo [ERROR] robocopy backend failed with errorlevel %ERRORLEVEL%
    exit /b 1
)
robocopy ..\mt5-bridge payload\bridge /E /NFL /NDL /NJH /NJS /nc /ns /np ^
  /XD .venv __pycache__ .pytest_cache .git ^
  /XF .env *.db *.pyc .installed _e2e* _login* *_evidence.txt
if errorlevel 8 (
    echo [ERROR] robocopy bridge failed with errorlevel %ERRORLEVEL%
    exit /b 1
)
REM Belt-and-braces: remove anything that still slipped through
if exist payload\bridge\.venv rmdir /S /Q payload\bridge\.venv
if exist payload\backend\.venv rmdir /S /Q payload\backend\.venv
if exist payload\backend\tests rmdir /S /Q payload\backend\tests
del /Q payload\bridge\_e2e*.txt 2>nul
del /Q payload\bridge\_login*.txt 2>nul
del /Q payload\bridge\*_evidence.txt 2>nul
del /Q payload\bridge\*.db 2>nul
del /Q payload\backend\*.db 2>nul
if exist payload\backend\.env del payload\backend\.env
if exist payload\bridge\.env  del payload\bridge\.env
echo OK

REM ---- 3b) Stamp build_info.json (version + UTC build time + git sha) ----
echo Stamping build_info.json ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$b=[ordered]@{version='%ATLAS_VER%';build='%GITSHA%';built_at=((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'));channel='release'}; $j=($b|ConvertTo-Json -Compress); [System.IO.File]::WriteAllText((Join-Path (Get-Location) 'payload\backend\build_info.json'), $j, (New-Object System.Text.UTF8Encoding $false))" || exit /b 1
echo OK

REM ---- 4) Build frontend via Corepack Yarn 1.22.22 (no npm fallback) ----
echo.
echo [4/6] Building frontend ^(clean rebuild, Corepack Yarn 1.22.22^)...
if exist payload\frontend_build rmdir /S /Q payload\frontend_build
pushd ..\frontend
if not exist yarn.lock (
    echo [ERROR] frontend\yarn.lock is missing.
    echo         A clean clone needs the committed Yarn 1 lockfile. Do not use npm ci.
    popd
    exit /b 1
)
if not exist package.json (
    echo [ERROR] frontend\package.json is missing.
    popd
    exit /b 1
)
echo [frontend] Corepack Yarn:
call corepack yarn --version
if errorlevel 1 (
    echo [ERROR] corepack yarn failed. Node 18+ with Corepack is required ^(packageManager yarn@1.22.22^).
    popd
    exit /b 1
)
REM Yarn classic 1.x is the supported resolver for date-fns@4.1.0 + react-day-picker@8.10.1
REM (npm 7+ peer-dep conflict). Do not --force / --legacy-peer-deps / npm ci.
call corepack yarn install --frozen-lockfile
if errorlevel 1 (
    echo [ERROR] yarn install --frozen-lockfile failed. Lockfile and package.json are out of sync, or the registry is unreachable.
    popd
    exit /b 1
)
REM Same-origin: dashboard is served by the backend, so no external API base.
set "REACT_APP_BACKEND_URL="
call corepack yarn build
if errorlevel 1 (
    echo [ERROR] corepack yarn build failed.
    popd
    exit /b 1
)
popd
if not exist ..\frontend\build\index.html (
    echo [ERROR] frontend\build\index.html missing after yarn build.
    exit /b 1
)
xcopy /E /I /Y ..\frontend\build payload\frontend_build >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy frontend\build to payload\frontend_build
    exit /b 1
)
echo OK

REM ---- 5) (MT5 setup wizard removed — configured from the Dashboard) --
if exist payload\wizard rmdir /S /Q payload\wizard

REM ---- 5) Compile Inno Setup ---------------------------------
echo.
echo [5/5] Compiling Atlas_Setup.exe...
REM Unsigned on purpose — founder applies the Microsoft signature after review.
"%ISCC_EXE%" "/DMyAppVersion=%ATLAS_VER%" atlas_setup.iss || exit /b 1

echo.
echo ============================================
echo  Build complete: dist\Atlas_Setup.exe
echo  (unsigned — do not distribute until signed)
echo ============================================
dir dist\Atlas_Setup.exe
echo.
echo SHA-256:
certutil -hashfile dist\Atlas_Setup.exe SHA256
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

REM ------------------------------------------------------------------
:download_python_zip
REM %1 = URL  %2 = dest ZIP  %3 = min bytes
set "_DL_URL=%~1"
set "_DL_OUT=%~2"
set "_DL_MIN=%~3"
if not defined _DL_MIN set "_DL_MIN=5000000"
if exist "%_DL_OUT%" del /F /Q "%_DL_OUT%" >nul 2>nul
set "PY_LAUNCH="
where py >nul 2>nul
if not errorlevel 1 set "PY_LAUNCH=py -3"
if not defined PY_LAUNCH (
    where python >nul 2>nul
    if not errorlevel 1 set "PY_LAUNCH=python"
)
if not defined PY_LAUNCH (
    where python3 >nul 2>nul
    if not errorlevel 1 set "PY_LAUNCH=python3"
)
if defined PY_LAUNCH (
    echo [download] Python found: %PY_LAUNCH%  ^(urllib, then curl, then IWR^)
    %PY_LAUNCH% "%~dp0scripts\download_url.py" --min-bytes %_DL_MIN% --expect-member python.exe --timeout 90 "%_DL_URL%" "%_DL_OUT%"
    if not errorlevel 1 exit /b 0
    echo [download] Python helper failed; trying curl/IWR from this script...
)
call :download_without_python "%_DL_URL%" "%_DL_OUT%" %_DL_MIN%
exit /b %ERRORLEVEL%

REM ------------------------------------------------------------------
:download_without_python
REM %1 URL  %2 dest  %3 min bytes
set "_NU_URL=%~1"
set "_NU_OUT=%~2"
set "_NU_MIN=%~3"
where curl >nul 2>nul
if not errorlevel 1 (
    echo [download] trying curl.exe ...
    curl.exe -L --fail --retry 3 --retry-delay 2 --connect-timeout 30 -A "Atlas-installer-build/1.0" -o "%_NU_OUT%" "%_NU_URL%"
    if not errorlevel 1 (
        call :verify_zip_nopy "%_NU_OUT%" %_NU_MIN%
        if not errorlevel 1 exit /b 0
        echo [download] curl wrote a file that failed ZIP verification.
        del /F /Q "%_NU_OUT%" >nul 2>nul
    ) else (
        echo [download] curl failed.
    )
) else (
    echo [download] curl not on PATH.
)
echo [download] trying PowerShell Invoke-WebRequest ^(last resort^) ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}; Invoke-WebRequest -Uri '%_NU_URL%' -OutFile '%_NU_OUT%' -UseBasicParsing -TimeoutSec 90 -UserAgent 'Atlas-installer-build/1.0'"
if errorlevel 1 (
    echo [download] Invoke-WebRequest failed.
    del /F /Q "%_NU_OUT%" >nul 2>nul
    exit /b 1
)
call :verify_zip_nopy "%_NU_OUT%" %_NU_MIN%
if errorlevel 1 (
    echo [download] IWR wrote a file that failed ZIP verification ^(often an HTML error page^).
    del /F /Q "%_NU_OUT%" >nul 2>nul
    exit /b 1
)
exit /b 0

REM ------------------------------------------------------------------
:verify_zip_nopy
REM %1 file  %2 min bytes. Uses file size + tar listing when Python is absent.
set "_ZF=%~1"
set "_ZMIN=%~2"
if not exist "%_ZF%" (
    echo [ERROR] expected ZIP missing: %_ZF%
    exit /b 1
)
for %%A in ("%_ZF%") do set "_ZSIZE=%%~zA"
if !_ZSIZE! LSS !_ZMIN! (
    echo [ERROR] %_ZF% is !_ZSIZE! bytes; need at least !_ZMIN!. Refusing to extract.
    exit /b 1
)
tar -tf "%_ZF%" 2>nul | findstr /I /C:"python.exe" >nul
if errorlevel 1 (
    echo [ERROR] %_ZF% is not a ZIP containing python.exe. Refusing to extract.
    exit /b 1
)
echo [download] verified %_ZF% ^(!_ZSIZE! bytes, contains python.exe^)
exit /b 0

REM ------------------------------------------------------------------
:extract_python_zip
REM %1 zip  %2 dest dir
set "_EX_ZIP=%~1"
set "_EX_DIR=%~2"
set "PY_LAUNCH="
where py >nul 2>nul
if not errorlevel 1 set "PY_LAUNCH=py -3"
if not defined PY_LAUNCH (
    where python >nul 2>nul
    if not errorlevel 1 set "PY_LAUNCH=python"
)
if not defined PY_LAUNCH (
    where python3 >nul 2>nul
    if not errorlevel 1 set "PY_LAUNCH=python3"
)
if defined PY_LAUNCH (
    %PY_LAUNCH% -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "%_EX_ZIP%" "%_EX_DIR%"
    if not errorlevel 1 exit /b 0
    echo [extract] Python zipfile failed; trying Expand-Archive.
)
powershell -NoProfile -Command "Expand-Archive -Force '%_EX_ZIP%' '%_EX_DIR%'"
exit /b %ERRORLEVEL%
