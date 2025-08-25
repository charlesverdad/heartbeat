# VM Infrastructure Implementation Plan

## Overview
Create an Azure VM for running Docker Compose workloads with Cloudflare Tunnel access, Key Vault integration, and automated provisioning.

## Architecture Decisions

### Cloudflared Deployment
**Decision: Run cloudflared as a systemd service (not Docker container)**
- Reasoning: SSH access is critical infrastructure - if Docker daemon fails, we'd lose access to fix it
- systemd provides better reliability and system integration for essential services
- Docker containers will be used for application workloads only

### Secrets Management
- Azure Key Vault will store all secrets
- VM uses Managed Identity to access Key Vault
- Secrets are pulled during cloud-init and written to `/secrets/` with appropriate permissions
- Docker containers can mount `/secrets/` as read-only volumes

## Implementation Steps

### 1. Terraform Infrastructure (`terraform/vm/`)

#### Files to create:
- `main.tf` - Core Azure resources
- `variables.tf` - Input variables
- `outputs.tf` - Resource outputs  
- `providers.tf` - Terraform providers
- `key-vault.tf` - Azure Key Vault and secrets
- `cloud-init.tf` - Cloud-init configuration
- `prod.tfvars` - Production environment values

#### Resources:
1. **Resource Group**: `rg-vm1-prod-{random}`
2. **Key Vault**: `kv-vm1-prod-{random}`
3. **Key Vault Secrets**:
   - `cloudflare-tunnel-token`
   - `cloudflare-ca-public-key`
   - `git-repo-url` (default: https://github.com/charlesverdad/heartbeat)
4. **Networking**:
   - VNet: `vnet-vm1-prod` (10.42.0.0/16)
   - Subnet: `snet-vm1-prod` (10.42.1.0/24)
   - NSG: Inbound deny all, Outbound allow 443 + apt mirrors
5. **VM Components**:
   - User-Assigned Managed Identity
   - NIC (private IP only)
   - VM: Ubuntu 22.04 LTS, Standard_B1ms
   - OS Disk: Standard SSD
   - Data Disk: 32 GiB Standard SSD
6. **IAM**: Managed Identity access to Key Vault

#### Variables:
```hcl
# Core variables
variable "environment" { default = "prod" }
variable "location" { default = "australiaeast" }
variable "vm_name" { default = "vm1" }
variable "vm_size" { default = "Standard_B1ms" }
variable "data_disk_size" { default = 32 }

# Network configuration
variable "vnet_address_space" { default = "10.42.0.0/16" }
variable "subnet_address_space" { default = "10.42.1.0/24" }

# User configuration
variable "admin_username" { default = "user" }

# Tags
variable "tags" {
  default = {
    Project     = "vm1-prod"
    ManagedBy   = "terraform"
    Environment = "prod"
  }
}
```

### 2. Cloud-Init Configuration

#### Tasks (in order):
1. **System Updates**: Update package lists, install prerequisites
2. **User Setup**: Create user, add to docker group
3. **Disk Management**: Format and mount data disk to `/data`
4. **Docker Installation**: Install Docker CE + Compose plugin
5. **Azure CLI**: Install and configure for Key Vault access
6. **Secret Retrieval**: Pull secrets from Key Vault to `/secrets/`
7. **Cloudflared Setup**: Install and configure as systemd service
8. **SSH Configuration**: Configure cert-based auth with Cloudflare CA
9. **Repository Clone**: Clone heartbeat repo to `/home/user/heartbeat`
10. **Docker Compose**: Start initial services
11. **Security**: Configure ufw, enable unattended-upgrades

#### Key Vault Integration:
```bash
# Example secret retrieval in cloud-init
az login --identity
az keyvault secret show --vault-name "kv-vm1-prod-xxxx" --name "cloudflare-tunnel-token" --query "value" -o tsv > /secrets/cloudflare-tunnel-token
chmod 400 /secrets/cloudflare-tunnel-token
chown user:user /secrets/cloudflare-tunnel-token
```

### 3. VM Directory Structure (`vm/`)

#### Files to create:
- `docker-compose.yaml` - Initial Docker services
- `README.md` - VM usage documentation

#### Docker Compose Services:
```yaml
version: '3.8'
services:
  # Secrets synchronization service (future enhancement)
  secrets-sync:
    image: alpine:latest
    container_name: secrets-sync
    volumes:
      - /secrets:/secrets
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - KEY_VAULT_NAME=${KEY_VAULT_NAME}
      - SYNC_INTERVAL=300  # 5 minutes
    command: |
      sh -c '
        echo "Secrets sync service - implementation pending"
        echo "Will regularly check Key Vault for secret updates"
        echo "Will restart affected containers when secrets change"
        sleep infinity
      '
    restart: unless-stopped
    network_mode: host

  # Container update service
  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /secrets:/secrets:ro
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_SCHEDULE=0 2 * * *
    restart: unless-stopped
```

### 4. Security Configuration

#### SSH Setup:
- Disable password authentication
- Configure TrustedUserCAKeys for Cloudflare CA
- Cloudflare CA public key stored in Key Vault
- SSH config written during cloud-init

#### Network Security:
- No public IP on VM
- NSG rules: Inbound deny all, Outbound minimal
- UFW configured for additional local protection

#### Access Pattern:
```bash
# Client access via Cloudflare Access
cloudflared access ssh --hostname vm1.heartbeatchurch.com.au
```

### 5. Outputs

#### Terraform Outputs:
- `vm_private_ip`: Private IP address
- `vm_name`: Virtual machine name
- `resource_group_name`: Resource group name
- `key_vault_name`: Key Vault name
- `managed_identity_principal_id`: Managed Identity ID

## File Structure After Implementation

```
terraform/vm/
├── agent-plan.md
├── README.md
├── main.tf
├── variables.tf
├── outputs.tf
├── providers.tf
├── key-vault.tf
├── cloud-init.tf
└── prod.tfvars

vm/
├── docker-compose.yaml
└── README.md
```

## Deployment Process

1. **Populate Secrets**: Manually add secrets to Key Vault after first apply:
   ```bash
   # After terraform creates Key Vault
   az keyvault secret set --vault-name "kv-vm1-prod-xxxx" --name "cloudflare-tunnel-token" --value "your-token"
   az keyvault secret set --vault-name "kv-vm1-prod-xxxx" --name "cloudflare-ca-public-key" --value "ssh-rsa AAAAB3..."
   ```

2. **Apply Terraform**:
   ```bash
   tf -f prod apply
   ```

3. **Cloudflare Configuration** (manual, one-time):
   - Create Zero Trust Access application for SSH
   - Create tunnel for vm1.heartbeatchurch.com.au
   - Configure access policies

## Future Enhancements

- **Implement secrets-sync service**: Replace placeholder with actual Azure CLI-based secret synchronization
- Add systemd timer for automated docker-compose updates
- Add monitoring/logging services
- Add backup solution for `/data`
- Add CI/CD integration for application deployments

## Cost Estimation

- VM (Standard_B1ms): ~$15/month
- Storage (OS + Data disks): ~$8/month  
- Key Vault: ~$3/month
- Network: Minimal (no public IP, internal traffic)
- **Total**: ~$26/month

## Risk Mitigation

- Cloud-init logs available in `/var/log/cloud-init.log`
- Key Vault access logged via Azure Monitor
- SSH access logged via Cloudflare Access
- All infrastructure as code for reproducibility
- Data disk separate from OS for persistence
