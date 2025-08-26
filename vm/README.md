# VM Docker Compose Services

This directory contains Docker Compose configurations for services running on the Azure VM.

## Overview

The VM is designed to run Docker Compose workloads with the following features:
- Private networking (no public IP)
- SSH access via Cloudflare Access tunnel
- Secrets managed through Azure Key Vault
- Automated container updates via Watchtower
- Persistent storage on `/data` disk

## Services

### Current Services

#### secrets-sync
- **Purpose**: Placeholder for future secret synchronization service
- **Status**: Currently logs placeholder messages
- **Future**: Will sync secrets from Azure Key Vault and restart containers when secrets change
- **Environment Variables**:
  - `KEY_VAULT_NAME`: Name of the Azure Key Vault (auto-populated from .env)
  - `SYNC_INTERVAL`: Sync interval in seconds (default: 300)

#### watchtower
- **Purpose**: Automatically update Docker containers
- **Schedule**: Daily at 2 AM
- **Features**:
  - Cleans up old images
  - Monitors all containers for updates
  - Logs update activities

### Adding New Services

1. Add your service to `docker-compose.yaml`
2. Use persistent volumes under `/data/` for any data storage
3. Mount `/secrets` read-only for access to Key Vault secrets
4. Use the `vm-network` network for inter-container communication

Example service addition:
```yaml
services:
  my-app:
    image: my-app:latest
    container_name: my-app
    volumes:
      - /data/my-app:/app/data
      - /secrets:/secrets:ro
    environment:
      - DATABASE_URL=file:///app/data/app.db
    ports:
      - "127.0.0.1:3000:3000"  # Bind to localhost only
    restart: unless-stopped
    networks:
      - default
```

## Directory Structure

```
/home/user/heartbeat/vm/
├── docker-compose.yaml    # Main compose file
├── README.md             # This file
└── .env                  # Environment variables (auto-generated)

/data/                    # Persistent data disk
├── apps/                 # Application data
├── databases/            # Database files
└── logs/                 # Log files

/secrets/                 # Key Vault secrets (read-only)
├── cloudflare-tunnel-token
├── cloudflare-ca-public-key
└── git-repo-url
```

## Management Commands

### Service Management
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View service logs
docker compose logs -f [service_name]

# Restart a specific service
docker compose restart [service_name]

# Pull latest images and restart
docker compose pull && docker compose up -d
```

### System Information
```bash
# Check disk usage
df -h /data

# View VM system logs
sudo journalctl -u cloud-init-local.service
sudo journalctl -u cloud-init.service

# Check secrets sync logs
sudo tail -f /var/log/secrets-sync.log

# View cloud-init logs
sudo cat /var/log/cloud-init-output.log
```

### Secrets Management
Secrets are automatically synced from Azure Key Vault every 5 minutes via a systemd timer.

```bash
# Check secret sync status
sudo systemctl status secrets-sync.timer
sudo systemctl status secrets-sync.service

# Manually trigger secret sync
sudo systemctl start secrets-sync.service

# View available secrets
ls -la /secrets/
```

## Network Access

- **No Public IP**: The VM has no direct internet access for inbound connections
- **SSH Access**: Use Cloudflare Access tunnel: `cloudflared access ssh --hostname vm1.heartbeatchurch.com.au`
- **Application Access**: Configure Cloudflare tunnels to expose specific services
- **Local Binding**: Services should bind to `127.0.0.1` or use Docker networks

## Security Considerations

1. **No Public Services**: Never bind services to `0.0.0.0` unless using Cloudflare tunnel
2. **Secret Access**: Secrets in `/secrets/` are read-only and auto-synced
3. **Container Updates**: Watchtower automatically updates containers - test updates in dev first
4. **Firewall**: UFW is enabled with default deny-all inbound policy
5. **SSH**: Only certificate-based authentication via Cloudflare Access is enabled

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check Docker daemon
sudo systemctl status docker

# Check compose file syntax
docker compose config

# Check service logs
docker compose logs [service_name]
```

**Secrets not available:**
```bash
# Check managed identity
az account show

# Test Key Vault access
az keyvault secret list --vault-name [key_vault_name]

# Check sync service
sudo systemctl status secrets-sync.service
```

**Disk space issues:**
```bash
# Clean up Docker
docker system prune -a

# Check disk usage
du -sh /data/*

# Clean old logs
sudo journalctl --vacuum-time=7d
```

### Log Locations

- Cloud-init: `/var/log/cloud-init-output.log`
- Docker Compose: `docker compose logs`
- Secrets Sync: `/var/log/secrets-sync.log`
- System: `sudo journalctl`

## Cost Optimization

- VM automatically shuts down unused containers
- Watchtower cleans up old Docker images
- Logs are rotated automatically
- Use bind mounts instead of volumes where possible

## Future Enhancements

- [ ] Implement actual secrets-sync service with Azure CLI
- [ ] Add monitoring/alerting services
- [ ] Add backup service for `/data`
- [ ] Add log aggregation service
- [ ] Add CI/CD webhook service for automated deployments
