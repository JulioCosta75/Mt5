@echo off
REM ============================================================
REM  Atlas - one-click installer (fresh git clone / dev layout)
REM  ----------------------------------------------------------
REM  1. Installs Python dependencies
REM  2. Configures MT5 (optional prompts)
REM  3. Starts the tray launcher (no Windows services / no admin)
REM ============================================================
setlocal
cd /d "%~dp0"
title Atlas Installer

echo ============================================================
echo   Atlas installation (tray app — no Administrator needed)
echo ============================================================
echo.

call "scripts\_detect_env.bat"
if errorlevel 1 (
    echo [FAILED] Environment detection failed.
    pause
    exit /b 1
)

call "scripts\install_deps.bat"
if errorlevel 1 (
    echo [FAILED] Dependency install failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Connect your MetaTrader 5 account
echo ============================================================
call "scripts\configure_mt5.bat"
if errorlevel 1 (
    echo.
    echo [WARN] MT5 was not configured. The dashboard will still start,
    echo        but the bridge stays offline until you configure it from
    echo        the dashboard Settings page or by re-running:
    echo            scripts\configure_mt5.bat
    echo.
)

echo.
echo ============================================================
echo   Starting Atlas ^(tray launcher^)
echo ============================================================
call "scripts\start_atlas_app.bat"

echo.
echo ============================================================
echo   Installation complete.
echo   Dashboard : http://127.0.0.1:8001/
echo   Health    : http://127.0.0.1:8001/healthcheck
echo   Tip       : look for the Atlas icon in the system tray.
echo ============================================================
echo.
pause
endlocal
