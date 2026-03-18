# Production environment configuration
environment  = "prod"
project_name = "vm-pulse"

# VM Resource references (from VM terraform output)
vm_resource_group_name   = "rg-vm1-prod-8ts0"
vm_managed_identity_name = "id-vm1-prod-8ts0"

# Cloudflare Configuration
cloudflare_account_id = "d26a8771162442a563371ea8097acc89"
cloudflare_zone_id    = "80440a32523d928c9d7e015168a67758"
domain_name           = "pulse.heartbeatchurch.com.au"

# Application secrets (replace with actual values before applying)
session_secret      = "REPLACE_ME"
db_password         = "REPLACE_ME"
google_client_id    = "REPLACE_ME"
google_client_secret = "REPLACE_ME"
vapid_public_key    = "REPLACE_ME"
vapid_private_key   = "REPLACE_ME"
smtp_pass           = "REPLACE_ME"

# Resource Tags
tags = {
  Project     = "vm-hb-pulse"
  Environment = "prod"
  ManagedBy   = "terraform"
  Purpose     = "hb-pulse-vm-deployment"
}
