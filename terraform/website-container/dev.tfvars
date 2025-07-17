# Development environment configuration

# Azure region for resources
location = "australiaeast"

# Environment name
environment = "dev"

# Project name for resource naming
project_name = "site"

# Cloudflare account ID (same as original)
cloudflare_account_id = "d26a8771162442a563371ea8097acc89"

# Cloudflare zone ID for heartbeatchurch.com.au
cloudflare_zone_id = "80440a32523d928c9d7e015168a67758"

# Domain name for the website
domain_name = "dev2.heartbeatchurch.com.au"

# Common tags
tags = {
  Project     = "website-container"
  Environment = "dev"
  ManagedBy   = "terraform"
  Owner       = "charles"
}
