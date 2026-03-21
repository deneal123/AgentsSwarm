@echo off
REM ===========================================
REM vLLM Service Deployment Script (Windows)
REM ===========================================
REM
REM Usage:
REM   deploy.bat build     Build Docker image
REM   deploy.bat up        Start service
REM   deploy.bat down      Stop service
REM   deploy.bat logs      View logs
REM   deploy.bat status    Check status
REM ===========================================

setlocal EnableDelayedExpansion

REM Get script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Colors (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "NC=[0m"

if "%1"=="" goto help
if "%1"=="build" goto build
if "%1"=="up" goto up
if "%1"=="down" goto down
if "%1"=="logs" goto logs
if "%1"=="status" goto status
if "%1"=="restart" goto restart
if "%1"=="help" goto help
if "%1"=="--help" goto help
if "%1"=="-h" goto help

echo Unknown command: %1
goto help

:help
echo.
echo ===========================================
echo      vLLM Service Deployment Script
echo ===========================================
echo.
echo Usage: %0 ^<command^>
echo.
echo Commands:
echo   build     Build Docker image
echo   up        Start service
echo   down      Stop service
echo   logs      View logs
echo   status    Check status
echo   restart   Restart service
echo.
echo Setup:
echo   1. Copy environment file:
echo      copy .env.node0 .env  (for coordinator)
echo      copy .env.node1 .env  (for worker)
echo.
echo   2. Edit .env with your configuration
echo.
echo   3. Deploy:
echo      %0 build
echo      %0 up
echo.
goto end

:check_env
if not exist .env (
    echo %RED%Error: .env file not found!%NC%
    echo.
    echo Please copy one of the example files:
    echo   copy .env.node0 .env  (for coordinator, rank 0)
    echo   copy .env.node1 .env  (for worker, rank 1)
    echo.
    exit /b 1
)

REM Load .env variables
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "%%a=%%b"
    REM Skip comments
    echo %%a | findstr /r "^#" >nul || set "%%a=%%b"
)

echo %GREEN%Configuration loaded:%NC%
echo   Model: %VLLM_MODEL_NAME%
echo   DP Size: %VLLM_DATA_PARALLEL_SIZE%
echo   DP Rank: %VLLM_DATA_PARALLEL_RANK%
echo   Coordinator: %VLLM_DATA_PARALLEL_ADDRESS%:%VLLM_DATA_PARALLEL_RPC_PORT%
echo.
exit /b 0

:build
echo.
echo ===========================================
echo      Building Docker Image
echo ===========================================
echo.
docker compose build --no-cache
echo.
echo %GREEN%Build complete!%NC%
goto end

:up
echo.
echo ===========================================
echo      Starting vLLM Service
echo ===========================================
echo.
call :check_env
if errorlevel 1 goto end

if "%VLLM_DATA_PARALLEL_RANK%"=="0" (
    echo %BLUE%Starting as Coordinator (rank 0)%NC%
) else (
    echo %BLUE%Starting as Worker (rank %VLLM_DATA_PARALLEL_RANK%)%NC%
)

docker compose up -d

echo.
echo %GREEN%Service started!%NC%
echo.
echo Check status:
echo   %0 status
echo.
echo View logs:
echo   %0 logs
echo.
echo Test API:
echo   curl http://localhost:%VLLM_PORT%/health
goto end

:down
echo.
echo %YELLOW%Stopping vLLM service...%NC%
docker compose down
echo %GREEN%Service stopped.%NC%
goto end

:logs
docker compose logs -f
goto end

:status
echo.
echo %YELLOW%Service Status:%NC%
echo.
docker compose ps
echo.

REM Check health endpoint
set PORT=8000
if defined VLLM_PORT set PORT=%VLLM_PORT%

curl -s --connect-timeout 2 "http://localhost:%PORT%/health" >nul 2>&1
if errorlevel 1 (
    echo %RED%Health check: FAILED (service may still be starting)%NC%
) else (
    echo %GREEN%Health check: OK%NC%
)
goto end

:restart
call :down
echo.
call :up
goto end

:end
endlocal
