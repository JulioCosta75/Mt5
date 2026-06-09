@echo off
REM ============================================================
REM  Bootstraps pip inside the embedded Python distribution.
REM  (Embeddable Python does NOT ship with pip.)
REM ============================================================
setlocal
set ATLAS_DIR=%~dp0..
set PYTHON=%ATLAS_DIR%\python\python.exe

if not exist "%PYTHON%" (
    echo [ERROR] Python runtime missing: %PYTHON%
    exit /b 1
)

if exist "%ATLAS_DIR%\python\Scripts\pip.exe" (
    echo pip already installed.
    exit /b 0
)

echo Downloading get-pip.py...
powershell -NoProfile -Command ^
  "Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py'" || exit /b 1

"%PYTHON%" "%TEMP%\get-pip.py" --no-warn-script-location || exit /b 1
del "%TEMP%\get-pip.py"
echo pip ready.
endlocal
