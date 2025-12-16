# Heimdall V2.0 - Quick Start Guide

## What's New in V2.0

Heimdall V2.0 adds support for more platforms and integrations:

- ✅ **macOS Agent** - Monitor macOS systems
- ✅ **Firewall Agent** - Collect firewall logs
- ✅ **Telegram Alerts** - Real-time security notifications
- ✅ **Modular Architecture** - Better code organization
- ✅ **Enhanced Data Models** - Support for new event types

---

## Installation

### 1. Clone and Setup
```bash
cd /home/n0desyn/Nexus/coding/Heimdall
source /home/n0desyn/venvs/mini_siem/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python -m core.database
```

---

## Running Heimdall

### Terminal 1: Start API Server
```bash
python -m core.server_api
# API runs at http://localhost:8000
```

### Terminal 2: Start Dashboard
```bash
streamlit run ui/dashboard.py
# Dashboard runs at http://localhost:8501
```

### Terminal 3: Deploy Agents
Choose which agents to run:

**Linux:**
```bash
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=default-insecure-key-change-me
python agents/agent_linux.py
```

**Windows (requires Administrator):**
```powershell
$env:SIEM_API_URL = "http://localhost:8000"
$env:SIEM_API_KEY = "default-insecure-key-change-me"
python agents/agent_windows.py
```

**macOS:**
```bash
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=default-insecure-key-change-me
python agents/agent_macos.py
```

**Firewall:**
```bash
export FIREWALL_TYPE=iptables  # or ufw, pfsense, opnsense, generic
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=default-insecure-key-change-me
python agents/agent_firewall.py
```

**Pi-hole (runs on Pi-hole server):**
```bash
export SIEM_API_URL=http://your-server:8000
export SIEM_API_KEY=default-insecure-key-change-me
python agents/agent_pihole.py
```

---

## Testing

### Generate Sample Data
```bash
python tests/test_api.py
```

This will:
- Generate sample events from all agent types
- Submit them to the API
- Verify the API processes them correctly
- Display dashboard metrics

---

## Configuration

### Environment Variables
Set these for custom configuration:

```bash
# API Configuration
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=your-secure-key

# Database
export SIEM_DATABASE_PATH=mini_siem.db

# Telegram Alerts (optional)
export TELEGRAM_BOT_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id

# Firewall Agent
export FIREWALL_TYPE=generic
export FIREWALL_LOG_PATH=/var/log/firewall.log
```

### Change API Key (IMPORTANT!)
For production use, always change the default API key:

```bash
export SIEM_API_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

---

## Dashboard Features

### Key Metrics (24-hour)
- Total alerts count
- Threats by OS breakdown
- Most blocked domain

### Charts
- Events per minute (by OS)
- Top attacking IPs
- Threat distribution by OS

### Filtering
- Filter by OS (Windows, Linux, macOS, Pi-hole, Firewall)
- Filter by severity (Critical, High, Medium, Low, Info)
- Filter by event type
- Export as CSV or JSON

---

## Supported Event Types

### By Agent

**Linux Agent**
- LOGIN_FAIL
- SUDO_ESCALATION

**Windows Agent**
- LOGIN_FAIL
- ACCOUNT_CREATE
- LOG_TAMPERING

**macOS Agent**
- LOGIN_FAIL
- SUDO_ESCALATION
- CRITICAL_ERROR

**Firewall Agent**
- CONNECTION_BLOCKED
- PORT_SCAN
- CRITICAL_ERROR

**Pi-hole Agent**
- DNS_BLOCK

---

## Troubleshooting

### Port Already in Use
```bash
# Change API port
python -m core.server_api --port 8001

# Change dashboard port
streamlit run ui/dashboard.py --server.port 8502
```

### Can't Connect to API
```bash
# Check if API is running
curl http://localhost:8000/health

# Check firewall rules
netstat -tuln | grep 8000
```

### Agent Can't Connect to API
```bash
# Verify API URL
echo $SIEM_API_URL

# Test connection
curl -H "api-key: $SIEM_API_KEY" http://localhost:8000/events
```

### No Data in Dashboard
1. Run test: `python tests/test_api.py`
2. Check database: `sqlite3 mini_siem.db "SELECT COUNT(*) FROM logs;"`
3. Refresh browser (F5)
4. Check browser console (F12)

---

## Production Deployment

For production use:

1. **Change API Key** - Use a strong, unique key
2. **Enable HTTPS** - Use a reverse proxy (nginx, Apache)
3. **Database Backups** - Set up automated backups
4. **Systemd Services** - Run agents as services
5. **Log Rotation** - Configure log rotation for agents
6. **Monitoring** - Monitor Heimdall itself

See `docs/instructions.md` for detailed production setup.

---

## Documentation

- **Overview**: `docs/README.md`
- **Features**: `HEIMDALL.md`
- **Setup**: `docs/QUICKSTART.md`
- **Deployment**: `docs/instructions.md`
- **Migration**: `docs/UPGRADE_TO_V2.md`
- **Technical**: `docs/PROJECT_SUMMARY.md`

---

## Support

For issues or questions:

1. Check the documentation files
2. Review agent logs for errors
3. Test with `python tests/test_api.py`
4. Verify API health: `curl http://localhost:8000/health`

---

**Heimdall V2.0 - Standing Guard Over Your Infrastructure** 🛡️

