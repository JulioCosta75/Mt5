@echo off
REM -----------------------------------------------------------
REM Sr. Atlas backend launcher (Windows)
REM
REM Pre-requisites:
REM   1. Python 3.10-3.12 installed and on PATH
REM   2. Optional backend\.env (copy from .env.example if present)
REM -----------------------------------------------------------

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv || goto :error
)

call .venv\Scripts\activate.bat || goto :error

if not exist ".venv\.installed" (
    python -c "import uvicorn" >nul 2>nul
    if errorlevel 1 (
        echo Installing dependencies...
        pip install -r requirements.txt || goto :error
    ) else (
        echo Existing virtual environment looks ready — skipping pip install.
    )
    echo. > .venv\.installed
)

if not exist ".env" (
    echo [WARN] .env not found - backend will use defaults / mock mode.
    echo        Copy .env.example to .env if you need bridge or store settings.
)

echo Starting Sr. Atlas backend on http://127.0.0.1:8001 ...
python -m uvicorn server:app --host 127.0.0.1 --port 8001
goto :eof

:error
echo Backend startup failed.
pause
exit /b 1
