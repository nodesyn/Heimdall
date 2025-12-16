#!/bin/bash

# Heimdall Linux Agent Installer
# Installs Python dependencies, sets up the agent script, and configures a systemd service.

set -e

# Configuration
INSTALL_DIR="/opt/heimdall"
CONFIG_DIR="/etc/heimdall"
SERVICE_NAME="heimdall-agent"
AGENT_SCRIPT_NAME="agent_linux.py"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root${NC}"
  exit 1
fi

# Usage usage
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <API_URL> <API_KEY>"
  echo "Example: $0 http://YOUR_HUB_IP:8010 my-secret-key"
  exit 1
fi

API_URL=$1
API_KEY=$2

echo -e "${GREEN}Installing Heimdall Linux Agent...${NC}"

# 1. Install Python 3 and Pip if missing
echo "Checking dependencies..."
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv
elif command -v dnf &> /dev/null; then
    # Fedora/RHEL 8+
    dnf install -y python3 python3-pip
elif command -v yum &> /dev/null; then
    # CentOS/RHEL 7
    yum install -y python3 python3-pip
else
    echo -e "${YELLOW}Warning: Could not detect package manager. Ensure Python 3 is installed.${NC}"
fi

# 2. Setup Directory Structure
echo "Setting up directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"

# 3. Create Virtual Environment (Avoid breaking system python)
echo "Creating Python virtual environment..."
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi

# 4. Install Python Dependencies
echo "Installing Python libraries..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install requests python-dateutil psutil

# 5. Copy Agent Script
# Assumes agent_linux.py is in the same directory as this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SOURCE_AGENT="$SCRIPT_DIR/$AGENT_SCRIPT_NAME"

if [ ! -f "$SOURCE_AGENT" ]; then
    echo -e "${RED}Error: $AGENT_SCRIPT_NAME not found in $SCRIPT_DIR${NC}"
    echo "Please ensure both install_linux_agent.sh and $AGENT_SCRIPT_NAME are in the same folder."
    exit 1
fi

echo "Copying agent script..."
cp "$SOURCE_AGENT" "$INSTALL_DIR/$AGENT_SCRIPT_NAME"
chmod +x "$INSTALL_DIR/$AGENT_SCRIPT_NAME"

# 6. Create Configuration File
echo "Configuring agent..."
cat > "$CONFIG_DIR/agent.env" <<EOF
SIEM_API_URL=$API_URL
SIEM_API_KEY=$API_KEY
SIEM_LINUX_INTERVAL=30
# Uncomment and customize SIEM_LOG_FILES to monitor additional log paths (comma-separated)
# SIEM_LOG_FILES=/var/log/auth.log,/var/log/syslog,/var/log/nginx/access.log
EOF
chmod 600 "$CONFIG_DIR/agent.env"

# 7. Create Systemd Service
echo "Creating systemd service..."
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Heimdall Linux Security Agent
After=network.target

[Service]
Type=simple
User=root
EnvironmentFile=$CONFIG_DIR/agent.env
Environment=PYTHONUNBUFFERED=1
WorkingDirectory=$INSTALL_DIR
# Use the virtual environment's python
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/$AGENT_SCRIPT_NAME
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 8. Enable and Start Service
echo "Starting service..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo -e "${GREEN}Installation Complete!${NC}"
echo "------------------------------------------------"
echo "Status: $(systemctl is-active $SERVICE_NAME)"
echo "Logs:   journalctl -u $SERVICE_NAME -f"
echo "Config: $CONFIG_DIR/agent.env"
echo "------------------------------------------------"
