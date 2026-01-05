#!/bin/bash
#
# mount-secrets.sh - Mount Azure Key Vault secrets to /secrets directory
# This script uses the VM's managed identity to fetch secrets from Key Vault
#

set -euo pipefail

# Configuration
SECRETS_DIR="/secrets/bookstack"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-}"
REQUIRED_SECRETS=(
    "app-key"
    "db-password"
    "mysql-root-password"
    "google-app-id"
    "google-app-secret"
    "mail-username"
    "mail-password"
    "cloudflare-tunnel-token"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

# Check if KEY_VAULT_NAME is provided
if [[ -z "$KEY_VAULT_NAME" ]]; then
    error "KEY_VAULT_NAME environment variable is required"
fi

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    error "Azure CLI is not installed"
fi

# Create secrets directory
log "Creating secrets directory: $SECRETS_DIR"
mkdir -p "$SECRETS_DIR"
# Allow traversable access to /secrets, but 700 on the app subfolder
chmod 755 /secrets || true
chmod 700 "$SECRETS_DIR"

# Login with managed identity
log "Logging in with managed identity..."
if ! az login --identity --output none; then
    error "Failed to login with managed identity"
fi

# Fetch and mount secrets
log "Fetching secrets from Key Vault: $KEY_VAULT_NAME"
for secret_name in "${REQUIRED_SECRETS[@]}"; do
    log "Fetching secret: $secret_name"
    
    secret_file="$SECRETS_DIR/$secret_name"
    
    # Try different naming conventions if needed, but for now assuming 1:1 mapping
    # Note: secrets in KV are kebab-case, files will be kebab-case
    
    if az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$secret_name" --query value -o tsv | tr -d '\r\n' > "$secret_file"; then
        chmod 600 "$secret_file"
        log "✓ Secret $secret_name mounted (and stripped) to $secret_file"
    else
        error "Failed to fetch secret: $secret_name"
    fi
done

log "All secrets successfully mounted to $SECRETS_DIR"

# Ensure the directory and files are accessible by the vmadmin user (PUID 1000)
# so the containers can read them.
log "Setting ownership to vmadmin (1000:1000)..."
chown -R 1000:1000 "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"
find "$SECRETS_DIR" -type f -exec chmod 600 {} +

log "Directory listing:"
ls -la "$SECRETS_DIR"
