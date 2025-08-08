## Knowledgebase Container

This contains terraform resources to deploy BookStack as our internal knowledgebase website.

## Overview

This deployment creates a complete BookStack instance with:
- **BookStack**: Main wiki/documentation application
- **MariaDB**: Database backend (co-located for cost savings)
- **Redis**: Caching and session storage
- **Azure Files**: Persistent storage for data
- **Azure Key Vault**: Secure secret management
- **Cloudflare Tunnel**: Secure external access

## Architecture

All services run in a single Azure Container App with multiple containers:
1. `bookstack` - Main application (lscr.io/linuxserver/bookstack)
2. `mariadb` - Database (lscr.io/linuxserver/mariadb)
3. `redis` - Caching (redis:7-alpine)
4. `cloudflared` - Tunnel for external access

## Authentication

BookStack is configured for:
- **Google OAuth** - Primary authentication method
- **SMTP via Gmail** - Email notifications and password resets

## Deployment

### Prerequisites

1. **Google Cloud Project**: Ensure you have a Google Cloud project (configured in tfvars)
2. **Google Cloud Authentication**: Set up gcloud authentication or service account
3. **Gmail App Password**: Generate an app-specific password for SMTP

### Deploy to Development

```bash
# Deploy to dev environment
bin/tf -f dev apply terraform/kb-container
```

### Deploy to Production

```bash
# Deploy to prod environment
bin/tf -f prod apply terraform/kb-container
```

### Post-Deployment Configuration

After deployment, you need to complete the setup:

1. **Google OAuth Client**: The OAuth client is automatically created during deployment. You can find the client ID in the Terraform outputs.

2. **Gmail App Password**: Update the Gmail app password in Azure Key Vault:
   ```bash
   # Replace with actual Gmail app password
   az keyvault secret set --vault-name <key-vault-name> --name gmail-app-password --value <your-app-password>
   ```

3. **Configure OAuth Consent Screen** (if not done previously):
   - Go to Google Cloud Console > APIs & Services > OAuth consent screen
   - Configure the consent screen with your application details
   - Add authorized domains (heartbeatchurch.com.au)

4. **Restart Container App** to pick up new secrets:
   ```bash
   az containerapp revision restart --name <container-app-name> --resource-group <resource-group-name>
   ```

## Environment Variables

The following environment variables are configured for BookStack:

### Core Settings
- `APP_URL`: Set to the domain name
- `APP_KEY`: Auto-generated secure key
- `TZ`: Australia/Sydney

### Database
- `DB_HOST`: localhost (MariaDB container)
- `DB_DATABASE`: bookstack
- `DB_USERNAME`: bookstack
- `DB_PASSWORD`: Auto-generated

### Caching
- `REDIS_SERVERS`: localhost:6379:1
- `CACHE_DRIVER`: redis
- `SESSION_DRIVER`: redis

### Authentication
- `AUTH_METHOD`: social (Google OAuth only)
- `GOOGLE_CLIENT_ID`: From Key Vault
- `GOOGLE_CLIENT_SECRET`: From Key Vault
- `GOOGLE_REDIRECT_URI`: Auto-configured

### Email
- `MAIL_DRIVER`: smtp
- `MAIL_HOST`: smtp.gmail.com
- `MAIL_PORT`: 587
- `MAIL_ENCRYPTION`: tls
- `MAIL_USERNAME`: hello@heartbeatchurch.com.au
- `MAIL_FROM_ADDRESS`: hello@heartbeatchurch.com.au
- `MAIL_FROM_NAME`: Heartbeat Church

## Storage

- **BookStack Data**: `/config` mounted to Azure Files
- **MariaDB Data**: `/config` mounted to Azure Files  
- Data persists across container restarts and redeployments

## Domains

- **Development**: kb-dev.heartbeatchurch.com.au
- **Production**: kb.heartbeatchurch.com.au

## Cost Optimization

- Single container app with multiple containers (no separate database service)
- Minimal storage allocation (20GB BookStack, 10GB MariaDB)
- Standard LRS storage replication
- Shared resources across all containers

