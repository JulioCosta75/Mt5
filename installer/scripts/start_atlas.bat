@echo off
REM ============================================================
REM  Compatibility entry: Start Atlas as the tray app (no services).
REM ============================================================
call "%~dp0start_atlas_app.bat"
exit /b %ERRORLEVEL%
