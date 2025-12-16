# Heimdall (Mini-SIEM)

## Project Overview
Heimdall is a robust, modular Security Information and Event Management (SIEM) and Remote Monitoring & Management (RMM) system designed to monitor infrastructure security and health. It employs a "hub and spoke" architecture where distributed agents collect logs and system metrics from various sources (Windows, Linux, macOS, Pi-hole, Firewalls) and push normalized events to a central API server for aggregation, visualization, and alerting.

**Current Version Status:** Production Ready (v2.2) - Features stateful agents, duplicate prevention, precise heartbeat monitoring, and full RMM capabilities (System Status).

## Architecture
*   **Server (The Hub):** A FastAPI-based REST API that receives logs and system status, validates them, and stores them in a PostgreSQL database.
*   **Agents (The Spokes):** Standalone Python scripts deployed on endpoints. They are **stateful** (tracking their progress), use **deterministic IDs** to prevent duplicate data ingestion, and collect detailed system metrics (CPU, RAM, Disk, etc.) using `psutil`.
*   **Dashboard:** A responsive HTML/JS web interface for real-time visualization of threats, events, and host status, featuring dark-mode "LCARS" aesthetics and drill-down modals.
*   **Database:** PostgreSQL for high concurrency and JSONB support.

## Key Technologies
*   **Backend:** Python 3.10+, FastAPI, Uvicorn, PostgreSQL (psycopg2)
*   **Frontend:** HTML5, CSS3, JavaScript (Vanilla), Chart.js
*   **Database:** PostgreSQL
*   **Data Validation:** Pydantic
*   **Deployment:** Docker, Docker Compose

## Building and Running

### Local Development
1.  **Setup:**
    ```bash
    pip install -r requirements.txt
    python -m core.database_pg  # Initialize DB
    ```
2.  **Run Server:**
    ```bash
    python -m core.server_api
    # Runs on http://localhost:8010
    ```
3.  **Run Dashboard:**
    ```bash
    python ui/dashboard_server.py
    # Runs on http://localhost:8501
    ```
4.  **Run Agents:**
    *   **Windows:** `python agents/agent_windows.py` (Requires `pywin32`, `psutil`, runs as Admin)
    *   **Linux:** `python agents/agent_linux.py` (Requires `psutil`, read access to logs)
    *   **Pi-hole:** `python agents/agent_pihole.py` (Run on Pi-hole server)

### Docker Deployment
The project includes a `docker-compose.yml` for orchestrating the server and dashboard.
```bash
docker-compose up --build -d
```

## Key Files and Directories
*   `core/server_api.py`: FastAPI server. Handles `/ingest` (logs), `/heartbeat`, `/system-status`.
*   `core/database_pg.py`: PostgreSQL abstraction. Handles deduplication via `UNIQUE` constraints and JSONB storage.
*   `core/models.py`: Pydantic models for `LogEvent` and `SystemStatus`.
*   `ui/index.html`: Main dashboard interface.
*   `agents/`:
    *   `agent_windows.py`: Monitors Event Logs (Security, System) and System Metrics.
    *   `agent_linux.py`: Monitors Log Files (Auth, Web, Mail, Syslog) and System Metrics.
    *   `install_linux_agent.sh`: Automated installer for Linux.
    *   `Install-HeimdallAgent.ps1`: Automated installer for Windows.

## Development Conventions & Critical Implementation Details
*   **Duplicate Prevention:**
    *   **Deterministic IDs:** Agents generate `event_id`s based on content hashes (`md5(line)`) or unique properties (`RecordNumber`) to prevent duplicates.
    *   **State Persistence:** Agents track their progress (`.linux_agent_state`, `win_agent_state.json`) to avoid re-reading old logs on restart.
*   **Heartbeats:**
    *   Agents send heartbeats every 30-60s.
    *   Headers: `source-host`, `os-type`, `api-key`.
    *   Timestamps: ISO 8601 UTC.
*   **System Status (RMM):**
    *   Agents collect CPU, RAM, Disk, Network, and Process data using `psutil`.
    *   Sent via `POST /system-status`.
    *   Stored in `system_status` table (JSONB).
*   **Configuration:**
    *   Environment variables: `SIEM_API_URL`, `SIEM_API_KEY`, `SIEM_LOG_FILES`.
    *   Alert rules are stored in the database (`config` table).

## Troubleshooting
*   **Heartbeat Failures:** Ensure agents use `source-host` (not `source_host`) in headers.
*   **Agent Crashes:** Check for `psutil` dependency. Verify file permissions.
*   **Inactive Hosts:** Check if agent machine time is synchronized. Verify `record_heartbeat` logic in server.
*   **Missing Events:** Check `SIEM_LOG_FILES` config in `agent.env`. Ensure server has updated `core/models.py` for new event types.
