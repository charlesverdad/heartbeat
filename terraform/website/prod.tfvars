# Production environment configuration

# Azure region for resources
location = "australiaeast"

# Environment name
environment = "prod"

# Project name for resource naming
project_name = "website"

# AKS kubelet identity object ID from AKS production deployment
aks_kubelet_identity_object_id = "542f81f5-5636-41b9-b6d9-e7730d55bad4"

# Cloudflare account ID (this is the same for all environments)
cloudflare_account_id = "d26a8771162442a563371ea8097acc89"

# MySQL configuration
mysql_admin_username = "ghostadmin"
mysql_version = "8.0.21"
mysql_availability_zone = "1"

# Common tags
tags = {
  Project     = "website"
  Environment = "prod"
  ManagedBy   = "terraform"
  Owner       = "charles"
}
