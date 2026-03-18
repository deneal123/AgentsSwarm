@echo off

setlocal EnableDelayedExpansion
pushd "%~dp0\..\.." || exit /b 1
set "PROJECT_ROOT=%CD%"
if defined PYTHONPATH (
  set "PYTHONPATH=%PROJECT_ROOT%/pushi;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%PROJECT_ROOT%/pushi"
)
set "PATH=%PATH%"

for /f "delims=" %%A in ('echo prompt $E ^| cmd') do set "ESC=%%A"
set "RED=!ESC![31m"
set "GREEN=!ESC![32m"
set "YELLOW=!ESC![33m"
set "BLUE=!ESC![34m"
set "RESET=!ESC![0m"

set "MODE="
set "RUNMODE_SOURCE="

call :detect_mode
call :echoinfo "RUN_MODE=!RUN_MODE! (source: !RUNMODE_SOURCE!)"
call :echoinfo "chosen MODE=!MODE!"

if /I "%MODE%"=="poetry" (
  poetry run python -m pytest --maxfail=1 -v %*
) else if /I "%MODE%"=="legacy" (
  call :activate_venv
  python -m pytest --maxfail=1 -v %*
) else (
  python -m pytest --maxfail=1 -v %*
)

popd
endlocal
exit /b %ERRORLEVEL%

:detect_mode
if defined RUN_MODE (
  set "MODE=!RUN_MODE!"
  set "RUNMODE_SOURCE=environment"
  goto :eof
)
if exist ".env" (
  for /f "usebackq tokens=1* delims==" %%A in (".env") do (
    if /I "%%A"=="RUN_MODE" (
      set "RUN_MODE=%%B"
    )
  )
)
if defined RUN_MODE (
  set "MODE=!RUN_MODE!"
  set "RUNMODE_SOURCE=file"
  goto :eof
)
where poetry >nul 2>nul
if %ERRORLEVEL%==0 (
  set "MODE=poetry"
  set "RUNMODE_SOURCE=auto(poetry)"
  goto :eof
)
if exist ".venv\Scripts\activate.bat" (
  set "MODE=legacy"
  set "RUNMODE_SOURCE=auto(.venv)"
  goto :eof
)
if exist "venv\Scripts\activate.bat" (
  set "MODE=legacy"
  set "RUNMODE_SOURCE=auto(venv)"
  goto :eof
)
set "MODE=direct"
set "RUNMODE_SOURCE=auto(direct)"
goto :eof

:activate_venv
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
  goto :eof
) else if exist "venv\Scripts\activate.bat" (
  call "venv\Scripts\activate.bat"
  goto :eof
)
goto :eof

:echoinfo
powershell -NoProfile -Command "Write-Host '%~1' -ForegroundColor Green" >nul 2>&1 || echo %~1
goto :eof

:echowarn
powershell -NoProfile -Command "Write-Host '%~1' -ForegroundColor Yellow" >nul 2>&1 || echo %~1
goto :eof

:echoerr
powershell -NoProfile -Command "Write-Host '%~1' -ForegroundColor Red" >nul 2>&1 || echo %~1
goto :eof
