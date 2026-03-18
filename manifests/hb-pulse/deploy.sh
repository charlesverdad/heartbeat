#!/bin/bash
#
# deploy.sh - Deploy HB-Pulse on VM with Docker Compose
#
# This script deploys the Pulse knowledgebase application using:
# - Docker Compose for container orchestration (app + PostgreSQL)
# - Azure Key Vault for secrets management
# - Cloudflare tunnel for secure external access
#
# External access: https://pulse.heartbeatchurch.com.au
# Local access: http://localhost:3001
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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    error "Do not run this script as root. Run as vmadmin user."
fi

# Check if secrets directory exists
SECRETS_DIR="/secrets/hb-pulse"
if [[ ! -d "$SECRETS_DIR" ]]; then
    error "Secrets directory $SECRETS_DIR does not exist. Run mount-secrets.sh first."
fi

log "Reading secrets from Key Vault..."
export DB_PASSWORD=$(sudo cat $SECRETS_DIR/db-password)
export SESSION_SECRET=$(sudo cat $SECRETS_DIR/session-secret)
export GOOGLE_CLIENT_ID=$(sudo cat $SECRETS_DIR/google-client-id)
export GOOGLE_CLIENT_SECRET=$(sudo cat $SECRETS_DIR/google-client-secret)
export VAPID_PUBLIC_KEY=$(sudo cat $SECRETS_DIR/vapid-public-key)
export VAPID_PRIVATE_KEY=$(sudo cat $SECRETS_DIR/vapid-private-key)
export SMTP_PASS=$(sudo cat $SECRETS_DIR/smtp-pass)
export TUNNEL_TOKEN=$(sudo cat $SECRETS_DIR/cloudflare-tunnel-token)
export ADMIN_EMAIL="charles@heartbeatchurch.com.au"

# Verify all secrets were read
for var in DB_PASSWORD SESSION_SECRET GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET \
           VAPID_PUBLIC_KEY VAPID_PRIVATE_KEY SMTP_PASS TUNNEL_TOKEN; do
    if [[ -z "${!var}" ]]; then
        error "Failed to read secret for $var"
    fi
done

# Create data directories
log "Ensuring data directories exist..."
sudo mkdir -p /data/hb-pulse/postgres
sudo mkdir -p /data/hb-pulse/uploads

log "Stopping any existing deployment..."
docker compose down || true

log "Starting HB-Pulse deployment..."
docker compose up -d

log "Checking container status..."
sleep 5
docker compose ps

log "Testing application..."
if curl -f http://localhost:3001/health >/dev/null 2>&1; then
    log "Application is responding locally"
else
    log "Application may still be starting up — check with: docker compose logs pulse"
fi

log "Deployment complete!"
log "Local access: http://localhost:3001"
log "External access: https://pulse.heartbeatchurch.com.au"
log ""
log "TROUBLESHOOTING:"
log "- If tunnel fails: Check 'docker compose logs cloudflared-pulse'"
log "- If app fails: Check 'docker compose logs pulse'"
log "- If DB fails: Check 'docker compose logs pulse-db'"
log "- If secrets missing: Run 'sudo KEY_VAULT_NAME=<name> ./mount-secrets.sh'"
