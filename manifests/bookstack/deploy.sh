#!/bin/bash
#
# deploy.sh - Deploy Bookstack on VM with Docker Compose
#

set -euo pipefail

# Configuration
APP_DOMAIN="docs.heartbeatchurch.com.au"
APP_URL="https://${APP_DOMAIN}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    error "Do not run this script as root. Run as vmadmin user."
fi

# Check if secrets directory exists
if ! sudo test -d "/secrets/bookstack"; then
    error "Secrets directory /secrets/bookstack does not exist. Run mount-secrets.sh first."
fi

# Check variables
if sudo test -f "/secrets/bookstack/cloudflare-tunnel-token"; then
    log "Reading tunnel token from secrets..."
    export TUNNEL_TOKEN=$(sudo cat /secrets/bookstack/cloudflare-tunnel-token)
else
    error "Tunnel token not found in /secrets/bookstack"
fi

if sudo test -f "/secrets/bookstack/mail-username"; then
    log "Reading mail username from secrets..."
    export MAIL_USERNAME=$(sudo cat /secrets/bookstack/mail-username)
else
    export MAIL_USERNAME="noreply@heartbeatchurch.com.au" # Fallback or error?
    log "Mail username not found, using default: $MAIL_USERNAME"
fi

export APP_URL="${APP_URL}"
log "Setting APP_URL to $APP_URL"

log "Stopping any existing deployment..."
docker compose down || true

log "Killing any conflicting cloudflared processes..."
sudo pkill -f cloudflared || true
sleep 2

log "Starting Bookstack deployment..."
docker compose up -d

log "Checking container status..."
sleep 5
docker compose ps

log "Testing application..."
# Bookstack on port 6875 (host mapped)
if curl -f http://localhost:6875 >/dev/null 2>&1; then
    log "✅ Application is responding locally"
else
    log "⚠️ Application might be starting up (Bookstack takes a moment) or failed."
fi

log "🎉 Deployment script finished."
log "Local access: http://localhost:6875"
log "External access: $APP_URL"
