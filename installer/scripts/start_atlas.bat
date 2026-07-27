@echo off
REM ============================================================
REM  Starts the Atlas services (bridge first, backend second).
REM ============================================================
setlocal
title Atlas - Start

REM ---- Make sure the services actually exist -----------------
sc query AtlasBackend >nul 2>nul
if errorlevel 1 (
    echo [ERROR] The AtlasBackend service is not installed yet.
    echo         Run  install_services.bat  ^(as Administrator^) first,
    echo         or use  install.bat  in the installer folder.
    exit /b 1
)

echo Starting Atlas services ...
net start AtlasBridge  >nul 2>nul && (echo   AtlasBridge  started.) || echo   AtlasBridge  not started ^(configure MT5 first - see logs\bridge.err.log^).
net start AtlasBackend >nul 2>nul && (echo   AtlasBackend started.) || echo   AtlasBackend already running or failed ^(see logs\backend.err.log^).

echo.
echo Dashboard: http://localhost:8001/
echo Health:    http://localhost:8001/healthcheck
timeout /t 3 >nul
start "" "http://localhost:8001/"
endlocal
