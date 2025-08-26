# Production environment configuration
environment = "prod"

# Project configuration
project_name = "vm-llbs"

# VM Resource references (from VM terraform output)
vm_resource_group_name    = "rg-vm1-prod-8ts0"
vm_managed_identity_name  = "id-vm1-prod-8ts0"

# Cloudflare Configuration
cloudflare_account_id = "d26a8771162442a563371ea8097acc89"
cloudflare_zone_id    = "80440a32523d928c9d7e015168a67758"
domain_name           = "living-life.heartbeatchurch.com.au"

# Application secrets (replace with actual values)
teacher_password = "secure-teacher-password-123"
session_secret   = "your-secure-session-secret-key-here-must-be-very-long"

# Resource Tags
tags = {
  Project     = "vm-living-life-quiz"
  Environment = "prod"
  ManagedBy   = "terraform"
  Purpose     = "living-life-quiz-vm-deployment"
}
