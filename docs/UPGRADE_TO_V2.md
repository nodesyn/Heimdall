# Mini-SIEM v2.0 Upgrade Guide

Upgrade from v1.0 to v2.0 with new features: macOS support, Firewall agent, Telegram alerts, and reorganized code structure.

## What's New in v2.0

### 🎉 New Features

1. **macOS Agent** (`agents/agent_macos.py`)
   - Monitors auth logs, audit events, and system logs
   - Detects login failures, sudo escalation, kernel audits
   - Compatible with macOS 10.12+

2. **Firewall Agent** (`agents/agent_firewall.py`)
   - Generic firewall log collector
   - Support for: iptables, UFW, pfSense, OPNsense
   - Detects: blocked connections, port scans, intrusion attempts
   - Configurable via `FIREWALL_TYPE` environment variable

3. **Telegram Alerting System** (`alerts/telegram_alerts.py`)
   - Real-time security notifications via Telegram
   - Alert types: critical events, attack summaries, metrics reports, status updates
   - Configurable thresholds and message formats
   - Easy extension for Slack/Email integration

4. **Reorganized Codebase**
   - `agents/` - All log collector agents
   - `core/` - Core system (models, database, API)
   - `ui/` - User interface (dashboard)
   - `alerts/` - Alerting systems
   - `tests/` - Testing utilities
   - `docs/` - All documentation

### ✨ Improvements

- Better code organization and maintainability
- Enhanced error handling and logging
- More event types supported
- Improved documentation
- Added Python package structure (__init__.py files)

## Migration from v1.0

### Step 1: Backup Old Installation

```bash
# Backup your current v1.0 installation
cp -r Python_Siem Python_Siem.backup
```

### Step 2: Reorganize File Structure

The new v2.0 uses a directory structure instead of flat files:

**Old v1.0 structure:**
```
agent_windows.py
agent_linux.py
agent_pihole.py
models.py
database.py
server_api.py
dashboard.py
```

**New v2.0 structure:**
```
agents/
├── agent_windows.py
├── agent_linux.py
├── agent_pihole.py
├── agent_macos.py      # NEW
└── agent_firewall.py   # NEW
core/
├── models.py
├── database.py
└── server_api.py
ui/
└── dashboard.py
alerts/                 # NEW
└── telegram_alerts.py
```

### Step 3: Update Installation

```bash
cd Python_Siem

# Install dependencies (same as before)
pip install -r requirements.txt

# Initialize database (path changed)
python -m core.database

# Note: If you have an old mini_siem.db, it will work as-is
```

### Step 4: Update Agent Deployments

#### For Windows Agents

Update your scheduled task or service:

**Old:**
```powershell
python C:\path\to\agent_windows.py
```

**New:**
```powershell
python C:\path\to\agents\agent_windows.py
```

#### For Linux Agents

Update your systemd service file:

**Old:**
```ini
ExecStart=/usr/bin/python3 /path/to/agent_linux.py
```

**New:**
```ini
ExecStart=/usr/bin/python3 /path/to/agents/agent_linux.py
```

Then restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart siem-agent-linux
```

#### For Pi-hole Agents

Update your deployment:

**Old:**
```bash
python agent_pihole.py
```

**New:**
```bash
python agents/agent_pihole.py
```

### Step 5: Configure Telegram Alerts (Optional)

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Test connection
python -m alerts.telegram_alerts

# If successful, add to your systemd services or shell profile
```

### Step 6: Update API Server Startup

**Old:**
```bash
python server_api.py
# or
uvicorn server_api:app --host 0.0.0.0 --port 8000
```

**New:**
```bash
python -m core.server_api
# or
uvicorn core.server_api:app --host 0.0.0.0 --port 8000
```

### Step 7: Update Dashboard Startup

**Old:**
```bash
streamlit run dashboard.py
```

**New:**
```bash
streamlit run ui/dashboard.py
```

### Step 8: Update Documentation References

Update any internal documentation or scripts that reference:
- `database.py` → `core.database`
- `server_api.py` → `core.server_api`
- `dashboard.py` → `ui/dashboard.py`
- `test_api.py` → `tests/test_api.py`

## Database Compatibility

Good news: **Your existing `mini_siem.db` database is 100% compatible!**

The database schema hasn't changed, so:
- ✅ All existing events are preserved
- ✅ No migration needed
- ✅ Can run v1.0 and v2.0 against same database
- ✅ No data loss

## Import Changes for Custom Scripts

If you have custom scripts importing from the system:

**Old v1.0:**
```python
from models import LogEvent
from database import insert_event
```

**New v2.0:**
```python
from core.models import LogEvent
from core.database import insert_event
```

## Troubleshooting Migration Issues

### "Module not found" errors

**Problem:** `ModuleNotFoundError: No module named 'models'`

**Solution:** Update imports to use new paths:
```python
# Change from:
from models import ...

# To:
from core.models import ...
```

### Agent not connecting to API

**Problem:** Agent can't reach the API server

**Solution:** Make sure API is running from new location:
```bash
# Check API is running
curl http://localhost:8000/health

# If not, start it:
python -m core.server_api
```

### Dashboard won't load

**Problem:** Streamlit can't find dashboard

**Solution:** Run from correct location:
```bash
# Make sure you're in the Python_Siem directory
cd /path/to/Python_Siem

# Run with new path
streamlit run ui/dashboard.py
```

### Old systemd services still point to old paths

**Solution:** Update all systemd service files:

```bash
# Find all SIEM services
systemctl list-units | grep siem

# Edit each service file
sudo nano /etc/systemd/system/siem-*.service

# Update ExecStart paths and save

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart siem-agent-*
```

## Rollback to v1.0

If you need to rollback:

```bash
# Stop all v2.0 services
sudo systemctl stop siem-*

# Restore backup
rm -rf Python_Siem
cp -r Python_Siem.backup Python_Siem

# Restart services
sudo systemctl start siem-*
```

## New Features to Try

### 1. Deploy macOS Agent

```bash
# On a macOS system
export SIEM_API_URL=http://your-server:8000
export SIEM_API_KEY=your-api-key
python agents/agent_macos.py
```

### 2. Deploy Firewall Agent

```bash
# For iptables
export FIREWALL_TYPE=iptables
python agents/agent_firewall.py

# For UFW
export FIREWALL_TYPE=ufw
python agents/agent_firewall.py
```

### 3. Set Up Telegram Alerts

```bash
# Get bot token and chat ID
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Test
python -m alerts.telegram_alerts

# System now sends alerts to Telegram!
```

## Performance Considerations

v2.0 is more efficient than v1.0:
- ✅ Better code organization = easier debugging
- ✅ Same database performance (WAL mode unchanged)
- ✅ Same API performance (FastAPI unchanged)
- ✅ Telegram alerting is async (non-blocking)

## Migration Checklist

- [ ] Backup v1.0 installation
- [ ] Create new v2.0 directory structure
- [ ] Update Python imports in custom scripts
- [ ] Update systemd service files
- [ ] Update startup scripts
- [ ] Test each agent connection
- [ ] Verify dashboard loads
- [ ] Configure Telegram (optional)
- [ ] Test Telegram alerts (optional)
- [ ] Update documentation
- [ ] Delete v1.0 backup (if migration successful)

## Support

If you encounter issues during migration:

1. Check [README.md](README.md) for troubleshooting
2. Review [instructions.md](instructions.md) for detailed setup
3. Check agent logs for error messages
4. Verify API is running: `curl http://localhost:8000/health`
5. Test database: `sqlite3 mini_siem.db "SELECT COUNT(*) FROM logs;"`

## Next Steps

After upgrading to v2.0:

1. **Try new agents**: Deploy macOS or Firewall agent
2. **Enable alerts**: Set up Telegram notifications
3. **Explore new features**: Check updated dashboard
4. **Update docs**: Update internal documentation
5. **Clean up**: Remove old backup when stable

---

**Upgrade Version:** 2.0.0  
**Upgrade Date:** 2024-01-15  
**Migration Time:** ~30 minutes  
**Downtime:** ~5 minutes (during agent restart)

Good luck with your upgrade! 🚀

