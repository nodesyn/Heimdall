# Heimdall Windows Agent as a Service

This guide explains how to compile the Windows Agent as an EXE and run it as a Windows Service for production deployment.

## Quick Start (Easiest Method)

### Prerequisites
- Windows Server 2016+ or Windows 10+
- Administrator privileges
- Python 3.8+ installed
- Required packages: `pip install pyinstaller pywin32 requests`

### Installation (5 minutes)

**Step 1: Build the EXE**
```powershell
cd C:\path\to\Heimdall\agents
build_windows_agent.bat
```

This creates `dist\HeimdallAgent.exe`

**Step 2: Run Installation Script**
```powershell
# As Administrator
Install-HeimdallAgent.ps1 -ApiUrl "http://your-siem-server:8000" -ApiKey "your-api-key"
```

Or use the batch file:
```batch
setup_windows_agent.bat
```

**Done!** The service is now running and will start automatically on reboot.

## Manual Installation

If you prefer to install manually:

### 1. Build the EXE
```batch
cd agents
build_windows_agent.bat
```

### 2. Create Installation Directory
```batch
mkdir C:\Heimdall
mkdir C:\Heimdall\logs
mkdir C:\Heimdall\data
copy dist\HeimdallAgent.exe C:\Heimdall\
```

### 3. Set Environment Variables (as Administrator)
```batch
setx SIEM_API_URL "http://your-siem-server:8000"
setx SIEM_API_KEY "your-secure-api-key"
setx SIEM_AGENT_INTERVAL "60"
setx HEIMDALL_LOG_DIR "C:\Heimdall\logs"
```

### 4. Install Service (as Administrator)
```batch
C:\Heimdall\HeimdallAgent.exe install
```

### 5. Start Service
```batch
C:\Heimdall\HeimdallAgent.exe start
```

## Service Commands

Once installed, use these commands:

```batch
REM Start the service
C:\Heimdall\HeimdallAgent.exe start

REM Stop the service
C:\Heimdall\HeimdallAgent.exe stop

REM Restart the service
C:\Heimdall\HeimdallAgent.exe restart

REM Remove the service
C:\Heimdall\HeimdallAgent.exe remove
```

Or use Windows Services Manager:
```batch
services.msc
```

## Configuration

Configuration is done through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SIEM_API_URL` | http://localhost:8000 | API server address |
| `SIEM_API_KEY` | default-insecure-key-change-me | API authentication key |
| `SIEM_AGENT_INTERVAL` | 60 | Event collection interval (seconds) |
| `HEIMDALL_LOG_DIR` | C:\Heimdall\logs | Log file directory |

### Change Configuration Later

```batch
REM Stop the service
C:\Heimdall\HeimdallAgent.exe stop

REM Update environment variable
setx SIEM_API_URL "http://new-server:8000"

REM Restart (must restart for env var changes to take effect)
C:\Heimdall\HeimdallAgent.exe start
```

## Logging

Logs are written to: `C:\Heimdall\logs\heimdall-agent.log`

View logs:
```powershell
# Real-time log viewing
Get-Content C:\Heimdall\logs\heimdall-agent.log -Tail 20 -Wait

# Full log
Get-Content C:\Heimdall\logs\heimdall-agent.log
```

### Log Rotation

For production, set up log rotation. You can use the Windows Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Heimdall Log Cleanup"
4. Trigger: Daily at 2 AM
5. Action: Run script
   ```powershell
   Get-ChildItem C:\Heimdall\logs\*.log -File |
     Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} |
     Remove-Item
   ```

## Troubleshooting

### Service won't start
1. Check logs: `C:\Heimdall\logs\heimdall-agent.log`
2. Verify API URL is reachable: `ping your-siem-server`
3. Check API key is correct
4. Review Event Viewer: Applications and Services Logs > Application

```powershell
# View service error details
Get-EventLog -LogName Application -Source "HeimdallAgent" -Newest 10
```

### API Connection Failed
```
Error: Cannot connect to API server
```

Solutions:
1. Verify API URL: `Test-NetConnection -ComputerName your-siem-server -Port 8000`
2. Check firewall rules on the API server
3. Verify API is running: `curl http://your-siem-server:8000`
4. Check API key matches in both agent and server config

### Permission Denied
```
Error: Permission denied writing to log directory
```

Solutions:
```powershell
# Verify directory exists and is writable
icacls "C:\Heimdall\logs" /grant "NT Service\HeimdallAgent:(F)"
```

### Service Installation Failed

Ensure:
1. Running as Administrator
2. Service name "HeimdallAgent" isn't already taken
3. Check Event Viewer for details

Remove and reinstall:
```batch
C:\Heimdall\HeimdallAgent.exe remove
C:\Heimdall\HeimdallAgent.exe install
```

## Advanced: Custom Service Properties

### Run as Specific User

By default, the service runs as SYSTEM. To run as a specific user:

```powershell
# Stop the service
Stop-Service HeimdallAgent

# Change service user (run as Administrator)
$ServiceName = "HeimdallAgent"
$UserAccount = "DOMAIN\username"
$Password = "password"

# Use sc.exe to configure user
sc.exe config $ServiceName obj= "$UserAccount" password= "$Password"

# Start the service
Start-Service HeimdallAgent
```

### Autostart on Reboot

The service is already configured to autostart. To verify:

```powershell
Get-Service HeimdallAgent | Select-Object StartType
# Should show "Automatic"
```

To change:
```powershell
Set-Service HeimdallAgent -StartupType Automatic
```

### Performance Tuning

Collection interval (how often to check for new events):

```batch
REM More frequent checks (higher overhead)
setx SIEM_AGENT_INTERVAL "30"

REM Less frequent checks (lower overhead)
setx SIEM_AGENT_INTERVAL "120"
```

## Security Considerations

1. **API Key**: Change from default!
   ```batch
   setx SIEM_API_KEY "your-strong-api-key"
   ```

2. **Firewall Rules**: Allow outbound HTTPS to your SIEM server
   ```powershell
   New-NetFirewallRule -DisplayName "Heimdall Agent" `
     -Direction Outbound `
     -Protocol TCP `
     -RemoteAddress "your-siem-server" `
     -RemotePort 8000 `
     -Action Allow
   ```

3. **Service Permissions**: Service runs as SYSTEM by default
   - Handles Event Log with admin privileges
   - Logs to `C:\Heimdall\logs` directory
   - Verify directory permissions:
     ```powershell
     icacls "C:\Heimdall" /T
     ```

4. **Log File Access**: Restrict log file permissions
   ```powershell
   icacls "C:\Heimdall\logs" /inheritance:r /grant:r "Administrators:(F)" "SYSTEM:(F)"
   ```

## Uninstallation

To completely remove the agent:

```batch
REM Stop the service
C:\Heimdall\HeimdallAgent.exe stop

REM Remove service registration
C:\Heimdall\HeimdallAgent.exe remove

REM Delete files (optional)
rmdir /s /q C:\Heimdall

REM Remove environment variables (optional)
setx SIEM_API_URL ""
setx SIEM_API_KEY ""
setx SIEM_AGENT_INTERVAL ""
setx HEIMDALL_LOG_DIR ""
```

## Upgrading

1. Stop the service
   ```batch
   C:\Heimdall\HeimdallAgent.exe stop
   ```

2. Build new EXE from updated code
   ```batch
   build_windows_agent.bat
   ```

3. Copy new EXE
   ```batch
   copy dist\HeimdallAgent.exe C:\Heimdall\
   ```

4. Start the service
   ```batch
   C:\Heimdall\HeimdallAgent.exe start
   ```

## Building from Source

### Requirements
```bash
pip install pyinstaller pywin32 requests
```

### Build Process

```batch
cd agents

REM Download pywin32 post-install script
python Scripts/pywin32_postinstall.py -install

REM Build the EXE
pyinstaller --onefile `
    --name HeimdallAgent `
    --console `
    --add-data "agent_windows.py;." `
    windows_service_wrapper.py
```

Output: `dist\HeimdallAgent.exe`

### Customization

Edit `build_windows_exe.spec` to:
- Add custom icon: `icon='C:\\path\\to\\icon.ico'`
- Exclude modules to reduce EXE size
- Add additional data files
- Change output directory

Then rebuild:
```batch
pyinstaller build_windows_exe.spec
```

## Docker Distribution (Optional)

If you prefer to run the agent in Docker on Windows:

```dockerfile
FROM python:3.11-windowsservercore

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY agents/agent_windows.py .
COPY agents/windows_service_wrapper.py .

ENV SIEM_API_URL=http://host.docker.internal:8000
ENV SIEM_API_KEY=your-key

CMD ["python", "windows_service_wrapper.py"]
```

Build and run:
```powershell
docker build -t heimdall-agent-windows .
docker run -e SIEM_API_URL="http://your-siem:8000" -e SIEM_API_KEY="key" heimdall-agent-windows
```

## Support

For issues:
1. Check logs: `C:\Heimdall\logs\heimdall-agent.log`
2. Review Windows Event Viewer
3. Test connectivity: `Test-NetConnection -ComputerName your-siem -Port 8000`
4. Verify configuration: Environment variables are set correctly
5. Test API key: `curl -H "api-key: your-key" http://your-siem:8000/`

## Files Reference

| File | Purpose |
|------|---------|
| `agent_windows.py` | Core Windows agent logic |
| `windows_service_wrapper.py` | Windows service integration |
| `build_windows_exe.spec` | PyInstaller configuration |
| `build_windows_agent.bat` | EXE builder script |
| `setup_windows_agent.bat` | Service setup script |
| `Install-HeimdallAgent.ps1` | PowerShell installer |

## Version History

- **v2.0.0** - Service wrapper, PyInstaller build, automated installation
- **v1.0.0** - Initial Python script agent
