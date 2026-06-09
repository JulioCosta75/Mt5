@echo off
net stop AtlasBackend >nul 2>nul
net stop AtlasBridge  >nul 2>nul
echo Atlas services stopped.
timeout /t 2 >nul
