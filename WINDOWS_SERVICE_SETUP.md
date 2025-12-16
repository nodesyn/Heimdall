# Windows Agent as Windows Service - Setup Guide

This document summarizes the Windows service deployment capability for Heimdall Windows Agent.

## What Was Created

### 1. Python Service Wrapper
**File:** `agents/windows_service_wrapper.py`

- Windows Service integration using `pywin32`
- Wraps `agent_windows.py` in a ServiceFramework
- Implements service lifecycle (start, stop, install, remove)
- Proper logging to file and event log
- Graceful shutdown handling
- Command-line interface for service management

### 2. Build Automation

**File:** `agents/build_windows_agent.bat`
- Compiles Python code to standalone EXE using PyInstaller
- Creates `dist/HeimdallAgent.exe` (~50MB with all dependencies)
- Single executable, no Python installation required on target system

**File:** `agents/build_windows_exe.spec`
- PyInstaller configuration
- Specifies hidden imports (pywin32, win32evtlog, etc.)
- Optimizes for Windows service deployment

### 3. Installation Scripts

**File:** `agents/Install-HeimdallAgent.ps1` (Recommended)
- PowerShell installer (modern, flexible)
- Accepts parameters: API URL, API key, installation path
- Creates directories
- Sets environment variables
- Installs and starts service
- Example: `Install-HeimdallAgent.ps1 -ApiUrl "http://siem:8000" -ApiKey "key"`

**File:** `agents/setup_windows_agent.bat`
- Batch file installer (traditional, works on older systems)
- Interactive prompts for configuration
- Creates `C:\Heimdall` directory structure
- Installs service
- Sets up logs directory

**File:** `agents/WINDOWS_SERVICE_README.md`
- Quick reference guide
- File overview
- Common commands
- Troubleshooting tips

### 4. Documentation

**File:** `docs/WINDOWS_AGENT_SERVICE.md` (Comprehensive - 400+ lines)
- Complete setup guide
- Installation methods (Quick Start, Manual, PowerShell, Batch)
- Configuration options
- Service commands and management
- Logging and log rotation
- Troubleshooting guide
- Security considerations
- Advanced topics (custom users, autostart, performance tuning)
- Uninstallation and upgrade procedures
- Building from source
- Docker option

**File:** `CLAUDE.md` (Updated)
- Added Windows service section
- Quick reference for building and running as service
- Links to full documentation

## How It Works

### Architecture
```
agent_windows.py (core logic - unchanged)
     ↓
windows_service_wrapper.py (service integration)
     ↓
PyInstaller (build_windows_agent.bat)
     ↓
HeimdallAgent.exe (standalone executable)
     ↓
Windows Service Control Manager (SCM)
     ↓
Runs as Windows Service (auto-start, auto-restart)
```

### Installation Flow
```
Install-HeimdallAgent.ps1 or setup_windows_agent.bat
     ↓
Create C:\Heimdall directory structure
     ↓
Set environment variables
     ↓
Copy HeimdallAgent.exe to C:\Heimdall
     ↓
Register service with Windows SCM
     ↓
Start service
     ↓
Service auto-starts on reboot
```

## Deployment Steps

### For Windows Systems (Development)

```powershell
# 1. Install dependencies
pip install pyinstaller pywin32 requests

# 2. Build EXE
cd C:\path\to\Heimdall\agents
build_windows_agent.bat

# 3. Install service (as Administrator)
Install-HeimdallAgent.ps1 -ApiUrl "http://your-siem:8000" -ApiKey "your-api-key"

# 4. Verify
Get-Service HeimdallAgent | Select-Object Name, Status, StartType
```

### For Windows Systems (Production)

1. Copy `HeimdallAgent.exe` to target system (`C:\Heimdall` or custom path)
2. Run installer script with appropriate parameters:
   ```powershell
   Install-HeimdallAgent.ps1 -ApiUrl "http://siem-server:8000" -ApiKey "secure-key"
   ```
3. Service runs automatically, logs to `C:\Heimdall\logs\heimdall-agent.log`

## Key Features

✅ **Standalone EXE** - No Python runtime required on target system
✅ **Windows Service** - Runs as system service, auto-starts on reboot
✅ **Proper Logging** - File-based and Windows Event Log integration
✅ **Graceful Shutdown** - Properly handles Windows stop signals
✅ **Configuration via Environment Variables** - Easy to configure
✅ **Event Log Access** - Runs with SYSTEM privileges to read Security log
✅ **Command-Line Management** - Easy start/stop/restart/remove
✅ **Windows Services UI** - Integrate with services.msc
✅ **Auto-Restart** - Windows restarts failed service
✅ **Admin Privileges** - Can read Security Event Log (requires SYSTEM or Admin)

## Configuration

All configuration through environment variables:

```batch
SIEM_API_URL=http://your-siem-server:8000       # API endpoint
SIEM_API_KEY=your-secure-api-key                # Authentication
SIEM_AGENT_INTERVAL=60                          # Collection interval (seconds)
HEIMDALL_LOG_DIR=C:\Heimdall\logs               # Log directory
```

## Service Operations

### Start
```batch
C:\Heimdall\HeimdallAgent.exe start
```

### Stop
```batch
C:\Heimdall\HeimdallAgent.exe stop
```

### Restart
```batch
C:\Heimdall\HeimdallAgent.exe restart
```

### Remove
```batch
C:\Heimdall\HeimdallAgent.exe stop
C:\Heimdall\HeimdallAgent.exe remove
```

## Logging

Service logs to: `C:\Heimdall\logs\heimdall-agent.log`

View logs:
```powershell
# Last 20 lines
Get-Content C:\Heimdall\logs\heimdall-agent.log -Tail 20

# Real-time monitoring
Get-Content C:\Heimdall\logs\heimdall-agent.log -Tail 20 -Wait

# Search for errors
Select-String "ERROR\|WARN" C:\Heimdall\logs\heimdall-agent.log
```

## Requirements

### Build System
- Windows 10+ or Windows Server 2016+
- Python 3.8+
- `pip install pyinstaller pywin32 requests`

### Target System
- Windows 10+ or Windows Server 2016+
- Administrator privileges to install service
- Network access to Heimdall API server
- Event Log access (for Security log collection)

## Troubleshooting

### Build fails: "No module named 'pywin32'"
```bash
pip install pywin32
python Scripts/pywin32_postinstall.py -install
```

### Service won't start: "API connection failed"
1. Check API URL: `Test-NetConnection -ComputerName your-siem -Port 8000`
2. Verify API is running
3. Check API key matches configuration

### Service won't install: "Access denied"
- Run Command Prompt or PowerShell as Administrator
- Windows requires admin privileges to register services

### Service won't read event log
- Service must run as SYSTEM or Administrators
- Default deployment runs as SYSTEM ✓

## Advanced Features

See `docs/WINDOWS_AGENT_SERVICE.md` for:
- Running as specific user account
- Custom service properties
- Performance tuning
- Security hardening
- Log rotation
- Docker containerization
- Building from modified source

## File Dependencies

The executable bundles:
- `agent_windows.py` - Core Windows agent logic
- `windows_service_wrapper.py` - Service integration
- `pywin32` - Windows API bindings
- `requests` - HTTP client
- Python standard library

Total executable size: ~50MB (PyInstaller compressed)

## Version Compatibility

- Heimdall v2.0+
- Windows 10+ / Windows Server 2016+
- Python 3.8+
- pywin32 (latest)
- PyInstaller 5.0+

## Migration Path

### From Python Script to Service

```bash
# Old: Run Python script manually
python agents/agent_windows.py

# New: Run as Windows Service
C:\Heimdall\HeimdallAgent.exe start

# Benefits:
# - Auto-starts on reboot
# - Auto-restarts if crashed
# - Windows Services integration (services.msc)
# - Proper event logging
# - No Python installation needed
# - Can be deployed with Group Policy
```

## Support & Documentation

- **Quick Start:** See `agents/WINDOWS_SERVICE_README.md`
- **Complete Guide:** See `docs/WINDOWS_AGENT_SERVICE.md`
- **Development:** See `CLAUDE.md`
- **Issues:** Check logs at `C:\Heimdall\logs\heimdall-agent.log`
- **Event Viewer:** Applications and Services Logs > Application > "HeimdallAgent"

## Next Steps

1. Read `docs/WINDOWS_AGENT_SERVICE.md` for complete documentation
2. Build EXE: `build_windows_agent.bat`
3. Install service: `Install-HeimdallAgent.ps1` or `setup_windows_agent.bat`
4. Verify in Services (press Win+R → `services.msc`)
5. Monitor logs: `C:\Heimdall\logs\heimdall-agent.log`
