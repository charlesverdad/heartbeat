variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "australiaeast"
}

variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "website"
}

variable "aks_kubelet_identity_object_id" {
  description = "Object ID of the AKS kubelet identity for role assignments"
  type        = string
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "website"
    ManagedBy = "terraform"
  }
}
