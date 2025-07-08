# Development environment configuration

# Azure region for resources
location = "australiaeast"

# Environment name
environment = "dev"

# Project name for resource naming
project_name = "website"

# AKS kubelet identity object ID from AKS deployment
aks_kubelet_identity_object_id = "c6d13428-15a4-40e1-9abc-a61f571f6295"

# Common tags
tags = {
  Project     = "website"
  Environment = "dev"
  ManagedBy   = "terraform"
  Owner       = "charles"
}
