@echo off
REM ============================================================
REM  Installs the backend + bridge Python dependencies into the
REM  detected Python runtime (embedded or system).
REM  Safe to run multiple times (pip is idempotent).
REM ============================================================
setlocal

call "%~dp0_detect_env.bat"
if errorlevel 1 exit /b 1

REM ---- Ensure pip is available (embedded Python ships without) ----
"%PYTHON%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo Bootstrapping pip ...
    call "%~dp0bootstrap_pip.bat"
    if errorlevel 1 (
        echo [ERROR] Could not bootstrap pip.
        exit /b 1
    )
)

echo Upgrading pip ...
"%PYTHON%" -m pip install --disable-pip-version-check --no-warn-script-location --upgrade pip >nul 2>nul

echo Installing backend dependencies ...
"%PYTHON%" -m pip install --no-warn-script-location --disable-pip-version-check ^
    fastapi==0.110.1 uvicorn==0.25.0 httpx pydantic python-dotenv ^
    "starlette<0.40" "anyio<5" "click<9" || goto :err

echo Installing bridge dependencies (incl. MetaTrader5) ...
"%PYTHON%" -m pip install --no-warn-script-location --disable-pip-version-check ^
    "MetaTrader5>=5.0.4732" "APScheduler>=3.10" || goto :err

echo All dependencies installed.
endlocal
exit /b 0

:err
echo [ERROR] dependency installation failed.
endlocal
exit /b 1
