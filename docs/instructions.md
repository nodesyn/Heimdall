# Heimdall - Security Monitoring Platform
## Deployment & Usage Guide

**Standing Guard Over Your Infrastructure**

## Overview

Heimdall is a modern, modular security monitoring platform built with Python. It follows a "Hub and Spoke" architecture designed for visibility across your entire infrastructure:

- **Agents (Spokes):** Lightweight collectors on Windows, Linux, macOS, Firewalls, and Pi-hole
- **Server (Hub):** FastAPI backend ingesting and correlating all events
- **Dashboard (Interface):** Real-time Streamlit UI for security intelligence
- **Alerting (Notifications):** Instant Telegram notifications for critical events

## System Requirements

- **Python:** 3.10 or higher
- **OS Support:** Windows, Linux, macOS (agents), any OS (server & dashboard)
- **Database:** SQLite 3.x (included with Python)
- **Network:** Agents must have network access to the server

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note for Windows:** On Windows systems, you must also install pywin32:
```bash
pip install pywin32
python -m pip install --upgrade pywin32
```

### 2. Environment Variables

Create a `.env` file or set environment variables:

```bash
# API Configuration
SIEM_API_URL=http://localhost:8000          # Server URL (used by agents)
SIEM_API_KEY=your-secure-api-key-here       # Must match on all agents and dashboard

# Telegram Alerting (Optional but recommended)
TELEGRAM_BOT_TOKEN=your_bot_token_here      # Get from @BotFather
TELEGRAM_CHAT_ID=your_chat_id_here          # Get from @userinfobot

# Firewall Agent Configuration (Optional)
FIREWALL_TYPE=generic                       # generic|iptables|ufw|pfsense|opnsense
FIREWALL_LOG_PATH=/var/log/firewall.log     # Path to firewall log file

# Alert Thresholds (Optional)
ALERT_CRITICAL_THRESHOLD=5                  # Severity level for critical alerts
ALERT_HIGH_THRESHOLD=3                      # Severity level for high alerts

# Optional
PIHOLE_DB_PATH=/etc/pihole/pihole-FTL.db   # Pi-hole database location
```

## Component Details

### Database Schema

The unified data schema normalizes all logs:

```json
{
  "event_id": "UUID-v4",
  "timestamp": "ISO-8601 String (UTC)",
  "source_host": "hostname",
  "os_type": "WINDOWS|LINUX|PIHOLE",
  "event_type": "LOGIN_FAIL|SUDO_ESCALATION|DNS_BLOCK|CRITICAL_ERROR|ACCOUNT_CREATE|LOG_TAMPERING",
  "severity": 1-5,
  "source_ip": "IPv4/IPv6 or N/A",
  "user": "username or system",
  "raw_message": "original log line"
}
```

### Event Types & Severity

| Event Type | OS | Severity | Description |
|---|---|---|---|
| LOGIN_FAIL | WINDOWS, LINUX | 3 | Failed authentication attempt |
| SUDO_ESCALATION | LINUX | 2 | Sudo command execution |
| DNS_BLOCK | PIHOLE | 1 | Blocked DNS query |
| ACCOUNT_CREATE | WINDOWS | 4 | New user account created |
| LOG_TAMPERING | WINDOWS | 5 | Security log cleared/tampered |
| CRITICAL_ERROR | Any | 5 | Critical system error |

Severity Levels:
- 1 = Info
- 2 = Low
- 3 = Medium
- 4 = High
- 5 = Critical

## Deployment Guide

### Server Setup

#### 1. Initialize Database

```bash
python -m core.database
```

This creates `mini_siem.db` with proper schema and indices.

#### 2. Start FastAPI Server

```bash
# Development mode
python -m core.server_api

# Or with Uvicorn directly
uvicorn core.server_api:app --host 0.0.0.0 --port 8000

# Production mode (with multiple workers)
uvicorn core.server_api:app --host 0.0.0.0 --port 8000 --workers 4
```

The server will listen on `http://0.0.0.0:8000` by default.

**API Endpoints:**

- `GET /` - Health check
- `POST /ingest` - Log ingestion (requires api-key header)
- `GET /events` - Query events (with optional filters)
- `GET /metrics` - Get dashboard metrics
- `GET /health` - Detailed health check

### Agent Deployment

#### Windows Agent

**Prerequisites:**
- Windows 7 or later
- Administrator privileges to read Security event log
- pywin32 installed

**Deployment Methods:**

Option 1: Run as Background Script
```bash
set SIEM_API_URL=http://your-server-ip:8000
set SIEM_API_KEY=your-api-key
python agents/agent_windows.py
```

Option 2: Run as Windows Service (Recommended)
```bash
# Create a .bat file to run the agent at startup
# Add to Task Scheduler with "System" privileges
# or install as service using nssm (Non-Sucking Service Manager)

nssm install "SIEM Agent Windows" python C:\path\to\agents\agent_windows.py
nssm start "SIEM Agent Windows"
```

Option 3: Run as Scheduled Task
```powershell
# Create a scheduled task running every 5 minutes
$action = New-ScheduledTaskAction -Execute 'C:\Python310\python.exe' `
  -Argument 'C:\path\to\agents\agent_windows.py'
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) `
  -At (Get-Date) -RepetitionDuration (New-TimeSpan -Days 365)
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "SIEM Agent"
```

**Events Monitored:**
- Event ID 4625: Failed logon
- Event ID 4720: User created
- Event ID 1102: Log cleared

#### Linux Agent

**Prerequisites:**
- Debian/Ubuntu or RHEL/CentOS
- Read access to `/var/log/auth.log` or `/var/log/secure`
- Python 3.10+

**Deployment Methods:**

Option 1: Run as Background Process
```bash
export SIEM_API_URL=http://your-server-ip:8000
export SIEM_API_KEY=your-api-key
nohup python agents/agent_linux.py > agent.log 2>&1 &
```

Option 2: Run as Systemd Service (Recommended)
```ini
# /etc/systemd/system/siem-agent-linux.service

[Unit]
Description=SIEM Linux Agent
After=network.target

[Service]
Type=simple
User=root
Environment="SIEM_API_URL=http://your-server-ip:8000"
Environment="SIEM_API_KEY=your-api-key"
ExecStart=/usr/bin/python3 /path/to/agents/agent_linux.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable siem-agent
sudo systemctl start siem-agent
sudo systemctl status siem-agent
```

**Events Monitored:**
- Failed password attempts
- Invalid user login attempts
- Sudo command execution

#### Pi-hole Agent

**Prerequisites:**
- Pi-hole 5.0 or later
- SQLite database at `/etc/pihole/pihole-FTL.db`
- Database read permissions for the running user

**Deployment:**

```bash
export SIEM_API_URL=http://your-server-ip:8000
export SIEM_API_KEY=your-api-key
python agents/agent_pihole.py
```

Run as systemd service (same approach as Linux agent above).

**Events Monitored:**
- Blocked DNS queries (status codes 1, 4, 5, 9, 10, 11)

#### macOS Agent

**Prerequisites:**
- macOS 10.12 or later
- Read access to log files
- Python 3.10+

**Deployment:**

```bash
export SIEM_API_URL=http://your-server-ip:8000
export SIEM_API_KEY=your-api-key
python agents/agent_macos.py
```

**Events Monitored:**
- Failed password attempts
- Invalid user logins
- Sudo command execution
- Sudo authentication failures
- Kernel audit messages

Run as systemd service (macOS uses launchd, see `instructions.md` section "Run as LaunchAgent").

#### Firewall Agent

**Prerequisites:**
- Access to firewall log files
- Python 3.10+

**Supported Firewall Types:**
- Generic (reads from custom log path)
- iptables/netfilter
- UFW (Uncomplicated Firewall)
- pfSense/OPNsense

**Deployment:**

```bash
# Generic firewall (default)
export FIREWALL_TYPE=generic
export FIREWALL_LOG_PATH=/var/log/firewall.log
python agents/agent_firewall.py

# Or specific type
export FIREWALL_TYPE=iptables
python agents/agent_firewall.py

export FIREWALL_TYPE=ufw
python agents/agent_firewall.py

export FIREWALL_TYPE=pfsense
python agents/agent_firewall.py
```

**Events Monitored:**
- Blocked connections (severity 2)
- Port scan attempts (severity 4)
- Intrusion attempts (severity 5)

Run as systemd service (same approach as Linux agent above).

### Telegram Alerting Setup

**Prerequisites:**
- Telegram account
- Telegram bot token (from @BotFather)
- Your Telegram chat ID (from @userinfobot)

**Step 1: Create Telegram Bot**

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to create your bot
4. Save your bot token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

**Step 2: Get Your Chat ID**

1. Open Telegram and search for `@userinfobot`
2. Send any message to get your chat ID
3. Save your chat ID (e.g., `123456789`)

**Step 3: Configure Environment**

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"

# Optional: Set alert thresholds
export ALERT_CRITICAL_THRESHOLD=5
export ALERT_HIGH_THRESHOLD=3
```

**Step 4: Test Telegram Connection**

```bash
python -m alerts.telegram_alerts
```

You should receive a test message on your Telegram chat.

**Alert Types**

The system automatically sends Telegram alerts for:
- **Critical Events** (severity 5) - Immediate notification
- **High-Severity Events** (severity 4) - Grouped alerts
- **Daily Metrics Report** - 24-hour summary (if activity detected)
- **Agent Status Updates** - Online/offline notifications
- **System Status** - Server status changes

**Customizing Alerts**

Edit `alerts/telegram_alerts.py` to:
- Change alert message formats
- Add new alert types
- Adjust notification thresholds
- Integrate with other services (Slack, Email, etc.)

### Dashboard Setup

Start the Streamlit dashboard:

```bash
export SIEM_API_URL=http://your-server-ip:8000
export SIEM_API_KEY=your-api-key
streamlit run ui/dashboard.py
```

The dashboard will open at `http://localhost:8501`

**Features:**
- Real-time metrics for the last 24 hours
- Events per minute timeline chart
- Top attacking IPs bar chart
- Threat distribution pie chart
- Detailed event table with filtering
- Export data as CSV/JSON

## Testing & Validation

### 1. Generate Test Data

Create a test script to send sample events:

```python
import requests
from models import LogEvent
from datetime import datetime

api_url = "http://localhost:8000"
api_key = "your-api-key"

events = [
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_host": "test-host",
        "os_type": "LINUX",
        "event_type": "LOGIN_FAIL",
        "severity": 3,
        "source_ip": "192.168.1.100",
        "user": "admin",
        "raw_message": "Failed password for admin from 192.168.1.100"
    }
]

response = requests.post(
    f"{api_url}/ingest",
    json={"events": events},
    headers={"api-key": api_key}
)
print(response.json())
```

### 2. Query API Directly

```bash
# Get events
curl -H "api-key: your-api-key" http://localhost:8000/events

# Get metrics
curl -H "api-key: your-api-key" http://localhost:8000/metrics

# Filter by OS
curl -H "api-key: your-api-key" "http://localhost:8000/events?os_type=LINUX"
```

### 3. Monitor Agent Logs

Check agent output for ingestion success:

```bash
tail -f agent.log
```

Look for lines like:
```
✓ Sent 5 events to API
```

## Security Best Practices

1. **Change Default API Key**
   ```bash
   export SIEM_API_KEY=$(openssl rand -hex 32)
   ```

2. **Use HTTPS in Production**
   - Deploy behind a reverse proxy (nginx, Apache)
   - Use SSL certificates (Let's Encrypt)
   - Update agent URLs to use `https://`

3. **Firewall Rules**
   - Restrict API access to trusted agents
   - Use IP whitelisting at network level
   - Block direct dashboard access from internet

4. **Database Security**
   - Store `mini_siem.db` on encrypted volume
   - Set restrictive file permissions (600)
   - Consider PostgreSQL for production scale

5. **Log Rotation**
   - Implement log rotation for agents
   - Archive database periodically
   - Set retention policies

## Troubleshooting

### Agent Can't Connect to Server

```bash
# Test connectivity
curl http://your-server-ip:8000/health

# Check firewall
netstat -tuln | grep 8000  # Linux
netstat -ano | findstr :8000  # Windows
```

### Missing Event Log Data

**Windows:**
- Run agent as Administrator
- Check Event Viewer > Security log has entries
- Verify event IDs 4625, 4720, 1102 exist

**Linux:**
- Verify file exists: `ls -la /var/log/auth.log`
- Check read permissions
- Tail the file: `tail -f /var/log/auth.log`

**Pi-hole:**
- Verify database: `ls -la /etc/pihole/pihole-FTL.db`
- Check Pi-hole is running: `sudo systemctl status pihole-FTL`
- Query database: `sqlite3 /etc/pihole/pihole-FTL.db "SELECT COUNT(*) FROM queries"`

### Database Locked

SQLite with WAL mode handles concurrency. If you see "database is locked":

```bash
# Check if processes are holding locks
lsof | grep mini_siem.db

# If needed, restart the server
```

### Dashboard Slow

- Reduce `limit` parameter in filters (default 500)
- Archive old events to separate database
- Consider upgrading to PostgreSQL

## Production Checklist

- [ ] Change default API key
- [ ] Configure HTTPS/TLS
- [ ] Set up agent systemd services
- [ ] Configure log rotation
- [ ] Set up database backups
- [ ] Configure monitoring/alerting
- [ ] Test failover scenarios
- [ ] Document deployment
- [ ] Train security team
- [ ] Set up log retention policies

## Performance Tuning

### SQLite Optimization

```sql
-- Run these manually to optimize
PRAGMA optimize;
VACUUM;
```

### Archive Old Events

```python
# Archive events older than 90 days
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("mini_siem.db")
cursor = conn.cursor()

cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
cursor.execute("SELECT COUNT(*) FROM logs WHERE timestamp < ?", (cutoff,))
count = cursor.fetchone()[0]

# Backup first
cursor.execute("ATTACH DATABASE 'archive.db' AS archive")
cursor.execute("CREATE TABLE IF NOT EXISTS archive.logs AS SELECT * FROM logs WHERE timestamp < ?", (cutoff,))
cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))

conn.commit()
conn.close()
```

## Future Enhancements

- [ ] PostgreSQL support for enterprise scale
- [ ] ElasticSearch integration for log indexing
- [ ] Machine learning for anomaly detection
- [ ] Slack/email alerting
- [ ] Multi-tenancy support
- [ ] Web UI for agent management
- [ ] MacOS agent
- [ ] Firewall/WAF log ingestion
- [ ] Performance metrics dashboard
- [ ] Automated threat response playbooks

## Support & Contributing

For issues or contributions, refer to the project documentation.

---

**Version:** 1.0.0  
**Last Updated:** 2024-01-15

