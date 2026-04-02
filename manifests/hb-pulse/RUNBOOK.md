# HB-Pulse Deployment Runbook

Operational reference for deploying and managing Pulse on the Heartbeat VM.

## Access

```bash
SSH="ssh vmadmin@20.58.140.44 -i /Users/charles/.ssh/heartbeat_vm_access_key -o StrictHostKeyChecking=no"
```

## Paths on VM

| Path | Purpose |
|------|---------|
| `~/hb-pulse` | App source (git@github.com:charlesverdad/hb-pulse.git via SSH on port 443) |
| `~/heartbeat/manifests/hb-pulse` | docker-compose.yml, deploy.sh, mount-secrets.sh |
| `/secrets/hb-pulse/` | Mounted Key Vault secrets (root-owned, 600) |
| `/data/hb-pulse/postgres/` | PostgreSQL data |
| `/data/hb-pulse/uploads/` | User uploads |

## Key Details

| Item | Value |
|------|-------|
| URL | https://pulse.heartbeatchurch.com.au |
| Local port | 3001 (maps to container 3000) |
| Key Vault | `kv-vm-pulse-prod-w9es` |
| Terraform | `terraform/vm-hb-pulse/` with `tf -f prod plan/apply` |
| Docker image | `pulse:latest` (built locally or shipped from macOS) |
| Database | PostgreSQL 16 in `pulse-db` container |
| Tunnel | Cloudflare tunnel via `cloudflared-pulse` container |
| Admin email | charles@heartbeatchurch.com.au |
| SMTP | smtp.gmail.com:587 as noreply@heartbeatchurch.com.au |
| Git SSH config | VM uses `ssh.github.com:443` (port 22 blocked by NSG) |

## Common Operations

### Deploy new version

Always build locally on macOS — **never build on the VM** (it OOMs and causes downtime).
Requires `just release <version>` in `~/work/hb-pulse`, which creates a git tag and builds
`pulse:<version>` + `pulse:latest` for `linux/amd64`.

```bash
# 1. Tag and build locally (in ~/work/hb-pulse)
just release 0.2.2      # produces pulse:0.2.2 + pulse:latest

# 2. Export, transfer, load
VERSION=0.2.2
docker save pulse:$VERSION | gzip > /tmp/pulse-$VERSION.tar.gz
scp -i /Users/charles/.ssh/heartbeat_vm_access_key -o StrictHostKeyChecking=no /tmp/pulse-$VERSION.tar.gz vmadmin@20.58.140.44:/tmp/
$SSH "gunzip -c /tmp/pulse-$VERSION.tar.gz | docker load && docker tag pulse:$VERSION pulse:latest && rm /tmp/pulse-$VERSION.tar.gz"
rm /tmp/pulse-$VERSION.tar.gz

# 3. Redeploy
$SSH 'cd ~/heartbeat/manifests/hb-pulse && ./deploy.sh'
```

### Restart without rebuilding

```bash
$SSH 'cd ~/heartbeat/manifests/hb-pulse && ./deploy.sh'
```

### View logs

```bash
$SSH 'cd ~/heartbeat/manifests/hb-pulse && docker compose logs pulse --tail 50'
$SSH 'cd ~/heartbeat/manifests/hb-pulse && docker compose logs pulse-db --tail 50'
$SSH 'cd ~/heartbeat/manifests/hb-pulse && docker compose logs cloudflared-pulse --tail 50'
```

### Check health

```bash
$SSH 'curl -s http://localhost:3001/health'
$SSH 'docker stats --no-stream'
```

### Re-mount secrets (after Key Vault update)

```bash
$SSH 'cd ~/heartbeat/manifests/hb-pulse && sudo KEY_VAULT_NAME=kv-vm-pulse-prod-w9es ./mount-secrets.sh'
```

### Update manifests (docker-compose, deploy scripts)

```bash
$SSH 'cd ~/heartbeat && git pull origin main'
```

## Containers

| Container | Image | Port | Network |
|-----------|-------|------|---------|
| `pulse-db` | `postgres:16-alpine` | 5432 (internal) | pulse-network |
| `pulse` | `pulse:latest` | 3001→3000 | pulse-network |
| `cloudflared-pulse` | `cloudflare/cloudflared:latest` | — (host network) | host |

## Secrets in Key Vault

`session-secret`, `db-password`, `google-client-id`, `google-client-secret`, `vapid-public-key`, `vapid-private-key`, `smtp-pass`, `cloudflare-tunnel-token`

## Coexisting Services

The living-life quiz runs on the same VM on port 3000. Its manifests are at `~/heartbeat/manifests/living-life-quiz/` and secrets at `/secrets/`.
