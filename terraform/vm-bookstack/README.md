# BookStack Terraform Configuration

This Terraform configuration creates the necessary secrets infrastructure for running BookStack in production with Google OAuth and Gmail SMTP support.

## What This Creates

- **Azure Key Vault**: Securely stores all secrets
- **Cloudflare Tunnel**: Provides secure access to BookStack
- **DNS Records**: Configures domain routing through Cloudflare

## Required Secrets

### BookStack Application Secrets
1. **app_key**: Laravel application key (base64 encoded)
2. **db_password**: MySQL/MariaDB password for BookStack database user
3. **mysql_root_password**: MySQL root password

### Google OAuth Secrets
4. **google_app_id**: Google OAuth Client ID
5. **google_app_secret**: Google OAuth Client Secret

### SMTP/Gmail Secrets
6. **mail_username**: Gmail address for sending emails
7. **mail_password**: Gmail App Password

## Setup Instructions

### 1. Generate APP_KEY

Run this command to generate a secure Laravel application key:

```bash
docker run --rm lscr.io/linuxserver/bookstack php /app/www/artisan key:generate --show
```

Copy the output (e.g., `base64:abcd1234...`) and use it for `app_key` in `prod.tfvars`.

### 2. Create Google OAuth Credentials

1. Go to [Google Developers Console](https://console.developers.google.com/)
2. Create a new project (or select existing)
3. Navigate to **APIs & Services** > **OAuth consent screen**
   - Enter product name: "BookStack"
   - Fill in required details and save
4. Navigate to **APIs & Services** > **Credentials**
5. Click **Create Credentials** > **OAuth client ID**
6. Choose application type: **Web application**
7. Add **Authorized redirect URIs**:
   ```
   https://bookstack.heartbeatchurch.com.au/login/service/google/callback
   https://bookstack.heartbeatchurch.com.au/register/service/google/callback
   ```
8. Click **Create** and note the **Client ID** and **Client Secret**

### 3. Create Gmail App Password

1. Go to [Google Account App Passwords](https://myaccount.google.com/apppasswords)
2. Sign in with your Gmail account
3. Create a new app password for "BookStack"
4. Copy the 16-character password (no spaces)

### 4. Configure prod.tfvars

Edit `prod.tfvars` and replace all placeholder values:

```hcl
app_key              = "base64:YOUR_GENERATED_KEY"
db_password          = "your-secure-db-password"
mysql_root_password  = "your-secure-root-password"
google_app_id        = "123456789-abcdef.apps.googleusercontent.com"
google_app_secret    = "GOCSPX-your-client-secret"
mail_username        = "your-email@gmail.com"
mail_password        = "your-app-password"
```

### 5. Deploy with Terraform

```bash
# Initialize Terraform
bin/tf -f prod init

# Review the plan
bin/tf -f prod plan

# Apply (do not use -auto-approve)
bin/tf -f prod apply
```

## Environment Variables for BookStack

Once deployed, configure your BookStack docker-compose.yaml to use these secrets:

```yaml
environment:
  - APP_KEY=${APP_KEY}              # From: app-key
  - DB_PASSWORD=${DB_PASSWORD}      # From: db-password
  - MYSQL_ROOT_PASSWORD=${ROOT_PWD} # From: mysql-root-password
  - GOOGLE_APP_ID=${GOOGLE_ID}      # From: google-app-id
  - GOOGLE_APP_SECRET=${GOOGLE_SEC} # From: google-app-secret
  - MAIL_USERNAME=${MAIL_USER}      # From: mail-username
  - MAIL_PASSWORD=${MAIL_PWD}       # From: mail-password
  
  # Static SMTP configuration for Gmail
  - MAIL_DRIVER=smtp
  - MAIL_HOST=smtp.gmail.com
  - MAIL_PORT=587
  - MAIL_ENCRYPTION=tls
  - MAIL_FROM=${MAIL_USER}
  - MAIL_FROM_NAME=BookStack
```

## Key Vault Secret Names

The following secrets are created in Azure Key Vault:

- `app-key`
- `db-password`
- `mysql-root-password`
- `google-app-id`
- `google-app-secret`
- `mail-username`
- `mail-password`
- `cloudflare-tunnel-token`

## Outputs

After deployment, Terraform outputs:

- `key_vault_name`: Name of the created Key Vault
- `key_vault_uri`: URI for accessing the Key Vault
- `cloudflare_tunnel_id`: ID of the Cloudflare tunnel
- `domain_name`: Configured domain name
- `dns_record_id`: Cloudflare DNS record ID

## Security Notes

- All secrets are stored in Azure Key Vault with RBAC authorization
- The VM's managed identity has "Key Vault Secrets User" role to read secrets
- Secrets are marked as sensitive in Terraform
- Never commit `prod.tfvars` with actual secret values to version control
