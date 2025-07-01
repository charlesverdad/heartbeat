# Ghost Blog on Azure with Terraform

This Terraform configuration deploys a production-ready Ghost blog on Azure using modern cloud-native services and best practices.

## Architecture

- **Azure Container Apps**: Hosts the Ghost application with auto-scaling
- **Azure Database for MySQL Flexible Server**: Managed database service
- **Azure Storage Account**: Blob storage for uploads and content
- **Azure Key Vault**: Secure storage for passwords and API tokens
- **Cloudflare Tunnel**: Secure access without exposing public IPs
- **Cloudflare Access**: Protects the Ghost admin area (/ghost)
- **Log Analytics**: Monitoring and logging for Container Apps

## Prerequisites

1. **Azure CLI** - Authenticated with appropriate permissions
2. **Terraform** >= 1.0
3. **Cloudflare Account** - With domain management
4. **Domain** - Managed by Cloudflare

## Required Azure Permissions

Your Azure account needs the following roles:
- `Contributor` on the subscription or resource group
- `Key Vault Administrator` for managing secrets
- `User Access Administrator` for role assignments

## Setup Instructions

### 1. Create Cloudflare API Token

Create a Cloudflare API token with the proper scopes. You have two options:

#### Option A: Using cloudflared CLI (Recommended)
```bash
# Login to cloudflared (this will open a browser and create a cert)
cloudflared tunnel login
```

#### Option B: Manual token creation
Go to https://dash.cloudflare.com/profile/api-tokens and create a custom token with these permissions:

**Zone permissions (for your specific domain zone):**
- `Zone:Zone:Read`
- `Zone:DNS:Edit` 
- `Zone:Zone Settings:Read`
- `Zone:Page Rules:Edit`

**Account permissions:**
- `Account:Cloudflare Tunnel:Edit`
- `Account:Access: Organizations, Identity Providers, and Groups:Edit`
- `Account:Access: Apps and Policies:Edit`

**Zone Resources:**
- Include: Specific zone → `your-domain.com`

**Account Resources:**
- Include: All accounts (or your specific account)

**Client IP Address Filtering:**
- Leave empty or restrict to your IP for additional security

### 2. Configure Environment Variables

Copy the environment template and configure your values:

```bash
cp .env.example .env
```

Edit `.env` with your specific values:

- **CLOUDFLARE_API_TOKEN**: Token created above
- **CLOUDFLARE_ZONE_ID**: Found in your domain's Cloudflare dashboard
- **CLOUDFLARE_ACCOUNT_ID**: Found in the right sidebar of Cloudflare dashboard
- **DOMAIN_NAME**: Your domain (e.g., "example.com")
- **ADMIN_EMAIL**: Email address that can access /ghost admin area

### 2. Initialize and Deploy

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Deploy the infrastructure
terraform apply
```

### 3. Post-Deployment Setup

After deployment, you'll need to set up the Cloudflare tunnel. Terraform has already created the tunnel configuration, but you need to run the tunnel daemon:

1. **Get the tunnel token from Azure Key Vault**:
   ```bash
   # Get the tunnel token that Terraform stored in Key Vault
   az keyvault secret show --vault-name $(terraform output -raw key_vault_name) --name cloudflare-tunnel-token --query value -o tsv
   ```

2. **Run the Cloudflare tunnel**:
   ```bash
   # Run the tunnel using the token from Key Vault
   cloudflared tunnel run --token <tunnel-token-from-keyvault>
   
   # Or run as a service (recommended for production)
   sudo cloudflared service install <tunnel-token-from-keyvault>
   ```

3. **Alternative: Manual tunnel creation (if you prefer CLI approach)**:
   ```bash
   # If you want to create the tunnel manually instead of using Terraform:
   # First, comment out the Cloudflare resources in cloudflare.tf
   # Then create tunnel manually:
   cloudflared tunnel login
   cloudflared tunnel create ghostblog-dev-tunnel
   
   # Configure the tunnel (create config.yml)
   cloudflared tunnel route dns ghostblog-dev-tunnel blog.example.com
   cloudflared tunnel run ghostblog-dev-tunnel
   ```

4. **Access Ghost Admin**:
   - Navigate to `https://your-subdomain.your-domain.com/ghost`
   - Complete the Ghost setup wizard
   - Create your admin account

## Environment Variables

The Container App automatically configures Ghost with these environment variables:

- `url`: Your custom domain URL
- `database__client`: mysql
- `database__connection__host`: MySQL server FQDN
- `database__connection__user`: Admin username
- `database__connection__database`: ghost
- `database__connection__password`: Auto-generated secure password
- `AZURE_STORAGE_CONNECTION_STRING`: For blob storage integration

## Security Features

- **Azure Key Vault**: All secrets (database passwords, API tokens) are stored securely
- **Managed Identity**: Container App uses managed identity for Key Vault access
- **Cloudflare Access**: Protects Ghost admin area with email-based authentication
- **Network Security**: No public IPs exposed; all traffic goes through Cloudflare
- **TLS**: End-to-end encryption via Cloudflare

## Storage Configuration

- **Uploads Container**: Public blob access for uploaded images
- **Themes Container**: Private storage for Ghost themes
- **Content Container**: Private storage for Ghost content
- **CORS**: Configured to allow requests from your domain

## Database Configuration

- **MySQL 8.0**: Latest stable version
- **Burstable Tier**: Cost-optimized for development/small blogs
- **Automated Backups**: 7-day retention
- **Firewall**: Restricted to Azure services only

## Monitoring

- **Log Analytics**: Container logs and metrics
- **Application Insights**: Can be added for advanced monitoring
- **Azure Monitor**: Built-in monitoring for all Azure resources

## Cost Optimization

- **Burstable MySQL**: B_Standard_B1s tier for cost efficiency
- **Container Apps**: Pay-per-use scaling
- **LRS Storage**: Locally redundant storage (upgrade to GRS for production)
- **Auto-scaling**: Scales down to 1 replica when not busy

## Scaling for Production

For production workloads, consider:

1. **MySQL**: Upgrade to General Purpose or Memory Optimized tiers
2. **Storage**: Enable geo-redundant backup (GRS)
3. **Key Vault**: Enable purge protection
4. **Network**: Implement private endpoints
5. **Monitoring**: Add Application Insights and alerts

## Troubleshooting

### Container App Issues
```bash
# Check container logs
az containerapp logs show --name <app-name> --resource-group <rg-name>

# Check container status
az containerapp show --name <app-name> --resource-group <rg-name>
```

### Database Connection Issues
```bash
# Test MySQL connectivity
mysql -h <mysql-fqdn> -u <username> -p
```

### Cloudflare Tunnel Issues
```bash
# Check tunnel status
cloudflared tunnel list

# Test tunnel connectivity
cloudflared tunnel info <tunnel-id>
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all data including the database and storage. Make sure to backup important content first.

## Support

For issues related to:
- **Terraform Configuration**: Check the Azure Provider documentation
- **Ghost Setup**: Refer to Ghost.org documentation
- **Cloudflare**: Check Cloudflare's developer documentation
- **Azure Services**: Use Azure documentation and support
