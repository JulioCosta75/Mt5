@echo off
setlocal
set NSSM=%~dp0..\nssm.exe
"%NSSM%" stop   AtlasBackend >nul 2>nul
"%NSSM%" remove AtlasBackend confirm
"%NSSM%" stop   AtlasBridge  >nul 2>nul
"%NSSM%" remove AtlasBridge  confirm
echo Atlas services removed.
endlocal
