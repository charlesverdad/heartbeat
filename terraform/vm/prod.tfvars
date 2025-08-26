# Production environment configuration
environment = "prod"
location    = "australiaeast"

# VM Configuration
vm_name          = "vm1"
vm_size          = "Standard_B1ms"
data_disk_size   = 32
admin_username   = "vmadmin"

# Network Configuration
vnet_address_space   = "10.42.0.0/16"
subnet_address_space = "10.42.1.0/24"

# Repository Configuration
git_repo_url = "https://github.com/charlesverdad/heartbeat"

# Cloudflare Configuration
cloudflare_account_id = "d26a8771162442a563371ea8097acc89"
cloudflare_zone_id    = "80440a32523d928c9d7e015168a67758"
domain_name           = "vm1.heartbeatchurch.com.au"

# Resource Tags
tags = {
  Project     = "vm1-prod"
  ManagedBy   = "terraform"
  Environment = "prod"
  Purpose     = "docker-compose-workloads"
}
