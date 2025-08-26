#!/bin/bash
#
# deploy.sh - Deploy Living Life Quiz with proper tunnel token
#

set -euo pipefail

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

# Check if running as root for secrets access
if [[ $EUID -eq 0 ]]; then
    error "Do not run this script as root. Run as vmadmin user."
fi

# Check if secrets directory exists
if [[ ! -d "/secrets" ]]; then
    error "Secrets directory /secrets does not exist. Run mount-secrets.sh first."
fi

# Check if tunnel token exists (using sudo since it may have restricted permissions)
if ! sudo test -f "/secrets/cloudflare-tunnel-token"; then
    error "Tunnel token not found. Run mount-secrets.sh first."
fi

log "Reading tunnel token from Key Vault secrets..."
export TUNNEL_TOKEN=$(sudo cat /secrets/cloudflare-tunnel-token)

if [[ -z "$TUNNEL_TOKEN" ]]; then
    error "Failed to read tunnel token"
fi

log "Stopping any existing deployment..."
docker compose down || true

log "Killing any conflicting cloudflared processes..."
sudo pkill -f cloudflared || true
sleep 2

log "Starting Living Life Quiz deployment..."
docker compose up -d

log "Checking container status..."
sleep 5
docker compose ps

log "Testing application..."
if curl -f http://localhost:3000 >/dev/null 2>&1; then
    log "✅ Application is responding locally"
else
    error "❌ Application is not responding locally"
fi

log "🎉 Deployment complete!"
log "Local access: http://localhost:3000"
log "External access: https://living-life.heartbeatchurch.com.au"
