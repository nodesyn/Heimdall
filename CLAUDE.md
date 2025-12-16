# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Heimdall** is a lightweight, production-ready security monitoring system (Mini-SIEM) that collects, correlates, and alerts on security events from multiple sources:

- **Windows, Linux, macOS systems** - Authentication, privilege escalation, critical errors
- **Firewalls** - Connection blocks, port scans (iptables, UFW, pfSense, OPNsense)
- **Pi-hole DNS** - Blocked DNS queries
- **Centralized dashboard** - Real-time visualization and analytics
- **Telegram alerting** - Instant notifications for critical events

## Architecture

### Core Components

```
agents/           - Log collectors (Windows, Linux, macOS, Firewall, Pi-hole)
core/             - Central system (API server, database, event models)
ui/               - Streamlit dashboard
alerts/           - Notification systems (Telegram)
tests/            - Test utilities
docs/             - Comprehensive documentation
```

### Data Flow

1. **Agents** collect logs from their respective sources
2. **Agents normalize logs** into the unified `LogEvent` schema defined in `core/models.py`
3. **Agents POST to API** at `/ingest` endpoint with API key authentication
4. **Database** stores events in SQLite with proper indexing
5. **Dashboard** queries API to display metrics and events
6. **Alerting** system sends Telegram notifications for critical events

### Unified Event Schema

All agents normalize events to the `LogEvent` model (`core/models.py`):
- `event_id` - UUID for uniqueness (prevents duplicates)
- `timestamp` - ISO-8601 string (UTC)
- `source_host` - Hostname of event source
- `os_type` - One of: WINDOWS, LINUX, PIHOLE, MACOS, FIREWALL
- `event_type` - LOGIN_FAIL, SUDO_ESCALATION, DNS_BLOCK, CRITICAL_ERROR, ACCOUNT_CREATE, LOG_TAMPERING, CONNECTION_BLOCKED, PORT_SCAN
- `severity` - 1-5 scale (1=Info, 5=Critical)
- `source_ip` - IPv4/IPv6 or "N/A"
- `user` - Username or "system"
- `raw_message` - Original log line for context

## Development Commands

### Local Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -m core.database

# Load environment variables (optional, but recommended for secrets)
source .env  # contains SIEM_API_KEY, TELEGRAM_BOT_TOKEN, etc.
```

### Running Locally (Development)

```bash
# Terminal 1: Start API server (listens on :8000)
python -m core.server_api

# Terminal 2: Start dashboard (listens on :8501)
streamlit run ui/dashboard.py

# Terminal 3+: Run any agent
python agents/agent_linux.py
python agents/agent_windows.py
python agents/agent_macos.py
python agents/agent_firewall.py
python agents/agent_pihole.py
```

### Deployment to Remote Host
```bash
# Deploy using the provided deployment script
bash deploy.sh

# Script handles:
# - SSH connectivity checks
# - Docker/docker-compose availability verification
# - File synchronization via rsync (excludes .git, __pycache__, *.db, etc.)
# - Docker image build on remote host
# - Service startup with docker-compose
# - Health check verification
```

The `deploy.sh` script is the recommended method for deployment. It:
- Requires SSH key authentication (no password prompts)
- Excludes database files, cache, and git history from sync
- Transfers `.env` file separately for security
- Builds Docker image on the remote host
- Performs health checks post-deployment

### Windows Agent as a Service (Production)

Build the agent as an executable and run as a Windows Service. Can be built on Windows, Linux, or macOS.

**Option 1: Build on Linux/macOS (Recommended for this server)**
```bash
cd agents
chmod +x build_windows_exe_cross_platform.sh
./build_windows_exe_cross_platform.sh
# Output: dist/HeimdallAgent.exe
# Deploy: scp dist/HeimdallAgent.exe user@windows-machine:C:/Heimdall/
```

**Option 2: Build on Windows**
```batch
cd agents
build_windows_agent.bat
# Output: dist\HeimdallAgent.exe
```

**Install on Windows (as Administrator)**
```batch
C:\Heimdall\HeimdallAgent.exe install
C:\Heimdall\HeimdallAgent.exe start
```

Or use PowerShell installer:
```powershell
Install-HeimdallAgent.ps1 -ApiUrl "http://your-siem:8000" -ApiKey "your-key"
```

Service management:
```batch
C:\Heimdall\HeimdallAgent.exe start    # Start service
C:\Heimdall\HeimdallAgent.exe stop     # Stop service
C:\Heimdall\HeimdallAgent.exe restart  # Restart service
C:\Heimdall\HeimdallAgent.exe remove   # Remove service
```

See documentation:
- Quick reference: `agents/WINDOWS_SERVICE_README.md`
- Complete guide: `docs/WINDOWS_AGENT_SERVICE.md`
- Cross-platform deployment: `docs/CROSS_PLATFORM_WINDOWS_AGENT.md`

### Local Docker Deployment
```bash
# Build image locally
docker build -t heimdall .

# Start containers
docker-compose up

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

See **Deployment to Remote Host** section above for production deployment to a remote server.

### Testing
```bash
# Test API connectivity
python tests/test_api.py

# Quick connection test for agents
python agents/test_windows_connection.py
```

## Configuration

All configuration uses environment variables:

```bash
# API & Database
SIEM_API_URL=http://localhost:8000          # Agent connection point
SIEM_API_KEY=your-secure-key-here           # Authentication (CHANGE in production!)
SIEM_DATABASE_PATH=mini_siem.db             # Database location

# Dashboard
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# API Server
SIEM_SERVER_HOST=0.0.0.0
SIEM_SERVER_PORT=8000

# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_bot_token           # For notifications
TELEGRAM_CHAT_ID=your_chat_id

# Firewall Agent
FIREWALL_TYPE=iptables|ufw|pfsense|opnsense
FIREWALL_LOG_PATH=/path/to/firewall/logs

# Alert Thresholds
ALERT_CRITICAL_THRESHOLD=5                  # Events triggering critical alert
ALERT_HIGH_THRESHOLD=3
```

See `config.example.txt` for a complete configuration template.

## Key Files & Their Roles

### Core System (`core/`)
- **`server_api.py`** - FastAPI server handling `/ingest` endpoint and event queries. Validates API keys, processes events, manages CORS. Port 8000 by default.
- **`database.py`** - SQLite database initialization, insert/query functions, WAL mode for concurrency, indexed tables for events and heartbeats
- **`models.py`** - Pydantic models: `LogEvent` (main schema), `IngestRequest`, `IngestResponse`, `MetricsResponse`. All agents normalize to `LogEvent`.

### Agents (`agents/`)
- **`agent_linux.py`** - Reads `/var/log/auth.log` or `/var/log/secure`, extracts LOGIN_FAIL, SUDO_ESCALATION, AUTH_FAILURE events
- **`agent_windows.py`** - Reads Windows Event Log via WMI, extracts failed logins and privilege escalation
- **`agent_macos.py`** - Reads macOS unified logging, extracts failed logins and sudo commands
- **`agent_firewall.py`** - Parses firewall logs (iptables/UFW/pfSense), extracts CONNECTION_BLOCKED and PORT_SCAN events
- **`agent_pihole.py`** - Connects to Pi-hole API for DNS_BLOCK events
- **`windows_service_wrapper.py`** - Windows Service integration for agent_windows.py. Wraps agent in ServiceFramework for Windows SCM integration.
- **`build_windows_agent.bat`** - Batch script to compile agent_windows.py into standalone HeimdallAgent.exe using PyInstaller
- **`setup_windows_agent.bat`** - Batch installer for Windows service setup (environment variables, installation, startup)
- **`Install-HeimdallAgent.ps1`** - PowerShell installer script (preferred method for Windows service deployment)
- **`build_windows_exe.spec`** - PyInstaller specification file for EXE compilation

All agents:
1. Read logs/API endpoints
2. Match patterns and extract security-relevant data
3. Normalize to `LogEvent` schema
4. POST batches to API `/ingest` endpoint
5. Track position/state to avoid re-processing

### UI & Alerts (`ui/` and `alerts/`)
- **`ui/index.html`** - Main dashboard HTML with inline CSS and JavaScript. LCARS-styled interface with real-time charts, system status, and event timeline. Uses Chart.js for data visualization.
- **`ui/heimdall-logo.svg`** - Bold black SVG logo with orange accents (all-seeing eye design with 4 directional spikes: Watch, Guard, Protect, Defend)
- **`ui/heimdall-text.svg`** - Styled "HEIMDALL" text SVG matching the logo design with orange gradient and decorative lines
- **`ui/dashboard.py`** - Legacy Streamlit app (dashboard functionality now in index.html)
- **`alerts/telegram_alerts.py`** - Sends Telegram messages for critical events. Integrates with API server for event subscriptions.

#### UI Design Notes
The dashboard uses LCARS (Library Computer Access/Retrieval System) styling from Star Trek TNG with colors:
- Orange: #FF9900, #FF8800 (primary accent)
- Blue: #0099FF, #0077BB (secondary accent)
- Yellow: #FFCC00 (text highlight)
- Green: #00FF99 (status - online/active)
- Red: #FF3366 (status - offline/critical)

The index.html file includes:
- Real-time event timeline chart (events per hour)
- Severity distribution chart (donut chart)
- OS type distribution chart
- System status indicators (online/offline/alerts)
- Event tables with filtering and search
- Live stardate and local time display
- All assets are SVG-based for crisp scaling

## Important Implementation Details

### Event Deduplication
- Events use UUID (`uuid.uuid4()`) as `event_id` for guaranteed uniqueness
- Database has `UNIQUE` constraint on `event_id` column
- Prevents agent retries from creating duplicates

### Stateful Log Reading
- Linux and Windows agents track file position/inode to read only new logs
- Pi-hole agent uses API timestamps to fetch only new blocks
- Firewall agent tracks log file position similarly

### API Authentication
- All `/ingest` requests require `api_key` header matching `SIEM_API_KEY`
- Returns 401 if missing, 403 if invalid
- Change default key in production!

### Database Concurrency
- SQLite WAL (Write-Ahead Logging) mode enabled for multiple concurrent readers
- Dashboard can query while agents write
- Proper indexing on timestamp, event_type, source_ip, os_type, severity

### Agent Design Pattern
Each agent class:
1. Initializes with API URL and key
2. Opens log file/API connection
3. Reads incrementally (tracking position)
4. Matches regex patterns against each line
5. Normalizes matches to `LogEvent` objects
6. Batches events (typically 10-100 at a time)
7. POSTs to `/ingest` endpoint
8. Sleeps before next iteration

### Dashboard Chart Handling
The index.html dashboard uses Chart.js with proper canvas management:
- **Canvas destruction pattern**: Charts must be destroyed before reuse to prevent "Canvas is already in use" errors
- **Data parsing**: API returns `events_per_minute` as array of `{minute, os_type, count}` objects
- **Time handling**: Stardate calculated from current date; local browser time displayed (not UTC)
- **Event timeline**: Aggregates per-minute data into per-hour buckets for display

Common chart reset pattern (required for all three charts):
```javascript
if (charts.main) {
    try {
        charts.main.destroy();
        charts.main = null;
    } catch (e) {
        console.warn('Error destroying chart:', e);
        charts.main = null;
    }
}
canvas.width = canvas.offsetWidth;
canvas.height = canvas.offsetHeight;
```

## Common Development Tasks

### Adding a New Log Source
1. Create `agents/agent_*.py` following existing patterns
2. Implement log parsing and pattern matching
3. Normalize events to `LogEvent` schema with proper os_type
4. POST to `/ingest` endpoint
5. Update documentation and RELEASE_NOTES

### Adding a New Event Type
1. Add to `event_type` Literal in `core/models.py`
2. Update agents that should detect it
3. Update dashboard filters if needed
4. Add alerting rules if needed

### Creating a New Alerting Channel
1. Create `alerts/new_alerting_system.py` (follow telegram_alerts.py pattern)
2. Implement alert formatting and sending
3. Integrate with API server if needed (subscribe to events)
4. Add environment variables for configuration

### Modifying Event Schema
⚠️ Breaking change - requires database migration:
1. Update `LogEvent` model in `core/models.py`
2. Create migration script to update existing records
3. Update all agents using the new fields
4. Test thoroughly before deployment

## Testing & Validation

- **API health check:** GET http://localhost:8000/
- **Test API endpoint:** POST http://localhost:8000/ingest with sample events
- **Dashboard access:** http://localhost:8501
- **Database check:** Query `mini_siem.db` directly with `sqlite3` or tools

## Database Schema

### logs table
```sql
id INTEGER PRIMARY KEY
event_id TEXT UNIQUE
timestamp TEXT
source_host TEXT
os_type TEXT
event_type TEXT
severity INTEGER
source_ip TEXT
user TEXT
raw_message TEXT
created_at TIMESTAMP
```

Indices: timestamp DESC, event_type, source_ip, os_type, severity

### heartbeats table
```sql
id INTEGER PRIMARY KEY
source_host TEXT UNIQUE
os_type TEXT
last_seen TIMESTAMP
updated_at TIMESTAMP
```

Agent heartbeats track which hosts are currently active (optional feature).

## Deployment Notes

### Production Considerations
- Change `SIEM_API_KEY` from default
- Use HTTPS for agent-to-API communication
- Set appropriate file permissions on database
- Consider log rotation for agent logs
- Monitor agent process health with systemd/supervisord
- Telegram credentials should be in secure environment variables

### Agent Systemd Service Example
```ini
[Unit]
Description=Heimdall Linux Agent
After=network.target

[Service]
Type=simple
User=siem
WorkingDirectory=/opt/heimdall
ExecStart=/usr/bin/python3 /opt/heimdall/agents/agent_linux.py
Restart=always
RestartSec=10
Environment="SIEM_API_URL=http://localhost:8000"
Environment="SIEM_API_KEY=your-key"

[Install]
WantedBy=multi-user.target
```

## Documentation

Key documentation files in `docs/`:
- **START_HERE.md** - Welcome and orientation guide
- **QUICKSTART.md** - 5-minute setup guide
- **instructions.md** - Detailed deployment for all agents
- **UPGRADE_TO_V2.md** - Migration from v1 to v2
- **README.md** - Feature overview
- **sas.md** - Technical specification

## Recent Changes (v2.0)

- Code reorganized into `agents/`, `core/`, `ui/`, `alerts/` directories
- macOS and Firewall agents added
- Telegram alerting system
- Event ID changed from `time.time()` to `uuid.uuid4()` for uniqueness
- Heartbeat table for agent status tracking
- Better error handling and logging

## Advanced Search & Filtering (v2.1)

The dashboard now supports Splunk-like advanced event filtering with real-time pagination.

### Search Syntax

Users can search events using field:value syntax with support for AND/OR/NOT operators.

#### Basic Syntax Examples
```
host:ubuntu                    # Search by hostname
user:root                      # Search by username
severity:5                     # Search by exact severity level
type:LOGIN_FAIL               # Search by event type
ip:192.168.1.100              # Search by source IP
```

#### Operators
```
AND                           # Combine filters (default between terms)
OR                            # Match any filter
NOT field:value               # Negate/exclude
-field:value                  # Shorthand for negation
```

#### Complex Queries
```
host:ubuntu AND severity:4                           # AND (default)
user:root OR user:admin                              # OR condition
-user:guest                                           # Exclude guest user
host:ubuntu AND (type:LOGIN_FAIL OR type:SUDO_ESCALATION)  # Grouping
(host:ubuntu OR host:debian) AND severity:5          # Complex query
```

#### Field Aliases
- **host, hostname** → source_host
- **user, username** → user
- **ip, source_ip** → source_ip
- **type, eventtype, event_type** → event_type
- **severity** → severity
- **os, os_type** → os_type
- **message, msg, raw_message** → raw_message

#### Quoted Values
```
"failed login attempt"         # Search raw_message for multi-word phrases
"authentication failed"        # Exact phrase matching in messages
```

### Quick Filters

In addition to search syntax, users can select from dynamic dropdowns:
- **Host**: Populated with unique hostnames from events
- **User**: Populated with unique usernames from events
- **Severity**: 1-5 scale selector
- **Event Type**: Predefined event types (LOGIN_FAIL, SUDO_ESCALATION, etc.)

### Pagination

- **Previous/Next buttons**: Navigate through pages
- **Page indicator**: Shows current page and total matches
- **Go-to-page input**: Jump directly to a specific page
- **Page size**: Fixed at 100 events per page
- **Total count**: API returns total matching events for accurate pagination

### Filtering Behavior

- **Real-time table updates**: Search results display immediately in the event table
- **Export integration**: Search filters apply to CSV/JSON exports
- **Pagination respects filters**: Pages calculated based on filtered results
- **Filter precedence**: Export dialog filters can override search filters for the same field
- **Client-side AND/OR/NOT**: Complex operators handled on the browser
- **Server-side equality**: Basic field matching done on API for efficiency

### Implementation Details

**Backend Support** (`core/server_api.py`):
- `/events` endpoint accepts filter parameters: source_ip, user, source_host, raw_message, severity_min, start_date, end_date, offset, limit
- Returns response with total_count for pagination
- Maximum limit: 10,000 events per request
- All date filters use ISO format (YYYY-MM-DD)

**Frontend Parser** (`ui/index.html`):
- `parseSearchQuery()`: Tokenizes search syntax into structured filters
- `buildApiParams()`: Converts parsed query to API parameters
- `applyClientFilters()`: Applies AND/OR/NOT logic on client-side
- Handles quoted strings for multi-word values
- Case-insensitive matching for text fields

**Filter State Management**:
- `filterState`: Tracks current search query, parsed tokens, quick filters, pagination state
- `allRawEvents`: Stores full dataset before pagination for accurate filtering
- Dynamic dropdown population from event data

### Testing Checklist

✓ Basic field searches (host:ubuntu, user:root, severity:5)
✓ Operators (AND, OR, NOT/-prefix)
✓ Complex queries with parentheses
✓ Quoted multi-word values
✓ Quick filter dropdowns
✓ Pagination with filters (prev, next, go-to-page)
✓ Filter chips with removable buttons
✓ Search syntax help panel
✓ CSV/JSON export with filters
✓ Reset filters button
✓ Empty result handling
✓ Special characters in search
✓ Case-insensitive matching
✓ Mobile responsive design
✓ Performance with 1000+ events

## Git Workflow

Current branch: `master`

When making changes:
1. Make edits locally
2. Test thoroughly (run API, dashboard, agents)
3. Commit with clear message describing what was fixed/added
4. All modified agent files will auto-update with changes
