@echo off
REM Heimdall Windows Agent Setup Script
REM Configures environment variables and installs the Windows service
REM
REM Run this as Administrator

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  Heimdall Windows Agent Setup
echo ========================================
echo.

REM Check if running as Administrator
openfiles >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script must be run as Administrator
    echo.
    echo Please right-click Command Prompt and select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

REM Create Heimdall directories
set HEIMDALL_HOME=C:\Heimdall
set HEIMDALL_LOGS=%HEIMDALL_HOME%\logs
set HEIMDALL_DATA=%HEIMDALL_HOME%\data

echo [*] Creating Heimdall directories...
if not exist "%HEIMDALL_HOME%" mkdir "%HEIMDALL_HOME%"
if not exist "%HEIMDALL_LOGS%" mkdir "%HEIMDALL_LOGS%"
if not exist "%HEIMDALL_DATA%" mkdir "%HEIMDALL_DATA%"

REM Set environment variables
echo.
echo [*] Configuring environment variables...
echo    (Change these values to match your setup)
echo.

set /p API_URL="Enter Heimdall API URL [http://localhost:8000]: " || set API_URL=http://localhost:8000
set /p API_KEY="Enter Heimdall API Key [default-insecure-key-change-me]: " || set API_KEY=default-insecure-key-change-me
set /p INTERVAL="Enter event collection interval in seconds [60]: " || set INTERVAL=60

echo.
echo [*] Setting system environment variables...

REM Set environment variables permanently (requires admin)
setx SIEM_API_URL "%API_URL%"
setx SIEM_API_KEY "%API_KEY%"
setx SIEM_AGENT_INTERVAL "%INTERVAL%"
setx HEIMDALL_LOG_DIR "%HEIMDALL_LOGS%"

echo    - SIEM_API_URL=%API_URL%
echo    - SIEM_API_KEY=***MASKED***
echo    - SIEM_AGENT_INTERVAL=%INTERVAL%
echo    - HEIMDALL_LOG_DIR=%HEIMDALL_LOGS%

REM Copy the EXE to Heimdall directory
if exist "dist\HeimdallAgent.exe" (
    echo.
    echo [*] Copying HeimdallAgent.exe to %HEIMDALL_HOME%...
    copy "dist\HeimdallAgent.exe" "%HEIMDALL_HOME%\HeimdallAgent.exe"

    if errorlevel 1 (
        echo [ERROR] Failed to copy EXE
        pause
        exit /b 1
    )

    echo [OK] EXE copied
) else (
    echo [WARNING] dist\HeimdallAgent.exe not found
    echo    Run: build_windows_agent.bat
    echo.
)

REM Install as Windows service
echo.
echo [*] Installing Windows service...
echo    This may take a moment...
echo.

"%HEIMDALL_HOME%\HeimdallAgent.exe" install

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install service
    echo    Make sure HeimdallAgent.exe is in %HEIMDALL_HOME%
    echo.
    pause
    exit /b 1
)

echo [OK] Service installed

REM Start the service
echo.
echo [*] Starting Heimdall Agent service...
"%HEIMDALL_HOME%\HeimdallAgent.exe" start

echo.
echo ========================================
echo  Installation Complete!
echo ========================================
echo.
echo Service Details:
echo   Name: HeimdallAgent
echo   Display: Heimdall Security Agent
echo   Location: %HEIMDALL_HOME%\HeimdallAgent.exe
echo   Logs: %HEIMDALL_LOGS%
echo.
echo Useful Commands:
echo   Start:   "%HEIMDALL_HOME%\HeimdallAgent.exe" start
echo   Stop:    "%HEIMDALL_HOME%\HeimdallAgent.exe" stop
echo   Restart: "%HEIMDALL_HOME%\HeimdallAgent.exe" restart
echo   Remove:  "%HEIMDALL_HOME%\HeimdallAgent.exe" remove
echo.
echo View service status:
echo   - Services.msc (press Win+R, type services.msc)
echo   - Look for "Heimdall Security Agent"
echo.
echo View logs:
echo   - %HEIMDALL_LOGS%\heimdall-agent.log
echo.
echo Test connectivity:
echo   - Check logs for "API connection successful"
echo.
pause
