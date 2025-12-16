# Heimdall Heartbeat Implementation

## Overview

The heartbeat mechanism allows agents to signal their active status to the dashboard without creating database events. This keeps the event database focused on actual security events while enabling real-time visibility into agent availability.

## What Changed

### 1. Database Schema (core/database.py)

**New Table: `heartbeats`**
```sql
CREATE TABLE heartbeats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_host TEXT NOT NULL UNIQUE,
    os_type TEXT NOT NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

This table tracks the last time each agent sent a heartbeat, regardless of whether security events were detected.

**New Function: `record_heartbeat()`**
- Records or updates a heartbeat entry for an agent
- Uses `ON CONFLICT` to upsert (insert or update)
- Updates `last_seen` timestamp on every heartbeat

**Enhanced Function: `get_host_status()`**
- Now queries from both `heartbeats` and `logs` tables
- Uses `FULL OUTER JOIN` to capture all hosts
- Heartbeat timestamps take precedence for determining active status
- Maintains backward compatibility with event-based status

### 2. API Endpoint (core/server_api.py)

**New Endpoint: `POST /heartbeat`**
```
Headers:
  - api-key: Agent API key
  - source_host: Hostname of the agent
  - os_type: Operating system type (WINDOWS, LINUX, MACOS, PIHOLE)

Response:
  {
    "success": true,
    "message": "Heartbeat recorded for <hostname>",
    "timestamp": "2025-12-03T20:49:50.123456Z"
  }
```

Benefits:
- Lightweight (no event payload needed)
- Doesn't clutter the event database
- Only updates timestamps
- Silent operation (no logging required)

### 3. Agent Updates (All Agents)

**Modified `send_heartbeat()` Method:**
- Now calls `/heartbeat` endpoint instead of sending a fake event
- Uses HTTP headers to pass metadata (no request body)
- Fails silently if the call fails

**Modified `send_events()` Method:**
- Calls `send_heartbeat()` when no events are collected
- Ensures heartbeat is sent at every interval, regardless of event activity
- Maintains database cleanliness

**Agents Updated:**
- `agents/agent_windows.py`
- `agents/agent_linux.py`
- `agents/agent_macos.py`
- `agents/agent_pihole.py`

Example flow:
```python
def send_events(self, events):
    if not events:
        # No security events, send heartbeat only
        return self.send_heartbeat()
    
    # Has events, send them normally
    # If successful, heartbeat is implicit in the dashboard update
    ...
```

## How It Works

### Active Host Detection

1. **Event-based Activity:** When an agent sends events, the `logs` table is updated with new timestamps
2. **Heartbeat-based Activity:** When an agent has no events, it sends a heartbeat to update the `heartbeats` table
3. **Dashboard Query:** The `/hosts` endpoint queries both tables:
   - Shows agents with recent `heartbeat.last_seen` timestamps as "Active"
   - Shows agents without recent activity as "Inactive"
   - Threshold is configurable (default: 15 minutes)

### Database Impact

- **Event Log Size:** Remains clean - only real security events stored
- **Heartbeat Table:** One entry per agent, updated frequently
- **Query Performance:** Uses indexed lookups for fast host status retrieval

## Configuration

### Inactive Threshold

Control when hosts are considered "inactive" via the `/hosts` endpoint:

```bash
GET /hosts?inactive_threshold=15
```

- Default: 15 minutes
- Adjust based on your agent poll interval
- Recommended: 2-3x the agent collection interval

## Agent Configuration

Agents automatically send heartbeats when no events are detected:

```bash
# Environment Variables
SIEM_API_URL=http://YOUR_HUB_IP:8010
SIEM_API_KEY=your-api-key
```

The heartbeat interval matches the agent's collection interval:
- **Windows Agent:** 60 seconds
- **Linux Agent:** 30 seconds
- **macOS Agent:** 30 seconds
- **Pi-hole Agent:** 60 seconds

## Deployment Notes

After updating to this version:

1. **No Database Migration Required:** New tables are created automatically on startup
2. **Existing Events Preserved:** All historical event data remains intact
3. **Agent Update:** Copy new agent files to all monitored hosts
4. **Dashboard Refresh:** The dashboard automatically uses the new heartbeat mechanism

## Testing

### Verify Heartbeat Recording

1. Start an agent (or manually send heartbeat):
   ```bash
   curl -X POST http://YOUR_HUB_IP:8010/heartbeat \
     -H "api-key: your-api-key" \
     -H "source_host: test-host" \
     -H "os_type: LINUX"
   ```

2. Check host status:
   ```bash
   curl -H "api-key: your-api-key" \
     http://YOUR_HUB_IP:8010/hosts
   ```

3. Verify the host appears in "active_hosts" with recent "last_seen" timestamp

### Monitor Heartbeats

Check the database directly:
```bash
sqlite3 mini_siem.db "SELECT * FROM heartbeats ORDER BY last_seen DESC;"
```

## Troubleshooting

### Host Shows as Inactive

**Symptoms:** Agent is running but dashboard shows "Inactive"

**Check:**
1. Agent is actually running and connecting to API
2. API URL is correct (`SIEM_API_URL`)
3. API key is correct (`SIEM_API_KEY`)
4. Network connectivity from agent to API server
5. Check inactive threshold setting (default 15 min)

**Debug:**
```bash
# Check heartbeat table
sqlite3 mini_siem.db "SELECT * FROM heartbeats WHERE source_host='your-hostname';"

# Check API logs
ssh n0de@YOUR_HUB_IP 'cd ~/heimdall && docker-compose logs api'
```

### Old Heartbeats Not Updating

**Symptoms:** Heartbeat timestamp is old, agent should be running

**Check:**
1. Agent process is running
2. Agent can reach API endpoint (test with curl)
3. API key configuration matches on both ends
4. No firewall rules blocking the connection

### Events Not Appearing But Heartbeats Are

**Symptoms:** Host shows active on dashboard but no events

**This is normal if:**
- No security events are being triggered
- Agent is configured correctly but monitoring a quiet system

**To verify:** Check that heartbeats are being sent:
```bash
ssh n0de@YOUR_HUB_IP 'cd ~/heimdall && docker-compose logs --tail=20 | grep heartbeat'
```

## Architecture Diagram

```
Agent (Windows/Linux/macOS/Pi-hole)
    │
    ├─→ Collects Events
    │   └─→ Has events?
    │       ├─ YES → Send to /ingest → logs table
    │       └─ NO → Send to /heartbeat → heartbeats table
    │
    └─ Every poll interval (30-60 sec)

Dashboard
    │
    └─→ GET /hosts
        └─→ Query heartbeats + logs
            └─→ Show active/inactive status
```

## Benefits

✅ **Clean Database:** Events only contain real security data
✅ **Real-time Visibility:** See agent status updated every poll interval
✅ **Efficient:** Minimal overhead per heartbeat (~100 bytes)
✅ **Backward Compatible:** Works with existing event collection
✅ **Simple:** No complex state management needed
✅ **Scalable:** One database entry per agent regardless of event volume

## Future Enhancements

- Heartbeat metrics (e.g., total heartbeats, average latency)
- Stale agent detection and alerts
- Heartbeat failure patterns analysis
- Agent health scoring based on heartbeat consistency
