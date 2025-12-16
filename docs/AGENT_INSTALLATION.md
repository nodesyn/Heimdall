# Heimdall Agent Installation Guide

Complete instructions for installing and configuring Heimdall agents on various platforms.

## Prerequisites

Before installing agents, ensure:
1. **Heimdall Hub is deployed** and accessible at `http://YOUR_HUB_IP`
2. **API key is configured** (get from your Heimdall hub administrator)
3. **Python 3.10+** is installed on the target host
4. **Network connectivity** from agent host to hub (port 8010)

## Quick Start

All agents require these environment variables:
```bash
export SIEM_API_URL=http://YOUR_HUB_IP
export SIEM_API_KEY=your-api-key-here
```

---

## Linux Agent

### Prerequisites
- Debian/Ubuntu or RHEL/CentOS
- Read access to `/var/log/auth.log` (Debian/Ubuntu) or `/var/log/secure` (RHEL/CentOS)
- Python 3.10+
- Root or sudo access for systemd service

### Installation Steps (Automated)

The recommended way to install the Linux agent is using the provided installer script. This script handles dependencies (creating a virtual environment), configuration, and systemd service setup automatically.

1.  **Transfer Files:** Copy `agents/install_linux_agent.sh` and `agents/agent_linux.py` to the target machine.
2.  **Run Installer:**
    ```bash
    chmod +x install_linux_agent.sh
    sudo ./install_linux_agent.sh http://YOUR_HUB_IP:8010 YOUR_API_KEY
    ```

The script will:
*   Install Python 3 and `pip` if missing.
*   Create a virtual environment in `/opt/heimdall/venv`.
*   Install required libraries (`requests`, `psutil`, `python-dateutil`).
*   Create the configuration file at `/etc/heimdall/agent.env`.
*   Install and start the `heimdall-agent` systemd service.

### Manual Installation (Alternative)

If you prefer to install manually:

#### 1. Install Python Dependencies
```bash
pip3 install requests python-dateutil psutil
```

#### 2. Download Agent
```bash
# Clone or download the Heimdall repository
cd /opt
git clone <repository-url> heimdall
# Or copy agents/agent_linux.py to /opt/heimdall/
```

#### 3. Create Configuration File
```bash
sudo mkdir -p /etc/heimdall
sudo tee /etc/heimdall/agent.env << EOF
SIEM_API_URL=http://YOUR_HUB_IP
SIEM_API_KEY=your-api-key-here
SIEM_LINUX_INTERVAL=30
# SIEM_LOG_FILES=/var/log/auth.log,/var/log/syslog
EOF
```

#### 4. Create Systemd Service
```bash
sudo tee /etc/systemd/system/heimdall-agent.service << EOF
[Unit]
Description=Heimdall Linux Security Agent
After=network.target

[Service]
Type=simple
User=root
EnvironmentFile=/etc/heimdall/agent.env
WorkingDirectory=/opt/heimdall
ExecStart=/usr/bin/python3 /opt/heimdall/agents/agent_linux.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### 5. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable heimdall-agent
sudo systemctl start heimdall-agent
sudo systemctl status heimdall-agent
```

### Verification
```bash
# Check service status
sudo systemctl status heimdall-agent

# View logs
sudo journalctl -u heimdall-agent -f

# Test manually
cd /opt/heimdall
export SIEM_API_URL=http://YOUR_HUB_IP
export SIEM_API_KEY=your-api-key-here
python3 agents/agent_linux.py
```

### Events Monitored
- Failed password attempts
- Invalid user login attempts
- Sudo command execution
- Authentication failures

---

## Windows Agent

### Prerequisites
- Windows 7 or later
- Administrator privileges (to read Security event log)
- Python 3.10+
- pywin32 library

### Installation Steps (Simplified)

The easiest way to deploy the Windows agent is using the smart PowerShell installer, which handles dependencies and service creation for you.

#### 1. Prepare the Installation Package
On your development machine:
1.  Create a folder containing:
    *   `agent_windows.py` (Latest version)
    *   `Install-HeimdallAgent.ps1`
    *   `agent.env` (Configuration file)
2.  Edit `agent.env` with your Hub details:
    ```env
    SIEM_API_URL=http://YOUR_HUB_IP:8010
    SIEM_API_KEY=your-api-key
    SIEM_AGENT_INTERVAL=60
    HEIMDALL_LOG_DIR=C:\Heimdall\logs
    ```
3.  Zip these files together.

#### 2. Deploy and Install
On the target Windows machine:
1.  Unzip the package.
2.  Open PowerShell as **Administrator**.
3.  Run the installer:
    ```powershell
    .\Install-HeimdallAgent.ps1
    ```

The script will automatically:
*   Check for Python 3.10+ (and warn if missing).
*   Install required Python libraries (`requests`, `psutil`, `pywin32`) via pip.
*   Download `nssm.exe` (Service Manager) if needed.
*   Install the agent as a Windows Service ("HeimdallAgent").
*   Start the service immediately.

#### 3. Verification
Check the logs at `C:\Heimdall\logs\agent.log` to confirm it is running and sending data.

### Manual Installation (Legacy / Advanced)

#### 1. Install Python Dependencies
```powershell
pip install requests python-dateutil pywin32 psutil
python -m pip install --upgrade pywin32
```

#### 2. Download Agent
```powershell
# Clone or download the Heimdall repository
# Copy agents/agent_windows.py to C:\Heimdall\
```

#### 3. Create Configuration File
Create `C:\Heimdall\agent.env`:
```env
SIEM_API_URL=http://YOUR_HUB_IP
SIEM_API_KEY=your-api-key-here
SIEM_WINDOWS_INTERVAL=60
```

#### 4. Create Wrapper Batch File (Required for Scheduled Tasks)

**Important:** Scheduled Tasks don't inherit environment variables. Create a batch file to set them:

Create `C:\Heimdall\run_agent.bat`:
```batch
@echo off
set SIEM_API_URL=http://YOUR_HUB_IP
set SIEM_API_KEY=your-api-key-here
cd /d "C:\Heimdall"
python agent_windows.py
```

Replace `your-api-key-here` with your actual API key from the deployment.

#### 5. Install as Windows Service (Recommended: NSSM)

**NSSM (Non-Sucking Service Manager)** is the most reliable way to run the agent as a Windows Service.

##### Step 1: Download and Extract NSSM

```powershell
# Create temp directory
$nssm_temp = "$env:TEMP\nssm_download"
New-Item -ItemType Directory -Path $nssm_temp -Force | Out-Null

# Download NSSM
Invoke-WebRequest -Uri "https://nssm.cc/download/nssm-2.24.zip" -OutFile "$nssm_temp\nssm.zip"

# Extract
Expand-Archive -Path "$nssm_temp\nssm.zip" -DestinationPath "C:\Heimdall" -Force

# Verify extraction
Get-ChildItem "C:\Heimdall\nssm-2.24\win64\nssm.exe"
```

##### Step 2: Install Service

Run PowerShell **as Administrator**:

```powershell
# Define paths
$nssm_exe = "C:\Heimdall\nssm-2.24\win64\nssm.exe"
$python_exe = "$((py -3.11 -c 'import sys; print(sys.executable)') 2>$null)" # Auto-detect Python path
$agent_script = "C:\Heimdall\agent_windows.py"
$work_dir = "C:\Heimdall"

# If auto-detect failed, set manually (adjust version as needed)
if (-not $python_exe) {
    $python_exe = "C:\Python311\python.exe"
}

# Install service
& $nssm_exe install "Heimdall Agent" $python_exe "-u $agent_script"

# Set working directory
& $nssm_exe set "Heimdall Agent" AppDirectory $work_dir

# Set environment variables
& $nssm_exe set "Heimdall Agent" AppEnvironmentExtra "SIEM_API_URL=http://YOUR_HUB_IP SIEM_API_KEY=your-api-key-here PYTHONIOENCODING=utf-8"

# Configure to restart on failure
& $nssm_exe set "Heimdall Agent" AppRestartDelay 5000

# Start the service
Start-Service -Name "Heimdall Agent"

# Verify
Get-Service -Name "Heimdall Agent"
```

**Replace `your-api-key-here` with your actual API key.**

##### Verify Service is Running

```powershell
# Check service status
Get-Service -Name "Heimdall Agent" | Select-Object Status, DisplayName

# Check if Python process is running
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*agent_windows.py*"}

# View service info
sc query "Heimdall Agent"
```

##### Uninstall Service (if needed)

```powershell
$nssm_exe = "C:\Heimdall\nssm-2.24\win64\nssm.exe"

# Stop service
Stop-Service -Name "Heimdall Agent" -Force

# Uninstall service
& $nssm_exe remove "Heimdall Agent" confirm
```

##### Troubleshooting

- **Service won't start:** Verify Python path is correct
- **API not responding:** Check `SIEM_API_URL` and `SIEM_API_KEY` environment variables
- **View service logs:** Check Windows Event Viewer → Windows Logs → System

### Verification

Check dashboard at `http://YOUR_HUB_IP:8501` and look for your hostname in the "Active Hosts" section.

```powershell
# View agent logs (check Event Viewer for service events)
Get-EventLog -LogName System -Source "NSSM" -Newest 5

# Test manually (for troubleshooting)
$env:SIEM_API_URL="http://YOUR_HUB_IP"
$env:SIEM_API_KEY="your-api-key-here"
python "C:\Program Files\Heimdall\agent_windows.py"
```

### Events Monitored
- Event ID 4625: Failed logon attempts
- Event ID 4720: User account creation
- Event ID 1102: Security log cleared/tampered

---

## macOS Agent

### Prerequisites
- macOS 10.12 or later
- Python 3.10+
- Read access to system logs

### Installation Steps

#### 1. Install Python Dependencies
```bash
pip3 install requests python-dateutil
```

#### 2. Download Agent
```bash
# Clone or download the Heimdall repository
cd /opt
sudo mkdir -p heimdall
# Copy agents/agent_macos.py to /opt/heimdall/
```

#### 3. Create LaunchAgent Configuration
```bash
sudo tee ~/Library/LaunchAgents/com.heimdall.agent.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.heimdall.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/opt/heimdall/agents/agent_macos.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>SIEM_API_URL</key>
        <string>http://YOUR_HUB_IP</string>
        <key>SIEM_API_KEY</key>
        <string>your-api-key-here</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/heimdall-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/heimdall-agent.error.log</string>
</dict>
</plist>
EOF
```

#### 4. Load LaunchAgent
```bash
launchctl load ~/Library/LaunchAgents/com.heimdall.agent.plist
launchctl start com.heimdall.agent
```

### Verification
```bash
# Check status
launchctl list | grep heimdall

# View logs
tail -f /var/log/heimdall-agent.log

# Test manually
export SIEM_API_URL=http://YOUR_HUB_IP
export SIEM_API_KEY=your-api-key-here
python3 /opt/heimdall/agents/agent_macos.py
```

### Events Monitored
- Failed password attempts
- Invalid user logins
- Sudo command execution
- Sudo authentication failures
- Kernel audit messages

---

## Pi-hole Agent

### Prerequisites
- Pi-hole 5.0 or later installed
- SQLite database at `/etc/pihole/pihole-FTL.db`
- Read access to Pi-hole database
- Python 3.10+

### Installation Steps

#### 1. Install Python Dependencies
```bash
pip3 install requests python-dateutil
```

#### 2. Download Agent
```bash
cd /opt
sudo mkdir -p heimdall
# Copy agents/agent_pihole.py to /opt/heimdall/
```

#### 3. Create Configuration File
```bash
sudo tee /etc/heimdall/pihole-agent.env << EOF
SIEM_API_URL=http://YOUR_HUB_IP
SIEM_API_KEY=your-api-key-here
SIEM_PIHOLE_DB_PATH=/etc/pihole/pihole-FTL.db
SIEM_PIHOLE_INTERVAL=60
EOF
```

#### 4. Create Systemd Service
```bash
sudo tee /etc/systemd/system/heimdall-pihole.service << EOF
[Unit]
Description=Heimdall Pi-hole Security Agent
After=network.target pihole-FTL.service

[Service]
Type=simple
User=root
EnvironmentFile=/etc/heimdall/pihole-agent.env
WorkingDirectory=/opt/heimdall
ExecStart=/usr/bin/python3 /opt/heimdall/agents/agent_pihole.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### 5. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable heimdall-pihole
sudo systemctl start heimdall-pihole
sudo systemctl status heimdall-pihole
```

### Verification
```bash
# Check service status
sudo systemctl status heimdall-pihole

# View logs
sudo journalctl -u heimdall-pihole -f

# Verify Pi-hole database access
sudo sqlite3 /etc/pihole/pihole-FTL.db "SELECT COUNT(*) FROM queries LIMIT 1"
```

### Events Monitored
- Blocked DNS queries (status codes 1, 4, 5, 9, 10, 11)
- Malicious domain blocks
- Ad blocking events

---

## Firewall Agent

### Prerequisites
- Access to firewall log files
- Python 3.10+
- Read permissions for log files

### Supported Firewall Types
- Generic (custom log path)
- iptables/netfilter
- UFW (Uncomplicated Firewall)
- pfSense/OPNsense

### Installation Steps

#### 1. Install Python Dependencies
```bash
pip3 install requests python-dateutil
```

#### 2. Download Agent
```bash
cd /opt
sudo mkdir -p heimdall
# Copy agents/agent_firewall.py to /opt/heimdall/
```

#### 3. Configure Firewall Logging

**For iptables:**
```bash
# Enable logging in iptables rules
sudo iptables -A INPUT -j LOG --log-prefix "IPTABLES: "
sudo iptables -A FORWARD -j LOG --log-prefix "IPTABLES: "
# Logs go to /var/log/kern.log or /var/log/syslog
```

**For UFW:**
```bash
# UFW logs to /var/log/ufw.log
sudo ufw logging on
```

**For pfSense/OPNsense:**
- Logs typically at `/var/log/filter.log`

#### 4. Create Configuration File
```bash
sudo tee /etc/heimdall/firewall-agent.env << EOF
SIEM_API_URL=http://YOUR_HUB_IP
SIEM_API_KEY=your-api-key-here
FIREWALL_TYPE=iptables
FIREWALL_LOG_PATH=/var/log/kern.log
EOF
```

#### 5. Create Systemd Service
```bash
sudo tee /etc/systemd/system/heimdall-firewall.service << EOF
[Unit]
Description=Heimdall Firewall Security Agent
After=network.target

[Service]
Type=simple
User=root
EnvironmentFile=/etc/heimdall/firewall-agent.env
WorkingDirectory=/opt/heimdall
ExecStart=/usr/bin/python3 /opt/heimdall/agents/agent_firewall.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### 6. Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable heimdall-firewall
sudo systemctl start heimdall-firewall
sudo systemctl status heimdall-firewall
```

### Verification
```bash
# Check service status
sudo systemctl status heimdall-firewall

# View logs
sudo journalctl -u heimdall-firewall -f

# Test manually
export SIEM_API_URL=http://YOUR_HUB_IP
export SIEM_API_KEY=your-api-key-here
export FIREWALL_TYPE=iptables
export FIREWALL_LOG_PATH=/var/log/kern.log
python3 /opt/heimdall/agents/agent_firewall.py
```

### Events Monitored
- Blocked connections (severity 2)
- Port scan attempts (severity 4)
- Intrusion attempts (severity 5)
- Firewall rule violations

---

## Troubleshooting

### Agent Cannot Connect to Hub

**Symptoms:** Agent logs show connection errors

**Solutions:**
1. Verify network connectivity:
   ```bash
   curl http://YOUR_HUB_IP/health
   ```

2. Check firewall rules:
   ```bash
   # Linux
   sudo iptables -L -n | grep 8010
   
   # Windows
   netsh advfirewall firewall show rule name=all | findstr 8010
   ```

3. Verify API key matches hub configuration

4. Check DNS resolution:
   ```bash
   ping YOUR_HUB_IP
   nslookup YOUR_HUB_IP
   ```

### No Events Being Collected

**Symptoms:** Dashboard shows no events from agent

**Solutions:**
1. Check agent logs for errors
2. Verify log file permissions (Linux/macOS)
3. Verify event log access (Windows - run as Administrator)
4. Test agent manually to see output
5. Check database path (Pi-hole agent)

### Service Fails to Start

**Symptoms:** systemd/LaunchAgent/Task Scheduler shows failed status

**Solutions:**
1. Check service logs:
   ```bash
   # Linux
   sudo journalctl -u heimdall-agent -n 50
   
   # macOS
   tail -f /var/log/heimdall-agent.log
   
   # Windows
   # Check Event Viewer > Windows Logs > Application
   ```

2. Verify Python path is correct
3. Check file permissions
4. Verify environment variables are set correctly

### High CPU/Memory Usage

**Solutions:**
1. Increase polling interval:
   ```bash
   export SIEM_LINUX_INTERVAL=60  # Increase from 30 to 60 seconds
   ```

2. Check for log file rotation issues
3. Verify agent is not processing duplicate events

---

## Security Best Practices

1. **Use Strong API Keys**
   ```bash
   openssl rand -hex 32
   ```

2. **Restrict Network Access**
   - Use firewall rules to limit access to hub IP
   - Consider VPN for remote agents

3. **File Permissions**
   ```bash
   # Linux/macOS
   chmod 600 /etc/heimdall/*.env
   chown root:root /etc/heimdall/*.env
   ```

4. **Service Account**
   - Run agents with minimal required privileges
   - Use dedicated service accounts when possible

5. **Log Rotation**
   - Configure log rotation for agent logs
   - Monitor disk space usage

---

## Testing Agent Connectivity

After installation, test agent connectivity:

```bash
# Test API endpoint
curl -H "api-key: your-api-key-here" http://YOUR_HUB_IP/health

# Should return:
# {"status":"healthy","timestamp":"...","api_version":"1.0.0"}

# Send test event manually
python3 -c "
import requests
import os
from datetime import datetime

api_url = 'http://YOUR_HUB_IP'
api_key = 'your-api-key-here'

test_event = {
    'events': [{
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'source_host': 'test-host',
        'os_type': 'LINUX',
        'event_type': 'LOGIN_FAIL',
        'severity': 3,
        'source_ip': '192.168.1.100',
        'user': 'testuser',
        'raw_message': 'Test event from agent installation'
    }]
}

response = requests.post(
    f'{api_url}/ingest',
    json=test_event,
    headers={'api-key': api_key}
)
print(response.json())
"
```

---

## Next Steps

After installing agents:
1. Verify events appear in Heimdall dashboard
2. Configure Telegram alerts (optional)
3. Set up log rotation
4. Monitor agent health
5. Review security events regularly

For support, refer to the main Heimdall documentation or check agent logs for detailed error messages.
