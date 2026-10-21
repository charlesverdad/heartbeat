#!/bin/bash
#
# deploy.sh - Deploy Pulse v2 to Cloudflare from a prebuilt bundle
# (pulse-v2 docs/deploy.md section 10: an infra repo keeps its own wrangler.jsonc).
#
# Usage (from the heartbeat repo root, in its nix shell, after `wrangler login`):
#   CONFIRM=yes manifests/pulse-v2/deploy.sh [--release vX.Y.Z | --ref <git ref>] [--secrets] [--rotate-hmac]
#
#   --release   download that GitHub release's bundle (charlesverdad/pulse-v2)
#   --ref       build the bundle from ~/work/pulse-v2 at this ref, in a throwaway
#               worktree (default: origin/main). Use until releases are cut.
#   --secrets   also upload the secrets from Azure Key Vault (secrets.sh). Needs
#               ADMIN_EMAILS. Required on the first deploy.
#   --rotate-hmac  include a new HMAC_SECRET (first deploy only: it signs everyone out)
#
# Reads the D1 id from terraform/pulse-v2's outputs and PUBLIC_ORIGIN from its
# prod.tfvars, applies remote D1 migrations, then deploys env.production.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HERE="$REPO_ROOT/manifests/pulse-v2"
TF_DIR="$REPO_ROOT/terraform/pulse-v2"
PULSE_V2_REPO="${PULSE_V2_REPO:-$HOME/work/pulse-v2}"
GH_REPO="charlesverdad/pulse-v2"

release=""
ref="origin/main"
with_secrets=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --release) release="$2"; shift 2 ;;
        --ref) ref="$2"; shift 2 ;;
        --secrets) with_secrets=yes; shift ;;
        --rotate-hmac) export ROTATE_HMAC=yes; shift ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [[ "${CONFIRM:-}" != "yes" ]]; then
    echo "Refusing to deploy: this changes production. Re-run with CONFIRM=yes." >&2
    exit 1
fi
if [[ -n "${ROTATE_HMAC:-}" && -z "$with_secrets" ]]; then
    echo "--rotate-hmac needs --secrets" >&2
    exit 2
fi

log() { echo "==> $*" >&2; }

# ── Values from terraform/pulse-v2 ──────────────────────────────────────────
d1_id=$(tofu -chdir="$TF_DIR" output -raw d1_database_id)
hostname=$(sed -n 's/^hostname *= *"\(.*\)"/\1/p' "$TF_DIR/prod.tfvars")
[[ "$d1_id" =~ ^[0-9a-f-]{36}$ ]] || { echo "bad d1_database_id from tofu: $d1_id" >&2; exit 1; }
[[ -n "$hostname" ]] || { echo "hostname not found in $TF_DIR/prod.tfvars" >&2; exit 1; }
public_origin="https://$hostname"
log "D1 $d1_id, PUBLIC_ORIGIN $public_origin"

# ── Get the bundle ──────────────────────────────────────────────────────────
work=$(mktemp -d)
src=""
cleanup() {
    [[ -n "$src" ]] && git -C "$PULSE_V2_REPO" worktree remove --force "$src" >/dev/null 2>&1 || true
    rm -rf "$work"
}
trap cleanup EXIT

if [[ -n "$release" ]]; then
    log "Downloading release $release"
    gh release download "$release" -R "$GH_REPO" -p "pulse-$release.tar.gz*" -D "$work"
    (cd "$work" && shasum -a 256 -c "pulse-$release.tar.gz.sha256")
    tarball="$work/pulse-$release.tar.gz"
else
    git -C "$PULSE_V2_REPO" fetch -q origin
    sha=$(git -C "$PULSE_V2_REPO" rev-parse --short "$ref")
    version="ref-$sha"
    log "Building bundle from $ref ($sha)"
    src="$work/src"
    git -C "$PULSE_V2_REPO" worktree add --detach "$src" "$sha" >/dev/null
    # The build bakes in no secrets; the placeholder only satisfies the dev fallback check.
    (cd "$src" && HMAC_SECRET=build-only-placeholder nix-shell shell.nix --run \
        "pnpm install --frozen-lockfile && just release-bundle $version" >&2)
    tarball="$src/dist/pulse-$version.tar.gz"
fi

bundle="$work/bundle"
mkdir -p "$bundle"
tar -xzf "$tarball" -C "$bundle"
wrangler_version=$(sed -n 's/.*Built with wrangler \([0-9.]*\).*/\1/p' "$bundle/DEPLOY.md")
[[ -n "$wrangler_version" ]] || { echo "wrangler version not found in DEPLOY.md" >&2; exit 1; }
# A local install, called directly: npx would not pass the <(secrets.sh) descriptor through.
log "Installing wrangler $wrangler_version"
npm install --silent --no-save --prefix "$work/wrangler" "wrangler@$wrangler_version" >&2
wrangler() { (cd "$bundle" && "$work/wrangler/node_modules/.bin/wrangler" "$@"); }
log "$(head -3 "$bundle/DEPLOY.md" | tr '\n' ' ')"

sed -e "s/__D1_DATABASE_ID__/$d1_id/" -e "s#__PUBLIC_ORIGIN__#$public_origin#" \
    "$HERE/wrangler.jsonc" > "$bundle/wrangler.jsonc"

# ── Our config must declare the same bindings as the bundle's example ───────
bindings() {
    local out
    out=$(wrangler deploy --dry-run --env production -c "$1" --outdir "$work/dry-$1") \
        || { echo "dry run failed for $1" >&2; return 1; }
    out=$(sed -n 's/^\(env\.[A-Z_]*\).*  \([A-Z][A-Za-z0-9 ]*[a-z0-9]\) *$/\1 \2/p' <<<"$out" | sort)
    [[ -n "$out" ]] || { echo "no bindings parsed from the $1 dry run" >&2; return 1; }
    echo "$out"
}
theirs=$(bindings wrangler.example.jsonc)
ours=$(bindings wrangler.jsonc)
if [[ "$theirs" != "$ours" ]]; then
    diff <(echo "$theirs") <(echo "$ours") >&2 || true
    echo "Bindings differ from the bundle's wrangler.example.jsonc (< bundle, > ours)." >&2
    echo "Update manifests/pulse-v2/wrangler.jsonc to match, then re-run." >&2
    exit 1
fi

# Read secrets before touching anything, so a failure (az login expired, missing
# Key Vault entry) stops the deploy. Held in memory only; printf is a builtin, so
# the values never reach argv.
secrets_json=""
if [[ -n "$with_secrets" ]]; then
    secrets_json=$("$HERE/secrets.sh")
fi

# ── Migrate, then deploy ────────────────────────────────────────────────────
log "Applying D1 migrations"
wrangler d1 migrations apply DB --remote --env production

log "Deploying"
if [[ -n "$with_secrets" ]]; then
    wrangler deploy --env production --secrets-file <(printf '%s' "$secrets_json")
else
    wrangler deploy --env production
fi

log "Deployed. Smoke test: curl -sI $public_origin/ (docs/deploy.md section 5 in pulse-v2)"
