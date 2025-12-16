#!/bin/bash

# Heimdall SIEM Docker Deployment Script
# Deploys to remote host via SSH

set -e

# Configuration
REMOTE_USER="n0de"
REMOTE_HOST="YOUR_REMOTE_HOST"
REMOTE_DIR="~/heimdall"
SSH_TARGET="${REMOTE_USER}@${REMOTE_HOST}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Heimdall SIEM Deployment Script${NC}"
echo "=================================="
echo "Target: ${SSH_TARGET}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found.${NC}"
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env file with your configuration before deploying.${NC}"
        exit 1
    else
        echo -e "${RED}Error: .env.example not found.${NC}"
        exit 1
    fi
fi

# Check SSH connectivity
echo "Checking SSH connectivity..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes ${SSH_TARGET} exit 2>/dev/null; then
    echo -e "${RED}Error: Cannot connect to ${SSH_TARGET}${NC}"
    echo "Please ensure:"
    echo "  1. SSH key is configured"
    echo "  2. Host is reachable"
    echo "  3. User has access"
    exit 1
fi
echo -e "${GREEN}SSH connection successful${NC}"

# Check Docker on remote host
echo "Checking Docker on remote host..."
if ! ssh ${SSH_TARGET} "command -v docker >/dev/null 2>&1"; then
    echo -e "${RED}Error: Docker not found on remote host${NC}"
    echo "Please install Docker first:"
    echo "  curl -fsSL https://get.docker.com | sh"
    exit 1
fi
echo -e "${GREEN}Docker found${NC}"

# Check docker-compose on remote host
echo "Checking docker-compose on remote host..."
if ! ssh ${SSH_TARGET} "command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1"; then
    echo -e "${YELLOW}Warning: docker-compose not found, will use 'docker compose'${NC}"
fi

# Create remote directory
echo "Creating remote directory..."
ssh ${SSH_TARGET} "mkdir -p ${REMOTE_DIR}"

# Transfer files
echo "Transferring files..."
rsync -avz --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '*.db' \
    --exclude '*.db-shm' \
    --exclude '*.db-wal' \
    --exclude 'data/' \
    --exclude '.env' \
    ./ ${SSH_TARGET}:${REMOTE_DIR}/

# Transfer .env file separately (with confirmation)
echo ""
echo -e "${YELLOW}Transferring .env file...${NC}"
scp .env ${SSH_TARGET}:${REMOTE_DIR}/.env

# Build and start on remote host
echo ""
echo "Building Docker image on remote host..."
ssh ${SSH_TARGET} "cd ${REMOTE_DIR} && docker-compose build || docker compose build"

echo ""
echo "Starting services..."
ssh ${SSH_TARGET} "cd ${REMOTE_DIR} && docker-compose up -d || docker compose up -d"

# Wait for services to start
echo ""
echo "Waiting for services to start..."
sleep 5

# Health check
echo ""
echo "Checking service health..."
if ssh ${SSH_TARGET} "curl -f -s http://localhost:8010/health >/dev/null 2>&1"; then
    echo -e "${GREEN}✓ API server is healthy${NC}"
else
    echo -e "${YELLOW}⚠ API server health check failed (may still be starting)${NC}"
fi

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Services:"
echo "  API Server: http://${REMOTE_HOST}:8010"
echo "  Dashboard: http://${REMOTE_HOST}:8501"
echo ""
echo "To view logs:"
echo "  ssh ${SSH_TARGET} 'cd ${REMOTE_DIR} && docker-compose logs -f'"
echo ""
echo "To stop services:"
echo "  ssh ${SSH_TARGET} 'cd ${REMOTE_DIR} && docker-compose down'"
