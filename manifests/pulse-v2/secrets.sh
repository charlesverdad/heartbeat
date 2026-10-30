#!/bin/bash
#
# secrets.sh - Print the Pulse v2 Worker secrets as JSON on stdout, for
# `wrangler deploy --secrets-file <(secrets.sh)`. deploy.sh --secrets does that;
# you should not need to run this directly.
#
# Values come from v1's Azure Key Vault (kv-vm-pulse-prod-*) and are streamed
# straight to wrangler: never written to disk, never printed to a terminal.
#
#   GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET  <- google-client-id / google-client-secret (v1's sign-in client)
#   GDRIVE_SA_EMAIL / GDRIVE_SA_PRIVATE_KEY  <- google-service-account-key (Drive folder embeds)
#   GMAIL_APP_PASSWORD                       <- smtp-pass (v1's Google Workspace app password for GMAIL_USER)
#   ADMIN_EMAILS                             <- $ADMIN_EMAILS (comma list of bootstrap admins)
#   HMAC_SECRET                              <- freshly generated, only with ROTATE_HMAC=yes
#
# HMAC_SECRET signs sessions and invite links, so a new one signs everyone out
# and voids open invites. It is needed once, on the first deploy.

set -euo pipefail

if [[ -t 1 ]]; then
    echo "Refusing to print secrets to a terminal. Use: CONFIRM=yes manifests/pulse-v2/deploy.sh --secrets" >&2
    exit 1
fi
: "${ADMIN_EMAILS:?set ADMIN_EMAILS to a comma list of bootstrap admins}"

KV=$(az keyvault list --query "[?starts_with(name, 'kv-vm-pulse-prod-')].name | [0]" -o tsv)
if [[ -z "$KV" ]]; then
    echo "v1 Key Vault kv-vm-pulse-prod-* not found. Run 'az login' first." >&2
    exit 1
fi
echo "Reading secrets from Key Vault $KV" >&2

kv() { az keyvault secret show --vault-name "$KV" --name "$1" --query value -o tsv; }
hmac() { if [[ "${ROTATE_HMAC:-}" == "yes" ]]; then openssl rand -base64 48; fi; }

# Process substitutions keep values out of argv. Their exit codes are lost, so
# jq checks every value is present instead.
jq -n \
    --rawfile id <(kv google-client-id) \
    --rawfile secret <(kv google-client-secret) \
    --rawfile sa <(kv google-service-account-key) \
    --rawfile gmail <(kv smtp-pass) \
    --rawfile hmac <(hmac) \
    --arg admins "$ADMIN_EMAILS" '
    def need($name): if . == "" then error("missing \($name)") else . end;
    ($sa | fromjson) as $key
    | {
        GOOGLE_CLIENT_ID: ($id | rtrimstr("\n") | need("google-client-id")),
        GOOGLE_CLIENT_SECRET: ($secret | rtrimstr("\n") | need("google-client-secret")),
        GDRIVE_SA_EMAIL: ($key.client_email | need("client_email")),
        GDRIVE_SA_PRIVATE_KEY: ($key.private_key | need("private_key")),
        GMAIL_APP_PASSWORD: ($gmail | rtrimstr("\n") | need("smtp-pass")),
        ADMIN_EMAILS: $admins
      }
    + (if $hmac == "" then {} else { HMAC_SECRET: ($hmac | gsub("\\s"; "")) } end)'
