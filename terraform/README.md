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

### 1. Configure Variables

Copy the example variables file and customize it:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your specific values:

- **cloudflare_api_token**: Create one at https://dash.cloudflare.com/profile/api-tokens
- **cloudflare_zone_id**: Found in your domain's Cloudflare dashboard
- **cloudflare_account_id**: Found in the right sidebar of Cloudflare dashboard
- **domain_name**: Your domain (e.g., "example.com")
- **admin_emails**: Email addresses that can access /ghost admin area

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

After deployment, you'll need to:

1. **Install Cloudflare Tunnel**:
   ```bash
   # Get the tunnel token from Key Vault
   az keyvault secret show --vault-name <key-vault-name> --name cloudflare-tunnel-token --query value -o tsv
   
   # Install cloudflared and run the tunnel
   cloudflared tunnel run --token <tunnel-token>
   ```

2. **Access Ghost Admin**:
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
