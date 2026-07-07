@echo off
REM ============================================================
REM  Atlas - one-click installer (fresh git clone friendly)
REM  ----------------------------------------------------------
REM  1. Installs Python dependencies
REM  2. Registers AtlasBridge + AtlasBackend Windows services
REM  3. Starts them and opens the dashboard
REM
REM  Right-click this file  ->  "Run as administrator".
REM ============================================================
setlocal
cd /d "%~dp0"
title Atlas Installer

net session >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Administrator rights are required.
    echo         Right-click install.bat and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   Atlas installation
echo ============================================================
echo.

call "scripts\install_services.bat"
if errorlevel 1 (
    echo.
    echo [FAILED] Installation did not complete. See the messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Starting Atlas
echo ============================================================
call "scripts\start_atlas.bat"

echo.
echo ============================================================
echo   Installation complete.
echo   Dashboard : http://localhost:8001/
echo   Health    : http://localhost:8001/healthcheck
echo ============================================================
echo.
echo   To connect your MetaTrader 5 account, copy
echo     mt5-bridge\.env.example  ->  mt5-bridge\.env
echo   fill in your broker credentials, then run:
echo     scripts\stop_atlas.bat  ^&^&  scripts\start_atlas.bat
echo.
pause
endlocal
