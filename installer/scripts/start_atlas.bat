@echo off
REM ============================================================
REM  Starts the Atlas services (bridge first, backend second).
REM  Retries on first-boot NSSM I/O races (error 1051), and only
REM  opens the browser once AtlasBackend is confirmed Running.
REM ============================================================
setlocal EnableExtensions EnableDelayedExpansion
title Atlas - Start

REM ---- Make sure the services actually exist -----------------
sc query AtlasBackend >nul 2>nul
if errorlevel 1 (
    echo [ERROR] The AtlasBackend service is not installed yet.
    echo         Run  install_services.bat  ^(as Administrator^) first,
    echo         or use  install.bat  in the installer folder.
    call :notify "Atlas Backend is not installed yet. Run the installer again, or run install_services.bat as Administrator."
    exit /b 1
)

REM NSSM AppStdout/AppStderr need the logs folder to exist; creating
REM it here avoids a common first-start "Error setting up I/O filehandles".
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs" >nul 2>nul

echo Starting Atlas services ...
call :start_with_retry AtlasBridge  5 2
set "BRIDGE_OK=!ERRORLEVEL!"
call :start_with_retry AtlasBackend 5 2
set "BACKEND_OK=!ERRORLEVEL!"

echo.
if "!BACKEND_OK!"=="0" (
    echo Dashboard: http://127.0.0.1:8001/
    echo Health:    http://127.0.0.1:8001/healthcheck
    timeout /t 2 >nul
    start "" "http://127.0.0.1:8001/"
    endlocal & exit /b 0
)

echo [ERROR] AtlasBackend did not reach Running state.
echo         Check logs\backend.err.log and try Start Atlas again.
if not "!BRIDGE_OK!"=="0" (
    echo         AtlasBridge also failed — see logs\bridge.err.log
)
call :notify "Atlas Backend failed to start after several attempts. Do not refresh the browser yet. Check logs\backend.err.log, then use Start Atlas from the Start Menu."
endlocal & exit /b 1

REM ------------------------------------------------------------
REM :start_with_retry SERVICE ATTEMPTS DELAY_SECONDS
REM Returns 0 if service is Running, 1 otherwise.
REM ------------------------------------------------------------
:start_with_retry
set "_SVC=%~1"
set "_MAX=%~2"
set "_DELAY=%~3"
if "%_MAX%"=="" set "_MAX=5"
if "%_DELAY%"=="" set "_DELAY=2"

for /L %%I in (1,1,%_MAX%) do (
    call :is_running "%_SVC%"
    if not errorlevel 1 (
        echo   %_SVC%  running.
        exit /b 0
    )
    echo   %_SVC%  start attempt %%I/%_MAX% ...
    net start "%_SVC%" >nul 2>nul
    timeout /t %_DELAY% /nobreak >nul
    call :is_running "%_SVC%"
    if not errorlevel 1 (
        echo   %_SVC%  started.
        exit /b 0
    )
)
echo   %_SVC%  FAILED to start after %_MAX% attempts.
exit /b 1

REM ------------------------------------------------------------
REM :is_running SERVICE  — exit 0 if STATE is RUNNING
REM ------------------------------------------------------------
:is_running
sc query "%~1" | findstr /I /C:"RUNNING" >nul 2>nul
exit /b %ERRORLEVEL%

REM ------------------------------------------------------------
REM :notify MESSAGE — visible even when launched runhidden by Inno
REM ------------------------------------------------------------
:notify
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('%~1','Atlas',0,'Warning') | Out-Null" >nul 2>nul
exit /b 0
