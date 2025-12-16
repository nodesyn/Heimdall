# Cross-Platform Windows Agent Deployment

Build the Heimdall Windows Agent EXE on Linux/macOS and deploy it to Windows systems.

## Perfect For

✅ Building from this Linux server (YOUR_HUB_IP)
✅ CI/CD pipelines
✅ Centralized build infrastructure
✅ Creating deployment packages
✅ Automated Windows rollouts
✅ Air-gapped environments (build once, copy to many)

## How It Works

PyInstaller can cross-compile Python to Windows EXE from Linux/macOS. The resulting binary works identically on any Windows system.

```
Linux/macOS (Build System)
    ↓
pyinstaller (with Windows-specific hidden imports)
    ↓
HeimdallAgent.exe (standalone binary)
    ↓
scp/USB/download to Windows machine
    ↓
Run as Windows Service
```

## Build on Linux/macOS

### Prerequisites

```bash
# Python 3.8+
python3 --version

# PyInstaller
pip install pyinstaller requests
```

### Build Steps

```bash
cd /path/to/Heimdall/agents

# Make script executable
chmod +x build_windows_exe_cross_platform.sh

# Build
./build_windows_exe_cross_platform.sh
```

Output: `dist/HeimdallAgent.exe` (~50MB)

### Verify Build

```bash
# Check file exists
file dist/HeimdallAgent.exe

# Should show: PE32+ executable (console) x86-64

# Check size (should be 40-60MB)
ls -lh dist/HeimdallAgent.exe
```

## Deploy to Windows

### Method 1: Direct Copy (Recommended)

```bash
# From build machine (Linux)
scp dist/HeimdallAgent.exe user@windows-machine:C:/Heimdall/
```

On Windows machine (as Administrator):
```batch
C:\Heimdall\HeimdallAgent.exe install
C:\Heimdall\HeimdallAgent.exe start
```

### Method 2: Manual File Copy

1. On Linux/macOS: Locate `dist/HeimdallAgent.exe`
2. Copy to USB or download
3. On Windows: Copy to `C:\Heimdall\`
4. On Windows (Admin): Run:
   ```batch
   C:\Heimdall\HeimdallAgent.exe install
   C:\Heimdall\HeimdallAgent.exe start
   ```

### Method 3: With Full Setup

Copy both EXE and installer:

```bash
# From Linux
scp dist/HeimdallAgent.exe user@windows:C:/Heimdall/
scp agents/Install-HeimdallAgent.ps1 user@windows:C:/Heimdall/
```

On Windows (as Administrator):
```powershell
cd C:\Heimdall
Install-HeimdallAgent.ps1 -ApiUrl "http://your-siem:8000" -ApiKey "your-key"
```

## Quick Deploy Script (For Multiple Windows Machines)

Create `deploy-agent.sh` on Linux:

```bash
#!/bin/bash
# Deploy HeimdallAgent to multiple Windows machines

WINDOWS_MACHINES=(
    "10.0.0.5"
    "10.0.0.6"
    "10.0.0.7"
)

API_URL="http://your-siem:8000"
API_KEY="your-secure-key"

# Build once
echo "[*] Building HeimdallAgent.exe..."
cd agents
./build_windows_exe_cross_platform.sh

if [ ! -f dist/HeimdallAgent.exe ]; then
    echo "[ERROR] Build failed"
    exit 1
fi

# Deploy to each machine
for machine in "${WINDOWS_MACHINES[@]}"; do
    echo "[*] Deploying to $machine..."

    # Copy EXE
    scp dist/HeimdallAgent.exe "admin@$machine:C:/Heimdall/"

    # Copy installer script
    scp agents/Install-HeimdallAgent.ps1 "admin@$machine:C:/Heimdall/"

    # Execute installation (requires PS Remoting enabled)
    ssh "admin@$machine" powershell.exe -Command \
        "cd C:\\Heimdall; .\\Install-HeimdallAgent.ps1 -ApiUrl '$API_URL' -ApiKey '$API_KEY'"

    echo "[OK] $machine deployed"
done

echo "[OK] All machines deployed!"
```

Make executable and run:
```bash
chmod +x deploy-agent.sh
./deploy-agent.sh
```

## Automated Deployment with Group Policy (Enterprise)

For large deployments, use Windows Group Policy:

### 1. Create Deployment Package

```bash
# Build EXE
./build_windows_exe_cross_platform.sh

# Create package structure
mkdir -p deploy/{bin,scripts}
cp dist/HeimdallAgent.exe deploy/bin/
cp agents/Install-HeimdallAgent.ps1 deploy/scripts/

# Create deployment script
cat > deploy/scripts/deploy.ps1 << 'EOF'
# GPO Deployment Script
$InstallPath = "C:\Heimdall"
mkdir $InstallPath -Force

Copy-Item -Path "\\server\share\deploy\bin\HeimdallAgent.exe" -Destination "$InstallPath\" -Force

# Configure environment variables (local machine scope for services)
[Environment]::SetEnvironmentVariable("SIEM_API_URL", "http://your-siem:8000", "Machine")
[Environment]::SetEnvironmentVariable("SIEM_API_KEY", "your-key", "Machine")

# Install service
& "$InstallPath\HeimdallAgent.exe" install
& "$InstallPath\HeimdallAgent.exe" start
EOF
```

### 2. Configure Group Policy

1. Share deployment package on network: `\\server\share\deploy`
2. Open Group Policy Editor (gpedit.msc)
3. Navigate to: Computer Configuration > Windows Settings > Scripts (Startup/Shutdown)
4. Add: `\\server\share\deploy\scripts\deploy.ps1`
5. Deploy policy to target computers

### 3. Verify Deployment

Windows computers will automatically:
- Download and run deployment script at startup
- Install HeimdallAgent service
- Start monitoring immediately

## Troubleshooting Cross-Platform Builds

### Build Fails: "Module not found"

The hidden imports may not be available on Linux. This is fine - they'll be available on Windows.

```bash
# This error is OK during build:
# WARNING: Python module not found: win32evtlog

# It will work on Windows because:
# 1. PyInstaller bundles the imports anyway
# 2. Windows has pywin32 libraries
# 3. The EXE will find them at runtime
```

### EXE Won't Run on Windows: "Module not found"

Install dependencies on Windows:
```powershell
pip install pywin32
python -m pip install --upgrade pywin32
python Scripts/pywin32_postinstall.py -install
```

Wait, that shouldn't happen because EXE is self-contained. If it does:
1. Verify EXE was built successfully on Linux
2. Check file size (should be 40-60MB)
3. Try building on Windows directly using `build_windows_agent.bat`

### Build Machine: PyInstaller Issues

```bash
# Ensure you have the right version
pip install --upgrade pyinstaller

# Clear cache if weird issues occur
rm -rf build dist *.spec __pycache__

# Rebuild
./build_windows_exe_cross_platform.sh
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Windows Agent

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pyinstaller requests

      - name: Build Windows Agent
        run: |
          cd agents
          ./build_windows_exe_cross_platform.sh

      - name: Upload artifact
        uses: actions/upload-artifact@v2
        with:
          name: HeimdallAgent.exe
          path: agents/dist/HeimdallAgent.exe
```

Then download artifact and deploy to Windows machines.

### GitLab CI Example

```yaml
build_windows_agent:
  stage: build
  image: python:3.11
  script:
    - pip install pyinstaller requests
    - cd agents
    - chmod +x build_windows_exe_cross_platform.sh
    - ./build_windows_exe_cross_platform.sh
  artifacts:
    paths:
      - agents/dist/HeimdallAgent.exe
    expire_in: 30 days
```

## Version Control

### What to Commit

✅ Do commit:
- `agents/agent_windows.py`
- `agents/windows_service_wrapper.py`
- `agents/build_windows_exe_cross_platform.sh`
- `agents/build_windows_agent.bat`
- `agents/Install-HeimdallAgent.ps1`

❌ Don't commit:
- `dist/` directory (use .gitignore)
- `build/` directory
- `.spec` files (regenerated)
- `*.exe` files (too large, rebuild on demand)

### .gitignore Update

```bash
# Build outputs
agents/dist/
agents/build/
agents/*.spec
*.exe
```

## Maintenance & Updates

### Rebuild After Code Changes

```bash
cd agents

# Clean old build
rm -rf dist build *.spec

# Rebuild
./build_windows_exe_cross_platform.sh

# Deploy updated EXE
scp dist/HeimdallAgent.exe user@windows:C:/Heimdall/
```

On Windows (stop old, replace, start new):
```batch
C:\Heimdall\HeimdallAgent.exe stop
REM copy new exe to C:\Heimdall\
C:\Heimdall\HeimdallAgent.exe start
```

## Performance Notes

- **Build time:** 1-2 minutes (first build slower, cached after)
- **EXE size:** ~50MB (includes Python runtime, all dependencies)
- **Runtime memory:** ~30-50MB per service instance
- **Startup time:** 2-5 seconds to initialize service

## Security Considerations

### For Build Machine (Linux/macOS)

```bash
# Use specific versions
pip install pyinstaller==5.x requests==2.x

# Keep build machine updated
sudo apt update && sudo apt upgrade

# Restrict access to build outputs
chmod 700 agents/dist/
```

### For Windows Deployment

```batch
# Restrict EXE permissions
icacls "C:\Heimdall\HeimdallAgent.exe" /inheritance:r /grant:r "SYSTEM:(F)" "Administrators:(F)"

# Restrict logs
icacls "C:\Heimdall\logs" /inheritance:r /grant:r "SYSTEM:(F)" "Administrators:(F)"
```

## Troubleshooting Deployment

### Service Not Starting After Copy

Check logs:
```batch
type C:\Heimdall\logs\heimdall-agent.log
```

Common issues:
1. **API URL unreachable** - Check network connectivity
2. **API key wrong** - Verify environment variable
3. **Permissions** - Run `Install-HeimdallAgent.ps1` script which sets up ACLs

### EXE Signature

The cross-platform built EXE won't be signed. For enterprise:

```powershell
# Self-sign the EXE
Set-AuthenticodeSignature -FilePath "C:\Heimdall\HeimdallAgent.exe" `
    -Certificate (Get-ChildItem cert:\LocalMachine\My | Where-Object {$_.Subject -match "YourCompany"})
```

## Advanced: Customizing Builds

### Add Custom Code

Before building, modify `agents/agent_windows.py` or `windows_service_wrapper.py`:

```bash
# Edit source
vi agents/agent_windows.py

# Rebuild
./build_windows_exe_cross_platform.sh

# Deploy
scp dist/HeimdallAgent.exe user@windows:C:/Heimdall/
```

### Modify Build Parameters

Edit `build_windows_exe_cross_platform.sh`:

```bash
# Change EXE name
--name MyCustomAgent

# Add console window
--console

# Remove console (background service)
--windowed
```

## Support

For issues:
1. Check build logs on Linux/macOS
2. Check service logs on Windows: `C:\Heimdall\logs\heimdall-agent.log`
3. Verify network connectivity: `ping your-siem-server`
4. Check Event Viewer on Windows

## Summary

| Aspect | Details |
|--------|---------|
| **Build Time** | 1-2 minutes |
| **EXE Size** | ~50MB |
| **Platform** | Build: Linux/macOS; Run: Windows |
| **Dependencies** | PyInstaller, requests |
| **Distribution** | Single EXE file |
| **Deployment** | SCP, USB, Group Policy, or manual copy |
| **Advantages** | Build once, deploy to many; CI/CD friendly; No Python on target |
