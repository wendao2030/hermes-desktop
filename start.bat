@echo off
setlocal

set "HERMES_HOME=%~dp0"
if "%HERMES_HOME:~-1%"=="\" set "HERMES_HOME=%HERMES_HOME:~0,-1%"

set "PYTHONW=%HERMES_HOME%\runtime\python311\pythonw.exe"
set "LAUNCHER=%HERMES_HOME%\tools\launch_hermes.py"

if not exist "%PYTHONW%" goto missing_runtime

if not exist "%LAUNCHER%" goto missing_launcher

start "" "%PYTHONW%" "%LAUNCHER%"
exit /b 0

:missing_runtime
echo [ERROR] Private Python runtime was not found:
echo   %PYTHONW%
echo.
echo Please copy a complete Hermes folder, including runtime\python311.
pause
exit /b 1

:missing_launcher
echo [ERROR] Hermes launcher was not found:
echo   %LAUNCHER%
pause
exit /b 1
