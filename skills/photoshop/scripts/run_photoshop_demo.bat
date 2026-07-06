@echo off
setlocal

if "%HERMES_HOME%"=="" set "HERMES_HOME=%LOCALAPPDATA%\hermes"

set "PY=%HERMES_HOME%\hermes-agent\venv\Scripts\python.exe"
set "SCRIPT=%HERMES_HOME%\skills\photoshop\scripts\photoshop_demo_presets.py"

if not exist "%PY%" (
  echo [ERROR] Python with pywin32 not found: %PY%
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo [ERROR] Photoshop demo script not found: %SCRIPT%
  exit /b 3
)

"%PY%" "%SCRIPT%" %*
exit /b %ERRORLEVEL%
