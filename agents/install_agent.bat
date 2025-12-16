@echo off
setlocal

:: Heimdall Windows Agent One-Click Installer
:: Automatically requests Admin privileges and runs the PowerShell installer

:: Check for Administrator privileges
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Administrator privileges required.
    echoRequesting elevation...
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Change to the script directory
cd /d "%~dp0"

echo.
echo ========================================
echo  Heimdall Windows Agent Installer
echo ========================================
echo.

:: Check if agent.env exists
if not exist "agent.env" (
    echo [ERROR] agent.env configuration file not found!
    echo Please create agent.env with SIEM_API_URL and SIEM_API_KEY.
    pause
    exit /b 1
)

:: Check if HeimdallAgent.exe exists
if not exist "HeimdallAgent.exe" (
    echo [WARNING] HeimdallAgent.exe not found in current directory.
    echo The installer will look for it in C:\Heimdall if previously installed,
    echo or you must provide it.
    echo.
)

echo [*] Launching PowerShell installer...
powershell -NoProfile -ExecutionPolicy Bypass -File "Install-HeimdallAgent.ps1"

echo.
echo [OK] Process complete.
pause
