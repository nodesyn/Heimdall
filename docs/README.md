# 🛡️ Heimdall

**Standing Guard Over Your Infrastructure**

A production-ready, lightweight Security Information and Event Management platform built with Python. Designed for small to medium-sized networks with a modular "Hub and Spoke" architecture.

Heimdall monitors everything—Windows Event Logs, Linux auth logs, macOS system events, firewall blocks, and DNS queries—giving you complete visibility into your security landscape.

**v2.0 Features:**
- ✨ MacOS agent for Darwin systems
- 🔥 Generic Firewall agent (iptables, UFW, pfSense, OPNsense)
- 📱 Telegram alerting system (real-time notifications)
- 📦 Modular architecture (agents/, core/, ui/, alerts/)
- 🚀 Production-ready security monitoring

## 🎯 Quick Start

### Installation

```bash
cd Heimdall

# Install dependencies (requires Python 3.10+)
python -m pip install -r requirements.txt

# Initialize database
python -m core.database
```

### Run Components (in separate terminals)

**Terminal 1: Start the API Server**
```bash
python -m core.server_api
# Server runs on http://localhost:8000
```

**Terminal 2: Start the Dashboard**
```bash
streamlit run ui/dashboard.py
# Dashboard opens at http://localhost:8501
```

**Terminal 3: Test the System**
```bash
python tests/test_api.py
# Generates sample data and validates system
```

## 📊 Features

### Core Capabilities

✅ **Real-time Log Ingestion** - FastAPI backend with async processing  
✅ **Comprehensive Visibility** - Windows, Linux, macOS, Firewall, Pi-hole  
✅ **Unified Data Model** - All events normalized to common schema  
✅ **Beautiful Dashboard** - Streamlit UI with real-time charts  
✅ **Instant Alerts** - Telegram notifications for critical events  
✅ **Smart Agents** - Stateful collection, duplicate handling  
✅ **RESTful API** - Easy integration with your stack  
✅ **Zero-Config DB** - SQLite with WAL mode  
✅ **Enterprise Ready** - Full error handling, logging, alerting  

### Dashboard Metrics

- **24-Hour Alerts** - Total events in the last 24 hours
- **Events per Minute** - Timeline chart colored by OS type
- **Top Attacking IPs** - Global ranking of source IPs
- **Threats by OS** - Distribution pie chart
- **Most Blocked Domain** - Top blocked DNS domain
- **Detailed Event Table** - Filterable, sortable log entries
- **Export Options** - Download as CSV or JSON

### Supported Agents

| Agent | Platform | Events Monitored | Status |
|-------|----------|-----------------|--------|
| **Windows** | Windows 7+ | Event Log (4625, 4720, 1102) | ✅ Stable |
| **Linux** | Linux (any distro) | Auth logs, sudo, logins | ✅ Stable |
| **macOS** | macOS 10.12+ | Auth logs, audit, system | ✨ NEW |
| **Pi-hole** | Pi-hole 5.0+ | Blocked DNS queries | ✅ Stable |
| **Firewall** | Generic/iptables/pfSense | Connection blocks, port scans | 🔥 NEW |

### Event Types

| Type | Severity | Agents | Description |
|------|----------|--------|-------------|
| **LOGIN_FAIL** | 3 | Windows, Linux, macOS | Failed authentication attempts |
| **SUDO_ESCALATION** | 2 | Linux, macOS | Privilege escalation |
| **DNS_BLOCK** | 1 | Pi-hole | Blocked DNS query |
| **CONNECTION_BLOCKED** | 2 | Firewall | Firewall-blocked connection |
| **PORT_SCAN** | 4 | Firewall | Detected port scan attempt |
| **ACCOUNT_CREATE** | 4 | Windows | New user account created |
| **LOG_TAMPERING** | 5 | Windows | Security log cleared |
| **CRITICAL_ERROR** | 5 | All | Critical system error |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  HEIMDALL - Security Guardian               │
└─────────────────────────────────────────────────────────────┘

AGENTS (Spokes)          SERVER (Hub)              INTERFACE
────────────────         ──────────────            ─────────
"Eyes Everywhere"        "The Watchman"            "Your View"
                                                   
┌─────────────┐          ┌──────────┐              ┌────────┐
│  Windows    │          │ FastAPI  │              │Streamlit
│  Agent      ├─────────→│ Server   │←────────────→│Dashboard
├─────────────┤          │(8000)    │              │(8501)
│  Linux      │          │          │              └────────┘
│  Agent      ├─────────→│ SQLite   │
├─────────────┤          │  DB      │              ┌────────┐
│  macOS      │          │          │              │Telegram
│  Agent      ├─────────→│ Alerts   │←────────────→│Alerts
├─────────────┤          │(AlertMgr)│              └────────┘
│  Firewall   │          │          │
│  Agent      ├─────────→│ WAL Mode │
├─────────────┤          │  Index   │
│  Pi-hole    │          └──────────┘
│  Agent      ├─────────→
└─────────────┘          

All agents push → API (POST /ingest)
Dashboard queries → API (GET /metrics, /events)
Alerts triggered → Telegram (async, instant)
```

## 📁 Project Structure

```
Python_Siem/
├── agents/                    # 🤖 Log collector agents
│   ├── agent_windows.py      # Windows Event Log collector
│   ├── agent_linux.py        # Linux auth log collector
│   ├── agent_macos.py        # macOS log collector (NEW)
│   ├── agent_firewall.py     # Generic firewall collector (NEW)
│   └── agent_pihole.py       # Pi-hole DNS blocker collector
│
├── core/                      # 💾 Core system
│   ├── models.py             # Pydantic schemas
│   ├── database.py           # SQLite management
│   └── server_api.py         # FastAPI backend
│
├── ui/                        # 📊 User interface
│   └── dashboard.py          # Streamlit dashboard
│
├── alerts/                    # 🚨 Alerting system (NEW)
│   └── telegram_alerts.py    # Telegram bot integration
│
├── tests/                     # 🧪 Testing
│   └── test_api.py           # API testing script
│
├── docs/                      # 📚 Documentation
│   ├── README.md             # Project overview
│   ├── QUICKSTART.md         # 5-minute setup
│   ├── instructions.md       # Deployment guide
│   └── ...other docs
│
├── requirements.txt          # Python dependencies
├── config.example.txt        # Configuration template
└── mini_siem.db             # SQLite database (created on first run)
```

## 🚀 Deployment

### Development

```bash
# Terminal 1: Server
python server_api.py

# Terminal 2: Dashboard
streamlit run dashboard.py

# Terminal 3: Linux agent
python agent_linux.py
```

Visit `http://localhost:8501` for the dashboard.

### Production

See `instructions.md` for:
- Systemd service setup
- Windows Task Scheduler configuration
- HTTPS/TLS deployment
- Database optimization
- Backup strategies

Key production steps:
```bash
# Set environment variables
export SIEM_API_URL=https://your-siem-server.com
export SIEM_API_KEY=$(openssl rand -hex 32)

# Deploy server with multiple workers
uvicorn server_api:app --host 0.0.0.0 --port 8000 --workers 4

# Deploy agents as systemd services
# Deploy dashboard with Nginx reverse proxy
```

## 🔑 API Reference

### Authentication

All API calls require the `api-key` header:

```bash
curl -H "api-key: your-api-key" http://localhost:8000/events
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Detailed health status |
| `POST` | `/ingest` | Submit log events |
| `GET` | `/events` | Query events with filters |
| `GET` | `/metrics` | Get dashboard metrics |

### Example: Ingest Events

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -H "api-key: your-api-key" \
  -d '{
    "events": [{
      "timestamp": "2024-01-15T10:30:00Z",
      "source_host": "ubuntu-01",
      "os_type": "LINUX",
      "event_type": "LOGIN_FAIL",
      "severity": 3,
      "source_ip": "192.168.1.100",
      "user": "admin",
      "raw_message": "Failed password attempt"
    }]
  }'
```

### Example: Query Events

```bash
# Get all events
curl -H "api-key: your-api-key" http://localhost:8000/events

# Filter by OS
curl -H "api-key: your-api-key" "http://localhost:8000/events?os_type=LINUX"

# Filter by severity
curl -H "api-key: your-api-key" "http://localhost:8000/events?severity=5"

# Filter by event type with limit
curl -H "api-key: your-api-key" "http://localhost:8000/events?event_type=LOGIN_FAIL&limit=100"
```

## 📱 Telegram Alerting

### Setup

1. **Create a Telegram Bot** (once):
   ```bash
   # Chat with @BotFather on Telegram
   # Commands: /newbot → follow prompts → get your bot token
   ```

2. **Get Your Chat ID**:
   ```bash
   # Chat with @userinfobot on Telegram to get your chat ID
   ```

3. **Configure Environment**:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_CHAT_ID="your_chat_id_here"
   ```

4. **Test Connection**:
   ```bash
   python -m alerts.telegram_alerts
   ```

### Alert Types

The system automatically sends Telegram alerts for:
- **Critical Events** (severity 5) - Immediate notification
- **Attack Summaries** - Grouped high-severity events
- **Daily Metrics** - 24-hour summary report
- **Agent Status** - Agent online/offline updates
- **System Status** - Server status changes

## 🚀 Deploy New Agents

### macOS Agent

```bash
export SIEM_API_URL=http://your-server:8000
export SIEM_API_KEY=your-secure-key
python agents/agent_macos.py
```

Monitors:
- Failed authentication attempts
- Sudo escalation commands
- Kernel audit messages

### Firewall Agent

```bash
# Generic (reads from /var/log/firewall.log)
export FIREWALL_TYPE=generic
export FIREWALL_LOG_PATH=/path/to/logs
python agents/agent_firewall.py

# Or specific firewall type
export FIREWALL_TYPE=iptables     # iptables/netfilter
export FIREWALL_TYPE=ufw          # Ubuntu UFW
export FIREWALL_TYPE=pfsense      # pfSense/OPNsense
python agents/agent_firewall.py
```

Detects:
- Blocked connections
- Port scan attempts
- Intrusion attempts
- Connection drops

## 🔒 Security

### Default Configuration

⚠️ **WARNING:** The default API key is `default-insecure-key-change-me`

**Change it immediately:**

```bash
export SIEM_API_KEY=$(openssl rand -hex 32)
```

### Security Checklist

- [ ] Change default API key
- [ ] Use HTTPS/TLS in production
- [ ] Deploy behind reverse proxy
- [ ] Restrict agent network access
- [ ] Store database on encrypted volume
- [ ] Enable firewall rules
- [ ] Set up log rotation
- [ ] Regular database backups
- [ ] Test Telegram alerting
- [ ] Configure alert thresholds

See `instructions.md` for detailed security hardening.

## 📊 Sample Data

Generate test data to try out the dashboard:

```python
import requests
from datetime import datetime

api_url = "http://localhost:8000"
api_key = "default-insecure-key-change-me"

# Sample events
events = [
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_host": "web-server-01",
        "os_type": "LINUX",
        "event_type": "LOGIN_FAIL",
        "severity": 3,
        "source_ip": "203.0.113.42",
        "user": "admin",
        "raw_message": "Failed password for admin from 203.0.113.42 port 22 ssh2"
    },
    {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_host": "dns-server",
        "os_type": "PIHOLE",
        "event_type": "DNS_BLOCK",
        "severity": 1,
        "source_ip": "192.168.1.50",
        "user": "pihole",
        "raw_message": "Blocked DNS query for ads.doubleclick.net"
    }
]

response = requests.post(
    f"{api_url}/ingest",
    json={"events": events},
    headers={"api-key": api_key}
)

print(response.json())
```

## 🧪 Testing

### Test API Connectivity

```bash
curl http://localhost:8000/health
```

### Test Event Ingestion

```bash
# Create test_events.py and run the sample data script above
python test_events.py
```

### Check Database

```bash
# Query SQLite directly
sqlite3 mini_siem.db "SELECT COUNT(*) as total_events FROM logs;"
sqlite3 mini_siem.db "SELECT event_type, COUNT(*) FROM logs GROUP BY event_type;"
```

## 🛠️ Troubleshooting

### Agents Not Sending Data

1. Check connectivity to server:
   ```bash
   curl http://your-server:8000/health
   ```

2. Verify API key matches:
   ```bash
   echo $SIEM_API_KEY
   ```

3. Check agent logs for errors

### Database Locked

SQLite occasionally reports "database is locked". This is normal with high concurrency.

```bash
# Restart the server to clear locks
pkill -f server_api.py
python server_api.py
```

### Dashboard Slow

- Reduce the record limit in filters
- Consider archiving old events (see `instructions.md`)
- Upgrade to PostgreSQL for production scale

## 📚 Documentation

- **`instructions.md`** - Complete deployment and configuration guide
- **`models.py`** - Data schema documentation
- **`server_api.py`** - API endpoint details
- **`dashboard.py`** - UI customization

## 🤝 Contributing

Contributions welcome! Areas of interest:

- [ ] PostgreSQL backend support
- [ ] MacOS agent
- [ ] ElasticSearch integration
- [ ] Machine learning anomaly detection
- [ ] Slack/email alerting
- [ ] Performance optimizations

## 📝 License

This project is provided as-is for educational and commercial use.

## 🎓 Learning Resources

This project demonstrates:

- **FastAPI** - Modern async Python web framework
- **SQLite** - Database design with indices and WAL mode
- **Pydantic** - Data validation and serialization
- **Streamlit** - Rapid dashboard development
- **Log Parsing** - Regex patterns for security events
- **REST API Design** - Clean API with proper error handling
- **System Integration** - Windows Event Logs, Linux auth logs, Pi-hole database

## 📞 Support

For issues or questions:

1. Check `instructions.md` for detailed troubleshooting
2. Review API documentation in `server_api.py`
3. Check agent logs for error messages
4. Verify database connectivity and permissions

---

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2024-01-15

**Built with ❤️ for security teams**

