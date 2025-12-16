# Heimdall (Mini-SIEM)

## Project Overview
Heimdall is a robust, modular Security Information and Event Management (SIEM) and Remote Monitoring & Management (RMM) system designed to monitor infrastructure security and health. It employs a "hub and spoke" architecture where distributed agents collect logs and system metrics from various sources (Windows, Linux, macOS, Pi-hole, Firewalls) and push normalized events to a central API server for aggregation, visualization, and alerting.

**Current Version Status:** Production Ready (v2.3) - Features stateful agents, RMM capabilities (System Status), advanced threat correlation, and mobile-responsive UI.

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

## Deployment & Installation

### 1. Hub (Server) Deployment
Deploy the Heimdall server using Docker Compose.
```bash
# Clone repository
git clone https://github.com/nodesyn/Heimdall.git
cd Heimdall

# Configure environment
cp .env.example .env
# Edit .env with your desired API key and database credentials

# Start services
docker-compose up --build -d
```
The dashboard will be available at `http://YOUR_SERVER_IP:8501`.

### 2. Agent Deployment

#### Linux Agent
Use the automated installer script for Debian/Ubuntu or RHEL/CentOS systems.
```bash
# On the target Linux machine:
# 1. Copy install_linux_agent.sh and agent_linux.py to the machine
# 2. Run the installer
sudo ./install_linux_agent.sh http://YOUR_HUB_IP:8010 YOUR_API_KEY
```
*   **Requirements:** Python 3.10+
*   **Configuration:** Edit `/etc/heimdall/agent.env` to add more log files to `SIEM_LOG_FILES`.

#### Windows Agent
Use the simplified "One-Click" installer.
1.  **Prepare Package:** Zip `agent_windows.py`, `Install-HeimdallAgent.ps1`, and a configured `agent.env`.
2.  **Deploy:** Unzip on target machine.
3.  **Install:** Right-click `Install-HeimdallAgent.ps1` -> "Run with PowerShell" (or run `install_agent.bat`).
*   **Requirements:** Windows 10/11 or Server 2016+, Administrator privileges.
*   **Features:** Runs as a Windows Service ("HeimdallAgent"), auto-installs dependencies (`psutil`, etc.).

#### macOS & Pi-hole
See detailed instructions in `docs/AGENT_INSTALLATION.md`.

## Key Features
*   **Security Monitoring:** Detects failed logins, sudo escalation, web attacks (SQLi/XSS), and more.
*   **RMM (System Status):** Real-time tracking of CPU, RAM, Disk usage, Network interfaces, and Top Processes.
*   **Threat Intelligence:** Correlates attacks by IP, showing target history and attack patterns.
*   **Alerting:** Configurable Telegram alerts for critical events and offline hosts.

## Documentation
*   [Agent Installation Guide](docs/AGENT_INSTALLATION.md)
*   [Windows Agent Troubleshooting](docs/WINDOWS_AGENT_TROUBLESHOOTING.md)
*   [Upgrade Guide](docs/UPGRADE_TO_V2.md)

## Development Conventions
*   **Duplicate Prevention:** Agents use content-hashing for deterministic IDs.
*   **State Persistence:** Agents track read positions to survive restarts without data loss.
*   **Timezones:** Agents report timestamps with local offsets; Dashboard standardizes display (user-selectable).
