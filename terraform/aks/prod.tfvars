# Production configuration for AKS deployment
# Based on dev.tfvars with minimal resources for low traffic

# Azure region for resources
location = "australiaeast"

# Environment name
environment = "prod"

# Project name for resource naming
project_name = "heartbeat-k8s"

# Kubernetes version (leave null for latest stable)
kubernetes_version = null

# Node configuration - minimal for cost savings
node_count   = 1
node_vm_size = "Standard_B2s"

# Private cluster for enhanced security (enabled for production)
private_cluster_enabled = true

# Note: Azure AD group for AKS administrators is automatically created
# The current user (you) will be added as owner and member of this group

# Common tags
tags = {
  Project     = "heartbeat-k8s"
  Environment = "prod"
  ManagedBy   = "terraform"
  Owner       = "charles"
}
