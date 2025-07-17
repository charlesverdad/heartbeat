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


variable "cloudflare_account_id" {
  description = "Cloudflare account ID for tunnel management"
  type        = string
}

variable "mysql_admin_username" {
  description = "MySQL administrator username"
  type        = string
  default     = "ghostadmin"
}

variable "mysql_version" {
  description = "MySQL version"
  type        = string
  default     = "8.0.21"
}

variable "mysql_availability_zone" {
  description = "Availability zone for MySQL server"
  type        = string
  default     = "1"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "website"
    ManagedBy = "terraform"
  }
}
