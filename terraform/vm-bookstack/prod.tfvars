# Production environment configuration
environment = "prod"

# Project configuration
project_name = "vm-bookstack"

# VM Resource references (from VM terraform output)
vm_resource_group_name   = "rg-vm1-prod-8ts0"
vm_managed_identity_name = "id-vm1-prod-8ts0"

# Cloudflare Configuration
cloudflare_account_id = "d26a8771162442a563371ea8097acc89"
cloudflare_zone_id    = "80440a32523d928c9d7e015168a67758"
domain_name           = "docs.heartbeatchurch.com.au"

# BookStack Application Secrets
# Generate APP_KEY with: docker run --rm lscr.io/linuxserver/bookstack php /app/www/artisan key:generate --show
app_key              = "base64:REPLACE_WITH_GENERATED_KEY"
db_password          = "REPLACE_WITH_SECURE_PASSWORD"
mysql_root_password  = "REPLACE_WITH_SECURE_ROOT_PASSWORD"

# Google OAuth Configuration
# Create OAuth credentials at: https://console.developers.google.com/
# Authorized redirect URIs: https://docs.heartbeatchurch.com.au/login/service/google/callback
google_app_id     = "REPLACE_WITH_GOOGLE_CLIENT_ID"
google_app_secret = "REPLACE_WITH_GOOGLE_CLIENT_SECRET"

# SMTP/Gmail Configuration
# For Gmail, create an App Password at: https://myaccount.google.com/apppasswords
mail_username = "REPLACE_WITH_GMAIL_ADDRESS"
mail_password = "REPLACE_WITH_GMAIL_APP_PASSWORD"

# Resource Tags
tags = {
  Project     = "vm-bookstack"
  Environment = "prod"
  ManagedBy   = "terraform"
  Purpose     = "bookstack-wiki-deployment"
}
