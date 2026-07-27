@echo off
REM ============================================================
REM  Bootstraps pip inside the detected Python distribution.
REM  (Windows embeddable Python does NOT ship with pip.)
REM ============================================================
setlocal

call "%~dp0_detect_env.bat"
if errorlevel 1 exit /b 1

if not exist "%PYTHON%" (
    echo [ERROR] Python runtime missing: %PYTHON%
    exit /b 1
)

"%PYTHON%" -m pip --version >nul 2>nul
if not errorlevel 1 (
    echo pip already available.
    endlocal & exit /b 0
)

echo Downloading get-pip.py ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py' -UseBasicParsing" || (endlocal & exit /b 1)

"%PYTHON%" "%TEMP%\get-pip.py" --no-warn-script-location || (endlocal & exit /b 1)
del "%TEMP%\get-pip.py" >nul 2>nul
echo pip ready.
endlocal
exit /b 0
