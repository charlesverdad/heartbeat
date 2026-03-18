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
| Docker image | `pulse:latest` (built locally on VM) |
| Database | PostgreSQL 16 in `pulse-db` container |
| Tunnel | Cloudflare tunnel via `cloudflared-pulse` container |
| Admin email | charles@heartbeatchurch.com.au |
| SMTP | smtp.gmail.com:587 as noreply@heartbeatchurch.com.au |
| Git SSH config | VM uses `ssh.github.com:443` (port 22 blocked by NSG) |

## Common Operations

### Deploy new version

```bash
# Pull latest app code and rebuild
$SSH 'cd ~/hb-pulse && GIT_SSH_COMMAND="ssh -p 443" git pull origin main && docker build -t pulse:latest .'

# Redeploy containers
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
