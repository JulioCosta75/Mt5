@echo off
REM ============================================================
REM  Atlas installer — build.bat
REM  Run this on a Windows machine with Inno Setup 6 installed.
REM  Produces:  dist\Atlas_Setup.exe
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo === Atlas installer builder ===
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
where iscc >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Inno Setup 6 not found on PATH.
    echo         Install from https://jrsoftware.org/isdl.php and add ISCC.exe to PATH,
    echo         or set ISCC=path\to\ISCC.exe and rerun.
    exit /b 1
)

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

REM ---- 5) Build the wizard (PyInstaller) ---------------------
echo.
echo [5/6] Building Atlas Wizard.exe (PyInstaller)...
if not exist payload\wizard mkdir payload\wizard
pushd wizard
if not exist .venv (
    py -3.11 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q pyinstaller requests || exit /b 1
pyinstaller --noconfirm --clean --windowed --onefile ^
    --name "Atlas Wizard" --icon ..\icons\atlas.ico atlas_wizard.py
copy /Y "dist\Atlas Wizard.exe" "..\payload\wizard\Atlas Wizard.exe"
popd
echo OK

REM ---- 6) Compile Inno Setup ---------------------------------
echo.
echo [6/6] Compiling Atlas_Setup.exe...
iscc "/DMyAppVersion=%ATLAS_VER%" atlas_setup.iss || exit /b 1

echo.
echo ============================================
echo  Build complete: dist\Atlas_Setup.exe
echo ============================================
dir /B dist\Atlas_Setup.exe
endlocal
