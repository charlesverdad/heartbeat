#!/bin/bash
# Terraform wrapper script that pre-loads secrets from Azure Key Vault
# Usage: ./bin/tf.sh [terraform commands and arguments]

set -euo pipefail

# Configuration
KEYVAULT_NAME="kv-terraform-${ENVIRONMENT:-dev}"
CLOUDFLARE_SECRET_NAME="tf-cloudflare-api-token"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if Azure CLI is available and authenticated
check_azure_auth() {
    if ! command -v az >/dev/null 2>&1; then
        log_error "Azure CLI is not installed or not in PATH"
        exit 1
    fi

    if ! az account show >/dev/null 2>&1; then
        log_error "Not authenticated with Azure. Run 'az login' first."
        exit 1
    fi
}

# Fetch Cloudflare API token from Key Vault
get_cloudflare_token() {
    log_info "Fetching Cloudflare API token from Key Vault: $KEYVAULT_NAME"
    
    local token
    token=$(az keyvault secret show \
        --vault-name "$KEYVAULT_NAME" \
        --name "$CLOUDFLARE_SECRET_NAME" \
        --query "value" \
        --output tsv 2>/dev/null) || {
        log_error "Failed to fetch Cloudflare API token from Key Vault"
        log_error "Make sure the Key Vault '$KEYVAULT_NAME' exists and contains secret '$CLOUDFLARE_SECRET_NAME'"
        log_error "Also ensure you have 'Get' permission on the Key Vault secrets"
        exit 1
    }

    if [[ "$token" == "replace-me-with-actual-token" ]] || [[ -z "$token" ]]; then
        log_error "Cloudflare API token is not set or still has placeholder value"
        log_error "Update the secret with: az keyvault secret set --vault-name '$KEYVAULT_NAME' --name '$CLOUDFLARE_SECRET_NAME' --value 'your-actual-token'"
        exit 1
    fi

    echo "$token"
}

# Main execution
main() {
    log_info "Starting Terraform with Azure Key Vault integration"
    
    # Check prerequisites
    check_azure_auth
    
    # Fetch and export Cloudflare API token
    export CLOUDFLARE_API_TOKEN=$(get_cloudflare_token)
    log_info "✓ Cloudflare API token loaded from Key Vault"
    
    # Set other common Terraform variables
    export TF_VAR_environment="${ENVIRONMENT:-dev}"
    
    # Execute terraform with all provided arguments
    log_info "Executing: terraform $*"
    exec terraform "$@"
}

# Show usage if no arguments provided
if [[ $# -eq 0 ]]; then
    cat << EOF
Terraform Wrapper Script

This script automatically loads secrets from Azure Key Vault before running Terraform.

Usage: $0 [terraform command and arguments]

Examples:
  $0 init
  $0 plan
  $0 apply
  $0 destroy

Environment Variables:
  ENVIRONMENT  - Environment name (default: dev)

Prerequisites:
  - Azure CLI installed and authenticated (az login)
  - Key Vault '$KEYVAULT_NAME' exists
  - Secret '$CLOUDFLARE_SECRET_NAME' is set in the Key Vault
  - You have 'Get' permission on the Key Vault secrets

EOF
    exit 0
fi

# Run main function
main "$@"
