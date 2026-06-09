@echo off
REM ============================================================
REM  Install Atlas Backend + Atlas Bridge as Windows Services
REM  via NSSM. Run as administrator.
REM ============================================================
setlocal
set ATLAS_DIR=%~dp0..
set NSSM=%ATLAS_DIR%\nssm.exe
set PYTHON=%ATLAS_DIR%\python\python.exe

if not exist "%NSSM%" (
    echo [ERROR] nssm.exe missing at %NSSM%
    exit /b 1
)

REM ---- Atlas Bridge service ----------------------------------
echo Installing service: AtlasBridge
"%NSSM%" stop    AtlasBridge >nul 2>nul
"%NSSM%" remove  AtlasBridge confirm >nul 2>nul

"%NSSM%" install AtlasBridge "%PYTHON%" "%ATLAS_DIR%\bridge\bridge_server.py"
"%NSSM%" set AtlasBridge AppDirectory       "%ATLAS_DIR%\bridge"
"%NSSM%" set AtlasBridge AppStdout          "%ATLAS_DIR%\logs\bridge.out.log"
"%NSSM%" set AtlasBridge AppStderr          "%ATLAS_DIR%\logs\bridge.err.log"
"%NSSM%" set AtlasBridge AppRotateFiles     1
"%NSSM%" set AtlasBridge AppRotateOnline    1
"%NSSM%" set AtlasBridge AppRotateBytes     10485760
"%NSSM%" set AtlasBridge DisplayName        "Atlas MT5 Bridge"
"%NSSM%" set AtlasBridge Description        "Bridges the local MetaTrader 5 terminal to the Atlas backend."
"%NSSM%" set AtlasBridge Start              SERVICE_AUTO_START

REM ---- Atlas Backend service ---------------------------------
echo Installing service: AtlasBackend
"%NSSM%" stop    AtlasBackend >nul 2>nul
"%NSSM%" remove  AtlasBackend confirm >nul 2>nul

"%NSSM%" install AtlasBackend "%PYTHON%" "-m" "uvicorn" "server:app" "--host" "127.0.0.1" "--port" "8001"
"%NSSM%" set AtlasBackend AppDirectory       "%ATLAS_DIR%\backend"
"%NSSM%" set AtlasBackend AppStdout          "%ATLAS_DIR%\logs\backend.out.log"
"%NSSM%" set AtlasBackend AppStderr          "%ATLAS_DIR%\logs\backend.err.log"
"%NSSM%" set AtlasBackend AppRotateFiles     1
"%NSSM%" set AtlasBackend AppRotateOnline    1
"%NSSM%" set AtlasBackend AppRotateBytes     10485760
"%NSSM%" set AtlasBackend DisplayName        "Atlas Backend"
"%NSSM%" set AtlasBackend Description        "Atlas API + dashboard server."
"%NSSM%" set AtlasBackend Start              SERVICE_AUTO_START
"%NSSM%" set AtlasBackend DependOnService    AtlasBridge

REM ---- Inject required env vars ------------------------------
REM Backend reads its own .env via python-dotenv, but uvicorn-as-service
REM doesn't inherit shell env; set the critical ones at the service level:
"%NSSM%" set AtlasBackend AppEnvironmentExtra ^
    ATLAS_STORE=sqlite ^
    ATLAS_SQLITE_PATH=%ATLAS_DIR%\data\atlas.db ^
    SERVE_FRONTEND=true ^
    FRONTEND_BUILD=%ATLAS_DIR%\frontend_build

echo.
echo Services installed. To start: net start AtlasBridge ^&^& net start AtlasBackend
echo (or use scripts\start_atlas.bat)
endlocal
