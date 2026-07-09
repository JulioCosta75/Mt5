@echo off
REM -----------------------------------------------------------
REM MT5 Bridge launcher (Windows)
REM
REM Pre-requisites:
REM   1. Python 3.10-3.12 installed and on PATH
REM   2. MT5 terminal installed, logged in, Algo Trading enabled
REM   3. `.env` file (optional) — copy from .env.example and edit. Without
REM      it the bridge still starts in UNCONFIGURED mode and serves /health.
REM -----------------------------------------------------------

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv || goto :error
)

call .venv\Scripts\activate.bat || goto :error

if not exist ".venv\.installed" (
    echo Installing dependencies...
    pip install -r requirements.txt || goto :error
    echo. > .venv\.installed
)

if not exist ".env" (
    echo [WARN] .env not found - starting in UNCONFIGURED mode.
    echo        The bridge will serve /health and report "unconfigured"
    echo        until you copy .env.example to .env and add your MT5 account
    echo        ^(or configure it from the dashboard^), then restart.
)

echo Starting MT5 bridge on port from .env (default 8002)...
python bridge_server.py
goto :eof

:error
echo Bridge startup failed.
pause
exit /b 1
