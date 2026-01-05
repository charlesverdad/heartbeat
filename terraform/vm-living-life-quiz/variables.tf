variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "vm-llbs"
}

variable "vm_resource_group_name" {
  description = "Name of the VM's resource group"
  type        = string
}

variable "vm_managed_identity_name" {
  description = "Name of the VM's managed identity"
  type        = string
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
  description = "Domain name for the website"
  type        = string
  default     = "living-life.heartbeatchurch.com.au"
}

variable "teacher_password" {
  description = "Password for teacher access"
  type        = string
  sensitive   = true
}

variable "session_secret" {
  description = "Secret key for session management"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "vm-living-life-quiz"
    ManagedBy   = "terraform"
    Environment = "prod"
  }
}
