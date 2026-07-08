@echo off
setlocal

set "HERMES_HOME=%~dp0"
if "%HERMES_HOME:~-1%"=="\" set "HERMES_HOME=%HERMES_HOME:~0,-1%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%HERMES_HOME%\tools\portable_setup.ps1" -HermesHome "%HERMES_HOME%"
if errorlevel 1 goto failed

pause
exit /b 0

:failed
echo.
echo [ERROR] Hermes portable setup failed.
pause
exit /b 1
