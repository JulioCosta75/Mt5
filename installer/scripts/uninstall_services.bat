@echo off
REM ============================================================
REM  Removes the Atlas Windows services and releases file locks.
REM  Called from the Inno Setup uninstaller ([UninstallRun]) and
REM  available for manual cleanup.
REM ============================================================
setlocal

call "%~dp0release_atlas_locks.bat"
if errorlevel 1 (
    echo [WARN] release_atlas_locks.bat reported an error — continuing.
)

echo Atlas services removed.
endlocal
exit /b 0
