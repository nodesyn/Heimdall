# Heimdall v2.0 Changelog

**Standing Guard Over Your Infrastructure**

## Version 2.0.1 - Bug Fix (2024-12-03)

### 🐛 Bug Fixes
- **Fixed duplicate event entries in dashboard**
  - Replaced `time.time()` with `uuid.uuid4()` for event ID generation
  - Affects: `agent_windows.py`, `agent_linux.py`, `agent_macos.py`, `agent_firewall.py`
  - Database unique constraint now reliably prevents duplicates
  - No breaking changes, fully backward compatible

## Version 2.0.0 - Major Release

### 🎉 New Agents

#### macOS Agent (`agents/agent_macos.py`)
- **Events Monitored:**
  - Failed authentication attempts
  - Invalid user logins
  - Sudo command execution
  - Sudo authentication failures
  - Kernel audit messages
- **Compatibility:** macOS 10.12+
- **Status:** ✨ NEW

#### Firewall Agent (`agents/agent_firewall.py`)
- **Supported Firewall Types:**
  - Generic (custom log path)
  - iptables/netfilter
  - UFW (Uncomplicated Firewall)
  - pfSense/OPNsense
- **Events Monitored:**
  - Blocked connections
  - Port scan attempts
  - Intrusion detection
- **Status:** 🔥 NEW

### 🚨 New Features

#### Telegram Alerting System (`alerts/telegram_alerts.py`)
- **Components:**
  - `TelegramAlert` - Send alerts via Telegram bot
  - `AlertManager` - Threshold-based alert routing
- **Alert Types:**
  - Critical event alerts (severity 5)
  - High event summaries (severity 4+)
  - Daily metrics reports
  - System status updates
  - Agent status notifications
- **Features:**
  - Non-blocking async notifications
  - Configurable thresholds
  - Easy extension for Slack/Email
- **Setup:** 5 minutes with @BotFather and @userinfobot
- **Status:** 📱 NEW

### 📦 Codebase Reorganization

**New Directory Structure:**
```
Python_Siem/
├── agents/              # Log collector agents (5 total)
├── core/                # Core system (models, DB, API)
├── ui/                  # User interface (dashboard)
├── alerts/              # Alerting systems
├── tests/               # Testing utilities
└── docs/                # Documentation
```

**Module Separation Benefits:**
- ✅ Better code organization
- ✅ Easier to maintain
- ✅ Clear separation of concerns
- ✅ Simpler to extend

### 🚀 Running v2.0

**Start Server:**
```bash
python -m core.server_api
```

**Start Dashboard:**
```bash
streamlit run ui/dashboard.py
```

**Run Agents:**
```bash
python agents/agent_windows.py
python agents/agent_linux.py
python agents/agent_macos.py
python agents/agent_firewall.py
python agents/agent_pihole.py
```

**Test Alerts:**
```bash
python -m alerts.telegram_alerts
```

### 📚 Documentation Updates

| Document | Changes |
|----------|---------|
| README.md | Updated with v2.0 features, new agents, Telegram setup |
| instructions.md | Added macOS, Firewall, Telegram sections; updated paths |
| UPGRADE_TO_V2.md | NEW - Complete migration guide from v1.0 |
| V2_CHANGELOG.md | NEW - This file |

### 🔄 Event Type Additions

**New in v2.0:**
- `CONNECTION_BLOCKED` (severity 2) - Firewall connections
- `PORT_SCAN` (severity 4) - Firewall port scans

**Existing (unchanged):**
- `LOGIN_FAIL` (severity 3)
- `SUDO_ESCALATION` (severity 2)
- `DNS_BLOCK` (severity 1)
- `ACCOUNT_CREATE` (severity 4)
- `LOG_TAMPERING` (severity 5)
- `CRITICAL_ERROR` (severity 5)

### 🔧 Configuration Updates

**New Environment Variables:**
```bash
# Telegram Alerts
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"

# Firewall Agent
FIREWALL_TYPE=generic|iptables|ufw|pfsense|opnsense
FIREWALL_LOG_PATH=/path/to/logs

# Alert Thresholds
ALERT_CRITICAL_THRESHOLD=5
ALERT_HIGH_THRESHOLD=3
```

### ✨ Quality Improvements

- **Code Organization:** Modular structure with clear separation
- **Error Handling:** Enhanced with Telegram alerting
- **Documentation:** Comprehensive upgrade and deployment guides
- **Extensibility:** Easy to add new agents or alerting systems
- **Python Package Structure:** Added __init__.py to all modules

### 🔄 Backward Compatibility

**Database:** ✅ 100% compatible
- Existing `mini_siem.db` works with v2.0
- No migration needed
- All events preserved

**API:** ✅ Fully compatible
- Same endpoints
- Same request/response format
- Same authentication

**Agents:** ⚠️ Requires path update
- Need to update agent deployment paths
- See UPGRADE_TO_V2.md for details

### 📊 Statistics

| Metric | v1.0 | v2.0 | Change |
|--------|------|------|--------|
| Agents | 3 | 5 | +2 |
| Event Types | 6 | 8 | +2 |
| Alerting Systems | 0 | 1 | +1 |
| Python Files | 7 | 12 | +5 |
| Documentation Files | 6 | 8 | +2 |
| Total Lines | ~1,200 | ~2,100 | +900 |

### 🐛 Bug Fixes

- Improved error handling in agent log parsing
- Better timestamp parsing across different systems
- Fixed regex patterns for firewall logs
- Enhanced duplicate detection

### 🚀 Performance

- **No degradation** - Same performance as v1.0
- **Telegram alerts:** Async (non-blocking)
- **Database:** Unchanged WAL mode
- **API:** Unchanged FastAPI performance

### 🔒 Security

- API authentication unchanged
- Telegram alerts use secure HTTPS
- No new security issues
- Security best practices updated in docs

### 📝 Migration Path

For v1.0 users:
1. Backup existing installation
2. Update directory structure
3. Update import paths
4. Update systemd services
5. Test all agents
6. Deploy new agents (optional)
7. Configure Telegram (optional)

See [UPGRADE_TO_V2.md](UPGRADE_TO_V2.md) for detailed steps.

### 🎯 Next Planned Features (v2.1+)

- [ ] PostgreSQL support
- [ ] ElasticSearch integration
- [ ] Machine learning anomaly detection
- [ ] Slack alerting
- [ ] Email alerts
- [ ] Custom rule builder
- [ ] Web UI for agent management
- [ ] Docker containerization

### 📞 Support

- Documentation: See `docs/` folder
- Troubleshooting: [README.md](README.md)
- Upgrade Guide: [UPGRADE_TO_V2.md](UPGRADE_TO_V2.md)
- Deployment: [instructions.md](instructions.md)

### 👥 Contributors

Built for security teams by security enthusiasts.

---

**Version:** 2.0.0  
**Release Date:** 2024-01-15  
**Status:** Production Ready  
**Upgrade Recommended:** Yes

## Highlights

🎯 **What Makes v2.0 Special:**
1. **Multi-platform Support** - Now covers Windows, Linux, macOS, and Firewalls
2. **Real-time Alerts** - Telegram integration for instant notifications
3. **Better Organization** - Modular codebase structure
4. **Production Ready** - Comprehensive alerting system
5. **Easy to Extend** - Clear patterns for adding new agents/alerts

**Migration Time:** ~30 minutes  
**Downtime:** ~5 minutes (during agent restart)  
**Complexity:** Low (mostly path updates)

---

Thank you for using Mini-SIEM! 🛡️

