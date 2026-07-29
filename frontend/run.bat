@echo off
REM -----------------------------------------------------------
REM Sr. Atlas frontend launcher (Windows)
REM
REM Pre-requisites:
REM   1. Node.js LTS installed and on PATH (npm available)
REM   2. Optional frontend\.env with REACT_APP_BACKEND_URL
REM      (default expected: http://127.0.0.1:8001)
REM -----------------------------------------------------------

cd /d "%~dp0"

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js LTS and reopen this window.
    goto :error
)

if not exist "node_modules\" (
    echo Installing frontend dependencies...
    call npm install || goto :error
)

if not exist ".env" (
    echo [WARN] .env not found.
    echo        Create frontend\.env with:
    echo          REACT_APP_BACKEND_URL=http://127.0.0.1:8001
    echo        then restart this launcher.
)

echo Starting Sr. Atlas frontend (npm start / craco) on http://localhost:3000 ...
call npm start
goto :eof

:error
echo Frontend startup failed.
pause
exit /b 1
