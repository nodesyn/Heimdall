# Python Mini-SIEM - Project Manifest

## 📋 Complete File Listing

### Core Application Files (7)

#### 1. **models.py** (67 lines)
**Purpose:** Data models and validation  
**Key Classes:**
- `LogEvent` - Unified event schema (9 fields)
- `IngestRequest` - API request body
- `IngestResponse` - API response body
- `MetricsResponse` - Metrics payload

**Usage:** Imported by all components for type checking and validation

---

#### 2. **database.py** (190 lines)
**Purpose:** SQLite database layer  
**Key Functions:**
- `init_database()` - Create schema with indices
- `insert_event()` - Add single event
- `get_all_events()` - Retrieve recent events
- `get_events_by_filter()` - Query with filters
- `get_metrics_24h()` - Dashboard metrics
- `get_top_attacking_ips()` - IP ranking
- `get_events_per_minute()` - Timeline data

**Database Schema:**
```
logs table (10 columns)
├── id (PRIMARY KEY)
├── event_id (UNIQUE)
├── timestamp (indexed)
├── source_host
├── os_type (indexed)
├── event_type (indexed)
├── severity (indexed)
├── source_ip (indexed)
├── user
├── raw_message
└── created_at
```

**Usage:** Imported by server_api.py and dashboard.py

---

#### 3. **server_api.py** (155 lines)
**Purpose:** FastAPI REST API server  
**Key Endpoints:**
- `GET /` - Health check
- `GET /health` - Detailed status
- `POST /ingest` - Event ingestion (requires api-key)
- `GET /events` - Query events (filters: os_type, severity, event_type)
- `GET /metrics` - Dashboard metrics

**Security:**
- API key header validation
- Pydantic request validation
- CORS middleware enabled
- Error handling with detail messages

**Usage:** Run with `python server_api.py` or `uvicorn server_api:app`

---

#### 4. **agent_windows.py** (150 lines)
**Purpose:** Windows Security event log collector  
**Class:** `WindowsAgent`

**Monitored Events:**
- Event ID 4625: Failed Logon → LOGIN_FAIL (severity 3)
- Event ID 4720: User Created → ACCOUNT_CREATE (severity 4)
- Event ID 1102: Log Cleared → LOG_TAMPERING (severity 5)

**Key Methods:**
- `collect_events()` - Read from Windows Security log
- `parse_event()` - Extract and normalize event data
- `send_events()` - POST to API
- `run()` - Main loop (60-second interval)

**Requirements:** pywin32 library, Administrator privileges

**Usage:**
```bash
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=your-key
python agent_windows.py
```

---

#### 5. **agent_linux.py** (240 lines)
**Purpose:** Linux authentication log collector  
**Class:** `LinuxAgent`

**Monitored Events (via regex):**
- Failed password attempts → LOGIN_FAIL (severity 3)
- Invalid user login → LOGIN_FAIL (severity 3)
- Sudo command execution → SUDO_ESCALATION (severity 2)

**Log Files Supported:**
- `/var/log/auth.log` (Debian/Ubuntu)
- `/var/log/secure` (RHEL/CentOS)

**Key Methods:**
- `read_new_lines()` - Stateful log reading (track file position)
- `parse_event()` - Regex-based event parsing
- `send_events()` - POST to API
- `run()` - Main loop (30-second interval)

**Features:**
- Duplicate detection (hash-based)
- Automatic log file selection
- ISO-8601 timestamp normalization

**Usage:**
```bash
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=your-key
python agent_linux.py
```

---

#### 6. **agent_pihole.py** (155 lines)
**Purpose:** Pi-hole DNS blocking events collector  
**Class:** `PiholeAgent`

**Data Source:** SQLite database at `/etc/pihole/pihole-FTL.db`

**Monitored Status Codes:** 1, 4, 5, 9, 10, 11 (blocked queries)

**Key Methods:**
- `query_blocked_domains()` - Direct SQLite query to FTL database
- `send_events()` - POST to API
- `run()` - Main loop (60-second interval)

**Features:**
- No text parsing (direct database access)
- Stateful: tracks last processed ID
- Automatic duplicate prevention

**Usage:**
```bash
export SIEM_API_URL=http://your-server:8000
export SIEM_API_KEY=your-key
python agent_pihole.py
```

**Requirements:**
- Must run on Pi-hole server
- Database read access
- Pi-hole 5.0+

---

#### 7. **dashboard.py** (280 lines)
**Purpose:** Streamlit web dashboard  

**Sections:**
1. **Key Metrics** (24-hour data):
   - Total alerts count
   - Threats by OS breakdown
   - Most blocked domain

2. **Charts:**
   - Line chart: Events per minute (by OS)
   - Bar chart: Top 10 attacking IPs
   - Pie chart: Threat distribution by OS

3. **Data Table:**
   - Filterable by OS, Severity, Event Type
   - Sortable columns
   - Customizable record limit

4. **Export:**
   - Download as CSV
   - Download as JSON

**Features:**
- Auto-refresh option (30 seconds)
- 30-second response caching
- Responsive layout with Plotly
- Professional styling

**Usage:**
```bash
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=your-key
streamlit run dashboard.py
# Opens at http://localhost:8501
```

---

### Documentation Files (6)

#### 8. **README.md**
- Project overview and features
- Quick start instructions
- Architecture diagram
- API reference
- Security checklist
- Troubleshooting guide

#### 9. **QUICKSTART.md**
- 5-minute setup guide
- Step-by-step instructions
- Dashboard features explanation
- API testing commands
- Common issues and fixes

#### 10. **instructions.md** (Most comprehensive)
- Complete deployment guide
- System requirements
- Installation procedures
- Component details and specifications
- Deployment methods for each agent
- Windows service setup
- Linux systemd setup
- Production security hardening
- Performance tuning
- Backup strategies
- Future enhancements

#### 11. **PROJECT_SUMMARY.md**
- Project completion status
- Specification compliance checklist
- Feature implementation details
- Code statistics
- Performance characteristics
- Security considerations
- Quality metrics

#### 12. **MANIFEST.md** (This file)
- Complete file listing
- File descriptions
- Usage instructions
- Key information for each component

#### 13. **sas.md** (Original specification)
- System Architecture Specification
- Requirements document
- Reference implementation

---

### Configuration & Dependencies (2)

#### 14. **requirements.txt**
```
fastapi==0.104.1          # REST API framework
uvicorn==0.24.0           # ASGI server
pydantic==2.5.0           # Data validation
streamlit==1.28.1         # Dashboard UI
plotly==5.18.0            # Charts and graphs
watchdog==3.0.0           # File system monitoring
python-dateutil==2.8.2    # Date parsing utilities
pywin32==306              # Windows API (optional)
requests==2.31.0          # HTTP client
```

#### 15. **config.example.txt**
- Environment variable template
- Configuration options documented
- Security settings
- Performance tuning options
- Agent-specific settings
- Deployment recommendations

---

### Testing & Utilities (1)

#### 16. **test_api.py** (250 lines)
**Purpose:** Testing script and sample data generator

**Test Functions:**
- `health_check()` - Verify API availability
- `generate_linux_events()` - Create sample Linux events
- `generate_windows_events()` - Create sample Windows events
- `generate_pihole_events()` - Create sample Pi-hole events
- `submit_events()` - POST events to API
- `query_events()` - GET events from API
- `get_metrics()` - Fetch dashboard metrics

**Usage:**
```bash
python test_api.py
```

**Output:**
- Connection status check
- 13 sample events generated (3 Linux, 2 Windows, 8 Pi-hole)
- API ingestion results
- Metrics summary

---

## 📊 Project Statistics

| Metric | Count |
|--------|-------|
| Total Files | 16 |
| Python Files | 7 |
| Documentation Files | 6 |
| Config/Support Files | 3 |
| Total Lines of Code | ~1,200 |
| Total Lines of Documentation | ~3,000+ |
| Total Project Size | 216 KB |

---

## 🚀 Quick Start Sequence

### 1. Setup (First Time Only)
```bash
pip install -r requirements.txt
python database.py
```

### 2. Terminal 1: Start Server
```bash
python server_api.py
# API at http://localhost:8000
```

### 3. Terminal 2: Start Dashboard
```bash
streamlit run dashboard.py
# Dashboard at http://localhost:8501
```

### 4. Terminal 3: Test System
```bash
python test_api.py
# Generates sample data and validates system
```

### 5. Deploy Agents (Production)
```bash
# Linux agent
python agent_linux.py

# Or Windows agent
python agent_windows.py

# Or Pi-hole agent
python agent_pihole.py
```

---

## 🔧 Key Configuration Points

### API Server (`server_api.py`)
- Default port: 8000
- Default API key: `default-insecure-key-change-me` (change in production!)
- CORS: Enabled for all origins

### Database (`database.py`)
- Location: `mini_siem.db` (SQLite)
- WAL mode: Enabled (for concurrency)
- Indices: 5 (timestamp, event_type, source_ip, os_type, severity)

### Agents
- Linux: 30-second polling interval
- Windows: 60-second polling interval
- Pi-hole: 60-second polling interval

### Dashboard (`dashboard.py`)
- Port: 8501
- Cache duration: 30 seconds
- Auto-refresh interval: 30 seconds

---

## 📚 Documentation Map

| Document | Best For |
|----------|----------|
| **README.md** | Overview and features |
| **QUICKSTART.md** | Getting started fast |
| **instructions.md** | Production deployment |
| **PROJECT_SUMMARY.md** | Technical details |
| **MANIFEST.md** (this) | File reference |
| **Code comments** | Implementation details |

---

## 🎯 Common Tasks

### Add a new event type
1. Update `models.py` - Add to event_type Literal
2. Update agent - Add parsing logic
3. Update dashboard - Add to filter options

### Deploy to production
1. Read `instructions.md` - Production section
2. Change API key in environment
3. Set up HTTPS/TLS
4. Deploy as systemd services
5. Configure backups

### Scale the system
1. Add database indices
2. Switch to PostgreSQL
3. Add multiple FastAPI workers
4. Implement caching layer (Redis)
5. Set up load balancer

### Add a new agent
1. Create `agent_newos.py`
2. Inherit from agent pattern
3. Implement event collection
4. Use models.py for validation
5. Deploy and test

---

## ✅ Pre-Deployment Checklist

- [ ] All files present and readable
- [ ] Python 3.10+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Database initialized: `python database.py`
- [ ] API server starts: `python server_api.py`
- [ ] Dashboard loads: `streamlit run dashboard.py`
- [ ] Test data generates: `python test_api.py`
- [ ] API key changed (if production)
- [ ] Agents configured with correct API URL
- [ ] Firewall rules configured
- [ ] Backups configured

---

## 🆘 Quick Reference

### Start Components
```bash
# Server
python server_api.py

# Dashboard
streamlit run dashboard.py

# Linux Agent
python agent_linux.py

# Windows Agent
python agent_windows.py

# Pi-hole Agent
python agent_pihole.py

# Test
python test_api.py
```

### Test API
```bash
# Health check
curl http://localhost:8000/health

# Query events
curl -H "api-key: default-insecure-key-change-me" http://localhost:8000/events

# Get metrics
curl -H "api-key: default-insecure-key-change-me" http://localhost:8000/metrics
```

### Database
```bash
# Connect to database
sqlite3 mini_siem.db

# Count events
SELECT COUNT(*) FROM logs;

# Events by type
SELECT event_type, COUNT(*) FROM logs GROUP BY event_type;

# Top attacking IPs
SELECT source_ip, COUNT(*) FROM logs GROUP BY source_ip ORDER BY COUNT(*) DESC LIMIT 10;
```

---

## 📞 Support Resources

1. **Setup Issues** → Check `QUICKSTART.md`
2. **Deployment Issues** → Check `instructions.md`
3. **API Issues** → Check `server_api.py` comments
4. **Agent Issues** → Check relevant `agent_*.py` file
5. **Dashboard Issues** → Check `dashboard.py` comments

---

**Version:** 1.0.0  
**Status:** Production Ready  
**Files:** 16  
**Last Updated:** 2024-01-15

All components are complete, tested, and ready for deployment. 🚀

