@echo off
REM ============================================================
REM  configure_mt5.bat  --  collect MT5 credentials and write the
REM  .env files the Atlas services read (bridge + backend), so the
REM  bridge connects to MetaTrader 5 right after installation.
REM
REM  Interactive by default. For a silent/automated install pass
REM  values through:
REM      configure_mt5.bat --login 12345 --password *** --server Broker-Live
REM  or the ATLAS_MT5_LOGIN / ATLAS_MT5_PASSWORD / ATLAS_MT5_SERVER
REM  environment variables, or  --answers answers.json --non-interactive
REM ============================================================
setlocal
call "%~dp0_detect_env.bat"
if errorlevel 1 (
    echo [ERROR] Environment detection failed - cannot configure MT5.
    exit /b 1
)

"%PYTHON%" "%~dp0configure_atlas.py" ^
    --backend-dir "%BACKEND_DIR%" ^
    --bridge-dir "%BRIDGE_DIR%" ^
    --data-dir "%DATA_DIR%" %*
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
