# Heimdall Windows Agent Service

Compile the Windows agent as an EXE and run it as a Windows Service for production deployment.

## Quick Start

### Option A: Build on Windows (Easiest)

#### 1. Install Dependencies
```powershell
pip install pyinstaller pywin32 requests
python -m pip install --upgrade pywin32
python Scripts/pywin32_postinstall.py -install
```

#### 2. Build EXE
```batch
cd agents
build_windows_agent.bat
```

This creates `dist\HeimdallAgent.exe`

### Option B: Build on Linux/macOS, Deploy on Windows (Recommended)

This is perfect for CI/CD pipelines or building from this Linux server for Windows deployment.

#### 1. Install Dependencies (on Linux/macOS)
```bash
pip install pyinstaller requests
```

#### 2. Build EXE
```bash
cd agents
chmod +x build_windows_exe_cross_platform.sh
./build_windows_exe_cross_platform.sh
```

This creates `dist/HeimdallAgent.exe` (works on Windows even though built on Linux)

#### 3. Copy to Windows
```bash
# From Linux/macOS
scp dist/HeimdallAgent.exe user@windows-machine:C:/Heimdall/

# Or manually copy dist/HeimdallAgent.exe to Windows
```

#### 4. Install on Windows (as Administrator)
```batch
C:\Heimdall\HeimdallAgent.exe install
C:\Heimdall\HeimdallAgent.exe start
```

### 3. Install Service (Choose One)

**Option A: PowerShell (Recommended)**
```powershell
# Run as Administrator
Install-HeimdallAgent.ps1 -ApiUrl "http://your-siem:8000" -ApiKey "your-key"
```

**Option B: Batch Installer**
```batch
# Run as Administrator
setup_windows_agent.bat
```

**Option C: Manual**
```batch
mkdir C:\Heimdall
copy dist\HeimdallAgent.exe C:\Heimdall\
C:\Heimdall\HeimdallAgent.exe install
C:\Heimdall\HeimdallAgent.exe start
```

## Files Overview

| File | Purpose |
|------|---------|
| `windows_service_wrapper.py` | Service integration layer (imports agent_windows.py) |
| `agent_windows.py` | Core Windows agent logic (unchanged) |
| `build_windows_agent.bat` | Builds EXE from Python code |
| `build_windows_exe.spec` | PyInstaller configuration |
| `setup_windows_agent.bat` | Batch installer (sets up environment, installs service) |
| `Install-HeimdallAgent.ps1` | PowerShell installer (recommended) |

## Service Management

Once installed:

```batch
# Start
C:\Heimdall\HeimdallAgent.exe start

# Stop
C:\Heimdall\HeimdallAgent.exe stop

# Restart
C:\Heimdall\HeimdallAgent.exe restart

# Remove
C:\Heimdall\HeimdallAgent.exe remove
```

Or use Windows Services (press Win+R → `services.msc` → find "Heimdall Security Agent")

## Configuration

Environment variables (set before or after install):
```batch
setx SIEM_API_URL "http://your-siem:8000"
setx SIEM_API_KEY "your-secure-key"
setx SIEM_AGENT_INTERVAL "60"
setx HEIMDALL_LOG_DIR "C:\Heimdall\logs"
```

## Logs

View logs: `C:\Heimdall\logs\heimdall-agent.log`

```powershell
# Real-time monitoring
Get-Content C:\Heimdall\logs\heimdall-agent.log -Tail 20 -Wait
```

## Troubleshooting

**Service won't start:**
1. Check logs: `C:\Heimdall\logs\heimdall-agent.log`
2. Verify API URL is reachable
3. Check Event Viewer for error messages

**Cannot connect to API:**
```powershell
# Test connectivity
Test-NetConnection -ComputerName your-siem -Port 8000
```

## Full Documentation

See `docs/WINDOWS_AGENT_SERVICE.md` for comprehensive guide including:
- Advanced configuration
- Troubleshooting
- Security considerations
- Log rotation
- Custom user accounts
- Docker deployment option

## Dependencies

Built into EXE:
- `pywin32` - Windows API access (Event Log)
- `requests` - HTTP communication with SIEM server
- Standard library: `json`, `logging`, `socket`, `time`, `pathlib`

## Notes

- Service runs as SYSTEM account (can read Security Event Log)
- Auto-start enabled on reboot
- Logs to `C:\Heimdall\logs\heimdall-agent.log`
- Configuration via environment variables
- Restart required after changing environment variables

## Support

Check logs and Event Viewer (Applications and Services Logs > Application)
