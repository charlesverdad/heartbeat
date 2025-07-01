# Copy this file to terraform.tfvars and customize the values

# Azure region for resources
location = "australiaeast"

# Environment name
environment = "dev"

# Project name for resource naming
project_name = "heartbeat-k8s"

# Kubernetes version (leave null for latest stable)
kubernetes_version = null

# Node configuration
node_count   = 2
node_vm_size = "Standard_B2s"

# Private cluster for enhanced security (default: true)
# Set to false for easier access for development
private_cluster_enabled = false

# Note: Azure AD group for AKS administrators is automatically created
# The current user (you) will be added as owner and member of this group

# Common tags
tags = {
  Project     = "heartbeat-k8s"
  Environment = "dev"
  ManagedBy   = "terraform"
  Owner       = "charles"
}
