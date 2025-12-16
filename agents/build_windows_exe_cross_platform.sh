#!/bin/bash

# Heimdall Windows Agent EXE Cross-Platform Builder
# Build on Linux/macOS, deploy on Windows
#
# Usage: ./build_windows_exe_cross_platform.sh
#
# This script builds a Windows EXE on Linux/macOS using PyInstaller.
# The resulting EXE can be copied to any Windows machine and run as a service.

set -e

echo ""
echo "========================================"
echo "  Heimdall Windows Agent Builder"
echo "  Cross-Platform (Linux/macOS → Windows)"
echo "========================================"
echo ""

# Check if PyInstaller is installed
if ! python3 -m PyInstaller --version &>/dev/null; then
    echo "[ERROR] PyInstaller not found"
    echo ""
    echo "Install with: pip install pyinstaller"
    exit 1
fi

# Check if required dependencies are available
echo "[*] Checking dependencies..."

python3 -c "import requests" 2>/dev/null && echo "  ✓ requests" || (echo "  ✗ requests (install: pip install requests)" && exit 1)

echo ""
echo "[*] Building HeimdallAgent.exe..."
echo "    (This may take 1-2 minutes)"
echo ""

# Build the EXE
# Note: The hidden imports include Windows-specific modules that will be available on Windows
python3 -m PyInstaller \
    --onefile \
    --name HeimdallAgent \
    --console \
    --add-data "agent_windows.py:." \
    --hidden-import=win32serviceutil \
    --hidden-import=win32service \
    --hidden-import=win32event \
    --hidden-import=servicemanager \
    --hidden-import=win32evtlog \
    --hidden-import=win32con \
    --hidden-import=win32security \
    --hidden-import=requests \
    --hidden-import=uuid \
    --hidden-import=json \
    --hidden-import=socket \
    --hidden-import=time \
    --hidden-import=logging \
    --hidden-import=pathlib \
    --hidden-import=psutil \
    windows_service_wrapper.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Build completed successfully!"
    echo ""
    echo "Output: dist/HeimdallAgent.exe"
    echo ""
    echo "Next steps:"
    echo "  1. Copy to Windows machine: dist/HeimdallAgent.exe"
    echo "  2. Copy to: C:\\Heimdall\\HeimdallAgent.exe"
    echo "  3. On Windows, run (as Administrator):"
    echo "     C:\\Heimdall\\HeimdallAgent.exe install"
    echo "     C:\\Heimdall\\HeimdallAgent.exe start"
    echo ""
    echo "Or use the Windows installer:"
    echo "  Install-HeimdallAgent.ps1 -ApiUrl 'http://your-siem:8000' -ApiKey 'key'"
    echo ""
else
    echo ""
    echo "✗ Build failed. Check error messages above."
    exit 1
fi
