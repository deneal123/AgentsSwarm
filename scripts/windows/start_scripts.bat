@echo off

setlocal EnableDelayedExpansion
pushd "%~dp0\..\.." || exit /b 1
set "PROJECT_ROOT=%CD%"
if defined PYTHONPATH (
    set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%PROJECT_ROOT%"
)

set "MODE="
for /f "delims=" %%A in ('echo prompt $E ^| cmd') do set "ESC=%%A"
set "RED=!ESC![31m"
set "GREEN=!ESC![32m"
set "YELLOW=!ESC![33m"
set "RESET=!ESC![0m"

call :detect_mode
call :echoinfo "RUN_MODE=!RUN_MODE! (source: !RUNMODE_SOURCE!)"
call :echoinfo "chosen MODE=!MODE!"

if /I "%MODE%"=="poetry" (
    poetry run python %*
) else if /I "%MODE%"=="legacy" (
    call :activate_venv
    python %*
) else (
    python %*
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
