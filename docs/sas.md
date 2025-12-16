This is a "System Architecture Specification" designed to be fed into an LLM. It provides the strict constraints, architecture, and schema definitions necessary to build a production-grade, future-proof MVP.

You can copy and paste the block below directly into your AI coding assistant.

-----

# System Specification: Python Mini-SIEM (Multi-OS + Pi-hole)

**Role:** Act as a Senior Python Solutions Architect.
**Objective:** Build a modular, extensible Mini-SIEM (Security Information and Event Management) system using Python.
**Core Philosophy:** "Hub and Spoke" architecture. Agents must be lightweight and decoupled from the central server.

## 1\. High-Level Architecture

The system consists of three distinct parts:

1.  **The Collectors (Agents):** Lightweight Python scripts running on client machines (Windows, Linux, Pi-hole). They push data to the API.
2.  **The Core (Server):** A FastAPI backend that ingests logs and stores them in a central database.
3.  **The Interface (Dashboard):** A Streamlit application for visualization and threat hunting.

## 2\. Technology Stack Requirements

  * **Language:** Python 3.10+
  * **Backend API:** FastAPI (for high-performance async log ingestion).
  * **Database:** SQLite (with `wal` mode enabled for concurrency) or PostgreSQL (optional for scale).
  * **Dashboard:** Streamlit (with `plotly` for charts).
  * **OS Libraries:**
      * Windows: `pywin32` (for Event Log access).
      * Linux: `watchdog` (for file system monitoring) or standard I/O.
      * Pi-hole: `sqlite3` (for reading FTLDNS database).

## 3\. The Unified Data Schema

All agents must normalize their specific logs into this JSON structure before sending to the API:

```json
{
  "event_id": "UUID-v4",
  "timestamp": "ISO-8601 String (UTC)",
  "source_host": "String (e.g., 'ubuntu-server-01')",
  "os_type": "String ('WINDOWS', 'LINUX', 'PIHOLE')",
  "event_type": "String ('LOGIN_FAIL', 'SUDO_ESCALATION', 'DNS_BLOCK', 'CRITICAL_ERROR')",
  "severity": "Integer (1=Info, 2=Low, 3=Medium, 4=High, 5=Critical)",
  "source_ip": "String (IPv4/IPv6 or 'N/A')",
  "user": "String (Username or 'system')",
  "raw_message": "String (Original log line for context)"
}
```

## 4\. Agent Specifications (The "Spokes")

### A. Windows Agent (`agent_windows.py`)

  * **Library:** Use `pywin32`.
  * **Logic:**
      * Must run as a background service or scheduled task.
      * Query the **Security** event log.
      * **Filter 1:** Event ID `4625` (Failed Logon). Map to `LOGIN_FAIL`, Severity 3.
      * **Filter 2:** Event ID `4720` (User Created). Map to `ACCOUNT_CREATE`, Severity 4.
      * **Filter 3:** Event ID `1102` (Log Cleared). Map to `LOG_TAMPERING`, Severity 5.

### B. Linux Agent (`agent_linux.py`)

  * **Library:** Standard file I/O or `watchdog`.
  * **Logic:**
      * Tail `/var/log/auth.log` (Debian/Ubuntu) or `/var/log/secure` (RHEL/CentOS).
      * **Regex Pattern 1:** Detect "Failed password". Map to `LOGIN_FAIL`, Severity 3. Use Regex to extract IP and User.
      * **Regex Pattern 2:** Detect "COMMAND=/usr/bin/sudo". Map to `SUDO_ESCALATION`, Severity 2.

### C. Pi-hole Agent (`agent_pihole.py`)

  * **Method:** Do not parse text logs. Connect directly to the FTL database: `/etc/pihole/pihole-FTL.db`.
  * **Logic:**
      * Query the `queries` table.
      * **Filter:** Select rows where `status` IN (1, 4, 5, 9, 10, 11) (These status codes represent "Blocked" queries in Pi-hole v5/v6).
      * **Mapping:** Map these to `DNS_BLOCK`.
      * **Frequency:** Poll every 60 seconds (stateful: remember the last `id` processed to avoid duplicates).

## 5\. Server Specifications (The "Hub")

### API (`server_api.py`)

  * Create a `POST /ingest` endpoint.
  * Validate incoming JSON against the **Unified Data Schema** using Pydantic.
  * **Buffering:** If database is locked, implement a simple retry mechanism or memory queue.
  * **Future Proofing:** Include an `api_key` header check for security.

### Database (`database.py`)

  * Table `logs` must mirror the Unified Schema.
  * Create indices on `timestamp`, `event_type`, and `source_ip` for fast dashboard queries.

## 6\. Dashboard Specifications (`dashboard.py`)

  * **Framework:** Streamlit.
  * **Layout:**
      * **Top Row:** Key Metrics (Total Alerts (24h), Threats by OS, Most Blocked Domain).
      * **Middle Row:**
          * Chart 1: Line chart of "Events per Minute" colored by `os_type`.
          * Chart 2: Bar chart of "Top Attacking IPs" (Global).
      * **Bottom Row:** Raw Data Table with filters for `OS`, `Severity`, and `Event Type`.
  * **Refresh:** Add a button or auto-refresh logic (every 30s).

## 7\. Implementation Roadmap

Please generate the code in the following order:

1.  **`models.py`**: The Pydantic schemas.
2.  **`server_api.py`**: The FastAPI backend.
3.  **`agent_*.py`**: The three agent scripts (Windows, Linux, Pi-hole).
4.  **`dashboard.py`**: The Streamlit interface.
5.  **`instructions.md`**: How to run each component.

-----

### How to use this document

1.  **Copy the text** between the horizontal lines.
2.  **Paste it** into a fresh chat with your LLM.
3.  **Review the output:** The LLM will generate the file structure and code exactly matching these constraints.

**Why this is future-proof:**

  * **Decoupling:** By using an API (`POST /ingest`) instead of having agents write directly to the DB, you can move the server to the cloud later without changing the agents.
  * **Unified Schema:** The `os_type` field allows you to add MacOS or Firewall logs later without breaking the database structure.
  * **Pi-hole DB Access:** Reading the SQLite DB is far more reliable than parsing text logs, which change format often.