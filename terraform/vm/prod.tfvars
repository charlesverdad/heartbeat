# Production environment configuration
environment = "prod"
location    = "australiaeast"

# VM Configuration
vm_name          = "vm1"
vm_size          = "Standard_B1ms"
data_disk_size   = 32
admin_username   = "user"

# Network Configuration
vnet_address_space   = "10.42.0.0/16"
subnet_address_space = "10.42.1.0/24"

# Repository Configuration
git_repo_url = "https://github.com/charlesverdad/heartbeat"

# Resource Tags
tags = {
  Project     = "vm1-prod"
  ManagedBy   = "terraform"
  Environment = "prod"
  Purpose     = "docker-compose-workloads"
}
