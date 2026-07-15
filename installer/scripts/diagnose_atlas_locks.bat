@echo off
REM ============================================================
REM  diagnose_atlas_locks.bat
REM  Identifies which process blocks Atlas install folders.
REM  Run as Administrator for complete service/process data.
REM ============================================================
setlocal

set "SCRIPTS_DIR=%~dp0"
for %%I in ("%SCRIPTS_DIR%..") do set "ATLAS_ROOT=%%~fI"

set "TARGET=%ATLAS_ROOT%\backend"
if not "%~1"=="" set "TARGET=%~1"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPTS_DIR%diagnose_atlas_locks.ps1" -AtlasRoot "%ATLAS_ROOT%" -TargetPath "%TARGET%"
exit /b %ERRORLEVEL%
