# Quick Fix: Windows Agent Not Connecting

## Immediate Diagnostic Steps

### Step 1: Run Diagnostic Script

On your Windows host, run:

```powershell
# Set environment variables first
$env:SIEM_API_URL = "http://YOUR_HUB_IP:8010"
$env:SIEM_API_KEY = "your-secure-api-key"

# Run diagnostic
python agents\test_windows_connection.py
```

This will test:
- Environment variables
- DNS resolution
- Port connectivity
- HTTP connection
- API authentication
- Event ingestion

### Step 2: Check Scheduled Task Configuration

**The most common issue:** Scheduled Tasks don't inherit environment variables!

```powershell
# Check current task configuration
$task = Get-ScheduledTask -TaskName "Heimdall Agent"
$task.Actions[0] | Format-List
```

If it's calling Python directly, it won't have the environment variables.

### Step 3: Fix Scheduled Task with Batch File

Create `C:\Program Files\Heimdall\run_agent.bat`:

```batch
@echo off
set SIEM_API_URL=http://YOUR_HUB_IP:8010
set SIEM_API_KEY=your-secure-api-key
cd /d "C:\Program Files\Heimdall"
python agents\agent_windows.py >> agent.log 2>&1
```

Then update the Scheduled Task:

```powershell
# Remove old task
Unregister-ScheduledTask -TaskName "Heimdall Agent" -Confirm:$false

# Create new task using batch file
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

### Step 4: Check Agent Logs

```powershell
# View the log file
Get-Content "C:\Program Files\Heimdall\agent.log" -Tail 50

# Or watch it in real-time
Get-Content "C:\Program Files\Heimdall\agent.log" -Wait -Tail 20
```

### Step 5: Test Manually

Run the agent manually to see what happens:

```powershell
$env:SIEM_API_URL = "http://YOUR_HUB_IP:8010"
$env:SIEM_API_KEY = "your-secure-api-key"
cd "C:\Program Files\Heimdall"
python agents\agent_windows.py
```

You should see:
- Connection test results
- Event collection status
- Send success/failure messages

## Common Issues

### Issue 1: Wrong API URL
**Symptom:** Agent connects to localhost:8000 instead of YOUR_HUB_IP:8010

**Fix:** Use batch file wrapper (see Step 3)

### Issue 2: Wrong API Key
**Symptom:** Authentication errors (403 Forbidden)

**Fix:** Verify API key matches exactly:
```
your-secure-api-key
```

### Issue 3: Firewall Blocking
**Symptom:** Connection timeout or "Connection refused"

**Fix:** 
```powershell
# Test connectivity
Test-NetConnection -ComputerName YOUR_HUB_IP -Port 8010

# If blocked, allow Python through firewall
New-NetFirewallRule -DisplayName "Heimdall Agent Outbound" -Direction Outbound -Program "C:\Python310\python.exe" -Action Allow
```

### Issue 4: No Events to Send
**Symptom:** Agent runs but sends 0 events

**Fix:** 
- Check Security event log has events (Event IDs 4625, 4720, 1102)
- Generate test events (failed login, create user, etc.)
- Verify agent runs as Administrator

### Issue 5: Agent Not Running
**Symptom:** No process running

**Fix:**
```powershell
# Check task status
Get-ScheduledTask -TaskName "Heimdall Agent"

# Check if task is enabled
$task = Get-ScheduledTask -TaskName "Heimdall Agent"
$task.State

# Start if stopped
Start-ScheduledTask -TaskName "Heimdall Agent"
```

## Quick Verification

After fixing, verify it's working:

1. **Check agent is running:**
   ```powershell
   Get-Process python | Where-Object {$_.CommandLine -like "*agent_windows*"}
   ```

2. **Check logs show connection:**
   ```powershell
   Get-Content "C:\Program Files\Heimdall\agent.log" | Select-String "API connection\|Sent.*events"
   ```

3. **Check dashboard shows host:**
   - Visit http://YOUR_HUB_IP:8501
   - Check "Host Status" section
   - Should see your Windows hostname in "Active Hosts"

4. **Check server logs:**
   ```bash
   ssh n0de@YOUR_HUB_IP "cd ~/heimdall && docker-compose logs | grep -i ingest"
   ```

## Still Not Working?

Run the diagnostic script and share the output. The improved agent will now show detailed error messages that will help identify the exact issue.
