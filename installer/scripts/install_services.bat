@echo off
REM ============================================================
REM  Install Atlas Backend + Atlas Bridge as Windows Services
REM  (via NSSM).  Works from a production install OR a fresh
REM  git clone.  Run as Administrator.
REM
REM  No manual steps required:
REM    * NSSM is bundled (installer\nssm.exe) with a download
REM      fallback.
REM    * Python is auto-detected (embedded or system).
REM    * Dependencies are installed automatically.
REM ============================================================
setlocal
title Atlas - Install Windows Services

REM ---- Require Administrator ---------------------------------
net session >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Administrator rights are required.
    echo         Right-click this file - or install.bat - and pick
    echo         "Run as administrator", then try again.
    exit /b 1
)

call "%~dp0_detect_env.bat"
if errorlevel 1 (
    echo [ERROR] Environment detection failed - see messages above.
    exit /b 1
)

echo ============================================================
echo  Atlas service installer
echo ------------------------------------------------------------
echo   Root        : %ATLAS_ROOT%
echo   Backend     : %BACKEND_DIR%
echo   Bridge      : %BRIDGE_DIR%
echo   Frontend    : %FRONTEND_BUILD%
echo   Python      : %PYTHON%  (%PY_MODE%)
echo   NSSM        : %NSSM%
echo ============================================================

if not exist "%BACKEND_DIR%\server.py" (
    echo [ERROR] Backend not found at %BACKEND_DIR%\server.py
    exit /b 1
)
if not exist "%FRONTEND_BUILD%\index.html" (
    echo [WARN] Frontend build missing at %FRONTEND_BUILD%\index.html
    echo        The dashboard will not render until you build it:
    echo            cd frontend  ^&^&  yarn install  ^&^&  yarn build
    echo        Continuing with service installation ...
)

REM ---- Install Python dependencies ---------------------------
echo.
echo Installing Python dependencies ...
call "%~dp0install_deps.bat"
if errorlevel 1 (
    echo [ERROR] Dependency installation failed - aborting.
    exit /b 1
)

REM ---- AtlasBridge service -----------------------------------
echo.
echo Installing service: AtlasBridge
"%NSSM%" stop    AtlasBridge >nul 2>nul
"%NSSM%" remove  AtlasBridge confirm >nul 2>nul
REM Use the same uvicorn module pattern as AtlasBackend (reliable under NSSM).
"%NSSM%" install AtlasBridge "%PYTHON%" "-m" "uvicorn" "bridge_server:app" "--host" "127.0.0.1" "--port" "8002"
"%NSSM%" set AtlasBridge AppDirectory       "%BRIDGE_DIR%"
"%NSSM%" set AtlasBridge AppStdout          "%LOGS_DIR%\bridge.out.log"
"%NSSM%" set AtlasBridge AppStderr          "%LOGS_DIR%\bridge.err.log"
"%NSSM%" set AtlasBridge AppRotateFiles     1
"%NSSM%" set AtlasBridge AppRotateOnline    1
"%NSSM%" set AtlasBridge AppRotateBytes     10485760
"%NSSM%" set AtlasBridge AppThrottle        30000
"%NSSM%" set AtlasBridge DisplayName        "Atlas MT5 Bridge"
"%NSSM%" set AtlasBridge Description         "Bridges the local MetaTrader 5 terminal to the Atlas backend."
"%NSSM%" set AtlasBridge Start              SERVICE_AUTO_START

REM ---- AtlasBackend service ----------------------------------
REM  NOTE: intentionally NOT dependent on AtlasBridge so the
REM  dashboard + API always come up, even before MT5 is set up.
echo Installing service: AtlasBackend
"%NSSM%" stop    AtlasBackend >nul 2>nul
"%NSSM%" remove  AtlasBackend confirm >nul 2>nul
"%NSSM%" install AtlasBackend "%PYTHON%" "-m" "uvicorn" "server:app" "--host" "127.0.0.1" "--port" "8001"
"%NSSM%" set AtlasBackend AppDirectory      "%BACKEND_DIR%"
"%NSSM%" set AtlasBackend AppStdout         "%LOGS_DIR%\backend.out.log"
"%NSSM%" set AtlasBackend AppStderr         "%LOGS_DIR%\backend.err.log"
"%NSSM%" set AtlasBackend AppRotateFiles    1
"%NSSM%" set AtlasBackend AppRotateOnline   1
"%NSSM%" set AtlasBackend AppRotateBytes    10485760
"%NSSM%" set AtlasBackend AppThrottle       15000
"%NSSM%" set AtlasBackend DisplayName       "Atlas Backend"
"%NSSM%" set AtlasBackend Description        "Atlas API + dashboard server."
"%NSSM%" set AtlasBackend Start             SERVICE_AUTO_START
"%NSSM%" set AtlasBackend AppEnvironmentExtra "ATLAS_STORE=sqlite" "ATLAS_SQLITE_PATH=%DATA_DIR%\atlas.db" "SERVE_FRONTEND=true" "FRONTEND_BUILD=%FRONTEND_BUILD%"

echo.
echo ============================================================
echo  [OK] Services installed successfully.
echo       Start them now:  scripts\start_atlas.bat
echo       (or)             net start AtlasBackend
echo       Dashboard:       http://localhost:8001/
echo ============================================================
endlocal
exit /b 0
