# Windows Agent Troubleshooting Guide

## Quick Diagnosis Steps

### 1. Verify Agent is Running

**Check if the agent process is running:**
```powershell
Get-Process python | Where-Object {$_.Path -like "*heimdall*"}
```

**Check Scheduled Task status:**
```powershell
Get-ScheduledTask -TaskName "Heimdall Agent" | Format-List
```

**Check Task Scheduler history:**
```powershell
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational | Where-Object {$_.Message -like "*Heimdall*"} | Select-Object -First 10
```

### 2. Verify Configuration

**Check environment variables (if running manually):**
```powershell
$env:SIEM_API_URL
$env:SIEM_API_KEY
```

**For Scheduled Task, check task environment:**
```powershell
$task = Get-ScheduledTask -TaskName "Heimdall Agent"
$task.Actions[0].Execute
$task.Actions[0].Arguments
```

**Important:** Scheduled Tasks don't inherit environment variables! You need to set them explicitly.

### 3. Test API Connectivity

**Test connection to Heimdall hub:**
```powershell
# Test basic connectivity
Test-NetConnection -ComputerName YOUR_HUB_IP -Port 8010

# Test API endpoint
$headers = @{"api-key" = "your-secure-api-key"}
Invoke-RestMethod -Uri "http://YOUR_HUB_IP:8010/health" -Headers $headers -Method Get
```

### 4. Run Agent Manually (for testing)

**Set environment variables:**
```powershell
$env:SIEM_API_URL = "http://YOUR_HUB_IP:8010"
$env:SIEM_API_KEY = "your-secure-api-key"
```

**Run agent:**
```powershell
cd "C:\Program Files\Heimdall"
python agents\agent_windows.py
```

You should see output like:
```
Windows Agent starting (host: YOUR-HOSTNAME)
API URL: http://YOUR_HUB_IP:8010
✓ Sent X events to API
```

### 5. Check for Errors

**Check Windows Event Viewer:**
```powershell
Get-WinEvent -LogName Application | Where-Object {$_.ProviderName -like "*Python*" -or $_.Message -like "*Heimdall*"} | Select-Object -First 20
```

**Check if agent can read Security log:**
```powershell
# Run as Administrator
Get-WinEvent -LogName Security -MaxEvents 5
```

## Common Issues and Solutions

### Issue 1: Agent Not Sending Events

**Symptoms:** Agent runs but no events appear in dashboard

**Causes:**
1. **Wrong API URL** - Agent is using default `http://localhost:8000` instead of `http://YOUR_HUB_IP:8010`
2. **Wrong API Key** - API key doesn't match hub configuration
3. **No events to collect** - Security log doesn't have relevant events (4625, 4720, 1102)
4. **Network connectivity** - Can't reach the hub server

**Solutions:**

**A. Fix API URL and Key in Scheduled Task:**

Create a wrapper script that sets environment variables:

**Create `C:\Program Files\Heimdall\run_agent.bat`:**
```batch
@echo off
set SIEM_API_URL=http://YOUR_HUB_IP:8010
set SIEM_API_KEY=your-secure-api-key
cd /d "C:\Program Files\Heimdall"
python agents\agent_windows.py
```

**Update Scheduled Task to use the batch file:**
```powershell
$action = New-ScheduledTaskAction -Execute 'C:\Program Files\Heimdall\run_agent.bat' -WorkingDirectory 'C:\Program Files\Heimdall'
$trigger = New-ScheduledTaskTrigger -At (Get-Date) -Once
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Remove old task if exists
Unregister-ScheduledTask -TaskName "Heimdall Agent" -Confirm:$false -ErrorAction SilentlyContinue

# Register new task
Register-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -TaskName "Heimdall Agent" -Description "Heimdall Security Monitoring Agent"

# Set repetition
$task = Get-ScheduledTask -TaskName "Heimdall Agent"
$task.Triggers[0].Repetition.Interval = "PT1M"
$task.Triggers[0].Repetition.Duration = "P365D"
Set-ScheduledTask -InputObject $task
```

**B. Generate Test Events:**

To verify the agent is working, generate some test events:

**Failed logon attempt (Event ID 4625):**
```powershell
# Try to login with wrong password (this will generate Event ID 4625)
# Or use a test account
```

**Create a test user (Event ID 4720):**
```powershell
# Run as Administrator
New-LocalUser -Name "TestUser" -Password (ConvertTo-SecureString "TempPass123!" -AsPlainText -Force) -Description "Test user for Heimdall"
Remove-LocalUser -Name "TestUser"  # Clean up after
```

### Issue 2: "Access Denied" or "Permission Denied"

**Symptoms:** Agent can't read Security event log

**Solution:** Run agent as Administrator or SYSTEM account

**Verify permissions:**
```powershell
# Check if running as Administrator
([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

**Fix Scheduled Task to run as SYSTEM:**
```powershell
$task = Get-ScheduledTask -TaskName "Heimdall Agent"
$task.Principal.UserId = "SYSTEM"
$task.Principal.LogonType = "ServiceAccount"
$task.Principal.RunLevel = "Highest"
Set-ScheduledTask -InputObject $task
```

### Issue 3: Network Connectivity Issues

**Symptoms:** "Connection refused" or timeout errors

**Check firewall:**
```powershell
# Check Windows Firewall
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Python*" -or $_.DisplayName -like "*8010*"}

# Allow Python through firewall (if needed)
New-NetFirewallRule -DisplayName "Heimdall Agent Outbound" -Direction Outbound -Program "C:\Python310\python.exe" -Action Allow
```

**Test connectivity:**
```powershell
# Test TCP connection
Test-NetConnection -ComputerName YOUR_HUB_IP -Port 8010

# Test HTTP connection
try {
    $response = Invoke-WebRequest -Uri "http://YOUR_HUB_IP:8010/health" -TimeoutSec 5
    Write-Host "Connection successful: $($response.StatusCode)"
} catch {
    Write-Host "Connection failed: $_"
}
```

### Issue 4: Python/Module Not Found

**Symptoms:** "python: command not found" or import errors

**Check Python installation:**
```powershell
python --version
python -c "import requests; print('requests OK')"
python -c "import win32evtlog; print('pywin32 OK')"
```

**Install missing modules:**
```powershell
pip install requests python-dateutil pywin32
```

**Fix Python path in Scheduled Task:**
```powershell
# Find Python path
where.exe python

# Update Scheduled Task with full path
$task = Get-ScheduledTask -TaskName "Heimdall Agent"
$task.Actions[0].Execute = "C:\Python310\python.exe"  # Use your actual Python path
Set-ScheduledTask -InputObject $task
```

## Verification Checklist

- [ ] Agent process is running (check Task Manager or `Get-Process`)
- [ ] Scheduled Task is enabled and running
- [ ] Environment variables are set correctly (SIEM_API_URL, SIEM_API_KEY)
- [ ] API URL points to `http://YOUR_HUB_IP:8010` (not localhost:8000)
- [ ] API key matches the hub configuration
- [ ] Network connectivity to hub (port 8010) works
- [ ] Agent can read Security event log (run as Administrator)
- [ ] Security log contains relevant events (4625, 4720, 1102)
- [ ] Python and required modules are installed
- [ ] Agent runs successfully when executed manually

## Test Agent Manually

**Complete test script:**

```powershell
# Set environment variables
$env:SIEM_API_URL = "http://YOUR_HUB_IP:8010"
$env:SIEM_API_KEY = "your-secure-api-key"

# Test API connectivity
Write-Host "Testing API connectivity..."
try {
    $headers = @{"api-key" = $env:SIEM_API_KEY}
    $response = Invoke-RestMethod -Uri "$($env:SIEM_API_URL)/health" -Headers $headers -Method Get
    Write-Host "✓ API is reachable: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot reach API: $_" -ForegroundColor Red
    exit 1
}

# Test Security log access
Write-Host "`nTesting Security log access..."
try {
    $events = Get-WinEvent -LogName Security -MaxEvents 1 -ErrorAction Stop
    Write-Host "✓ Can read Security log" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot read Security log: $_" -ForegroundColor Red
    Write-Host "  Run PowerShell as Administrator!" -ForegroundColor Yellow
    exit 1
}

# Run agent
Write-Host "`nStarting agent (will run for 60 seconds)..."
cd "C:\Program Files\Heimdall"
python agents\agent_windows.py
```

## Still Not Working?

1. **Check agent output** - Run manually and watch for error messages
2. **Check hub logs** - Verify events are being received:
   ```bash
   ssh n0de@YOUR_HUB_IP "cd ~/heimdall && docker-compose logs | grep -i 'ingest\|windows'"
   ```
3. **Check dashboard** - Verify events appear in the dashboard at http://YOUR_HUB_IP:8501
4. **Verify API key** - Double-check the API key matches exactly (no extra spaces)

## Quick Fix: Complete Reinstall

If nothing works, reinstall the agent completely:

```powershell
# Stop and remove old task
Unregister-ScheduledTask -TaskName "Heimdall Agent" -Confirm:$false

# Create batch file with correct configuration
@"
@echo off
set SIEM_API_URL=http://YOUR_HUB_IP:8010
set SIEM_API_KEY=your-secure-api-key
cd /d "C:\Program Files\Heimdall"
python agents\agent_windows.py
"@ | Out-File -FilePath "C:\Program Files\Heimdall\run_agent.bat" -Encoding ASCII

# Create new scheduled task
$action = New-ScheduledTaskAction -Execute 'C:\Program Files\Heimdall\run_agent.bat' -WorkingDirectory 'C:\Program Files\Heimdall'
$trigger = New-ScheduledTaskTrigger -At (Get-Date) -Once
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -TaskName "Heimdall Agent" -Description "Heimdall Security Monitoring Agent"

# Set repetition
$task = Get-ScheduledTask -TaskName "Heimdall Agent"
$task.Triggers[0].Repetition.Interval = "PT1M"
$task.Triggers[0].Repetition.Duration = "P365D"
Set-ScheduledTask -InputObject $task

# Start the task
Start-ScheduledTask -TaskName "Heimdall Agent"
```
