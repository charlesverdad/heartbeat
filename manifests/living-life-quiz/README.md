# Living Life Quiz - VM Deployment

This directory contains the production deployment configuration for the Living Life Quiz application running on Azure VM.

## Architecture

- **Application**: Living Life Quiz Node.js app
- **Tunnel**: Cloudflare tunnel for secure external access
- **Secrets**: Azure Key Vault secrets mounted to `/secrets`
- **Storage**: Docker volume for persistent SQLite database
- **Domain**: living-life.heartbeatchurch.com.au

## Files

- `docker-compose.yml` - Production Docker Compose configuration
- `mount-secrets.sh` - Script to mount Key Vault secrets to `/secrets`
- `README.md` - This file

## Prerequisites

1. VM with Docker and Azure CLI installed
2. VM managed identity with Key Vault access
3. ACR access configured for pulling images
4. Terraform resources deployed from `terraform/vm-living-life-quiz`

## Deployment Steps

### 1. Deploy Terraform Resources

```bash
cd terraform/vm-living-life-quiz
tf -f prod apply
```

This creates:
- Azure Key Vault with secrets
- Cloudflare tunnel and DNS record
- VM managed identity permissions

### 2. SSH into VM

```bash
ssh vmadmin@vm1.heartbeatchurch.com.au -o ProxyCommand="cloudflared access ssh --hostname vm1.heartbeatchurch.com.au" -i terraform/vm/vm_access_key
```

### 3. Clone Repository and Navigate

```bash
git clone https://github.com/charlesverdad/heartbeat.git
cd heartbeat/manifests/living-life-quiz
```

### 4. Mount Secrets

```bash
# Get Key Vault name from terraform output
export KEY_VAULT_NAME="kv-living-life-quiz-prod-xxxx"

# Mount secrets
sudo ./mount-secrets.sh
```

### 5. Login to ACR

```bash
az login --identity
az acr login --name acrheartbeatterraformzi87
```

### 6. Deploy Application

```bash
docker compose pull
docker compose up -d
```

### 7. Verify Deployment

```bash
# Check container status
docker compose ps

# Check logs
docker compose logs -f

# Test local access
curl http://localhost:3000

# Test external access
curl https://living-life.heartbeatchurch.com.au
```

## Monitoring

```bash
# View logs
docker compose logs -f living-life-quiz
docker compose logs -f cloudflared

# Check container health
docker compose ps
```

## Updating

```bash
# Pull latest images
docker compose pull

# Restart services
docker compose up -d
```

## Secrets Management

Secrets are managed via Azure Key Vault and mounted to `/secrets`:

- `/secrets/teacher-password` - Teacher login password
- `/secrets/session-secret` - Session encryption key
- `/secrets/cloudflare-tunnel-token` - Tunnel authentication token

## Troubleshooting

### Container not starting
```bash
docker compose logs living-life-quiz
```

### Tunnel connection issues
```bash
docker compose logs cloudflared
```

### Secrets not mounted
```bash
sudo ./mount-secrets.sh
ls -la /secrets
```

### ACR access issues
```bash
az login --identity
az acr login --name acrheartbeatterraformzi87
```
