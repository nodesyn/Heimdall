# Quick Start Guide - Mini-SIEM

Get the Mini-SIEM system up and running in 5 minutes!

## Prerequisites

- Python 3.10 or later
- pip package manager
- ~2 GB disk space

## Step 1: Install Dependencies (2 min)

```bash
cd /home/n0desyn/Nexus/coding/Python_Siem

# Install all required packages
pip install -r requirements.txt
```

## Step 2: Initialize Database (30 sec)

```bash
python database.py
```

This creates the `mini_siem.db` file with proper tables and indices.

## Step 3: Start the Server (Terminal 1)

```bash
python server_api.py
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The API is now ready at `http://localhost:8000`

## Step 4: Start the Dashboard (Terminal 2)

```bash
streamlit run dashboard.py
```

Expected output:
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

Open `http://localhost:8501` in your web browser.

## Step 5: Test with Sample Data (Terminal 3)

```bash
python test_api.py
```

This script will:
1. ✅ Check API health
2. ✅ Generate sample events (Linux, Windows, Pi-hole)
3. ✅ Submit events to the API
4. ✅ Query recent events
5. ✅ Display dashboard metrics

You should see the data appear in the dashboard!

## 📊 Dashboard Features

Once the dashboard loads (at `http://localhost:8501`), you'll see:

- **Key Metrics:** Total alerts, threats by OS, most blocked domain
- **Events per Minute:** Timeline chart showing activity over time
- **Top Attacking IPs:** Bar chart of source IPs
- **Threats by OS:** Pie chart distribution
- **Event Details:** Filterable table with all events

### Filtering Options

Use the sidebar filters to:
- Filter by OS (Windows, Linux, Pi-hole)
- Filter by severity (Info, Low, Medium, High, Critical)
- Filter by event type (LOGIN_FAIL, SUDO_ESCALATION, DNS_BLOCK, etc.)
- Control how many records to display

### Export Data

Download events as CSV or JSON for further analysis.

## 🔑 API Access

Test the API directly:

```bash
# Check health
curl http://localhost:8000/health

# Get events (replace YOUR_API_KEY with default: default-insecure-key-change-me)
curl -H "api-key: default-insecure-key-change-me" http://localhost:8000/events

# Filter by OS
curl -H "api-key: default-insecure-key-change-me" \
  "http://localhost:8000/events?os_type=LINUX&limit=5"

# Get metrics
curl -H "api-key: default-insecure-key-change-me" http://localhost:8000/metrics
```

## 🖥️ Next: Deploy an Agent

Once everything is working, deploy an agent to collect real logs.

### Linux Agent

```bash
# Set environment variables
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=default-insecure-key-change-me

# Run the agent (in another terminal)
python agent_linux.py
```

The Linux agent will:
- Monitor `/var/log/auth.log` (or `/var/log/secure`)
- Detect failed logins and sudo commands
- Send events to the API every 30 seconds

### Windows Agent

On Windows (PowerShell as Administrator):

```powershell
# Set environment variables
$env:SIEM_API_URL = "http://localhost:8000"
$env:SIEM_API_KEY = "default-insecure-key-change-me"

# Run the agent
python agent_windows.py
```

The Windows agent will:
- Monitor Security event log
- Detect failed logins, account creation, log tampering
- Send events to the API every 60 seconds

### Pi-hole Agent

On the Pi-hole server:

```bash
export SIEM_API_URL=http://your-central-server:8000
export SIEM_API_KEY=default-insecure-key-change-me

python agent_pihole.py
```

The Pi-hole agent will:
- Query the Pi-hole FTL database for blocked DNS queries
- Send events to the API every 60 seconds

## ⚠️ Security Notes

**Default API Key:** `default-insecure-key-change-me`

For testing, this is fine. **In production, change it:**

```bash
# Generate a new secure API key
export SIEM_API_KEY=$(openssl rand -hex 32)

# Update all agents with the new key
```

## 📚 Documentation

- **Full Instructions:** See `instructions.md` for production deployment
- **API Reference:** See `server_api.py` for all endpoints
- **Architecture:** See `README.md` for system overview

## 🆘 Troubleshooting

### API Won't Start

```bash
# Check if port 8000 is in use
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Use different port
python server_api.py --port 8001
```

### Dashboard Won't Load

```bash
# Check if Streamlit is installed
pip install streamlit

# Try port 8502
streamlit run dashboard.py --server.port 8502
```

### Test Script Fails

```bash
# Make sure the server is running
curl http://localhost:8000/health

# Check API key matches
echo $SIEM_API_KEY

# Verify database exists
ls -la mini_siem.db
```

### No Data in Dashboard

1. Verify test script ran successfully: `python test_api.py`
2. Check database has events: `sqlite3 mini_siem.db "SELECT COUNT(*) FROM logs;"`
3. Refresh dashboard page (F5)
4. Check browser console for errors (F12)

## 🎯 What's Next?

1. ✅ **Now:** Explore the dashboard with test data
2. ⏭️ **Then:** Deploy a real agent (Linux, Windows, or Pi-hole)
3. ⏳ **Later:** Set up production with HTTPS and persistent agents
4. 🚀 **Finally:** Integrate with your security monitoring workflow

## 📞 Need Help?

1. Check `instructions.md` for detailed setup
2. Review logs in each terminal window
3. Test API endpoints directly with curl
4. See `README.md` for architecture overview

---

**Congratulations!** 🎉

You now have a working Mini-SIEM system running locally. The dashboard is collecting test data, and the API is ready for real agents.

Next: Connect a real Linux or Windows agent to start collecting actual security events!

