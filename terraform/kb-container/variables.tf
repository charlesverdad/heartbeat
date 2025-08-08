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
  default     = "kb"
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID for tunnel management"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for DNS record management"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the BookStack instance"
  type        = string
}


variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project   = "bookstack-kb"
    ManagedBy = "terraform"
  }
}
