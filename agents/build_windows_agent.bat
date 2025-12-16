@echo off
REM Heimdall Windows Agent EXE Builder
REM Compiles the Windows agent to a standalone EXE using PyInstaller
REM
REM Usage: Run this batch file from the agents directory
REM Requirements: PyInstaller installed (pip install pyinstaller)

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  Heimdall Windows Agent Builder
echo ========================================
echo.

REM Check if PyInstaller is installed
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found
    echo.
    echo Please install PyInstaller:
    echo   pip install pyinstaller
    echo.
    exit /b 1
)

REM Check if pywin32 is installed
python -c "import win32serviceutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pywin32 not found
    echo.
    echo Please install pywin32:
    echo   pip install pywin32
    echo.
    exit /b 1
)

REM Check if psutil is installed
python -c "import psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] psutil not found
    echo.
    echo Please install psutil:
    echo   pip install psutil
    echo.
    exit /b 1
)

echo [*] Building HeimdallAgent.exe...
echo.

REM Build using PyInstaller with spec file (includes all hidden imports)
python -m PyInstaller HeimdallAgent.exe.spec

if %errorlevel% equ 0 (
    echo.
    echo [OK] Build completed successfully!
    echo.
    echo Output: dist\HeimdallAgent.exe
    echo.
    echo Next steps:
    echo   1. Copy HeimdallAgent.exe to C:\Heimdall\ or desired location
    echo   2. Set environment variables (see setup_windows_agent.bat)
    echo   3. Run: HeimdallAgent.exe install
    echo   4. Run: HeimdallAgent.exe start
    echo.
) else (
    echo.
    echo [ERROR] Build failed. Check the error messages above.
    echo.
    exit /b 1
)
