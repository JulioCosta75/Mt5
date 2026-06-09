@echo off
REM Starts both Atlas services (bridge first, backend second).
net start AtlasBridge  || echo (AtlasBridge already running or failed — see logs)
net start AtlasBackend || echo (AtlasBackend already running or failed — see logs)
echo.
echo Dashboard: http://localhost:8001/
echo Health:    http://localhost:8001/healthcheck
timeout /t 3 >nul
