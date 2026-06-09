@echo off
REM ============================================================
REM  Installs backend + bridge Python dependencies into the
REM  embedded Python's site-packages.
REM ============================================================
setlocal
set ATLAS_DIR=%~dp0..
set PYTHON=%ATLAS_DIR%\python\python.exe
set PIP=%PYTHON% -m pip

echo Installing backend dependencies...
%PIP% install --no-warn-script-location --disable-pip-version-check ^
    fastapi==0.110.1 uvicorn==0.25.0 httpx pydantic python-dotenv ^
    "starlette<0.40" "anyio<5" "click<9" || goto :err

echo Installing bridge dependencies (incl. MetaTrader5)...
%PIP% install --no-warn-script-location --disable-pip-version-check ^
    MetaTrader5==5.0.45 APScheduler>=3.10 || goto :err

echo All dependencies installed.
exit /b 0

:err
echo [ERROR] dependency installation failed.
exit /b 1
endlocal
