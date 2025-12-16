# 🛡️ Python Mini-SIEM - START HERE

Welcome! You now have a complete, production-ready Security Information and Event Management (SIEM) system.

## ⚡ 5-Minute Quick Start

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Initialize Database
```bash
python database.py
```

### Step 3: Start Server (Terminal 1)
```bash
python server_api.py
```

### Step 4: Start Dashboard (Terminal 2)
```bash
streamlit run dashboard.py
```

### Step 5: Generate Test Data (Terminal 3)
```bash
python test_api.py
```

**Done!** 🎉 Open dashboard at `http://localhost:8501`

---

## 📚 Documentation Guide

### 🚀 **New to this project?**
Start here → **[QUICKSTART.md](QUICKSTART.md)**  
(5-minute setup guide)

### 🔧 **Want to deploy to production?**
Read this → **[instructions.md](instructions.md)**  
(Complete deployment guide)

### 📖 **Need an overview?**
Check this → **[README.md](README.md)**  
(Features, architecture, troubleshooting)

### 📋 **Looking for file reference?**
See this → **[MANIFEST.md](MANIFEST.md)**  
(All files explained)

### ✨ **What was implemented?**
Review this → **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**  
(Complete feature list and status)

---

## 🎯 Key Features

✅ **Real-time Log Collection**
- Windows Event Logs (Event IDs: 4625, 4720, 1102)
- Linux Auth Logs (/var/log/auth.log)
- Pi-hole DNS Blocks (SQLite FTL database)

✅ **Central Dashboard**
- 24-hour metrics and trends
- Interactive charts (Plotly)
- Filterable event table
- Export as CSV/JSON

✅ **REST API**
- FastAPI backend
- Async/concurrent processing
- API key authentication
- Queryable event endpoint

✅ **Production Ready**
- Error handling
- Duplicate detection
- Stateful agents
- Database indices
- Comprehensive documentation

---

## 📊 System Components

```
Your Mini-SIEM
├── 📱 API Server (FastAPI)
│   └── Listens on http://localhost:8000
├── 📊 Dashboard (Streamlit)
│   └── Web UI at http://localhost:8501
├── 💾 Database (SQLite)
│   └── Local file: mini_siem.db
└── 🤖 Agents
    ├── Windows Agent (Event Logs)
    ├── Linux Agent (Auth Logs)
    └── Pi-hole Agent (DNS Blocks)
```

---

## 🔐 First-Time Security

⚠️ **Default API Key:** `default-insecure-key-change-me`

For development/testing, this is fine. **Before production, change it:**

```bash
export SIEM_API_KEY=$(openssl rand -hex 32)
```

Then update all agents and dashboard with the new key.

---

## 🚀 Next Steps

### Option A: Explore the System (5 min)
1. Run the quick start steps above
2. Check out the dashboard at `http://localhost:8501`
3. Run `python test_api.py` to generate test data
4. Play with filters and export options

### Option B: Deploy Linux Agent (10 min)
```bash
export SIEM_API_URL=http://localhost:8000
export SIEM_API_KEY=default-insecure-key-change-me
python agent_linux.py
```
This will monitor your system's auth logs in real-time.

### Option C: Deploy Windows Agent (10 min)
On Windows (as Administrator):
```powershell
$env:SIEM_API_URL = "http://localhost:8000"
$env:SIEM_API_KEY = "default-insecure-key-change-me"
python agent_windows.py
```
This will monitor Security event log in real-time.

### Option D: Go to Production (30 min)
1. Read [instructions.md](instructions.md) - Production section
2. Set up HTTPS/TLS
3. Deploy as systemd services
4. Configure database backups
5. Update firewall rules

---

## 📁 What's Included

### Core Application (7 files)
- `models.py` - Data validation
- `database.py` - SQLite backend
- `server_api.py` - FastAPI server
- `agent_windows.py` - Windows collector
- `agent_linux.py` - Linux collector
- `agent_pihole.py` - Pi-hole collector
- `dashboard.py` - Streamlit UI

### Documentation (7 files)
- `README.md` - Project overview
- `QUICKSTART.md` - 5-minute setup
- `instructions.md` - Full deployment guide
- `PROJECT_SUMMARY.md` - Implementation details
- `MANIFEST.md` - File reference
- `config.example.txt` - Configuration template
- `START_HERE.md` - This file!

### Testing (1 file)
- `test_api.py` - Sample data generator

### Configuration (2 files)
- `requirements.txt` - Python dependencies
- `sas.md` - Original specification

---

## ✅ Verification Checklist

After running the quick start, verify:

- [ ] Server started: `curl http://localhost:8000/health`
- [ ] Dashboard loaded: Visit `http://localhost:8501`
- [ ] Database created: `ls -la mini_siem.db`
- [ ] Test data sent: Check dashboard shows events
- [ ] Data in DB: `sqlite3 mini_siem.db "SELECT COUNT(*) FROM logs;"`

All should show success/data! ✅

---

## 🆘 Troubleshooting

### Port Already in Use?
```bash
# API on port 8001
python server_api.py --port 8001

# Dashboard on port 8502
streamlit run dashboard.py --server.port 8502
```

### Module Not Found?
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Can't Connect to API?
```bash
# Check API is running
curl -v http://localhost:8000/health

# Check firewall rules
netstat -tuln | grep 8000  # Linux
netstat -ano | findstr :8000  # Windows
```

### No Data in Dashboard?
1. Check test script: `python test_api.py`
2. Check database: `sqlite3 mini_siem.db "SELECT COUNT(*) FROM logs;"`
3. Refresh browser (F5)
4. Check browser console (F12)

See **[QUICKSTART.md](QUICKSTART.md)** troubleshooting section for more help.

---

## 📞 Getting Help

| Issue | Document |
|-------|----------|
| Installation | [QUICKSTART.md](QUICKSTART.md) |
| Setup | [QUICKSTART.md](QUICKSTART.md) |
| Production | [instructions.md](instructions.md) |
| Features | [README.md](README.md) |
| API Details | [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) |
| Files | [MANIFEST.md](MANIFEST.md) |

---

## 🎓 Architecture Overview

Your Mini-SIEM uses a **Hub and Spoke** model:

```
Agents (Spokes)          Server (Hub)           Interface
─────────────            ──────────             ─────────

┌─────────────┐         ┌──────────┐           ┌────────┐
│   Windows   │         │  FastAPI │           │ Stream-│
│   Agent     ├────────→│  Server  │←─────────→│  lit   │
└─────────────┘         │ (port    │           │ (port  │
                        │  8000)   │           │ 8501)  │
┌─────────────┐         │          │           └────────┘
│   Linux     │         │ SQLite   │
│   Agent     ├────────→│   DB     │
└─────────────┘         │          │
                        └──────────┘
┌─────────────┐             ↓
│  Pi-hole    │         mini_siem.db
│   Agent     ├────────→  (events)
└─────────────┘
```

- **Agents** collect logs and push to the API
- **Server** stores in SQLite database
- **Dashboard** queries the server for metrics

---

## 🚀 You're Ready!

Everything is set up and ready to go. Pick a next step above and get started!

**Questions?** Check the documentation files above.

**Issues?** See Troubleshooting section or read detailed guides.

**Ready for production?** Follow the deployment guide in [instructions.md](instructions.md).

---

## 🎉 Welcome to Your Mini-SIEM!

Built with ❤️ for security teams. Now go collect some security events! 🛡️

**Version:** 1.0.0 | **Status:** Production Ready | **Last Updated:** 2024-01-15

