variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ghostblog"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US 2"
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token"
  type        = string
  sensitive   = true
  default     = null
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID"
  type        = string
  default     = null
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID"
  type        = string
  default     = null
}

variable "admin_emails" {
  description = "List of admin email addresses for Cloudflare Access"
  type        = list(string)
  default     = []
}

variable "domain_name" {
  description = "Domain name for the Ghost blog"
  type        = string
  default     = null
}

variable "subdomain" {
  description = "Subdomain for the Ghost blog"
  type        = string
  default     = "blog"
}

variable "mysql_admin_username" {
  description = "MySQL administrator username"
  type        = string
  default     = "ghostadmin"
}

variable "container_cpu" {
  description = "CPU allocation for the container"
  type        = number
  default     = 1.0
}

variable "container_memory" {
  description = "Memory allocation for the container"
  type        = string
  default     = "2Gi"
}

variable "min_replicas" {
  description = "Minimum number of container replicas"
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum number of container replicas"
  type        = number
  default     = 3
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    Project     = "Ghost Blog"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}
