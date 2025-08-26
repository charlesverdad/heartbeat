# Heartbeat VM Golden Image

## Overview
This golden image contains a fully configured Ubuntu 22.04 VM with all necessary components pre-installed and optimized for fast deployment.

## What's Included
- ✅ **Docker & Docker Compose** - Ready to run containerized workloads
- ✅ **Cloudflared** - Configured for secure SSH tunneling
- ✅ **Azure CLI** - Pre-installed with managed identity support
- ✅ **SSH Auto User Creation** - Automatic user creation from Cloudflare certificates
- ✅ **Security Hardening** - UFW firewall, unattended upgrades, password auth disabled
- ✅ **Monitoring Scripts** - Built-in setup progress monitoring
- ✅ **Optimized Setup Script** - Fast boot sequence prioritizing SSH access

## Golden Image Details
- **Name**: `heartbeat-vm-golden-image`
- **Resource Group**: `RG-VM1-PROD-8TS0`
- **Location**: Australia East
- **OS**: Ubuntu 22.04 LTS (Gen2)
- **Created**: 2025-08-26T04:42:30Z

## Quick Deployment Commands

### 1. Create VM from Golden Image
```bash
# Set variables
RESOURCE_GROUP="rg-new-vm-prod"
VM_NAME="new-vm-prod"
LOCATION="australiaeast"
VM_SIZE="Standard_B1ms"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create VM from golden image
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image "/subscriptions/356b0996-276c-4104-b906-efa2014f9d64/resourceGroups/RG-VM1-PROD-8TS0/providers/Microsoft.Compute/images/heartbeat-vm-golden-image" \
  --size $VM_SIZE \
  --admin-username vmadmin \
  --generate-ssh-keys \
  --public-ip-address "" \
  --nsg-rule NONE
```

### 2. SSH Access via Cloudflare
```bash
# Access via Cloudflare tunnel (recommended)
ssh vmadmin@vm-hostname.yourdomain.com -o ProxyCommand="cloudflared access ssh --hostname vm-hostname.yourdomain.com"
```

## Post-Deployment Steps

1. **Configure Cloudflare Tunnel** (if using different hostname):
   ```bash
   # SSH into the VM and update tunnel configuration
   sudo cloudflared service install NEW_TUNNEL_TOKEN
   ```

2. **Update Secrets** (if using different Key Vault):
   ```bash
   # Update environment variables and restart services
   export KEY_VAULT_NAME="your-new-keyvault"
   ```

3. **Deploy Applications**:
   ```bash
   # Your docker-compose files will be in /home/vmadmin/heartbeat/vm/
   cd /home/vmadmin/heartbeat/vm
   docker compose up -d
   ```

## Benefits of Golden Image

- **⚡ Fast Deployment**: Skip 5-8 minutes of software installation
- **🔒 Security First**: Pre-hardened with optimal security settings  
- **📦 Ready-to-Run**: Docker and essential tools pre-installed
- **🔧 Standardized**: Consistent environment across all deployments
- **💰 Cost Effective**: Minimal image size, quick startup

## Monitoring New VMs

Once deployed from golden image, monitor startup with:
```bash
sudo /usr/local/bin/check-setup-progress.sh
```

## Image Updates

To update the golden image:
1. Deploy a VM from the current golden image
2. Make your updates and improvements  
3. Run sysprep: `sudo waagent -deprovision+user -force`
4. Deallocate and generalize the VM
5. Create new image version

## Support

For issues with VMs deployed from this golden image, check:
- `/var/log/cloud-init-output.log` for cloud-init issues
- `/var/log/vm-setup.log` for custom setup script logs  
- `sudo systemctl status cloudflared` for tunnel connectivity
- `docker ps` for container status
