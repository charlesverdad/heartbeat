# Development environment configuration

# Azure region for resources
location = "australiaeast"

# Environment name
environment = "dev"

# Project name for resource naming
project_name = "website"

# AKS kubelet identity object ID from AKS deployment
aks_kubelet_identity_object_id = "c6d13428-15a4-40e1-9abc-a61f571f6295"

# Cloudflare account ID (this is the same for all environments)
# TODO: move this to a global variable. maybe in bin/tf script
cloudflare_account_id = "d26a8771162442a563371ea8097acc89"

# Common tags
tags = {
  Project     = "website"
  Environment = "dev"
  ManagedBy   = "terraform"
  Owner       = "charles"
}
