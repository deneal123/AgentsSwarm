@echo off
REM Launcher for NVIDIA Isaac Sim container (Docker mode) on Windows (Docker Desktop + WSL2 backend).
REM Usage: start_isaac.bat [headless|gui|check]
REM Env: IMAGE (default nvcr.io/nvidia/isaac-sim:5.1.0), ISAAC_ROOT (default %USERPROFILE%\docker\isaac-sim)

setlocal EnableDelayedExpansion

set "MODE=%~1"
if "%MODE%"=="" set "MODE=headless"

if /I "%MODE%"=="-h" goto :usage
if /I "%MODE%"=="--help" goto :usage
if /I NOT "%MODE%"=="headless" if /I NOT "%MODE%"=="gui" if /I NOT "%MODE%"=="check" (
  echo Unknown mode: %MODE%
  goto :usage
)

if "%IMAGE%"=="" set "IMAGE=nvcr.io/nvidia/isaac-sim:5.1.0"
if "%ISAAC_ROOT%"=="" set "ISAAC_ROOT=%USERPROFILE%\docker\isaac-sim"

REM Quick checks
where docker >nul 2>&1 || (echo Docker not found. Install Docker Desktop with WSL2 backend & exit /b 1)
where nvidia-smi >nul 2>&1 || (echo nvidia-smi not found. Install/enable NVIDIA driver and restart. & exit /b 1)

REM Prepare directories
for %%D in (cache\main\ov cache\main\warp cache\computecache config data\documents data\Kit logs pkg) do (
  if not exist "%ISAAC_ROOT%\%%D" mkdir "%ISAAC_ROOT%\%%D"
)

set "COMMON_OPTS=--name isaac-sim --rm --gpus all --network=host -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y"
set "MOUNTS=^ 
 -v "%ISAAC_ROOT%/cache/main:/isaac-sim/.cache:rw" ^
 -v "%ISAAC_ROOT%/cache/computecache:/isaac-sim/.nv/ComputeCache:rw" ^
 -v "%ISAAC_ROOT%/logs:/isaac-sim/.nvidia-omniverse/logs:rw" ^
 -v "%ISAAC_ROOT%/config:/isaac-sim/.nvidia-omniverse/config:rw" ^
 -v "%ISAAC_ROOT%/data:/isaac-sim/.local/share/ov/data:rw" ^
 -v "%ISAAC_ROOT%/pkg:/isaac-sim/.local/share/ov/pkg:rw""

if /I "%MODE%"=="headless" (
  echo Running Isaac Sim headless...
  docker run %COMMON_OPTS% %MOUNTS% -u 1234:1234 %IMAGE% ./runheadless.sh -v
  goto :eof
)

if /I "%MODE%"=="gui" (
  if "%DISPLAY%"=="" set "DISPLAY=host.docker.internal:0"
  echo Running Isaac Sim with GUI (DISPLAY=%DISPLAY%). Requires X server on Windows.
  docker run %COMMON_OPTS% %MOUNTS% -e DISPLAY=%DISPLAY% -u 1234:1234 %IMAGE% ./runapp.sh
  goto :eof
)

if /I "%MODE%"=="check" (
  echo Running compatibility check...
  docker run %COMMON_OPTS% %MOUNTS% -u 1234:1234 %IMAGE% ./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
  goto :eof
)

:usage
echo Usage: %~nx0 ^<headless^|gui^|check^>
echo   IMAGE=nvcr.io/nvidia/isaac-sim:5.1.0   ^(override to use other tag^) 
echo   ISAAC_ROOT=%%USERPROFILE%%\docker\isaac-sim   ^(override mount root^)
echo Modes:
echo   headless - run ./runheadless.sh -v
echo   gui      - run ./runapp.sh with X11; needs Windows X server and DISPLAY
echo   check    - run ./isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
endlocal